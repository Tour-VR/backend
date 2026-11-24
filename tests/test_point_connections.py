"""Regras do modo VR nos pontos: panorama e conexoes (plano 019)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from bson import ObjectId
from pymongo.errors import PyMongoError

from app.repositories.point_repository import PointRepository
from tests.test_admin_points import VALID_PAYLOAD, fake_update, make_point, patch_repo


def connection(target: str, yaw: float = 90, label: str = "Cantina") -> dict[str, Any]:
    return {"target_slug": target, "label": label, "yaw_degrees": yaw}


def panorama(url: str = "/media/p.jpg") -> dict[str, Any]:
    return {"kind": "panorama", "url": url, "alt_text": "Vista 360"}


def create_ok(monkeypatch: pytest.MonkeyPatch, existing: set[str]) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def create(point_data: dict[str, Any]) -> str:
        captured.update(point_data)
        return str(ObjectId())

    def find_slugs_in(slugs: list[str]) -> set[str]:
        return {slug for slug in slugs if slug in existing}

    patch_repo(monkeypatch, find_by_slug=None, create_point=create, find_slugs_in=find_slugs_in)
    return captured


def test_create_with_valid_connection_returns_201(client, monkeypatch, as_admin) -> None:
    captured = create_ok(monkeypatch, {"cantina"})

    response = client.post(
        "/admin/points",
        json={
            **VALID_PAYLOAD,
            "media": [panorama()],
            "connections": [connection(" Cantina ", yaw=-45.5, label=" Cantina ")],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["connections"] == [connection("cantina", yaw=-45.5)]
    assert body["media"][0]["kind"] == "panorama"
    assert captured["connections"] == [connection("cantina", yaw=-45.5)]


def test_create_without_connections_stores_empty_list(client, monkeypatch, as_admin) -> None:
    captured = create_ok(monkeypatch, set())

    response = client.post("/admin/points", json=VALID_PAYLOAD)

    assert response.status_code == 201
    assert response.json()["connections"] == []
    assert captured["connections"] == []


def test_create_with_missing_target_returns_400(client, monkeypatch, as_admin) -> None:
    create_ok(monkeypatch, {"cantina"})

    response = client.post(
        "/admin/points",
        json={**VALID_PAYLOAD, "connections": [connection("cantina"), connection("ginasio")]},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Ponto de destino nao encontrado: ginasio."}


def test_create_connection_to_itself_returns_400(client, monkeypatch, as_admin) -> None:
    create_ok(monkeypatch, {"biblioteca-central"})

    response = client.post(
        "/admin/points",
        json={**VALID_PAYLOAD, "connections": [connection("biblioteca-central")]},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Um ponto nao pode se conectar a si mesmo."}


def test_create_repeated_target_returns_400(client, monkeypatch, as_admin) -> None:
    create_ok(monkeypatch, {"cantina"})

    response = client.post(
        "/admin/points",
        json={**VALID_PAYLOAD, "connections": [connection("cantina"), connection("cantina", 10)]},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Conexao repetida para o mesmo ponto."}


def test_create_with_nine_connections_returns_422(client, as_admin) -> None:
    connections = [connection(f"ponto-{index}") for index in range(9)]

    response = client.post("/admin/points", json={**VALID_PAYLOAD, "connections": connections})

    assert response.status_code == 422


@pytest.mark.parametrize(
    "item",
    [
        connection("cantina", yaw=181),
        connection("cantina", yaw=-180.5),
        connection("cantina", label=""),
        connection("cantina", label="x" * 61),
        connection("Cantina Nova"),
    ],
)
def test_create_with_invalid_connection_returns_422(client, as_admin, item) -> None:
    response = client.post("/admin/points", json={**VALID_PAYLOAD, "connections": [item]})

    assert response.status_code == 422


def test_create_with_two_panoramas_returns_400(client, monkeypatch, as_admin) -> None:
    create_ok(monkeypatch, set())

    response = client.post(
        "/admin/points",
        json={**VALID_PAYLOAD, "media": [panorama("/media/a.jpg"), panorama("/media/b.jpg")]},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "O ponto pode ter apenas um panorama."}


def test_update_replaces_connections(client, monkeypatch, as_admin) -> None:
    stored = make_point(connections=[connection("antiga")])
    captured: dict[str, Any] = {}
    patch_repo(
        monkeypatch,
        find_by_id=stored,
        find_slugs_in={"cantina"},
        update_point=fake_update(stored, captured),
    )

    response = client.put(
        f"/admin/points/{stored['_id']}", json={"connections": [connection("cantina")]}
    )

    assert response.status_code == 200
    assert captured["connections"] == [connection("cantina")]
    assert response.json()["connections"] == [connection("cantina")]


def test_update_with_two_panoramas_returns_400(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, find_by_id=make_point())

    response = client.put(
        f"/admin/points/{ObjectId()}",
        json={"media": [panorama("/media/a.jpg"), panorama("/media/b.jpg")]},
    )

    assert response.status_code == 400


def test_update_connection_to_itself_returns_400(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, find_by_id=make_point())

    response = client.put(
        f"/admin/points/{ObjectId()}", json={"connections": [connection("biblioteca-central")]}
    )

    assert response.status_code == 400


def test_old_document_without_connections_reads_empty(client, monkeypatch, as_admin) -> None:
    point = make_point()
    assert "connections" not in point
    patch_repo(monkeypatch, find_by_id=point)

    response = client.get(f"/admin/points/{point['_id']}")

    assert response.status_code == 200
    assert response.json()["connections"] == []


def test_connection_lookup_returns_503_when_database_fails(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, find_by_slug=None, find_slugs_in=ConnectionError("fora do ar"))

    response = client.post(
        "/admin/points", json={**VALID_PAYLOAD, "connections": [connection("cantina")]}
    )

    assert response.status_code == 503


def test_delete_cleanup_returns_503_when_database_fails(client, monkeypatch, as_admin) -> None:
    patch_repo(
        monkeypatch,
        find_by_id=make_point(),
        delete_point=True,
        remove_connections_to=ConnectionError("fora do ar"),
    )

    response = client.delete(f"/admin/points/{ObjectId()}")

    assert response.status_code == 503


class RecordingCollection:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def find(self, query: dict[str, Any], projection: dict[str, int]) -> Any:
        self.calls.append(("find", query, projection))
        return _Cursor([{"slug": "a", "name": "Ponto A"}])

    async def update_many(self, query: dict[str, Any], update: dict[str, Any], **kw: Any) -> None:
        self.calls.append(("update_many", query, update, kw))


class _Cursor:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self.documents = documents

    async def to_list(self, length: int | None) -> list[dict[str, Any]]:
        assert length is None
        return self.documents


def test_repository_connection_queries() -> None:
    collection = RecordingCollection()
    repository = PointRepository({"points": collection})

    assert asyncio.run(repository.find_slugs_in(["a", "b"])) == {"a"}
    assert asyncio.run(repository.find_slugs_in([])) == set()
    assert asyncio.run(repository.find_published_by_slugs(["a"])) == [
        {"slug": "a", "name": "Ponto A"}
    ]
    assert asyncio.run(repository.find_published_by_slugs([])) == []
    asyncio.run(repository.remove_connections_to("a"))
    asyncio.run(repository.rename_connection_target("a", "b"))

    assert collection.calls == [
        ("find", {"slug": {"$in": ["a", "b"]}}, {"slug": 1}),
        ("find", {"slug": {"$in": ["a"]}, "status": "published"}, {"slug": 1, "name": 1}),
        ("update_many", {}, {"$pull": {"connections": {"target_slug": "a"}}}, {}),
        (
            "update_many",
            {"connections.target_slug": "a"},
            {"$set": {"connections.$[conn].target_slug": "b"}},
            {"array_filters": [{"conn.target_slug": "a"}]},
        ),
    ]


@pytest.mark.parametrize(
    "call",
    [
        lambda r: r.find_slugs_in(["a"]),
        lambda r: r.find_published_by_slugs(["a"]),
        lambda r: r.remove_connections_to("a"),
        lambda r: r.rename_connection_target("a", "b"),
    ],
)
def test_repository_connection_queries_translate_mongo_errors(call: Any) -> None:
    class Failing:
        def find(self, *_args: Any) -> Any:
            raise PyMongoError("falhou")

        async def update_many(self, *_args: Any, **_kwargs: Any) -> None:
            raise PyMongoError("falhou")

    repository = PointRepository({"points": Failing()})

    with pytest.raises(ConnectionError):
        asyncio.run(call(repository))

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from bson import ObjectId

from app.core.security import create_access_token
from app.repositories.errors import UniqueConstraintError
from app.repositories.point_repository import PointRepository
from app.repositories.user_repository import UserRepository

OLD_DATE = datetime(2026, 1, 1, tzinfo=UTC)
SLUG_LOCKED = (
    "O slug nao pode mudar depois da primeira publicacao, "
    "pois os QR Codes impressos deixariam de funcionar."
)
VALID_PAYLOAD: dict[str, Any] = {
    "slug": "biblioteca-central",
    "name": "Biblioteca Central",
    "summary": "Onde ficam os livros.",
    "history": "Historia do nome.",
}


def make_point(**kwargs: Any) -> dict[str, Any]:
    point: dict[str, Any] = {
        "_id": ObjectId(),
        "slug": "biblioteca-central",
        "name": "Biblioteca Central",
        "summary": "Onde ficam os livros.",
        "history": "Historia do nome.",
        "status": "draft",
        "media": [],
        "created_at": OLD_DATE,
        "updated_at": OLD_DATE,
        "published_at": None,
    }
    point.update(kwargs)
    return point


def patch_repo(monkeypatch: pytest.MonkeyPatch, **methods: Any) -> None:
    """Troca metodos do PointRepository por funcoes async que devolvem o valor dado."""

    for name, value in methods.items():

        async def fake(_self: PointRepository, *_args: Any, _value: Any = value) -> Any:
            if isinstance(_value, Exception):
                raise _value
            return _value(*_args) if callable(_value) else _value

        monkeypatch.setattr(PointRepository, name, fake)


def fake_update(stored: dict[str, Any], captured: dict[str, Any]) -> Any:
    def update(_point_id: str, update_data: dict[str, Any]) -> dict[str, Any]:
        captured.clear()
        captured.update(update_data)
        stored.update(update_data)
        return dict(stored)

    return update


def test_create_point_success_returns_201(client, monkeypatch, as_admin) -> None:
    captured: dict[str, Any] = {}
    new_id = ObjectId()

    def create(point_data: dict[str, Any]) -> str:
        captured.update(point_data)
        return str(new_id)

    patch_repo(monkeypatch, find_by_slug=None, create_point=create)

    response = client.post(
        "/admin/points",
        json={
            **VALID_PAYLOAD,
            "slug": " Biblioteca-Central ",
            "media": [{"url": "https://x/foto.jpg", "alt_text": "Fachada"}],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == str(new_id)
    assert body["slug"] == "biblioteca-central"
    assert body["status"] == "draft"
    assert body["published_at"] is None
    assert body["media"][0]["id"]
    assert body["media"][0]["kind"] == "photo"
    assert captured["media"][0]["id"] == body["media"][0]["id"]


def test_create_point_invalid_slug_returns_422(client, as_admin) -> None:
    response = client.post("/admin/points", json={**VALID_PAYLOAD, "slug": "Biblioteca Central"})

    assert response.status_code == 422


def test_create_point_duplicate_slug_returns_409(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, find_by_slug=make_point())

    response = client.post("/admin/points", json=VALID_PAYLOAD)

    assert response.status_code == 409
    assert response.json() == {"detail": "Ja existe um ponto com este slug."}


def test_create_point_duplicate_key_returns_409(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, find_by_slug=None, create_point=UniqueConstraintError("slug"))

    response = client.post("/admin/points", json=VALID_PAYLOAD)

    assert response.status_code == 409
    assert response.json() == {"detail": "Ja existe um ponto com este slug."}


def test_create_point_returns_503_when_database_fails(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, find_by_slug=ConnectionError("fora do ar"))

    response = client.post("/admin/points", json=VALID_PAYLOAD)

    assert response.status_code == 503
    assert response.json() == {"detail": "Banco de dados indisponivel."}


def test_list_points_filters_by_status(client, monkeypatch, as_admin) -> None:
    received: list[str | None] = []

    def list_points(status: str | None) -> list[dict[str, Any]]:
        received.append(status)
        return [make_point(status="published", published_at=OLD_DATE)]

    patch_repo(monkeypatch, list_points=list_points)

    response = client.get("/admin/points", params={"status": "published"})

    assert response.status_code == 200
    assert received == ["published"]
    assert response.json()[0]["status"] == "published"


def test_list_points_invalid_status_returns_422(client, as_admin) -> None:
    response = client.get("/admin/points", params={"status": "xyz"})

    assert response.status_code == 422


def test_get_point_not_found_returns_404(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, find_by_id=None)

    response = client.get(f"/admin/points/{ObjectId()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Ponto de interesse nao encontrado."}


def test_get_point_success(client, monkeypatch, as_admin) -> None:
    point = make_point()
    patch_repo(monkeypatch, find_by_id=point)

    response = client.get(f"/admin/points/{point['_id']}")

    assert response.status_code == 200
    assert response.json()["id"] == str(point["_id"])


def test_update_point_success(client, monkeypatch, as_admin) -> None:
    stored = make_point()
    captured: dict[str, Any] = {}
    patch_repo(monkeypatch, find_by_id=stored, update_point=fake_update(stored, captured))

    response = client.put(f"/admin/points/{stored['_id']}", json={"name": "Biblioteca Nova"})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Biblioteca Nova"
    assert captured["updated_at"] > OLD_DATE
    assert set(captured) == {"name", "updated_at"}


def test_update_point_replaces_media_and_generates_ids(client, monkeypatch, as_admin) -> None:
    stored = make_point()
    captured: dict[str, Any] = {}
    patch_repo(monkeypatch, find_by_id=stored, update_point=fake_update(stored, captured))

    response = client.put(
        f"/admin/points/{stored['_id']}",
        json={
            "media": [
                {"id": "fixo", "url": "https://x/a.jpg", "alt_text": "A"},
                {"url": "https://x/b.jpg", "alt_text": "B", "caption": "Legenda"},
            ]
        },
    )

    assert response.status_code == 200
    media = captured["media"]
    assert media[0]["id"] == "fixo"
    assert media[1]["id"]
    assert media[1]["caption"] == "Legenda"
    assert "caption" in media[0]


def test_update_point_empty_payload_returns_400(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, find_by_id=make_point())

    response = client.put(f"/admin/points/{ObjectId()}", json={})

    assert response.status_code == 400
    assert response.json() == {"detail": "Nenhum campo valido para atualizacao."}


def test_update_slug_after_publication_returns_400(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, find_by_id=make_point(status="draft", published_at=OLD_DATE))

    response = client.put(f"/admin/points/{ObjectId()}", json={"slug": "biblioteca-nova"})

    assert response.status_code == 400
    assert response.json() == {"detail": SLUG_LOCKED}


def test_update_slug_while_draft_succeeds(client, monkeypatch, as_admin) -> None:
    stored = make_point()
    captured: dict[str, Any] = {}
    patch_repo(
        monkeypatch,
        find_by_id=stored,
        find_by_slug=None,
        update_point=fake_update(stored, captured),
    )

    response = client.put(f"/admin/points/{stored['_id']}", json={"slug": "biblioteca-nova"})

    assert response.status_code == 200
    assert response.json()["slug"] == "biblioteca-nova"


def test_update_slug_used_by_other_point_returns_409(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, find_by_id=make_point(), find_by_slug=make_point())

    response = client.put(f"/admin/points/{ObjectId()}", json={"slug": "biblioteca-nova"})

    assert response.status_code == 409


def test_update_point_duplicate_key_returns_409(client, monkeypatch, as_admin) -> None:
    patch_repo(
        monkeypatch,
        find_by_id=make_point(),
        update_point=UniqueConstraintError("slug"),
    )

    response = client.put(f"/admin/points/{ObjectId()}", json={"name": "Outro nome"})

    assert response.status_code == 409


def test_update_point_removed_meanwhile_returns_404(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, find_by_id=make_point(), update_point=None)

    response = client.put(f"/admin/points/{ObjectId()}", json={"name": "Outro nome"})

    assert response.status_code == 404


def test_delete_point_returns_204(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, delete_point=True)

    response = client.delete(f"/admin/points/{ObjectId()}")

    assert response.status_code == 204
    assert response.content == b""


def test_delete_point_not_found_returns_404(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, delete_point=False)

    response = client.delete(f"/admin/points/{ObjectId()}")

    assert response.status_code == 404


def test_publish_sets_published_at_once(client, monkeypatch, as_admin) -> None:
    stored = make_point()
    captured: dict[str, Any] = {}

    def find_by_id(_point_id: str) -> dict[str, Any]:
        return dict(stored)

    patch_repo(monkeypatch, find_by_id=find_by_id, update_point=fake_update(stored, captured))

    first = client.post(f"/admin/points/{stored['_id']}/publish")
    first_published_at = first.json()["published_at"]
    second = client.post(f"/admin/points/{stored['_id']}/publish")

    assert first.status_code == 200
    assert first.json()["status"] == "published"
    assert first_published_at is not None
    assert second.status_code == 200
    assert second.json()["published_at"] == first_published_at
    assert "published_at" not in captured


def test_unpublish_keeps_published_at(client, monkeypatch, as_admin) -> None:
    stored = make_point(status="published", published_at=OLD_DATE)
    captured: dict[str, Any] = {}
    patch_repo(monkeypatch, find_by_id=stored, update_point=fake_update(stored, captured))

    response = client.post(f"/admin/points/{stored['_id']}/unpublish")

    assert response.status_code == 200
    assert response.json()["status"] == "draft"
    assert response.json()["published_at"] is not None
    assert "published_at" not in captured


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/admin/points"),
        ("get", "/admin/points/x"),
        ("delete", "/admin/points/x"),
        ("post", "/admin/points/x/publish"),
        ("post", "/admin/points/x/unpublish"),
    ],
)
def test_admin_points_return_503_when_database_fails(
    client, monkeypatch, as_admin, method: str, path: str
) -> None:
    failure = ConnectionError("fora do ar")
    patch_repo(monkeypatch, list_points=failure, find_by_id=failure, delete_point=failure)

    response = client.request(method, path)

    assert response.status_code == 503


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/admin/points"),
        ("post", "/admin/points"),
        ("delete", "/admin/points/x"),
        ("post", "/admin/points/x/publish"),
    ],
)
def test_admin_points_without_token_returns_401(client, method: str, path: str) -> None:
    response = client.request(method, path)

    assert response.status_code == 401


def test_admin_points_with_user_role_returns_403(client, monkeypatch) -> None:
    async def fake_find_by_email(_self: UserRepository, email: str) -> dict[str, Any]:
        return {"email": email, "role": "user", "is_active": True}

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)
    token = create_access_token("me@example.com", extra_claims={"role": "user"})

    response = client.get("/admin/points", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_create_point_non_text_field_returns_422(client, as_admin) -> None:
    response = client.post("/admin/points", json={**VALID_PAYLOAD, "name": 123})

    assert response.status_code == 422

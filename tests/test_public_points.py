from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from bson import ObjectId

from app.repositories.point_repository import PointRepository

PUBLISHED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def make_point(**kwargs: Any) -> dict[str, Any]:
    point: dict[str, Any] = {
        "_id": ObjectId(),
        "slug": "biblioteca-central",
        "name": "Biblioteca Central",
        "summary": "Onde ficam os livros.",
        "history": "Historia do nome.",
        "status": "published",
        "media": [],
        "created_at": PUBLISHED_AT,
        "updated_at": PUBLISHED_AT,
        "published_at": PUBLISHED_AT,
    }
    point.update(kwargs)
    return point


def photo(url: str, kind: str = "photo") -> dict[str, Any]:
    return {"id": url, "kind": kind, "url": url, "caption": None, "alt_text": "Foto"}


def patch_method(monkeypatch: pytest.MonkeyPatch, name: str, value: Any) -> None:
    async def fake(_self: PointRepository, *_args: Any) -> Any:
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(PointRepository, name, fake)


def test_public_list_returns_only_summary_fields(client, monkeypatch) -> None:
    with_photos = make_point(media=[photo("https://x/1.jpg"), photo("https://x/2.jpg")])
    without_photo = make_point(slug="cantina", name="Cantina")
    only_other_kind = make_point(slug="auditorio", media=[photo("https://x/p.jpg", "panorama")])
    patch_method(monkeypatch, "list_published", [with_photos, without_photo, only_other_kind])

    response = client.get("/public/points")

    assert response.status_code == 200
    body = response.json()
    assert body[0] == {
        "slug": "biblioteca-central",
        "name": "Biblioteca Central",
        "summary": "Onde ficam os livros.",
        "cover_url": "https://x/1.jpg",
        "has_panorama": False,
    }
    assert body[1]["cover_url"] is None
    assert body[2]["cover_url"] is None
    assert body[2]["has_panorama"] is True


def test_public_detail_success(client, monkeypatch) -> None:
    patch_method(
        monkeypatch, "find_published_by_slug", make_point(media=[photo("https://x/1.jpg")])
    )
    patch_method(monkeypatch, "find_published_by_slugs", [])

    response = client.get("/public/points/biblioteca-central")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "slug",
        "name",
        "summary",
        "history",
        "media",
        "panorama_url",
        "connections",
    }
    assert body["media"] == [photo("https://x/1.jpg")]
    assert body["panorama_url"] is None
    assert body["connections"] == []


def test_public_detail_draft_returns_404(client, monkeypatch) -> None:
    patch_method(monkeypatch, "find_published_by_slug", None)

    response = client.get("/public/points/rascunho")

    assert response.status_code == 404
    assert response.json() == {"detail": "Ponto de interesse nao encontrado."}


@pytest.mark.parametrize(
    ("method_name", "path"),
    [
        ("list_published", "/public/points"),
        ("find_published_by_slug", "/public/points/biblioteca-central"),
    ],
)
def test_public_points_return_503_when_database_fails(
    client, monkeypatch, method_name: str, path: str
) -> None:
    patch_method(monkeypatch, method_name, ConnectionError("fora do ar"))

    response = client.get(path)

    assert response.status_code == 503


def test_public_detail_with_panorama_and_connections(client, monkeypatch) -> None:
    received: list[list[str]] = []
    point = make_point(
        media=[photo("https://x/1.jpg"), photo("/media/p.jpg", "panorama")],
        connections=[
            {"target_slug": "rascunho", "label": "Oculto", "yaw_degrees": 10},
            {"target_slug": "cantina", "label": "Ir a cantina", "yaw_degrees": 90},
        ],
    )

    async def find_published_by_slugs(_self: PointRepository, slugs: list[str]) -> Any:
        received.append(slugs)
        return [{"slug": "cantina", "name": "Cantina"}]

    patch_method(monkeypatch, "find_published_by_slug", point)
    monkeypatch.setattr(PointRepository, "find_published_by_slugs", find_published_by_slugs)

    response = client.get("/public/points/biblioteca-central")

    assert response.status_code == 200
    body = response.json()
    assert body["panorama_url"] == "/media/p.jpg"
    assert body["connections"] == [
        {
            "target_slug": "cantina",
            "target_name": "Cantina",
            "label": "Ir a cantina",
            "yaw_degrees": 90,
        }
    ]
    assert received == [["rascunho", "cantina"]]


def test_public_detail_returns_503_when_connection_lookup_fails(client, monkeypatch) -> None:
    connections = [{"target_slug": "cantina", "label": "Cantina", "yaw_degrees": 0}]
    patch_method(monkeypatch, "find_published_by_slug", make_point(connections=connections))
    patch_method(monkeypatch, "find_published_by_slugs", ConnectionError("fora do ar"))

    response = client.get("/public/points/biblioteca-central")

    assert response.status_code == 503

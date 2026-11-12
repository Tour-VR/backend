from __future__ import annotations

from datetime import UTC
from typing import Any

import pytest

from app.repositories.point_repository import PointRepository
from app.repositories.visit_repository import VisitRepository

PUBLISHED_POINT: dict[str, Any] = {"slug": "biblioteca-central", "status": "published"}
VISITS_PATH = "/public/points/biblioteca-central/visits"


def patch_point(monkeypatch: pytest.MonkeyPatch, point: dict[str, Any] | None) -> None:
    async def fake_find(_self: PointRepository, _slug: str) -> dict[str, Any] | None:
        return point

    monkeypatch.setattr(PointRepository, "find_published_by_slug", fake_find)


@pytest.fixture()
def saved_visits(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Repository de visitas falso que guarda os documentos em memoria."""

    saved: list[dict[str, Any]] = []

    async def fake_create(_self: VisitRepository, visit_data: dict[str, Any]) -> None:
        saved.append(visit_data)

    monkeypatch.setattr(VisitRepository, "create_visit", fake_create)
    return saved


def test_record_visit_success_returns_201(client, monkeypatch, saved_visits) -> None:
    patch_point(monkeypatch, PUBLISHED_POINT)

    response = client.post(VISITS_PATH, json={"mode": "ar"})

    assert response.status_code == 201
    assert response.json() == {"recorded": True}
    assert len(saved_visits) == 1
    visit = saved_visits[0]
    assert visit["point_slug"] == "biblioteca-central"
    assert visit["mode"] == "ar"
    assert visit["visited_at"].tzinfo is UTC


def test_record_visit_vr_mode(client, monkeypatch, saved_visits) -> None:
    patch_point(monkeypatch, PUBLISHED_POINT)

    response = client.post(VISITS_PATH, json={"mode": "vr"})

    assert response.status_code == 201
    assert saved_visits[0]["mode"] == "vr"


def test_record_visit_invalid_mode_returns_422(client, monkeypatch, saved_visits) -> None:
    patch_point(monkeypatch, PUBLISHED_POINT)

    response = client.post(VISITS_PATH, json={"mode": "web"})

    assert response.status_code == 422
    assert saved_visits == []


def test_record_visit_unpublished_point_returns_404(client, monkeypatch, saved_visits) -> None:
    patch_point(monkeypatch, None)

    response = client.post("/public/points/rascunho/visits", json={"mode": "ar"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Ponto de interesse nao encontrado."}
    assert saved_visits == []


def test_record_visit_returns_503_when_database_fails(client, monkeypatch) -> None:
    patch_point(monkeypatch, PUBLISHED_POINT)

    async def failing_create(_self: VisitRepository, _visit_data: dict[str, Any]) -> None:
        raise ConnectionError("fora do ar")

    monkeypatch.setattr(VisitRepository, "create_visit", failing_create)

    response = client.post(VISITS_PATH, json={"mode": "ar"})

    assert response.status_code == 503


def test_visit_document_has_no_personal_data(client, monkeypatch, saved_visits) -> None:
    patch_point(monkeypatch, PUBLISHED_POINT)

    client.post(
        VISITS_PATH,
        json={"mode": "ar"},
        headers={"User-Agent": "Navegador de teste", "X-Forwarded-For": "10.0.0.1"},
    )

    assert set(saved_visits[0]) == {"point_slug", "mode", "visited_at"}

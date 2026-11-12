from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from app.core.security import create_access_token
from app.repositories.point_repository import PointRepository
from app.repositories.user_repository import UserRepository
from app.repositories.visit_repository import VisitRepository

OVERVIEW_PATH = "/admin/metrics/overview"


def patch_repositories(monkeypatch: pytest.MonkeyPatch) -> None:
    async def count_points(_self: PointRepository, status: str | None = None) -> int:
        return 2 if status == "published" else 3

    async def find_names(_self: PointRepository, slugs: list[str]) -> dict[str, str]:
        names = {"biblioteca-central": "Biblioteca Central", "cantina": "Cantina"}
        return {slug: names[slug] for slug in slugs if slug in names}

    async def count_all(_self: VisitRepository) -> int:
        return 10

    async def count_since(_self: VisitRepository, _since: datetime) -> int:
        return 4

    async def count_by_mode(_self: VisitRepository) -> dict[str, int]:
        return {"ar": 7, "vr": 3}

    async def top_slugs(_self: VisitRepository, _limit: int) -> list[tuple[str, int]]:
        return [("cantina", 6), ("biblioteca-central", 4)]

    monkeypatch.setattr(PointRepository, "count_points", count_points)
    monkeypatch.setattr(PointRepository, "find_names_by_slugs", find_names)
    monkeypatch.setattr(VisitRepository, "count_all", count_all)
    monkeypatch.setattr(VisitRepository, "count_since", count_since)
    monkeypatch.setattr(VisitRepository, "count_by_mode", count_by_mode)
    monkeypatch.setattr(VisitRepository, "top_point_slugs", top_slugs)


def test_metrics_overview_success(client, as_admin, monkeypatch) -> None:
    patch_repositories(monkeypatch)

    response = client.get(OVERVIEW_PATH)

    assert response.status_code == 200
    assert response.json() == {
        "points_total": 3,
        "points_published": 2,
        "visits_total": 10,
        "visits_last_7_days": 4,
        "visits_by_mode": {"ar": 7, "vr": 3},
        "top_points": [
            {"slug": "cantina", "name": "Cantina", "visits": 6},
            {"slug": "biblioteca-central", "name": "Biblioteca Central", "visits": 4},
        ],
    }


def test_metrics_overview_requires_admin(client, monkeypatch) -> None:
    without_token = client.get(OVERVIEW_PATH)

    async def fake_find_by_email(_self: UserRepository, email: str) -> dict[str, Any]:
        return {"email": email, "role": "user", "is_active": True}

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)
    token = create_access_token("me@example.com", extra_claims={"role": "user"})
    with_user_role = client.get(OVERVIEW_PATH, headers={"Authorization": f"Bearer {token}"})

    assert without_token.status_code == 401
    assert with_user_role.status_code == 403


def test_metrics_overview_returns_503_when_database_fails(client, as_admin, monkeypatch) -> None:
    async def failing_count(_self: PointRepository, _status: str | None = None) -> int:
        raise ConnectionError("fora do ar")

    monkeypatch.setattr(PointRepository, "count_points", failing_count)

    response = client.get(OVERVIEW_PATH)

    assert response.status_code == 503

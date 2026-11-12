from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.metrics_service import MetricsService

NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


class FakePointRepository:
    def __init__(self, names: dict[str, str] | None = None) -> None:
        self.names = names or {}

    async def count_points(self, _status: str | None = None) -> int:
        return len(self.names)

    async def find_names_by_slugs(self, slugs: list[str]) -> dict[str, str]:
        return {slug: self.names[slug] for slug in slugs if slug in self.names}


class FakeVisitRepository:
    def __init__(self, ranking: list[tuple[str, int]] | None = None) -> None:
        self.ranking = ranking or []
        self.since: datetime | None = None
        self.limit: int | None = None

    async def count_all(self) -> int:
        return sum(total for _, total in self.ranking)

    async def count_since(self, since: datetime) -> int:
        self.since = since
        return 0

    async def count_by_mode(self) -> dict[str, int]:
        return {"ar": 0, "vr": 0}

    async def top_point_slugs(self, limit: int) -> list[tuple[str, int]]:
        self.limit = limit
        return self.ranking


def build_service(points: FakePointRepository, visits: FakeVisitRepository) -> MetricsService:
    fake_points: Any = points
    fake_visits: Any = visits
    return MetricsService(fake_points, fake_visits)


def test_overview_uses_seven_day_window() -> None:
    visits = FakeVisitRepository()

    asyncio.run(build_service(FakePointRepository(), visits).overview(NOW))

    assert visits.since == NOW - timedelta(days=7)
    assert visits.limit == 5


def test_overview_skips_deleted_points_in_ranking() -> None:
    points = FakePointRepository({"cantina": "Cantina", "auditorio": "Auditorio"})
    visits = FakeVisitRepository([("cantina", 9), ("excluido", 5), ("auditorio", 2)])

    result = asyncio.run(build_service(points, visits).overview(NOW))

    assert result["top_points"] == [
        {"slug": "cantina", "name": "Cantina", "visits": 9},
        {"slug": "auditorio", "name": "Auditorio", "visits": 2},
    ]


def test_overview_empty_database() -> None:
    result = asyncio.run(build_service(FakePointRepository(), FakeVisitRepository()).overview(NOW))

    assert result == {
        "points_total": 0,
        "points_published": 0,
        "visits_total": 0,
        "visits_last_7_days": 0,
        "visits_by_mode": {"ar": 0, "vr": 0},
        "top_points": [],
    }

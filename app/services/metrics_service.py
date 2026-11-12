"""Resumo administrativo com contagens reais de pontos e visitas."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.models.point import POINT_STATUS_PUBLISHED
from app.repositories.point_repository import PointRepository
from app.repositories.visit_repository import VisitRepository

METRICS_RECENT_DAYS = 7
TOP_POINTS_LIMIT = 5


class MetricsService:
    def __init__(
        self,
        point_repository: PointRepository,
        visit_repository: VisitRepository,
    ) -> None:
        self.point_repository = point_repository
        self.visit_repository = visit_repository

    async def _top_points(self) -> list[dict[str, Any]]:
        """Ranking dos mais visitados; pontos excluidos (sem nome) ficam de fora."""

        ranking = await self.visit_repository.top_point_slugs(TOP_POINTS_LIMIT)
        names = await self.point_repository.find_names_by_slugs([slug for slug, _ in ranking])
        return [
            {"slug": slug, "name": names[slug], "visits": visits}
            for slug, visits in ranking
            if slug in names
        ]

    async def overview(self, now: datetime) -> dict[str, Any]:
        """Monta o resumo no formato de `MetricsOverviewResponse`."""

        since = now - timedelta(days=METRICS_RECENT_DAYS)
        return {
            "points_total": await self.point_repository.count_points(),
            "points_published": await self.point_repository.count_points(POINT_STATUS_PUBLISHED),
            "visits_total": await self.visit_repository.count_all(),
            "visits_last_7_days": await self.visit_repository.count_since(since),
            "visits_by_mode": await self.visit_repository.count_by_mode(),
            "top_points": await self._top_points(),
        }

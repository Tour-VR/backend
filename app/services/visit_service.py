"""Regras de negocio do registro anonimo de visitas."""

from __future__ import annotations

from app.models.visit import VisitModel
from app.repositories.point_repository import PointRepository
from app.repositories.visit_repository import VisitRepository
from app.services.point_service import POINT_NOT_FOUND_MESSAGE, PointNotFoundError


class VisitService:
    def __init__(
        self,
        visit_repository: VisitRepository,
        point_repository: PointRepository,
    ) -> None:
        self.visit_repository = visit_repository
        self.point_repository = point_repository

    async def record_visit(self, slug: str, mode: str) -> dict[str, bool]:
        """Registra a visita anonima a um ponto publicado."""

        point = await self.point_repository.find_published_by_slug(slug)
        if point is None:
            raise PointNotFoundError(POINT_NOT_FOUND_MESSAGE)
        await self.visit_repository.create_visit(VisitModel(point_slug=slug, mode=mode).to_mongo())
        return {"recorded": True}

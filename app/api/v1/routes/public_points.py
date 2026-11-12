"""Rotas publicas de pontos (sem token; so pontos publicados) e registro de visitas."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import build_database_http_exception, get_point_service, get_visit_service
from app.schemas.point import PointPublicDetail, PointPublicSummary
from app.schemas.visit import VisitCreate, VisitRecordedResponse
from app.services.point_service import PointNotFoundError, PointService
from app.services.visit_service import VisitService

router = APIRouter(prefix="/public/points", tags=["Publico"])


@router.get("", response_model=list[PointPublicSummary])
async def list_public_points(
    service: PointService = Depends(get_point_service),
) -> list[dict[str, Any]]:
    try:
        return await service.list_published()
    except ConnectionError as exc:
        raise build_database_http_exception(exc) from exc


@router.get("/{slug}", response_model=PointPublicDetail)
async def get_public_point(
    slug: str,
    service: PointService = Depends(get_point_service),
) -> dict[str, Any]:
    try:
        return await service.get_published(slug)
    except PointNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConnectionError as exc:
        raise build_database_http_exception(exc) from exc


@router.post(
    "/{slug}/visits",
    response_model=VisitRecordedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_visit(
    slug: str,
    payload: VisitCreate,
    service: VisitService = Depends(get_visit_service),
) -> dict[str, bool]:
    """Registra uma visita anonima ao ponto publicado."""

    try:
        return await service.record_visit(slug, payload.mode)
    except PointNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConnectionError as exc:
        raise build_database_http_exception(exc) from exc

"""Rotas administrativas de pontos de interesse (somente papel admin)."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import build_database_http_exception, get_point_service, require_admin
from app.schemas.point import PointAdminResponse, PointCreate, PointUpdate
from app.services.point_service import (
    PointConflictError,
    PointInputError,
    PointNotFoundError,
    PointService,
)

router = APIRouter(
    prefix="/admin/points",
    tags=["Admin - Pontos"],
    dependencies=[Depends(require_admin)],
)

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    PointNotFoundError: status.HTTP_404_NOT_FOUND,
    PointConflictError: status.HTTP_409_CONFLICT,
    PointInputError: status.HTTP_400_BAD_REQUEST,
}

_HANDLED_ERRORS = (PointNotFoundError, PointConflictError, PointInputError, ConnectionError)


def _to_http_error(exc: Exception) -> HTTPException:
    """Traduz as excecoes de dominio e de banco em respostas HTTP."""

    if isinstance(exc, ConnectionError):
        return build_database_http_exception(exc)
    return HTTPException(status_code=_STATUS_BY_ERROR[type(exc)], detail=str(exc))


@router.get("", response_model=list[PointAdminResponse])
async def list_points(
    point_status: Literal["draft", "published"] | None = Query(default=None, alias="status"),
    service: PointService = Depends(get_point_service),
) -> list[dict[str, Any]]:
    try:
        return await service.list_points(point_status)
    except _HANDLED_ERRORS as exc:
        raise _to_http_error(exc) from exc


@router.post("", response_model=PointAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_point(
    payload: PointCreate,
    service: PointService = Depends(get_point_service),
) -> dict[str, Any]:
    try:
        return await service.create_point(payload)
    except _HANDLED_ERRORS as exc:
        raise _to_http_error(exc) from exc


@router.get("/{point_id}", response_model=PointAdminResponse)
async def get_point(
    point_id: str,
    service: PointService = Depends(get_point_service),
) -> dict[str, Any]:
    try:
        return await service.get_point(point_id)
    except _HANDLED_ERRORS as exc:
        raise _to_http_error(exc) from exc


@router.put("/{point_id}", response_model=PointAdminResponse)
async def update_point(
    point_id: str,
    payload: PointUpdate,
    service: PointService = Depends(get_point_service),
) -> dict[str, Any]:
    try:
        return await service.update_point(point_id, payload)
    except _HANDLED_ERRORS as exc:
        raise _to_http_error(exc) from exc


@router.delete("/{point_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_point(
    point_id: str,
    service: PointService = Depends(get_point_service),
) -> Response:
    try:
        await service.delete_point(point_id)
    except _HANDLED_ERRORS as exc:
        raise _to_http_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{point_id}/publish", response_model=PointAdminResponse)
async def publish_point(
    point_id: str,
    service: PointService = Depends(get_point_service),
) -> dict[str, Any]:
    try:
        return await service.publish_point(point_id)
    except _HANDLED_ERRORS as exc:
        raise _to_http_error(exc) from exc


@router.post("/{point_id}/unpublish", response_model=PointAdminResponse)
async def unpublish_point(
    point_id: str,
    service: PointService = Depends(get_point_service),
) -> dict[str, Any]:
    try:
        return await service.unpublish_point(point_id)
    except _HANDLED_ERRORS as exc:
        raise _to_http_error(exc) from exc

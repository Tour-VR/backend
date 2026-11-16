"""Rotas administrativas de gestao de usuarios (somente papel admin)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import build_database_http_exception, get_user_service, require_admin
from app.schemas.user import UserAdminResponse, UserAdminUpdate, UserListResponse
from app.services.user_service import (
    DEFAULT_PAGE_SIZE,
    UserInputError,
    UserNotFoundError,
    UserService,
)

router = APIRouter(prefix="/admin/users", tags=["Admin - Usuarios"])

_HANDLED_ERRORS = (UserInputError, UserNotFoundError, ConnectionError)


def _to_http_error(exc: Exception) -> HTTPException:
    """Traduz as excecoes de dominio e de banco em respostas HTTP."""

    if isinstance(exc, ConnectionError):
        return build_database_http_exception(exc)
    if isinstance(exc, UserNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    _admin: dict[str, Any] = Depends(require_admin),
    service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    """Lista usuarios do mais recente para o mais antigo, paginado."""

    try:
        return await service.list_users(page, page_size)
    except _HANDLED_ERRORS as exc:
        raise _to_http_error(exc) from exc


@router.patch("/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: str,
    payload: UserAdminUpdate,
    current_admin: dict[str, Any] = Depends(require_admin),
    service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    """Ativa, desativa ou muda o papel de um usuario."""

    try:
        return await service.update_user_admin(current_admin, user_id, payload)
    except _HANDLED_ERRORS as exc:
        raise _to_http_error(exc) from exc

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import build_database_http_exception, get_current_user, get_user_service
from app.schemas.user import (
    MessageResponse,
    UserChangePassword,
    UserMeResponse,
    UserUpdateMe,
)
from app.services.user_service import (
    AuthenticationError,
    UserConflictError,
    UserInputError,
    UserNotFoundError,
    UserService,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserMeResponse)
async def read_me(
    current_user: dict[str, Any] = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Devolve apenas os campos publicos do usuario autenticado."""

    return service.serialize_user(current_user)


@router.put("/me", response_model=UserMeResponse)
async def update_me(
    payload: UserUpdateMe,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    try:
        return await service.update_current_user(current_user, payload)
    except (UserConflictError, UserInputError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConnectionError as exc:
        raise build_database_http_exception(exc) from exc


@router.put("/me/password", response_model=MessageResponse)
async def update_my_password(
    payload: UserChangePassword,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    try:
        return await service.change_current_user_password(current_user, payload)
    except (AuthenticationError, UserInputError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConnectionError as exc:
        raise build_database_http_exception(exc) from exc

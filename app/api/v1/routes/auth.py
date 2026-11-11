from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import (
    build_database_http_exception,
    get_login_rate_limiter,
    get_user_service,
    require_admin,
)
from app.core.rate_limit import LoginRateLimiter
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserRegisterResponse
from app.services.user_service import (
    AuthenticationError,
    UserConflictError,
    UserInputError,
    UserService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRegisterResponse)
async def register(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
    _admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """Cria um novo usuario. Exige papel admin."""

    try:
        return await service.register_user(payload)
    except (UserConflictError, UserInputError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ConnectionError as exc:
        raise build_database_http_exception(exc) from exc


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLogin,
    request: Request,
    service: UserService = Depends(get_user_service),
    limiter: LoginRateLimiter = Depends(get_login_rate_limiter),
) -> dict[str, Any]:
    """Valida as credenciais e devolve o token Bearer."""

    # IP e identificador juntos: atras do Docker todos podem chegar com o mesmo IP.
    client_host = request.client.host if request.client else "desconhecido"
    key = f"{client_host}|{payload.email}"
    if limiter.is_blocked(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Tente novamente em alguns minutos.",
        )

    try:
        token = await service.login_user(payload)
    except AuthenticationError as exc:
        limiter.register_failure(key)
        logger.info("Falha de login para o identificador %s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except ConnectionError as exc:
        raise build_database_http_exception(exc) from exc

    limiter.reset(key)
    return token

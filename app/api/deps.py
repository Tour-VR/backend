from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.rate_limit import LoginRateLimiter
from app.core.security import decode_access_token
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def get_user_service(request: Request) -> UserService:
    """Monta o service de usuario usando o banco salvo no estado da app."""

    database = request.app.state.mongo_manager.database
    repository = UserRepository(database)
    return UserService(repository)


def get_login_rate_limiter(request: Request) -> LoginRateLimiter:
    """Recupera o limitador de tentativas de login salvo no estado da app."""

    limiter: LoginRateLimiter = request.app.state.login_rate_limiter
    return limiter


def build_database_http_exception(exc: Exception) -> HTTPException:
    """Padroniza a resposta 503 quando o MongoDB nao estiver disponivel."""

    logger.error("Falha de acesso ao banco: %s", exc)
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Banco de dados indisponivel.",
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    """Valida o token e devolve o usuario atual vindo do banco."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token nao informado.",
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        email = str(payload.get("sub", "")).strip().lower()
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido ou expirado.",
        ) from exc

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido.",
        )

    try:
        user = await service.user_repository.find_by_email(email)
    except ConnectionError as exc:
        raise build_database_http_exception(exc) from exc

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario nao encontrado.",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inativo.",
        )

    return user

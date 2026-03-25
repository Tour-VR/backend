"""Funcoes basicas de seguranca usadas no fluxo de autenticacao."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

PASSWORD_MIN_LENGTH = 8
PASSWORD_RULE_MESSAGE = (
    "A senha deve ter pelo menos 8 caracteres e incluir letra e numero."
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def validate_password_strength(password: str) -> str:
    """Aplica uma regra minima de senha sem acoplar a validacao as rotas."""

    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(PASSWORD_RULE_MESSAGE)

    has_letter = any(character.isalpha() for character in password)
    has_digit = any(character.isdigit() for character in password)

    if not has_letter or not has_digit:
        raise ValueError(PASSWORD_RULE_MESSAGE)

    return password


def hash_password(password: str) -> str:
    """Recebe a senha pura e devolve a senha protegida em hash."""

    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Compara a senha digitada com o hash salvo no banco."""

    return pwd_context.verify(password, hashed_password)


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Cria um JWT usando as configuracoes carregadas do `.env`."""

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica o JWT e devolve os dados do usuario autenticado."""

    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

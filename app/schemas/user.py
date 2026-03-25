"""Schemas Pydantic usados nas rotas de autenticacao e perfil."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.security import validate_password_strength

USERNAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{1,28}[a-z0-9])?$")
USERNAME_RULE_MESSAGE = (
    "Username deve ter entre 3 e 30 caracteres e usar apenas letras, numeros, "
    "ponto, underscore ou hifen."
)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _normalize_username(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None

    normalized = normalized.lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError(USERNAME_RULE_MESSAGE)

    return normalized


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = Field(default=None, max_length=120)
    username: str | None = Field(default=None, max_length=30)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        return _normalize_username(value)


class UserResponse(BaseModel):
    email: EmailStr
    username: str | None = None
    full_name: str | None = None
    role: str = "user"
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserRegisterResponse(UserResponse):
    """Resposta publica devolvida logo apos o cadastro."""


class UserMeResponse(UserResponse):
    """Resposta publica usada pelas rotas protegidas do perfil."""


class UserUpdateMe(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    username: str | None = Field(default=None, max_length=30)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        return _normalize_username(value)


class UserChangePassword(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @model_validator(mode="after")
    def ensure_password_changed(self) -> "UserChangePassword":
        if self.current_password == self.new_password:
            raise ValueError("A nova senha deve ser diferente da senha atual.")
        return self


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    """Resposta padrao do login para o frontend guardar o token."""

    access_token: str
    token_type: str


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Informe um email ou username valido.")
        return normalized

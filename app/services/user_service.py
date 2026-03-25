"""Regras de negocio do fluxo de usuario e autenticacao."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import UserModel
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    UserChangePassword,
    UserCreate,
    UserLogin,
    UserUpdateMe,
)


class UserInputError(ValueError):
    """Erro de validacao de negocio para requests do modulo de usuario."""


class UserConflictError(UserInputError):
    """Erro usado quando email ou username ja estao em uso."""


class AuthenticationError(ValueError):
    """Erro usado para credenciais invalidas ou senha atual incorreta."""


class UserNotFoundError(ValueError):
    """Erro usado quando o usuario nao e encontrado na camada de negocio."""


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def is_ready(self) -> bool:
        return self.user_repository.collection is not None

    def serialize_user(self, user_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "email": user_data["email"],
            "username": user_data.get("username"),
            "full_name": user_data.get("full_name"),
            "role": user_data.get("role", "user"),
            "is_active": user_data.get("is_active", True),
            "is_verified": user_data.get("is_verified", False),
            "created_at": user_data.get("created_at"),
            "updated_at": user_data.get("updated_at"),
        }

    async def register_user(self, payload: UserCreate) -> dict[str, Any]:
        existing_email = await self.user_repository.find_by_email(payload.email)
        if existing_email:
            raise UserConflictError("Ja existe um usuario com este email.")

        if payload.username:
            existing_username = await self.user_repository.find_by_username(
                payload.username
            )
            if existing_username:
                raise UserConflictError("Ja existe um usuario com este username.")

        user = UserModel(
            email=payload.email,
            username=payload.username,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role="user",
            is_active=True,
            is_verified=False,
        )

        user_document = user.to_mongo()
        await self.user_repository.create_user(user_document)
        return self.serialize_user(user_document)

    async def login_user(self, payload: UserLogin) -> dict[str, str]:
        user = await self.user_repository.find_by_email_or_username(payload.email)
        if not user:
            raise AuthenticationError("Credenciais invalidas.")

        if not user.get("is_active", True):
            raise AuthenticationError("Credenciais invalidas.")

        if not verify_password(payload.password, user["hashed_password"]):
            raise AuthenticationError("Credenciais invalidas.")

        token = create_access_token(
            subject=user["email"],
            extra_claims={"role": user.get("role", "user")},
        )

        return {
            "access_token": token,
            "token_type": "bearer",
        }

    async def update_current_user(
        self,
        current_user: dict[str, Any],
        payload: UserUpdateMe,
    ) -> dict[str, Any]:
        payload_data = payload.model_dump(exclude_unset=True)
        update_data: dict[str, Any] = {}

        if "full_name" in payload_data:
            update_data["full_name"] = payload_data["full_name"]

        if "username" in payload_data:
            new_username = payload_data["username"]
            if new_username is not None and new_username != current_user.get("username"):
                existing_username = await self.user_repository.find_by_username(
                    new_username
                )
                if (
                    existing_username is not None
                    and existing_username["email"] != current_user["email"]
                ):
                    raise UserConflictError("Ja existe um usuario com este username.")

            update_data["username"] = new_username

        if not update_data:
            raise UserInputError("Nenhum campo valido para atualizacao.")

        update_data["updated_at"] = datetime.now(timezone.utc)
        updated_user = await self.user_repository.update_user_by_email(
            current_user["email"],
            update_data,
        )

        if not updated_user:
            raise UserNotFoundError("Usuario nao encontrado.")

        return self.serialize_user(updated_user)

    async def change_current_user_password(
        self,
        current_user: dict[str, Any],
        payload: UserChangePassword,
    ) -> dict[str, str]:
        if not verify_password(payload.current_password, current_user["hashed_password"]):
            raise AuthenticationError("Senha atual invalida.")

        updated_user = await self.user_repository.update_user_by_email(
            current_user["email"],
            {
                "hashed_password": hash_password(payload.new_password),
                "updated_at": datetime.now(timezone.utc),
            },
        )

        if not updated_user:
            raise UserNotFoundError("Usuario nao encontrado.")

        return {"message": "Senha atualizada com sucesso."}

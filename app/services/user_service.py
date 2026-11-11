"""Regras de negocio do fluxo de usuario e autenticacao."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.roles import ROLE_ADMIN, ROLE_USER
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import UserModel
from app.repositories.errors import UniqueConstraintError
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


EMAIL_CONFLICT_MESSAGE = "Ja existe um usuario com este email."
USERNAME_CONFLICT_MESSAGE = "Ja existe um usuario com este username."


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
            "role": user_data.get("role", ROLE_USER),
            "is_active": user_data.get("is_active", True),
            "is_verified": user_data.get("is_verified", False),
            "created_at": user_data.get("created_at"),
            "updated_at": user_data.get("updated_at"),
        }

    async def register_user(self, payload: UserCreate) -> dict[str, Any]:
        existing_email = await self.user_repository.find_by_email(payload.email)
        if existing_email:
            raise UserConflictError(EMAIL_CONFLICT_MESSAGE)

        if payload.username:
            existing_username = await self.user_repository.find_by_username(payload.username)
            if existing_username:
                raise UserConflictError(USERNAME_CONFLICT_MESSAGE)

        user_document = self._build_user_document(payload, ROLE_USER)
        await self._insert_user(user_document)
        return self.serialize_user(user_document)

    async def create_or_promote_admin(self, payload: UserCreate) -> tuple[dict[str, Any], bool]:
        """Cria um admin ou promove um usuario existente. Retorna (usuario, criado)."""

        existing_user = await self.user_repository.find_by_email(payload.email)
        if existing_user:
            # A senha do usuario existente e preservada: promover nao redefine credenciais.
            updated_user = await self.user_repository.update_user_by_email(
                payload.email,
                {"role": ROLE_ADMIN, "is_active": True, "updated_at": datetime.now(UTC)},
            )
            if not updated_user:
                raise UserNotFoundError("Usuario nao encontrado.")
            return self.serialize_user(updated_user), False

        user_document = self._build_user_document(payload, ROLE_ADMIN)
        await self._insert_user(user_document)
        return self.serialize_user(user_document), True

    def _build_user_document(self, payload: UserCreate, role: str) -> dict[str, Any]:
        """Monta o documento de um usuario novo com a senha ja convertida em hash."""

        user = UserModel(
            email=payload.email,
            username=payload.username,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role=role,
            is_active=True,
            is_verified=False,
        )
        return user.to_mongo()

    async def _insert_user(self, user_document: dict[str, Any]) -> None:
        """Grava o usuario traduzindo violacao de indice unico em conflito de negocio."""

        try:
            await self.user_repository.create_user(user_document)
        except UniqueConstraintError as exc:
            # O indice unico e a garantia contra cadastros simultaneos.
            message = EMAIL_CONFLICT_MESSAGE if exc.field == "email" else USERNAME_CONFLICT_MESSAGE
            raise UserConflictError(message) from exc

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
            extra_claims={"role": user.get("role", ROLE_USER)},
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
                existing_username = await self.user_repository.find_by_username(new_username)
                if (
                    existing_username is not None
                    and existing_username["email"] != current_user["email"]
                ):
                    raise UserConflictError(USERNAME_CONFLICT_MESSAGE)

            update_data["username"] = new_username

        if not update_data:
            raise UserInputError("Nenhum campo valido para atualizacao.")

        update_data["updated_at"] = datetime.now(UTC)
        try:
            updated_user = await self.user_repository.update_user_by_email(
                current_user["email"],
                update_data,
            )
        except UniqueConstraintError as exc:
            raise UserConflictError(USERNAME_CONFLICT_MESSAGE) from exc

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
                "updated_at": datetime.now(UTC),
            },
        )

        if not updated_user:
            raise UserNotFoundError("Usuario nao encontrado.")

        return {"message": "Senha atualizada com sucesso."}

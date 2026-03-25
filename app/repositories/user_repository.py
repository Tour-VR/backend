"""Repository responsavel por conversar com a collection `users`."""

from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument
from pymongo.errors import PyMongoError


class UserRepository:
    def __init__(self, database: Any | None) -> None:
        self.database = database

    @property
    def collection(self) -> Any | None:
        if self.database is None:
            return None
        return self.database["users"]

    def _require_collection(self) -> Any:
        if self.collection is None:
            raise ConnectionError("A conexao com o MongoDB nao esta disponivel.")
        return self.collection

    async def find_by_email(self, email: str) -> dict[str, Any] | None:
        try:
            return await self._require_collection().find_one({"email": email})
        except PyMongoError as exc:
            raise ConnectionError("Falha ao buscar usuario no MongoDB.") from exc

    async def find_by_username(self, username: str) -> dict[str, Any] | None:
        try:
            return await self._require_collection().find_one({"username": username})
        except PyMongoError as exc:
            raise ConnectionError("Falha ao buscar usuario no MongoDB.") from exc

    async def find_by_email_or_username(
        self,
        identifier: str,
    ) -> dict[str, Any] | None:
        try:
            return await self._require_collection().find_one(
                {
                    "$or": [
                        {"email": identifier},
                        {"username": identifier},
                    ]
                }
            )
        except PyMongoError as exc:
            raise ConnectionError("Falha ao buscar usuario no MongoDB.") from exc

    async def create_user(self, user_data: dict[str, Any]) -> Any:
        try:
            return await self._require_collection().insert_one(user_data)
        except PyMongoError as exc:
            raise ConnectionError("Falha ao criar usuario no MongoDB.") from exc

    async def update_user_by_email(
        self,
        email: str,
        update_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        try:
            return await self._require_collection().find_one_and_update(
                {"email": email},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as exc:
            raise ConnectionError("Falha ao atualizar usuario no MongoDB.") from exc

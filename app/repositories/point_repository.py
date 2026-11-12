"""Repository responsavel por conversar com a collection `points`."""

from __future__ import annotations

from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.models.point import POINT_STATUS_PUBLISHED
from app.repositories.errors import UniqueConstraintError, duplicated_field


def _to_object_id(point_id: str) -> ObjectId | None:
    """Converte o id textual; formato invalido equivale a ponto inexistente."""

    try:
        return ObjectId(point_id)
    except (InvalidId, TypeError):
        return None


class PointRepository:
    def __init__(self, database: Any | None) -> None:
        self.database = database

    @property
    def collection(self) -> Any | None:
        if self.database is None:
            return None
        return self.database["points"]

    def _require_collection(self) -> Any:
        if self.collection is None:
            raise ConnectionError("A conexao com o MongoDB nao esta disponivel.")
        return self.collection

    async def _find_many(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            cursor = self._require_collection().find(query).sort("name", 1)
            points: list[dict[str, Any]] = await cursor.to_list(length=None)
            return points
        except PyMongoError as exc:
            raise ConnectionError("Falha ao listar pontos no MongoDB.") from exc

    async def _find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        try:
            point: dict[str, Any] | None = await self._require_collection().find_one(query)
            return point
        except PyMongoError as exc:
            raise ConnectionError("Falha ao buscar ponto no MongoDB.") from exc

    async def list_points(self, status: str | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {} if status is None else {"status": status}
        return await self._find_many(query)

    async def list_published(self) -> list[dict[str, Any]]:
        return await self._find_many({"status": POINT_STATUS_PUBLISHED})

    async def find_by_id(self, point_id: str) -> dict[str, Any] | None:
        object_id = _to_object_id(point_id)
        if object_id is None:
            return None
        return await self._find_one({"_id": object_id})

    async def find_by_slug(self, slug: str) -> dict[str, Any] | None:
        return await self._find_one({"slug": slug})

    async def find_published_by_slug(self, slug: str) -> dict[str, Any] | None:
        return await self._find_one({"slug": slug, "status": POINT_STATUS_PUBLISHED})

    async def create_point(self, point_data: dict[str, Any]) -> str:
        try:
            result = await self._require_collection().insert_one(point_data)
            return str(result.inserted_id)
        except DuplicateKeyError as exc:
            raise UniqueConstraintError(duplicated_field(exc)) from exc
        except PyMongoError as exc:
            raise ConnectionError("Falha ao criar ponto no MongoDB.") from exc

    async def update_point(
        self,
        point_id: str,
        update_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        object_id = _to_object_id(point_id)
        if object_id is None:
            return None
        try:
            point: dict[str, Any] | None = await self._require_collection().find_one_and_update(
                {"_id": object_id},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER,
            )
            return point
        except DuplicateKeyError as exc:
            raise UniqueConstraintError(duplicated_field(exc)) from exc
        except PyMongoError as exc:
            raise ConnectionError("Falha ao atualizar ponto no MongoDB.") from exc

    async def delete_point(self, point_id: str) -> bool:
        object_id = _to_object_id(point_id)
        if object_id is None:
            return False
        try:
            result = await self._require_collection().delete_one({"_id": object_id})
            return bool(result.deleted_count)
        except PyMongoError as exc:
            raise ConnectionError("Falha ao remover ponto no MongoDB.") from exc

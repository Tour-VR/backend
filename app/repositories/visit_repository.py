"""Repository responsavel por conversar com a collection `visits`."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo.errors import PyMongoError

from app.models.visit import VISIT_MODE_AR, VISIT_MODE_VR


class VisitRepository:
    def __init__(self, database: Any | None) -> None:
        self.database = database

    @property
    def collection(self) -> Any | None:
        if self.database is None:
            return None
        return self.database["visits"]

    def _require_collection(self) -> Any:
        if self.collection is None:
            raise ConnectionError("A conexao com o MongoDB nao esta disponivel.")
        return self.collection

    async def _aggregate(self, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        try:
            cursor = await self._require_collection().aggregate(pipeline)
            results: list[dict[str, Any]] = await cursor.to_list(length=None)
            return results
        except PyMongoError as exc:
            raise ConnectionError("Falha ao agregar visitas no MongoDB.") from exc

    async def _count(self, query: dict[str, Any]) -> int:
        try:
            total: int = await self._require_collection().count_documents(query)
            return total
        except PyMongoError as exc:
            raise ConnectionError("Falha ao contar visitas no MongoDB.") from exc

    async def create_visit(self, visit_data: dict[str, Any]) -> None:
        try:
            await self._require_collection().insert_one(visit_data)
        except PyMongoError as exc:
            raise ConnectionError("Falha ao registrar visita no MongoDB.") from exc

    async def count_all(self) -> int:
        return await self._count({})

    async def count_since(self, since: datetime) -> int:
        return await self._count({"visited_at": {"$gte": since}})

    async def count_by_mode(self) -> dict[str, int]:
        rows = await self._aggregate([{"$group": {"_id": "$mode", "total": {"$sum": 1}}}])
        totals = {VISIT_MODE_AR: 0, VISIT_MODE_VR: 0}
        for row in rows:
            if row["_id"] in totals:
                totals[row["_id"]] = int(row["total"])
        return totals

    async def top_point_slugs(self, limit: int) -> list[tuple[str, int]]:
        rows = await self._aggregate(
            [
                {"$group": {"_id": "$point_slug", "total": {"$sum": 1}}},
                {"$sort": {"total": -1, "_id": 1}},
                {"$limit": limit},
            ]
        )
        return [(str(row["_id"]), int(row["total"])) for row in rows]

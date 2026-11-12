"""Regras de negocio dos pontos de interesse (ADR-0007)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.models.point import (
    MEDIA_KIND_PHOTO,
    POINT_STATUS_DRAFT,
    POINT_STATUS_PUBLISHED,
    PointModel,
)
from app.repositories.errors import UniqueConstraintError
from app.repositories.point_repository import PointRepository
from app.schemas.point import MediaItemInput, PointCreate, PointUpdate


class PointInputError(ValueError):
    """Erro de regra de negocio na entrada de um ponto (HTTP 400)."""


class PointConflictError(ValueError):
    """Erro usado quando o slug ja pertence a outro ponto (HTTP 409)."""


class PointNotFoundError(ValueError):
    """Erro usado quando o ponto nao existe ou nao esta visivel (HTTP 404)."""


POINT_NOT_FOUND_MESSAGE = "Ponto de interesse nao encontrado."
POINT_SLUG_CONFLICT_MESSAGE = "Ja existe um ponto com este slug."
POINT_SLUG_LOCKED_MESSAGE = (
    "O slug nao pode mudar depois da primeira publicacao, "
    "pois os QR Codes impressos deixariam de funcionar."
)
POINT_EMPTY_UPDATE_MESSAGE = "Nenhum campo valido para atualizacao."


def _now() -> datetime:
    return datetime.now(UTC)


def _build_media(items: list[MediaItemInput]) -> list[dict[str, Any]]:
    """Converte a midia recebida, gerando `id` para os itens que nao trazem um."""

    return [{**item.model_dump(), "id": item.id or str(uuid4())} for item in items]


def _serialize_media(point: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "kind": item["kind"],
            "url": item["url"],
            "caption": item.get("caption"),
            "alt_text": item["alt_text"],
        }
        for item in point.get("media", [])
    ]


class PointService:
    def __init__(self, point_repository: PointRepository) -> None:
        self.point_repository = point_repository

    @staticmethod
    def serialize_admin(point: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(point["_id"]),
            "slug": point["slug"],
            "name": point["name"],
            "summary": point["summary"],
            "history": point["history"],
            "status": point.get("status", POINT_STATUS_DRAFT),
            "media": _serialize_media(point),
            "created_at": point.get("created_at"),
            "updated_at": point.get("updated_at"),
            "published_at": point.get("published_at"),
        }

    @staticmethod
    def serialize_public_summary(point: dict[str, Any]) -> dict[str, Any]:
        cover_url = next(
            (
                item["url"]
                for item in point.get("media", [])
                if item.get("kind") == MEDIA_KIND_PHOTO
            ),
            None,
        )
        return {
            "slug": point["slug"],
            "name": point["name"],
            "summary": point["summary"],
            "cover_url": cover_url,
        }

    @staticmethod
    def serialize_public_detail(point: dict[str, Any]) -> dict[str, Any]:
        return {
            "slug": point["slug"],
            "name": point["name"],
            "summary": point["summary"],
            "history": point["history"],
            "media": _serialize_media(point),
        }

    async def _load(self, point_id: str) -> dict[str, Any]:
        point = await self.point_repository.find_by_id(point_id)
        if point is None:
            raise PointNotFoundError(POINT_NOT_FOUND_MESSAGE)
        return point

    async def _save(self, point_id: str, update_data: dict[str, Any]) -> dict[str, Any]:
        try:
            updated = await self.point_repository.update_point(point_id, update_data)
        except UniqueConstraintError as exc:
            raise PointConflictError(POINT_SLUG_CONFLICT_MESSAGE) from exc
        if updated is None:
            raise PointNotFoundError(POINT_NOT_FOUND_MESSAGE)
        return self.serialize_admin(updated)

    async def list_points(self, status: str | None = None) -> list[dict[str, Any]]:
        points = await self.point_repository.list_points(status)
        return [self.serialize_admin(point) for point in points]

    async def get_point(self, point_id: str) -> dict[str, Any]:
        return self.serialize_admin(await self._load(point_id))

    async def create_point(self, payload: PointCreate) -> dict[str, Any]:
        if await self.point_repository.find_by_slug(payload.slug):
            raise PointConflictError(POINT_SLUG_CONFLICT_MESSAGE)

        document = PointModel(
            slug=payload.slug,
            name=payload.name,
            summary=payload.summary,
            history=payload.history,
            media=_build_media(payload.media),
        ).to_mongo()
        try:
            point_id = await self.point_repository.create_point(document)
        except UniqueConstraintError as exc:
            raise PointConflictError(POINT_SLUG_CONFLICT_MESSAGE) from exc
        return self.serialize_admin({**document, "_id": point_id})

    async def update_point(self, point_id: str, payload: PointUpdate) -> dict[str, Any]:
        point = await self._load(point_id)

        update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not update_data:
            raise PointInputError(POINT_EMPTY_UPDATE_MESSAGE)
        if payload.media is not None:
            update_data["media"] = _build_media(payload.media)

        new_slug = update_data.get("slug")
        if new_slug is not None and new_slug != point["slug"]:
            await self._check_slug_change(point, new_slug)

        update_data["updated_at"] = _now()
        return await self._save(point_id, update_data)

    async def _check_slug_change(self, point: dict[str, Any], new_slug: str) -> None:
        if point.get("published_at") is not None:
            raise PointInputError(POINT_SLUG_LOCKED_MESSAGE)
        owner = await self.point_repository.find_by_slug(new_slug)
        if owner is not None and owner.get("_id") != point.get("_id"):
            raise PointConflictError(POINT_SLUG_CONFLICT_MESSAGE)

    async def delete_point(self, point_id: str) -> None:
        if not await self.point_repository.delete_point(point_id):
            raise PointNotFoundError(POINT_NOT_FOUND_MESSAGE)

    async def publish_point(self, point_id: str) -> dict[str, Any]:
        point = await self._load(point_id)
        now = _now()
        update_data: dict[str, Any] = {"status": POINT_STATUS_PUBLISHED, "updated_at": now}
        if point.get("published_at") is None:
            update_data["published_at"] = now
        return await self._save(point_id, update_data)

    async def unpublish_point(self, point_id: str) -> dict[str, Any]:
        await self._load(point_id)
        return await self._save(point_id, {"status": POINT_STATUS_DRAFT, "updated_at": _now()})

    async def list_published(self) -> list[dict[str, Any]]:
        points = await self.point_repository.list_published()
        return [self.serialize_public_summary(point) for point in points]

    async def get_published(self, slug: str) -> dict[str, Any]:
        point = await self.point_repository.find_published_by_slug(slug)
        if point is None:
            raise PointNotFoundError(POINT_NOT_FOUND_MESSAGE)
        return self.serialize_public_detail(point)

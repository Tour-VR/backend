"""Regras de negocio dos pontos de interesse (ADR-0007)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.models.point import (
    MEDIA_KIND_PANORAMA,
    MEDIA_KIND_PHOTO,
    POINT_STATUS_DRAFT,
    POINT_STATUS_PUBLISHED,
    PointModel,
)
from app.repositories.errors import UniqueConstraintError
from app.repositories.point_repository import PointRepository
from app.schemas.point import (
    MAX_PANORAMAS,
    MediaItemInput,
    PointConnectionSchema,
    PointCreate,
    PointUpdate,
)


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
PANORAMA_LIMIT_MESSAGE = "O ponto pode ter apenas um panorama."
CONNECTION_SELF_MESSAGE = "Um ponto nao pode se conectar a si mesmo."
CONNECTION_REPEATED_MESSAGE = "Conexao repetida para o mesmo ponto."
CONNECTION_TARGET_NOT_FOUND_MESSAGE = "Ponto de destino nao encontrado: {slug}."


def _now() -> datetime:
    return datetime.now(UTC)


def _build_media(items: list[MediaItemInput]) -> list[dict[str, Any]]:
    """Converte a midia recebida, gerando `id` para os itens que nao trazem um."""

    return [{**item.model_dump(), "id": item.id or str(uuid4())} for item in items]


def _build_connections(items: list[PointConnectionSchema]) -> list[dict[str, Any]]:
    return [item.model_dump() for item in items]


def _serialize_connections(point: dict[str, Any]) -> list[dict[str, Any]]:
    """Documentos antigos nao tem `connections`: lidos como lista vazia."""

    return [
        {
            "target_slug": item["target_slug"],
            "label": item["label"],
            "yaw_degrees": item["yaw_degrees"],
        }
        for item in point.get("connections", [])
    ]


def _first_url(point: dict[str, Any], kind: str) -> str | None:
    return next(
        (str(item["url"]) for item in point.get("media", []) if item.get("kind") == kind),
        None,
    )


def _check_connection_shape(point_slug: str, connections: list[PointConnectionSchema]) -> None:
    seen: set[str] = set()
    for connection in connections:
        if connection.target_slug == point_slug:
            raise PointInputError(CONNECTION_SELF_MESSAGE)
        if connection.target_slug in seen:
            raise PointInputError(CONNECTION_REPEATED_MESSAGE)
        seen.add(connection.target_slug)


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
            "connections": _serialize_connections(point),
            "created_at": point.get("created_at"),
            "updated_at": point.get("updated_at"),
            "published_at": point.get("published_at"),
        }

    @staticmethod
    def serialize_public_summary(point: dict[str, Any]) -> dict[str, Any]:
        return {
            "slug": point["slug"],
            "name": point["name"],
            "summary": point["summary"],
            "cover_url": _first_url(point, MEDIA_KIND_PHOTO),
            "has_panorama": _first_url(point, MEDIA_KIND_PANORAMA) is not None,
        }

    @staticmethod
    def serialize_public_detail(
        point: dict[str, Any], published_names: dict[str, str]
    ) -> dict[str, Any]:
        """`published_names` = `{slug: name}` dos alvos publicados; os demais sao omitidos."""

        connections = [
            {**connection, "target_name": published_names[connection["target_slug"]]}
            for connection in _serialize_connections(point)
            if connection["target_slug"] in published_names
        ]
        return {
            "slug": point["slug"],
            "name": point["name"],
            "summary": point["summary"],
            "history": point["history"],
            "media": _serialize_media(point),
            "panorama_url": _first_url(point, MEDIA_KIND_PANORAMA),
            "connections": connections,
        }

    async def _validate_vr_fields(
        self,
        point_slug: str,
        media: list[MediaItemInput] | None,
        connections: list[PointConnectionSchema] | None,
    ) -> None:
        """Regras do modo VR (plano 019); levanta `PointInputError`."""

        if media is not None:
            panoramas = [item for item in media if item.kind == MEDIA_KIND_PANORAMA]
            if len(panoramas) > MAX_PANORAMAS:
                raise PointInputError(PANORAMA_LIMIT_MESSAGE)
        if not connections:
            return
        _check_connection_shape(point_slug, connections)
        targets = [connection.target_slug for connection in connections]
        existing = await self.point_repository.find_slugs_in(targets)
        missing = next((slug for slug in targets if slug not in existing), None)
        if missing is not None:
            raise PointInputError(CONNECTION_TARGET_NOT_FOUND_MESSAGE.format(slug=missing))

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
        await self._validate_vr_fields(payload.slug, payload.media, payload.connections)

        document = PointModel(
            slug=payload.slug,
            name=payload.name,
            summary=payload.summary,
            history=payload.history,
            media=_build_media(payload.media),
        ).to_mongo()
        document["connections"] = _build_connections(payload.connections)
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
        if payload.connections is not None:
            update_data["connections"] = _build_connections(payload.connections)

        old_slug = str(point["slug"])
        new_slug = str(update_data.get("slug", old_slug))
        if new_slug != old_slug:
            await self._check_slug_change(point, new_slug)
        await self._validate_vr_fields(new_slug, payload.media, payload.connections)

        update_data["updated_at"] = _now()
        saved = await self._save(point_id, update_data)
        if new_slug != old_slug:
            await self.point_repository.rename_connection_target(old_slug, new_slug)
        return saved

    async def _check_slug_change(self, point: dict[str, Any], new_slug: str) -> None:
        if point.get("published_at") is not None:
            raise PointInputError(POINT_SLUG_LOCKED_MESSAGE)
        owner = await self.point_repository.find_by_slug(new_slug)
        if owner is not None and owner.get("_id") != point.get("_id"):
            raise PointConflictError(POINT_SLUG_CONFLICT_MESSAGE)

    async def delete_point(self, point_id: str) -> None:
        """Exclui o ponto e remove as setas que apontavam para ele."""

        point = await self._load(point_id)
        if not await self.point_repository.delete_point(point_id):
            raise PointNotFoundError(POINT_NOT_FOUND_MESSAGE)
        await self.point_repository.remove_connections_to(str(point["slug"]))

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
        targets = [item["target_slug"] for item in _serialize_connections(point)]
        published = await self.point_repository.find_published_by_slugs(targets)
        names = {str(item["slug"]): str(item["name"]) for item in published}
        return self.serialize_public_detail(point, names)

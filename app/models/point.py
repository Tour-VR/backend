"""Modelo interno de ponto de interesse usado por services e repositories."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

POINT_STATUS_DRAFT = "draft"
POINT_STATUS_PUBLISHED = "published"
MEDIA_KIND_PHOTO = "photo"


@dataclass(slots=True)
class PointModel:
    """Documento da collection `points`.

    Cada item de `media` tem o formato
    `{"id": str, "kind": "photo", "url": str, "caption": str | None, "alt_text": str}`.
    """

    slug: str
    name: str
    summary: str
    history: str
    status: str = POINT_STATUS_DRAFT
    media: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    published_at: datetime | None = None

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)

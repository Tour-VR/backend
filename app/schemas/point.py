"""Schemas Pydantic das rotas de pontos de interesse.

Limites do contrato (fonte unica, espelhados pelo painel no plano 012):

- SLUG_PATTERN: letras minusculas e numeros, palavras separadas por um hifen.
- SLUG_MIN_LENGTH / SLUG_MAX_LENGTH: tamanho do slug (vai no QR Code).
- NAME_MIN_LENGTH / NAME_MAX_LENGTH: tamanho do nome do ponto.
- SUMMARY_MAX_LENGTH: resumo curto exibido nas listas.
- HISTORY_MAX_LENGTH: texto longo com a historia do lugar.
- MEDIA_MAX_ITEMS: quantidade maxima de midias embutidas no ponto.
- MEDIA_URL_MAX_LENGTH, CAPTION_MAX_LENGTH, ALT_TEXT_MAX_LENGTH: limites de cada midia.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_MIN_LENGTH, SLUG_MAX_LENGTH = 3, 60
NAME_MIN_LENGTH, NAME_MAX_LENGTH = 3, 120
SUMMARY_MAX_LENGTH = 280
HISTORY_MAX_LENGTH = 10_000
MEDIA_MAX_ITEMS = 20
MEDIA_URL_MAX_LENGTH = 500
CAPTION_MAX_LENGTH = 200
ALT_TEXT_MAX_LENGTH = 200
SLUG_RULE_MESSAGE = (
    "Slug deve ter de 3 a 60 caracteres, apenas letras minusculas, numeros e hifens "
    "entre palavras (ex.: biblioteca-central)."
)

PointStatus = Literal["draft", "published"]


def _strip(value: object) -> object:
    """Remove espacos das pontas; outros tipos seguem para a validacao do Pydantic."""

    if isinstance(value, str):
        return value.strip()
    return value


def _normalize_slug(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip().lower()
    if not (
        SLUG_MIN_LENGTH <= len(normalized) <= SLUG_MAX_LENGTH and SLUG_PATTERN.fullmatch(normalized)
    ):
        raise ValueError(SLUG_RULE_MESSAGE)
    return normalized


class MediaItemInput(BaseModel):
    id: str | None = None
    kind: Literal["photo"] = "photo"
    url: str = Field(min_length=1, max_length=MEDIA_URL_MAX_LENGTH)
    caption: str | None = Field(default=None, max_length=CAPTION_MAX_LENGTH)
    alt_text: str = Field(min_length=1, max_length=ALT_TEXT_MAX_LENGTH)

    @field_validator("url", "caption", "alt_text", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip(value)


class MediaItemResponse(BaseModel):
    id: str
    kind: str
    url: str
    caption: str | None = None
    alt_text: str


class PointCreate(BaseModel):
    slug: str
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    summary: str = Field(min_length=1, max_length=SUMMARY_MAX_LENGTH)
    history: str = Field(min_length=1, max_length=HISTORY_MAX_LENGTH)
    media: list[MediaItemInput] = Field(default_factory=list, max_length=MEDIA_MAX_ITEMS)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        return str(_normalize_slug(value))

    @field_validator("name", "summary", "history", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip(value)


class PointUpdate(BaseModel):
    """Atualizacao parcial: campo ausente ou `None` nao e alterado."""

    slug: str | None = None
    name: str | None = Field(default=None, min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    summary: str | None = Field(default=None, min_length=1, max_length=SUMMARY_MAX_LENGTH)
    history: str | None = Field(default=None, min_length=1, max_length=HISTORY_MAX_LENGTH)
    media: list[MediaItemInput] | None = Field(default=None, max_length=MEDIA_MAX_ITEMS)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        return _normalize_slug(value)

    @field_validator("name", "summary", "history", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip(value)


class PointAdminResponse(BaseModel):
    id: str
    slug: str
    name: str
    summary: str
    history: str
    status: PointStatus
    media: list[MediaItemResponse]
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None


class PointPublicSummary(BaseModel):
    slug: str
    name: str
    summary: str
    cover_url: str | None = None


class PointPublicDetail(BaseModel):
    slug: str
    name: str
    summary: str
    history: str
    media: list[MediaItemResponse]

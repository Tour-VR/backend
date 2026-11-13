"""Schemas Pydantic do envio de midia."""

from __future__ import annotations

from pydantic import BaseModel


class MediaUploadResponse(BaseModel):
    url: str
    content_type: str
    size_bytes: int

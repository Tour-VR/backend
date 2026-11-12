"""Schemas Pydantic do registro de visitas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class VisitCreate(BaseModel):
    mode: Literal["ar", "vr"]


class VisitRecordedResponse(BaseModel):
    recorded: bool

"""Schemas Pydantic do resumo administrativo de metricas."""

from __future__ import annotations

from pydantic import BaseModel


class VisitsByMode(BaseModel):
    ar: int
    vr: int


class TopPoint(BaseModel):
    slug: str
    name: str
    visits: int


class MetricsOverviewResponse(BaseModel):
    points_total: int
    points_published: int
    visits_total: int
    visits_last_7_days: int
    visits_by_mode: VisitsByMode
    top_points: list[TopPoint]

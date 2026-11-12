"""Rotas administrativas de metricas (somente papel admin)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import build_database_http_exception, get_metrics_service, require_admin
from app.schemas.metrics import MetricsOverviewResponse
from app.services.metrics_service import MetricsService

router = APIRouter(
    prefix="/admin/metrics",
    tags=["Admin - Metricas"],
    dependencies=[Depends(require_admin)],
)


@router.get("/overview", response_model=MetricsOverviewResponse)
async def metrics_overview(
    service: MetricsService = Depends(get_metrics_service),
) -> dict[str, Any]:
    """Resumo com contagens reais de pontos e visitas."""

    try:
        return await service.overview(datetime.now(UTC))
    except ConnectionError as exc:
        raise build_database_http_exception(exc) from exc

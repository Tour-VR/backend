"""Modelo interno de visita anonima a um ponto de interesse."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

VISIT_MODE_AR = "ar"
VISIT_MODE_VR = "vr"


@dataclass(slots=True)
class VisitModel:
    """Documento da collection `visits`.

    Guarda apenas o ponto, o modo e o instante: nada de IP nem navegador (privacidade).
    """

    point_slug: str
    mode: str
    visited_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_mongo(self) -> dict[str, Any]:
        return asdict(self)

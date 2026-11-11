"""Erros da camada de repository, independentes de HTTP e de dominio."""

from __future__ import annotations

from pymongo.errors import DuplicateKeyError


class UniqueConstraintError(ValueError):
    """Violacao de indice unico no MongoDB."""

    def __init__(self, field: str) -> None:
        super().__init__(f"Valor duplicado no campo {field}.")
        self.field = field


def duplicated_field(exc: DuplicateKeyError) -> str:
    """Extrai o nome do campo do erro do MongoDB (keyPattern)."""

    details = exc.details or {}
    key_pattern = details.get("keyPattern") or {}
    return next(iter(key_pattern), "desconhecido")

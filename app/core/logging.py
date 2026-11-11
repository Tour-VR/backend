"""Configuracao do logging padrao da aplicacao."""

from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """Configura o logging padrao da aplicacao (texto, uma linha por evento)."""

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

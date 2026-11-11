"""Fixtures compartilhadas para os testes."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.main as app_main
from app.core.database import MongoManager
from main import app


@pytest.fixture(autouse=True)
def fake_ensure_indexes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Evita que o lifespan tente criar indices num MongoDB real."""

    async def noop(_database: Any) -> None:
        return None

    monkeypatch.setattr(app_main, "ensure_indexes", noop)


@pytest.fixture(autouse=True)
def clear_login_rate_limiter() -> None:
    """Cada teste comeca sem falhas de login registradas."""

    app.state.login_rate_limiter.clear()


@pytest.fixture()
def mongo_up(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simula MongoDB conectado."""

    async def fake_ping(self: MongoManager) -> bool:
        self.connected = True
        self.last_error = None
        return True

    monkeypatch.setattr(MongoManager, "_has_placeholder_credentials", lambda _self: False)
    monkeypatch.setattr(MongoManager, "ping", fake_ping)


@pytest.fixture()
def mongo_down(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simula MongoDB desconectado."""

    async def fake_ping(self: MongoManager) -> bool:
        self.connected = False
        self.last_error = "MongoDB indisponivel para teste."
        return False

    monkeypatch.setattr(MongoManager, "_has_placeholder_credentials", lambda _self: False)
    monkeypatch.setattr(MongoManager, "ping", fake_ping)


@pytest.fixture()
def client(mongo_up: None) -> TestClient:
    """TestClient com MongoDB simulado como conectado."""

    with TestClient(app) as c:
        yield c

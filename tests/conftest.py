"""Fixtures compartilhadas para os testes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.database import MongoManager
from main import app


@pytest.fixture()
def mongo_up(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simula MongoDB conectado."""

    async def fake_ping(self: MongoManager) -> bool:
        self.connected = True
        self.last_error = None
        return True

    monkeypatch.setattr(MongoManager, "_has_placeholder_credentials", lambda self: False)
    monkeypatch.setattr(MongoManager, "ping", fake_ping)


@pytest.fixture()
def mongo_down(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simula MongoDB desconectado."""

    async def fake_ping(self: MongoManager) -> bool:
        self.connected = False
        self.last_error = "MongoDB indisponivel para teste."
        return False

    monkeypatch.setattr(MongoManager, "_has_placeholder_credentials", lambda self: False)
    monkeypatch.setattr(MongoManager, "ping", fake_ping)


@pytest.fixture()
def client(mongo_up: None) -> TestClient:
    """TestClient com MongoDB simulado como conectado."""

    with TestClient(app) as c:
        yield c

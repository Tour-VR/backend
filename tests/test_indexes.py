from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pymongo.errors import PyMongoError

import app.main as app_main
from app.core.indexes import ensure_indexes
from main import app


class FakeCollection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def create_index(self, key: str, **kwargs: Any) -> str:
        self.calls.append((key, kwargs))
        return str(kwargs["name"])


class FakeDatabase:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections.setdefault(name, FakeCollection())


def test_ensure_indexes_creates_user_indexes() -> None:
    database = FakeDatabase()

    asyncio.run(ensure_indexes(database))

    assert database["users"].calls == [
        ("email", {"unique": True, "name": "users_email_unique"}),
        (
            "username",
            {
                "unique": True,
                "name": "users_username_unique",
                "partialFilterExpression": {"username": {"$type": "string"}},
            },
        ),
    ]


def test_ensure_indexes_creates_point_slug_index() -> None:
    database = FakeDatabase()

    asyncio.run(ensure_indexes(database))

    assert database["points"].calls == [
        ("slug", {"unique": True, "name": "points_slug_unique"}),
    ]


def test_lifespan_survives_index_failure(mongo_up: None, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []

    async def failing_ensure_indexes(database: Any) -> None:
        calls.append(database)
        raise PyMongoError("indice duplicado")

    monkeypatch.setattr(app_main, "ensure_indexes", failing_ensure_indexes)

    with TestClient(app) as client:
        response = client.get("/health/")

    assert response.status_code == 200
    assert len(calls) == 1

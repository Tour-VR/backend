from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest
from pymongo.errors import PyMongoError

from app.repositories.visit_repository import VisitRepository


class FakeCursor:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self.documents = documents

    async def to_list(self, length: int | None) -> list[dict[str, Any]]:
        assert length is None
        return self.documents


class FakeCollection:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or []
        self.pipelines: list[list[dict[str, Any]]] = []
        self.queries: list[dict[str, Any]] = []
        self.inserted: list[dict[str, Any]] = []

    async def aggregate(self, pipeline: list[dict[str, Any]]) -> FakeCursor:
        self.pipelines.append(pipeline)
        return FakeCursor(self.rows)

    async def count_documents(self, query: dict[str, Any]) -> int:
        self.queries.append(query)
        return 7

    async def insert_one(self, document: dict[str, Any]) -> None:
        self.inserted.append(document)


class FailingCollection:
    async def aggregate(self, _pipeline: list[dict[str, Any]]) -> Any:
        raise PyMongoError("falhou")

    async def count_documents(self, _query: dict[str, Any]) -> int:
        raise PyMongoError("falhou")

    async def insert_one(self, _document: dict[str, Any]) -> None:
        raise PyMongoError("falhou")


def repository_with(collection: Any) -> VisitRepository:
    return VisitRepository({"visits": collection})


def test_count_by_mode_fills_missing_modes() -> None:
    collection = FakeCollection([{"_id": "ar", "total": 3}])

    result = asyncio.run(repository_with(collection).count_by_mode())

    assert result == {"ar": 3, "vr": 0}
    assert collection.pipelines == [[{"$group": {"_id": "$mode", "total": {"$sum": 1}}}]]


def test_top_point_slugs_uses_ranking_pipeline() -> None:
    collection = FakeCollection([{"_id": "cantina", "total": 4}, {"_id": "biblioteca", "total": 2}])

    result = asyncio.run(repository_with(collection).top_point_slugs(5))

    assert result == [("cantina", 4), ("biblioteca", 2)]
    assert collection.pipelines == [
        [
            {"$group": {"_id": "$point_slug", "total": {"$sum": 1}}},
            {"$sort": {"total": -1, "_id": 1}},
            {"$limit": 5},
        ]
    ]


def test_counts_and_insert_use_expected_queries() -> None:
    collection = FakeCollection()
    repository = repository_with(collection)
    since = datetime(2026, 11, 4, tzinfo=UTC)

    assert asyncio.run(repository.count_all()) == 7
    assert asyncio.run(repository.count_since(since)) == 7
    asyncio.run(repository.create_visit({"point_slug": "a", "mode": "ar"}))

    assert collection.queries == [{}, {"visited_at": {"$gte": since}}]
    assert collection.inserted == [{"point_slug": "a", "mode": "ar"}]


@pytest.mark.parametrize(
    "call",
    [
        lambda r: r.create_visit({"point_slug": "a"}),
        lambda r: r.count_all(),
        lambda r: r.count_by_mode(),
        lambda r: r.top_point_slugs(5),
    ],
)
def test_mongo_errors_become_connection_error(call: Any) -> None:
    repository = repository_with(FailingCollection())

    with pytest.raises(ConnectionError):
        asyncio.run(call(repository))


def test_missing_database_raises_connection_error() -> None:
    with pytest.raises(ConnectionError):
        asyncio.run(VisitRepository(None).count_all())

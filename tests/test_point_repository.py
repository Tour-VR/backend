from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.repositories.errors import UniqueConstraintError
from app.repositories.point_repository import PointRepository


class ExplodingCollection:
    """Collection falsa que falha se qualquer metodo for chamado."""

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"A collection nao deveria ser usada ({name}).")


class FakeCursor:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self.documents = documents
        self.sort_args: tuple[str, int] | None = None

    def sort(self, key: str, direction: int) -> FakeCursor:
        self.sort_args = (key, direction)
        return self

    async def to_list(self, length: int | None) -> list[dict[str, Any]]:
        assert length is None
        return self.documents


class FakeCollection:
    def __init__(self) -> None:
        self.queries: list[dict[str, Any]] = []
        self.cursor = FakeCursor([{"slug": "a"}])

    def find(self, query: dict[str, Any]) -> FakeCursor:
        self.queries.append(query)
        return self.cursor

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any]:
        self.queries.append(query)
        return {"slug": "a"}

    async def insert_one(self, _document: dict[str, Any]) -> SimpleNamespace:
        return SimpleNamespace(inserted_id=ObjectId("0123456789ab0123456789ab"))

    async def find_one_and_update(self, query: dict[str, Any], *_args: Any, **_kw: Any) -> Any:
        self.queries.append(query)
        return {"slug": "b"}

    async def delete_one(self, query: dict[str, Any]) -> SimpleNamespace:
        self.queries.append(query)
        return SimpleNamespace(deleted_count=1)


class FailingCollection:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def find(self, _query: dict[str, Any]) -> Any:
        raise self.error

    async def find_one(self, _query: dict[str, Any]) -> Any:
        raise self.error

    async def insert_one(self, _document: dict[str, Any]) -> Any:
        raise self.error

    async def find_one_and_update(self, *_args: Any, **_kwargs: Any) -> Any:
        raise self.error

    async def delete_one(self, _query: dict[str, Any]) -> Any:
        raise self.error


def repository_with(collection: Any) -> PointRepository:
    return PointRepository({"points": collection})


def test_invalid_object_id_does_not_touch_collection() -> None:
    repository = repository_with(ExplodingCollection())

    assert asyncio.run(repository.find_by_id("nao-e-objectid")) is None
    assert asyncio.run(repository.update_point("nao-e-objectid", {"name": "x"})) is None
    assert asyncio.run(repository.delete_point("nao-e-objectid")) is False


def test_queries_use_expected_filters_and_order() -> None:
    collection = FakeCollection()
    repository = repository_with(collection)
    point_id = "0123456789ab0123456789ab"

    asyncio.run(repository.list_points())
    asyncio.run(repository.list_points("draft"))
    asyncio.run(repository.list_published())
    asyncio.run(repository.find_by_slug("a"))
    asyncio.run(repository.find_published_by_slug("a"))
    asyncio.run(repository.find_by_id(point_id))

    assert collection.queries == [
        {},
        {"status": "draft"},
        {"status": "published"},
        {"slug": "a"},
        {"slug": "a", "status": "published"},
        {"_id": ObjectId(point_id)},
    ]
    assert collection.cursor.sort_args == ("name", 1)


def test_write_operations_return_expected_values() -> None:
    repository = repository_with(FakeCollection())
    point_id = "0123456789ab0123456789ab"

    assert asyncio.run(repository.create_point({"slug": "a"})) == point_id
    assert asyncio.run(repository.update_point(point_id, {"slug": "b"})) == {"slug": "b"}
    assert asyncio.run(repository.delete_point(point_id)) is True


def test_duplicate_key_is_translated() -> None:
    error = DuplicateKeyError("dup", 11000, {"keyPattern": {"slug": 1}})
    repository = repository_with(FailingCollection(error))

    with pytest.raises(UniqueConstraintError) as created:
        asyncio.run(repository.create_point({"slug": "a"}))
    with pytest.raises(UniqueConstraintError) as updated:
        asyncio.run(repository.update_point("0123456789ab0123456789ab", {"slug": "a"}))

    assert created.value.field == "slug"
    assert updated.value.field == "slug"


@pytest.mark.parametrize(
    "call",
    [
        lambda r: r.list_points(),
        lambda r: r.find_by_slug("a"),
        lambda r: r.create_point({"slug": "a"}),
        lambda r: r.update_point("0123456789ab0123456789ab", {"slug": "a"}),
        lambda r: r.delete_point("0123456789ab0123456789ab"),
    ],
)
def test_mongo_errors_become_connection_error(call: Any) -> None:
    repository = repository_with(FailingCollection(PyMongoError("falhou")))

    with pytest.raises(ConnectionError):
        asyncio.run(call(repository))


def test_missing_database_raises_connection_error() -> None:
    repository = PointRepository(None)

    with pytest.raises(ConnectionError):
        asyncio.run(repository.find_by_slug("a"))


class CountingCollection:
    def __init__(self) -> None:
        self.queries: list[Any] = []

    async def count_documents(self, query: dict[str, Any]) -> int:
        self.queries.append(query)
        return 3

    def find(self, query: dict[str, Any], projection: dict[str, int]) -> FakeCursor:
        self.queries.append((query, projection))
        return FakeCursor([{"slug": "a", "name": "Ponto A"}])


def test_count_points_and_names_by_slugs() -> None:
    collection = CountingCollection()
    repository = repository_with(collection)

    assert asyncio.run(repository.count_points()) == 3
    assert asyncio.run(repository.count_points("published")) == 3
    assert asyncio.run(repository.find_names_by_slugs(["a", "b"])) == {"a": "Ponto A"}
    assert asyncio.run(repository.find_names_by_slugs([])) == {}

    assert collection.queries == [
        {},
        {"status": "published"},
        ({"slug": {"$in": ["a", "b"]}}, {"slug": 1, "name": 1}),
    ]


def test_count_and_names_translate_mongo_errors() -> None:
    class Failing:
        async def count_documents(self, _query: dict[str, Any]) -> int:
            raise PyMongoError("falhou")

        def find(self, *_args: Any) -> Any:
            raise PyMongoError("falhou")

    repository = repository_with(Failing())

    with pytest.raises(ConnectionError):
        asyncio.run(repository.count_points())
    with pytest.raises(ConnectionError):
        asyncio.run(repository.find_names_by_slugs(["a"]))

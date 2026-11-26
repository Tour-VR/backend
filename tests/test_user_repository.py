from __future__ import annotations

import asyncio
from typing import Any

import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.repositories.errors import UniqueConstraintError
from app.repositories.user_repository import UserRepository


class DuplicateCollection:
    def __init__(self, key_pattern: dict[str, int]) -> None:
        self.error = DuplicateKeyError("dup", 11000, {"keyPattern": key_pattern})

    async def insert_one(self, _document: dict[str, Any]) -> None:
        raise self.error

    async def find_one_and_update(self, *_args: Any, **_kwargs: Any) -> None:
        raise self.error


def make_repository(key_pattern: dict[str, int]) -> UserRepository:
    return UserRepository({"users": DuplicateCollection(key_pattern)})


def test_create_user_translates_duplicate_key() -> None:
    repository = make_repository({"email": 1})

    with pytest.raises(UniqueConstraintError) as exc_info:
        asyncio.run(repository.create_user({"email": "dup@example.com"}))

    assert exc_info.value.field == "email"


def test_update_user_translates_duplicate_key() -> None:
    repository = make_repository({"username": 1})

    with pytest.raises(UniqueConstraintError) as exc_info:
        asyncio.run(repository.update_user_by_email("a@example.com", {"username": "x"}))

    assert exc_info.value.field == "username"


def test_update_user_by_id_translates_duplicate_key() -> None:
    repository = make_repository({"email": 1})

    with pytest.raises(UniqueConstraintError) as exc_info:
        asyncio.run(repository.update_user_by_id(str(ObjectId()), {"email": "x@example.com"}))

    assert exc_info.value.field == "email"


def test_duplicate_without_key_pattern_reports_unknown_field() -> None:
    repository = make_repository({})

    with pytest.raises(UniqueConstraintError) as exc_info:
        asyncio.run(repository.create_user({"email": "dup@example.com"}))

    assert exc_info.value.field == "desconhecido"


class FakeCursor:
    def __init__(self, documents: list[dict[str, Any]], calls: list[tuple[str, Any]]) -> None:
        self.documents = documents
        self.calls = calls

    def sort(self, field: str, direction: int) -> FakeCursor:
        self.calls.append(("sort", (field, direction)))
        return self

    def skip(self, amount: int) -> FakeCursor:
        self.calls.append(("skip", amount))
        return self

    def limit(self, amount: int) -> FakeCursor:
        self.calls.append(("limit", amount))
        return self

    async def to_list(self, _length: int | None) -> list[dict[str, Any]]:
        return self.documents


class ListingCollection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.user = {"_id": ObjectId(), "email": "a@example.com"}

    def find(self, query: dict[str, Any]) -> FakeCursor:
        self.calls.append(("find", query))
        return FakeCursor([self.user], self.calls)

    async def count_documents(self, query: dict[str, Any]) -> int:
        self.calls.append(("count", query))
        return 7

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("find_one", query))
        return self.user

    async def find_one_and_update(self, query: dict[str, Any], *_args: Any, **_kw: Any) -> Any:
        self.calls.append(("update", query))
        return self.user


class BrokenCollection:
    def find(self, _query: dict[str, Any]) -> None:
        raise PyMongoError("fora")

    async def count_documents(self, _query: dict[str, Any]) -> None:
        raise PyMongoError("fora")

    async def find_one(self, _query: dict[str, Any]) -> None:
        raise PyMongoError("fora")

    async def find_one_and_update(self, *_args: Any, **_kwargs: Any) -> None:
        raise PyMongoError("fora")


def test_list_users_sorts_by_created_at_desc_and_paginates() -> None:
    collection = ListingCollection()
    repository = UserRepository({"users": collection})

    users = asyncio.run(repository.list_users(skip=40, limit=20))

    assert users == [collection.user]
    assert collection.calls == [
        ("find", {}),
        ("sort", ("created_at", -1)),
        ("skip", 40),
        ("limit", 20),
    ]


def test_count_and_find_by_id_use_collection() -> None:
    collection = ListingCollection()
    repository = UserRepository({"users": collection})
    user_id = str(collection.user["_id"])

    assert asyncio.run(repository.count_users()) == 7
    assert asyncio.run(repository.find_by_id(user_id)) == collection.user
    assert asyncio.run(repository.update_user_by_id(user_id, {"is_active": False}))
    assert ("find_one", {"_id": collection.user["_id"]}) in collection.calls


def test_invalid_id_returns_none_without_query() -> None:
    collection = ListingCollection()
    repository = UserRepository({"users": collection})

    assert asyncio.run(repository.find_by_id("abc")) is None
    assert asyncio.run(repository.update_user_by_id("abc", {"is_active": False})) is None
    assert collection.calls == []


def test_new_methods_translate_pymongo_error() -> None:
    repository = UserRepository({"users": BrokenCollection()})
    valid_id = str(ObjectId())

    with pytest.raises(ConnectionError):
        asyncio.run(repository.list_users(0, 20))
    with pytest.raises(ConnectionError):
        asyncio.run(repository.count_users())
    with pytest.raises(ConnectionError):
        asyncio.run(repository.find_by_id(valid_id))
    with pytest.raises(ConnectionError):
        asyncio.run(repository.update_user_by_id(valid_id, {}))

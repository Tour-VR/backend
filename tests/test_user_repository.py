from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pymongo.errors import DuplicateKeyError

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


def test_duplicate_without_key_pattern_reports_unknown_field() -> None:
    repository = make_repository({})

    with pytest.raises(UniqueConstraintError) as exc_info:
        asyncio.run(repository.create_user({"email": "dup@example.com"}))

    assert exc_info.value.field == "desconhecido"

"""Testes da regra de criar ou promover administrador."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest

from app.core.security import verify_password
from app.repositories.errors import UniqueConstraintError
from app.schemas.user import UserCreate
from app.services.user_service import UserConflictError, UserNotFoundError, UserService


class FakeUserRepository:
    """Repository em memoria que registra as chamadas recebidas."""

    def __init__(self, existing: dict[str, Any] | None = None) -> None:
        self.existing = existing
        self.created: list[dict[str, Any]] = []
        self.updates: list[tuple[str, dict[str, Any]]] = []
        self.create_error: Exception | None = None

    async def find_by_email(self, _email: str) -> dict[str, Any] | None:
        return self.existing

    async def create_user(self, user_data: dict[str, Any]) -> dict[str, str]:
        if self.create_error is not None:
            raise self.create_error
        self.created.append(user_data)
        return {"inserted_id": "fake-id"}

    async def update_user_by_email(
        self, email: str, update_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        self.updates.append((email, update_data))
        if self.existing is None:
            return None
        return {**self.existing, **update_data}


def admin_payload() -> UserCreate:
    return UserCreate(email="Admin@Example.com", password="abc12345", full_name="Admin")


def run_create_or_promote(repository: FakeUserRepository) -> tuple[dict[str, Any], bool]:
    service = UserService(repository)  # type: ignore[arg-type]
    return asyncio.run(service.create_or_promote_admin(admin_payload()))


def test_create_or_promote_admin_creates_when_missing() -> None:
    repository = FakeUserRepository()

    user, created = run_create_or_promote(repository)

    assert created is True
    assert user["role"] == "admin"
    assert user["email"] == "admin@example.com"
    assert "hashed_password" not in user
    assert verify_password("abc12345", repository.created[0]["hashed_password"])
    assert repository.created[0]["role"] == "admin"


def test_create_or_promote_admin_promotes_existing() -> None:
    existing = {
        "email": "admin@example.com",
        "hashed_password": "hash-antigo",
        "role": "user",
        "is_active": False,
        "created_at": datetime.now(UTC),
    }
    repository = FakeUserRepository(existing=existing)

    user, created = run_create_or_promote(repository)

    assert created is False
    assert user["role"] == "admin"
    assert user["is_active"] is True
    assert not repository.created
    email, update_data = repository.updates[0]
    assert email == "admin@example.com"
    assert update_data["role"] == "admin"
    assert update_data["is_active"] is True
    assert "hashed_password" not in update_data


def test_create_or_promote_admin_translates_unique_constraint() -> None:
    repository = FakeUserRepository()
    repository.create_error = UniqueConstraintError("email")

    with pytest.raises(UserConflictError):
        run_create_or_promote(repository)


def test_create_or_promote_admin_raises_when_promoted_user_vanishes() -> None:
    repository = FakeUserRepository(existing={"email": "admin@example.com"})

    async def vanished(email: str, update_data: dict[str, Any]) -> None:
        return None

    repository.update_user_by_email = vanished  # type: ignore[method-assign]

    with pytest.raises(UserNotFoundError):
        run_create_or_promote(repository)

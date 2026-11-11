"""Testes do comando create-admin."""

from __future__ import annotations

from typing import Any

import pytest

from app import cli
from app.repositories.errors import UniqueConstraintError
from app.repositories.user_repository import UserRepository

PASSWORD = "Segredo123"


def run_create_admin(email: str = "Novo@Example.com", password: str = PASSWORD) -> int:
    return cli.main(["create-admin", "--email", email, "--password", password])


@pytest.fixture(autouse=True)
def fake_cli_indexes(monkeypatch: pytest.MonkeyPatch) -> None:
    """O comando nao deve tentar criar indices num MongoDB real."""

    async def noop(_database: Any) -> None:
        return None

    monkeypatch.setattr(cli, "ensure_indexes", noop)


@pytest.fixture()
def empty_users(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Banco sem usuarios: o comando deve criar o administrador."""

    created: list[dict[str, Any]] = []

    async def fake_find_by_email(self: UserRepository, email: str) -> None:
        return None

    async def fake_create_user(self: UserRepository, user_data: dict[str, Any]) -> None:
        created.append(user_data)

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)
    monkeypatch.setattr(UserRepository, "create_user", fake_create_user)
    return created


def test_create_admin_success_prints_email(mongo_up, empty_users, capsys) -> None:
    exit_code = run_create_admin()

    captured = capsys.readouterr()
    assert exit_code == cli.EXIT_OK
    assert "Administrador criado: novo@example.com" in captured.out
    assert PASSWORD not in captured.out + captured.err
    assert empty_users[0]["role"] == "admin"


def test_create_admin_promotes_existing_user(mongo_up, monkeypatch, capsys) -> None:
    async def fake_find_by_email(self: UserRepository, email: str) -> dict[str, Any]:
        return {"email": email, "role": "user", "hashed_password": "hash"}

    async def fake_update_user_by_email(
        self: UserRepository, email: str, update_data: dict[str, Any]
    ) -> dict[str, Any]:
        return {"email": email, "hashed_password": "hash", **update_data}

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)
    monkeypatch.setattr(UserRepository, "update_user_by_email", fake_update_user_by_email)

    exit_code = run_create_admin()

    captured = capsys.readouterr()
    assert exit_code == cli.EXIT_OK
    assert "Usuario promovido a administrador: novo@example.com" in captured.out
    assert PASSWORD not in captured.out + captured.err


def test_create_admin_invalid_password_returns_2(capsys) -> None:
    exit_code = run_create_admin(password="curta")

    captured = capsys.readouterr()
    assert exit_code == cli.EXIT_INVALID_INPUT
    assert "Dados invalidos" in captured.err
    assert "curta" not in captured.err


def test_create_admin_database_down_returns_1(mongo_down, capsys) -> None:
    exit_code = run_create_admin()

    captured = capsys.readouterr()
    assert exit_code == cli.EXIT_DATABASE_UNAVAILABLE
    assert "Banco de dados indisponivel" in captured.err


def test_create_admin_repository_failure_returns_1(mongo_up, monkeypatch, capsys) -> None:
    async def fake_find_by_email(self: UserRepository, email: str) -> None:
        raise ConnectionError("Falha ao buscar usuario no MongoDB.")

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)

    assert run_create_admin() == cli.EXIT_DATABASE_UNAVAILABLE
    assert "Banco de dados indisponivel" in capsys.readouterr().err


def test_create_admin_conflict_returns_2(mongo_up, empty_users, monkeypatch, capsys) -> None:
    async def fake_create_user(self: UserRepository, user_data: dict[str, Any]) -> None:
        raise UniqueConstraintError("email")

    monkeypatch.setattr(UserRepository, "create_user", fake_create_user)

    assert run_create_admin() == cli.EXIT_INVALID_INPUT
    assert "Ja existe um usuario com este email." in capsys.readouterr().err

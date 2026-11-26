from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from bson import ObjectId

from app.api.deps import require_admin
from app.core.security import create_access_token
from app.repositories.errors import UniqueConstraintError
from app.repositories.user_repository import UserRepository
from main import app

USERS_PATH = "/admin/users"
OLD_DATE = datetime(2026, 1, 1, tzinfo=UTC)
ADMIN_ID = ObjectId()
SELF_LOCKOUT = "Você não pode remover o próprio acesso de administrador."


def make_user(**kwargs: Any) -> dict[str, Any]:
    user: dict[str, Any] = {
        "_id": ObjectId(),
        "email": "ana@example.com",
        "username": "ana",
        "full_name": "Ana Souza",
        "hashed_password": "hash-secreto",
        "role": "user",
        "is_active": True,
        "created_at": OLD_DATE,
    }
    user.update(kwargs)
    return user


def patch_repo(monkeypatch: pytest.MonkeyPatch, **methods: Any) -> None:
    """Troca metodos do UserRepository por funcoes async que devolvem o valor dado."""

    for name, value in methods.items():

        async def fake(_self: UserRepository, *_args: Any, _value: Any = value) -> Any:
            if isinstance(_value, Exception):
                raise _value
            return _value(*_args) if callable(_value) else _value

        monkeypatch.setattr(UserRepository, name, fake)


@pytest.fixture()
def as_self_admin() -> Iterator[dict[str, Any]]:
    """Admin autenticado com `_id`, para testar a autoprotecao."""

    admin = make_user(_id=ADMIN_ID, email="admin@example.com", role="admin")
    app.dependency_overrides[require_admin] = lambda: admin
    yield admin
    app.dependency_overrides.pop(require_admin, None)


def test_list_users_returns_page_without_password(client, monkeypatch, as_admin) -> None:
    received: list[tuple[int, int]] = []
    users = [make_user(), make_user(email="bia@example.com", created_at=None)]

    def list_users(skip: int, limit: int) -> list[dict[str, Any]]:
        received.append((skip, limit))
        return users

    patch_repo(monkeypatch, list_users=list_users, count_users=42)

    response = client.get(USERS_PATH, params={"page": 3, "page_size": 2})

    assert response.status_code == 200
    body = response.json()
    assert received == [(4, 2)]
    assert body["total"] == 42
    assert body["page"] == 3
    assert body["page_size"] == 2
    assert body["items"][0]["id"] == str(users[0]["_id"])
    assert body["items"][1]["created_at"] is None
    assert "hash" not in response.text
    assert "password" not in response.text


def test_list_users_uses_default_page_size(client, monkeypatch, as_admin) -> None:
    received: list[tuple[int, int]] = []

    def list_users(skip: int, limit: int) -> list[dict[str, Any]]:
        received.append((skip, limit))
        return []

    patch_repo(monkeypatch, list_users=list_users, count_users=0)

    response = client.get(USERS_PATH)

    assert response.status_code == 200
    assert received == [(0, 20)]
    assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}


@pytest.mark.parametrize("params", [{"page_size": 101}, {"page": 0}, {"page_size": 0}])
def test_list_users_rejects_invalid_pagination(client, as_admin, params) -> None:
    response = client.get(USERS_PATH, params=params)

    assert response.status_code == 400


def test_patch_deactivates_other_user(client, monkeypatch, as_self_admin) -> None:
    target = make_user()
    captured: dict[str, Any] = {}

    def update(user_id: str, update_data: dict[str, Any]) -> dict[str, Any]:
        captured.update(update_data, user_id=user_id)
        return {**target, **update_data}

    patch_repo(monkeypatch, find_by_id=target, update_user_by_id=update)

    response = client.patch(f"{USERS_PATH}/{target['_id']}", json={"is_active": False})

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert captured["user_id"] == str(target["_id"])
    assert captured["is_active"] is False
    assert "updated_at" in captured
    assert "role" not in captured
    assert "hash" not in response.text


def test_patch_promotes_user_to_admin(client, monkeypatch, as_self_admin) -> None:
    target = make_user()
    patch_repo(
        monkeypatch,
        find_by_id=target,
        update_user_by_id=lambda _id, data: {**target, **data},
    )

    response = client.patch(f"{USERS_PATH}/{target['_id']}", json={"role": "admin"})

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


@pytest.mark.parametrize("payload", [{"is_active": False}, {"role": "user"}])
def test_patch_self_lockout_returns_400(client, monkeypatch, as_self_admin, payload) -> None:
    patch_repo(
        monkeypatch,
        find_by_id=as_self_admin,
        update_user_by_id=AssertionError("nao deveria gravar"),
    )

    response = client.patch(f"{USERS_PATH}/{ADMIN_ID}", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": SELF_LOCKOUT}


def test_patch_self_keeping_admin_is_allowed(client, monkeypatch, as_self_admin) -> None:
    patch_repo(
        monkeypatch,
        find_by_id=as_self_admin,
        update_user_by_id=lambda _id, data: {**as_self_admin, **data},
    )

    response = client.patch(f"{USERS_PATH}/{ADMIN_ID}", json={"role": "admin"})

    assert response.status_code == 200


def test_patch_invalid_id_returns_404(client, as_admin) -> None:
    response = client.patch(f"{USERS_PATH}/nao-e-um-id", json={"is_active": False})

    assert response.status_code == 404
    assert response.json() == {"detail": "Usuário não encontrado."}


def test_patch_unknown_id_returns_404(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, find_by_id=None)

    response = client.patch(f"{USERS_PATH}/{ObjectId()}", json={"is_active": False})

    assert response.status_code == 404


def test_patch_user_removed_during_update_returns_404(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, find_by_id=make_user(), update_user_by_id=None)

    response = client.patch(f"{USERS_PATH}/{ObjectId()}", json={"is_active": True})

    assert response.status_code == 404


def test_patch_empty_body_returns_400(client, as_admin) -> None:
    response = client.patch(f"{USERS_PATH}/{ObjectId()}", json={})

    assert response.status_code == 400
    assert response.json() == {"detail": "Nenhum campo valido para atualizacao."}


def test_patch_invalid_role_returns_422(client, as_admin) -> None:
    response = client.patch(f"{USERS_PATH}/{ObjectId()}", json={"role": "root"})

    assert response.status_code == 422


def test_admin_users_requires_admin(client, monkeypatch) -> None:
    without_token = client.get(USERS_PATH)

    async def fake_find_by_email(_self: UserRepository, email: str) -> dict[str, Any]:
        return {"email": email, "role": "user", "is_active": True}

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)
    token = create_access_token("me@example.com", extra_claims={"role": "user"})
    headers = {"Authorization": f"Bearer {token}"}
    list_as_user = client.get(USERS_PATH, headers=headers)
    patch_as_user = client.patch(
        f"{USERS_PATH}/{ObjectId()}", json={"is_active": False}, headers=headers
    )

    assert without_token.status_code == 401
    assert list_as_user.status_code == 403
    assert patch_as_user.status_code == 403


def test_list_users_returns_503_when_database_fails(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, list_users=ConnectionError("fora do ar"))

    response = client.get(USERS_PATH)

    assert response.status_code == 503
    assert response.json() == {"detail": "Banco de dados indisponivel."}


def test_patch_returns_503_when_database_fails(client, monkeypatch, as_admin) -> None:
    patch_repo(monkeypatch, find_by_id=ConnectionError("fora do ar"))

    response = client.patch(f"{USERS_PATH}/{ObjectId()}", json={"is_active": False})

    assert response.status_code == 503


EMAIL_CONFLICT = "Ja existe um usuario com este email."
USERNAME_CONFLICT = "Ja existe um usuario com este username."


def test_patch_edits_basic_data_normalized(client, monkeypatch, as_self_admin) -> None:
    target = make_user()
    captured: dict[str, Any] = {}

    def update(_user_id: str, update_data: dict[str, Any]) -> dict[str, Any]:
        captured.update(update_data)
        return {**target, **update_data}

    patch_repo(
        monkeypatch,
        find_by_id=target,
        find_by_email=None,
        find_by_username=None,
        update_user_by_id=update,
    )

    response = client.patch(
        f"{USERS_PATH}/{target['_id']}",
        json={"email": " Ana.Nova@Example.COM ", "full_name": " Ana Lima ", "username": "AnaL"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "ana.nova@example.com"
    assert body["full_name"] == "Ana Lima"
    assert body["username"] == "anal"
    assert "is_active" not in captured
    assert "role" not in captured


def test_patch_clears_full_name_and_username(client, monkeypatch, as_admin) -> None:
    target = make_user()
    captured: dict[str, Any] = {}

    def update(_user_id: str, update_data: dict[str, Any]) -> dict[str, Any]:
        captured.update(update_data)
        return {**target, **update_data}

    patch_repo(monkeypatch, find_by_id=target, update_user_by_id=update)

    response = client.patch(
        f"{USERS_PATH}/{target['_id']}", json={"full_name": "", "username": None}
    )

    assert response.status_code == 200
    assert captured["full_name"] is None
    assert captured["username"] is None


def test_patch_null_email_is_ignored(client, as_admin) -> None:
    response = client.patch(f"{USERS_PATH}/{ObjectId()}", json={"email": None, "role": None})

    assert response.status_code == 400
    assert response.json() == {"detail": "Nenhum campo valido para atualizacao."}


def test_patch_same_email_skips_conflict_check(client, monkeypatch, as_admin) -> None:
    target = make_user()
    patch_repo(
        monkeypatch,
        find_by_id=target,
        find_by_email=AssertionError("nao deveria buscar"),
        update_user_by_id=lambda _id, data: {**target, **data},
    )

    response = client.patch(f"{USERS_PATH}/{target['_id']}", json={"email": target["email"]})

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("payload", "lookup", "message"),
    [
        ({"email": "bia@example.com"}, "find_by_email", EMAIL_CONFLICT),
        ({"username": "bia"}, "find_by_username", USERNAME_CONFLICT),
    ],
)
def test_patch_identity_taken_by_other_returns_400(
    client, monkeypatch, as_admin, payload, lookup, message
) -> None:
    target = make_user()
    patch_repo(monkeypatch, find_by_id=target, **{lookup: make_user(email="bia@example.com")})

    response = client.patch(f"{USERS_PATH}/{target['_id']}", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": message}


@pytest.mark.parametrize(
    ("field", "message"), [("email", EMAIL_CONFLICT), ("username", USERNAME_CONFLICT)]
)
def test_patch_unique_index_violation_returns_400(
    client, monkeypatch, as_admin, field, message
) -> None:
    target = make_user()
    patch_repo(
        monkeypatch,
        find_by_id=target,
        find_by_email=None,
        find_by_username=None,
        update_user_by_id=UniqueConstraintError(field),
    )

    response = client.patch(
        f"{USERS_PATH}/{target['_id']}", json={"email": "novo@example.com", "username": "novo"}
    )

    assert response.status_code == 400
    assert response.json() == {"detail": message}


def test_patch_invalid_email_returns_422(client, as_admin) -> None:
    response = client.patch(f"{USERS_PATH}/{ObjectId()}", json={"email": "sem-arroba"})

    assert response.status_code == 422

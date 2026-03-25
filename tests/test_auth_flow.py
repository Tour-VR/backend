from __future__ import annotations

from datetime import datetime, timezone

from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository


def test_register_success(client, monkeypatch) -> None:
    """O cadastro deve normalizar email e username antes de salvar."""

    captured_user_data: dict = {}

    async def fake_find_by_email(self: UserRepository, email: str):
        assert email == "new-user@example.com"
        return None

    async def fake_find_by_username(self: UserRepository, username: str):
        assert username == "newuser"
        return None

    async def fake_create_user(self: UserRepository, user_data: dict):
        captured_user_data.update(user_data)
        return {"inserted_id": "fake-id"}

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)
    monkeypatch.setattr(UserRepository, "find_by_username", fake_find_by_username)
    monkeypatch.setattr(UserRepository, "create_user", fake_create_user)

    response = client.post(
        "/auth/register",
        json={
            "email": "NEW-USER@EXAMPLE.COM",
            "password": "abc12345",
            "full_name": "New User",
            "username": "NewUser",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "new-user@example.com"
    assert body["username"] == "newuser"
    assert body["full_name"] == "New User"
    assert body["role"] == "user"
    assert body["is_active"] is True
    assert body["is_verified"] is False
    assert body["created_at"]
    assert body["updated_at"]
    assert captured_user_data["email"] == "new-user@example.com"
    assert captured_user_data["username"] == "newuser"
    assert verify_password("abc12345", captured_user_data["hashed_password"])


def test_register_duplicate_email_returns_400(client, monkeypatch) -> None:
    async def fake_find_by_email(self: UserRepository, email: str):
        return {"email": email}

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)

    response = client.post(
        "/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "abc12345",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Ja existe um usuario com este email."}


def test_register_duplicate_username_returns_400(client, monkeypatch) -> None:
    async def fake_find_by_email(self: UserRepository, email: str):
        return None

    async def fake_find_by_username(self: UserRepository, username: str):
        return {"username": username}

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)
    monkeypatch.setattr(UserRepository, "find_by_username", fake_find_by_username)

    response = client.post(
        "/auth/register",
        json={
            "email": "fresh@example.com",
            "password": "abc12345",
            "username": "duplicado",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Ja existe um usuario com este username."}


def test_register_invalid_password_returns_422(client) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "weak@example.com",
            "password": "12345678",
        },
    )

    assert response.status_code == 422
    assert "A senha deve ter pelo menos 8 caracteres" in response.text


def test_login_success_returns_token(client, monkeypatch) -> None:
    async def fake_find_by_email_or_username(self: UserRepository, email: str):
        return {
            "email": "login@example.com",
            "hashed_password": hash_password("abc12345"),
            "role": "user",
            "is_active": True,
        }

    monkeypatch.setattr(
        UserRepository, "find_by_email_or_username", fake_find_by_email_or_username
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "login@example.com",
            "password": "abc12345",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]


def test_login_accepts_username(client, monkeypatch) -> None:
    async def fake_find_by_email_or_username(self: UserRepository, email: str):
        assert email == "loginuser"
        return {
            "email": "login@example.com",
            "username": "loginuser",
            "hashed_password": hash_password("abc12345"),
            "role": "user",
            "is_active": True,
        }

    monkeypatch.setattr(
        UserRepository, "find_by_email_or_username", fake_find_by_email_or_username
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "loginuser",
            "password": "abc12345",
        },
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_login_invalid_password_returns_401(client, monkeypatch) -> None:
    async def fake_find_by_email_or_username(self: UserRepository, email: str):
        return {
            "email": "login@example.com",
            "hashed_password": hash_password("abc12345"),
            "role": "user",
            "is_active": True,
        }

    monkeypatch.setattr(
        UserRepository, "find_by_email_or_username", fake_find_by_email_or_username
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "login@example.com",
            "password": "wrong999",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciais invalidas."}


def test_login_inactive_user_returns_401(client, monkeypatch) -> None:
    async def fake_find_by_email_or_username(self: UserRepository, email: str):
        return {
            "email": "login@example.com",
            "hashed_password": hash_password("abc12345"),
            "role": "user",
            "is_active": False,
        }

    monkeypatch.setattr(
        UserRepository, "find_by_email_or_username", fake_find_by_email_or_username
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "login@example.com",
            "password": "abc12345",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciais invalidas."}


def test_register_returns_503_when_database_fails(client, monkeypatch) -> None:
    async def fake_find_by_email(self: UserRepository, email: str):
        raise ConnectionError("Falha ao buscar usuario no MongoDB.")

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)

    response = client.post(
        "/auth/register",
        json={
            "email": "db-down@example.com",
            "password": "abc12345",
        },
    )

    assert response.status_code == 503
    assert "Banco de dados indisponivel." in response.json()["detail"]


def test_login_returns_503_when_database_fails(client, monkeypatch) -> None:
    async def fake_find_by_email_or_username(self: UserRepository, email: str):
        raise ConnectionError("Falha ao buscar usuario no MongoDB.")

    monkeypatch.setattr(
        UserRepository, "find_by_email_or_username", fake_find_by_email_or_username
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "db-down@example.com",
            "password": "abc12345",
        },
    )

    assert response.status_code == 503
    assert "Banco de dados indisponivel." in response.json()["detail"]


def test_users_me_success(client, monkeypatch) -> None:
    async def fake_find_by_email(self: UserRepository, email: str):
        now = datetime.now(timezone.utc)
        return {
            "email": email,
            "full_name": "Current User",
            "username": "currentuser",
            "role": "user",
            "is_active": True,
            "is_verified": False,
            "hashed_password": hash_password("abc12345"),
            "created_at": now,
            "updated_at": now,
        }

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)
    token = create_access_token("me@example.com", extra_claims={"role": "user"})

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "me@example.com"
    assert body["username"] == "currentuser"
    assert body["role"] == "user"
    assert body["is_active"] is True
    assert body["is_verified"] is False
    assert "hashed_password" not in body


def test_users_me_update_success(client, monkeypatch) -> None:
    now = datetime.now(timezone.utc)

    async def fake_find_by_email(self: UserRepository, email: str):
        return {
            "email": email,
            "full_name": "Current User",
            "username": "currentuser",
            "role": "user",
            "is_active": True,
            "is_verified": False,
            "hashed_password": hash_password("abc12345"),
            "created_at": now,
            "updated_at": now,
        }

    async def fake_find_by_username(self: UserRepository, username: str):
        return None

    async def fake_update_user_by_email(
        self: UserRepository,
        email: str,
        update_data: dict,
    ):
        return {
            "email": email,
            "full_name": update_data.get("full_name", "Current User"),
            "username": update_data.get("username", "currentuser"),
            "role": "user",
            "is_active": True,
            "is_verified": False,
            "hashed_password": hash_password("abc12345"),
            "created_at": now,
            "updated_at": update_data["updated_at"],
        }

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)
    monkeypatch.setattr(UserRepository, "find_by_username", fake_find_by_username)
    monkeypatch.setattr(UserRepository, "update_user_by_email", fake_update_user_by_email)

    token = create_access_token("me@example.com", extra_claims={"role": "user"})
    response = client.put(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Nome Atualizado",
            "username": "novo_user",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Nome Atualizado"
    assert body["username"] == "novo_user"
    assert "hashed_password" not in body


def test_users_me_update_duplicate_username_returns_400(client, monkeypatch) -> None:
    now = datetime.now(timezone.utc)

    async def fake_find_by_email(self: UserRepository, email: str):
        return {
            "email": email,
            "full_name": "Current User",
            "username": "currentuser",
            "role": "user",
            "is_active": True,
            "is_verified": False,
            "hashed_password": hash_password("abc12345"),
            "created_at": now,
            "updated_at": now,
        }

    async def fake_find_by_username(self: UserRepository, username: str):
        return {"email": "other@example.com", "username": username}

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)
    monkeypatch.setattr(UserRepository, "find_by_username", fake_find_by_username)

    token = create_access_token("me@example.com", extra_claims={"role": "user"})
    response = client.put(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "ocupado"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Ja existe um usuario com este username."}


def test_users_me_change_password_success(client, monkeypatch) -> None:
    current_hash = hash_password("abc12345")
    updated_hashes: list[str] = []

    async def fake_find_by_email(self: UserRepository, email: str):
        now = datetime.now(timezone.utc)
        return {
            "email": email,
            "full_name": "Current User",
            "username": "currentuser",
            "role": "user",
            "is_active": True,
            "is_verified": False,
            "hashed_password": current_hash,
            "created_at": now,
            "updated_at": now,
        }

    async def fake_update_user_by_email(
        self: UserRepository,
        email: str,
        update_data: dict,
    ):
        updated_hashes.append(update_data["hashed_password"])
        return {"email": email, "hashed_password": update_data["hashed_password"]}

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)
    monkeypatch.setattr(UserRepository, "update_user_by_email", fake_update_user_by_email)

    token = create_access_token("me@example.com", extra_claims={"role": "user"})
    response = client.put(
        "/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "abc12345",
            "new_password": "nova1234",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Senha atualizada com sucesso."}
    assert updated_hashes
    assert verify_password("nova1234", updated_hashes[0])


def test_users_me_change_password_with_wrong_current_password_returns_400(
    client,
    monkeypatch,
) -> None:
    async def fake_find_by_email(self: UserRepository, email: str):
        now = datetime.now(timezone.utc)
        return {
            "email": email,
            "full_name": "Current User",
            "username": "currentuser",
            "role": "user",
            "is_active": True,
            "is_verified": False,
            "hashed_password": hash_password("abc12345"),
            "created_at": now,
            "updated_at": now,
        }

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)

    token = create_access_token("me@example.com", extra_claims={"role": "user"})
    response = client.put(
        "/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "senhaerrada",
            "new_password": "nova1234",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Senha atual invalida."}


def test_users_me_without_token_returns_401(client) -> None:
    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Token nao informado."}


def test_users_me_with_invalid_token_returns_401(client) -> None:
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Token invalido ou expirado."}


def test_users_me_with_inactive_user_returns_403(client, monkeypatch) -> None:
    async def fake_find_by_email(self: UserRepository, email: str):
        now = datetime.now(timezone.utc)
        return {
            "email": email,
            "full_name": "Current User",
            "username": "currentuser",
            "role": "user",
            "is_active": False,
            "is_verified": False,
            "hashed_password": hash_password("abc12345"),
            "created_at": now,
            "updated_at": now,
        }

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)
    token = create_access_token("me@example.com", extra_claims={"role": "user"})

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Usuario inativo."}


def test_users_me_returns_503_when_database_fails(client, monkeypatch) -> None:
    async def fake_find_by_email(self: UserRepository, email: str):
        raise ConnectionError("Falha ao buscar usuario no MongoDB.")

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)
    token = create_access_token("me@example.com", extra_claims={"role": "user"})

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert "Banco de dados indisponivel." in response.json()["detail"]

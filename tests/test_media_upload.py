from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.main import create_app
from app.repositories.media_storage import MediaStorage
from app.repositories.user_repository import UserRepository

JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"0" * 200


@pytest.fixture()
def media_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Grava a midia num diretorio temporario, nunca no `media/` do repositorio."""

    monkeypatch.setattr(settings, "media_dir", str(tmp_path))
    return tmp_path


def upload(client: TestClient, content: bytes, name: str = "foto.jpg") -> Any:
    return client.post("/admin/media", files={"file": (name, content, "image/jpeg")})


def test_upload_jpeg_returns_201_and_saves_file(client, as_admin, media_dir: Path) -> None:
    response = upload(client, JPEG_BYTES)

    assert response.status_code == 201
    body = response.json()
    assert body["content_type"] == "image/jpeg"
    assert body["size_bytes"] == len(JPEG_BYTES)
    assert body["url"].startswith("/media/") and body["url"].endswith(".jpg")
    assert (media_dir / body["url"].removeprefix("/media/")).read_bytes() == JPEG_BYTES


def test_upload_above_limit_returns_413_and_saves_nothing(
    client, as_admin, media_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "media_max_bytes", 100)

    response = upload(client, JPEG_BYTES)

    assert response.status_code == 413
    assert response.json()["detail"] == "Arquivo maior que 0 MB."
    assert list(media_dir.iterdir()) == []


def test_upload_text_named_jpg_returns_415(client, as_admin, media_dir: Path) -> None:
    response = upload(client, b"isto e um texto, nao uma foto")

    assert response.status_code == 415
    assert response.json()["detail"] == "Formato não suportado. Envie JPEG, PNG ou WebP."
    assert list(media_dir.iterdir()) == []


def test_upload_empty_file_returns_400(client, as_admin, media_dir: Path) -> None:
    response = upload(client, b"")

    assert response.status_code == 400
    assert response.json()["detail"] == "Arquivo vazio."


def test_upload_without_file_returns_422(client, as_admin, media_dir: Path) -> None:
    response = client.post("/admin/media")

    assert response.status_code == 422


def test_upload_returns_503_when_disk_fails(
    client, as_admin, media_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_save(_self: MediaStorage, _content: bytes, _extension: str) -> str:
        raise ConnectionError("Falha ao gravar o arquivo de midia.")

    monkeypatch.setattr(MediaStorage, "save", broken_save)

    response = upload(client, JPEG_BYTES)

    assert response.status_code == 503


def test_upload_without_token_returns_401(client, media_dir: Path) -> None:
    response = upload(client, JPEG_BYTES)

    assert response.status_code == 401


def test_upload_with_user_role_returns_403(
    client, media_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_find_by_email(_self: UserRepository, email: str) -> dict[str, Any]:
        return {"email": email, "role": "user", "is_active": True}

    monkeypatch.setattr(UserRepository, "find_by_email", fake_find_by_email)
    token = create_access_token("me@example.com", extra_claims={"role": "user"})

    response = client.post(
        "/admin/media",
        files={"file": ("foto.jpg", JPEG_BYTES, "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert list(media_dir.iterdir()) == []


def test_uploaded_file_is_served_under_media(client, as_admin, media_dir: Path) -> None:
    url = upload(client, JPEG_BYTES).json()["url"]

    # A montagem de /media le o diretorio na criacao da app: cria uma app nova apontando
    # para o diretorio temporario.
    with TestClient(create_app()) as media_client:
        response = media_client.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == JPEG_BYTES

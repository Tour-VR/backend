from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.repositories.media_storage import MediaStorage
from app.services.media_service import (
    CHUNK_SIZE,
    MediaEmptyError,
    MediaService,
    MediaTooLargeError,
    MediaTypeError,
)

JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"0" * 100


class FakeUpload:
    """Simula o `UploadFile`, contando quantos bytes foram lidos."""

    def __init__(self, content: bytes) -> None:
        self.content = content
        self.position = 0

    async def read(self, size: int = -1) -> bytes:
        end = len(self.content) if size < 0 else self.position + size
        chunk = self.content[self.position : end]
        self.position += len(chunk)
        return chunk


def test_store_saves_jpeg_and_returns_relative_url(tmp_path: Path) -> None:
    service = MediaService(MediaStorage(tmp_path), max_bytes=1024)

    result = asyncio.run(service.store(FakeUpload(JPEG_BYTES)))

    assert result["content_type"] == "image/jpeg"
    assert result["size_bytes"] == len(JPEG_BYTES)
    url = str(result["url"])
    assert url.startswith("/media/") and url.endswith(".jpg")
    assert (tmp_path / url.removeprefix("/media/")).read_bytes() == JPEG_BYTES


def test_store_stops_reading_once_limit_is_passed(tmp_path: Path) -> None:
    upload = FakeUpload(b"\xff\xd8\xff" + b"0" * (CHUNK_SIZE * 3))
    service = MediaService(MediaStorage(tmp_path), max_bytes=CHUNK_SIZE)

    with pytest.raises(MediaTooLargeError, match=r"Arquivo maior que 1 MB."):
        asyncio.run(service.store(upload))

    assert upload.position == CHUNK_SIZE * 2
    assert list(tmp_path.iterdir()) == []


def test_store_rejects_empty_file(tmp_path: Path) -> None:
    service = MediaService(MediaStorage(tmp_path), max_bytes=1024)

    with pytest.raises(MediaEmptyError):
        asyncio.run(service.store(FakeUpload(b"")))


def test_store_rejects_non_image_content(tmp_path: Path) -> None:
    service = MediaService(MediaStorage(tmp_path), max_bytes=1024)

    with pytest.raises(MediaTypeError):
        asyncio.run(service.store(FakeUpload(b"texto qualquer")))

    assert list(tmp_path.iterdir()) == []


def test_storage_translates_disk_error(tmp_path: Path) -> None:
    blocked = tmp_path / "arquivo-no-lugar-do-diretorio"
    blocked.write_text("x")
    storage = MediaStorage(blocked)

    with pytest.raises(ConnectionError, match=r"Falha ao gravar o arquivo de midia."):
        storage.save(b"conteudo", "jpg")

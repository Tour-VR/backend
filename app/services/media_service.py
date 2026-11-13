"""Regras de negocio do envio de midia: tamanho, tipo real e gravacao."""

from __future__ import annotations

from typing import Protocol

from app.core.media_types import SIGNATURE_BYTES, detect_image_type
from app.repositories.media_storage import MediaStorage

CHUNK_SIZE = 1024 * 1024
BYTES_PER_MB = 1024 * 1024
MEDIA_URL_PREFIX = "/media"


class MediaTooLargeError(ValueError):
    """Arquivo maior que o limite configurado."""


class MediaTypeError(ValueError):
    """Conteudo que nao e JPEG, PNG nem WebP."""


class MediaEmptyError(ValueError):
    """Arquivo sem nenhum byte."""


class ReadableUpload(Protocol):
    """Parte do `UploadFile` usada pelo service (facilita testar sem HTTP)."""

    async def read(self, size: int = -1) -> bytes: ...


class MediaService:
    def __init__(self, storage: MediaStorage, max_bytes: int) -> None:
        self.storage = storage
        self.max_bytes = max_bytes

    async def _read_limited(self, upload: ReadableUpload) -> bytes:
        """Le em blocos e aborta assim que o limite e ultrapassado."""

        content = bytearray()
        while chunk := await upload.read(CHUNK_SIZE):
            content.extend(chunk)
            if len(content) > self.max_bytes:
                limit_mb = self.max_bytes // BYTES_PER_MB
                raise MediaTooLargeError(f"Arquivo maior que {limit_mb} MB.")
        return bytes(content)

    async def store(self, upload: ReadableUpload) -> dict[str, str | int]:
        """Valida e grava o arquivo, devolvendo a URL relativa de acesso."""

        content = await self._read_limited(upload)
        if not content:
            raise MediaEmptyError("Arquivo vazio.")

        detected = detect_image_type(content[:SIGNATURE_BYTES])
        if detected is None:
            raise MediaTypeError("Formato não suportado. Envie JPEG, PNG ou WebP.")
        content_type, extension = detected

        file_name = self.storage.save(content, extension)
        return {
            "url": f"{MEDIA_URL_PREFIX}/{file_name}",
            "content_type": content_type,
            "size_bytes": len(content),
        }

"""Repository de arquivos de midia gravados em disco."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4


class MediaStorage:
    """Grava arquivos no diretorio de midia com nome aleatorio `<uuid>.<ext>`."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def save(self, content: bytes, extension: str) -> str:
        """Grava o conteudo e devolve o nome do arquivo criado."""

        file_name = f"{uuid4().hex}.{extension}"
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            (self.base_dir / file_name).write_bytes(content)
        except OSError as exc:
            raise ConnectionError("Falha ao gravar o arquivo de midia.") from exc
        return file_name

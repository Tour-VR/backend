"""Deteccao do tipo de imagem pela assinatura dos primeiros bytes do arquivo.

A extensao e o `content_type` vem do cliente e podem mentir; a assinatura nao.
"""

from __future__ import annotations

JPEG_SIGNATURE = b"\xff\xd8\xff"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
RIFF_SIGNATURE = b"RIFF"
WEBP_MARKER = b"WEBP"
WEBP_MARKER_OFFSET = 8
SIGNATURE_BYTES = 12


def detect_image_type(header: bytes) -> tuple[str, str] | None:
    """Devolve (content_type, extensao) a partir dos primeiros bytes, ou None."""

    if header.startswith(JPEG_SIGNATURE):
        return "image/jpeg", "jpg"
    if header.startswith(PNG_SIGNATURE):
        return "image/png", "png"
    if (
        header.startswith(RIFF_SIGNATURE)
        and header[WEBP_MARKER_OFFSET:SIGNATURE_BYTES] == WEBP_MARKER
    ):
        return "image/webp", "webp"
    return None

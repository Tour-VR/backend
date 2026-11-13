from __future__ import annotations

import pytest

from app.core.media_types import detect_image_type


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01", ("image/jpeg", "jpg")),
        (b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0d", ("image/png", "png")),
        (b"RIFF\x24\x00\x00\x00WEBP", ("image/webp", "webp")),
    ],
)
def test_detect_image_type_recognizes_supported_formats(
    header: bytes, expected: tuple[str, str]
) -> None:
    assert detect_image_type(header) == expected


@pytest.mark.parametrize(
    "header",
    [
        b"isto nao e uma imagem",
        b"GIF89a\x01\x00\x01\x00\x00\x00",
        b"RIFF\x24\x00\x00\x00WAVE",
        b"",
    ],
)
def test_detect_image_type_rejects_other_content(header: bytes) -> None:
    assert detect_image_type(header) is None

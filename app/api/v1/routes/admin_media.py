"""Rota administrativa de envio de midia (somente papel admin)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.api.deps import build_database_http_exception, get_media_service, require_admin
from app.schemas.media import MediaUploadResponse
from app.services.media_service import (
    MediaEmptyError,
    MediaService,
    MediaTooLargeError,
    MediaTypeError,
)

router = APIRouter(prefix="/admin/media", tags=["Admin - Midia"])

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    MediaTooLargeError: status.HTTP_413_CONTENT_TOO_LARGE,
    MediaTypeError: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    MediaEmptyError: status.HTTP_400_BAD_REQUEST,
}


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MediaUploadResponse)
async def upload_media(
    file: UploadFile,
    _admin: dict[str, Any] = Depends(require_admin),
    service: MediaService = Depends(get_media_service),
) -> dict[str, str | int]:
    try:
        return await service.store(file)
    except (MediaTooLargeError, MediaTypeError, MediaEmptyError) as exc:
        raise HTTPException(status_code=_STATUS_BY_ERROR[type(exc)], detail=str(exc)) from exc
    except ConnectionError as exc:
        raise build_database_http_exception(exc) from exc

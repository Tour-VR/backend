"""Rotas de diagnostico basico da API."""

from fastapi import APIRouter, Depends

from app.core.database import MongoManager, get_mongo_manager

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health_check(
    mongo_manager: MongoManager = Depends(get_mongo_manager),
) -> dict[str, object]:
    database = await mongo_manager.get_health_status()
    overall_status = "ok" if database["status"] == "up" else "degraded"

    return {
        "status": overall_status,
        "api": {"status": "ok"},
        "database": database,
    }

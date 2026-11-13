"""Factory da aplicacao FastAPI."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pymongo.errors import PyMongoError

from app.api.v1.router import api_router
from app.core.config import ensure_secure_settings, settings
from app.core.database import MongoManager
from app.core.indexes import ensure_indexes
from app.core.logging import configure_logging
from app.core.rate_limit import LoginRateLimiter

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Cria a aplicacao e registra o ciclo de vida."""

    ensure_secure_settings(settings)
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        mongo_manager = MongoManager(
            mongodb_url=settings.mongodb_url,
            database_name=settings.mongodb_db,
        )
        app.state.mongo_manager = mongo_manager
        await mongo_manager.connect()
        if mongo_manager.connected and mongo_manager.database is not None:
            try:
                await ensure_indexes(mongo_manager.database)
            except PyMongoError as exc:
                logger.warning("Nao foi possivel criar os indices: %s", exc)
        try:
            yield
        finally:
            await mongo_manager.close()

    application = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version="1.0.0",
        lifespan=lifespan,
    )

    # O frontend roda em outra origem no desenvolvimento, entao liberamos
    # apenas os enderecos configurados para o navegador concluir login e /users/me.
    application.state.login_rate_limiter = LoginRateLimiter(
        settings.login_max_failures,
        settings.login_window_seconds,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router)

    # Montado depois das rotas para nao sombrea-las; StaticFiles exige o diretorio existente.
    media_path = Path(settings.media_dir)
    media_path.mkdir(parents=True, exist_ok=True)
    application.mount("/media", StaticFiles(directory=media_path), name="media")

    @application.get("/", tags=["Root"])
    async def root() -> dict[str, str]:
        return {
            "message": "Bem-vindo ao backend MVP",
            "docs": "/docs",
            "health": "/health/",
        }

    return application


app = create_app()

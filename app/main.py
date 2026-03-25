"""Factory da aplicacao FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import MongoManager


def create_app() -> FastAPI:
    """Cria a aplicacao e registra o ciclo de vida."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        mongo_manager = MongoManager(
            mongodb_url=settings.mongodb_url,
            database_name=settings.mongodb_db,
        )
        app.state.mongo_manager = mongo_manager
        await mongo_manager.connect()
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
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router)

    @application.get("/", tags=["Root"])
    async def root() -> dict[str, str]:
        return {
            "message": "Bem-vindo ao backend MVP",
            "docs": "/docs",
            "health": "/health/",
        }

    return application


app = create_app()

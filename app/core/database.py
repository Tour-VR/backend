"""Gerencia a conexao com MongoDB sem impedir a API de subir."""

from __future__ import annotations

import inspect
from typing import Any

from fastapi import Request
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from app.core.config import settings


class MongoManager:
    """Encapsula a conexao e o estado atual do MongoDB."""

    def __init__(self, mongodb_url: str, database_name: str) -> None:
        self.mongodb_url = mongodb_url
        self.database_name = database_name
        self.client: AsyncMongoClient[Any] | None = None
        self.database: Any | None = None
        self.connected = False
        self.initialized = False
        self.last_error: str | None = None

    async def connect(self) -> None:
        """Prepara o client e tenta um ping inicial."""

        self.initialized = True

        if self._has_placeholder_credentials():
            self.connected = False
            self.last_error = (
                "A URL do MongoDB ainda contem um placeholder de senha. "
                "Substitua `<db_password>` pela senha real do usuario Atlas."
            )
            return

        try:
            self.client = AsyncMongoClient(
                self.mongodb_url,
                serverSelectionTimeoutMS=1500,
            )
            self.database = self.client[self.database_name]
            await self.ping()
        except PyMongoError as exc:
            self.connected = False
            self.last_error = self._format_connection_error(str(exc))

    async def ping(self) -> bool:
        """Testa a conexao atual com um ping curto."""

        if self.client is None:
            self.connected = False
            self.last_error = "MongoDB client ainda nao foi inicializado."
            return False

        try:
            await self.client.admin.command("ping")
            self.connected = True
            self.last_error = None
            return True
        except PyMongoError as exc:
            self.connected = False
            self.last_error = self._format_connection_error(str(exc))
            return False

    async def close(self) -> None:
        """Fecha o client sem assumir se a implementacao e sync ou async."""

        if self.client is not None:
            close_result = self.client.close()
            if inspect.isawaitable(close_result):
                await close_result

        self.client = None
        self.database = None
        self.connected = False

    async def get_health_status(self) -> dict[str, str | bool]:
        """Retorna um resumo amigavel para o endpoint de health."""

        if not self.initialized:
            return {
                "status": "down",
                "connected": False,
                "database": self.database_name,
                "detail": "MongoDB ainda nao foi inicializado no ciclo de vida da API.",
            }

        if self.client is not None:
            await self.ping()

        return {
            "status": "up" if self.connected else "down",
            "connected": self.connected,
            "database": self.database_name,
            "detail": self.last_error or "MongoDB conectado com sucesso.",
        }

    def _has_placeholder_credentials(self) -> bool:
        """Detecta placeholders comuns em strings de conexao."""

        placeholder_tokens = ("<db_password>", "<password>", "SUA_SENHA")
        return any(token in self.mongodb_url for token in placeholder_tokens)

    def _format_connection_error(self, error_message: str) -> str:
        """Traduz erros comuns para mensagens mais claras."""

        lowered_error = error_message.lower()
        if "bad auth" in lowered_error or "authentication failed" in lowered_error:
            return (
                "Falha de autenticacao no MongoDB Atlas. Confira usuario, senha "
                "e se caracteres especiais da senha foram codificados na URL."
            )
        return error_message


def get_mongo_manager(request: Request) -> MongoManager:
    """Recupera o gerenciador salvo no estado da aplicacao."""

    manager = getattr(request.app.state, "mongo_manager", None)
    if manager is None:
        manager = MongoManager(
            mongodb_url=settings.mongodb_url,
            database_name=settings.mongodb_db,
        )
        request.app.state.mongo_manager = manager
    return manager


def get_database(request: Request) -> Any | None:
    """Atalho para futuras camadas de repository."""

    return get_mongo_manager(request).database

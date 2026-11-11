"""Configuracao central carregada a partir do arquivo `.env`."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET_KEY = "troque_esta_chave"


class Settings(BaseSettings):
    """Valores usados pelo restante da aplicacao."""

    app_name: str = "Meu Backend MVP"
    app_env: str = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "meu_backend_db"

    jwt_secret_key: str = DEFAULT_JWT_SECRET_KEY
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    log_level: str = "INFO"
    login_max_failures: int = 5
    login_window_seconds: int = 900

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Converte a string do `.env` em lista para o middleware de CORS."""

        return [origin.strip() for origin in self.app_cors_origins.split(",") if origin.strip()]


class InsecureConfigurationError(RuntimeError):
    """Configuracao que nao pode ser usada fora do ambiente de desenvolvimento."""


def ensure_secure_settings(current: Settings) -> None:
    """Recusa subir com a chave JWT padrao fora de development."""

    if current.app_env != "development" and current.jwt_secret_key == DEFAULT_JWT_SECRET_KEY:
        raise InsecureConfigurationError(
            "JWT_SECRET_KEY nao foi configurada. Gere uma chave com "
            'python -c "import secrets; print(secrets.token_hex(32))" e defina no .env.'
        )


settings = Settings()

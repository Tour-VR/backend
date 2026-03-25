"""Configuracao central carregada a partir do arquivo `.env`."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores usados pelo restante da aplicacao."""

    app_name: str = "Meu Backend MVP"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "meu_backend_db"

    jwt_secret_key: str = "troque_esta_chave"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Converte a string do `.env` em lista para o middleware de CORS."""

        return [
            origin.strip()
            for origin in self.app_cors_origins.split(",")
            if origin.strip()
        ]


settings = Settings()

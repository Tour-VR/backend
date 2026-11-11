from __future__ import annotations

import pytest

from app.core.config import (
    DEFAULT_JWT_SECRET_KEY,
    InsecureConfigurationError,
    Settings,
    ensure_secure_settings,
)


def test_ensure_secure_settings_rejects_default_secret_outside_development() -> None:
    current = Settings(app_env="production", jwt_secret_key=DEFAULT_JWT_SECRET_KEY)

    with pytest.raises(InsecureConfigurationError, match=r"secrets.token_hex"):
        ensure_secure_settings(current)


def test_ensure_secure_settings_accepts_default_secret_in_development() -> None:
    current = Settings(app_env="development", jwt_secret_key=DEFAULT_JWT_SECRET_KEY)

    ensure_secure_settings(current)


def test_ensure_secure_settings_accepts_custom_secret_in_production() -> None:
    current = Settings(app_env="production", jwt_secret_key="chave-forte-de-teste")

    ensure_secure_settings(current)


def test_app_debug_defaults_to_false() -> None:
    assert Settings.model_fields["app_debug"].default is False

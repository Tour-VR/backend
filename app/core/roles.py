"""Papeis de usuario reconhecidos pelo sistema."""

from __future__ import annotations

ROLE_ADMIN = "admin"
ROLE_USER = "user"
VALID_ROLES: frozenset[str] = frozenset({ROLE_ADMIN, ROLE_USER})

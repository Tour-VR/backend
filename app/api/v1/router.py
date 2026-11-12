"""Roteador principal da API v1: agrega health, auth, users e pontos."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes.admin_points import router as admin_points_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.public_points import router as public_points_router
from app.api.v1.routes.users import router as users_router

# ---------------------------------------------------
# ROTEADOR PRINCIPAL DA V1
# ---------------------------------------------------
api_router = APIRouter()

# rota de health check
api_router.include_router(health_router)

# rotas de autenticação: register e login
api_router.include_router(auth_router)

# rotas de usuário, incluindo /users/me
api_router.include_router(users_router)

# rotas administrativas de pontos de interesse (papel admin)
api_router.include_router(admin_points_router)

# rotas publicas de leitura de pontos (sem token)
api_router.include_router(public_points_router)

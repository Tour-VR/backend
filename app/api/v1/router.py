from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.health import router as health_router
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
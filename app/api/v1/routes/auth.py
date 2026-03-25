from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import build_database_http_exception, get_user_service
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserRegisterResponse
from app.services.user_service import (
    AuthenticationError,
    UserConflictError,
    UserInputError,
    UserService,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRegisterResponse)
async def register(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
):
    """Cria um novo usuario mantendo o contrato atual da rota."""

    try:
        return await service.register_user(payload)
    except (UserConflictError, UserInputError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ConnectionError as exc:
        raise build_database_http_exception(exc) from exc


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLogin,
    service: UserService = Depends(get_user_service),
):
    """Valida as credenciais e devolve o token Bearer."""

    try:
        return await service.login_user(payload)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except ConnectionError as exc:
        raise build_database_http_exception(exc) from exc

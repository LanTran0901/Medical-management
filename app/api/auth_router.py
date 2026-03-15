from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
import uuid

from app.application.dtos.auth_dto import (
    LoginRequest, GoogleLoginRequest, TokenResponse, 
    ChangePasswordRequest, RefreshTokenRequest,
    ForgotPasswordRequest, ResetPasswordRequest, ForgotPasswordResponse,
    LogoutRequest
)
from app.application.dtos.user_dto import CreateUserRequest, UserResponse
from app.application.usecases.auth_usecases import (
    RegisterUseCase, LoginUseCase, GoogleLoginUseCase, 
    ChangePasswordUseCase, RefreshTokenUseCase,
    ForgotPasswordUseCase, ResetPasswordUseCase, LogoutUseCase
)
from app.infrastructure.config.database.postgres.connection import get_session
from app.infrastructure.repositories.user_repository_pg import UserRepositoryPG
from app.infrastructure.repositories.auth_repository_pg import AuthRepositoryPG
from app.api.dependencies import get_current_user
from app.domain.entities.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

def get_user_repository(session: AsyncSession = Depends(get_session)) -> UserRepositoryPG:
    return UserRepositoryPG(session)

def get_auth_repository(session: AsyncSession = Depends(get_session)) -> AuthRepositoryPG:
    return AuthRepositoryPG(session)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: CreateUserRequest,
    user_repo: UserRepositoryPG = Depends(get_user_repository),
) -> UserResponse:
    try:
        user = await RegisterUseCase(user_repo).execute(payload)
        return UserResponse.from_entity(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    user_repo: UserRepositoryPG = Depends(get_user_repository),
    auth_repo: AuthRepositoryPG = Depends(get_auth_repository),
) -> TokenResponse:
    try:
        return await LoginUseCase(user_repo, auth_repo).execute(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

@router.post("/login/swagger", response_model=TokenResponse)
async def login_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repo: UserRepositoryPG = Depends(get_user_repository),
    auth_repo: AuthRepositoryPG = Depends(get_auth_repository),
) -> TokenResponse:
    # A quick adaptation for Swagger UI's "Authorize" button
    # device_id dùng sentinel cố định cho Swagger UI (không phải thiết bị thật)
    login_request = LoginRequest(
        email=form_data.username,
        password=form_data.password,
        device_id="swagger-ui",
    )
    try:
        return await LoginUseCase(user_repo, auth_repo).execute(login_request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

@router.post("/google", response_model=TokenResponse)
async def google_login(
    payload: GoogleLoginRequest,
    user_repo: UserRepositoryPG = Depends(get_user_repository),
    auth_repo: AuthRepositoryPG = Depends(get_auth_repository),
) -> TokenResponse:
    try:
        return await GoogleLoginUseCase(user_repo, auth_repo).execute(payload)
    except NotImplementedError as e:
         raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    auth_repo: AuthRepositoryPG = Depends(get_auth_repository),
) -> TokenResponse:
    try:
        return await RefreshTokenUseCase(auth_repo).execute(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    user_repo: UserRepositoryPG = Depends(get_user_repository),
):
    try:
        await ChangePasswordUseCase(user_repo).execute(user.id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return None

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    user_repo: UserRepositoryPG = Depends(get_user_repository),
) -> ForgotPasswordResponse:
    try:
        return await ForgotPasswordUseCase(user_repo).execute(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    payload: ResetPasswordRequest,
    reset_token: str,
    user_repo: UserRepositoryPG = Depends(get_user_repository),
):
    try:
        await ResetPasswordUseCase(user_repo).execute(reset_token, payload)
    except ValueError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return None

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    user: User = Depends(get_current_user),
    auth_repo: AuthRepositoryPG = Depends(get_auth_repository),
):
    try:
        await LogoutUseCase(auth_repo).execute(user.id, payload)
    except ValueError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return None

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import secrets

from app.application.dtos.auth_dto import (
    LoginRequest, GoogleLoginRequest, TokenResponse, 
    ChangePasswordRequest, RefreshTokenRequest, 
    ForgotPasswordRequest, ResetPasswordRequest, ForgotPasswordResponse,
    LogoutRequest
)
from app.application.dtos.user_dto import CreateUserRequest
from app.application.ports.user_port import UserRepositoryPort
from app.application.ports.auth_port import AuthRepositoryPort
from app.domain.entities.user import User
from app.domain.entities.auth import UserDevice, RefreshToken
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token_string, decode_token
from app.core.email import send_otp_email
import random
import jwt
from fastapi import HTTPException

class RegisterUseCase:
    def __init__(self, user_repository: UserRepositoryPort):
        self.user_repository = user_repository

    async def execute(self, request: CreateUserRequest) -> User:
        existing_user = await self.user_repository.get_by_email(request.email)
        if existing_user is not None:
            raise ValueError("User with this email already exists.")

        user = User.create(
            email=request.email,
            full_name=request.full_name,
            dob=request.dob,
            gender=request.gender,
            avatar_url=request.avatar_url,
            password_hash=get_password_hash(request.password_hash) if request.password_hash else None,
        )
        return await self.user_repository.create(user)

class LoginUseCase:
    def __init__(self, user_repository: UserRepositoryPort, auth_repository: AuthRepositoryPort):
        self.user_repository = user_repository
        self.auth_repository = auth_repository

    async def execute(self, request: LoginRequest) -> TokenResponse:
        user = await self.user_repository.get_by_email(request.email)
        if not user or not user.is_active or not user.password_hash:
            raise ValueError("Incorrect email or password")
        
        if not verify_password(request.password, user.password_hash):
            raise ValueError("Incorrect email or password")

        return await _generate_tokens(
            user.id, request.device_id, request.device_name, request.platform, request.fcm_token, self.auth_repository
        )

# For Google Login, we verify the google_token via google-auth library
class GoogleLoginUseCase:
    def __init__(self, user_repository: UserRepositoryPort, auth_repository: AuthRepositoryPort):
        self.user_repository = user_repository
        self.auth_repository = auth_repository

    async def execute(self, request: GoogleLoginRequest) -> TokenResponse:
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests
        except ImportError:
            raise NotImplementedError("Google token verification requires google-auth library")

        from app.core.config import settings
        if not settings.google_client_id:
            raise ValueError("Valid CLIENT_ID is required for Google login")

        try:
            id_info = id_token.verify_oauth2_token(
                request.google_token, requests.Request(), settings.google_client_id
            )
        except ValueError as e:
            raise ValueError(f"Invalid Google token: {str(e)}")

        email = id_info.get("email")
        google_id = id_info.get("sub")
        
        if not email or not google_id:
            raise ValueError("Google token missing required profile information")

        user = await self.user_repository.get_by_email(email)

        if user:
            # ACCOUNT LINKING: User exists, just link the google_id if not already linked
            if not user.google_id:
                user.google_id = google_id
                await self.user_repository.update(user)
        else:
            # CREATE NEW: User doesn't exist, create a new user without password
            user = User.create(
                email=email,
                google_id=google_id,
                full_name=id_info.get("name"),
                avatar_url=id_info.get("picture")
            )
            user = await self.user_repository.create(user)

        if not user.is_active:
            raise ValueError("User account is inactive.")

        return await _generate_tokens(
            user.id, request.device_id, request.device_name, request.platform, request.fcm_token, self.auth_repository
        )

class ChangePasswordUseCase:
    def __init__(self, user_repository: UserRepositoryPort):
        self.user_repository = user_repository

    async def execute(self, user_id: uuid.UUID, request: ChangePasswordRequest) -> None:
        user = await self.user_repository.get_by_id(user_id)
        if not user or not user.is_active:
            raise ValueError("User not found")
        
        if not user.password_hash or not verify_password(request.old_password, user.password_hash):
            raise ValueError("Incorrect old password")
        
        user.password_hash = get_password_hash(request.new_password)
        await self.user_repository.update(user)

class RefreshTokenUseCase:
    def __init__(self, auth_repository: AuthRepositoryPort):
        self.auth_repository = auth_repository

    async def execute(self, request: RefreshTokenRequest) -> TokenResponse:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise ValueError("Invalid payload")
        user_id = uuid.UUID(user_id_str)

        jti = payload.get("jti")
        token_record = await self.auth_repository.get_refresh_token(jti)
        if not token_record or not token_record.is_valid:
            raise ValueError("Refresh token revoked or expired")
        
        # Revoke old token
        token_record.revoke()
        await self.auth_repository.update_refresh_token(token_record)

        # Lấy device_id từ payload của refresh token
        device_id = payload.get("device_id")
        if not device_id:
            raise ValueError("Refresh token missing device_id claim")

        # Lấy thông tin thiết bị hiện tại để giữ nguyên device_name, platform, fcm_token
        device = await self.auth_repository.get_device(device_id, user_id)

        return await _generate_tokens(
            user_id,
            device_id,
            device.device_name if device else None,
            device.platform if device else None,
            device.fcm_token if device else None,
            self.auth_repository
        )

async def _generate_tokens(
    user_id: uuid.UUID, 
    device_id: str,
    device_name: str | None, 
    platform: str | None, 
    fcm_token: str | None, 
    auth_repository: AuthRepositoryPort,
) -> TokenResponse:
    # 1. Update or create device based on composite key (device_id, user_id)
    device = await auth_repository.get_device(device_id, user_id)
    if device:
        device.update_activity(fcm_token)
        device = await auth_repository.update_device(device)
    else:
        device = UserDevice.create(device_id, user_id, fcm_token, device_name, platform)
        device = await auth_repository.create_device(device)

    # 2. Access Token
    access_token_expires = 60 # minutes
    access_token = create_access_token(
        data={"sub": str(user_id), "device_id": device_id}
    )

    # 3. Refresh Token
    jti = secrets.token_hex(16)
    refresh_token_jwt = create_refresh_token_string(
        data={"sub": str(user_id), "jti": jti, "device_id": device_id}
    )
    
    expires_at = datetime.now(timezone.utc)
    # Using hardcoded import or from settings
    from app.core.config import settings
    from datetime import timedelta
    expires_at = expires_at + timedelta(days=settings.refresh_token_expire_days)

    refresh_token = RefreshToken.create(
        user_id=user_id,
        token_hash=jti, # We store jti as token_hash for lookup
        expires_at=expires_at,
        device_id=device_id
    )
    await auth_repository.create_refresh_token(refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_jwt,
        expires_in=access_token_expires * 60
    )


class ForgotPasswordUseCase:
    def __init__(self, user_repository: UserRepositoryPort):
        self.user_repository = user_repository

    async def execute(self, request: ForgotPasswordRequest) -> ForgotPasswordResponse:
        user = await self.user_repository.get_by_email(request.email)
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        # Sinh mã OTP 6 chữ số
        otp_code = f"{random.randint(100000, 999999)}"
        
        # Băm OTP
        otp_hash = get_password_hash(otp_code)

        # Gửi email chứa OTP cho User (giả lập mock smtp)
        await send_otp_email(user.email, otp_code)

        # Tạo Stateless Reset Token mang hash của OTP và email
        from app.core.config import settings
        from datetime import timedelta
        expire = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        to_encode = {
            "sub": user.email,
            "type": "reset_password",
            "otp_hash": otp_hash,
            "exp": expire
        }
        reset_token = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        # Trả JWT Token này cho Client.
        return ForgotPasswordResponse(
            message="OTP has been sent to your email.",
            reset_token=reset_token
        )


class ResetPasswordUseCase:
    def __init__(self, user_repository: UserRepositoryPort):
        self.user_repository = user_repository

    async def execute(self, reset_token: str, request: ResetPasswordRequest) -> None:
        try:
            payload = decode_token(reset_token)
            if payload.get("type") != "reset_password":
                raise ValueError("Invalid token type")
            
            token_email = payload.get("sub")
            if not token_email or token_email != request.email:
                raise ValueError("Email does not match the token")

            otp_hash = payload.get("otp_hash")
            if not otp_hash or not verify_password(request.otp_code, otp_hash):
                raise ValueError("Invalid or expired OTP")
                
        except Exception as e:
            raise ValueError(f"Invalid or expired Reset Token: {str(e)}")

        # OTP verified, change password
        user = await self.user_repository.get_by_email(request.email)
        if not user or not user.is_active:
             raise ValueError("User not found or inactive")

        user.password_hash = get_password_hash(request.new_password)
        await self.user_repository.update(user)

class LogoutUseCase:
    def __init__(self, auth_repository: AuthRepositoryPort):
        self.auth_repository = auth_repository

    async def execute(self, user_id: uuid.UUID, request: LogoutRequest) -> None:
        try:
            payload = decode_token(request.refresh_token)
            if payload.get("type") != "refresh":
                pass
            
            jti = payload.get("jti")
            if jti:
                token_record = await self.auth_repository.get_refresh_token(jti)
                if token_record and token_record.is_valid:
                    token_record.revoke()
                    await self.auth_repository.update_refresh_token(token_record)
        except Exception:
            # If the token is already expired or invalid, we still want to proceed to clear the FCM token
            pass

        # Find the device and clear FCM token to prevent ghost notifications
        device = await self.auth_repository.get_device(request.device_id, user_id)
        if device:
            device.fcm_token = None
            await self.auth_repository.update_device(device)

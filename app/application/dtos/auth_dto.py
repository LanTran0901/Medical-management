from __future__ import annotations

import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


E164_PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")


class RegisterRequest(BaseModel):
    """Public registration — plain password at API boundary; hashed in RegisterUseCase."""

    email: str
    phone_number: str = Field(..., min_length=8, max_length=16)
    password: str = Field(..., min_length=6)
    google_id: Optional[str] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        normalized = value.strip()
        if not E164_PHONE_RE.fullmatch(normalized):
            raise ValueError("phone_number must be valid E.164 format (e.g. +84901234567)")
        return normalized


class LoginRequest(BaseModel):
    email: str
    password: str
    device_id: str = Field(..., min_length=1, description="ID định danh thiết bị, không được để trống")
    device_name: Optional[str] = None
    platform: Optional[str] = None
    fcm_token: Optional[str] = None

class GoogleLoginRequest(BaseModel):
    google_token: str
    device_id: str = Field(..., min_length=1, description="ID định danh thiết bị, không được để trống")
    device_name: Optional[str] = None
    platform: Optional[str] = None
    fcm_token: Optional[str] = None

class UpdateDeviceTokenRequest(BaseModel):
    device_id: str = Field(..., min_length=1, description="ID thiet bi can cap nhat token")
    fcm_token: Optional[str] = None
    device_name: Optional[str] = None
    platform: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str

class ResetPasswordRequest(BaseModel):
    email: str
    otp_code: str
    new_password: str = Field(..., min_length=6)

class LogoutRequest(BaseModel):
    refresh_token: str
    device_id: str

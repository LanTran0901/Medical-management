from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

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

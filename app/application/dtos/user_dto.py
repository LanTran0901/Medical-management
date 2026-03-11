from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.entities.user import User, UserStatus


class CreateUserRequest(BaseModel):
    email: str
    full_name: str | None = None
    avatar_url: str | None = None
    password_hash: str | None = None
    google_id: str | None = None
    apple_id: str | None = None


class UpdateUserRequest(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None
    password_hash: str | None = None
    google_id: str | None = None
    apple_id: str | None = None
    status: UserStatus | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    status: UserStatus
    created_at: datetime
    full_name: str | None = None
    avatar_url: str | None = None
    google_id: str | None = None
    apple_id: str | None = None
    deleted_at: datetime | None = None

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            status=user.status,
            created_at=user.created_at,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            google_id=user.google_id,
            apple_id=user.apple_id,
            deleted_at=user.deleted_at,
        )
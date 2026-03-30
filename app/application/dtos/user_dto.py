from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.user import User, UserStatus


class UpdateUserRequest(BaseModel):
    password_hash: str | None = None
    google_id: str | None = None
    status: UserStatus | None = None
    phone_number: str | None = None


class PatchUserMeRequest(BaseModel):
    """PATCH /users/me — scoped fields for the authenticated user."""

    phone_number: str | None = Field(default=None, max_length=64)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    status: UserStatus
    created_at: datetime
    google_id: str | None = None
    phone_number: str | None = None
    deleted_at: datetime | None = None

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            status=user.status,
            created_at=user.created_at,
            google_id=user.google_id,
            phone_number=user.phone_number,
            deleted_at=user.deleted_at,
        )

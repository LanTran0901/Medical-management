from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.entities.user import User, UserStatus


class CreateUserRequest(BaseModel):
    email: str
    password_hash: str
    google_id: str | None = None


class UpdateUserRequest(BaseModel):
    password_hash: str | None = None
    google_id: str | None = None
    status: UserStatus | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    status: UserStatus
    created_at: datetime
    google_id: str | None = None
    deleted_at: datetime | None = None

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            status=user.status,
            created_at=user.created_at,
            google_id=user.google_id,
            deleted_at=user.deleted_at,
        )

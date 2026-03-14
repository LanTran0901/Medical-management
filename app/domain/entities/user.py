from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from enum import Enum
from typing import Optional


class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    banned = "banned"


@dataclass
class User:

    id: uuid.UUID
    email: str
    status: UserStatus
    created_at: datetime
    full_name: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    avatar_url: Optional[str] = None
    password_hash: Optional[str] = None
    google_id: Optional[str] = None
    apple_id: Optional[str] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.active and self.deleted_at is None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        if self.is_deleted:
            raise ValueError("User is already deleted.")
        self.deleted_at = datetime.now(timezone.utc)
        self.status = UserStatus.inactive

    def has_social_login(self) -> bool:
        return bool(self.google_id or self.apple_id)

    # ── Factory ───────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        email: str,
        *,
        full_name: Optional[str] = None,
        dob: Optional[date] = None,
        gender: Optional[str] = None,
        avatar_url: Optional[str] = None,
        password_hash: Optional[str] = None,
        google_id: Optional[str] = None,
        apple_id: Optional[str] = None,
    ) -> "User":
        return cls(
            id=uuid.uuid4(),
            email=email.lower().strip(),
            status=UserStatus.active,
            created_at=datetime.now(timezone.utc),
            full_name=full_name,
            dob=dob,
            gender=gender,
            avatar_url=avatar_url,
            password_hash=password_hash,
            google_id=google_id,
            apple_id=apple_id,
        )

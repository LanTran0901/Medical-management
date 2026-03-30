from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
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
    password_hash: Optional[str] = None
    google_id: Optional[str] = None
    phone_number: Optional[str] = None
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
        return bool(self.google_id)

    # ── Factory ───────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        email: str,
        *,
        password_hash: Optional[str] = None,
        google_id: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> "User":
        return cls(
            id=uuid.uuid4(),
            email=email.lower().strip(),
            status=UserStatus.active,
            created_at=datetime.now(timezone.utc),
            password_hash=password_hash,
            google_id=google_id,
            phone_number=phone_number.strip() if phone_number else None,
        )

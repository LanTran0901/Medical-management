from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class UserDevice:
    device_id: str
    user_id: uuid.UUID
    fcm_token: Optional[str] = None
    device_name: Optional[str] = None
    platform: Optional[str] = None
    last_active: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        device_id: str,
        user_id: uuid.UUID,
        fcm_token: Optional[str] = None,
        device_name: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> "UserDevice":
        return cls(
            device_id=device_id,
            user_id=user_id,
            fcm_token=fcm_token,
            device_name=device_name,
            platform=platform,
            last_active=datetime.now(timezone.utc),
        )

    def update_activity(self, fcm_token: Optional[str] = None) -> None:
        self.last_active = datetime.now(timezone.utc)
        if fcm_token is not None:
            self.fcm_token = fcm_token


@dataclass
class RefreshToken:
    id: uuid.UUID
    user_id: uuid.UUID
    token_hash: str
    expires_at: datetime
    is_revoked: bool
    created_at: datetime
    device_id: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_revoked and not self.is_expired

    def revoke(self) -> None:
        self.is_revoked = True

    @classmethod
    def create(
        cls,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        device_id: Optional[str] = None,
    ) -> "RefreshToken":
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
            created_at=datetime.now(timezone.utc),
            device_id=device_id,
        )

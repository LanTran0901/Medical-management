from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class ProfileKind(StrEnum):
    """Logical kind; not a DB column — derived from linked_user_id / owner."""

    PERSONAL = "PERSONAL"
    VIRTUAL = "VIRTUAL"


class ProfileStatus(StrEnum):
    """FR-004 — must match PostgreSQL enum `profile_status`."""

    SHADOW = "SHADOW"
    PENDING_LINK = "PENDING_LINK"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass(frozen=True, slots=True)
class Profile:
    id: UUID
    owner_user_id: UUID
    linked_user_id: UUID | None
    full_name: str
    dob: date | None
    gender: str | None
    height_cm: Decimal | None
    weight_kg: Decimal | None
    address: str | None
    avatar_url: str | None
    status: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class FamilyRole(StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class FamilyInviteStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class FamilyPublicInviteStatus(StrEnum):
    PENDING = "PENDING"
    CONSUMED = "CONSUMED"
    REVOKED = "REVOKED"


@dataclass(frozen=True, slots=True)
class Family:
    id: UUID
    family_name: str
    invite_code: str
    created_at: datetime
    created_by: UUID | None = None
    address: str | None = None
    avatar_url: str | None = None


@dataclass(frozen=True, slots=True)
class FamilyMembership:
    id: UUID
    family_id: UUID
    profile_id: UUID
    role: FamilyRole
    added_by: UUID
    created_at: datetime
    relation_role: str | None = None


@dataclass(frozen=True, slots=True)
class FamilyInvite:
    id: UUID
    family_id: UUID
    role: FamilyRole
    status: FamilyInviteStatus
    invited_by: UUID
    invited_at: datetime
    phone_number: str | None = None
    user_id: UUID | None = None
    relation_role: str | None = None
    responded_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PublicInvitePreview:
    """Public deep-link preview; valid=False when expired, consumed, or revoked."""

    family_id: UUID
    family_name: str
    invite_code: str
    valid: bool
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class FamilyInviteInboxItem:
    invite: FamilyInvite
    family_name: str
    family_avatar_url: str | None
    family_member_count: int
    inviter_name: str | None
    inviter_role: FamilyRole | None

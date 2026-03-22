from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class FamilyRole(StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


@dataclass(frozen=True, slots=True)
class Family:
    id: UUID
    family_name: str
    invite_code: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class FamilyMembership:
    id: UUID
    family_id: UUID
    profile_id: UUID
    role: FamilyRole
    added_by: UUID
    created_at: datetime

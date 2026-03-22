from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.family import Family, FamilyMembership, FamilyRole
from app.domain.entities.health_detail import HealthDetail
from app.domain.entities.profile import Profile


class CreateFamilyRequest(BaseModel):
    family_name: str = Field(..., min_length=1, max_length=255)
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name for creator's personal profile in this family",
    )


class JoinFamilyRequest(BaseModel):
    invite_code: str = Field(..., min_length=1, max_length=64)
    full_name: str | None = Field(
        None,
        max_length=255,
        description="Required when creating a new personal profile (no linked_user row yet)",
    )


class PatchFamilyRequest(BaseModel):
    family_name: str = Field(..., min_length=1, max_length=255)


class PatchMembershipRoleRequest(BaseModel):
    role: FamilyRole


class CreateProfileInFamilyRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    owner_user_id: UUID
    role: FamilyRole = FamilyRole.MEMBER
    dob: date | None = None
    gender: str | None = None


class PatchProfileRequest(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    dob: date | None = None
    gender: str | None = None
    height_cm: Decimal | None = None
    weight_kg: Decimal | None = None
    address: str | None = None
    avatar_url: str | None = None
    status: str | None = None


class LinkProfileRequest(BaseModel):
    user_id: UUID


class HealthDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile_id: UUID
    blood_type: str | None
    chronic_diseases: list[str] | None
    allergies: list[str] | None
    emergency_contact: str | None
    notes: str | None
    updated_at: datetime

    @classmethod
    def from_entity(cls, e: HealthDetail) -> HealthDetailResponse:
        return cls(
            profile_id=e.profile_id,
            blood_type=e.blood_type,
            chronic_diseases=e.chronic_diseases,
            allergies=e.allergies,
            emergency_contact=e.emergency_contact,
            notes=e.notes,
            updated_at=e.updated_at,
        )


class PatchHealthDetailRequest(BaseModel):
    blood_type: str | None = None
    chronic_diseases: list[str] | None = None
    allergies: list[str] | None = None
    emergency_contact: str | None = None
    notes: str | None = None


class FamilyResponse(BaseModel):
    id: UUID
    family_name: str
    invite_code: str
    created_at: datetime

    @classmethod
    def from_entity(cls, f: Family) -> FamilyResponse:
        return cls(
            id=f.id,
            family_name=f.family_name,
            invite_code=f.invite_code,
            created_at=f.created_at,
        )


class FamilySummaryResponse(BaseModel):
    """List item — omit invite_code for non-owners if desired later."""

    id: UUID
    family_name: str
    invite_code: str
    created_at: datetime

    @classmethod
    def from_entity(cls, f: Family) -> FamilySummaryResponse:
        return cls(
            id=f.id,
            family_name=f.family_name,
            invite_code=f.invite_code,
            created_at=f.created_at,
        )


class MembershipResponse(BaseModel):
    id: UUID
    family_id: UUID
    profile_id: UUID
    role: FamilyRole
    added_by: UUID
    created_at: datetime
    profile_full_name: str | None = None
    linked_user_id: UUID | None = None

    @classmethod
    def from_entity(
        cls,
        m: FamilyMembership,
        profile_full_name: str | None = None,
        linked_user_id: UUID | None = None,
    ) -> MembershipResponse:
        return cls(
            id=m.id,
            family_id=m.family_id,
            profile_id=m.profile_id,
            role=m.role,
            added_by=m.added_by,
            created_at=m.created_at,
            profile_full_name=profile_full_name,
            linked_user_id=linked_user_id,
        )


class ProfileResponse(BaseModel):
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

    @classmethod
    def from_entity(cls, p: Profile) -> ProfileResponse:
        return cls(
            id=p.id,
            owner_user_id=p.owner_user_id,
            linked_user_id=p.linked_user_id,
            full_name=p.full_name,
            dob=p.dob,
            gender=p.gender,
            height_cm=p.height_cm,
            weight_kg=p.weight_kg,
            address=p.address,
            avatar_url=p.avatar_url,
            status=p.status,
            created_at=p.created_at,
            updated_at=p.updated_at,
            deleted_at=p.deleted_at,
        )


class CreateFamilyResponse(BaseModel):
    family: FamilyResponse
    profile: ProfileResponse
    membership: MembershipResponse

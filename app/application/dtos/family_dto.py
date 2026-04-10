from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.entities.family import Family, FamilyInvite, FamilyInviteInboxItem, FamilyMembership, FamilyRole
from app.domain.entities.health_detail import HealthDetail
from app.domain.entities.profile import Profile, ProfileStatus


E164_PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")
FAMILY_PERMISSION_ROLE_VALUES = {role.value for role in FamilyRole}


def _coerce_relation_role_payload(value: object) -> object:
    if not isinstance(value, dict):
        return value
    data = dict(value)
    raw_role = data.get("role")
    if isinstance(raw_role, str):
        normalized = raw_role.strip()
        if normalized:
            upper = normalized.upper()
            if upper in FAMILY_PERMISSION_ROLE_VALUES:
                data["role"] = upper
            else:
                data.setdefault("relation_role", normalized)
                data["role"] = FamilyRole.MEMBER.value
    return data


class CreateFamilyRequest(BaseModel):
    name: str = Field(
        validation_alias=AliasChoices("name", "family_name"),
        min_length=1,
        max_length=255,
    )
    owner_profile_full_name: str = Field(
        validation_alias=AliasChoices("owner_profile_full_name", "full_name"),
        min_length=1,
        max_length=255,
        description="Display name for creator's personal profile in this family",
    )
    address: str | None = None
    avatar_url: str | None = None


class JoinFamilyRequest(BaseModel):
    invite_code: str | None = Field(None, min_length=1, max_length=64)
    profile_id: UUID | None = Field(
        None,
        description="Optional linked profile to use for the membership when user has multiple profiles",
    )
    full_name: str | None = Field(
        None,
        max_length=255,
        description="Required when creating a new personal profile (no linked_user row yet)",
    )
    action: Literal["accept", "reject"] | None = None
    invite_id: UUID | None = None

    @model_validator(mode="after")
    def validate_mode(self) -> JoinFamilyRequest:
        by_code = self.invite_code is not None
        by_action = self.action is not None or self.invite_id is not None
        if by_code and by_action:
            raise ValueError("Provide either invite_code or action+invite_id, not both")
        if not by_code and not (self.action and self.invite_id):
            raise ValueError("Either invite_code or action+invite_id is required")
        return self


class FamilyInviteListRequest(BaseModel):
    status: str | None = Field(default="pending")
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in {"pending", "accepted", "rejected"}:
            raise ValueError("status must be one of: pending, accepted, rejected")
        return normalized


class InviteByPhoneRequest(BaseModel):
    phone_number: str = Field(..., min_length=8, max_length=16)
    full_name: str | None = Field(
        None,
        max_length=255,
        description="Used when invited user has no personal profile yet",
    )
    dry_run: bool = False
    user_id: UUID | None = None
    role: FamilyRole = FamilyRole.MEMBER
    relation_role: str | None = Field(default=None, max_length=64)

    @model_validator(mode="before")
    @classmethod
    def normalize_role_payload(cls, value: object) -> object:
        return _coerce_relation_role_payload(value)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        normalized = value.strip()
        if not E164_PHONE_RE.fullmatch(normalized):
            raise ValueError("phone_number must be valid E.164 format (e.g. +84901234567)")
        return normalized


class CreatePersonalProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)


class InvitePreviewResponse(BaseModel):
    family_name: str
    invite_code: str
    valid: bool = True
    expires_at: datetime


class InviteLinkableMemberResponse(BaseModel):
    id: UUID
    full_name: str
    role: FamilyRole
    relation_role: str | None = None
    avatar_url: str | None = None


class ListLinkableProfilesResponse(BaseModel):
    id: UUID
    name: str
    address: str | None = None
    avatar_url: str | None = None
    invite_code: str
    created_at: datetime
    members: list[InviteLinkableMemberResponse]


class LinkInviteProfileRequest(BaseModel):
    invite_code: str = Field(..., min_length=1, max_length=64)
    profile_id: UUID


class LinkInviteProfileResponse(BaseModel):
    success: bool
    family_id: UUID
    profile_id: UUID
    health_profile_id: UUID | None
    linked_user_id: UUID
    membership_created: bool
    post_login_flow_completed: bool


class PatchFamilyRequest(BaseModel):
    name: str = Field(validation_alias=AliasChoices("name", "family_name"), min_length=1, max_length=255)


class PatchMembershipRoleRequest(BaseModel):
    role: FamilyRole


class CreateProxyProfilePayload(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: date | None = None
    gender: str | None = None
    height_cm: Decimal | None = None
    weight_kg: Decimal | None = None
    address: str | None = None
    avatar_url: str | None = None


class CreateProxyHealthPayload(BaseModel):
    blood_type: str | None = None
    chronic_conditions: list[str] | None = None
    allergies: list[str] | None = None


class CreateProfileInFamilyRequest(BaseModel):
    role: FamilyRole = FamilyRole.MEMBER
    relation_role: str | None = Field(default=None, max_length=64)
    profile: CreateProxyProfilePayload | None = None
    health_profile: CreateProxyHealthPayload | None = None
    # Backward-compatible fields
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    owner_user_id: UUID | None = None
    dob: date | None = None
    gender: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_role_payload(cls, value: object) -> object:
        return _coerce_relation_role_payload(value)

    @model_validator(mode="after")
    def validate_profile_payload(self) -> CreateProfileInFamilyRequest:
        if self.profile is None and not self.full_name:
            raise ValueError("profile.full_name (or legacy full_name) is required")
        return self


class PatchProfileRequest(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    dob: date | None = None
    gender: str | None = None
    height_cm: Decimal | None = None
    weight_kg: Decimal | None = None
    address: str | None = None
    avatar_url: str | None = None
    status: ProfileStatus | None = None


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
    chronic_diseases: list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("chronic_diseases", "chronic_conditions"),
    )
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
    relation_role: str | None = None

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
            relation_role=m.relation_role,
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


class FamilyMemberProfileResponse(BaseModel):
    id: UUID
    full_name: str
    date_of_birth: date | None
    gender: str | None
    height_cm: Decimal | None
    weight_kg: Decimal | None
    address: str | None
    avatar_url: str | None

    @classmethod
    def from_entity(cls, p: Profile) -> FamilyMemberProfileResponse:
        return cls(
            id=p.id,
            full_name=p.full_name,
            date_of_birth=p.dob,
            gender=p.gender,
            height_cm=p.height_cm,
            weight_kg=p.weight_kg,
            address=p.address,
            avatar_url=p.avatar_url,
        )


class FamilyMemberHealthResponse(BaseModel):
    blood_type: str | None
    chronic_conditions: list[str]
    allergies: list[str]

    @classmethod
    def from_entity(cls, h: HealthDetail | None) -> FamilyMemberHealthResponse:
        return cls(
            blood_type=h.blood_type if h else None,
            chronic_conditions=list(h.chronic_diseases or []) if h else [],
            allergies=list(h.allergies or []) if h else [],
        )


class FamilyMemberResponse(BaseModel):
    id: UUID
    family_id: UUID
    user_id: UUID | None = None
    role: FamilyRole
    relation_role: str | None = None
    is_owner: bool = False
    is_self: bool = False
    joined_at: datetime | None = None
    profile: FamilyMemberProfileResponse
    health_profile: FamilyMemberHealthResponse

    @classmethod
    def from_entities(
        cls,
        *,
        membership: FamilyMembership,
        profile: Profile,
        health: HealthDetail | None,
        current_user_id: UUID,
    ) -> FamilyMemberResponse:
        return cls(
            id=membership.id,
            family_id=membership.family_id,
            user_id=profile.linked_user_id,
            role=membership.role,
            relation_role=membership.relation_role,
            is_owner=membership.role == FamilyRole.OWNER,
            is_self=profile.owner_user_id == current_user_id or profile.linked_user_id == current_user_id,
            joined_at=membership.created_at,
            profile=FamilyMemberProfileResponse.from_entity(profile),
            health_profile=FamilyMemberHealthResponse.from_entity(health),
        )


class FamilyInviteResponse(BaseModel):
    id: UUID
    family_id: UUID
    phone_number: str | None = None
    user_id: UUID | None = None
    role: FamilyRole
    relation_role: str | None = None
    status: str
    invited_by: UUID
    invited_at: datetime
    responded_at: datetime | None = None

    @classmethod
    def from_entity(cls, invite: FamilyInvite) -> FamilyInviteResponse:
        return cls(
            id=invite.id,
            family_id=invite.family_id,
            phone_number=invite.phone_number,
            user_id=invite.user_id,
            role=invite.role,
            relation_role=invite.relation_role,
            status=invite.status.value.lower(),
            invited_by=invite.invited_by,
            invited_at=invite.invited_at,
            responded_at=invite.responded_at,
        )


class FamilyInviteInboxResponse(FamilyInviteResponse):
    family_name: str
    family_avatar_url: str | None = None
    family_member_count: int
    inviter_name: str | None = None
    inviter_role: FamilyRole | None = None

    @classmethod
    def from_entity(cls, row: FamilyInviteInboxItem) -> FamilyInviteInboxResponse:
        base = FamilyInviteResponse.from_entity(row.invite)
        return cls(
            **base.model_dump(),
            family_name=row.family_name,
            family_avatar_url=row.family_avatar_url,
            family_member_count=row.family_member_count,
            inviter_name=row.inviter_name,
            inviter_role=row.inviter_role,
        )


class FamilyContractResponse(BaseModel):
    id: UUID
    name: str
    address: str | None = None
    avatar_url: str | None = None
    invite_code: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    members: list[FamilyMemberResponse]
    invites: list[FamilyInviteResponse] | None = None

    @classmethod
    def from_parts(
        cls,
        *,
        family: Family,
        members: list[FamilyMemberResponse],
        invites: list[FamilyInviteResponse] | None = None,
    ) -> FamilyContractResponse:
        return cls(
            id=family.id,
            name=family.family_name,
            address=family.address,
            avatar_url=family.avatar_url,
            invite_code=family.invite_code,
            created_by=family.created_by,
            created_at=family.created_at,
            members=members,
            invites=invites,
        )


class UserSearchByPhoneResponse(BaseModel):
    id: UUID
    full_name: str | None = None
    phone_number: str | None = None
    avatar_url: str | None = None
    has_account: bool = True


class InviteByPhoneResponse(BaseModel):
    dry_run: bool
    found: bool | None = None
    user: UserSearchByPhoneResponse | None = None
    invite: FamilyInviteResponse | None = None


class InviteActionResponse(BaseModel):
    success: bool
    invite_id: UUID
    status: str
    family_member_id: UUID | None = None


InviteByPhoneResponse.model_rebuild()

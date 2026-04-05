from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.application.dtos.family_dto import ProfileResponse
from app.application.dtos.medical_dto import MedicalRecordResponse
from app.application.dtos.vaccination_dto import UserVaccinationWithDosesResponse
from app.domain.entities.health_detail import HealthDetail
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


class UserMeHealthProfileResponse(BaseModel):
    """Sức khỏe + bệnh án + tiêm chủng (personal profile) — dùng cache tab Home / Sức khỏe."""

    profile_id: UUID
    blood_type: str | None
    chronic_diseases: list[str] | None
    allergies: list[str] | None
    emergency_contact: str | None
    notes: str | None
    updated_at: datetime
    medical_records: list[MedicalRecordResponse] = Field(default_factory=list)
    vaccinations: list[UserVaccinationWithDosesResponse] = Field(default_factory=list)

    @classmethod
    def from_parts(
        cls,
        profile_id: UUID,
        health: HealthDetail | None,
        medical_records: list[MedicalRecordResponse],
        vaccinations: list[UserVaccinationWithDosesResponse],
    ) -> UserMeHealthProfileResponse:
        if health is not None:
            return cls(
                profile_id=health.profile_id,
                blood_type=health.blood_type,
                chronic_diseases=health.chronic_diseases,
                allergies=health.allergies,
                emergency_contact=health.emergency_contact,
                notes=health.notes,
                updated_at=health.updated_at,
                medical_records=medical_records,
                vaccinations=vaccinations,
            )
        return cls(
            profile_id=profile_id,
            blood_type=None,
            chronic_diseases=None,
            allergies=None,
            emergency_contact=None,
            notes=None,
            updated_at=datetime.now(timezone.utc),
            medical_records=medical_records,
            vaccinations=vaccinations,
        )


class UserMeProfileBundleResponse(BaseModel):
    """One linked profile + health aggregate + family membership summary."""

    profile: ProfileResponse
    health_profile: UserMeHealthProfileResponse
    family_ids: list[UUID] = Field(default_factory=list)
    family_count: int = 0


class UserMeResponse(BaseModel):
    """GET /users/me — bundle cho cache client."""

    user: UserResponse
    profiles: list[UserMeProfileBundleResponse] = Field(default_factory=list)
    profile: ProfileResponse | None = None
    health_profile: UserMeHealthProfileResponse | None = None

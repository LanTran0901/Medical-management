from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.application.dtos.family_dto import EmergencyContactItem, ProfileResponse
from app.application.dtos.medical_dto import MedicalRecordResponse
from app.application.dtos.medicine_dto import MedicineInventoryResponse, MedicineReminderResponse
from app.application.dtos.vaccination_dto import UserVaccinationWithDosesResponse
from app.domain.entities.appointment_reminder import AppointmentReminder
from app.domain.entities.health_detail import HealthDetail
from app.domain.entities.user import User, UserStatus
from app.domain.remind_before import RemindBeforeUnit


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


class AppointmentReminderResponse(BaseModel):
    id: UUID
    profile_id: UUID
    reminder_type: str
    title: str
    hospital_name: str | None
    department: str | None
    appointment_at: datetime
    remind_before_value: int
    remind_before_unit: RemindBeforeUnit
    vaccine_name: str | None
    dose_number: int | None
    total_doses: int | None
    status: str
    note: str | None
    follow_up_appointment_id: UUID | None
    vaccination_dose_id: UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, row: AppointmentReminder) -> "AppointmentReminderResponse":
        return cls(
            id=row.id,
            profile_id=row.profile_id,
            reminder_type=row.reminder_type,
            title=row.title,
            hospital_name=row.hospital_name,
            department=row.department,
            appointment_at=row.appointment_at,
            remind_before_value=row.remind_before_value,
            remind_before_unit=RemindBeforeUnit(str(row.remind_before_unit).upper()),
            vaccine_name=row.vaccine_name,
            dose_number=row.dose_number,
            total_doses=row.total_doses,
            status=row.status,
            note=row.note,
            follow_up_appointment_id=row.follow_up_appointment_id,
            vaccination_dose_id=row.vaccination_dose_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class UserMeMedicineInventoryItem(MedicineInventoryResponse):
    medicine_reminder: MedicineReminderResponse | None = None


class UserMeHealthProfileResponse(BaseModel):
    """Sức khỏe + bệnh án + tiêm chủng (personal profile) — dùng cache tab Home / Sức khỏe."""

    profile_id: UUID
    blood_type: str | None
    chronic_diseases: list[str] | None
    allergies: list[str] | None
    drug_allergies: list[str] | None = None
    food_allergies: list[str] | None = None
    emergency_contacts: list[EmergencyContactItem] = Field(default_factory=list)
    notes: str | None
    updated_at: datetime
    medical_records: list[MedicalRecordResponse] = Field(default_factory=list)
    vaccinations: list[UserVaccinationWithDosesResponse] = Field(default_factory=list)
    medicine_inventory: list[UserMeMedicineInventoryItem] = Field(default_factory=list)
    appointment_reminders: list[AppointmentReminderResponse] = Field(default_factory=list)

    @classmethod
    def from_parts(
        cls,
        profile_id: UUID,
        health: HealthDetail | None,
        medical_records: list[MedicalRecordResponse],
        vaccinations: list[UserVaccinationWithDosesResponse],
        *,
        medicine_inventory: list[UserMeMedicineInventoryItem] | None = None,
        appointment_reminders: list[AppointmentReminderResponse] | None = None,
    ) -> UserMeHealthProfileResponse:
        med_inv = medicine_inventory if medicine_inventory is not None else []
        appt = appointment_reminders if appointment_reminders is not None else []
        if health is not None:
            return cls(
                profile_id=health.profile_id,
                blood_type=health.blood_type,
                chronic_diseases=health.chronic_diseases,
                allergies=health.allergies,
                drug_allergies=health.drug_allergies,
                food_allergies=health.food_allergies,
                emergency_contacts=[
                    EmergencyContactItem(name=x.name, phone=x.phone, relationship=x.relationship)
                    for x in health.emergency_contacts
                ],
                notes=health.notes,
                updated_at=health.updated_at,
                medical_records=medical_records,
                vaccinations=vaccinations,
                medicine_inventory=med_inv,
                appointment_reminders=appt,
            )
        return cls(
            profile_id=profile_id,
            blood_type=None,
            chronic_diseases=None,
            allergies=None,
            drug_allergies=None,
            food_allergies=None,
            emergency_contacts=[],
            notes=None,
            updated_at=datetime.now(timezone.utc),
            medical_records=medical_records,
            vaccinations=vaccinations,
            medicine_inventory=med_inv,
            appointment_reminders=appt,
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


class UserMeProfileSummaryResponse(BaseModel):
    """Một profile liên kết + danh sách family (không tải bệnh án / tiêm / tủ thuốc)."""

    profile: ProfileResponse
    family_ids: list[UUID] = Field(default_factory=list)
    family_count: int = 0


class UserMeSummaryResponse(BaseModel):
    """GET /users/me/summary — phản hồi nhẹ cho bootstrap hoặc lazy-load full GET /users/me."""

    user: UserResponse
    profiles: list[UserMeProfileSummaryResponse] = Field(default_factory=list)
    profile: ProfileResponse | None = None
    health_profile: UserMeHealthProfileResponse | None = None

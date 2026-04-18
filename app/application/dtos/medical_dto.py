from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MedicalRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: UUID
    created_by: UUID
    title: str | None
    diagnosis_name: str | None
    diagnosis_slug: str | None
    doctor_name: str | None
    hospital_name: str | None
    visit_date: date | None
    specialty: str | None
    symptoms: list[str] | None
    test_results: str | None
    doctor_advice: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class CreateMedicalRecordRequest(BaseModel):
    title: str | None = Field(None, max_length=255)
    diagnosis_name: str | None = None
    diagnosis_slug: str | None = None
    doctor_name: str | None = Field(None, max_length=255)
    hospital_name: str | None = None
    visit_date: date | None = None
    specialty: str | None = None
    symptoms: list[str] | None = None
    test_results: str | None = None
    doctor_advice: str | None = None
    notes: str | None = None


class PatchMedicalRecordRequest(BaseModel):
    title: str | None = Field(None, max_length=255)
    diagnosis_name: str | None = None
    diagnosis_slug: str | None = None
    doctor_name: str | None = Field(None, max_length=255)
    hospital_name: str | None = None
    visit_date: date | None = None
    specialty: str | None = None
    symptoms: list[str] | None = None
    test_results: str | None = None
    doctor_advice: str | None = None
    notes: str | None = None


class MedicalAttachmentResponse(BaseModel):
    id: UUID
    medical_record_id: UUID
    file_name: str
    file_type: str
    file_url: str


class AttachmentUrlOnlyRequest(BaseModel):
    """FR-007 MAY — no bytes on server."""

    file_name: str = Field(..., min_length=1, max_length=512)
    file_type: str = Field(..., min_length=1, max_length=128)
    file_url: str = Field(..., min_length=1, max_length=8192)

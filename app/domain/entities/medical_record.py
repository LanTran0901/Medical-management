from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MedicalRecord:
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
    deleted_at: datetime | None


@dataclass(frozen=True, slots=True)
class MedicalRecordAttachment:
    id: UUID
    medical_record_id: UUID
    file_name: str
    file_type: str
    file_url: str

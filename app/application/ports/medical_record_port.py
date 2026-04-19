from __future__ import annotations

from datetime import date
from uuid import UUID

from app.domain.entities.medical_record import MedicalRecord, MedicalRecordAttachment


class MedicalRecordRepositoryPort:
    async def list_records_for_profile(self, profile_id: UUID) -> list[MedicalRecord]:
        raise NotImplementedError

    async def list_records_for_profiles(
        self, profile_ids: list[UUID]
    ) -> dict[UUID, list[MedicalRecord]]:
        """All non-deleted records for many profiles (single query; GET /users/me optimization)."""
        raise NotImplementedError

    async def get_record(self, record_id: UUID, profile_id: UUID) -> MedicalRecord | None:
        raise NotImplementedError

    async def get_record_by_id(self, record_id: UUID) -> MedicalRecord | None:
        raise NotImplementedError

    async def get_record_any_state(self, record_id: UUID, profile_id: UUID) -> MedicalRecord | None:
        raise NotImplementedError

    async def create_record(
        self,
        *,
        profile_id: UUID,
        created_by: UUID,
        title: str | None,
        diagnosis_name: str | None,
        diagnosis_slug: str | None,
        doctor_name: str | None,
        hospital_name: str | None,
        visit_date: date | None,
        specialty: str | None,
        symptoms: list[str] | None,
        test_results: str | None,
        doctor_advice: str | None,
        notes: str | None,
    ) -> MedicalRecord:
        raise NotImplementedError

    async def apply_patch(self, record_id: UUID, fields: dict[str, object]) -> MedicalRecord | None:
        raise NotImplementedError

    async def soft_delete_record(self, record_id: UUID) -> bool:
        raise NotImplementedError

    async def hard_delete_record(self, record_id: UUID) -> bool:
        raise NotImplementedError

    async def list_attachments(self, medical_record_id: UUID) -> list[MedicalRecordAttachment]:
        raise NotImplementedError

    async def get_attachment(self, attachment_id: UUID) -> MedicalRecordAttachment | None:
        raise NotImplementedError

    async def create_attachment(
        self,
        *,
        attachment_id: UUID,
        medical_record_id: UUID,
        file_name: str,
        file_type: str,
        file_url: str,
    ) -> MedicalRecordAttachment:
        raise NotImplementedError

    async def delete_attachment(self, attachment_id: UUID) -> bool:
        raise NotImplementedError

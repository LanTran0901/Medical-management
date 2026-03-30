from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.medical_record_port import MedicalRecordRepositoryPort
from app.domain.entities.medical_record import MedicalRecord, MedicalRecordAttachment
from app.infrastructure.config.database.postgres.models.medical_record_models import (
    MedicalRecordAttachmentModel,
    MedicalRecordModel,
)


class MedicalRecordRepositoryPG(MedicalRecordRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_record(model: MedicalRecordModel) -> MedicalRecord:
        return MedicalRecord(
            id=model.id,
            profile_id=model.profile_id,
            created_by=model.created_by,
            diagnosis_name=model.diagnosis_name,
            diagnosis_slug=model.diagnosis_slug,
            doctor_name=model.doctor_name,
            hospital_name=model.hospital_name,
            visit_date=model.visit_date,
            specialty=model.specialty,
            notes=model.notes,
            created_at=model.created_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def _to_attachment(model: MedicalRecordAttachmentModel) -> MedicalRecordAttachment:
        return MedicalRecordAttachment(
            id=model.id,
            medical_record_id=model.medical_record_id,
            file_name=model.file_name,
            file_type=model.file_type,
            file_url=model.file_url,
        )

    async def list_records_for_profile(self, profile_id: UUID) -> list[MedicalRecord]:
        stmt = (
            select(MedicalRecordModel)
            .where(
                MedicalRecordModel.profile_id == profile_id,
                MedicalRecordModel.deleted_at.is_(None),
            )
            .order_by(MedicalRecordModel.created_at.desc())
        )
        r = await self.session.execute(stmt)
        return [self._to_record(row) for row in r.scalars().all()]

    async def get_record(self, record_id: UUID, profile_id: UUID) -> MedicalRecord | None:
        stmt = select(MedicalRecordModel).where(
            MedicalRecordModel.id == record_id,
            MedicalRecordModel.profile_id == profile_id,
            MedicalRecordModel.deleted_at.is_(None),
        )
        r = await self.session.execute(stmt)
        model = r.scalar_one_or_none()
        return self._to_record(model) if model else None

    async def get_record_any_state(self, record_id: UUID, profile_id: UUID) -> MedicalRecord | None:
        stmt = select(MedicalRecordModel).where(
            MedicalRecordModel.id == record_id,
            MedicalRecordModel.profile_id == profile_id,
        )
        r = await self.session.execute(stmt)
        model = r.scalar_one_or_none()
        return self._to_record(model) if model else None

    async def get_record_by_id(self, record_id: UUID) -> MedicalRecord | None:
        model = await self.session.get(MedicalRecordModel, record_id)
        return self._to_record(model) if model else None

    async def create_record(
        self,
        *,
        profile_id: UUID,
        created_by: UUID,
        diagnosis_name: str | None,
        diagnosis_slug: str | None,
        doctor_name: str | None,
        hospital_name: str | None,
        visit_date: date | None,
        specialty: str | None,
        notes: str | None,
    ) -> MedicalRecord:
        m = MedicalRecordModel(
            profile_id=profile_id,
            created_by=created_by,
            diagnosis_name=diagnosis_name,
            diagnosis_slug=diagnosis_slug,
            doctor_name=doctor_name,
            hospital_name=hospital_name,
            visit_date=visit_date,
            specialty=specialty,
            notes=notes,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_record(m)

    async def apply_patch(self, record_id: UUID, fields: dict[str, object]) -> MedicalRecord | None:
        m = await self.session.get(MedicalRecordModel, record_id)
        if m is None:
            return None
        for k, v in fields.items():
            setattr(m, k, v)
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_record(m)

    async def soft_delete_record(self, record_id: UUID) -> bool:
        m = await self.session.get(MedicalRecordModel, record_id)
        if m is None:
            return False
        m.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    async def hard_delete_record(self, record_id: UUID) -> bool:
        m = await self.session.get(MedicalRecordModel, record_id)
        if m is None:
            return False
        await self.session.delete(m)
        await self.session.flush()
        return True

    async def list_attachments(self, medical_record_id: UUID) -> list[MedicalRecordAttachment]:
        stmt = (
            select(MedicalRecordAttachmentModel)
            .where(MedicalRecordAttachmentModel.medical_record_id == medical_record_id)
            .order_by(MedicalRecordAttachmentModel.file_name)
        )
        r = await self.session.execute(stmt)
        return [self._to_attachment(row) for row in r.scalars().all()]

    async def get_attachment(self, attachment_id: UUID) -> MedicalRecordAttachment | None:
        model = await self.session.get(MedicalRecordAttachmentModel, attachment_id)
        return self._to_attachment(model) if model else None

    async def create_attachment(
        self,
        *,
        attachment_id: UUID,
        medical_record_id: UUID,
        file_name: str,
        file_type: str,
        file_url: str,
    ) -> MedicalRecordAttachment:
        m = MedicalRecordAttachmentModel(
            id=attachment_id,
            medical_record_id=medical_record_id,
            file_name=file_name,
            file_type=file_type,
            file_url=file_url,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_attachment(m)

    async def delete_attachment(self, attachment_id: UUID) -> bool:
        m = await self.session.get(MedicalRecordAttachmentModel, attachment_id)
        if m is None:
            return False
        await self.session.delete(m)
        await self.session.flush()
        return True

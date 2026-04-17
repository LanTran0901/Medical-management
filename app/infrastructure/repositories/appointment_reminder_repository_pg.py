from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.appointment_reminder_port import AppointmentReminderRepositoryPort
from app.domain.entities.appointment_reminder import AppointmentReminder
from app.infrastructure.config.database.postgres.models.appointment_reminder_models import (
    AppointmentReminderModel,
)


class AppointmentReminderRepositoryPG(AppointmentReminderRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: AppointmentReminderModel) -> AppointmentReminder:
        return AppointmentReminder(
            id=model.id,
            profile_id=model.profile_id,
            reminder_type=model.reminder_type,
            title=model.title,
            hospital_name=model.hospital_name,
            department=model.department,
            appointment_at=model.appointment_at,
            remind_before_value=model.remind_before_value,
            remind_before_unit=str(model.remind_before_unit),
            vaccine_name=model.vaccine_name,
            dose_number=model.dose_number,
            total_doses=model.total_doses,
            status=model.status,
            note=model.note,
            follow_up_appointment_id=model.follow_up_appointment_id,
            vaccination_dose_id=model.vaccination_dose_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def list_by_profile_id(
        self,
        profile_id: UUID,
        *,
        limit: int | None = None,
    ) -> list[AppointmentReminder]:
        stmt = (
            select(AppointmentReminderModel)
            .where(AppointmentReminderModel.profile_id == profile_id)
            .order_by(AppointmentReminderModel.appointment_at.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        r = await self._session.execute(stmt)
        rows = list(r.scalars().all())
        return [self._to_entity(m) for m in rows]

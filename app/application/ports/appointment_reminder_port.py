from __future__ import annotations

from uuid import UUID

from app.domain.entities.appointment_reminder import AppointmentReminder


class AppointmentReminderRepositoryPort:
    async def list_by_profile_id(
        self,
        profile_id: UUID,
        *,
        limit: int | None = None,
    ) -> list[AppointmentReminder]:
        raise NotImplementedError

from __future__ import annotations

from uuid import UUID

from app.application.dtos.user_dto import AppointmentReminderResponse
from app.application.ports.appointment_reminder_port import AppointmentReminderRepositoryPort
from app.application.usecases.access_control_usecases import AccessControlService


class AppointmentReminderReadService:
    def __init__(
        self,
        repo: AppointmentReminderRepositoryPort,
        access: AccessControlService,
    ) -> None:
        self._repo = repo
        self._access = access

    async def list_for_profile(
        self,
        profile_id: UUID,
        user_id: UUID,
        *,
        limit: int | None = None,
        skip_access_check: bool = False,
    ) -> list[AppointmentReminderResponse]:
        if not skip_access_check:
            await self._access.require_profile_read(profile_id, user_id)
        rows = await self._repo.list_by_profile_id(profile_id, limit=limit)
        return [AppointmentReminderResponse.from_entity(r) for r in rows]

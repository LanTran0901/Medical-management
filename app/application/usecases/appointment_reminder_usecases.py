from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.appointment_reminder_dto import (
    AppointmentReminderResponse,
    CreateAppointmentReminderRequest,
    PatchAppointmentReminderRequest,
)
from app.application.family_errors import NotFoundError
from app.application.usecases.access_control_usecases import AccessControlService
from app.domain.remind_before import RemindBeforeUnit


class AppointmentReminderService:
    def __init__(self, session: AsyncSession, access: AccessControlService) -> None:
        self._session = session
        self._access = access

    def _row_to_response(self, row: dict) -> AppointmentReminderResponse:
        return AppointmentReminderResponse(
            id=row["id"],
            profile_id=row["profile_id"],
            kind=row["type"],
            title=row["title"],
            hospital_name=row.get("hospital_name"),
            department=row.get("department"),
            appointment_at=row["appointment_at"],
            reminder_enabled=bool(row.get("reminder_enabled", True)),
            remind_before_value=(
                int(row["remind_before_value"])
                if row.get("remind_before_value") is not None
                else None
            ),
            remind_before_unit=(
                RemindBeforeUnit(str(row["remind_before_unit"]).upper())
                if row.get("remind_before_unit") is not None
                else None
            ),
            vaccine_name=row.get("vaccine_name"),
            dose_number=row.get("dose_number"),
            total_doses=row.get("total_doses"),
            status=row["status"],
            note=row.get("note"),
            follow_up_appointment_id=row.get("follow_up_appointment_id"),
            vaccination_dose_id=row.get("vaccination_dose_id"),
        )

    @staticmethod
    def _normalize_reminder(
        reminder_enabled: bool,
        remind_before_value: int | None,
        remind_before_unit: str | None,
    ) -> tuple[bool, int | None, str | None]:
        if not reminder_enabled:
            return False, None, None

        value = remind_before_value
        unit = remind_before_unit
        if value is None and unit is None:
            return True, 60, RemindBeforeUnit.MINUTES.value
        if value is None:
            value = 60
        if unit is None:
            unit = RemindBeforeUnit.MINUTES.value
        return True, value, unit

    async def list_for_profile(
        self, profile_id: UUID, user_id: UUID
    ) -> list[AppointmentReminderResponse]:
        await self._access.require_medical_profile_view(profile_id, user_id)
        r = await self._session.execute(
            text(
                """
                SELECT
                    id, profile_id, type::text AS type, title, hospital_name, department,
                    appointment_at, reminder_enabled,
                    remind_before_value, remind_before_unit::text AS remind_before_unit,
                    vaccine_name, dose_number, total_doses,
                    status::text AS status, note, follow_up_appointment_id, vaccination_dose_id
                FROM appointment_reminders
                WHERE profile_id = :pid
                ORDER BY appointment_at ASC
                """
            ),
            {"pid": profile_id},
        )
        return [self._row_to_response(dict(x)) for x in r.mappings().all()]

    async def create(
        self,
        profile_id: UUID,
        user_id: UUID,
        body: CreateAppointmentReminderRequest,
    ) -> AppointmentReminderResponse:
        await self._access.require_medical_profile_write(profile_id, user_id)

        rid = uuid.uuid4()
        at = body.appointment_at
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        reminder_enabled, remind_before_value, remind_before_unit = self._normalize_reminder(
            body.reminder_enabled,
            body.remind_before_value,
            body.remind_before_unit.value if body.remind_before_unit else None,
        )

        await self._session.execute(
            text(
                """
                INSERT INTO appointment_reminders (
                    id, profile_id, type, title, hospital_name, department,
                    appointment_at, reminder_enabled, remind_before_value, remind_before_unit,
                    vaccine_name, dose_number, total_doses,
                    status, note, follow_up_appointment_id, vaccination_dose_id
                )
                VALUES (
                    :id, :profile_id, CAST(:rtype AS appointment_reminder_type), :title,
                    :hospital_name, :department, :appointment_at,
                    :reminder_enabled, :remind_before_value,
                    CAST(:remind_before_unit AS follow_up_remind_before_unit),
                    :vaccine_name, :dose_number, :total_doses,
                    'pending'::appointment_reminder_status, :note,
                    :follow_up_appointment_id, :vaccination_dose_id
                )
                """
            ),
            {
                "id": rid,
                "profile_id": profile_id,
                "rtype": body.kind,
                "title": body.title,
                "hospital_name": body.hospital_name,
                "department": body.department,
                "appointment_at": at,
                "reminder_enabled": reminder_enabled,
                "remind_before_value": remind_before_value,
                "remind_before_unit": remind_before_unit,
                "vaccine_name": body.vaccine_name,
                "dose_number": body.dose_number,
                "total_doses": body.total_doses,
                "note": body.note,
                "follow_up_appointment_id": body.follow_up_appointment_id,
                "vaccination_dose_id": body.vaccination_dose_id,
            },
        )

        row = (
            await self._session.execute(
                text(
                    """
                    SELECT
                        id, profile_id, type::text AS type, title, hospital_name, department,
                        appointment_at, reminder_enabled,
                        remind_before_value, remind_before_unit::text AS remind_before_unit,
                        vaccine_name, dose_number, total_doses,
                        status::text AS status, note, follow_up_appointment_id, vaccination_dose_id
                    FROM appointment_reminders WHERE id = :id
                    """
                ),
                {"id": rid},
            )
        ).mappings().one()
        return self._row_to_response(dict(row))

    async def _get_row_for_user(
        self, reminder_id: UUID, user_id: UUID
    ) -> dict | None:
        r = await self._session.execute(
            text(
                """
                SELECT
                    ar.id, ar.profile_id, ar.type::text AS type, ar.title, ar.hospital_name,
                    ar.department, ar.appointment_at,
                    ar.reminder_enabled,
                    ar.remind_before_value, ar.remind_before_unit::text AS remind_before_unit,
                    ar.vaccine_name, ar.dose_number, ar.total_doses,
                    ar.status::text AS status, ar.note,
                    ar.follow_up_appointment_id, ar.vaccination_dose_id
                FROM appointment_reminders ar
                JOIN profiles p ON p.id = ar.profile_id
                WHERE ar.id = :rid
                  AND (p.owner_user_id = :uid OR p.linked_user_id = :uid)
                """
            ),
            {"rid": reminder_id, "uid": user_id},
        )
        m = r.mappings().one_or_none()
        return dict(m) if m else None

    async def patch(
        self,
        reminder_id: UUID,
        user_id: UUID,
        body: PatchAppointmentReminderRequest,
    ) -> AppointmentReminderResponse:
        row = await self._get_row_for_user(reminder_id, user_id)
        if row is None:
            raise NotFoundError("Reminder not found")
        await self._access.require_medical_profile_write(row["profile_id"], user_id)

        sets: list[str] = []
        params: dict = {"rid": reminder_id}
        body_fields = body.model_fields_set

        if body.title is not None:
            sets.append("title = :title")
            params["title"] = body.title
        if body.appointment_at is not None:
            at = body.appointment_at
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            sets.append("appointment_at = :appointment_at")
            params["appointment_at"] = at
        if (
            "reminder_enabled" in body_fields
            or "remind_before_value" in body_fields
            or "remind_before_unit" in body_fields
        ):
            reminder_enabled, remind_before_value, remind_before_unit = self._normalize_reminder(
                body.reminder_enabled
                if "reminder_enabled" in body_fields
                else bool(row.get("reminder_enabled", True)),
                body.remind_before_value
                if "remind_before_value" in body_fields
                else row.get("remind_before_value"),
                body.remind_before_unit.value
                if "remind_before_unit" in body_fields and body.remind_before_unit is not None
                else row.get("remind_before_unit"),
            )
            sets.append("reminder_enabled = :reminder_enabled")
            params["reminder_enabled"] = reminder_enabled
            sets.append("remind_before_value = :rbv")
            params["rbv"] = remind_before_value
            sets.append("remind_before_unit = CAST(:rbu AS follow_up_remind_before_unit)")
            params["rbu"] = remind_before_unit
        if body.hospital_name is not None:
            sets.append("hospital_name = :hospital_name")
            params["hospital_name"] = body.hospital_name
        if body.department is not None:
            sets.append("department = :department")
            params["department"] = body.department
        if body.vaccine_name is not None:
            sets.append("vaccine_name = :vaccine_name")
            params["vaccine_name"] = body.vaccine_name
        if body.dose_number is not None:
            sets.append("dose_number = :dose_number")
            params["dose_number"] = body.dose_number
        if body.total_doses is not None:
            sets.append("total_doses = :total_doses")
            params["total_doses"] = body.total_doses
        if body.note is not None:
            sets.append("note = :note")
            params["note"] = body.note
        if "vaccination_dose_id" in body_fields:
            sets.append("vaccination_dose_id = :vaccination_dose_id")
            params["vaccination_dose_id"] = body.vaccination_dose_id
        if body.status is not None:
            sets.append("status = CAST(:st AS appointment_reminder_status)")
            params["st"] = body.status

        if sets:
            sets.append("updated_at = now()")
            await self._session.execute(
                text(
                    f"UPDATE appointment_reminders SET {', '.join(sets)} WHERE id = :rid"
                ),
                params,
            )

        row2 = (
            await self._session.execute(
                text(
                    """
                    SELECT
                        id, profile_id, type::text AS type, title, hospital_name, department,
                        appointment_at, reminder_enabled,
                        remind_before_value, remind_before_unit::text AS remind_before_unit,
                        vaccine_name, dose_number, total_doses,
                        status::text AS status, note, follow_up_appointment_id, vaccination_dose_id
                    FROM appointment_reminders WHERE id = :rid
                    """
                ),
                {"rid": reminder_id},
            )
        ).mappings().one()
        return self._row_to_response(dict(row2))

    async def delete(self, reminder_id: UUID, user_id: UUID) -> None:
        row = await self._get_row_for_user(reminder_id, user_id)
        if row is None:
            raise NotFoundError("Reminder not found")
        await self._access.require_medical_profile_write(row["profile_id"], user_id)
        await self._session.execute(
            text("DELETE FROM appointment_reminders WHERE id = :rid"),
            {"rid": reminder_id},
        )

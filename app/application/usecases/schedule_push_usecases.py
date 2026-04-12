from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.notification_dto import (
    ScheduleComplianceRequest,
    ScheduleComplianceResponse,
    ScheduleDispatchResponse,
)
from app.core.config import settings
from app.infrastructure.services.fcm_service import FCMService

logger = logging.getLogger(__name__)

_OUTCOME_TO_STATUS = {"taken": "TAKEN", "skipped": "SKIPPED"}


class LogScheduleComplianceUseCase:
    """Insert schedule_logs when user marks taken or skipped."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(
        self,
        user_id: UUID,
        schedule_id: UUID,
        request: ScheduleComplianceRequest,
    ) -> ScheduleComplianceResponse:
        check = text(
            """
            SELECT s.id
            FROM schedules s
            JOIN profiles p ON p.id = s.profile_id
            WHERE s.id = :schedule_id
              AND (p.owner_user_id = :user_id OR p.linked_user_id = :user_id)
            """
        )
        result = await self.session.execute(
            check,
            {"schedule_id": schedule_id, "user_id": user_id},
        )
        if result.scalar_one_or_none() is None:
            return ScheduleComplianceResponse(
                success=False,
                message="Schedule not found or access denied.",
            )

        status = _OUTCOME_TO_STATUS[request.outcome]
        ins = text(
            """
            INSERT INTO schedule_logs (schedule_id, status, action_by)
            VALUES (:schedule_id, :status, :action_by)
            """
        )
        await self.session.execute(
            ins,
            {
                "schedule_id": schedule_id,
                "status": status,
                "action_by": user_id,
            },
        )
        return ScheduleComplianceResponse(
            success=True,
            message="Recorded.",
        )


class ProcessDueSchedulePushesUseCase:
    """Find MEDICINE schedules due this minute (UTC), dedupe via schedule_push_receipts, send FCM."""

    def __init__(self, session: AsyncSession, fcm_service: FCMService) -> None:
        self.session = session
        self._fcm = fcm_service

    async def execute(self) -> ScheduleDispatchResponse:
        channel = settings.fcm_android_channel_schedule
        now = datetime.now(timezone.utc)
        occurrence_date: date = now.date()
        current_hour = now.hour
        current_minute = now.minute

        rows_sql = text(
            """
            SELECT
                s.id AS schedule_id,
                s.remind_time AS remind_time,
                s.title AS title,
                mi.medicine_name AS medicine_name,
                p.full_name AS profile_name,
                p.owner_user_id AS owner_user_id,
                p.linked_user_id AS linked_user_id
            FROM schedules s
            JOIN profiles p ON p.id = s.profile_id
            LEFT JOIN medicine_inventory mi ON mi.id = s.medicine_id
            WHERE s.status = 'ACTIVE'
              AND s.category = 'MEDICINE'
              AND s.remind_time IS NOT NULL
            """
        )
        result = await self.session.execute(rows_sql)
        rows = result.mappings().all()

        processed = 0
        sent = 0
        skipped_duplicate = 0
        errors = 0

        for row in rows:
            rt = row["remind_time"]
            if rt is None:
                continue
            if rt.hour != current_hour or rt.minute != current_minute:
                continue

            processed += 1
            schedule_id: UUID = row["schedule_id"]
            time_slot = rt.strftime("%H:%M")

            ins_receipt = text(
                """
                INSERT INTO schedule_push_receipts (schedule_id, occurrence_date, time_slot)
                VALUES (:schedule_id, :occurrence_date, :time_slot)
                ON CONFLICT (schedule_id, occurrence_date, time_slot) DO NOTHING
                RETURNING id
                """
            )
            r2 = await self.session.execute(
                ins_receipt,
                {
                    "schedule_id": schedule_id,
                    "occurrence_date": occurrence_date,
                    "time_slot": time_slot,
                },
            )
            receipt_id = r2.scalar_one_or_none()
            if receipt_id is None:
                skipped_duplicate += 1
                continue

            await self.session.flush()

            profile_name = row.get("profile_name") or "Thành viên"
            med = row.get("medicine_name") or row.get("title") or "Thuốc"
            title = f"Nhắc uống thuốc — {profile_name}"
            body = str(med)

            user_ids: list[UUID] = []
            ou = row.get("owner_user_id")
            lu = row.get("linked_user_id")
            if ou is not None:
                user_ids.append(ou)
            if lu is not None and lu != ou:
                user_ids.append(lu)

            if not user_ids:
                errors += 1
                await self.session.execute(
                    text("DELETE FROM schedule_push_receipts WHERE id = :id"),
                    {"id": receipt_id},
                )
                continue

            fcm_tokens: list[str] = []
            seen: set[str] = set()
            tok_q = text(
                """
                SELECT fcm_token FROM user_devices
                WHERE user_id = :uid
                  AND fcm_token IS NOT NULL
                  AND btrim(fcm_token) <> ''
                """
            )
            for uid in user_ids:
                tr = await self.session.execute(tok_q, {"uid": uid})
                for (tok,) in tr.fetchall():
                    if tok and tok not in seen:
                        seen.add(tok)
                        fcm_tokens.append(tok)

            if not fcm_tokens:
                logger.warning(
                    "No FCM tokens for schedule %s users %s", schedule_id, user_ids
                )
                await self.session.execute(
                    text("DELETE FROM schedule_push_receipts WHERE id = :id"),
                    {"id": receipt_id},
                )
                errors += 1
                continue

            data = {
                "schedule_id": str(schedule_id),
                "category": "MEDICINE",
                "occurrence_date": occurrence_date.isoformat(),
                "time_slot": time_slot,
                "action": "compliance",
            }

            try:
                if len(fcm_tokens) == 1:
                    self._fcm.send_to_device(
                        fcm_tokens[0],
                        title,
                        body,
                        data,
                        android_channel_id=channel,
                        android_sound="default",
                    )
                else:
                    self._fcm.send_to_multiple(
                        fcm_tokens,
                        title,
                        body,
                        data,
                        android_channel_id=channel,
                        android_sound="default",
                    )
                sent += 1
            except Exception as e:
                logger.exception("FCM failed for schedule %s: %s", schedule_id, e)
                await self.session.execute(
                    text("DELETE FROM schedule_push_receipts WHERE id = :id"),
                    {"id": receipt_id},
                )
                errors += 1

        return ScheduleDispatchResponse(
            processed=processed,
            sent=sent,
            skipped_duplicate=skipped_duplicate,
            errors=errors,
        )

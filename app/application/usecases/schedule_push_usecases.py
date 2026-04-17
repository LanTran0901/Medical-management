from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.notification_dto import (
    ScheduleComplianceRequest,
    ScheduleComplianceResponse,
    ScheduleSnoozeRequest,
    ScheduleSnoozeResponse,
    ScheduleDispatchResponse,
)
from app.application.ports.notification_port import NotificationServicePort
from app.core.config import settings

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
            SELECT s.id, COALESCE(s.remind_tz, 'UTC') AS remind_tz
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
        crow = result.mappings().one_or_none()
        if crow is None:
            return ScheduleComplianceResponse(
                success=False,
                message="Schedule not found or access denied.",
            )
        tz = ProcessDueSchedulePushesUseCase._zone(crow.get("remind_tz"))
        occurrence_date = datetime.now(tz).date()

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

        # If user already marked the occurrence, any pending snooze for today is obsolete.
        await self.session.execute(
            text(
                """
                UPDATE schedule_snooze_overrides
                SET consumed_at = now()
                WHERE schedule_id = :schedule_id
                  AND occurrence_date = :occurrence_date
                  AND consumed_at IS NULL
                """
            ),
            {
                "schedule_id": schedule_id,
                "occurrence_date": occurrence_date,
            },
        )

        return ScheduleComplianceResponse(
            success=True,
            message="Recorded.",
        )


class SnoozeScheduleUseCase:
    """Create/update today's snooze override for a MEDICINE schedule."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(
        self,
        user_id: UUID,
        schedule_id: UUID,
        request: ScheduleSnoozeRequest,
    ) -> ScheduleSnoozeResponse:
        check = text(
            """
            SELECT s.id, s.remind_time, COALESCE(s.remind_tz, 'UTC') AS remind_tz
            FROM schedules s
            JOIN profiles p ON p.id = s.profile_id
            WHERE s.id = :schedule_id
              AND s.category = 'MEDICINE'
              AND s.status = 'ACTIVE'
              AND (p.owner_user_id = :user_id OR p.linked_user_id = :user_id)
            """
        )
        result = await self.session.execute(
            check,
            {"schedule_id": schedule_id, "user_id": user_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return ScheduleSnoozeResponse(
                success=False,
                message="Schedule not found, inactive, or access denied.",
            )

        remind_time = row.get("remind_time")
        if remind_time is None:
            return ScheduleSnoozeResponse(
                success=False,
                message="Schedule has no remind_time.",
            )

        tz_name = row.get("remind_tz") or "UTC"
        try:
            tz = ZoneInfo(str(tz_name))
        except Exception:
            tz = ZoneInfo("UTC")

        now_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        occurrence_date = datetime.now(tz).date()
        base_time_slot = remind_time.strftime("%H:%M")
        snoozed_until = (now_utc + timedelta(minutes=request.minutes)).replace(
            second=0,
            microsecond=0,
        )

        await self.session.execute(
            text(
                """
                INSERT INTO schedule_snooze_overrides (
                    schedule_id,
                    occurrence_date,
                    base_time_slot,
                    snooze_until_utc,
                    action_by
                )
                VALUES (
                    :schedule_id,
                    :occurrence_date,
                    :base_time_slot,
                    :snooze_until_utc,
                    :action_by
                )
                ON CONFLICT (schedule_id, occurrence_date, base_time_slot)
                DO UPDATE
                SET snooze_until_utc = EXCLUDED.snooze_until_utc,
                    action_by = EXCLUDED.action_by,
                    created_at = now(),
                    consumed_at = NULL
                """
            ),
            {
                "schedule_id": schedule_id,
                "occurrence_date": occurrence_date,
                "base_time_slot": base_time_slot,
                "snooze_until_utc": snoozed_until,
                "action_by": user_id,
            },
        )

        await self.session.execute(
            text(
                """
                INSERT INTO schedule_logs (schedule_id, status, action_by)
                VALUES (:schedule_id, 'SNOOZED', :action_by)
                """
            ),
            {
                "schedule_id": schedule_id,
                "action_by": user_id,
            },
        )

        return ScheduleSnoozeResponse(
            success=True,
            message=f"Snoozed for {request.minutes} minutes.",
            snoozed_until=snoozed_until,
        )


class ProcessDueSchedulePushesUseCase:
    """Find MEDICINE schedules due this minute in each schedule's remind_tz, dedupe, send push."""

    def __init__(self, session: AsyncSession, push_service: NotificationServicePort) -> None:
        self.session = session
        self._push = push_service

    @staticmethod
    def _extract_user_ids(row: dict) -> list[UUID]:
        user_ids: list[UUID] = []
        owner_user_id = row.get("owner_user_id")
        linked_user_id = row.get("linked_user_id")
        if owner_user_id is not None:
            user_ids.append(owner_user_id)
        if linked_user_id is not None and linked_user_id != owner_user_id:
            user_ids.append(linked_user_id)
        return user_ids

    async def _collect_fcm_tokens(self, user_ids: list[UUID]) -> list[str]:
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
        return fcm_tokens

    def _send_push(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: dict[str, str],
        channel: str,
    ) -> None:
        if len(tokens) == 1:
            self._push.send_to_device(
                tokens[0],
                title,
                body,
                data,
                android_channel_id=channel,
                android_sound="default",
            )
            return
        self._push.send_to_multiple(
            tokens,
            title,
            body,
            data,
            android_channel_id=channel,
            android_sound="default",
        )

    @staticmethod
    def _zone(tz_name: str | None) -> ZoneInfo:
        name = (tz_name or "UTC").strip() or "UTC"
        try:
            return ZoneInfo(name)
        except Exception:
            return ZoneInfo("UTC")

    async def execute(self) -> ScheduleDispatchResponse:
        channel = settings.fcm_android_channel_schedule
        now_utc = datetime.now(timezone.utc)

        rows_sql = text(
            """
            SELECT
                s.id AS schedule_id,
                s.remind_time AS remind_time,
                COALESCE(s.remind_tz, 'UTC') AS remind_tz,
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
            tz = self._zone(row.get("remind_tz"))
            now_local = now_utc.astimezone(tz)
            if rt.hour != now_local.hour or rt.minute != now_local.minute:
                continue

            occurrence_date: date = now_local.date()

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

            user_ids = self._extract_user_ids(row)

            if not user_ids:
                errors += 1
                await self.session.execute(
                    text("DELETE FROM schedule_push_receipts WHERE id = :id"),
                    {"id": receipt_id},
                )
                continue

            device_tokens = await self._collect_fcm_tokens(user_ids)

            if not device_tokens:
                logger.warning(
                    "No push tokens for schedule %s users %s", schedule_id, user_ids
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
                self._send_push(device_tokens, title, body, data, channel)
                sent += 1
            except Exception as e:
                logger.exception("Push failed for schedule %s: %s", schedule_id, e)
                await self.session.execute(
                    text("DELETE FROM schedule_push_receipts WHERE id = :id"),
                    {"id": receipt_id},
                )
                errors += 1

        # Process overdue pending snoozes (retry-able until consumed).
        now = now_utc
        snooze_rows = await self.session.execute(
            text(
                """
                SELECT
                    o.id AS override_id,
                    o.schedule_id AS schedule_id,
                    o.occurrence_date AS occurrence_date,
                    o.snooze_until_utc AS snooze_until_utc,
                    s.title AS title,
                    mi.medicine_name AS medicine_name,
                    p.full_name AS profile_name,
                    p.owner_user_id AS owner_user_id,
                    p.linked_user_id AS linked_user_id
                FROM schedule_snooze_overrides o
                JOIN schedules s ON s.id = o.schedule_id
                JOIN profiles p ON p.id = s.profile_id
                LEFT JOIN medicine_inventory mi ON mi.id = s.medicine_id
                WHERE o.consumed_at IS NULL
                  AND s.status = 'ACTIVE'
                  AND s.category = 'MEDICINE'
                  AND o.snooze_until_utc <= :now_utc
                ORDER BY o.snooze_until_utc ASC
                LIMIT 500
                """
            ),
            {"now_utc": now},
        )

        for row in snooze_rows.mappings().all():
            processed += 1
            schedule_id = row["schedule_id"]
            override_id = row["override_id"]
            override_occurrence_date = row["occurrence_date"]
            snooze_until = row.get("snooze_until_utc")

            if snooze_until is None:
                await self.session.execute(
                    text(
                        "UPDATE schedule_snooze_overrides SET consumed_at = now() WHERE id = :id"
                    ),
                    {"id": override_id},
                )
                continue

            snooze_time_slot = snooze_until.strftime("%H:%M")
            r2 = await self.session.execute(
                text(
                    """
                    INSERT INTO schedule_push_receipts (schedule_id, occurrence_date, time_slot)
                    VALUES (:schedule_id, :occurrence_date, :time_slot)
                    ON CONFLICT (schedule_id, occurrence_date, time_slot) DO NOTHING
                    RETURNING id
                    """
                ),
                {
                    "schedule_id": schedule_id,
                    "occurrence_date": override_occurrence_date,
                    "time_slot": snooze_time_slot,
                },
            )
            receipt_id = r2.scalar_one_or_none()
            if receipt_id is None:
                skipped_duplicate += 1
                await self.session.execute(
                    text(
                        "UPDATE schedule_snooze_overrides SET consumed_at = now() WHERE id = :id"
                    ),
                    {"id": override_id},
                )
                continue

            await self.session.flush()

            profile_name = row.get("profile_name") or "Thành viên"
            med = row.get("medicine_name") or row.get("title") or "Thuốc"
            title = f"Nhắc uống thuốc — {profile_name}"
            body = str(med)
            user_ids = self._extract_user_ids(row)

            if not user_ids:
                errors += 1
                await self.session.execute(
                    text("DELETE FROM schedule_push_receipts WHERE id = :id"),
                    {"id": receipt_id},
                )
                continue

            device_tokens = await self._collect_fcm_tokens(user_ids)
            if not device_tokens:
                logger.warning(
                    "No push tokens for snooze schedule %s users %s",
                    schedule_id,
                    user_ids,
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
                "occurrence_date": str(override_occurrence_date),
                "time_slot": snooze_time_slot,
                "action": "compliance",
            }

            try:
                self._send_push(device_tokens, title, body, data, channel)
                await self.session.execute(
                    text(
                        "UPDATE schedule_snooze_overrides SET consumed_at = now() WHERE id = :id"
                    ),
                    {"id": override_id},
                )
                sent += 1
            except Exception as e:
                logger.exception("Push failed for snooze schedule %s: %s", schedule_id, e)
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

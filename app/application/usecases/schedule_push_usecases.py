from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Sequence
from uuid import UUID
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
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

        logger.info(
            "Schedule compliance: schedule_id=%s user_id=%s outcome=%s source=%s occurrence_date=%s",
            schedule_id,
            user_id,
            request.outcome,
            request.source,
            occurrence_date,
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

    async def _collect_recipient_user_ids(self, row: dict) -> list[UUID]:
        base_user_ids = self._extract_user_ids(row)
        profile_id = row.get("profile_id")
        if profile_id is None:
            return base_user_ids

        family_rows = await self.session.execute(
            text(
                """
                SELECT DISTINCT uid
                FROM family_memberships fm1
                JOIN family_memberships fm2 ON fm2.family_id = fm1.family_id
                JOIN profiles p2 ON p2.id = fm2.profile_id
                CROSS JOIN LATERAL (
                    VALUES (p2.owner_user_id), (p2.linked_user_id)
                ) AS t(uid)
                WHERE fm1.profile_id = :profile_id
                  AND uid IS NOT NULL
                """
            ),
            {"profile_id": profile_id},
        )

        merged: list[UUID] = []
        seen: set[UUID] = set()
        for uid in base_user_ids + [r[0] for r in family_rows.fetchall() if r[0] is not None]:
            if uid not in seen:
                seen.add(uid)
                merged.append(uid)
        return merged

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

        expo_tokens = [
            tok for tok in fcm_tokens if tok.startswith("ExponentPushToken[")
        ]
        if expo_tokens:
            return expo_tokens

        return fcm_tokens

    async def _clear_failed_tokens(self, failed_tokens: Sequence[str]) -> None:
        cleaned = [tok.strip() for tok in failed_tokens if isinstance(tok, str) and tok.strip()]
        if not cleaned:
            return
        await self.session.execute(
            text(
                """
                UPDATE user_devices
                SET fcm_token = NULL
                WHERE fcm_token = ANY(:tokens)
                """
            ),
            {"tokens": cleaned},
        )

    def _send_push(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: dict[str, str],
        channel: str,
        *,
        notification_category_id: str | None = None,
    ) -> tuple[int, int, list[str]]:
        return self._push.send_to_multiple(
            tokens,
            title,
            body,
            data,
            android_channel_id=channel,
            android_sound="default",
            notification_category_id=notification_category_id,
        )

    @staticmethod
    def _zone(tz_name: str | None) -> ZoneInfo:
        name = (tz_name or "UTC").strip() or "UTC"
        try:
            return ZoneInfo(name)
        except Exception:
            return ZoneInfo("UTC")

    @staticmethod
    def _minute_of_day(hour: int, minute: int) -> int:
        return hour * 60 + minute

    @classmethod
    def _is_due_in_grace_window(
        cls,
        remind_time: time,
        now_local: datetime,
        grace_minutes: int,
    ) -> bool:
        now_minute = cls._minute_of_day(now_local.hour, now_local.minute)
        remind_minute = cls._minute_of_day(remind_time.hour, remind_time.minute)
        diff = now_minute - remind_minute
        return 0 <= diff <= grace_minutes

    @staticmethod
    def _rrule_matches_today(rrule_str: str | None, today: date) -> bool:
        """Check if *today* is a valid occurrence according to the rrule.

        Returns True when:
        - rrule_str is None/empty (legacy: treat as daily)
        - rrule_str is exactly 'FREQ=DAILY' (every day)
        - today is listed in the set of occurrences generated by the rrule
        """
        if not rrule_str or rrule_str.strip().upper() == "FREQ=DAILY":
            return True
        try:
            rule = rrulestr(
                f"RRULE:{rrule_str}",
                dtstart=datetime.combine(today - timedelta(days=730), datetime.min.time()),
                ignoretz=True,
            )
            # Generate occurrences up to end of today.
            end_of_today = datetime.combine(today, datetime.max.time())
            start_of_today = datetime.combine(today, datetime.min.time())
            for occ in rule:
                if occ > end_of_today:
                    break
                if occ >= start_of_today:
                    return True
            return False
        except Exception:
            # If parsing fails, fall back to allowing (don't block push).
            logger.warning("Failed to parse rrule '%s', treating as daily.", rrule_str)
            return True

    @staticmethod
    def _rrule_is_exhausted(rrule_str: str | None, today: date) -> bool:
        """Check if a COUNT-limited rrule has no more occurrences after today."""
        if not rrule_str:
            return False
        upper = rrule_str.strip().upper()
        if "COUNT" not in upper:
            return False
        try:
            rule = rrulestr(
                f"RRULE:{rrule_str}",
                dtstart=datetime.combine(today - timedelta(days=730), datetime.min.time()),
                ignoretz=True,
            )
            after_today = datetime.combine(today + timedelta(days=1), datetime.min.time())
            for occ in rule:
                if occ >= after_today:
                    return False
            return True
        except Exception:
            return False

    async def execute(self) -> ScheduleDispatchResponse:
        channel = settings.fcm_android_channel_schedule
        grace_minutes = settings.schedule_dispatch_due_grace_minutes
        now_utc = datetime.now(timezone.utc)

        rows_sql = text(
            """
            SELECT
                s.id AS schedule_id,
                s.remind_time AS remind_time,
                COALESCE(s.remind_tz, 'UTC') AS remind_tz,
                s.title AS title,
                s.dosage_per_time AS dosage_per_time,
                s.rrule AS rrule,
                mi.medicine_name AS medicine_name,
                mi.unit AS medicine_unit,
                p.id AS profile_id,
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
            if not self._is_due_in_grace_window(rt, now_local, grace_minutes):
                continue

            occurrence_date: date = now_local.date()

            # ── rrule gate: skip if today is not a valid occurrence ──
            rrule_raw = row.get("rrule")
            if not self._rrule_matches_today(rrule_raw, occurrence_date):
                continue

            # ── Auto-complete exhausted COUNT schedules ──
            schedule_id: UUID = row["schedule_id"]
            if self._rrule_is_exhausted(rrule_raw, occurrence_date):
                await self.session.execute(
                    text("UPDATE schedules SET status = 'COMPLETED' WHERE id = :sid AND status = 'ACTIVE'"),
                    {"sid": schedule_id},
                )
                logger.info("Schedule %s auto-completed (rrule COUNT exhausted).", schedule_id)
                continue

            processed += 1
            time_slot = rt.strftime("%H:%M")

            ins_receipt = text(
                """
                INSERT INTO schedule_push_receipts (schedule_id, occurrence_date, time_slot)
                VALUES (:schedule_id, :occurrence_date, :time_slot)
                ON CONFLICT (schedule_id, occurrence_date, time_slot) DO NOTHING
                RETURNING id
                """
            )
            try:
                r2 = await self.session.execute(
                    ins_receipt,
                    {
                        "schedule_id": schedule_id,
                        "occurrence_date": occurrence_date,
                        "time_slot": time_slot,
                    },
                )
            except IntegrityError:
                # Schedule could be deleted between the initial list query and receipt insert.
                # Skip gracefully instead of failing the whole dispatch iteration.
                logger.info(
                    "Schedule %s disappeared before receipt insert; skipping.",
                    schedule_id,
                )
                continue
            receipt_id = r2.scalar_one_or_none()
            if receipt_id is None:
                skipped_duplicate += 1
                continue

            await self.session.flush()

            profile_name = row.get("profile_name") or "Thành viên"
            med = row.get("medicine_name") or row.get("title") or "Thuốc"
            title = f"Nhắc uống thuốc — {profile_name}"
            dosage = row.get("dosage_per_time")
            unit = row.get("medicine_unit") or "viên"
            if dosage is not None:
                body = f"{med}: uống {dosage} {unit} lúc {time_slot}."
            else:
                body = f"{med}: đến giờ uống thuốc lúc {time_slot}."

            user_ids = await self._collect_recipient_user_ids(row)

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
                "dosage_per_time": str(dosage) if dosage is not None else "",
                "dosage_unit": str(unit),
            }

            try:
                success_count, failure_count, failed_tokens = self._send_push(
                    device_tokens,
                    title,
                    body,
                    data,
                    channel,
                    notification_category_id="MEDICINE_REMINDER_ACTIONS",
                )
                if failure_count:
                    await self._clear_failed_tokens(failed_tokens)
                    logger.warning(
                        "Push partially failed for schedule %s (%s/%s)",
                        schedule_id,
                        failure_count,
                        len(device_tokens),
                    )
                if success_count > 0:
                    logger.warning(
                        "Push sent successfully for schedule %s (%s success, %s failed, time_slot=%s, occurrence_date=%s)",
                        schedule_id,
                        success_count,
                        failure_count,
                        time_slot,
                        occurrence_date,
                    )
                    sent += 1
                    continue
                await self.session.execute(
                    text("DELETE FROM schedule_push_receipts WHERE id = :id"),
                    {"id": receipt_id},
                )
                errors += 1
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
                    s.dosage_per_time AS dosage_per_time,
                    mi.medicine_name AS medicine_name,
                    mi.unit AS medicine_unit,
                    p.id AS profile_id,
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
            try:
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
            except IntegrityError:
                # Override row can race with schedule deletion in another request.
                # Mark override consumed so it does not retry forever.
                logger.info(
                    "Snooze override %s skipped because schedule %s no longer exists.",
                    override_id,
                    schedule_id,
                )
                await self.session.execute(
                    text(
                        "UPDATE schedule_snooze_overrides SET consumed_at = now() WHERE id = :id"
                    ),
                    {"id": override_id},
                )
                continue
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
            dosage = row.get("dosage_per_time")
            unit = row.get("medicine_unit") or "viên"
            if dosage is not None:
                body = f"{med}: uống {dosage} {unit} ngay bây giờ."
            else:
                body = f"{med}: nhắc lại lịch uống thuốc."
            user_ids = await self._collect_recipient_user_ids(row)

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
                "dosage_per_time": str(dosage) if dosage is not None else "",
                "dosage_unit": str(unit),
            }

            try:
                success_count, failure_count, failed_tokens = self._send_push(
                    device_tokens,
                    title,
                    body,
                    data,
                    channel,
                    notification_category_id="MEDICINE_REMINDER_ACTIONS",
                )
                if failure_count:
                    await self._clear_failed_tokens(failed_tokens)
                    logger.warning(
                        "Push partially failed for snooze schedule %s (%s/%s)",
                        schedule_id,
                        failure_count,
                        len(device_tokens),
                    )
                if success_count == 0:
                    await self.session.execute(
                        text("DELETE FROM schedule_push_receipts WHERE id = :id"),
                        {"id": receipt_id},
                    )
                    errors += 1
                    continue
                logger.warning(
                    "Push sent successfully for snooze schedule %s (%s success, %s failed, time_slot=%s, occurrence_date=%s)",
                    schedule_id,
                    success_count,
                    failure_count,
                    snooze_time_slot,
                    override_occurrence_date,
                )
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

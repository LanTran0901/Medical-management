from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.notification_dto import ScheduleDispatchResponse
from app.application.ports.notification_port import NotificationServicePort
from app.core.config import settings

logger = logging.getLogger(__name__)


class ProcessDueAppointmentReminderPushesUseCase:
    """Fire push when now matches (appointment_at - remind_before_minutes), deduped."""

    def __init__(self, session: AsyncSession, push_service: NotificationServicePort) -> None:
        self.session = session
        self._push = push_service

    async def _collect_tokens(self, user_ids: list[UUID]) -> list[str]:
        tokens: list[str] = []
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
                    tokens.append(tok)
        return tokens

    @staticmethod
    def _user_ids(row: dict) -> list[UUID]:
        out: list[UUID] = []
        o = row.get("owner_user_id")
        l = row.get("linked_user_id")
        if o is not None:
            out.append(o)
        if l is not None and l != o:
            out.append(l)
        return out

    def _send(
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

    async def execute(self) -> ScheduleDispatchResponse:
        channel = settings.fcm_android_channel_schedule
        now = datetime.now(timezone.utc)
        current_bucket = now.replace(second=0, microsecond=0)

        q = text(
            """
            SELECT
                ar.id AS reminder_id,
                ar.type::text AS reminder_type,
                ar.title AS title,
                ar.appointment_at AS appointment_at,
                ar.remind_before_minutes AS remind_before_minutes,
                ar.vaccine_name AS vaccine_name,
                ar.hospital_name AS hospital_name,
                p.owner_user_id AS owner_user_id,
                p.linked_user_id AS linked_user_id
            FROM appointment_reminders ar
            JOIN profiles p ON p.id = ar.profile_id
            WHERE ar.status = 'pending'
            """
        )
        rows = (await self.session.execute(q)).mappings().all()

        processed = 0
        sent = 0
        skipped_duplicate = 0
        errors = 0

        for row in rows:
            appt_at = row.get("appointment_at")
            if appt_at is None:
                continue
            if appt_at.tzinfo is None:
                appt_at = appt_at.replace(tzinfo=timezone.utc)
            else:
                appt_at = appt_at.astimezone(timezone.utc)

            before = int(row.get("remind_before_minutes") or 60)
            remind_at = appt_at - timedelta(minutes=before)
            fire_bucket = remind_at.replace(second=0, microsecond=0)
            if fire_bucket != current_bucket:
                continue

            processed += 1
            reminder_id: UUID = row["reminder_id"]
            rtype = row.get("reminder_type") or "checkup"

            ins = text(
                """
                INSERT INTO appointment_reminder_push_receipts (reminder_id, fire_minute_utc)
                VALUES (:rid, :fm)
                ON CONFLICT (reminder_id, fire_minute_utc) DO NOTHING
                RETURNING id
                """
            )
            r2 = await self.session.execute(
                ins,
                {"rid": reminder_id, "fm": fire_bucket},
            )
            receipt_id = r2.scalar_one_or_none()
            if receipt_id is None:
                skipped_duplicate += 1
                continue

            await self.session.flush()

            category = "VACCINE" if rtype == "vaccine" else "CHECKUP"
            title_txt = str(row.get("title") or "Lịch hẹn")
            if category == "VACCINE":
                vn = row.get("vaccine_name")
                body_txt = f"{vn}" if vn else title_txt
            else:
                hn = row.get("hospital_name")
                body_txt = f"{hn}" if hn else title_txt

            uids = self._user_ids(row)
            if not uids:
                errors += 1
                await self.session.execute(
                    text(
                        "DELETE FROM appointment_reminder_push_receipts WHERE id = :id"
                    ),
                    {"id": receipt_id},
                )
                continue

            tokens = await self._collect_tokens(uids)
            if not tokens:
                logger.warning("No push tokens for appointment_reminder %s", reminder_id)
                errors += 1
                await self.session.execute(
                    text(
                        "DELETE FROM appointment_reminder_push_receipts WHERE id = :id"
                    ),
                    {"id": receipt_id},
                )
                continue

            data = {
                "appointment_reminder_id": str(reminder_id),
                "category": category,
                "action": "open",
            }

            try:
                self._send(tokens, title_txt, body_txt, data, channel)
                sent += 1
            except Exception as e:
                logger.exception("Push failed for appointment_reminder %s: %s", reminder_id, e)
                errors += 1
                await self.session.execute(
                    text(
                        "DELETE FROM appointment_reminder_push_receipts WHERE id = :id"
                    ),
                    {"id": receipt_id},
                )

        return ScheduleDispatchResponse(
            processed=processed,
            sent=sent,
            skipped_duplicate=skipped_duplicate,
            errors=errors,
        )

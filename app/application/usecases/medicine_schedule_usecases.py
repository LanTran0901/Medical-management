from __future__ import annotations

import uuid
from datetime import time
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.medicine_schedule_dto import (
    CreateMedicineScheduleRequest,
    MedicineScheduleResponse,
    PatchMedicineScheduleRequest,
)
from app.application.family_errors import ConflictError, ForbiddenError, NotFoundError
from app.application.usecases.access_control_usecases import AccessControlService


def _parse_hhmm_to_time(s: str) -> time:
    parts = s.strip().split(":")
    return time(hour=int(parts[0]), minute=int(parts[1]), second=0)


def _time_to_hhmm(t: time | None) -> str | None:
    if t is None:
        return None
    return t.strftime("%H:%M")


def _validate_remind_tz(name: str | None) -> str:
    n = (name or "UTC").strip() or "UTC"
    try:
        ZoneInfo(n)
    except Exception as exc:
        raise ValueError(f"Invalid remind_tz: {n}") from exc
    return n


class MedicineScheduleService:
    def __init__(self, session: AsyncSession, access: AccessControlService) -> None:
        self._session = session
        self._access = access

    async def _fallback_profile_id_for_family(self, family_id: UUID, user_id: UUID) -> UUID | None:
        row = await self._session.execute(
            text(
                """
                SELECT profile_id
                FROM family_memberships
                WHERE family_id = :fid AND user_id = :uid
                ORDER BY created_at ASC
                LIMIT 1
                """
            ),
            {"fid": family_id, "uid": user_id},
        )
        return row.scalar_one_or_none()

    async def _ensure_medicine_inventory_mirror(
        self,
        item_id: UUID,
        user_id: UUID,
        *,
        profile_id_hint: UUID | None = None,
    ) -> None:
        family_row = await self._session.execute(
            text(
                """
                SELECT
                    id,
                    family_id,
                    medicine_name,
                    quantity_stock,
                    unit,
                    expiry_date,
                    storage_location,
                    note,
                    min_stock_alert,
                    low_stock_alert_enabled,
                    expiry_alert_days_before
                FROM family_medicine_inventory
                WHERE id = :item_id
                LIMIT 1
                """
            ),
            {"item_id": item_id},
        )
        family_item = family_row.mappings().one_or_none()
        if family_item is None:
            return

        family_id: UUID = family_item["family_id"]
        await self._access.require_family_admin(family_id, user_id)

        profile_id = profile_id_hint or await self._fallback_profile_id_for_family(
            family_id,
            user_id,
        )

        await self._session.execute(
            text(
                """
                INSERT INTO medicine_inventory (
                    id,
                    profile_id,
                    medicine_name,
                    medicine_type,
                    expiry_date,
                    quantity_stock,
                    unit,
                    min_stock_alert,
                    instruction,
                    storage_location,
                    expiry_alert_days_before,
                    low_stock_alert_enabled,
                    use_tags
                )
                VALUES (
                    :id,
                    :profile_id,
                    :medicine_name,
                    NULL,
                    :expiry_date,
                    :quantity_stock,
                    :unit,
                    :min_stock_alert,
                    :instruction,
                    :storage_location,
                    :expiry_alert_days_before,
                    :low_stock_alert_enabled,
                    '{}'::text[]
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": family_item["id"],
                "profile_id": profile_id,
                "medicine_name": family_item["medicine_name"],
                "expiry_date": family_item["expiry_date"],
                "quantity_stock": family_item["quantity_stock"],
                "unit": family_item["unit"],
                "min_stock_alert": family_item["min_stock_alert"],
                "instruction": family_item["note"],
                "storage_location": family_item["storage_location"],
                "expiry_alert_days_before": family_item[
                    "expiry_alert_days_before"
                ],
                "low_stock_alert_enabled": family_item[
                    "low_stock_alert_enabled"
                ],
            },
        )

    async def _profile_in_family(self, profile_id: UUID, family_id: UUID) -> bool:
        r = await self._session.execute(
            text(
                """
                SELECT 1 FROM family_memberships
                WHERE profile_id = :pid AND family_id = :fid
                LIMIT 1
                """
            ),
            {"pid": profile_id, "fid": family_id},
        )
        return r.scalar_one_or_none() is not None

    async def list_for_medicine(
        self,
        item_id: UUID,
        user_id: UUID,
    ) -> list[MedicineScheduleResponse]:
        try:
            await self._access.require_medicine_item_write(item_id, user_id)
        except NotFoundError:
            await self._ensure_medicine_inventory_mirror(item_id, user_id)
            await self._access.require_medicine_item_write(item_id, user_id)

        q = text(
            """
            SELECT
                s.id, s.profile_id, s.medicine_id, s.title, s.category::text,
                s.remind_time, COALESCE(s.remind_tz, 'UTC') AS remind_tz,
                s.dosage_per_time, s.rrule, s.status::text
            FROM schedules s
            WHERE s.medicine_id = :mid AND s.category = 'MEDICINE'
            ORDER BY s.remind_time NULLS LAST
            """
        )
        result = await self._session.execute(q, {"mid": item_id})
        rows = result.mappings().all()
        out: list[MedicineScheduleResponse] = []
        for row in rows:
            rt = row["remind_time"]
            dpt = row.get("dosage_per_time")
            out.append(
                MedicineScheduleResponse(
                    id=row["id"],
                    profile_id=row["profile_id"],
                    medicine_id=row["medicine_id"],
                    title=row.get("title"),
                    category=row.get("category") or "MEDICINE",
                    remind_time=_time_to_hhmm(rt) if rt is not None else None,
                    remind_tz=str(row.get("remind_tz") or "UTC"),
                    dosage_per_time=str(dpt) if dpt is not None else None,
                    rrule=row.get("rrule"),
                    status=row.get("status") or "ACTIVE",
                )
            )
        return out

    async def create(
        self,
        item_id: UUID,
        user_id: UUID,
        body: CreateMedicineScheduleRequest,
    ) -> MedicineScheduleResponse:
        try:
            ctx = await self._access.require_medicine_item_write(item_id, user_id)
        except NotFoundError:
            await self._ensure_medicine_inventory_mirror(
                item_id,
                user_id,
                profile_id_hint=body.profile_id,
            )
            ctx = await self._access.require_medicine_item_write(item_id, user_id)
        if not ctx.family_ids:
            raise ForbiddenError("Medicine item is not linked to a family")
        family_id = ctx.family_ids[0]

        if not await self._profile_in_family(body.profile_id, family_id):
            raise ForbiddenError("Profile is not a member of this family")

        rt = _parse_hhmm_to_time(body.remind_time)
        remind_tz = _validate_remind_tz(body.remind_tz)
        rrule = body.rrule if body.rrule else "FREQ=DAILY"

        dup = await self._session.execute(
            text(
                """
                SELECT id FROM schedules
                WHERE profile_id = :pid AND medicine_id = :mid
                  AND remind_time = :rt AND category = 'MEDICINE'
                """
            ),
            {"pid": body.profile_id, "mid": item_id, "rt": rt},
        )
        if dup.scalar_one_or_none() is not None:
            raise ConflictError("Schedule already exists for this profile, medicine, and time")

        title = body.title
        if not title:
            title = f"Nhắc uống thuốc — {rt.strftime('%H:%M')}"

        schedule_id = uuid.uuid4()
        dosage = body.dosage_per_time

        await self._session.execute(
            text(
                """
                INSERT INTO schedules (
                    id, profile_id, medicine_id, title, category,
                    remind_time, remind_tz, dosage_per_time, rrule, status
                )
                VALUES (
                    :id, :profile_id, :medicine_id, :title, 'MEDICINE',
                    :remind_time, :remind_tz, :dosage_per_time, :rrule, 'ACTIVE'
                )
                """
            ),
            {
                "id": schedule_id,
                "profile_id": body.profile_id,
                "medicine_id": item_id,
                "title": title,
                "remind_time": rt,
                "remind_tz": remind_tz,
                "dosage_per_time": dosage,
                "rrule": rrule,
            },
        )

        await self._session.execute(
            text(
                """
                INSERT INTO schedule_logs (schedule_id, status, action_by)
                VALUES (:schedule_id, 'CREATED', :action_by)
                """
            ),
            {"schedule_id": schedule_id, "action_by": user_id},
        )

        return MedicineScheduleResponse(
            id=schedule_id,
            profile_id=body.profile_id,
            medicine_id=item_id,
            title=title,
            category="MEDICINE",
            remind_time=body.remind_time,
            remind_tz=remind_tz,
            dosage_per_time=str(dosage) if dosage is not None else None,
            rrule=rrule,
            status="ACTIVE",
        )

    async def patch(
        self,
        schedule_id: UUID,
        user_id: UUID,
        body: PatchMedicineScheduleRequest,
    ) -> MedicineScheduleResponse:
        scope = await self._session.execute(
            text(
                """
                SELECT s.id, s.profile_id, s.medicine_id, fm.family_id
                FROM schedules s
                JOIN family_memberships fm ON fm.profile_id = s.profile_id
                WHERE s.id = :sid AND s.category = 'MEDICINE'
                """
            ),
            {"sid": schedule_id},
        )
        sc = scope.mappings().one_or_none()
        if sc is None:
            raise NotFoundError("Schedule not found")

        await self._access.require_medicine_item_write(sc["medicine_id"], user_id)
        family_id: UUID = sc["family_id"]

        if not await self._profile_in_family(sc["profile_id"], family_id):
            raise ForbiddenError("Invalid schedule scope")

        sets: list[str] = []
        params: dict = {}

        if body.status is not None:
            sets.append("status = CAST(:st AS schedule_status)")
            params["st"] = body.status
        if body.remind_time is not None:
            sets.append("remind_time = :rt")
            params["rt"] = _parse_hhmm_to_time(body.remind_time)
        if body.remind_tz is not None:
            sets.append("remind_tz = :remind_tz")
            params["remind_tz"] = _validate_remind_tz(body.remind_tz)
        if body.title is not None:
            sets.append("title = :title")
            params["title"] = body.title
        if body.dosage_per_time is not None:
            sets.append("dosage_per_time = :dpt")
            params["dpt"] = body.dosage_per_time
        if body.rrule is not None:
            sets.append("rrule = :rrule")
            params["rrule"] = body.rrule

        if sets:
            params["qid"] = schedule_id
            await self._session.execute(
                text(f"UPDATE schedules SET {', '.join(sets)} WHERE id = :qid"),
                params,
            )

        row2 = await self._session.execute(
            text(
                """
                SELECT id, profile_id, medicine_id, title, category::text,
                       remind_time, COALESCE(remind_tz, 'UTC') AS remind_tz,
                       dosage_per_time, rrule, status::text
                FROM schedules WHERE id = :sid
                """
            ),
            {"sid": schedule_id},
        )
        u = row2.mappings().one()
        rt = u["remind_time"]
        dpt = u.get("dosage_per_time")
        return MedicineScheduleResponse(
            id=u["id"],
            profile_id=u["profile_id"],
            medicine_id=u["medicine_id"],
            title=u.get("title"),
            category=u.get("category") or "MEDICINE",
            remind_time=_time_to_hhmm(rt) if rt is not None else None,
            remind_tz=str(u.get("remind_tz") or "UTC"),
            dosage_per_time=str(dpt) if dpt is not None else None,
            rrule=u.get("rrule"),
            status=u.get("status") or "ACTIVE",
        )

    async def delete(
        self,
        schedule_id: UUID,
        user_id: UUID,
    ) -> None:
        row = await self._session.execute(
            text(
                """
                SELECT s.id, s.profile_id, s.medicine_id, fm.family_id
                FROM schedules s
                JOIN family_memberships fm ON fm.profile_id = s.profile_id
                WHERE s.id = :sid AND s.category = 'MEDICINE'
                """
            ),
            {"sid": schedule_id},
        )
        cur = row.mappings().one_or_none()
        if cur is None:
            raise NotFoundError("Schedule not found")

        await self._access.require_medicine_item_write(cur["medicine_id"], user_id)
        family_id: UUID = cur["family_id"]

        if not await self._profile_in_family(cur["profile_id"], family_id):
            raise ForbiddenError("Invalid schedule scope")

        await self._session.execute(
            text("DELETE FROM schedules WHERE id = :sid"),
            {"sid": schedule_id},
        )

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from app.application.family_errors import ForbiddenError, NotFoundError
from app.application.ports.family_port import FamilyRepositoryPort
from app.application.ports.medicine_inventory_port import MedicineInventoryRepositoryPort
from app.application.dtos.medicine_dto import (
    CreateMedicineInventoryRequest,
    MedicineInventoryResponse,
    MedicineReminderResponse,
    PatchMedicineInventoryRequest,
)
from app.application.dtos.user_dto import UserMeMedicineInventoryItem
from app.application.usecases.access_control_usecases import AccessControlService
from app.domain.entities.medicine_inventory import MedicineInventory
from app.domain.entities.medicine_reminder import MedicineReminder


def _alert_flags(m: MedicineInventory, today: date) -> tuple[bool, bool, bool]:
    """Returns (low_stock, expiring, expired)."""
    low = False
    if m.low_stock_alert_enabled and m.min_stock_alert is not None and m.quantity_stock is not None:
        low = m.quantity_stock <= m.min_stock_alert

    expired = False
    expiring = False
    if m.expiry_date is not None:
        if m.expiry_date < today:
            expired = True
        elif m.expiry_date == today:
            expiring = True
        elif m.expiry_alert_days_before is not None:
            start = m.expiry_date - timedelta(days=int(m.expiry_alert_days_before))
            if start <= today <= m.expiry_date:
                expiring = True
    return low, expiring, expired


def _to_response(m: MedicineInventory) -> MedicineInventoryResponse:
    today = date.today()
    low, expiring, expired = _alert_flags(m, today)
    return MedicineInventoryResponse(
        id=m.id,
        profile_id=m.profile_id,
        medicine_name=m.medicine_name,
        medicine_type=m.medicine_type,
        expiry_date=m.expiry_date,
        quantity_stock=m.quantity_stock,
        unit=m.unit,
        min_stock_alert=m.min_stock_alert,
        instruction=m.instruction,
        dosage_value=m.dosage_value,
        dosage_unit=m.dosage_unit,
        dosage_per_use_value=m.dosage_per_use_value,
        dosage_per_use_unit=m.dosage_per_use_unit,
        use_tags=m.use_tags,
        storage_location=m.storage_location,
        expiry_alert_days_before=m.expiry_alert_days_before,
        low_stock_alert_enabled=m.low_stock_alert_enabled,
        created_at=m.created_at,
        updated_at=m.updated_at,
        alert_low_stock=low,
        alert_expiring=expiring,
        alert_expired=expired,
    )


def _reminder_to_response(r: MedicineReminder) -> MedicineReminderResponse:
    return MedicineReminderResponse(
        id=r.id,
        medicine_inventory_id=r.medicine_inventory_id,
        enabled=r.enabled,
        start_date=r.start_date,
        repeat_every_value=r.repeat_every_value,
        repeat_every_unit=r.repeat_every_unit,
        active_days=r.active_days,
        times=r.times,
        remind_before_minutes=r.remind_before_minutes,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


class MedicineInventoryService:
    def __init__(
        self,
        repo: MedicineInventoryRepositoryPort,
        access: AccessControlService,
        family_repo: FamilyRepositoryPort,
    ) -> None:
        self._repo = repo
        self._access = access
        self._family_repo = family_repo

    async def list_items(
        self,
        family_id: UUID,
        user_id: UUID,
        *,
        alert: str | None,
    ) -> list[MedicineInventoryResponse]:
        await self._access.require_family_member(family_id, user_id)
        rows = await self._repo.list_by_family(family_id, alert=alert)
        return [_to_response(m) for m in rows]

    async def list_for_profile_with_reminders(
        self,
        profile_id: UUID,
        user_id: UUID,
    ) -> list[UserMeMedicineInventoryItem]:
        await self._access.require_profile_read(profile_id, user_id)
        rows = await self._repo.list_by_profile_id(profile_id)
        ids = [m.id for m in rows]
        reminders = await self._repo.list_medicine_reminders_by_inventory_ids(ids)
        out: list[UserMeMedicineInventoryItem] = []
        for m in rows:
            base = _to_response(m)
            rem = reminders.get(m.id)
            out.append(
                UserMeMedicineInventoryItem(
                    **base.model_dump(),
                    medicine_reminder=_reminder_to_response(rem) if rem is not None else None,
                )
            )
        return out

    async def get_item_by_id(self, item_id: UUID, user_id: UUID) -> MedicineInventoryResponse:
        context = await self._access.require_medicine_item_read(item_id, user_id)
        return _to_response(context.item)

    async def create_item(
        self,
        family_id: UUID,
        user_id: UUID,
        body: CreateMedicineInventoryRequest,
    ) -> MedicineInventoryResponse:
        await self._access.require_family_admin(family_id, user_id)
        if body.profile_id is None:
            raise ForbiddenError("profile_id is required for family medicine inventory")
        if not await self._family_repo.profile_in_family(body.profile_id, family_id):
            raise ForbiddenError("profile_id does not belong to this family")
        m = await self._repo.create(
            profile_id=body.profile_id,
            medicine_name=body.medicine_name,
            medicine_type=body.medicine_type,
            expiry_date=body.expiry_date,
            quantity_stock=body.quantity_stock,
            unit=body.unit,
            min_stock_alert=body.min_stock_alert,
            instruction=body.instruction,
            dosage_value=body.dosage_value,
            dosage_unit=body.dosage_unit,
            dosage_per_use_value=body.dosage_per_use_value,
            dosage_per_use_unit=body.dosage_per_use_unit,
            use_tags=body.use_tags,
            storage_location=body.storage_location,
            expiry_alert_days_before=body.expiry_alert_days_before,
            low_stock_alert_enabled=body.low_stock_alert_enabled,
        )
        return _to_response(m)

    async def patch_item(
        self,
        item_id: UUID,
        user_id: UUID,
        body: PatchMedicineInventoryRequest,
    ) -> MedicineInventoryResponse:
        await self._access.require_medicine_item_write(item_id, user_id)
        m = await self._repo.apply_patch(item_id, body.model_dump(exclude_unset=True))
        if m is None:
            raise NotFoundError("Medicine item not found")
        return _to_response(m)

    async def delete_item(self, item_id: UUID, user_id: UUID) -> bool:
        await self._access.require_medicine_item_write(item_id, user_id)
        return await self._repo.delete(item_id)

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from app.application.family_errors import NotFoundError
from app.application.ports.medicine_inventory_port import MedicineInventoryRepositoryPort
from app.application.dtos.medicine_dto import (
    CreateMedicineInventoryRequest,
    MedicineInventoryResponse,
    PatchMedicineInventoryRequest,
)
from app.application.usecases.access_control_usecases import AccessControlService
from app.domain.entities.medicine_inventory import MedicineInventory


def _alert_flags(m: MedicineInventory, today: date) -> tuple[bool, bool, bool]:
    """Returns (low_stock, expiring, expired)."""
    low = False
    if m.min_stock_alert is not None and m.quantity_stock is not None:
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
        family_id=m.family_id,
        medicine_name=m.medicine_name,
        medicine_type=m.medicine_type,
        expiry_date=m.expiry_date,
        quantity_stock=m.quantity_stock,
        unit=m.unit,
        min_stock_alert=m.min_stock_alert,
        instruction=m.instruction,
        expiry_alert_days_before=m.expiry_alert_days_before,
        alert_low_stock=low,
        alert_expiring=expiring,
        alert_expired=expired,
    )


class MedicineInventoryService:
    def __init__(
        self,
        repo: MedicineInventoryRepositoryPort,
        access: AccessControlService,
    ) -> None:
        self._repo = repo
        self._access = access

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
        m = await self._repo.create(
            family_id=family_id,
            medicine_name=body.medicine_name,
            medicine_type=body.medicine_type,
            expiry_date=body.expiry_date,
            quantity_stock=body.quantity_stock,
            unit=body.unit,
            min_stock_alert=body.min_stock_alert,
            instruction=body.instruction,
            expiry_alert_days_before=body.expiry_alert_days_before,
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

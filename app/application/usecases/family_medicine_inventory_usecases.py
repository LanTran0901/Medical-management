from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from app.application.dtos.medicine_dto import (
    CreateFamilyMedicineInventoryRequest,
    FamilyMedicineInventoryResponse,
)
from app.application.ports.family_medicine_inventory_port import FamilyMedicineInventoryRepositoryPort
from app.application.usecases.access_control_usecases import AccessControlService
from app.domain.entities.family_medicine_inventory import FamilyMedicineInventory


def _to_response(m: FamilyMedicineInventory) -> FamilyMedicineInventoryResponse:
    today = date.today()
    low_stock = m.low_stock_alert_enabled and m.quantity_stock <= m.min_stock_alert
    expiry_start = m.expiry_date - timedelta(days=max(m.expiry_alert_days_before, 0))
    expiring = expiry_start <= today <= m.expiry_date
    expired = m.expiry_date < today
    return FamilyMedicineInventoryResponse(
        id=m.id,
        family_id=m.family_id,
        created_by_user_id=m.created_by_user_id,
        medicine_name=m.medicine_name,
        quantity_stock=m.quantity_stock,
        unit=m.unit,
        expiry_date=m.expiry_date,
        storage_location=m.storage_location,
        note=m.note,
        min_stock_alert=m.min_stock_alert,
        low_stock_alert_enabled=m.low_stock_alert_enabled,
        expiry_alert_days_before=m.expiry_alert_days_before,
        created_at=m.created_at,
        updated_at=m.updated_at,
        alert_low_stock=low_stock,
        alert_expiring=expiring,
        alert_expired=expired,
    )


class FamilyMedicineInventoryService:
    def __init__(
        self,
        repo: FamilyMedicineInventoryRepositoryPort,
        access: AccessControlService,
    ) -> None:
        self._repo = repo
        self._access = access

    async def list_items(self, family_id: UUID, user_id: UUID) -> list[FamilyMedicineInventoryResponse]:
        await self._access.require_family_member(family_id, user_id)
        rows = await self._repo.list_by_family(family_id)
        return [_to_response(row) for row in rows]

    async def create_item(
        self,
        family_id: UUID,
        user_id: UUID,
        body: CreateFamilyMedicineInventoryRequest,
    ) -> FamilyMedicineInventoryResponse:
        membership = await self._access.require_family_admin(family_id, user_id)
        model = await self._repo.create(
            family_id=family_id,
            created_by_user_id=user_id,
            profile_id=membership.profile_id,
            medicine_name=body.medicine_name,
            quantity_stock=body.quantity_stock,
            unit=body.unit,
            expiry_date=body.expiry_date,
            storage_location=body.storage_location,
            note=body.note,
            min_stock_alert=body.min_stock_alert,
            low_stock_alert_enabled=body.low_stock_alert_enabled,
            expiry_alert_days_before=body.expiry_alert_days_before,
        )
        return _to_response(model)

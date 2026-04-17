from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.domain.entities.family_medicine_inventory import FamilyMedicineInventory


class FamilyMedicineInventoryRepositoryPort:
    async def list_by_family(self, family_id: UUID) -> list[FamilyMedicineInventory]:
        raise NotImplementedError

    async def create(
        self,
        *,
        family_id: UUID,
        created_by_user_id: UUID,
        profile_id: UUID,
        medicine_name: str,
        quantity_stock: Decimal,
        unit: str,
        expiry_date: date,
        storage_location: str | None,
        note: str | None,
        min_stock_alert: Decimal,
        low_stock_alert_enabled: bool,
        expiry_alert_days_before: int,
    ) -> FamilyMedicineInventory:
        raise NotImplementedError

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.domain.entities.medicine_inventory import MedicineInventory


class MedicineInventoryRepositoryPort:
    async def list_by_family(self, family_id: UUID, *, alert: str | None) -> list[MedicineInventory]:
        raise NotImplementedError

    async def get_by_id(self, item_id: UUID) -> MedicineInventory | None:
        raise NotImplementedError

    async def create(
        self,
        *,
        family_id: UUID,
        medicine_name: str,
        medicine_type: str | None,
        expiry_date: date | None,
        quantity_stock: Decimal | None,
        unit: str | None,
        min_stock_alert: Decimal | None,
        instruction: str | None,
        expiry_alert_days_before: int | None,
    ) -> MedicineInventory:
        raise NotImplementedError

    async def apply_patch(self, item_id: UUID, fields: dict[str, object]) -> MedicineInventory | None:
        raise NotImplementedError

    async def delete(self, item_id: UUID) -> bool:
        raise NotImplementedError

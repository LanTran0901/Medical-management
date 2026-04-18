from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.domain.entities.medicine_inventory import MedicineInventory
from app.domain.entities.medicine_reminder import MedicineReminder


class MedicineInventoryRepositoryPort:
    async def list_by_family(self, family_id: UUID, *, alert: str | None) -> list[MedicineInventory]:
        raise NotImplementedError

    async def list_by_profile_id(self, profile_id: UUID) -> list[MedicineInventory]:
        raise NotImplementedError

    async def list_medicine_reminders_by_inventory_ids(
        self, inventory_ids: list[UUID]
    ) -> dict[UUID, MedicineReminder]:
        raise NotImplementedError

    async def get_by_id(self, item_id: UUID) -> MedicineInventory | None:
        raise NotImplementedError

    async def create(
        self,
        *,
        profile_id: UUID | None,
        medicine_name: str,
        medicine_type: str | None,
        expiry_date: date | None,
        quantity_stock: Decimal | None,
        unit: str | None,
        min_stock_alert: Decimal | None,
        instruction: str | None,
        dosage_value: Decimal | None,
        dosage_unit: str | None,
        dosage_per_use_value: Decimal | None,
        dosage_per_use_unit: str | None,
        use_tags: list[str] | None,
        storage_location: str | None,
        expiry_alert_days_before: int | None,
        low_stock_alert_enabled: bool,
    ) -> MedicineInventory:
        raise NotImplementedError

    async def apply_patch(self, item_id: UUID, fields: dict[str, object]) -> MedicineInventory | None:
        raise NotImplementedError

    async def delete(self, item_id: UUID) -> bool:
        raise NotImplementedError

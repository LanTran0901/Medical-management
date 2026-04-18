from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MedicineInventory:
    """Domain shape for a medicine row (alerts computed at read time in use case)."""

    id: UUID
    profile_id: UUID | None
    medicine_name: str
    medicine_type: str | None
    expiry_date: date | None
    quantity_stock: Decimal | None
    unit: str | None
    min_stock_alert: Decimal | None
    instruction: str | None
    dosage_value: Decimal | None
    dosage_unit: str | None
    dosage_per_use_value: Decimal | None
    dosage_per_use_unit: str | None
    use_tags: list[str] | None
    storage_location: str | None
    expiry_alert_days_before: int | None
    low_stock_alert_enabled: bool
    created_at: datetime
    updated_at: datetime

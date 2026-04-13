from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FamilyMedicineInventory:
    id: UUID
    family_id: UUID
    created_by_user_id: UUID | None
    medicine_name: str
    quantity_stock: Decimal
    unit: str
    expiry_date: date
    storage_location: str | None
    note: str | None
    min_stock_alert: Decimal
    low_stock_alert_enabled: bool
    expiry_alert_days_before: int
    created_at: datetime
    updated_at: datetime

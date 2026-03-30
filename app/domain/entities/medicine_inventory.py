from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MedicineInventory:
    """Domain shape for a medicine row (alerts computed at read time in use case)."""

    id: UUID
    family_id: UUID
    medicine_name: str
    medicine_type: str | None
    expiry_date: date | None
    quantity_stock: Decimal | None
    unit: str | None
    min_stock_alert: Decimal | None
    instruction: str | None
    expiry_alert_days_before: int | None

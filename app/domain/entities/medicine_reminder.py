from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MedicineReminder:
    id: UUID
    medicine_inventory_id: UUID
    enabled: bool
    start_date: date | None
    repeat_every_value: int
    repeat_every_unit: str
    active_days: list[int]
    times: list[str]
    remind_before_minutes: int
    created_at: datetime
    updated_at: datetime

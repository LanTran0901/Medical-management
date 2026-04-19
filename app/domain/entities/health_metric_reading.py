from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(slots=True)
class HealthMetricReading:
    id: UUID
    profile_id: UUID
    metric_type: str
    measured_at: datetime
    systolic: int | None
    diastolic: int | None
    heart_rate: int | None
    weight_kg: Decimal | None
    glucose_mmol_l: Decimal | None
    status: str | None
    notes: str | None
    created_at: datetime
    deleted_at: datetime | None

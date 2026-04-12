from __future__ import annotations

from datetime import time
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateMedicineScheduleRequest(BaseModel):
    """Create one MEDICINE schedule row. `remind_time` is wall-clock UTC (matches dispatcher)."""

    profile_id: UUID
    remind_time: str = Field(..., description="HH:MM in 24h, UTC")
    title: str | None = Field(None, max_length=500)
    dosage_per_time: Decimal | None = None
    rrule: str | None = Field(None, description="Default FREQ=DAILY if omitted")

    @field_validator("remind_time")
    @classmethod
    def validate_hhmm(cls, v: str) -> str:
        parts = v.strip().split(":")
        if len(parts) != 2:
            raise ValueError("remind_time must be HH:MM")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("Invalid time")
        return f"{h:02d}:{m:02d}"


class PatchMedicineScheduleRequest(BaseModel):
    status: Literal["ACTIVE", "PAUSED", "COMPLETED"] | None = None
    remind_time: str | None = Field(None, description="HH:MM UTC")
    title: str | None = Field(None, max_length=500)
    dosage_per_time: Decimal | None = None
    rrule: str | None = None

    @field_validator("remind_time")
    @classmethod
    def validate_hhmm_optional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        parts = v.strip().split(":")
        if len(parts) != 2:
            raise ValueError("remind_time must be HH:MM")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("Invalid time")
        return f"{h:02d}:{m:02d}"


class MedicineScheduleResponse(BaseModel):
    id: UUID
    profile_id: UUID
    medicine_id: UUID
    title: str | None
    category: str
    remind_time: str | None
    dosage_per_time: str | None
    rrule: str | None
    status: str

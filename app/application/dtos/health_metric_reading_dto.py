from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class CreateHealthMetricReadingRequest(BaseModel):
    metric_type: str = Field(..., min_length=1, max_length=32)
    measured_at: datetime
    systolic: int | None = None
    diastolic: int | None = None
    heart_rate: int | None = None
    weight_kg: Decimal | None = None
    glucose_mmol_l: Decimal | None = None
    status: str | None = Field(None, max_length=32)
    notes: str | None = None


class PatchHealthMetricReadingRequest(BaseModel):
    metric_type: str | None = Field(None, min_length=1, max_length=32)
    measured_at: datetime | None = None
    systolic: int | None = None
    diastolic: int | None = None
    heart_rate: int | None = None
    weight_kg: Decimal | None = None
    glucose_mmol_l: Decimal | None = None
    status: str | None = Field(None, max_length=32)
    notes: str | None = None

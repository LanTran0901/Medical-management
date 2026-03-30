from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class MedicineInventoryResponse(BaseModel):
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
    alert_low_stock: bool = False
    alert_expiring: bool = False
    alert_expired: bool = False

    model_config = {"from_attributes": False}


class CreateMedicineInventoryRequest(BaseModel):
    medicine_name: str = Field(..., min_length=1, max_length=255)
    medicine_type: str | None = Field(None, max_length=128)
    expiry_date: date | None = None
    quantity_stock: Decimal | None = None
    unit: str | None = Field(None, max_length=64)
    min_stock_alert: Decimal | None = None
    instruction: str | None = None
    expiry_alert_days_before: int | None = Field(None, ge=0)


class PatchMedicineInventoryRequest(BaseModel):
    medicine_name: str | None = Field(None, min_length=1, max_length=255)
    medicine_type: str | None = Field(None, max_length=128)
    expiry_date: date | None = None
    quantity_stock: Decimal | None = None
    unit: str | None = Field(None, max_length=64)
    min_stock_alert: Decimal | None = None
    instruction: str | None = None
    expiry_alert_days_before: int | None = Field(None, ge=0)

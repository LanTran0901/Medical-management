from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class MedicineReminderResponse(BaseModel):
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


class MedicineInventoryResponse(BaseModel):
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
    alert_low_stock: bool = False
    alert_expiring: bool = False
    alert_expired: bool = False

    model_config = {"from_attributes": False}


class CreateMedicineInventoryRequest(BaseModel):
    profile_id: UUID | None = None
    medicine_name: str = Field(..., min_length=1, max_length=255)
    medicine_type: str | None = Field(None, max_length=128)
    expiry_date: date | None = None
    quantity_stock: Decimal | None = None
    unit: str | None = Field(None, max_length=64)
    min_stock_alert: Decimal | None = None
    instruction: str | None = None
    dosage_value: Decimal | None = None
    dosage_unit: str | None = Field(None, max_length=64)
    dosage_per_use_value: Decimal | None = None
    dosage_per_use_unit: str | None = Field(None, max_length=64)
    use_tags: list[str] | None = None
    storage_location: str | None = Field(None, max_length=255)
    expiry_alert_days_before: int | None = Field(None, ge=0)
    low_stock_alert_enabled: bool = True


class PatchMedicineInventoryRequest(BaseModel):
    profile_id: UUID | None = None
    medicine_name: str | None = Field(None, min_length=1, max_length=255)
    medicine_type: str | None = Field(None, max_length=128)
    expiry_date: date | None = None
    quantity_stock: Decimal | None = None
    unit: str | None = Field(None, max_length=64)
    min_stock_alert: Decimal | None = None
    instruction: str | None = None
    dosage_value: Decimal | None = None
    dosage_unit: str | None = Field(None, max_length=64)
    dosage_per_use_value: Decimal | None = None
    dosage_per_use_unit: str | None = Field(None, max_length=64)
    use_tags: list[str] | None = None
    storage_location: str | None = Field(None, max_length=255)
    expiry_alert_days_before: int | None = Field(None, ge=0)
    low_stock_alert_enabled: bool | None = None


class FamilyMedicineInventoryResponse(BaseModel):
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
    alert_low_stock: bool = False
    alert_expiring: bool = False
    alert_expired: bool = False


class CreateFamilyMedicineInventoryRequest(BaseModel):
    medicine_name: str = Field(..., min_length=1, max_length=255)
    quantity_stock: Decimal
    unit: str = Field(..., min_length=1, max_length=64)
    expiry_date: date
    storage_location: str | None = Field(None, max_length=255)
    note: str | None = None
    min_stock_alert: Decimal = Field(default=Decimal("0"))
    low_stock_alert_enabled: bool = True
    expiry_alert_days_before: int = Field(default=30, ge=0)

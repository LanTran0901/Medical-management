from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field, model_validator

from app.domain.remind_before import RemindBeforeUnit


class CreateAppointmentReminderRequest(BaseModel):
    """Create an appointment reminder (tái khám or vaccine)."""

    kind: Literal["checkup", "vaccine"] = Field(
        ...,
        validation_alias=AliasChoices("type", "kind"),
        description="checkup (tái khám) or vaccine",
    )
    title: str = Field(..., min_length=1, max_length=512)
    appointment_at: datetime
    reminder_enabled: bool = True
    remind_before_value: int | None = Field(default=None, ge=1)
    remind_before_unit: RemindBeforeUnit | None = None
    hospital_name: str | None = Field(None, max_length=512)
    department: str | None = Field(None, max_length=255)
    vaccine_name: str | None = Field(None, max_length=255)
    dose_number: int | None = None
    total_doses: int | None = None
    note: str | None = None
    follow_up_appointment_id: UUID | None = None
    vaccination_dose_id: UUID | None = None

    @model_validator(mode="after")
    def _validate_reminder(self) -> "CreateAppointmentReminderRequest":
        if not self.reminder_enabled:
            self.remind_before_value = None
            self.remind_before_unit = None
            return self

        if self.remind_before_value is None and self.remind_before_unit is None:
            self.remind_before_value = 60
            self.remind_before_unit = RemindBeforeUnit.MINUTES
            return self

        if self.remind_before_value is None or self.remind_before_unit is None:
            raise ValueError(
                "remind_before_value and remind_before_unit are required when reminder_enabled is true"
            )
        return self

    model_config = {"populate_by_name": True, "extra": "ignore"}


class PatchAppointmentReminderRequest(BaseModel):
    title: str | None = Field(None, max_length=512)
    appointment_at: datetime | None = None
    reminder_enabled: bool | None = None
    remind_before_value: int | None = Field(None, ge=1)
    remind_before_unit: RemindBeforeUnit | None = None
    hospital_name: str | None = None
    department: str | None = None
    vaccine_name: str | None = None
    dose_number: int | None = None
    total_doses: int | None = None
    note: str | None = None
    vaccination_dose_id: UUID | None = None
    status: Literal["pending", "done", "missed"] | None = None


class AppointmentReminderResponse(BaseModel):
    id: UUID
    profile_id: UUID
    kind: str = Field(
        ...,
        validation_alias="type",
        serialization_alias="type",
    )
    title: str
    hospital_name: str | None
    department: str | None
    appointment_at: datetime
    reminder_enabled: bool
    remind_before_value: int | None
    remind_before_unit: RemindBeforeUnit | None
    vaccine_name: str | None
    dose_number: int | None
    total_doses: int | None
    status: str
    note: str | None
    follow_up_appointment_id: UUID | None
    vaccination_dose_id: UUID | None

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
    }

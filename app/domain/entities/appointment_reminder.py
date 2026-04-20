from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AppointmentReminder:
    id: UUID
    profile_id: UUID
    reminder_type: str
    title: str
    hospital_name: str | None
    department: str | None
    appointment_at: datetime
    reminder_enabled: bool
    remind_before_value: int | None
    remind_before_unit: str | None
    vaccine_name: str | None
    dose_number: int | None
    total_doses: int | None
    status: str
    note: str | None
    follow_up_appointment_id: UUID | None
    vaccination_dose_id: UUID | None
    created_at: datetime
    updated_at: datetime

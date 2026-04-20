from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.application.dtos.appointment_reminder_dto import (
    CreateAppointmentReminderRequest,
)
from app.domain.remind_before import RemindBeforeUnit


def _base_payload() -> dict:
    return {
        "type": "checkup",
        "title": "Tai kham dinh ky",
        "appointment_at": datetime(2026, 4, 21, 8, 30, tzinfo=timezone.utc),
    }


def test_create_defaults_reminder_offset_when_enabled() -> None:
    dto = CreateAppointmentReminderRequest(**_base_payload())
    assert dto.reminder_enabled is True
    assert dto.remind_before_value == 60
    assert dto.remind_before_unit == RemindBeforeUnit.MINUTES


def test_create_turns_off_reminder_and_clears_offset() -> None:
    payload = _base_payload()
    payload.update(
        {
            "reminder_enabled": False,
            "remind_before_value": 3,
            "remind_before_unit": "DAYS",
        }
    )
    dto = CreateAppointmentReminderRequest(**payload)
    assert dto.reminder_enabled is False
    assert dto.remind_before_value is None
    assert dto.remind_before_unit is None


def test_create_rejects_half_offset_when_enabled() -> None:
    payload = _base_payload()
    payload.update(
        {
            "reminder_enabled": True,
            "remind_before_value": 2,
        }
    )
    with pytest.raises(ValidationError):
        CreateAppointmentReminderRequest(**payload)

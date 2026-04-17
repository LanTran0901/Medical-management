from __future__ import annotations

import pytest

from app.domain.remind_before import RemindBeforeUnit, remind_before_to_minutes


def test_remind_before_to_minutes_none_when_off() -> None:
    assert remind_before_to_minutes(None, None) is None


def test_remind_before_to_minutes_presets() -> None:
    assert remind_before_to_minutes(2, RemindBeforeUnit.HOURS) == 120
    assert remind_before_to_minutes(1, "DAYS") == 1440
    assert remind_before_to_minutes(3, "days") == 4320
    assert remind_before_to_minutes(1, "WEEKS") == 10080


def test_remind_before_to_minutes_rejects_mismatched_pair() -> None:
    with pytest.raises(ValueError, match="both"):
        remind_before_to_minutes(1, None)
    with pytest.raises(ValueError, match="both"):
        remind_before_to_minutes(None, "HOURS")


def test_remind_before_to_minutes_rejects_non_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        remind_before_to_minutes(0, "DAYS")


def test_remind_before_to_minutes_rejects_unknown_unit() -> None:
    with pytest.raises(ValueError, match="unknown"):
        remind_before_to_minutes(1, "YEARS")

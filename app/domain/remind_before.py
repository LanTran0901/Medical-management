"""Helpers for follow-up (and similar) reminder offsets stored as value + unit."""

from __future__ import annotations

from enum import StrEnum


class RemindBeforeUnit(StrEnum):
    MINUTES = "MINUTES"
    HOURS = "HOURS"
    DAYS = "DAYS"
    WEEKS = "WEEKS"


def remind_before_to_minutes(value: int | None, unit: str | None) -> int | None:
    """Convert stored offset to runtime minutes for scheduling.

    Returns ``None`` when reminder is off (no value/unit). Raises ``ValueError`` for unknown ``unit``.
    """
    if value is None and unit is None:
        return None
    if value is None or unit is None:
        raise ValueError("remind_before_value and remind_before_unit must both be set or both null")
    if value <= 0:
        raise ValueError("remind_before_value must be positive")

    try:
        u = unit if isinstance(unit, RemindBeforeUnit) else RemindBeforeUnit(str(unit).upper())
    except ValueError as exc:
        raise ValueError(f"unknown remind_before_unit: {unit!r}") from exc
    if u is RemindBeforeUnit.MINUTES:
        return value
    if u is RemindBeforeUnit.HOURS:
        return value * 60
    if u is RemindBeforeUnit.DAYS:
        return value * 24 * 60
    if u is RemindBeforeUnit.WEEKS:
        return value * 7 * 24 * 60
    raise ValueError(f"unknown remind_before_unit: {unit!r}")

"""appointment_reminders: add reminder_enabled and nullable remind offset.

Revision ID: 20260420_0900
Revises: 20260419_1200
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260420_0900"
down_revision: Union[str, None] = "20260419_1200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE appointment_reminders
        ADD COLUMN IF NOT EXISTS reminder_enabled BOOLEAN NOT NULL DEFAULT TRUE
        """
    )
    op.execute(
        """
        UPDATE appointment_reminders
        SET reminder_enabled = TRUE
        WHERE reminder_enabled IS NULL
        """
    )
    op.execute(
        """
        ALTER TABLE appointment_reminders
        ALTER COLUMN remind_before_value DROP NOT NULL,
        ALTER COLUMN remind_before_unit DROP NOT NULL
        """
    )
    op.execute(
        """
        ALTER TABLE appointment_reminders
        DROP CONSTRAINT IF EXISTS ck_appointment_reminders_remind_before_value_positive
        """
    )
    op.execute(
        """
        ALTER TABLE appointment_reminders
        DROP CONSTRAINT IF EXISTS ck_appointment_reminders_reminder_offset
        """
    )
    op.execute(
        """
        ALTER TABLE appointment_reminders
        ADD CONSTRAINT ck_appointment_reminders_reminder_offset
        CHECK (
            (NOT reminder_enabled AND remind_before_value IS NULL AND remind_before_unit IS NULL) OR
            (reminder_enabled AND remind_before_value IS NOT NULL AND remind_before_unit IS NOT NULL AND remind_before_value > 0)
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE appointment_reminders
        DROP CONSTRAINT IF EXISTS ck_appointment_reminders_reminder_offset
        """
    )
    op.execute(
        """
        UPDATE appointment_reminders
        SET
            remind_before_value = COALESCE(remind_before_value, 60),
            remind_before_unit = COALESCE(remind_before_unit, 'MINUTES'::follow_up_remind_before_unit),
            reminder_enabled = TRUE
        """
    )
    op.execute(
        """
        ALTER TABLE appointment_reminders
        ALTER COLUMN remind_before_value SET DEFAULT 60,
        ALTER COLUMN remind_before_value SET NOT NULL,
        ALTER COLUMN remind_before_unit SET DEFAULT 'MINUTES'::follow_up_remind_before_unit,
        ALTER COLUMN remind_before_unit SET NOT NULL
        """
    )
    op.execute(
        """
        ALTER TABLE appointment_reminders
        DROP COLUMN IF EXISTS reminder_enabled
        """
    )
    op.execute(
        """
        ALTER TABLE appointment_reminders
        ADD CONSTRAINT ck_appointment_reminders_remind_before_value_positive
        CHECK (remind_before_value > 0)
        """
    )

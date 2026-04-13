"""Align medicine inventory/reminder defaults and constraints.

Revision ID: 20260413_1500
Revises: 20260413_1400
Create Date: 2026-04-13 15:00:00
"""

from __future__ import annotations

from typing import Sequence, Union
from alembic import op


revision: str = "20260413_1500"
down_revision: Union[str, None] = "20260413_1400"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE medicine_inventory SET use_tags = '{}'::text[] WHERE use_tags IS NULL")
    op.execute(
        "ALTER TABLE medicine_inventory ALTER COLUMN use_tags SET DEFAULT '{}'::text[]"
    )
    op.execute("ALTER TABLE medicine_inventory ALTER COLUMN use_tags SET NOT NULL")

    op.execute(
        "UPDATE medicine_inventory SET expiry_alert_days_before = 30 WHERE expiry_alert_days_before IS NULL"
    )
    op.execute(
        "ALTER TABLE medicine_inventory ALTER COLUMN expiry_alert_days_before SET DEFAULT 30"
    )
    op.execute("ALTER TABLE medicine_inventory ALTER COLUMN expiry_alert_days_before SET NOT NULL")

    op.execute(
        "UPDATE medicine_reminders SET active_days = '{}'::integer[] WHERE active_days IS NULL"
    )
    op.execute(
        "ALTER TABLE medicine_reminders ALTER COLUMN repeat_every_unit SET DEFAULT 'week'"
    )
    op.execute(
        "ALTER TABLE medicine_reminders ALTER COLUMN active_days SET DEFAULT '{}'::integer[]"
    )
    op.execute("ALTER TABLE medicine_reminders ALTER COLUMN active_days SET NOT NULL")

    op.execute(
        "UPDATE medicine_reminders SET remind_before_minutes = 0 WHERE remind_before_minutes IS NULL"
    )
    op.execute(
        "ALTER TABLE medicine_reminders ALTER COLUMN remind_before_minutes SET DEFAULT 0"
    )
    op.execute("ALTER TABLE medicine_reminders ALTER COLUMN remind_before_minutes SET NOT NULL")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_medicine_reminders_medicine_inventory_id'
            ) THEN
                ALTER TABLE medicine_reminders
                ADD CONSTRAINT uq_medicine_reminders_medicine_inventory_id
                UNIQUE (medicine_inventory_id);
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE medicine_reminders DROP CONSTRAINT IF EXISTS uq_medicine_reminders_medicine_inventory_id"
    )

    op.execute(
        "ALTER TABLE medicine_reminders ALTER COLUMN remind_before_minutes DROP NOT NULL"
    )
    op.execute(
        "ALTER TABLE medicine_reminders ALTER COLUMN remind_before_minutes DROP DEFAULT"
    )
    op.execute("ALTER TABLE medicine_reminders ALTER COLUMN active_days DROP NOT NULL")
    op.execute("ALTER TABLE medicine_reminders ALTER COLUMN active_days DROP DEFAULT")
    op.execute("ALTER TABLE medicine_reminders ALTER COLUMN repeat_every_unit SET DEFAULT 'day'")

    op.execute("ALTER TABLE medicine_inventory ALTER COLUMN expiry_alert_days_before DROP NOT NULL")
    op.execute("ALTER TABLE medicine_inventory ALTER COLUMN expiry_alert_days_before DROP DEFAULT")
    op.execute("ALTER TABLE medicine_inventory ALTER COLUMN use_tags DROP NOT NULL")
    op.execute("ALTER TABLE medicine_inventory ALTER COLUMN use_tags DROP DEFAULT")


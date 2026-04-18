"""Dedupe table for appointment_reminders push dispatch.

Revision ID: 20260416_1100
Revises: 20260416_1000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260416_1100"
down_revision: Union[str, None] = "20260416_1000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "appointment_reminder_push_receipts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("reminder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fire_minute_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reminder_id"],
            ["appointment_reminders.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "reminder_id",
            "fire_minute_utc",
            name="uq_appt_reminder_fire_minute",
        ),
    )
    op.create_index(
        op.f("ix_appt_reminder_push_receipts_reminder_id"),
        "appointment_reminder_push_receipts",
        ["reminder_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_appt_reminder_push_receipts_reminder_id"),
        table_name="appointment_reminder_push_receipts",
    )
    op.drop_table("appointment_reminder_push_receipts")

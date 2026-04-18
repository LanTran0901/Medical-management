"""add schedule_snooze_overrides for server-side medicine snooze

Revision ID: 20260414_0900
Revises: 20260412_120000
Create Date: 2026-04-14 09:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260414_0900"
down_revision: Union[str, None] = "20260412_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedule_snooze_overrides",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occurrence_date", sa.Date(), nullable=False),
        sa.Column("base_time_slot", sa.String(length=8), nullable=False),
        sa.Column("snooze_until_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["action_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "schedule_id",
            "occurrence_date",
            "base_time_slot",
            name="uq_schedule_snooze_occurrence",
        ),
    )
    op.create_index(
        op.f("ix_schedule_snooze_overrides_schedule_id"),
        "schedule_snooze_overrides",
        ["schedule_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_schedule_snooze_overrides_due"),
        "schedule_snooze_overrides",
        ["consumed_at", "snooze_until_utc"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_schedule_snooze_overrides_due"),
        table_name="schedule_snooze_overrides",
    )
    op.drop_index(
        op.f("ix_schedule_snooze_overrides_schedule_id"),
        table_name="schedule_snooze_overrides",
    )
    op.drop_table("schedule_snooze_overrides")

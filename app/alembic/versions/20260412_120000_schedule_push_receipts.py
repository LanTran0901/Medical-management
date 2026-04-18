"""schedule_push_receipts for idempotent FCM dispatch per occurrence.

Revision ID: 20260412_120000
Revises: 20260411_1700
Create Date: 2026-04-12 12:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260412_120000"
down_revision: Union[str, None] = "20260411_1700"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedule_push_receipts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occurrence_date", sa.Date(), nullable=False),
        sa.Column("time_slot", sa.String(length=8), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["schedule_id"],
            ["schedules.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "schedule_id",
            "occurrence_date",
            "time_slot",
            name="uq_schedule_push_occurrence",
        ),
    )
    op.create_index(
        op.f("ix_schedule_push_receipts_schedule_id"),
        "schedule_push_receipts",
        ["schedule_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_schedule_push_receipts_schedule_id"),
        table_name="schedule_push_receipts",
    )
    op.drop_table("schedule_push_receipts")

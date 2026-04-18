"""Add appointment_reminders for checkup and vaccine scheduling.

Revision ID: 20260413_2000
Revises: 20260413_1900
Create Date: 2026-04-13 20:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260413_2000"
down_revision: Union[str, None] = "20260413_1900"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    reminder_type_create = postgresql.ENUM(
        "checkup",
        "vaccine",
        name="appointment_reminder_type",
        create_type=True,
    )
    reminder_type_create.create(bind, checkfirst=True)

    reminder_status_create = postgresql.ENUM(
        "pending",
        "done",
        "missed",
        name="appointment_reminder_status",
        create_type=True,
    )
    reminder_status_create.create(bind, checkfirst=True)

    reminder_type_col = postgresql.ENUM(
        "checkup",
        "vaccine",
        name="appointment_reminder_type",
        create_type=False,
    )
    reminder_status_col = postgresql.ENUM(
        "pending",
        "done",
        "missed",
        name="appointment_reminder_status",
        create_type=False,
    )

    op.create_table(
        "appointment_reminders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", reminder_type_col, nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("hospital_name", sa.String(length=512), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("appointment_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "remind_before_minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("60"),
        ),
        sa.Column("vaccine_name", sa.String(length=255), nullable=True),
        sa.Column("dose_number", sa.Integer(), nullable=True),
        sa.Column("total_doses", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            reminder_status_col,
            nullable=False,
            server_default=sa.text("'pending'::appointment_reminder_status"),
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("follow_up_appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vaccination_dose_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "NOT (follow_up_appointment_id IS NOT NULL AND vaccination_dose_id IS NOT NULL)",
            name="ck_appointment_reminders_single_source",
        ),
        sa.CheckConstraint(
            "(follow_up_appointment_id IS NULL) OR (type = 'checkup'::appointment_reminder_type)",
            name="ck_appointment_reminders_follow_up_is_checkup",
        ),
        sa.CheckConstraint(
            "(vaccination_dose_id IS NULL) OR (type = 'vaccine'::appointment_reminder_type)",
            name="ck_appointment_reminders_dose_is_vaccine",
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["follow_up_appointment_id"],
            ["follow_up_appointments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["vaccination_dose_id"],
            ["vaccination_doses.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_appointment_reminders_profile_id"),
        "appointment_reminders",
        ["profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_appointment_reminders_appointment_at"),
        "appointment_reminders",
        ["appointment_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_appointment_reminders_follow_up_appointment_id"),
        "appointment_reminders",
        ["follow_up_appointment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_appointment_reminders_vaccination_dose_id"),
        "appointment_reminders",
        ["vaccination_dose_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_appointment_reminders_vaccination_dose_id"),
        table_name="appointment_reminders",
    )
    op.drop_index(
        op.f("ix_appointment_reminders_follow_up_appointment_id"),
        table_name="appointment_reminders",
    )
    op.drop_index(
        op.f("ix_appointment_reminders_appointment_at"),
        table_name="appointment_reminders",
    )
    op.drop_index(
        op.f("ix_appointment_reminders_profile_id"),
        table_name="appointment_reminders",
    )
    op.drop_table("appointment_reminders")

    op.execute("DROP TYPE IF EXISTS appointment_reminder_status")
    op.execute("DROP TYPE IF EXISTS appointment_reminder_type")

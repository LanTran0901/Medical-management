"""follow_up_appointments: remind_before_days -> value + unit enum.

Revision ID: 20260417_1200
Revises: 20260415_0000
Create Date: 2026-04-17 12:00:00"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260417_1200"
down_revision: Union[str, None] = "20260416_1100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_unit_enum = postgresql.ENUM(
    "MINUTES",
    "HOURS",
    "DAYS",
    "WEEKS",
    name="follow_up_remind_before_unit",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        sa.text(
            "CREATE TYPE follow_up_remind_before_unit AS ENUM "
            "('MINUTES', 'HOURS', 'DAYS', 'WEEKS')"
        )
    )
    op.add_column(
        "follow_up_appointments",
        sa.Column("remind_before_value", sa.Integer(), nullable=True),
    )
    op.add_column(
        "follow_up_appointments",
        sa.Column("remind_before_unit", _unit_enum, nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE follow_up_appointments
            SET remind_before_value = remind_before_days,
                remind_before_unit = 'DAYS'::follow_up_remind_before_unit
            WHERE reminder_enabled IS TRUE
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE follow_up_appointments
            SET remind_before_value = NULL,
                remind_before_unit = NULL
            WHERE reminder_enabled IS NOT TRUE
            """
        )
    )
    op.drop_column("follow_up_appointments", "remind_before_days")
    op.create_check_constraint(
        "ck_follow_up_appt_reminder_offset",
        "follow_up_appointments",
        "(NOT reminder_enabled AND remind_before_value IS NULL AND remind_before_unit IS NULL) OR "
        "(reminder_enabled AND remind_before_value IS NOT NULL AND remind_before_unit IS NOT NULL "
        "AND remind_before_value > 0)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_follow_up_appt_reminder_offset", "follow_up_appointments", type_="check")
    op.add_column(
        "follow_up_appointments",
        sa.Column(
            "remind_before_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE follow_up_appointments SET remind_before_days = CASE
              WHEN remind_before_unit = 'MINUTES'::follow_up_remind_before_unit
                THEN GREATEST(1, CEIL(remind_before_value::numeric / 1440))
              WHEN remind_before_unit = 'HOURS'::follow_up_remind_before_unit
                THEN GREATEST(1, CEIL(remind_before_value::numeric / 24))
              WHEN remind_before_unit = 'DAYS'::follow_up_remind_before_unit
                THEN remind_before_value
              WHEN remind_before_unit = 'WEEKS'::follow_up_remind_before_unit
                THEN remind_before_value * 7
              ELSE 1
            END
            """
        )
    )
    op.alter_column("follow_up_appointments", "remind_before_days", server_default=None)
    op.drop_column("follow_up_appointments", "remind_before_unit")
    op.drop_column("follow_up_appointments", "remind_before_value")
    op.execute(sa.text("DROP TYPE follow_up_remind_before_unit"))

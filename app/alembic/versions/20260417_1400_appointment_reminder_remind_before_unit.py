"""appointment_reminders: remind_before_minutes -> value + unit.

Revision ID: 20260417_1400
Revises: 20260417_1300
Create Date: 2026-04-17 14:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260417_1400"
down_revision: Union[str, None] = "20260417_1300"
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
    op.add_column(
        "appointment_reminders",
        sa.Column("remind_before_value", sa.Integer(), nullable=True),
    )
    op.add_column(
        "appointment_reminders",
        sa.Column("remind_before_unit", _unit_enum, nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE appointment_reminders
            SET remind_before_value = remind_before_minutes,
                remind_before_unit = 'MINUTES'::follow_up_remind_before_unit
            """
        )
    )
    op.alter_column("appointment_reminders", "remind_before_value", nullable=False)
    op.alter_column("appointment_reminders", "remind_before_unit", nullable=False)
    op.create_check_constraint(
        "ck_appointment_reminders_remind_before_value_positive",
        "appointment_reminders",
        "remind_before_value > 0",
    )
    op.drop_column("appointment_reminders", "remind_before_minutes")


def downgrade() -> None:
    op.add_column(
        "appointment_reminders",
        sa.Column(
            "remind_before_minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("60"),
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE appointment_reminders SET remind_before_minutes = CASE
              WHEN remind_before_unit = 'MINUTES'::follow_up_remind_before_unit
                THEN remind_before_value
              WHEN remind_before_unit = 'HOURS'::follow_up_remind_before_unit
                THEN remind_before_value * 60
              WHEN remind_before_unit = 'DAYS'::follow_up_remind_before_unit
                THEN remind_before_value * 24 * 60
              WHEN remind_before_unit = 'WEEKS'::follow_up_remind_before_unit
                THEN remind_before_value * 7 * 24 * 60
              ELSE 60
            END
            """
        )
    )
    op.alter_column("appointment_reminders", "remind_before_minutes", server_default=None)
    op.drop_constraint(
        "ck_appointment_reminders_remind_before_value_positive",
        "appointment_reminders",
        type_="check",
    )
    op.drop_column("appointment_reminders", "remind_before_unit")
    op.drop_column("appointment_reminders", "remind_before_value")

"""vaccination_doses: remind_before_days -> value + unit (shared enum).

Revision ID: 20260417_1300
Revises: 20260417_1200
Create Date: 2026-04-17 13:00:00"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260417_1300"
down_revision: Union[str, None] = "20260417_1200"
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
        "vaccination_doses",
        sa.Column("remind_before_value", sa.Integer(), nullable=True),
    )
    op.add_column(
        "vaccination_doses",
        sa.Column("remind_before_unit", _unit_enum, nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE vaccination_doses
            SET remind_before_value = COALESCE(remind_before_days, 1),
                remind_before_unit = 'DAYS'::follow_up_remind_before_unit
            WHERE reminder_enabled IS TRUE
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE vaccination_doses
            SET remind_before_value = NULL,
                remind_before_unit = NULL
            WHERE reminder_enabled IS NOT TRUE
            """
        )
    )
    op.drop_column("vaccination_doses", "remind_before_days")
    op.create_check_constraint(
        "ck_vaccination_dose_reminder_offset",
        "vaccination_doses",
        "(NOT reminder_enabled AND remind_before_value IS NULL AND remind_before_unit IS NULL) OR "
        "(reminder_enabled AND remind_before_value IS NOT NULL AND remind_before_unit IS NOT NULL "
        "AND remind_before_value > 0)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_vaccination_dose_reminder_offset", "vaccination_doses", type_="check")
    op.add_column(
        "vaccination_doses",
        sa.Column("remind_before_days", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE vaccination_doses SET remind_before_days = CASE
              WHEN remind_before_unit = 'MINUTES'::follow_up_remind_before_unit
                THEN GREATEST(1, CEIL(remind_before_value::numeric / 1440))
              WHEN remind_before_unit = 'HOURS'::follow_up_remind_before_unit
                THEN GREATEST(1, CEIL(remind_before_value::numeric / 24))
              WHEN remind_before_unit = 'DAYS'::follow_up_remind_before_unit
                THEN remind_before_value
              WHEN remind_before_unit = 'WEEKS'::follow_up_remind_before_unit
                THEN remind_before_value * 7
              ELSE NULL
            END
            WHERE reminder_enabled IS TRUE
            """
        )
    )
    op.drop_column("vaccination_doses", "remind_before_unit")
    op.drop_column("vaccination_doses", "remind_before_value")

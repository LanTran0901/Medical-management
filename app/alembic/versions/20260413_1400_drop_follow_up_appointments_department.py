"""Drop department from follow_up_appointments.

Revision ID: 20260413_1400
Revises: 20260413_1200
Create Date: 2026-04-13 14:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260413_1400"
down_revision: Union[str, None] = "20260413_1200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE follow_up_appointments DROP COLUMN IF EXISTS department")


def downgrade() -> None:
    op.add_column(
        "follow_up_appointments",
        sa.Column("department", sa.Text(), nullable=True),
    )

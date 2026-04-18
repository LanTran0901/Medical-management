"""Add schedules.remind_tz for wall-clock reminders in IANA timezone.

Revision ID: 20260416_1000
Revises: 20260415_0000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260416_1000"
down_revision: Union[str, None] = "20260415_0000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "schedules",
        sa.Column(
            "remind_tz",
            sa.String(length=64),
            nullable=False,
            server_default="UTC",
        ),
    )


def downgrade() -> None:
    op.drop_column("schedules", "remind_tz")

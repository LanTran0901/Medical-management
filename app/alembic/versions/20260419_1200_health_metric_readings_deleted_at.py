"""health_metric_readings: add deleted_at (align ORM soft-delete filter).

Revision ID: 20260419_1200
Revises: 20260417_1400

The initial 20260412 migration created health_metric_readings without deleted_at;
SQLAlchemy model and queries filter on deleted_at — without this column GET /users/me fails with 500.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260419_1200"
down_revision: Union[str, None] = "20260417_1400"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE health_metric_readings
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE health_metric_readings
        DROP COLUMN IF EXISTS deleted_at
        """
    )

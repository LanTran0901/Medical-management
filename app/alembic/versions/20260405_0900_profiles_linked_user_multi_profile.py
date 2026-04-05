"""Allow one user to link multiple profiles.

Revision ID: 20260405_0900
Revises: 20260403_1600
Create Date: 2026-04-05 09:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260405_0900"
down_revision: Union[str, None] = "20260403_1600"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text('ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_linked_user_id_key'))
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_profiles_linked_user_id "
            "ON profiles (linked_user_id)"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_profiles_linked_user_id"))
    op.execute(
        sa.text(
            "ALTER TABLE profiles "
            "ADD CONSTRAINT profiles_linked_user_id_key UNIQUE (linked_user_id)"
        )
    )

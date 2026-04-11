"""Ensure profiles.linked_user_id is non-unique.

Revision ID: 20260411_1700
Revises: 20260409_1400
Create Date: 2026-04-11 17:00:00

This migration repairs environments that are stamped forward but still keep
the legacy unique constraint on profiles.linked_user_id.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260411_1700"
down_revision: Union[str, None] = "20260409_1400"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove legacy uniqueness and keep a normal index for lookups.
    op.execute(sa.text("ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_linked_user_id_key"))
    op.execute(sa.text("DROP INDEX IF EXISTS profiles_linked_user_id_key"))
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

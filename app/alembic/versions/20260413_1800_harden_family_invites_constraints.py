"""Harden family_invites constraints for UI invite flow.

Revision ID: 20260413_1800
Revises: 20260413_1700
Create Date: 2026-04-13 18:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260413_1800"
down_revision: Union[str, None] = "20260413_1700"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM family_invites
        WHERE user_id IS NULL
          AND phone_number IS NULL
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY family_id, user_id
                    ORDER BY invited_at DESC, id DESC
                ) AS rn
            FROM family_invites
            WHERE status = 'PENDING'
              AND user_id IS NOT NULL
        )
        UPDATE family_invites fi
        SET status = 'REJECTED',
            responded_at = COALESCE(responded_at, now())
        FROM ranked r
        WHERE fi.id = r.id
          AND r.rn > 1
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY family_id, phone_number
                    ORDER BY invited_at DESC, id DESC
                ) AS rn
            FROM family_invites
            WHERE status = 'PENDING'
              AND phone_number IS NOT NULL
        )
        UPDATE family_invites fi
        SET status = 'REJECTED',
            responded_at = COALESCE(responded_at, now())
        FROM ranked r
        WHERE fi.id = r.id
          AND r.rn > 1
        """
    )
    op.execute(
        """
        ALTER TABLE family_invites
        ADD CONSTRAINT ck_family_invites_target_required
        CHECK ((user_id IS NOT NULL) OR (phone_number IS NOT NULL))
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_family_invites_pending_family_user_unique
        ON family_invites (family_id, user_id)
        WHERE status = 'PENDING' AND user_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_family_invites_pending_family_phone_unique
        ON family_invites (family_id, phone_number)
        WHERE status = 'PENDING' AND phone_number IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_family_invites_pending_family_phone_unique")
    op.execute("DROP INDEX IF EXISTS ix_family_invites_pending_family_user_unique")
    op.execute(
        "ALTER TABLE family_invites DROP CONSTRAINT IF EXISTS ck_family_invites_target_required"
    )


"""recover missing revision bridge

Revision ID: 20260410_0900
Revises: 20260409_1400
Create Date: 2026-04-10 09:00:00.000000

This migration intentionally keeps schema unchanged.
It restores the post-`20260409_1400` bridge node that the notification branch
expected, without reusing an existing revision identifier.
"""

from __future__ import annotations


# revision identifiers, used by Alembic.
revision = "20260410_0900"
down_revision = "20260409_1400"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op bridge migration to recover revision chain."""


def downgrade() -> None:
    """No-op downgrade for bridge migration."""

"""recover missing revision

Revision ID: 20260409_1400
Revises: 20260315_203000
Create Date: 2026-04-09 14:00:00.000000

This migration intentionally keeps schema unchanged.
It restores a missing revision node so environments that were
already stamped to 20260409_1400 can migrate normally again.
"""

from __future__ import annotations


# revision identifiers, used by Alembic.
revision = "20260409_1400"
down_revision = "20260405_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op bridge migration to recover revision chain."""


def downgrade() -> None:
    """No-op downgrade for bridge migration."""

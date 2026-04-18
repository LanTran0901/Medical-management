"""Merge health-schema and notification-schema heads.

Revision ID: 20260415_0000
Revises: 20260413_2000, 20260414_0900
Create Date: 2026-04-15 00:00:00

This is a no-op merge revision so `alembic upgrade head` can advance
environments through both April 2026 branches deterministically.
"""

from __future__ import annotations

from typing import Sequence, Union


revision: str = "20260415_0000"
down_revision: Union[tuple[str, str], None] = ("20260413_2000", "20260414_0900")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge-point revision."""


def downgrade() -> None:
    """No-op downgrade for merge-point revision."""

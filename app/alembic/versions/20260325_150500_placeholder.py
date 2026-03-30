"""Placeholder: revision id legacy `20260325_150500` — không đổi schema.

Chạy sau `20260325_150501` (split medical dictionary) để giữ một nhánh duy nhất tới `003_mi_01`.

Revision ID: 20260325_150500
Revises: 20260325_150501
Create Date: 2026-03-28
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260325_150500"
down_revision: Union[str, None] = "20260325_150501"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

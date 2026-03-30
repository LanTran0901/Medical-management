"""Placeholder: revision từng tồn tại trên DB / branch khác — không đổi schema.

Nếu `alembic_version` = '20260325_150500' mà không có file, `upgrade head` sẽ lỗi.
File này khớp id đó; chuỗi tiếp theo là 003_mi_01 (003 medicine-inventory-api).

Revision ID: 20260325_150500
Revises: da58e3fdb641
Create Date: 2026-03-28
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260325_150500"
down_revision: Union[str, None] = "da58e3fdb641"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

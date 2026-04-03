"""Drop source_index from medical dictionary tables.

Revision ID: 20260403_1600
Revises: 20260402_1900
Create Date: 2026-04-03 16:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260403_1600"
down_revision: Union[str, None] = "20260402_1900"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_source_index(table_name: str) -> None:
    op.execute(sa.text(f'ALTER TABLE "{table_name}" DROP COLUMN IF EXISTS source_index CASCADE'))


def _add_source_index(table_name: str) -> None:
    op.execute(sa.text(f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS source_index integer'))
    op.execute(
        sa.text(
            f'CREATE INDEX IF NOT EXISTS "ix_{table_name}_source_index" '
            f'ON "{table_name}" (source_index)'
        )
    )


def upgrade() -> None:
    _drop_source_index("diseases")
    _drop_source_index("drugs")
    _drop_source_index("vaccines")


def downgrade() -> None:
    _add_source_index("diseases")
    _add_source_index("drugs")
    _add_source_index("vaccines")

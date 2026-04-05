"""Drop source_file column from medical dictionaries.

Revision ID: 20260405_1000
Revises: 20260405_0900
Create Date: 2026-04-05 10:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260405_1000"
down_revision: Union[str, None] = "20260405_0900"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('diseases', 'source_file')
    op.drop_column('drugs', 'source_file')
    op.drop_column('vaccines', 'source_file')


def downgrade() -> None:
    op.add_column('diseases', sa.Column('source_file', sa.String(255), nullable=False, server_default='unknown'))
    op.add_column('drugs', sa.Column('source_file', sa.String(255), nullable=False, server_default='unknown'))
    op.add_column('vaccines', sa.Column('source_file', sa.String(255), nullable=False, server_default='unknown'))

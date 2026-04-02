"""Add pgvector columns for medical dictionary RAG

Revision ID: 20260402_1900
Revises: 20260330_0100
Create Date: 2026-04-02 19:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260402_1900"
down_revision: Union[str, None] = "20260330_0100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
EMBEDDING_DIMENSIONS = 384


def _add_rag_columns(table_name: str) -> None:
    op.execute(
        sa.text(
            f'ALTER TABLE "{table_name}" '
            "ADD COLUMN IF NOT EXISTS search_document text"
        )
    )
    op.execute(
        sa.text(
            f'ALTER TABLE "{table_name}" '
            f"ADD COLUMN IF NOT EXISTS embedding vector({EMBEDDING_DIMENSIONS})"
        )
    )


def _drop_rag_columns(table_name: str) -> None:
    op.execute(sa.text(f'ALTER TABLE "{table_name}" DROP COLUMN IF EXISTS embedding'))
    op.execute(sa.text(f'ALTER TABLE "{table_name}" DROP COLUMN IF EXISTS search_document'))


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    _add_rag_columns("diseases")
    _add_rag_columns("drugs")
    _add_rag_columns("vaccines")


def downgrade() -> None:
    _drop_rag_columns("vaccines")
    _drop_rag_columns("drugs")
    _drop_rag_columns("diseases")

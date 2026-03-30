"""Add medical_records.deleted_at for soft-delete (US3)

Revision ID: 003_mi_04
Revises: 003_mi_03
Create Date: 2026-03-28
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_mi_04"
down_revision: Union[str, None] = "003_mi_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "medical_records",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_medical_records_deleted_at"),
        "medical_records",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_medical_records_deleted_at"), table_name="medical_records")
    op.drop_column("medical_records", "deleted_at")

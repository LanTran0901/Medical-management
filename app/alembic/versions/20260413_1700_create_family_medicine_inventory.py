"""Create family_medicine_inventory table.

Revision ID: 20260413_1700
Revises: 20260413_1600
Create Date: 2026-04-13 17:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260413_1700"
down_revision: Union[str, None] = "20260413_1600"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "family_medicine_inventory",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("medicine_name", sa.String(length=255), nullable=False),
        sa.Column("quantity_stock", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("storage_location", sa.String(length=255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("min_stock_alert", sa.Numeric(12, 3), nullable=False, server_default=sa.text("0")),
        sa.Column("low_stock_alert_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("expiry_alert_days_before", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        op.f("ix_family_medicine_inventory_family_id"),
        "family_medicine_inventory",
        ["family_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_family_medicine_inventory_created_by_user_id"),
        "family_medicine_inventory",
        ["created_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_family_medicine_inventory_created_by_user_id"), table_name="family_medicine_inventory")
    op.drop_index(op.f("ix_family_medicine_inventory_family_id"), table_name="family_medicine_inventory")
    op.drop_table("family_medicine_inventory")


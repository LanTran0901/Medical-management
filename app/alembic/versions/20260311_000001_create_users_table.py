"""create users table

Revision ID: 20260311_000001
Revises:
Create Date: 2026-03-11 00:00:01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260311_000001"
down_revision = None
branch_labels = None
depends_on = None


user_status = postgresql.ENUM(
    "active",
    "inactive",
    "banned",
    name="user_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    user_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("google_id", sa.String(length=128), nullable=True),
        sa.Column("apple_id", sa.String(length=128), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("dob", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=50), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("status", user_status, nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_id"),
        sa.UniqueConstraint("apple_id"),
    )


def downgrade() -> None:
    op.drop_table("users")
    user_status.drop(op.get_bind(), checkfirst=True)
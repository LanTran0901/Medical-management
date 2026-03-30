"""Public family invite tokens: single-use + expiry.

Revision ID: 20260330_0200
Revises: 20260330_0100
Create Date: 2026-03-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260330_0200"
down_revision: Union[str, None] = "20260330_0100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    family_public_invite_status = postgresql.ENUM(
        "PENDING",
        "CONSUMED",
        "REVOKED",
        name="family_public_invite_status",
    )
    family_public_invite_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "family_public_invites",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invite_code", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "CONSUMED",
                "REVOKED",
                name="family_public_invite_status",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'PENDING'::family_public_invite_status"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["consumed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_code", name="uq_family_public_invites_invite_code"),
    )
    op.create_index(
        op.f("ix_family_public_invites_family_id"),
        "family_public_invites",
        ["family_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_family_public_invites_status"),
        "family_public_invites",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_family_public_invites_one_pending_per_family",
        "family_public_invites",
        ["family_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'::family_public_invite_status"),
    )

    # Backfill: one long-lived PENDING token per existing family (matches current invite_code).
    op.execute(
        sa.text(
            """
            INSERT INTO family_public_invites (
                id, family_id, invite_code, expires_at, status, created_by, created_at
            )
            SELECT
                gen_random_uuid(),
                f.id,
                f.invite_code,
                NOW() + INTERVAL '90 days',
                'PENDING'::family_public_invite_status,
                f.created_by,
                NOW()
            FROM families f
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_family_public_invites_one_pending_per_family", table_name="family_public_invites")
    op.drop_index(op.f("ix_family_public_invites_status"), table_name="family_public_invites")
    op.drop_index(op.f("ix_family_public_invites_family_id"), table_name="family_public_invites")
    op.drop_table("family_public_invites")
    op.execute("DROP TYPE IF EXISTS family_public_invite_status")

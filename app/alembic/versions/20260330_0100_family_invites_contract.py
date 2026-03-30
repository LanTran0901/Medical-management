"""Family contract alignment: families metadata + pending family invites.

Revision ID: 20260330_0100
Revises: 003_mi_05
Create Date: 2026-03-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260330_0100"
down_revision: Union[str, None] = "003_mi_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("families", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("families", sa.Column("avatar_url", sa.Text(), nullable=True))
    op.add_column("families", sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True))

    op.add_column("family_memberships", sa.Column("relation_role", sa.String(length=64), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE families f
            SET created_by = owner_rows.added_by
            FROM (
                SELECT fm.family_id, fm.added_by
                FROM family_memberships fm
                WHERE fm.role = 'OWNER'
            ) AS owner_rows
            WHERE owner_rows.family_id = f.id
              AND f.created_by IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE families f
            SET created_by = fallback_rows.added_by
            FROM (
                SELECT DISTINCT ON (fm.family_id) fm.family_id, fm.added_by
                FROM family_memberships fm
                ORDER BY fm.family_id, fm.created_at ASC, fm.id ASC
            ) AS fallback_rows
            WHERE fallback_rows.family_id = f.id
              AND f.created_by IS NULL
            """
        )
    )

    op.alter_column("families", "created_by", nullable=False)
    op.create_foreign_key(
        "fk_families_created_by_users",
        "families",
        "users",
        ["created_by"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_families_created_by"), "families", ["created_by"], unique=False)

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_type t
                    JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE t.typname = 'family_invite_status'
                ) THEN
                    CREATE TYPE family_invite_status AS ENUM ('PENDING', 'ACCEPTED', 'REJECTED');
                END IF;
            END
            $$;
            """
        )
    )

    family_invite_status = postgresql.ENUM(
        "PENDING",
        "ACCEPTED",
        "REJECTED",
        name="family_invite_status",
        create_type=False,
    )

    op.create_table(
        "family_invites",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("phone_number", sa.String(length=64), nullable=True),
        sa.Column(
            "role",
            postgresql.ENUM("OWNER", "ADMIN", "MEMBER", name="family_role", create_type=False),
            nullable=False,
            server_default=sa.text("'MEMBER'::family_role"),
        ),
        sa.Column("relation_role", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            family_invite_status,
            nullable=False,
            server_default=sa.text("'PENDING'::family_invite_status"),
        ),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "invited_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_family_invites_family_id"), "family_invites", ["family_id"], unique=False)
    op.create_index(op.f("ix_family_invites_user_id"), "family_invites", ["user_id"], unique=False)
    op.create_index(op.f("ix_family_invites_phone_number"), "family_invites", ["phone_number"], unique=False)
    op.create_index(op.f("ix_family_invites_status"), "family_invites", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_family_invites_status"), table_name="family_invites")
    op.drop_index(op.f("ix_family_invites_phone_number"), table_name="family_invites")
    op.drop_index(op.f("ix_family_invites_user_id"), table_name="family_invites")
    op.drop_index(op.f("ix_family_invites_family_id"), table_name="family_invites")
    op.drop_table("family_invites")

    op.execute("DROP TYPE IF EXISTS family_invite_status CASCADE")

    op.drop_index(op.f("ix_families_created_by"), table_name="families")
    op.drop_constraint("fk_families_created_by_users", "families", type_="foreignkey")

    op.drop_column("family_memberships", "relation_role")

    op.drop_column("families", "created_by")
    op.drop_column("families", "avatar_url")
    op.drop_column("families", "address")

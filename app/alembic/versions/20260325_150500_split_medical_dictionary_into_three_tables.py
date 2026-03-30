"""split medical dictionary into three tables

Revision ID: 20260325_150501
Revises: da58e3fdb641
Create Date: 2026-03-25 15:05:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import ProgrammingError

revision: str = "20260325_150501"
down_revision: Union[str, None] = "da58e3fdb641"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists_public(conn, table_name: str) -> bool:
    """Kiểm tra bảng trong schema public (ổn định hơn inspector khi bảng đã tạo bởi seed/SQL)."""
    row = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t LIMIT 1"
        ),
        {"t": table_name},
    ).first()
    return row is not None


def _create_table(table_name: str) -> None:
    """Tạo bảng chỉ khi chưa có — tránh DuplicateTable khi seed đã tạo model trước."""
    conn = op.get_bind()
    if _table_exists_public(conn, table_name):
        return

    try:
        op.create_table(
            table_name,
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("source_index", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=512), nullable=False),
            sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("source_file", sa.String(length=255), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("source_index", name=f"uq_{table_name}_source_index"),
        )
        op.create_index(f"ix_{table_name}_source_index", table_name, ["source_index"], unique=False)
        op.create_index(f"ix_{table_name}_title", table_name, ["title"], unique=False)
    except ProgrammingError as exc:
        # 42P07 = duplicate_table (race hoặc inspector không thấy)
        if getattr(exc.orig, "pgcode", None) == "42P07" or "already exists" in str(exc.orig).lower():
            return
        raise


def upgrade() -> None:
    _create_table("diseases")
    _create_table("drugs")
    _create_table("vaccines")

    op.execute("DROP TABLE IF EXISTS medical_dictionary_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS disease_dictionary_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS drug_dictionary_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS vaccine_dictionary_entries CASCADE")


def _drop_table(table_name: str) -> None:
    op.execute(sa.text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))


def downgrade() -> None:
    _drop_table("vaccines")
    _drop_table("drugs")
    _drop_table("diseases")

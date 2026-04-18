"""Reconcile managed schema with current ORM.

Revision ID: 20260409_1400
Revises: 20260405_1000
Create Date: 2026-04-09 14:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260409_1400"
down_revision: Union[str, None] = "20260405_1000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    row = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND column_name = :column_name
            LIMIT 1
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).first()
    return row is not None


def _index_exists(table_name: str, index_name: str) -> bool:
    conn = op.get_bind()
    row = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = :table_name
              AND indexname = :index_name
            LIMIT 1
            """
        ),
        {"table_name": table_name, "index_name": index_name},
    ).first()
    return row is not None


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    conn = op.get_bind()
    row = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.table_constraints
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND constraint_name = :constraint_name
            LIMIT 1
            """
        ),
        {"table_name": table_name, "constraint_name": constraint_name},
    ).first()
    return row is not None


def _backfill_dictionary_columns(table_name: str, source_file: str) -> None:
    conn = op.get_bind()

    if not _column_exists(table_name, "source_index"):
        op.add_column(table_name, sa.Column("source_index", sa.Integer(), nullable=True))

    conn.execute(
        sa.text(
            f"""
            WITH ranked AS (
                SELECT id, ROW_NUMBER() OVER (ORDER BY created_at NULLS LAST, id) AS rn
                FROM "{table_name}"
            )
            UPDATE "{table_name}" AS t
            SET source_index = ranked.rn
            FROM ranked
            WHERE t.id = ranked.id
              AND t.source_index IS NULL
            """
        )
    )
    op.alter_column(table_name, "source_index", nullable=False)

    index_name = f"ix_{table_name}_source_index"
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, ["source_index"], unique=True)

    if not _column_exists(table_name, "source_file"):
        op.add_column(table_name, sa.Column("source_file", sa.String(length=255), nullable=True))

    conn.execute(
        sa.text(
            f"""
            UPDATE "{table_name}"
            SET source_file = :source_file
            WHERE source_file IS NULL
            """
        ),
        {"source_file": source_file},
    )
    op.alter_column(table_name, "source_file", nullable=False)


def upgrade() -> None:
    _backfill_dictionary_columns("diseases", "disease.json")
    _backfill_dictionary_columns("drugs", "thuoc.json")
    _backfill_dictionary_columns("vaccines", "vaccine.json")

    conn = op.get_bind()
    duplicate_count = conn.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM (
                SELECT linked_user_id
                FROM profiles
                WHERE linked_user_id IS NOT NULL
                GROUP BY linked_user_id
                HAVING COUNT(*) > 1
            ) AS dupes
            """
        )
    ).scalar_one()
    if duplicate_count:
        raise RuntimeError(
            "Cannot restore unique linked_user_id constraint: duplicate linked_user_id values exist."
        )

    if _index_exists("profiles", "ix_profiles_linked_user_id"):
        op.drop_index("ix_profiles_linked_user_id", table_name="profiles")

    if not _constraint_exists("profiles", "profiles_linked_user_id_key"):
        op.create_unique_constraint(
            "profiles_linked_user_id_key",
            "profiles",
            ["linked_user_id"],
        )


def downgrade() -> None:
    if _constraint_exists("profiles", "profiles_linked_user_id_key"):
        op.drop_constraint("profiles_linked_user_id_key", "profiles", type_="unique")

    if not _index_exists("profiles", "ix_profiles_linked_user_id"):
        op.create_index("ix_profiles_linked_user_id", "profiles", ["linked_user_id"], unique=False)

    for table_name in ("vaccines", "drugs", "diseases"):
        index_name = f"ix_{table_name}_source_index"
        if _index_exists(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
        if _column_exists(table_name, "source_file"):
            op.drop_column(table_name, "source_file")
        if _column_exists(table_name, "source_index"):
            op.drop_column(table_name, "source_index")

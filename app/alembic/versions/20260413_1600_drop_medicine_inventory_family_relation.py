"""Drop medicine_inventory relation to families.

Revision ID: 20260413_1600
Revises: 20260413_1500
Create Date: 2026-04-13 16:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260413_1600"
down_revision: Union[str, None] = "20260413_1500"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_medicine_inventory_family_id")
    op.execute(
        """
        DO $$
        DECLARE
            _constraint_name text;
        BEGIN
            SELECT tc.constraint_name
            INTO _constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = 'medicine_inventory'
              AND kcu.column_name = 'family_id'
            LIMIT 1;

            IF _constraint_name IS NOT NULL THEN
                EXECUTE format(
                    'ALTER TABLE medicine_inventory DROP CONSTRAINT IF EXISTS %I',
                    _constraint_name
                );
            END IF;
        END
        $$;
        """
    )
    op.execute("ALTER TABLE medicine_inventory DROP COLUMN IF EXISTS family_id")


def downgrade() -> None:
    op.execute("ALTER TABLE medicine_inventory ADD COLUMN IF NOT EXISTS family_id uuid")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_medicine_inventory_family_id_families'
            ) THEN
                ALTER TABLE medicine_inventory
                ADD CONSTRAINT fk_medicine_inventory_family_id_families
                FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE;
            END IF;
        END
        $$;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_medicine_inventory_family_id ON medicine_inventory (family_id)")


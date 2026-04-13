"""Backfill family_medicine_inventory from medicine_inventory.

Revision ID: 20260413_1900
Revises: 20260413_1800
Create Date: 2026-04-13 19:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "20260413_1900"
down_revision: Union[str, None] = "20260413_1800"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO family_medicine_inventory (
            family_id,
            created_by_user_id,
            medicine_name,
            quantity_stock,
            unit,
            expiry_date,
            storage_location,
            note,
            min_stock_alert,
            low_stock_alert_enabled,
            expiry_alert_days_before
        )
        SELECT
            fm.family_id,
            NULL,
            mi.medicine_name,
            COALESCE(mi.quantity_stock, 0),
            COALESCE(mi.unit, ''),
            COALESCE(mi.expiry_date, CURRENT_DATE),
            mi.storage_location,
            mi.instruction,
            COALESCE(mi.min_stock_alert, 0),
            COALESCE(mi.low_stock_alert_enabled, true),
            COALESCE(mi.expiry_alert_days_before, 30)
        FROM medicine_inventory mi
        JOIN family_memberships fm
          ON fm.profile_id = mi.profile_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM family_medicine_inventory fmi
            WHERE fmi.family_id = fm.family_id
              AND fmi.medicine_name = mi.medicine_name
              AND fmi.expiry_date = COALESCE(mi.expiry_date, CURRENT_DATE)
              AND fmi.quantity_stock = COALESCE(mi.quantity_stock, 0)
              AND fmi.unit = COALESCE(mi.unit, '')
        )
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM family_medicine_inventory WHERE created_by_user_id IS NULL")

"""003 medicine-inventory-api: users.phone_number, profile_status enum, medicine/medical columns

Revision ID: 003_mi_01
Revises: 20260325_150500
Create Date: 2026-03-28
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "003_mi_01"
down_revision: Union[str, None] = "20260325_150500"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    op.add_column("users", sa.Column("phone_number", sa.String(length=64), nullable=True))

    profile_status = postgresql.ENUM(
        "SHADOW",
        "PENDING_LINK",
        "ACTIVE",
        "INACTIVE",
        name="profile_status",
        create_type=True,
    )
    profile_status.create(bind, checkfirst=True)

    op.execute(
        sa.text(
            """
            ALTER TABLE profiles
            ALTER COLUMN status TYPE profile_status
            USING (
              CASE
                WHEN status IS NULL OR btrim(status::text) = '' THEN 'ACTIVE'::profile_status
                WHEN lower(btrim(status::text)) IN ('active', 'activated') THEN 'ACTIVE'::profile_status
                WHEN lower(btrim(status::text)) IN ('shadow') THEN 'SHADOW'::profile_status
                WHEN lower(btrim(status::text)) IN ('inactive', 'in_active') THEN 'INACTIVE'::profile_status
                WHEN lower(btrim(status::text)) IN ('pending', 'pending_link') THEN 'PENDING_LINK'::profile_status
                ELSE 'ACTIVE'::profile_status
              END
            );
            """
        )
    )
    op.execute(sa.text("ALTER TABLE profiles ALTER COLUMN status SET DEFAULT 'ACTIVE'::profile_status"))
    op.execute(sa.text("ALTER TABLE profiles ALTER COLUMN status SET NOT NULL"))

    insp = inspect(bind)
    prof_cols = {c["name"] for c in insp.get_columns("profiles")}
    if "is_shadow" in prof_cols:
        op.drop_column("profiles", "is_shadow")

    op.add_column(
        "medicine_inventory",
        sa.Column("expiry_alert_days_before", sa.Integer(), nullable=True),
    )
    op.add_column("medical_records", sa.Column("specialty", sa.Text(), nullable=True))
    op.add_column("medical_records", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("medical_records", "notes")
    op.drop_column("medical_records", "specialty")
    op.drop_column("medicine_inventory", "expiry_alert_days_before")

    op.execute(sa.text("ALTER TABLE profiles ALTER COLUMN status DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE profiles ALTER COLUMN status DROP NOT NULL"))
    op.execute(sa.text("ALTER TABLE profiles ALTER COLUMN status TYPE TEXT USING status::text"))
    op.execute(sa.text("DROP TYPE IF EXISTS profile_status"))

    op.drop_column("users", "phone_number")

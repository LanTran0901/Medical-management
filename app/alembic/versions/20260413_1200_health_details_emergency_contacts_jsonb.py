"""health_details: emergency_contact text -> emergency_contacts jsonb.

Revision ID: 20260413_1200
Revises: 20260412_2100
Create Date: 2026-04-13 12:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260413_1200"
down_revision: Union[str, None] = "20260412_2100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "health_details",
        sa.Column("emergency_contacts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE health_details
            SET emergency_contacts = jsonb_build_array(
                jsonb_build_object(
                    'name', emergency_contact,
                    'phone', NULL,
                    'relationship', NULL
                )
            )
            WHERE emergency_contact IS NOT NULL AND btrim(emergency_contact) != ''
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE health_details
            SET emergency_contacts = '[]'::jsonb
            WHERE emergency_contacts IS NULL
            """
        )
    )
    op.alter_column(
        "health_details",
        "emergency_contacts",
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )
    op.drop_column("health_details", "emergency_contact")


def downgrade() -> None:
    op.add_column("health_details", sa.Column("emergency_contact", sa.Text(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE health_details
            SET emergency_contact = CASE
                WHEN jsonb_array_length(COALESCE(emergency_contacts, '[]'::jsonb)) = 0 THEN NULL
                ELSE COALESCE(emergency_contacts->0->>'name', '')
                     || CASE
                         WHEN COALESCE(emergency_contacts->0->>'phone', '') = '' THEN ''
                         ELSE ' — ' || (emergency_contacts->0->>'phone')
                     END
            END
            """
        )
    )
    op.drop_column("health_details", "emergency_contacts")

"""Seed vaccination_recommendations catalog (optional baseline rows).

Revision ID: 003_mi_05
Revises: 003_mi_04
Create Date: 2026-03-28
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_mi_05"
down_revision: Union[str, None] = "003_mi_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO vaccination_recommendations (code, name, total_doses) VALUES
            ('COVID19', 'COVID-19 (primary series)', 3),
            ('MMR', 'MMR (Measles, Mumps, Rubella)', 2),
            ('INFLUENZA', 'Seasonal influenza', 1),
            ('TDAP', 'Tdap (Tetanus, Diphtheria, Pertussis)', 1)
            ON CONFLICT (code) DO NOTHING;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM vaccination_recommendations v
            WHERE v.code IN ('COVID19', 'MMR', 'INFLUENZA', 'TDAP')
            AND NOT EXISTS (
                SELECT 1 FROM user_vaccinations u WHERE u.recommendation_id = v.id
            );
            """
        )
    )

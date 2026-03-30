"""003 medicine-inventory-api: vaccination 3-layer + migrate vaccine_history

Revision ID: 003_mi_03
Revises: 003_mi_02
Create Date: 2026-03-28
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_mi_03"
down_revision: Union[str, None] = "003_mi_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vaccination_recommendations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("total_doses", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(
        op.f("ix_vaccination_recommendations_name"),
        "vaccination_recommendations",
        ["name"],
        unique=False,
    )

    op.create_table(
        "user_vaccinations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["vaccination_recommendations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_id",
            "recommendation_id",
            name="uq_user_vaccination_profile_recommendation",
        ),
    )
    op.create_index(
        op.f("ix_user_vaccinations_profile_id"),
        "user_vaccinations",
        ["profile_id"],
        unique=False,
    )

    op.create_table(
        "vaccination_doses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_vaccination_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dose_index", sa.Integer(), nullable=False),
        sa.Column("administered_at", sa.Date(), nullable=True),
        sa.Column("scheduled_at", sa.Date(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("proof_url", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_vaccination_id"],
            ["user_vaccinations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vaccination_doses_user_vaccination_id"),
        "vaccination_doses",
        ["user_vaccination_id"],
        unique=False,
    )

    connection = op.get_bind()
    vh_rows = connection.execute(
        sa.text(
            "SELECT id, profile_id, vaccine_name, dose_number, vaccinated_date, next_due_date "
            "FROM vaccine_history"
        )
    ).mappings().all()

    rec_cache: dict[str, uuid.UUID] = {}
    uv_cache: dict[tuple[uuid.UUID, uuid.UUID], uuid.UUID] = {}

    for row in vh_rows:
        name = (row["vaccine_name"] or "legacy").strip()[:255]
        if name not in rec_cache:
            rid = uuid.uuid4()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO vaccination_recommendations (id, code, name, total_doses)
                    VALUES (:id, :code, :name, :td)
                    """
                ),
                {
                    "id": rid,
                    "code": None,
                    "name": name,
                    "td": 3,
                },
            )
            rec_cache[name] = rid
        rec_id = rec_cache[name]

        profile_id = row["profile_id"]
        key = (profile_id, rec_id)
        if key not in uv_cache:
            uv_id = uuid.uuid4()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO user_vaccinations (id, profile_id, recommendation_id, status)
                    VALUES (:id, :pid, :rid, :st)
                    """
                ),
                {
                    "id": uv_id,
                    "pid": profile_id,
                    "rid": rec_id,
                    "st": "in_progress",
                },
            )
            uv_cache[key] = uv_id
        uv_id = uv_cache[key]

        dose_idx = row["dose_number"] if row["dose_number"] is not None else 1
        connection.execute(
            sa.text(
                """
                INSERT INTO vaccination_doses (id, user_vaccination_id, dose_index, administered_at, scheduled_at)
                VALUES (:id, :uv, :di, :adm, :sch)
                """
            ),
            {
                "id": uuid.uuid4(),
                "uv": uv_id,
                "di": int(dose_idx),
                "adm": row["vaccinated_date"],
                "sch": row["next_due_date"],
            },
        )

    op.drop_index(op.f("ix_vaccine_history_profile_id"), table_name="vaccine_history")
    op.drop_table("vaccine_history")


def downgrade() -> None:
    op.create_table(
        "vaccine_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vaccine_name", sa.String(length=255), nullable=False),
        sa.Column("dose_number", sa.Integer(), nullable=True),
        sa.Column("vaccinated_date", sa.Date(), nullable=True),
        sa.Column("next_due_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vaccine_history_profile_id"),
        "vaccine_history",
        ["profile_id"],
        unique=False,
    )

    op.drop_index(op.f("ix_vaccination_doses_user_vaccination_id"), table_name="vaccination_doses")
    op.drop_table("vaccination_doses")
    op.drop_index(op.f("ix_user_vaccinations_profile_id"), table_name="user_vaccinations")
    op.drop_table("user_vaccinations")
    op.drop_index(op.f("ix_vaccination_recommendations_name"), table_name="vaccination_recommendations")
    op.drop_table("vaccination_recommendations")

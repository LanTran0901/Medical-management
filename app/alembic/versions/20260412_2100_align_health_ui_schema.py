"""Align health domain schema with current UI contract.

Revision ID: 20260412_2100
Revises: 20260409_1400
Create Date: 2026-04-12 21:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260412_2100"
down_revision: Union[str, None] = "20260409_1400"
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


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    row = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = :table_name
            LIMIT 1
            """
        ),
        {"table_name": table_name},
    ).first()
    return row is not None


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    text_array = postgresql.ARRAY(sa.Text())

    _add_column_if_missing("health_details", sa.Column("drug_allergies", text_array, nullable=True))
    _add_column_if_missing("health_details", sa.Column("food_allergies", text_array, nullable=True))

    _add_column_if_missing("medical_records", sa.Column("title", sa.String(length=255), nullable=True))
    _add_column_if_missing("medical_records", sa.Column("symptoms", text_array, nullable=True))
    _add_column_if_missing("medical_records", sa.Column("test_results", sa.Text(), nullable=True))
    _add_column_if_missing("medical_records", sa.Column("doctor_advice", sa.Text(), nullable=True))
    _add_column_if_missing(
        "medical_records",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    _add_column_if_missing(
        "medical_record_attachments",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    _add_column_if_missing("follow_up_appointments", sa.Column("facility_name", sa.Text(), nullable=True))
    _add_column_if_missing("follow_up_appointments", sa.Column("doctor_name", sa.String(length=255), nullable=True))
    _add_column_if_missing("follow_up_appointments", sa.Column("notes", sa.Text(), nullable=True))
    _add_column_if_missing(
        "follow_up_appointments",
        sa.Column("reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    _add_column_if_missing(
        "follow_up_appointments",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    _add_column_if_missing(
        "medicine_inventory",
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    _add_column_if_missing("medicine_inventory", sa.Column("dosage_value", sa.Numeric(12, 3), nullable=True))
    _add_column_if_missing("medicine_inventory", sa.Column("dosage_unit", sa.String(length=64), nullable=True))
    _add_column_if_missing("medicine_inventory", sa.Column("dosage_per_use_value", sa.Numeric(12, 3), nullable=True))
    _add_column_if_missing("medicine_inventory", sa.Column("dosage_per_use_unit", sa.String(length=64), nullable=True))
    _add_column_if_missing("medicine_inventory", sa.Column("use_tags", text_array, nullable=True))
    _add_column_if_missing("medicine_inventory", sa.Column("storage_location", sa.String(length=255), nullable=True))
    _add_column_if_missing(
        "medicine_inventory",
        sa.Column("low_stock_alert_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    _add_column_if_missing(
        "medicine_inventory",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    _add_column_if_missing(
        "medicine_inventory",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_medicine_inventory_profile_id_profiles'
            ) THEN
                ALTER TABLE medicine_inventory
                    ADD CONSTRAINT fk_medicine_inventory_profile_id_profiles
                    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE SET NULL;
            END IF;
        END
        $$;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_medicine_inventory_profile_id ON medicine_inventory (profile_id)")

    _add_column_if_missing("vaccination_recommendations", sa.Column("disease_name", sa.String(length=255), nullable=True))
    _add_column_if_missing("vaccination_recommendations", sa.Column("notes", sa.Text(), nullable=True))

    _add_column_if_missing("vaccination_doses", sa.Column("reaction", sa.Text(), nullable=True))
    _add_column_if_missing(
        "vaccination_doses",
        sa.Column("reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    _add_column_if_missing("vaccination_doses", sa.Column("remind_before_days", sa.Integer(), nullable=True))

    if not _table_exists("medicine_reminders"):
        op.create_table(
            "medicine_reminders",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("medicine_inventory_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("repeat_every_value", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("repeat_every_unit", sa.String(length=16), nullable=False, server_default="week"),
            sa.Column("active_days", postgresql.ARRAY(sa.Integer()), nullable=False, server_default=sa.text("'{}'::integer[]")),
            sa.Column("times", postgresql.ARRAY(sa.String(length=5)), nullable=False, server_default=sa.text("'{}'::varchar[]")),
            sa.Column("remind_before_minutes", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("medicine_inventory_id", name="uq_medicine_reminders_medicine_inventory_id"),
            sa.ForeignKeyConstraint(["medicine_inventory_id"], ["medicine_inventory.id"], ondelete="CASCADE"),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_medicine_reminders_medicine_inventory_id ON medicine_reminders (medicine_inventory_id)")

    if not _table_exists("health_metric_readings"):
        op.create_table(
            "health_metric_readings",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("metric_type", sa.String(length=32), nullable=False),
            sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("systolic", sa.Integer(), nullable=True),
            sa.Column("diastolic", sa.Integer(), nullable=True),
            sa.Column("heart_rate", sa.Integer(), nullable=True),
            sa.Column("weight_kg", sa.Numeric(5, 1), nullable=True),
            sa.Column("glucose_mmol_l", sa.Numeric(5, 2), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_health_metric_readings_profile_id ON health_metric_readings (profile_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_health_metric_readings_metric_type ON health_metric_readings (metric_type)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_health_metric_readings_metric_type")
    op.execute("DROP INDEX IF EXISTS ix_health_metric_readings_profile_id")
    if _table_exists("health_metric_readings"):
        op.drop_table("health_metric_readings")
    op.execute("DROP INDEX IF EXISTS ix_medicine_reminders_medicine_inventory_id")
    if _table_exists("medicine_reminders"):
        op.drop_table("medicine_reminders")

    op.execute("DROP INDEX IF EXISTS ix_medicine_inventory_profile_id")
    op.execute(
        "ALTER TABLE medicine_inventory DROP CONSTRAINT IF EXISTS fk_medicine_inventory_profile_id_profiles"
    )

    for table_name, column_names in (
        ("vaccination_doses", ("remind_before_days", "reminder_enabled", "reaction")),
        ("vaccination_recommendations", ("notes", "disease_name")),
        (
            "medicine_inventory",
            (
                "updated_at",
                "created_at",
                "low_stock_alert_enabled",
                "storage_location",
                "use_tags",
                "dosage_per_use_unit",
                "dosage_per_use_value",
                "dosage_unit",
                "dosage_value",
                "profile_id",
            ),
        ),
        (
            "follow_up_appointments",
            ("created_at", "reminder_enabled", "notes", "doctor_name", "department", "facility_name"),
        ),
        ("medical_record_attachments", ("created_at",)),
        ("medical_records", ("updated_at", "doctor_advice", "test_results", "symptoms", "title")),
        ("health_details", ("food_allergies", "drug_allergies")),
    ):
        for column_name in column_names:
            if _column_exists(table_name, column_name):
                op.drop_column(table_name, column_name)

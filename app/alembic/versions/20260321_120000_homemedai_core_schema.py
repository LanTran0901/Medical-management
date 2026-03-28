"""homemedai core schema: profiles, families, schedules, refactor users/devices/tokens

Revision ID: 20260321_120000
Revises: 3049acc94cd2
Create Date: 2026-03-21 12:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260321_120000"
down_revision: Union[str, None] = "3049acc94cd2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- New ENUM types (user_status already exists: active/inactive/banned) ---
    family_role = postgresql.ENUM(
        "OWNER",
        "ADMIN",
        "MEMBER",
        name="family_role",
        create_type=False,
    )
    schedule_status = postgresql.ENUM(
        "ACTIVE",
        "PAUSED",
        "COMPLETED",
        name="schedule_status",
        create_type=False,
    )
    schedule_category = postgresql.ENUM(
        "MEDICINE",
        "VACCINE",
        "CHECKUP",
        "RE_CHECKUP",
        name="schedule_category",
        create_type=False,
    )
    gender_type = postgresql.ENUM(
        "male",
        "female",
        "other",
        name="gender_type",
        create_type=False,
    )
    blood_type_enum = postgresql.ENUM(
        "A_POS",
        "A_NEG",
        "B_POS",
        "B_NEG",
        "O_POS",
        "O_NEG",
        "AB_POS",
        "AB_NEG",
        name="blood_type_enum",
        create_type=False,
    )

    bind = op.get_bind()
    family_role.create(bind, checkfirst=True)
    schedule_status.create(bind, checkfirst=True)
    schedule_category.create(bind, checkfirst=True)
    gender_type.create(bind, checkfirst=True)
    blood_type_enum.create(bind, checkfirst=True)

    # --- users: remove profile fields (moved to profiles) ---
    op.drop_constraint("users_apple_id_key", "users", type_="unique")
    op.drop_column("users", "apple_id")
    op.drop_column("users", "full_name")
    op.drop_column("users", "dob")
    op.drop_column("users", "gender")
    op.drop_column("users", "avatar_url")

    # --- refresh_tokens + user_devices ---
    # Target schema matches UserDeviceModel: PK (id, user_id). This revision
    # recreates tables with PK(id) + FK refresh_tokens.device_id -> user_devices.id;
    # the following revision da58e3fdb641 switches to PK(id, user_id) and composite FK.
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index(op.f("ix_user_devices_user_id"), table_name="user_devices")
    op.drop_table("user_devices")

    op.create_table(
        "user_devices",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fcm_token", sa.Text(), nullable=True),
        sa.Column("device_name", sa.String(length=255), nullable=True),
        sa.Column("platform", sa.String(length=100), nullable=True),
        sa.Column(
            "last_active",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_devices_user_id"), "user_devices", ["user_id"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", sa.String(length=255), nullable=True),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["user_devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)

    # --- profiles & health ---
    op.create_table(
        "profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("linked_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("dob", sa.Date(), nullable=True),
        sa.Column("gender", gender_type, nullable=True),
        sa.Column("height_cm", sa.Numeric(5, 1), nullable=True),
        sa.Column("weight_kg", sa.Numeric(5, 1), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("linked_user_id"),
    )
    op.create_index(op.f("ix_profiles_owner_user_id"), "profiles", ["owner_user_id"], unique=False)

    op.create_table(
        "health_details",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("blood_type", blood_type_enum, nullable=True),
        sa.Column("chronic_diseases", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("allergies", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("emergency_contact", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id"),
    )

    # --- families ---
    op.create_table(
        "families",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("family_name", sa.String(length=255), nullable=False),
        sa.Column("invite_code", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_code"),
    )

    op.create_table(
        "family_memberships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            family_role,
            nullable=False,
            server_default=sa.text("'MEMBER'::family_role"),
        ),
        sa.Column("added_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("family_id", "profile_id", name="uq_family_membership_family_profile"),
    )
    op.create_index(
        op.f("ix_family_memberships_family_id"),
        "family_memberships",
        ["family_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_family_memberships_profile_id"),
        "family_memberships",
        ["profile_id"],
        unique=False,
    )

    # --- medical domain ---
    op.create_table(
        "medicine_inventory",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medicine_name", sa.String(length=255), nullable=False),
        sa.Column("medicine_type", sa.String(length=128), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("quantity_stock", sa.Numeric(12, 3), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("min_stock_alert", sa.Numeric(12, 3), nullable=True),
        sa.Column("instruction", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_medicine_inventory_family_id"),
        "medicine_inventory",
        ["family_id"],
        unique=False,
    )

    op.create_table(
        "medical_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("diagnosis_name", sa.Text(), nullable=True),
        sa.Column("diagnosis_slug", sa.Text(), nullable=True),
        sa.Column("doctor_name", sa.String(length=255), nullable=True),
        sa.Column("hospital_name", sa.Text(), nullable=True),
        sa.Column("visit_date", sa.Date(), nullable=True),
        sa.Column("attachment_urls", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_medical_records_profile_id"),
        "medical_records",
        ["profile_id"],
        unique=False,
    )

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

    op.create_table(
        "schedules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medicine_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("category", schedule_category, nullable=False),
        sa.Column("remind_time", sa.Time(), nullable=True),
        sa.Column("dosage_per_time", sa.Numeric(12, 3), nullable=True),
        sa.Column("rrule", sa.Text(), nullable=True),
        sa.Column(
            "status",
            schedule_status,
            nullable=False,
            server_default=sa.text("'ACTIVE'::schedule_status"),
        ),
        sa.ForeignKeyConstraint(["medicine_id"], ["medicine_inventory.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schedules_profile_id"), "schedules", ["profile_id"], unique=False)

    op.create_table(
        "schedule_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("action_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "action_time",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["action_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_schedule_logs_schedule_id"),
        "schedule_logs",
        ["schedule_id"],
        unique=False,
    )

    op.create_table(
        "growth_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("height_cm", sa.Numeric(6, 2), nullable=True),
        sa.Column("weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column(
            "recorded_at",
            sa.Date(),
            nullable=False,
            server_default=sa.text("CURRENT_DATE"),
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_growth_records_profile_id"),
        "growth_records",
        ["profile_id"],
        unique=False,
    )

    op.create_table(
        "activity_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_desc", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_activity_logs_family_id"),
        "activity_logs",
        ["family_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_activity_logs_family_id"), table_name="activity_logs")
    op.drop_table("activity_logs")
    op.drop_index(op.f("ix_growth_records_profile_id"), table_name="growth_records")
    op.drop_table("growth_records")
    op.drop_index(op.f("ix_schedule_logs_schedule_id"), table_name="schedule_logs")
    op.drop_table("schedule_logs")
    op.drop_index(op.f("ix_schedules_profile_id"), table_name="schedules")
    op.drop_table("schedules")
    op.drop_index(op.f("ix_vaccine_history_profile_id"), table_name="vaccine_history")
    op.drop_table("vaccine_history")
    op.drop_index(op.f("ix_medical_records_profile_id"), table_name="medical_records")
    op.drop_table("medical_records")
    op.drop_index(op.f("ix_medicine_inventory_family_id"), table_name="medicine_inventory")
    op.drop_table("medicine_inventory")
    op.drop_index(op.f("ix_family_memberships_profile_id"), table_name="family_memberships")
    op.drop_index(op.f("ix_family_memberships_family_id"), table_name="family_memberships")
    op.drop_table("family_memberships")
    op.drop_table("families")
    op.drop_table("health_details")
    op.drop_index(op.f("ix_profiles_owner_user_id"), table_name="profiles")
    op.drop_table("profiles")

    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index(op.f("ix_user_devices_user_id"), table_name="user_devices")
    op.drop_table("user_devices")

    op.create_table(
        "user_devices",
        sa.Column("device_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fcm_token", sa.Text(), nullable=True),
        sa.Column("device_name", sa.String(length=255), nullable=True),
        sa.Column("platform", sa.String(length=100), nullable=True),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("device_id", "user_id"),
    )
    op.create_index(op.f("ix_user_devices_user_id"), "user_devices", ["user_id"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", sa.String(length=255), nullable=True),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["device_id", "user_id"],
            ["user_devices.device_id", "user_devices.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)

    op.add_column("users", sa.Column("avatar_url", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("gender", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("dob", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("full_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("apple_id", sa.String(length=128), nullable=True))
    op.create_unique_constraint("users_apple_id_key", "users", ["apple_id"])

    op.execute("DROP TYPE IF EXISTS blood_type_enum CASCADE")
    op.execute("DROP TYPE IF EXISTS gender_type CASCADE")
    op.execute("DROP TYPE IF EXISTS schedule_category CASCADE")
    op.execute("DROP TYPE IF EXISTS schedule_status CASCADE")
    op.execute("DROP TYPE IF EXISTS family_role CASCADE")

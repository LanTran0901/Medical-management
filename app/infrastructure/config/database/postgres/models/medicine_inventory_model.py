from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.config.database.base import Base


class MedicineInventoryModel(Base):
    __tablename__ = "medicine_inventory"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    medicine_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    medicine_type: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    quantity_stock: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 3), nullable=True)
    unit: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    min_stock_alert: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 3), nullable=True)
    instruction: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    dosage_value: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 3), nullable=True)
    dosage_unit: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    dosage_per_use_value: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 3), nullable=True)
    dosage_per_use_unit: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    use_tags: Mapped[list[str]] = mapped_column(
        sa.ARRAY(sa.Text()),
        nullable=False,
        server_default=sa.text("'{}'::text[]"),
    )
    storage_location: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    expiry_alert_days_before: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("30"),
    )
    low_stock_alert_enabled: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )


class MedicineReminderModel(Base):
    __tablename__ = "medicine_reminders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    medicine_inventory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("medicine_inventory.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("true"),
    )
    start_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    repeat_every_value: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("1"),
    )
    repeat_every_unit: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        server_default="week",
    )
    active_days: Mapped[list[int]] = mapped_column(
        sa.ARRAY(sa.Integer()),
        nullable=False,
        server_default=sa.text("'{}'::integer[]"),
    )
    times: Mapped[list[str]] = mapped_column(
        sa.ARRAY(sa.String(5)),
        nullable=False,
        server_default=sa.text("'{}'::varchar[]"),
    )
    remind_before_minutes: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("0"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )


class FamilyMedicineInventoryModel(Base):
    __tablename__ = "family_medicine_inventory"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    medicine_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    quantity_stock: Mapped[Decimal] = mapped_column(sa.Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    expiry_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    storage_location: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    min_stock_alert: Mapped[Decimal] = mapped_column(
        sa.Numeric(12, 3),
        nullable=False,
        server_default=sa.text("0"),
    )
    low_stock_alert_enabled: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("true"),
    )
    expiry_alert_days_before: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("30"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )

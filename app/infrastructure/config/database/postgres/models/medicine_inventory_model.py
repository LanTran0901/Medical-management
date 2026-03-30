from __future__ import annotations

import uuid
from datetime import date
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
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    medicine_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    medicine_type: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    quantity_stock: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 3), nullable=True)
    unit: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    min_stock_alert: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 3), nullable=True)
    instruction: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    expiry_alert_days_before: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

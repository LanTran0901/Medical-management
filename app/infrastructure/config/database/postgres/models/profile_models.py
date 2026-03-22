from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.config.database.base import Base

gender_type_pg = ENUM(
    "male",
    "female",
    "other",
    name="gender_type",
    create_type=False,
)

blood_type_pg = ENUM(
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


class ProfileModel(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    linked_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    full_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    dob: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(gender_type_pg, nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 1), nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 1), nullable=True)
    address: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )


class HealthDetailModel(Base):
    __tablename__ = "health_details"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    blood_type: Mapped[str | None] = mapped_column(blood_type_pg, nullable=True)
    chronic_diseases: Mapped[list[str] | None] = mapped_column(
        sa.ARRAY(sa.Text()),
        nullable=True,
    )
    allergies: Mapped[list[str] | None] = mapped_column(
        sa.ARRAY(sa.Text()),
        nullable=True,
    )
    emergency_contact: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )

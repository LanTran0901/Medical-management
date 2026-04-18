from __future__ import annotations

import uuid
from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

vaccination_remind_before_unit_pg = ENUM(
    "MINUTES",
    "HOURS",
    "DAYS",
    "WEEKS",
    name="follow_up_remind_before_unit",
    create_type=False,
)

from app.infrastructure.config.database.base import Base


class VaccinationRecommendationModel(Base):
    __tablename__ = "vaccination_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    code: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, unique=True)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False, index=True)
    disease_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    total_doses: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("3"))
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )


class UserVaccinationModel(Base):
    __tablename__ = "user_vaccinations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("vaccination_recommendations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "profile_id",
            "recommendation_id",
            name="uq_user_vaccination_profile_recommendation",
        ),
    )


class VaccinationDoseModel(Base):
    __tablename__ = "vaccination_doses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    user_vaccination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("user_vaccinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dose_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    administered_at: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    scheduled_at: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    location: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    reaction: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    proof_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    reminder_enabled: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false"),
    )
    remind_before_value: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    remind_before_unit: Mapped[str | None] = mapped_column(
        vaccination_remind_before_unit_pg,
        nullable=True,
    )

    __table_args__ = (
        sa.CheckConstraint(
            "(NOT reminder_enabled AND remind_before_value IS NULL AND remind_before_unit IS NULL) OR "
            "(reminder_enabled AND remind_before_value IS NOT NULL AND remind_before_unit IS NOT NULL "
            "AND remind_before_value > 0)",
            name="ck_vaccination_dose_reminder_offset",
        ),
    )

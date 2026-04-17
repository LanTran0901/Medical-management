from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.config.database.base import Base

appointment_reminder_type_pg = ENUM(
    "checkup",
    "vaccine",
    name="appointment_reminder_type",
    create_type=False,
)

appointment_reminder_status_pg = ENUM(
    "pending",
    "done",
    "missed",
    name="appointment_reminder_status",
    create_type=False,
)

appointment_remind_before_unit_pg = ENUM(
    "MINUTES",
    "HOURS",
    "DAYS",
    "WEEKS",
    name="follow_up_remind_before_unit",
    create_type=False,
)


class AppointmentReminderModel(Base):
    """Unified reminders for follow-up visits and vaccination appointments."""

    __tablename__ = "appointment_reminders"

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
    reminder_type: Mapped[str] = mapped_column("type", appointment_reminder_type_pg, nullable=False)
    title: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    hospital_name: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    department: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    appointment_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    remind_before_value: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("60"))
    remind_before_unit: Mapped[str] = mapped_column(
        appointment_remind_before_unit_pg,
        nullable=False,
        server_default=sa.text("'MINUTES'::follow_up_remind_before_unit"),
    )
    vaccine_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    dose_number: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    total_doses: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        appointment_reminder_status_pg,
        nullable=False,
        server_default=sa.text("'pending'::appointment_reminder_status"),
    )
    note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    follow_up_appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("follow_up_appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vaccination_dose_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("vaccination_doses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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

    __table_args__ = (
        sa.CheckConstraint(
            "NOT (follow_up_appointment_id IS NOT NULL AND vaccination_dose_id IS NOT NULL)",
            name="ck_appointment_reminders_single_source",
        ),
        sa.CheckConstraint(
            "(follow_up_appointment_id IS NULL) OR (type = 'checkup'::appointment_reminder_type)",
            name="ck_appointment_reminders_follow_up_is_checkup",
        ),
        sa.CheckConstraint(
            "(vaccination_dose_id IS NULL) OR (type = 'vaccine'::appointment_reminder_type)",
            name="ck_appointment_reminders_dose_is_vaccine",
        ),
        sa.CheckConstraint(
            "remind_before_value > 0",
            name="ck_appointment_reminders_remind_before_value_positive",
        ),
    )

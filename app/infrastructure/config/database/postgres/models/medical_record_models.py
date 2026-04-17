from __future__ import annotations

import uuid
from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.config.database.base import Base

reminder_outcome_pg = ENUM(
    "COMPLETED",
    "SNOOZED",
    "SKIPPED",
    "DISMISSED",
    name="reminder_outcome",
    create_type=False,
)

follow_up_remind_before_unit_pg = ENUM(
    "MINUTES",
    "HOURS",
    "DAYS",
    "WEEKS",
    name="follow_up_remind_before_unit",
    create_type=False,
)


class MedicalRecordModel(Base):
    __tablename__ = "medical_records"

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
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    diagnosis_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    diagnosis_slug: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    hospital_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    visit_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    specialty: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    symptoms: Mapped[list[str] | None] = mapped_column(sa.ARRAY(sa.Text()), nullable=True)
    test_results: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    doctor_advice: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
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
        index=True,
    )


class MedicalRecordAttachmentModel(Base):
    __tablename__ = "medical_record_attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    medical_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("medical_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    file_url: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )


class FollowUpAppointmentModel(Base):
    __tablename__ = "follow_up_appointments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    medical_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("medical_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    appointment_date: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )
    purpose: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    facility_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    remind_before_value: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    remind_before_unit: Mapped[str | None] = mapped_column(
        follow_up_remind_before_unit_pg,
        nullable=True,
    )
    reminder_enabled: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )

    __table_args__ = (
        sa.CheckConstraint(
            "(NOT reminder_enabled AND remind_before_value IS NULL AND remind_before_unit IS NULL) OR "
            "(reminder_enabled AND remind_before_value IS NOT NULL AND remind_before_unit IS NOT NULL "
            "AND remind_before_value > 0)",
            name="ck_follow_up_appt_reminder_offset",
        ),
    )


class FollowUpReminderActionModel(Base):
    __tablename__ = "follow_up_reminder_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    follow_up_appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("follow_up_appointments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outcome: Mapped[str] = mapped_column(reminder_outcome_pg, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

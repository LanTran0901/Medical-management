"""003 medicine-inventory-api: medical_record_attachments, follow-ups, reminder actions

Revision ID: 003_mi_02
Revises: 003_mi_01
Create Date: 2026-03-28
"""

from __future__ import annotations

import json
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_mi_02"
down_revision: Union[str, None] = "003_mi_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    # Tạo type một lần (checkfirst: idempotent nếu DB đã có type từ lần chạy dở).
    reminder_outcome_type = postgresql.ENUM(
        "COMPLETED",
        "SNOOZED",
        "SKIPPED",
        "DISMISSED",
        name="reminder_outcome",
        create_type=True,
    )
    reminder_outcome_type.create(bind, checkfirst=True)

    # Cột bảng: create_type=False — nếu True, create_table sẽ emit CREATE TYPE lần nữa → DuplicateObject.
    reminder_outcome_col = postgresql.ENUM(
        "COMPLETED",
        "SNOOZED",
        "SKIPPED",
        "DISMISSED",
        name="reminder_outcome",
        create_type=False,
    )

    op.create_table(
        "medical_record_attachments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("medical_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("file_type", sa.String(length=128), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["medical_record_id"],
            ["medical_records.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_medical_record_attachments_medical_record_id"),
        "medical_record_attachments",
        ["medical_record_id"],
        unique=False,
    )

    op.create_table(
        "follow_up_appointments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("medical_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column(
            "remind_before_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.ForeignKeyConstraint(
            ["medical_record_id"],
            ["medical_records.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_follow_up_appointments_medical_record_id"),
        "follow_up_appointments",
        ["medical_record_id"],
        unique=False,
    )

    op.create_table(
        "follow_up_reminder_actions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("follow_up_appointment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome", reminder_outcome_col, nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["follow_up_appointment_id"],
            ["follow_up_appointments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_follow_up_reminder_actions_follow_up_id"),
        "follow_up_reminder_actions",
        ["follow_up_appointment_id"],
        unique=False,
    )

    # Best-effort migration from attachment_urls JSONB (see research.md)
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, attachment_urls FROM medical_records WHERE attachment_urls IS NOT NULL")
    ).fetchall()
    for record_id, raw in rows:
        if raw is None:
            continue
        urls: list[str] = []
        if isinstance(raw, list):
            urls = [str(u) for u in raw if u]
        elif isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    urls = [str(u) for u in parsed if u]
                else:
                    urls = [raw.strip()] if raw.strip() else []
            except json.JSONDecodeError:
                urls = [raw.strip()] if raw.strip() else []
        elif isinstance(raw, dict):
            # rare: single object — skip or stringify
            continue
        for u in urls:
            u = u.strip()
            if not u:
                continue
            name = (u.split("/")[-1] or "attachment")[:512]
            connection.execute(
                sa.text(
                    """
                    INSERT INTO medical_record_attachments (id, medical_record_id, file_name, file_type, file_url)
                    VALUES (:id, :rid, :fn, :ft, :fu)
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "rid": record_id,
                    "fn": name,
                    "ft": "application/octet-stream",
                    "fu": u[:8192],
                },
            )

    op.drop_column("medical_records", "attachment_urls")


def downgrade() -> None:
    op.add_column(
        "medical_records",
        sa.Column("attachment_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.drop_index(
        op.f("ix_follow_up_reminder_actions_follow_up_id"),
        table_name="follow_up_reminder_actions",
    )
    op.drop_table("follow_up_reminder_actions")
    op.drop_index(
        op.f("ix_follow_up_appointments_medical_record_id"),
        table_name="follow_up_appointments",
    )
    op.drop_table("follow_up_appointments")
    op.drop_index(
        op.f("ix_medical_record_attachments_medical_record_id"),
        table_name="medical_record_attachments",
    )
    op.drop_table("medical_record_attachments")
    op.execute(sa.text("DROP TYPE IF EXISTS reminder_outcome"))

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.config.database.base import Base


class _MedicalDictionaryBase:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )
    source_index: Mapped[int] = mapped_column(sa.Integer(), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(sa.String(512), nullable=False, index=True)
    aliases: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))
    summary: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    content: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    source_file: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class DiseaseModel(_MedicalDictionaryBase, Base):
    __tablename__ = "diseases"


class DrugModel(_MedicalDictionaryBase, Base):
    __tablename__ = "drugs"


class VaccineModel(_MedicalDictionaryBase, Base):
    __tablename__ = "vaccines"

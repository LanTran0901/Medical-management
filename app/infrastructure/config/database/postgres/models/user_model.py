
import uuid
from datetime import datetime, date

import sqlalchemy as sa
from sqlalchemy import Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.config.database.base import Base

# Native PostgreSQL ENUM type — Alembic autogenerate will emit CREATE TYPE
user_status_enum = PgEnum(
    "active",
    "inactive",
    "banned",
    name="user_status",
    create_type=True,
)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        sa.String(255),
        unique=True,
        nullable=False,
    )
    password_hash: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    google_id: Mapped[str | None] = mapped_column(
        sa.String(128), unique=True, nullable=True
    )
    apple_id: Mapped[str | None] = mapped_column(
        sa.String(128), unique=True, nullable=True
    )
    full_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    dob: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str] = mapped_column(
        user_status_enum,
        nullable=False,
        server_default="active",
    )
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, default=None
    )

    def __repr__(self) -> str:
        return f"<UserModel id={self.id} email={self.email!r} status={self.status}>"

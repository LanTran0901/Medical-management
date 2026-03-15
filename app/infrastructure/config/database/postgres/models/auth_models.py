import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.config.database.base import Base

class UserDeviceModel(Base):
    __tablename__ = "user_devices"

    device_id: Mapped[str] = mapped_column(sa.String(255), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )

    fcm_token: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    device_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    platform: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    last_active: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<UserDeviceModel device_id={self.device_id} user_id={self.user_id}>"

class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Chú ý: Vì UserDevice dùng Composite Key nên FK phải có đủ 2 cột
    # Trong RefreshTokenModel, ta sẽ lưu `device_id` và dùng chung cột `user_id`
    device_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["device_id", "user_id"],
            ["user_devices.device_id", "user_devices.user_id"],
            ondelete="CASCADE",
        ),
    )
    token_hash: Mapped[str] = mapped_column(
        sa.Text,
        unique=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )
    is_revoked: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )

    def __repr__(self) -> str:
        return f"<RefreshTokenModel id={self.id} user_id={self.user_id}>"

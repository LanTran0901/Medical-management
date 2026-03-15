from __future__ import annotations

from uuid import UUID
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.auth_port import AuthRepositoryPort
from app.domain.entities.auth import UserDevice, RefreshToken
from app.infrastructure.config.database.postgres.models.auth_models import UserDeviceModel, RefreshTokenModel

class AuthRepositoryPG(AuthRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_device(self, device: UserDevice) -> UserDevice:
        model = self._device_to_model(device)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._device_to_entity(model)

    async def get_device(self, device_id: str, user_id: UUID) -> Optional[UserDevice]:
        # get() with composite key takes a tuple of primary key values in the order defined in the model
        model = await self.session.get(UserDeviceModel, (device_id, user_id))
        if model is None:
            return None
        return self._device_to_entity(model)

    async def update_device(self, device: UserDevice) -> UserDevice:
        model = await self.session.get(UserDeviceModel, (device.device_id, device.user_id))
        if model is None:
            raise ValueError("Device not found.")

        model.fcm_token = device.fcm_token
        model.device_name = device.device_name
        model.platform = device.platform
        model.last_active = device.last_active

        await self.session.flush()
        await self.session.refresh(model)
        return self._device_to_entity(model)

    async def get_devices_by_user_id(self, user_id: UUID) -> list[UserDevice]:
        stmt = select(UserDeviceModel).where(UserDeviceModel.user_id == user_id)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._device_to_entity(m) for m in models]

    async def create_refresh_token(self, token: RefreshToken) -> RefreshToken:
        model = self._token_to_model(token)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._token_to_entity(model)

    async def get_refresh_token(self, token_hash: str) -> Optional[RefreshToken]:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._token_to_entity(model)

    async def update_refresh_token(self, token: RefreshToken) -> RefreshToken:
        model = await self.session.get(RefreshTokenModel, token.id)
        if model is None:
            raise ValueError("Token not found.")

        model.is_revoked = token.is_revoked
        # Only immutable fields shouldn't be updated, but we might just update all mapped fields
        model.token_hash = token.token_hash

        await self.session.flush()
        await self.session.refresh(model)
        return self._token_to_entity(model)

    @staticmethod
    def _device_to_entity(model: UserDeviceModel) -> UserDevice:
        return UserDevice(
            device_id=model.device_id,
            user_id=model.user_id,
            fcm_token=model.fcm_token,
            device_name=model.device_name,
            platform=model.platform,
            last_active=model.last_active,
        )

    @staticmethod
    def _device_to_model(device: UserDevice) -> UserDeviceModel:
        return UserDeviceModel(
            device_id=device.device_id,
            user_id=device.user_id,
            fcm_token=device.fcm_token,
            device_name=device.device_name,
            platform=device.platform,
            last_active=device.last_active,
        )

    @staticmethod
    def _token_to_entity(model: RefreshTokenModel) -> RefreshToken:
        return RefreshToken(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            expires_at=model.expires_at,
            is_revoked=model.is_revoked,
            created_at=model.created_at,
            device_id=model.device_id,
        )

    @staticmethod
    def _token_to_model(token: RefreshToken) -> RefreshTokenModel:
        return RefreshTokenModel(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            is_revoked=token.is_revoked,
            created_at=token.created_at,
            device_id=token.device_id,
        )

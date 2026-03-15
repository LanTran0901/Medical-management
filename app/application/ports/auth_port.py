from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional

from app.domain.entities.auth import UserDevice, RefreshToken


class AuthRepositoryPort(ABC):
    @abstractmethod
    async def create_device(self, device: UserDevice) -> UserDevice:
        raise NotImplementedError

    @abstractmethod
    async def get_device(self, device_id: str, user_id: UUID) -> Optional[UserDevice]:
        raise NotImplementedError

    @abstractmethod
    async def update_device(self, device: UserDevice) -> UserDevice:
        raise NotImplementedError

    @abstractmethod
    async def get_devices_by_user_id(self, user_id: UUID) -> list[UserDevice]:
        raise NotImplementedError

    @abstractmethod
    async def create_refresh_token(self, token: RefreshToken) -> RefreshToken:
        raise NotImplementedError

    @abstractmethod
    async def get_refresh_token(self, token_hash: str) -> Optional[RefreshToken]:
        raise NotImplementedError

    @abstractmethod
    async def update_refresh_token(self, token: RefreshToken) -> RefreshToken:
        raise NotImplementedError

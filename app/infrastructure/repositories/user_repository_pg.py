from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.user_port import UserRepositoryPort
from app.domain.entities.user import User, UserStatus
from app.infrastructure.config.database.postgres.models.user_model import UserModel


class UserRepositoryPG(UserRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user: User) -> User:
        model = self._to_model(user)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self.session.get(UserModel, user_id)
        if model is None:
            return None
        return self._to_entity(model)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email.lower().strip())
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def list_users(self) -> list[User]:
        stmt = (
            select(UserModel)
            .where(UserModel.deleted_at.is_(None))
            .order_by(UserModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [self._to_entity(model) for model in result.scalars().all()]

    async def update(self, user: User) -> User:
        model = await self.session.get(UserModel, user.id)
        if model is None:
            raise ValueError("User not found.")

        model.email = user.email
        model.full_name = user.full_name
        model.dob = user.dob
        model.gender = user.gender
        model.avatar_url = user.avatar_url
        model.password_hash = user.password_hash
        model.google_id = user.google_id
        model.apple_id = user.apple_id
        model.status = user.status.value
        model.deleted_at = user.deleted_at

        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            status=UserStatus(model.status),
            created_at=model.created_at,
            full_name=model.full_name,
            dob=model.dob,
            gender=model.gender,
            avatar_url=model.avatar_url,
            password_hash=model.password_hash,
            google_id=model.google_id,
            apple_id=model.apple_id,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def _to_model(user: User) -> UserModel:
        return UserModel(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            google_id=user.google_id,
            apple_id=user.apple_id,
            full_name=user.full_name,
            dob=user.dob,
            gender=user.gender,
            avatar_url=user.avatar_url,
            status=user.status.value,
            created_at=user.created_at,
            deleted_at=user.deleted_at,
        )
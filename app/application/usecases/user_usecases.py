from __future__ import annotations

from uuid import UUID

from app.application.dtos.user_dto import CreateUserRequest, UpdateUserRequest
from app.application.ports.user_port import UserRepositoryPort
from app.domain.entities.user import User


class CreateUserUseCase:
    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self.user_repository = user_repository

    async def execute(self, request: CreateUserRequest) -> User:
        existing_user = await self.user_repository.get_by_email(request.email)
        if existing_user is not None:
            raise ValueError("User with this email already exists.")

        user = User.create(
            email=request.email,
            full_name=request.full_name,
            avatar_url=request.avatar_url,
            password_hash=request.password_hash,
            google_id=request.google_id,
            apple_id=request.apple_id,
        )
        return await self.user_repository.create(user)


class GetUserUseCase:
    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self.user_repository = user_repository

    async def execute(self, user_id: UUID) -> User:
        user = await self.user_repository.get_by_id(user_id)
        if user is None or user.is_deleted:
            raise ValueError("User not found.")
        return user


class ListUsersUseCase:
    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self.user_repository = user_repository

    async def execute(self) -> list[User]:
        return await self.user_repository.list_users()


class UpdateUserUseCase:
    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self.user_repository = user_repository

    async def execute(self, user_id: UUID, request: UpdateUserRequest) -> User:
        user = await self.user_repository.get_by_id(user_id)
        if user is None or user.is_deleted:
            raise ValueError("User not found.")

        update_data = request.model_dump(exclude_unset=True)
        for field_name, field_value in update_data.items():
            setattr(user, field_name, field_value)

        return await self.user_repository.update(user)


class DeleteUserUseCase:
    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self.user_repository = user_repository

    async def execute(self, user_id: UUID) -> None:
        user = await self.user_repository.get_by_id(user_id)
        if user is None or user.is_deleted:
            raise ValueError("User not found.")

        user.soft_delete()
        await self.user_repository.update(user)
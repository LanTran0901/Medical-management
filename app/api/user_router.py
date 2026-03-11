from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.user_dto import CreateUserRequest, UpdateUserRequest, UserResponse
from app.application.usecases.user_usecases import (
    CreateUserUseCase,
    DeleteUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    UpdateUserUseCase,
)
from app.infrastructure.config.database.postgres.connection import get_session
from app.infrastructure.repositories.user_repository_pg import UserRepositoryPG

router = APIRouter(prefix="/users", tags=["users"])


def get_user_repository(session: AsyncSession = Depends(get_session)) -> UserRepositoryPG:
    return UserRepositoryPG(session)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: CreateUserRequest,
    repository: UserRepositoryPG = Depends(get_user_repository),
) -> UserResponse:
    try:
        user = await CreateUserUseCase(repository).execute(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserResponse.from_entity(user)


@router.get("", response_model=list[UserResponse])
async def list_users(
    repository: UserRepositoryPG = Depends(get_user_repository),
) -> list[UserResponse]:
    users = await ListUsersUseCase(repository).execute()
    return [UserResponse.from_entity(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    repository: UserRepositoryPG = Depends(get_user_repository),
) -> UserResponse:
    try:
        user = await GetUserUseCase(repository).execute(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UserResponse.from_entity(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: UpdateUserRequest,
    repository: UserRepositoryPG = Depends(get_user_repository),
) -> UserResponse:
    try:
        user = await UpdateUserUseCase(repository).execute(user_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UserResponse.from_entity(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    repository: UserRepositoryPG = Depends(get_user_repository),
) -> Response:
    try:
        await DeleteUserUseCase(repository).execute(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
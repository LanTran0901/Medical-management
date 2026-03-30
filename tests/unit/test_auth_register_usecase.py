from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.dtos.auth_dto import RegisterRequest
from app.application.usecases.auth_usecases import RegisterUseCase
from app.domain.entities.user import User, UserStatus


def _user(email: str, phone_number: str | None = None) -> User:
    return User(
        id=uuid4(),
        email=email,
        status=UserStatus.active,
        created_at=datetime.now(timezone.utc),
        password_hash="hash",
        phone_number=phone_number,
    )


@pytest.mark.asyncio
async def test_register_usecase_rejects_duplicate_phone() -> None:
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=None)
    repo.get_by_phone = AsyncMock(return_value=_user("a@test.local", "+15551234567"))
    usecase = RegisterUseCase(repo)

    with pytest.raises(ValueError, match="phone number"):
        await usecase.execute(
            RegisterRequest(
                email="b@test.local",
                phone_number="+15551234567",
                password="password123",
            )
        )


@pytest.mark.asyncio
async def test_register_usecase_persists_phone_number() -> None:
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=None)
    repo.get_by_phone = AsyncMock(return_value=None)

    async def _create(user: User) -> User:
        return user

    repo.create = AsyncMock(side_effect=_create)
    usecase = RegisterUseCase(repo)

    user = await usecase.execute(
        RegisterRequest(
            email="c@test.local",
            phone_number="+15557654321",
            password="password123",
        )
    )

    assert user.phone_number == "+15557654321"
    repo.get_by_phone.assert_awaited_once_with("+15557654321")

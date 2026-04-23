from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi import HTTPException
import pytest

from app.api.user_router import patch_current_user_me
from app.application.dtos.user_dto import PatchUserMeRequest
from app.domain.entities.user import User


@pytest.mark.asyncio
async def test_patch_current_user_me_updates_authenticated_user_phone_number() -> None:
    current_user = User.create(
        email="me@test.local",
        password_hash="hashed",
        phone_number="+15550000000",
    )
    repository = AsyncMock()
    repository.update = AsyncMock(return_value=current_user)

    response = await patch_current_user_me(
        body=PatchUserMeRequest(phone_number="+15551112222"),
        current_user=current_user,
        repository=repository,
    )

    repository.update.assert_awaited_once_with(current_user)
    assert current_user.phone_number == "+15551112222"
    assert response.phone_number == "+15551112222"


@pytest.mark.asyncio
async def test_patch_current_user_me_updates_authenticated_user_email() -> None:
    current_user = User.create(
        email="me@test.local",
        password_hash="hashed",
        phone_number="+15550000000",
    )
    repository = AsyncMock()
    repository.get_by_email = AsyncMock(return_value=None)
    repository.update = AsyncMock(return_value=current_user)

    response = await patch_current_user_me(
        body=PatchUserMeRequest(email="New.Email@Test.Local "),
        current_user=current_user,
        repository=repository,
    )

    repository.get_by_email.assert_awaited_once_with("new.email@test.local")
    repository.update.assert_awaited_once_with(current_user)
    assert current_user.email == "new.email@test.local"
    assert response.email == "new.email@test.local"


@pytest.mark.asyncio
async def test_patch_current_user_me_rejects_existing_email() -> None:
    current_user = User.create(
        email="me@test.local",
        password_hash="hashed",
        phone_number="+15550000000",
    )
    other_user = User.create(
        email="other@test.local",
        password_hash="hashed",
        phone_number="+15550000001",
    )
    repository = AsyncMock()
    repository.get_by_email = AsyncMock(return_value=other_user)
    repository.update = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await patch_current_user_me(
            body=PatchUserMeRequest(email="other@test.local"),
            current_user=current_user,
            repository=repository,
        )

    assert exc_info.value.status_code == 409
    repository.update.assert_not_awaited()

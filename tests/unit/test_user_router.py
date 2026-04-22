from __future__ import annotations

from unittest.mock import AsyncMock

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

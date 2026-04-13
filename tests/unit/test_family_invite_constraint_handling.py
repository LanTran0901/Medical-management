from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.application.dtos.family_dto import InviteByPhoneRequest
from app.application.family_errors import ConflictError
from app.application.usecases.family_usecases import FamiliesService
from app.domain.entities.family import Family, FamilyMembership, FamilyRole


def _dt() -> datetime:
    return datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_invite_member_by_phone_maps_unique_violation_to_conflict() -> None:
    repo = AsyncMock()
    users = AsyncMock()
    access = AsyncMock()

    svc = FamiliesService(repo, users, access)

    family_id = uuid4()
    user_id = uuid4()

    repo.get_family = AsyncMock(
        return_value=Family(
            id=family_id,
            family_name="A",
            invite_code="abc",
            created_at=_dt(),
            address=None,
            avatar_url=None,
        )
    )
    access.require_family_admin = AsyncMock(
        return_value=FamilyMembership(
            id=uuid4(),
            family_id=family_id,
            profile_id=uuid4(),
            role=FamilyRole.ADMIN,
            added_by=user_id,
            created_at=_dt(),
            relation_role=None,
        )
    )
    users.get_by_phone = AsyncMock(return_value=None)
    repo.find_pending_invite = AsyncMock(return_value=None)
    repo.create_family_invite = AsyncMock(
        side_effect=IntegrityError(
            "INSERT",
            {},
            SimpleNamespace(pgcode="23505"),
        )
    )

    with pytest.raises(ConflictError, match="Pending invite already exists"):
        await svc.invite_member_by_phone(
            family_id,
            user_id,
            InviteByPhoneRequest(phone_number="+84901234567"),
        )

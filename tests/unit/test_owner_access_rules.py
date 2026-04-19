from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.dtos.family_dto import CreateProfileInFamilyRequest, PatchMembershipRoleRequest
from app.application.family_errors import ForbiddenError, NotFoundError
from app.application.ports.access_control_port import MembershipAccessContext, ProfileAccessContext
from app.application.usecases.access_control_usecases import AccessControlService
from app.application.usecases.family_usecases import FamiliesService
from app.domain.entities.family import FamilyMembership, FamilyRole
from app.domain.entities.profile import Profile
from app.domain.entities.user import User, UserStatus


def _dt() -> datetime:
    return datetime.now(timezone.utc)


def _membership(*, family_id=None, role=FamilyRole.MEMBER, profile_id=None) -> FamilyMembership:
    return FamilyMembership(
        id=uuid4(),
        family_id=family_id or uuid4(),
        profile_id=profile_id or uuid4(),
        role=role,
        added_by=uuid4(),
        created_at=_dt(),
    )


def _profile(*, owner_user_id=None, linked_user_id=None) -> Profile:
    now = _dt()
    return Profile(
        id=uuid4(),
        owner_user_id=owner_user_id or uuid4(),
        linked_user_id=linked_user_id,
        full_name="Profile",
        dob=None,
        gender=None,
        height_cm=None,
        weight_kg=None,
        address=None,
        avatar_url=None,
        status="ACTIVE",
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def _user(user_id) -> User:
    return User(
        id=user_id,
        email="owner@test.local",
        status=UserStatus.active,
        created_at=_dt(),
        password_hash="hash",
    )


@pytest.mark.asyncio
async def test_require_family_member_returns_forbidden_when_family_exists_but_user_not_member() -> None:
    port = AsyncMock()
    port.get_user_membership_in_family.return_value = None
    port.family_exists.return_value = True
    svc = AccessControlService(port)

    with pytest.raises(ForbiddenError, match="Not a member"):
        await svc.require_family_member(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_require_family_member_returns_not_found_when_family_missing() -> None:
    port = AsyncMock()
    port.get_user_membership_in_family.return_value = None
    port.family_exists.return_value = False
    svc = AccessControlService(port)

    with pytest.raises(NotFoundError, match="Family not found"):
        await svc.require_family_member(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_require_membership_delete_allows_self_when_owner_user_matches() -> None:
    user_id = uuid4()
    family_id = uuid4()
    context = MembershipAccessContext(
        membership=_membership(family_id=family_id),
        owner_user_id=user_id,
        linked_user_id=None,
    )
    port = AsyncMock()
    port.get_membership_context.return_value = context
    svc = AccessControlService(port)

    out = await svc.require_membership_delete(uuid4(), user_id)
    assert out is context


@pytest.mark.asyncio
async def test_require_profile_read_allows_owner_even_without_linked_user() -> None:
    owner_id = uuid4()
    profile_context = ProfileAccessContext(
        profile=_profile(owner_user_id=owner_id, linked_user_id=None),
        family_ids=tuple(),
    )
    port = AsyncMock()
    port.get_profile_context.return_value = profile_context
    port.list_user_memberships_for_families.return_value = []
    svc = AccessControlService(port)

    out = await svc.require_profile_read(profile_context.profile.id, owner_id)
    assert out is profile_context


@pytest.mark.asyncio
async def test_admin_cannot_create_profile_with_owner_role() -> None:
    repo = AsyncMock()
    users = AsyncMock()
    access = AsyncMock()
    family_id = uuid4()
    actor_id = uuid4()
    target_owner_id = uuid4()
    access.require_family_admin.return_value = _membership(family_id=family_id, role=FamilyRole.ADMIN)
    users.get_by_id.return_value = _user(target_owner_id)
    svc = FamiliesService(repo, users, access)

    with pytest.raises(ForbiddenError, match="assign OWNER"):
        await svc.create_profile(
            family_id,
            actor_id,
            CreateProfileInFamilyRequest(
                full_name="Kid",
                owner_user_id=target_owner_id,
                role=FamilyRole.OWNER,
            ),
        )
    repo.create_profile_in_family.assert_not_awaited()


@pytest.mark.asyncio
async def test_owner_transfer_uses_transactional_transfer_method() -> None:
    repo = AsyncMock()
    users = AsyncMock()
    access = AsyncMock()
    family_id = uuid4()
    actor_id = uuid4()
    target_membership = _membership(family_id=family_id, role=FamilyRole.MEMBER)
    context = MembershipAccessContext(
        membership=target_membership,
        owner_user_id=uuid4(),
        linked_user_id=None,
    )
    access.require_membership_role_edit.return_value = context
    repo.transfer_family_owner.return_value = _membership(
        family_id=family_id,
        profile_id=target_membership.profile_id,
        role=FamilyRole.OWNER,
    )
    svc = FamiliesService(repo, users, access)

    out = await svc.patch_membership_role(
        target_membership.id,
        actor_id,
        PatchMembershipRoleRequest(role=FamilyRole.OWNER),
    )

    repo.transfer_family_owner.assert_awaited_once_with(
        family_id=family_id,
        new_owner_membership_id=target_membership.id,
        changed_by=actor_id,
    )
    assert out.role == FamilyRole.OWNER


@pytest.mark.asyncio
async def test_cannot_demote_current_owner_without_transfer() -> None:
    repo = AsyncMock()
    users = AsyncMock()
    access = AsyncMock()
    family_id = uuid4()
    owner_membership = _membership(family_id=family_id, role=FamilyRole.OWNER)
    access.require_membership_role_edit.return_value = MembershipAccessContext(
        membership=owner_membership,
        owner_user_id=uuid4(),
        linked_user_id=None,
    )
    svc = FamiliesService(repo, users, access)

    with pytest.raises(ForbiddenError, match="transfer ownership"):
        await svc.patch_membership_role(
            owner_membership.id,
            uuid4(),
            PatchMembershipRoleRequest(role=FamilyRole.ADMIN),
        )
    repo.update_membership_role.assert_not_awaited()


@pytest.mark.asyncio
async def test_require_profile_health_edit_allows_linked_user_even_without_family_admin() -> None:
    user_id = uuid4()
    profile = _profile(owner_user_id=user_id, linked_user_id=user_id)
    ctx = ProfileAccessContext(profile=profile, family_ids=tuple())
    port = AsyncMock()
    port.get_profile_context.return_value = ctx
    svc = AccessControlService(port)

    out = await svc.require_profile_health_edit(profile.id, user_id)
    assert out is ctx
    port.list_user_memberships_for_families.assert_not_awaited()


@pytest.mark.asyncio
async def test_require_profile_health_edit_allows_owner_without_linked_user() -> None:
    owner_id = uuid4()
    profile = _profile(owner_user_id=owner_id, linked_user_id=None)
    ctx = ProfileAccessContext(profile=profile, family_ids=tuple())
    port = AsyncMock()
    port.get_profile_context.return_value = ctx
    svc = AccessControlService(port)

    out = await svc.require_profile_health_edit(profile.id, owner_id)
    assert out is ctx


@pytest.mark.asyncio
async def test_require_profile_health_edit_forbids_member_for_other_profile() -> None:
    family_id = uuid4()
    other_user = uuid4()
    profile = _profile(owner_user_id=other_user, linked_user_id=other_user)
    ctx = ProfileAccessContext(profile=profile, family_ids=(family_id,))
    port = AsyncMock()
    port.get_profile_context.return_value = ctx
    port.list_user_memberships_for_families.return_value = [
        _membership(family_id=family_id, role=FamilyRole.MEMBER),
    ]
    svc = AccessControlService(port)
    actor = uuid4()

    with pytest.raises(ForbiddenError, match="Not allowed to edit health details"):
        await svc.require_profile_health_edit(profile.id, actor)


@pytest.mark.asyncio
async def test_require_profile_health_edit_allows_family_admin_for_other_profile() -> None:
    family_id = uuid4()
    profile = _profile()
    ctx = ProfileAccessContext(profile=profile, family_ids=(family_id,))
    port = AsyncMock()
    port.get_profile_context.return_value = ctx
    port.list_user_memberships_for_families.return_value = [
        _membership(family_id=family_id, role=FamilyRole.ADMIN),
    ]
    svc = AccessControlService(port)
    admin_id = uuid4()

    out = await svc.require_profile_health_edit(profile.id, admin_id)
    assert out is ctx

"""Unit tests cho `FamiliesService` — mock repository / user repo (không cần DB)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.application.dtos.family_dto import (
    CreateFamilyRequest,
    CreateProfileInFamilyRequest,
    InviteByPhoneRequest,
    JoinFamilyRequest,
    PatchFamilyRequest,
    PatchHealthDetailRequest,
    PatchMembershipRoleRequest,
    PatchProfileRequest,
)
from app.application.family_errors import ConflictError, ForbiddenError, NotFoundError
from app.application.ports.access_control_port import MembershipAccessContext
from app.application.usecases.access_control_usecases import AccessControlService
from app.application.usecases.family_usecases import FamiliesService
from app.domain.entities.family import (
    Family,
    FamilyInvite,
    FamilyInviteStatus,
    FamilyMembership,
    FamilyRole,
    PublicInvitePreview,
)
from app.domain.entities.health_detail import HealthDetail
from app.domain.entities.profile import Profile
from app.domain.entities.user import User, UserStatus

def _dt() -> datetime:
    return datetime.now(timezone.utc)


def _family(fid=None, name="N", code="abc") -> Family:
    return Family(
        id=fid or uuid4(),
        family_name=name,
        invite_code=code,
        created_at=_dt(),
        address="123 Family St",
        avatar_url="https://example.com/family.png",
    )


def _profile(pid=None, owner=None, linked=None, name="P", status=None, avatar_url=None) -> Profile:
    now = _dt()
    return Profile(
        id=pid or uuid4(),
        owner_user_id=owner or uuid4(),
        linked_user_id=linked,
        full_name=name,
        dob=None,
        gender=None,
        height_cm=None,
        weight_kg=None,
        address=None,
        avatar_url=avatar_url,
        status=status,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def _invite_preview(fam: Family, *, valid: bool = True) -> PublicInvitePreview:
    return PublicInvitePreview(
        family_id=fam.id,
        family_name=fam.family_name,
        invite_code=fam.invite_code,
        valid=valid,
        expires_at=_dt(),
    )


def _family_invite(
    *,
    iid=None,
    fid=None,
    role=FamilyRole.MEMBER,
    invited_by=None,
    phone: str | None = None,
    user_id=None,
) -> FamilyInvite:
    return FamilyInvite(
        id=iid or uuid4(),
        family_id=fid or uuid4(),
        role=role,
        status=FamilyInviteStatus.PENDING,
        invited_by=invited_by or uuid4(),
        invited_at=_dt(),
        phone_number=phone,
        user_id=user_id,
    )


def _mem(mid=None, fid=None, pid=None, role=FamilyRole.MEMBER, uid=None, relation_role=None) -> FamilyMembership:
    return FamilyMembership(
        id=mid or uuid4(),
        family_id=fid or uuid4(),
        profile_id=pid or uuid4(),
        role=role,
        added_by=uid or uuid4(),
        created_at=_dt(),
        relation_role=relation_role,
    )


def _user_entity(uid=None, phone_number: str | None = None) -> User:
    return User(
        id=uid or uuid4(),
        email="x@test.local",
        status=UserStatus.active,
        created_at=_dt(),
        password_hash="h",
        phone_number=phone_number,
    )


@pytest.fixture
def repo() -> AsyncMock:
    m = AsyncMock()
    m.get_family = AsyncMock(return_value=None)
    m.list_linked_profiles_for_user = AsyncMock(return_value=[])
    m.list_family_ids_for_profile = AsyncMock(return_value=[])
    m.claim_profile_to_user = AsyncMock(return_value=None)
    return m


@pytest.fixture
def users() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def access_port(repo: AsyncMock) -> AsyncMock:
    port = AsyncMock()
    # Luôn gọi qua `repo` hiện tại — không gán trực tiếp `repo.get_user_membership_in_family`
    # vì test sẽ thay thế thuộc tính đó; nếu gán một lần lúc fixture chạy thì port giữ mock cũ.
    async def _get_user_membership_in_family(family_id, user_id):
        return await repo.get_user_membership_in_family(family_id, user_id)

    port.get_user_membership_in_family = AsyncMock(side_effect=_get_user_membership_in_family)

    async def _family_exists(fid):
        fam = await repo.get_family(fid)
        return fam is not None

    port.family_exists = AsyncMock(side_effect=_family_exists)

    async def _get_membership_context(mid):
        mem = await repo.get_membership(mid)
        if mem is None:
            return None
        prof = await repo.get_profile(mem.profile_id)
        if prof is None:
            return None
        return MembershipAccessContext(
            membership=mem,
            owner_user_id=prof.owner_user_id,
            linked_user_id=prof.linked_user_id,
        )

    port.get_membership_context = AsyncMock(side_effect=_get_membership_context)
    port.list_user_memberships_for_families = AsyncMock(return_value=[])
    port.get_profile_context = AsyncMock(return_value=None)
    port.get_medicine_item_context = AsyncMock(return_value=None)
    port.get_medical_record_context = AsyncMock(return_value=None)
    port.get_attachment_context = AsyncMock(return_value=None)
    port.get_user_vaccination_context = AsyncMock(return_value=None)
    port.get_vaccination_dose_context = AsyncMock(return_value=None)
    return port


@pytest.fixture
def svc(repo: AsyncMock, users: AsyncMock, access_port: AsyncMock) -> FamiliesService:
    return FamiliesService(repo, users, AccessControlService(access_port))


@pytest.mark.asyncio
async def test_create_family_delegates(repo: AsyncMock, svc: FamiliesService) -> None:
    uid = uuid4()
    fam = _family()
    prof = _profile(owner=uid)
    mem = _mem(role=FamilyRole.OWNER)
    repo.create_family_with_owner_profile = AsyncMock(return_value=(fam, prof, mem))
    out = await svc.create_family(uid, CreateFamilyRequest(family_name="A", full_name="Me"))
    assert out[0] is fam
    repo.create_family_with_owner_profile.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_family_raises_when_family_missing(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid = uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(return_value=_mem(fid=fid, role=FamilyRole.MEMBER))
    repo.get_family = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError, match="Family not found"):
        await svc.get_family(fid, uid)


@pytest.mark.asyncio
async def test_patch_family_forbidden_for_member(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid = uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    with pytest.raises(ForbiddenError):
        await svc.patch_family(fid, uid, PatchFamilyRequest(family_name="X"))


@pytest.mark.asyncio
async def test_join_invalid_code(repo: AsyncMock, svc: FamiliesService) -> None:
    repo.preview_public_invite = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError, match="Invalid"):
        await svc.join_family(uuid4(), JoinFamilyRequest(invite_code="bad"))


@pytest.mark.asyncio
async def test_join_requires_full_name_when_no_profile(repo: AsyncMock, svc: FamiliesService) -> None:
    fam = _family()
    repo.preview_public_invite = AsyncMock(return_value=_invite_preview(fam))
    repo.list_linked_profiles_for_user = AsyncMock(return_value=[])
    with pytest.raises(ValueError, match="full_name"):
        await svc.join_family(uuid4(), JoinFamilyRequest(invite_code="ok", full_name=None))


@pytest.mark.asyncio
async def test_join_conflict_when_already_member(repo: AsyncMock, svc: FamiliesService) -> None:
    uid = uuid4()
    fam = _family()
    prof = _profile(owner=uid, linked=uid)
    repo.preview_public_invite = AsyncMock(return_value=_invite_preview(fam))
    repo.list_linked_profiles_for_user = AsyncMock(return_value=[prof])
    repo.has_membership = AsyncMock(return_value=True)
    with pytest.raises(ConflictError):
        await svc.join_family(uid, JoinFamilyRequest(invite_code="ok", full_name="x"))


@pytest.mark.asyncio
async def test_join_conflict_on_integrity(repo: AsyncMock, svc: FamiliesService) -> None:
    uid = uuid4()
    fam = _family()
    prof = _profile(owner=uid, linked=uid)
    repo.preview_public_invite = AsyncMock(return_value=_invite_preview(fam))
    repo.list_linked_profiles_for_user = AsyncMock(return_value=[prof])
    repo.has_membership = AsyncMock(return_value=False)
    repo.consume_pending_public_invite = AsyncMock(return_value=fam)
    repo.create_membership = AsyncMock(side_effect=IntegrityError("stmt", "params", Exception()))
    with pytest.raises(ConflictError):
        await svc.join_family(uid, JoinFamilyRequest(invite_code="ok", full_name="x"))


@pytest.mark.asyncio
async def test_join_requires_profile_id_when_user_has_multiple_profiles(repo: AsyncMock, svc: FamiliesService) -> None:
    uid = uuid4()
    fam = _family()
    repo.preview_public_invite = AsyncMock(return_value=_invite_preview(fam))
    repo.list_linked_profiles_for_user = AsyncMock(
        return_value=[
            _profile(owner=uid, linked=uid, name="A"),
            _profile(owner=uid, linked=uid, name="B"),
        ]
    )

    with pytest.raises(ConflictError, match="profile_id is required"):
        await svc.join_family(uid, JoinFamilyRequest(invite_code="ok"))


@pytest.mark.asyncio
async def test_join_uses_explicit_profile_id_when_user_has_multiple_profiles(repo: AsyncMock, svc: FamiliesService) -> None:
    uid = uuid4()
    fam = _family()
    prof_a = _profile(owner=uid, linked=uid, name="A")
    prof_b = _profile(owner=uid, linked=uid, name="B")
    membership = _mem(fid=fam.id, pid=prof_b.id, role=FamilyRole.MEMBER, uid=uid)
    repo.preview_public_invite = AsyncMock(return_value=_invite_preview(fam))
    repo.list_linked_profiles_for_user = AsyncMock(return_value=[prof_a, prof_b])
    repo.has_membership = AsyncMock(return_value=False)
    repo.consume_pending_public_invite = AsyncMock(return_value=fam)
    repo.create_membership = AsyncMock(return_value=membership)

    out = await svc.join_family(
        uid,
        JoinFamilyRequest(invite_code="ok", profile_id=prof_b.id),
    )

    assert out["profile_id"] == str(prof_b.id)
    repo.create_membership.assert_awaited_once()
    assert repo.create_membership.await_args.kwargs["profile_id"] == prof_b.id


@pytest.mark.asyncio
async def test_list_linkable_profiles_by_invite_returns_member_summaries(
    repo: AsyncMock,
    svc: FamiliesService,
) -> None:
    uid = uuid4()
    fam = _family(name="Linkable", code="invite-ok")
    owner_profile = _profile(
        owner=uuid4(),
        linked=None,
        name="Nguyen Van A",
        status="SHADOW",
        avatar_url="https://example.com/a.png",
    )
    linked_profile = _profile(
        owner=uuid4(),
        linked=uuid4(),
        name="Already Linked",
        status="ACTIVE",
    )
    pending_profile = _profile(
        owner=uuid4(),
        linked=None,
        name="Tran Thi B",
        status="PENDING_LINK",
        avatar_url=None,
    )
    repo.preview_public_invite = AsyncMock(return_value=_invite_preview(fam))
    repo.get_user_membership_in_family = AsyncMock(return_value=None)
    repo.get_family = AsyncMock(return_value=fam)
    repo.list_members_rows = AsyncMock(
        return_value=[
            (_mem(fid=fam.id, pid=owner_profile.id, role=FamilyRole.OWNER, relation_role="Cha"), owner_profile),
            (_mem(fid=fam.id, pid=linked_profile.id, role=FamilyRole.MEMBER, relation_role="Con"), linked_profile),
            (_mem(fid=fam.id, pid=pending_profile.id, role=FamilyRole.ADMIN, relation_role="Me"), pending_profile),
        ]
    )

    out = await svc.list_linkable_profiles_by_invite(uid, fam.invite_code)

    assert out["id"] == fam.id
    assert out["name"] == fam.family_name
    assert out["address"] == fam.address
    assert out["avatar_url"] == fam.avatar_url
    assert out["invite_code"] == fam.invite_code
    assert out["created_at"] == fam.created_at
    assert out["members"] == [
        {
            "id": owner_profile.id,
            "full_name": "Nguyen Van A",
            "role": FamilyRole.OWNER,
            "relation_role": "Cha",
            "avatar_url": "https://example.com/a.png",
        },
        {
            "id": pending_profile.id,
            "full_name": "Tran Thi B",
            "role": FamilyRole.ADMIN,
            "relation_role": "Me",
            "avatar_url": None,
        },
    ]


@pytest.mark.asyncio
async def test_invite_by_phone_forbidden_for_member(
    repo: AsyncMock,
    svc: FamiliesService,
) -> None:
    fid, uid = uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    with pytest.raises(ForbiddenError):
        await svc.invite_member_by_phone(
            fid,
            uid,
            InviteByPhoneRequest(phone_number="+15551234567", full_name="Invited"),
        )


@pytest.mark.asyncio
async def test_invite_by_phone_unknown_number_creates_invite_without_user_id(
    repo: AsyncMock,
    users: AsyncMock,
    svc: FamiliesService,
) -> None:
    fid, inviter = uuid4(), uuid4()
    fam = _family(fid=fid)
    invite = _family_invite(fid=fid, invited_by=inviter, phone="+15551234567", user_id=None)
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    repo.get_family = AsyncMock(return_value=fam)
    users.get_by_phone = AsyncMock(return_value=None)
    repo.find_pending_invite = AsyncMock(return_value=None)
    repo.create_family_invite = AsyncMock(return_value=invite)

    out = await svc.invite_member_by_phone(
        fid,
        inviter,
        InviteByPhoneRequest(phone_number="+15551234567", full_name="Invited"),
    )
    assert out["dry_run"] is False
    assert out["family"] is fam
    assert out["invite"] is invite
    repo.create_family_invite.assert_awaited()


@pytest.mark.asyncio
async def test_invite_by_phone_requires_full_name_when_no_personal_profile(
    repo: AsyncMock,
    users: AsyncMock,
    svc: FamiliesService,
) -> None:
    fid, inviter, invited = uuid4(), uuid4(), uuid4()
    async def _membership(family_id, user_id):
        if family_id == fid and user_id == inviter:
            return _mem(fid=fid, role=FamilyRole.OWNER)
        return None

    repo.get_user_membership_in_family = AsyncMock(side_effect=_membership)
    repo.get_family = AsyncMock(return_value=_family(fid=fid))
    users.get_by_phone = AsyncMock(return_value=_user_entity(invited, phone_number="+15551234567"))
    repo.find_personal_profile_for_user = AsyncMock(return_value=None)
    repo.find_pending_invite = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="full_name"):
        await svc.invite_member_by_phone(
            fid,
            inviter,
            InviteByPhoneRequest(phone_number="+15551234567", full_name=None),
        )


@pytest.mark.asyncio
async def test_invite_by_phone_conflict_when_already_member(
    repo: AsyncMock,
    users: AsyncMock,
    svc: FamiliesService,
) -> None:
    fid, inviter, invited, pid = uuid4(), uuid4(), uuid4(), uuid4()
    prof = _profile(pid=pid, owner=invited, linked=invited)
    async def _membership(family_id, user_id):
        if family_id == fid and user_id == inviter:
            return _mem(fid=fid, role=FamilyRole.ADMIN)
        if family_id == fid and user_id == invited:
            return _mem(fid=fid, pid=pid, role=FamilyRole.MEMBER)
        return None

    repo.get_user_membership_in_family = AsyncMock(side_effect=_membership)
    repo.get_family = AsyncMock(return_value=_family(fid=fid))
    users.get_by_phone = AsyncMock(return_value=_user_entity(invited, phone_number="+15551234567"))
    repo.find_personal_profile_for_user = AsyncMock(return_value=prof)
    repo.has_membership = AsyncMock(return_value=True)

    with pytest.raises(ConflictError):
        await svc.invite_member_by_phone(
            fid,
            inviter,
            InviteByPhoneRequest(phone_number="+15551234567", full_name="Invited"),
        )


@pytest.mark.asyncio
async def test_invite_by_phone_success(
    repo: AsyncMock,
    users: AsyncMock,
    svc: FamiliesService,
) -> None:
    fid, inviter, invited, pid = uuid4(), uuid4(), uuid4(), uuid4()
    fam = _family(fid=fid, name="Home")
    prof = _profile(pid=pid, owner=invited, linked=invited)

    async def _membership(family_id, user_id):
        if family_id == fid and user_id == inviter:
            return _mem(fid=fid, role=FamilyRole.OWNER)
        return None

    repo.get_user_membership_in_family = AsyncMock(side_effect=_membership)
    repo.get_family = AsyncMock(return_value=fam)
    users.get_by_phone = AsyncMock(return_value=_user_entity(invited, phone_number="+15551234567"))
    repo.find_personal_profile_for_user = AsyncMock(return_value=prof)
    repo.find_pending_invite = AsyncMock(return_value=None)
    invite = _family_invite(
        fid=fid,
        invited_by=inviter,
        phone="+15551234567",
        user_id=invited,
    )
    repo.create_family_invite = AsyncMock(return_value=invite)

    out = await svc.invite_member_by_phone(
        fid,
        inviter,
        InviteByPhoneRequest(phone_number="+15551234567", full_name="Invited"),
    )
    assert out["dry_run"] is False
    assert out["family"] is fam
    assert out["invite"] is invite


@pytest.mark.asyncio
async def test_rotate_forbidden_not_owner(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid = uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    with pytest.raises(ForbiddenError, match="OWNER"):
        await svc.rotate_invite(fid, uid)


@pytest.mark.asyncio
async def test_patch_membership_not_owner(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, mid, pid = uuid4(), uuid4(), uuid4(), uuid4()
    repo.get_membership = AsyncMock(return_value=_mem(mid=mid, fid=fid, pid=pid))
    repo.get_profile = AsyncMock(return_value=_profile(pid=pid))
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    with pytest.raises(ForbiddenError):
        await svc.patch_membership_role(
            mid,
            uid,
            PatchMembershipRoleRequest(role=FamilyRole.MEMBER),
        )


@pytest.mark.asyncio
async def test_create_profile_owner_not_found(repo: AsyncMock, users: AsyncMock, svc: FamiliesService) -> None:
    fid, uid = uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.OWNER),
    )
    users.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError, match="owner_user_id"):
        await svc.create_profile(
            fid,
            uid,
            CreateProfileInFamilyRequest(
                full_name="Kid",
                owner_user_id=uuid4(),
                role=FamilyRole.MEMBER,
            ),
        )


@pytest.mark.asyncio
async def test_link_profile_user_not_found(
    repo: AsyncMock,
    users: AsyncMock,
    svc: FamiliesService,
) -> None:
    fid, uid, pid, tid = uuid4(), uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.OWNER),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    users.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError, match="user_id"):
        await svc.link_profile(fid, pid, uid, tid)


@pytest.mark.asyncio
async def test_link_profile_integrity_conflict(repo: AsyncMock, users: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid, tid = uuid4(), uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.OWNER),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    users.get_by_id = AsyncMock(return_value=_user_entity(tid))
    repo.link_profile_to_user = AsyncMock(
        side_effect=IntegrityError("stmt", "params", Exception()),
    )
    with pytest.raises(ConflictError):
        await svc.link_profile(fid, pid, uid, tid)


@pytest.mark.asyncio
async def test_link_profile_returns_none_conflict(repo: AsyncMock, users: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid, tid = uuid4(), uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.OWNER),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    users.get_by_id = AsyncMock(return_value=_user_entity(tid))
    repo.link_profile_to_user = AsyncMock(return_value=None)
    with pytest.raises(ConflictError):
        await svc.link_profile(fid, pid, uid, tid)


@pytest.mark.asyncio
async def test_patch_health_member_forbidden(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    with pytest.raises(ForbiddenError):
        await svc.patch_health(
            fid,
            pid,
            uid,
            PatchHealthDetailRequest(notes="n"),
        )


@pytest.mark.asyncio
async def test_delete_membership_self(repo: AsyncMock, svc: FamiliesService) -> None:
    uid = uuid4()
    mid, fid, pid = uuid4(), uuid4(), uuid4()
    repo.get_membership = AsyncMock(return_value=_mem(mid=mid, fid=fid, pid=pid))
    repo.get_profile = AsyncMock(return_value=_profile(pid=pid, linked=uid))
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    repo.delete_membership = AsyncMock(return_value=True)
    await svc.delete_membership(mid, uid)
    repo.delete_membership.assert_awaited()


@pytest.mark.asyncio
async def test_delete_profile_soft_delete_fails(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.OWNER),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    repo.soft_delete_profile = AsyncMock(return_value=False)
    with pytest.raises(NotFoundError):
        await svc.delete_profile(fid, pid, uid)


@pytest.mark.asyncio
async def test_get_health_raises_profile_not_in_family(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    repo.profile_in_family = AsyncMock(return_value=False)
    with pytest.raises(NotFoundError):
        await svc.get_health(fid, pid, uid)


@pytest.mark.asyncio
async def test_list_profiles_delegates(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid = uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    repo.list_profiles_in_family = AsyncMock(return_value=[])
    out = await svc.list_profiles(fid, uid)
    assert out == []


@pytest.mark.asyncio
async def test_list_profiles_member_sees_full_family_list(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid_self, pid_other = uuid4(), uuid4(), uuid4(), uuid4()
    other = uuid4()
    mine = _profile(pid=pid_self, linked=uid)
    theirs = _profile(pid=pid_other, linked=other)
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    repo.list_profiles_in_family = AsyncMock(return_value=[mine, theirs])
    out = await svc.list_profiles(fid, uid)
    assert out == [mine, theirs]


@pytest.mark.asyncio
async def test_list_profiles_admin_sees_all(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid = uuid4(), uuid4()
    other = uuid4()
    a = _profile(linked=uid)
    b = _profile(linked=other)
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    repo.list_profiles_in_family = AsyncMock(return_value=[a, b])
    out = await svc.list_profiles(fid, uid)
    assert out == [a, b]


@pytest.mark.asyncio
async def test_list_my_linked_profiles_delegates(repo: AsyncMock, svc: FamiliesService) -> None:
    uid = uuid4()
    repo.list_linked_profiles_for_user = AsyncMock(return_value=[])
    assert await svc.list_my_linked_profiles(uid, "without_family") == []
    repo.list_linked_profiles_for_user.assert_awaited_once_with(uid, profile_scope="without_family")


@pytest.mark.asyncio
async def test_get_health_returns_none_from_repo(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    repo.get_profile = AsyncMock(return_value=_profile(pid=pid, linked=uid))
    repo.get_health = AsyncMock(return_value=None)
    assert await svc.get_health(fid, pid, uid) is None


@pytest.mark.asyncio
async def test_get_health_member_forbidden_other_profile(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid, other = uuid4(), uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    repo.get_profile = AsyncMock(return_value=_profile(pid=pid, linked=other))
    with pytest.raises(ForbiddenError):
        await svc.get_health(fid, pid, uid)


@pytest.mark.asyncio
async def test_get_health_admin_reads_any_profile(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid, other = uuid4(), uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    repo.get_health = AsyncMock(return_value=None)
    assert await svc.get_health(fid, pid, uid) is None
    repo.get_profile.assert_not_called()


@pytest.mark.asyncio
async def test_patch_health_ok(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    hd = HealthDetail(
        id=uuid4(),
        profile_id=pid,
        blood_type=None,
        chronic_diseases=None,
        allergies=None,
        notes=None,
        updated_at=_dt(),
        emergency_contacts=[],
    )
    repo.upsert_health = AsyncMock(return_value=hd)
    out = await svc.patch_health(
        fid,
        pid,
        uid,
        PatchHealthDetailRequest(notes="ok"),
    )
    assert out is hd


@pytest.mark.asyncio
async def test_membership_or_404_raises_forbidden_when_family_exists(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid = uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(return_value=None)
    repo.get_family = AsyncMock(return_value=_family(fid=fid))
    with pytest.raises(ForbiddenError, match="Not a member"):
        await svc.get_family(fid, uid)


@pytest.mark.asyncio
async def test_get_family_not_found_when_family_row_missing(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid = uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    repo.get_family = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError, match="Family not found"):
        await svc.get_family(fid, uid)


@pytest.mark.asyncio
async def test_list_my_families(repo: AsyncMock, svc: FamiliesService) -> None:
    uid = uuid4()
    fams = [_family()]
    repo.list_families_for_user = AsyncMock(return_value=fams)
    assert await svc.list_my_families(uid) is fams


@pytest.mark.asyncio
async def test_get_family_ok(repo: AsyncMock, svc: FamiliesService) -> None:
    uid = uuid4()
    fam = _family()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fam.id, role=FamilyRole.MEMBER),
    )
    repo.get_family = AsyncMock(return_value=fam)
    assert await svc.get_family(fam.id, uid) is fam


@pytest.mark.asyncio
async def test_patch_family_ok(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid = uuid4(), uuid4()
    updated = _family(fid=fid, name="New")
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    repo.update_family_name = AsyncMock(return_value=updated)
    out = await svc.patch_family(fid, uid, PatchFamilyRequest(family_name="New"))
    assert out is updated


@pytest.mark.asyncio
async def test_patch_family_not_found_after_update(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid = uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.OWNER),
    )
    repo.update_family_name = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError):
        await svc.patch_family(fid, uid, PatchFamilyRequest(family_name="X"))


@pytest.mark.asyncio
async def test_join_creates_personal_profile(repo: AsyncMock, svc: FamiliesService) -> None:
    uid = uuid4()
    fam = _family()
    new_prof = _profile(owner=uid, linked=uid, name="NewMe")
    mem = _mem(fid=fam.id, pid=new_prof.id, role=FamilyRole.MEMBER, uid=uid)
    repo.preview_public_invite = AsyncMock(return_value=_invite_preview(fam))
    repo.list_linked_profiles_for_user = AsyncMock(return_value=[])
    repo.create_personal_profile = AsyncMock(return_value=new_prof)
    repo.has_membership = AsyncMock(return_value=False)
    repo.consume_pending_public_invite = AsyncMock(return_value=fam)
    repo.create_membership = AsyncMock(return_value=mem)
    out = await svc.join_family(
        uid,
        JoinFamilyRequest(invite_code="ok", full_name="NewMe"),
    )
    assert out["mode"] == "invite_code"
    assert out["family_id"] == str(fam.id)
    assert out["profile_id"] == str(new_prof.id)
    repo.create_personal_profile.assert_awaited_once()


@pytest.mark.asyncio
async def test_rotate_invite_ok(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid = uuid4(), uuid4()
    fam = _family(fid=fid)
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.OWNER),
    )
    repo.rotate_invite = AsyncMock(return_value=fam)
    assert await svc.rotate_invite(fid, uid) is fam


@pytest.mark.asyncio
async def test_rotate_invite_family_missing(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid = uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.OWNER),
    )
    repo.rotate_invite = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError, match="Family not found"):
        await svc.rotate_invite(fid, uid)


@pytest.mark.asyncio
async def test_list_members_delegates(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid = uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    repo.list_members_rows = AsyncMock(return_value=[])
    assert await svc.list_members(fid, uid) == []


@pytest.mark.asyncio
async def test_patch_membership_ok(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, mid, pid = uuid4(), uuid4(), uuid4(), uuid4()
    updated = _mem(mid=mid, fid=fid, role=FamilyRole.ADMIN)
    repo.get_membership = AsyncMock(return_value=_mem(mid=mid, fid=fid, pid=pid))
    repo.get_profile = AsyncMock(return_value=_profile(pid=pid))
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.OWNER),
    )
    repo.update_membership_role = AsyncMock(return_value=updated)
    out = await svc.patch_membership_role(
        mid,
        uid,
        PatchMembershipRoleRequest(role=FamilyRole.ADMIN),
    )
    assert out is updated


@pytest.mark.asyncio
async def test_patch_membership_not_found_wrong_family(repo: AsyncMock, svc: FamiliesService) -> None:
    repo.get_membership = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError, match="Membership not found"):
        await svc.patch_membership_role(
            uuid4(),
            uuid4(),
            PatchMembershipRoleRequest(role=FamilyRole.MEMBER),
        )


@pytest.mark.asyncio
async def test_patch_membership_update_returns_none(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, mid, pid = uuid4(), uuid4(), uuid4(), uuid4()
    repo.get_membership = AsyncMock(return_value=_mem(mid=mid, fid=fid, pid=pid))
    repo.get_profile = AsyncMock(return_value=_profile(pid=pid))
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.OWNER),
    )
    repo.update_membership_role = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError):
        await svc.patch_membership_role(
            mid,
            uid,
            PatchMembershipRoleRequest(role=FamilyRole.MEMBER),
        )


@pytest.mark.asyncio
async def test_delete_membership_not_in_family(repo: AsyncMock, svc: FamiliesService) -> None:
    repo.get_membership = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError):
        await svc.delete_membership(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_delete_membership_target_missing(repo: AsyncMock, svc: FamiliesService) -> None:
    mid = uuid4()
    repo.get_membership = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError):
        await svc.delete_membership(mid, uuid4())


@pytest.mark.asyncio
async def test_delete_membership_admin_removes_other(repo: AsyncMock, svc: FamiliesService) -> None:
    uid, other_uid = uuid4(), uuid4()
    mid, fid, pid = uuid4(), uuid4(), uuid4()
    repo.get_membership = AsyncMock(return_value=_mem(mid=mid, fid=fid, pid=pid))
    repo.get_profile = AsyncMock(return_value=_profile(pid=pid, linked=other_uid))
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    repo.delete_membership = AsyncMock(return_value=True)
    await svc.delete_membership(mid, uid)
    repo.delete_membership.assert_awaited()


@pytest.mark.asyncio
async def test_delete_membership_forbidden_non_admin_non_self(repo: AsyncMock, svc: FamiliesService) -> None:
    uid, other_uid = uuid4(), uuid4()
    mid, fid, pid = uuid4(), uuid4(), uuid4()
    repo.get_membership = AsyncMock(return_value=_mem(mid=mid, fid=fid, pid=pid))
    repo.get_profile = AsyncMock(return_value=_profile(pid=pid, linked=other_uid))
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    with pytest.raises(ForbiddenError):
        await svc.delete_membership(mid, uid)


@pytest.mark.asyncio
async def test_create_profile_delegates(repo: AsyncMock, users: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, owner_id = uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    users.get_by_id = AsyncMock(return_value=_user_entity(owner_id))
    prof = _profile(owner=owner_id)
    mem = _mem()
    repo.create_profile_in_family = AsyncMock(return_value=(prof, mem))
    out = await svc.create_profile(
        fid,
        uid,
        CreateProfileInFamilyRequest(
            full_name="Kid",
            owner_user_id=owner_id,
            role=FamilyRole.MEMBER,
        ),
    )
    assert out == (prof, mem)


@pytest.mark.asyncio
async def test_create_profile_forbidden_member(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid = uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    with pytest.raises(ForbiddenError):
        await svc.create_profile(
            fid,
            uid,
            CreateProfileInFamilyRequest(
                full_name="Kid",
                owner_user_id=uuid4(),
                role=FamilyRole.MEMBER,
            ),
        )


@pytest.mark.asyncio
async def test_get_profile_ok(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    p = _profile(pid=pid, linked=uid)
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    repo.get_profile = AsyncMock(return_value=p)
    assert await svc.get_profile(fid, pid, uid) is p


@pytest.mark.asyncio
async def test_get_profile_member_forbidden_not_self(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid, other = uuid4(), uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    repo.get_profile = AsyncMock(return_value=_profile(pid=pid, linked=other))
    with pytest.raises(ForbiddenError):
        await svc.get_profile(fid, pid, uid)


@pytest.mark.asyncio
async def test_get_profile_repo_returns_none(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    repo.get_profile = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError):
        await svc.get_profile(fid, pid, uid)


@pytest.mark.asyncio
async def test_patch_profile_ok(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    p = _profile(pid=pid)
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.OWNER),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    repo.patch_profile = AsyncMock(return_value=p)
    out = await svc.patch_profile(
        fid,
        pid,
        uid,
        PatchProfileRequest(full_name="Z"),
    )
    assert out is p


@pytest.mark.asyncio
async def test_patch_profile_forbidden(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid, other = uuid4(), uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    repo.get_profile = AsyncMock(return_value=_profile(pid=pid, linked=other))
    with pytest.raises(ForbiddenError):
        await svc.patch_profile(fid, pid, uid, PatchProfileRequest(full_name="Z"))


@pytest.mark.asyncio
async def test_patch_profile_member_unlinked_profile_forbidden(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    repo.get_profile = AsyncMock(return_value=_profile(pid=pid, linked=None))
    with pytest.raises(ForbiddenError):
        await svc.patch_profile(fid, pid, uid, PatchProfileRequest(full_name="Z"))


@pytest.mark.asyncio
async def test_patch_profile_admin_edits_self_linked_profile_ok(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    p = _profile(pid=pid, linked=uid)
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    repo.get_profile = AsyncMock(return_value=_profile(pid=pid, linked=uid))
    repo.patch_profile = AsyncMock(return_value=p)
    out = await svc.patch_profile(fid, pid, uid, PatchProfileRequest(full_name="Me"))
    assert out is p


@pytest.mark.asyncio
async def test_patch_profile_not_in_family(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    repo.profile_in_family = AsyncMock(return_value=False)
    with pytest.raises(NotFoundError):
        await svc.patch_profile(fid, pid, uid, PatchProfileRequest(full_name="Z"))


@pytest.mark.asyncio
async def test_patch_profile_repo_none(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    repo.patch_profile = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError):
        await svc.patch_profile(fid, pid, uid, PatchProfileRequest(full_name="Z"))


@pytest.mark.asyncio
async def test_patch_profile_admin_self_linked_repo_none(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    repo.get_profile = AsyncMock(return_value=_profile(pid=pid, linked=uid))
    repo.patch_profile = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError):
        await svc.patch_profile(fid, pid, uid, PatchProfileRequest(full_name="Z"))


@pytest.mark.asyncio
async def test_delete_profile_ok(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    repo.soft_delete_profile = AsyncMock(return_value=True)
    await svc.delete_profile(fid, pid, uid)


@pytest.mark.asyncio
async def test_link_profile_ok(repo: AsyncMock, users: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid, tid = uuid4(), uuid4(), uuid4(), uuid4()
    p = _profile(pid=pid)
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    repo.profile_in_family = AsyncMock(return_value=True)
    users.get_by_id = AsyncMock(return_value=_user_entity(tid))
    repo.link_profile_to_user = AsyncMock(return_value=p)
    assert await svc.link_profile(fid, pid, uid, tid) is p


@pytest.mark.asyncio
async def test_link_profile_forbidden(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid, tid = uuid4(), uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.MEMBER),
    )
    with pytest.raises(ForbiddenError):
        await svc.link_profile(fid, pid, uid, tid)


@pytest.mark.asyncio
async def test_link_profile_not_in_family(repo: AsyncMock, users: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid, tid = uuid4(), uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    repo.profile_in_family = AsyncMock(return_value=False)
    users.get_by_id = AsyncMock(return_value=_user_entity(tid))
    with pytest.raises(NotFoundError):
        await svc.link_profile(fid, pid, uid, tid)


@pytest.mark.asyncio
async def test_patch_health_profile_not_in_family(repo: AsyncMock, svc: FamiliesService) -> None:
    fid, uid, pid = uuid4(), uuid4(), uuid4()
    repo.get_user_membership_in_family = AsyncMock(
        return_value=_mem(fid=fid, role=FamilyRole.ADMIN),
    )
    repo.profile_in_family = AsyncMock(return_value=False)
    with pytest.raises(NotFoundError):
        await svc.patch_health(
            fid,
            pid,
            uid,
            PatchHealthDetailRequest(notes="n"),
        )

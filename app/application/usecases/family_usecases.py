from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.config import settings as app_settings

from app.application.dtos.family_dto import (
    CreateFamilyRequest,
    CreatePersonalProfileRequest,
    CreateProfileInFamilyRequest,
    CreateProxyHealthPayload,
    FamilyInviteListRequest,
    InviteByPhoneRequest,
    JoinFamilyRequest,
    LinkInviteProfileRequest,
    PatchFamilyRequest,
    PatchHealthDetailRequest,
    PatchMembershipRoleRequest,
    PatchProfileRequest,
)
from app.application.family_errors import ConflictError, ForbiddenError, GoneError, NotFoundError
from app.application.ports.family_port import FamilyRepositoryPort
from app.application.ports.user_port import UserRepositoryPort
from app.application.usecases.access_control_usecases import AccessControlService
from app.domain.entities.family import (
    Family,
    FamilyInvite,
    FamilyInviteInboxItem,
    FamilyInviteStatus,
    FamilyMembership,
    FamilyRole,
    PublicInvitePreview,
)
from app.domain.entities.health_detail import EmergencyContactEntry, HealthDetail
from app.domain.entities.profile import Profile, ProfileStatus
from app.domain.services.family_permission import has_at_least


def _utc_now():
    return datetime.now(timezone.utc)


def _emergency_contacts_from_patch(body: PatchHealthDetailRequest) -> list[EmergencyContactEntry] | None:
    if "emergency_contacts" not in body.model_fields_set:
        return None
    raw = body.emergency_contacts
    if raw is None:
        return []
    return [
        EmergencyContactEntry(name=x.name, phone=x.phone, relationship=x.relationship) for x in raw
    ]


def _emergency_contacts_from_proxy_payload(hp: CreateProxyHealthPayload) -> list[EmergencyContactEntry] | None:
    if "emergency_contacts" not in hp.model_fields_set:
        return None
    raw = hp.emergency_contacts
    if raw is None:
        return []
    return [
        EmergencyContactEntry(name=x.name, phone=x.phone, relationship=x.relationship) for x in raw
    ]


def _is_unique_violation(exc: IntegrityError) -> bool:
    orig = getattr(exc, "orig", None)
    code = getattr(orig, "pgcode", None)
    if code is not None:
        return str(code) == "23505"
    return "unique" in str(exc).lower()


class FamiliesService:
    """Application service for families / profiles / health (feature 002)."""

    def __init__(
        self,
        repo: FamilyRepositoryPort,
        users: UserRepositoryPort,
        access: AccessControlService,
    ) -> None:
        self._repo = repo
        self._users = users
        self._access = access

    async def _membership_or_404(self, family_id: UUID, user_id: UUID) -> FamilyMembership:
        return await self._access.require_family_member(family_id, user_id)

    @staticmethod
    def _sort_profiles_for_default(profiles: list[Profile]) -> list[Profile]:
        return sorted(
            profiles,
            key=lambda profile: (profile.updated_at, profile.created_at, str(profile.id)),
            reverse=True,
        )

    async def _resolve_join_profile(
        self,
        user_id: UUID,
        *,
        profile_id: UUID | None,
        full_name: str | None,
    ) -> Profile:
        linked_profiles = self._sort_profiles_for_default(
            await self._repo.list_linked_profiles_for_user(user_id, profile_scope="all")
        )
        if profile_id is not None:
            selected = next((profile for profile in linked_profiles if profile.id == profile_id), None)
            if selected is None:
                raise ForbiddenError("profile_id does not belong to current user")
            return selected
        if len(linked_profiles) == 1:
            return linked_profiles[0]
        if len(linked_profiles) > 1:
            raise ConflictError("Multiple linked profiles found; profile_id is required")
        if not full_name or not full_name.strip():
            raise ValueError("full_name is required when you have no linked profile yet")
        return await self._repo.create_personal_profile(
            user_id=user_id,
            full_name=full_name.strip(),
        )

    async def create_family(
        self,
        user_id: UUID,
        body: CreateFamilyRequest,
    ) -> tuple[Family, Profile, FamilyMembership]:
        exp = _utc_now() + timedelta(seconds=app_settings.family_public_invite_ttl_seconds)
        return await self._repo.create_family_with_owner_profile(
            family_name=body.name,
            address=body.address,
            avatar_url=body.avatar_url,
            creator_user_id=user_id,
            creator_full_name=body.owner_profile_full_name,
            public_invite_expires_at=exp,
        )

    async def list_my_families(self, user_id: UUID) -> list[Family]:
        return await self._repo.list_families_for_user(user_id)

    async def get_family(self, family_id: UUID, user_id: UUID) -> Family:
        await self._membership_or_404(family_id, user_id)
        fam = await self._repo.get_family(family_id)
        if fam is None:
            raise NotFoundError("Family not found")
        return fam

    async def get_family_invites(self, family_id: UUID, user_id: UUID) -> list[FamilyInvite]:
        actor = await self._access.require_family_member(family_id, user_id)
        if not has_at_least(actor.role, FamilyRole.ADMIN):
            return []
        return await self._repo.list_family_invites(family_id)

    async def patch_family(
        self,
        family_id: UUID,
        user_id: UUID,
        body: PatchFamilyRequest,
    ) -> Family:
        m = await self._access.require_family_admin(family_id, user_id)
        if not has_at_least(m.role, FamilyRole.ADMIN):
            raise ForbiddenError("OWNER or ADMIN required")
        fam = await self._repo.update_family_name(family_id, body.name)
        if fam is None:
            raise NotFoundError("Family not found")
        return fam

    async def join_family(self, user_id: UUID, body: JoinFamilyRequest) -> dict:
        if body.invite_code:
            code = body.invite_code.strip()
            snap = await self._repo.preview_public_invite(code)
            if snap is None:
                raise NotFoundError("Invalid or expired invite code")
            prof = await self._resolve_join_profile(
                user_id,
                profile_id=body.profile_id,
                full_name=body.full_name,
            )
            if await self._repo.has_membership(snap.family_id, prof.id):
                raise ConflictError("Already a member of this family")
            fam = await self._repo.consume_pending_public_invite(code, user_id)
            if fam is None:
                if await self._repo.has_membership(snap.family_id, prof.id):
                    raise ConflictError("Already a member of this family")
                raise NotFoundError("Invalid or expired invite code")
            if fam.id != snap.family_id:
                raise NotFoundError("Invalid or expired invite code")
            try:
                membership = await self._repo.create_membership(
                    family_id=fam.id,
                    profile_id=prof.id,
                    role=FamilyRole.MEMBER,
                    relation_role=None,
                    added_by=user_id,
                )
            except IntegrityError as e:
                raise ConflictError("Already a member of this family") from e
            return {
                "mode": "invite_code",
                "family_id": str(fam.id),
                "family_name": fam.family_name,
                "profile_id": str(prof.id),
                "membership_id": str(membership.id),
                "message": "Joined family",
            }

        if body.invite_id is None or body.action is None:
            raise ValueError("Either invite_code or (action + invite_id) is required")

        invite = await self._repo.get_family_invite(body.invite_id)
        if invite is None:
            raise NotFoundError("Invite not found")
        if invite.status != FamilyInviteStatus.PENDING:
            raise ConflictError("Invite has already been responded")

        me = await self._users.get_by_id(user_id)
        if me is None:
            raise NotFoundError("User not found")

        matched = invite.user_id == user_id
        if not matched and invite.phone_number and me.phone_number:
            matched = invite.phone_number.strip() == me.phone_number.strip()
        if not matched:
            raise ForbiddenError("This invite does not belong to current user")

        if body.action == "reject":
            updated = await self._repo.update_family_invite_status(invite.id, FamilyInviteStatus.REJECTED)
            if updated is None:
                raise NotFoundError("Invite not found")
            return {
                "mode": "invite_action",
                "success": True,
                "invite_id": str(updated.id),
                "status": updated.status.value.lower(),
            }

        if invite.role == FamilyRole.OWNER:
            raise ForbiddenError("Ownership transfer must be done via membership role transfer")

        profile = await self._resolve_join_profile(
            user_id,
            profile_id=body.profile_id,
            full_name=body.full_name,
        )
        if await self._repo.has_membership(invite.family_id, profile.id):
            raise ConflictError("Already a member of this family")
        try:
            membership = await self._repo.create_membership(
                family_id=invite.family_id,
                profile_id=profile.id,
                role=invite.role,
                relation_role=invite.relation_role,
                added_by=invite.invited_by,
            )
        except IntegrityError as e:
            raise ConflictError("Already a member of this family") from e

        updated = await self._repo.update_family_invite_status(invite.id, FamilyInviteStatus.ACCEPTED)
        if updated is None:
            raise NotFoundError("Invite not found")
        return {
            "mode": "invite_action",
            "success": True,
            "invite_id": str(updated.id),
            "status": updated.status.value.lower(),
            "family_member_id": str(membership.id),
        }

    async def invite_member_by_phone(
        self,
        family_id: UUID,
        inviter_user_id: UUID,
        body: InviteByPhoneRequest,
    ) -> dict:
        actor = await self._access.require_family_admin(family_id, inviter_user_id)
        if not has_at_least(actor.role, FamilyRole.ADMIN):
            raise ForbiddenError("OWNER or ADMIN required")
        if body.role == FamilyRole.OWNER:
            raise ForbiddenError("Only current OWNER can assign OWNER via ownership transfer")

        fam = await self._repo.get_family(family_id)
        if fam is None:
            raise NotFoundError("Family not found")

        user = await self._users.get_by_phone(body.phone_number)
        if body.dry_run:
            if user is None:
                return {
                    "dry_run": True,
                    "found": False,
                    "user": None,
                }
            profile = await self._repo.find_personal_profile_for_user(user.id)
            return {
                "dry_run": True,
                "found": True,
                "user": {
                    "id": user.id,
                    "full_name": profile.full_name if profile else None,
                    "phone_number": user.phone_number,
                    "avatar_url": profile.avatar_url if profile else None,
                    "has_account": True,
                },
            }

        target_user_id = user.id if user is not None else body.user_id
        if user is not None:
            existing_profile = await self._repo.find_personal_profile_for_user(user.id)
            if await self._repo.get_user_membership_in_family(fam.id, user.id) is not None:
                raise ConflictError("User is already a member of this family")
            if existing_profile is None and (not body.full_name or not str(body.full_name).strip()):
                raise ValueError("full_name is required when you have no personal profile yet")

        pending = await self._repo.find_pending_invite(
            family_id=fam.id,
            user_id=target_user_id,
            phone_number=body.phone_number,
        )
        if pending is not None:
            raise ConflictError("Pending invite already exists for this target")

        try:
            invite = await self._repo.create_family_invite(
                family_id=fam.id,
                user_id=target_user_id,
                phone_number=body.phone_number,
                role=body.role,
                relation_role=body.relation_role,
                invited_by=inviter_user_id,
            )
        except IntegrityError as e:
            if _is_unique_violation(e):
                raise ConflictError("Pending invite already exists for this target") from e
            raise
        return {
            "dry_run": False,
            "invite": invite,
            "family": fam,
        }

    async def rotate_invite(self, family_id: UUID, user_id: UUID) -> Family:
        m = await self._access.require_family_member(family_id, user_id)
        if m.role != FamilyRole.OWNER:
            raise ForbiddenError("Only OWNER can rotate invite code")
        exp = _utc_now() + timedelta(seconds=app_settings.family_public_invite_ttl_seconds)
        fam = await self._repo.rotate_invite(
            family_id,
            public_invite_expires_at=exp,
            rotated_by=user_id,
        )
        if fam is None:
            raise NotFoundError("Family not found")
        return fam

    async def list_members(
        self,
        family_id: UUID,
        user_id: UUID,
    ) -> list[tuple[FamilyMembership, Profile]]:
        await self._access.require_family_member(family_id, user_id)
        return await self._repo.list_members_rows(family_id)

    async def list_member_details(
        self,
        family_id: UUID,
        user_id: UUID,
    ) -> list[tuple[FamilyMembership, Profile, HealthDetail | None]]:
        rows = await self.list_members(family_id, user_id)
        health_map = await self._repo.list_health_for_profiles([p.id for _, p in rows])
        return [(m, p, health_map.get(p.id)) for m, p in rows]

    async def list_invites_for_user(
        self,
        user_id: UUID,
        query: FamilyInviteListRequest,
    ) -> list[FamilyInviteInboxItem]:
        status = FamilyInviteStatus(query.status.upper()) if query.status else None
        offset = max(query.page - 1, 0) * query.limit
        return await self._repo.list_invites_for_user_with_context(
            user_id=user_id,
            status=status,
            offset=offset,
            limit=query.limit,
        )

    async def patch_membership_role(
        self,
        membership_id: UUID,
        user_id: UUID,
        body: PatchMembershipRoleRequest,
    ) -> FamilyMembership:
        context = await self._access.require_membership_role_edit(membership_id, user_id)
        if body.role == FamilyRole.OWNER:
            updated = await self._repo.transfer_family_owner(
                family_id=context.membership.family_id,
                new_owner_membership_id=membership_id,
                changed_by=user_id,
            )
            if updated is None:
                raise NotFoundError("Membership not found")
            return updated

        if context.membership.role == FamilyRole.OWNER:
            raise ForbiddenError("Current OWNER cannot be demoted directly; transfer ownership first")

        updated = await self._repo.update_membership_role(membership_id, body.role)
        if updated is None:
            raise NotFoundError("Membership not found")
        return updated

    async def delete_membership(
        self,
        membership_id: UUID,
        user_id: UUID,
    ) -> None:
        await self._access.require_membership_delete(membership_id, user_id)
        await self._repo.delete_membership(membership_id)

    async def create_profile(
        self,
        family_id: UUID,
        user_id: UUID,
        body: CreateProfileInFamilyRequest,
    ) -> tuple[Profile, FamilyMembership]:
        m = await self._access.require_family_admin(family_id, user_id)
        if not has_at_least(m.role, FamilyRole.ADMIN):
            raise ForbiddenError("OWNER or ADMIN required")
        if body.role == FamilyRole.OWNER:
            raise ForbiddenError("Only current OWNER can assign OWNER via ownership transfer")
        owner_user_id = body.owner_user_id or user_id
        owner = await self._users.get_by_id(owner_user_id)
        if owner is None:
            raise NotFoundError("owner_user_id not found")
        profile_full_name = body.full_name
        dob = body.dob
        gender = body.gender
        height_cm = None
        weight_kg = None
        address = None
        avatar_url = None
        if body.profile is not None:
            profile_full_name = body.profile.full_name
            dob = body.profile.date_of_birth
            gender = body.profile.gender
            height_cm = body.profile.height_cm
            weight_kg = body.profile.weight_kg
            address = body.profile.address
            avatar_url = body.profile.avatar_url

        prof, membership = await self._repo.create_profile_in_family(
            family_id=family_id,
            owner_user_id=owner_user_id,
            full_name=profile_full_name,
            role=body.role,
            relation_role=body.relation_role,
            added_by=user_id,
            dob=dob,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            address=address,
            avatar_url=avatar_url,
            linked_user_id=None,
        )
        if body.health_profile is not None:
            hp = body.health_profile
            await self._repo.upsert_health(
                prof.id,
                blood_type=hp.blood_type,
                chronic_diseases=hp.chronic_conditions,
                allergies=hp.allergies,
                drug_allergies=hp.drug_allergies,
                food_allergies=hp.food_allergies,
                emergency_contacts=_emergency_contacts_from_proxy_payload(hp),
            )
        return prof, membership

    async def list_profiles(self, family_id: UUID, user_id: UUID) -> list[Profile]:
        await self._access.require_family_member(family_id, user_id)
        return await self._repo.list_profiles_in_family(family_id)

    async def list_my_linked_profiles(
        self,
        user_id: UUID,
        profile_scope: Literal["all", "without_family", "with_family"] = "all",
    ) -> list[Profile]:
        return self._sort_profiles_for_default(
            await self._repo.list_linked_profiles_for_user(
                user_id,
                profile_scope=profile_scope,
            )
        )

    async def get_personal_profile_for_user(self, user_id: UUID) -> Profile | None:
        """Profile cá nhân (linked_user_id = user), nếu đã tạo."""
        profiles = await self.list_my_linked_profiles(user_id, profile_scope="all")
        return profiles[0] if profiles else None

    async def list_family_ids_for_profile(self, profile_id: UUID) -> list[UUID]:
        return await self._repo.list_family_ids_for_profile(profile_id)

    async def create_my_personal_profile(self, user_id: UUID, body: CreatePersonalProfileRequest) -> Profile:
        return await self._repo.create_personal_profile(
            user_id=user_id,
            full_name=body.full_name,
            dob=body.dob,
            gender=body.gender,
            height_cm=body.height_cm,
            weight_kg=body.weight_kg,
            address=body.address,
            avatar_url=body.avatar_url,
        )

    async def preview_invite(self, invite_code: str) -> PublicInvitePreview:
        prev = await self._repo.preview_public_invite(invite_code)
        if prev is None:
            raise NotFoundError("Invalid or expired invite code")
        return prev

    async def list_linkable_profiles_by_invite(self, user_id: UUID, invite_code: str) -> dict:
        code = invite_code.strip()
        prev = await self._repo.preview_public_invite(code)
        if prev is None:
            raise NotFoundError("Invite code not found")
        if not prev.valid:
            raise GoneError("Invite code has expired or is no longer active")

        if await self._repo.get_user_membership_in_family(prev.family_id, user_id) is not None:
            raise ConflictError("Already a member of this family")

        family = await self._repo.get_family(prev.family_id)
        if family is None:
            raise NotFoundError("Family not found")

        rows = await self._repo.list_members_rows(prev.family_id)
        candidate_members = [
            (membership, profile)
            for membership, profile in rows
            if profile.linked_user_id is None
            and profile.status in {ProfileStatus.SHADOW.value, ProfileStatus.PENDING_LINK.value}
        ]

        return {
            "id": family.id,
            "name": family.family_name,
            "address": family.address,
            "avatar_url": family.avatar_url,
            "invite_code": family.invite_code,
            "created_at": family.created_at,
            "members": [
                {
                    "id": profile.id,
                    "full_name": profile.full_name,
                    "role": membership.role,
                    "relation_role": membership.relation_role,
                    "avatar_url": profile.avatar_url,
                }
                for membership, profile in candidate_members
            ],
        }

    async def link_profile_by_invite(self, user_id: UUID, body: LinkInviteProfileRequest) -> dict:
        code = body.invite_code.strip()
        prev = await self._repo.preview_public_invite(code)
        if prev is None:
            raise NotFoundError("Invite code not found")
        if not prev.valid:
            raise GoneError("Invite code has expired or is no longer active")

        if await self._repo.get_user_membership_in_family(prev.family_id, user_id) is not None:
            raise ConflictError("Already a member of this family")

        if not await self._repo.profile_in_family(body.profile_id, prev.family_id):
            raise ConflictError("Profile does not belong to invite family")

        profile = await self._repo.get_profile(body.profile_id)
        if profile is None:
            raise NotFoundError("Profile not found")
        if profile.linked_user_id is not None:
            raise ConflictError("Profile has already been linked")
        if profile.status not in {ProfileStatus.SHADOW.value, ProfileStatus.PENDING_LINK.value}:
            raise ConflictError("Profile is not claimable")

        fam = await self._repo.consume_pending_public_invite(code, user_id)
        if fam is None:
            raise GoneError("Invite code has expired or is no longer active")

        linked = await self._repo.claim_profile_to_user(body.profile_id, user_id)
        if linked is None:
            raise ConflictError("Profile has already been linked")

        membership_created = False
        if not await self._repo.has_membership(fam.id, body.profile_id):
            try:
                await self._repo.create_membership(
                    family_id=fam.id,
                    profile_id=body.profile_id,
                    role=FamilyRole.MEMBER,
                    relation_role=None,
                    added_by=user_id,
                )
                membership_created = True
            except IntegrityError:
                membership_created = False

        health = await self._repo.get_health(body.profile_id)
        return {
            "success": True,
            "family_id": fam.id,
            "profile_id": body.profile_id,
            "health_profile_id": health.profile_id if health else None,
            "linked_user_id": user_id,
            "membership_created": membership_created,
            "post_login_flow_completed": True,
        }

    async def get_profile(self, family_id: UUID, profile_id: UUID, user_id: UUID) -> Profile:
        m = await self._membership_or_404(family_id, user_id)
        if not await self._repo.profile_in_family(profile_id, family_id):
            raise NotFoundError("Profile not found")
        p = await self._repo.get_profile(profile_id)
        if p is None:
            raise NotFoundError("Profile not found")
        if not has_at_least(m.role, FamilyRole.ADMIN):
            if p.linked_user_id != user_id:
                raise ForbiddenError("Not allowed to view this profile")
        return p

    async def patch_profile(
        self,
        family_id: UUID,
        profile_id: UUID,
        user_id: UUID,
        body: PatchProfileRequest,
    ) -> Profile:
        m = await self._access.require_family_admin(family_id, user_id)
        if not has_at_least(m.role, FamilyRole.ADMIN):
            raise ForbiddenError("OWNER or ADMIN required")
        m = await self._membership_or_404(family_id, user_id)
        if not await self._repo.profile_in_family(profile_id, family_id):
            raise NotFoundError("Profile not found")
        if not has_at_least(m.role, FamilyRole.ADMIN):
            prof = await self._repo.get_profile(profile_id)
            if prof is None:
                raise NotFoundError("Profile not found")
            if prof.linked_user_id != user_id:
                raise ForbiddenError("OWNER or ADMIN required")
        p = await self._repo.patch_profile(
            profile_id,
            full_name=body.full_name,
            dob=body.dob,
            gender=body.gender,
            height_cm=body.height_cm,
            weight_kg=body.weight_kg,
            address=body.address,
            avatar_url=body.avatar_url,
            status=body.status.value if body.status is not None else None,
        )
        if p is None:
            raise NotFoundError("Profile not found")
        return p

    async def delete_profile(self, family_id: UUID, profile_id: UUID, user_id: UUID) -> None:
        m = await self._access.require_family_admin(family_id, user_id)
        if not has_at_least(m.role, FamilyRole.ADMIN):
            raise ForbiddenError("OWNER or ADMIN required")
        if not await self._repo.profile_in_family(profile_id, family_id):
            raise NotFoundError("Profile not found")
        ok = await self._repo.soft_delete_profile(profile_id)
        if not ok:
            raise NotFoundError("Profile not found")

    async def link_profile(
        self,
        family_id: UUID,
        profile_id: UUID,
        user_id: UUID,
        target_user_id: UUID,
    ) -> Profile:
        m = await self._access.require_family_admin(family_id, user_id)
        if not has_at_least(m.role, FamilyRole.ADMIN):
            raise ForbiddenError("OWNER or ADMIN required")
        if not await self._repo.profile_in_family(profile_id, family_id):
            raise NotFoundError("Profile not found")
        target_user = await self._users.get_by_id(target_user_id)
        if target_user is None:
            raise NotFoundError("user_id not found")
        try:
            p = await self._repo.link_profile_to_user(profile_id, target_user_id)
        except IntegrityError as e:
            raise ConflictError("Profile already linked or not found") from e
        if p is None:
            raise ConflictError("Profile already linked or not found")
        return p

    async def get_health(
        self,
        family_id: UUID,
        profile_id: UUID,
        user_id: UUID,
    ) -> HealthDetail | None:
        await self._access.require_family_member(family_id, user_id)
        m = await self._membership_or_404(family_id, user_id)
        if not await self._repo.profile_in_family(profile_id, family_id):
            raise NotFoundError("Profile not found")
        if not has_at_least(m.role, FamilyRole.ADMIN):
            p = await self._repo.get_profile(profile_id)
            if p is None:
                raise NotFoundError("Profile not found")
            if p.linked_user_id != user_id:
                raise ForbiddenError("Not allowed to view this profile's health details")
        return await self._repo.get_health(profile_id)

    async def patch_health(
        self,
        family_id: UUID,
        profile_id: UUID,
        user_id: UUID,
        body: PatchHealthDetailRequest,
    ) -> HealthDetail:
        m = await self._access.require_family_admin(family_id, user_id)
        if not has_at_least(m.role, FamilyRole.ADMIN):
            raise ForbiddenError("OWNER or ADMIN required to edit health details")
        if not await self._repo.profile_in_family(profile_id, family_id):
            raise NotFoundError("Profile not found")
        return await self._repo.upsert_health(
            profile_id,
            blood_type=body.blood_type,
            chronic_diseases=body.chronic_diseases,
            allergies=body.allergies,
            drug_allergies=body.drug_allergies,
            food_allergies=body.food_allergies,
            emergency_contacts=_emergency_contacts_from_patch(body),
            notes=body.notes,
        )

    async def patch_profile_by_id(
        self,
        profile_id: UUID,
        user_id: UUID,
        body: PatchProfileRequest,
    ) -> Profile:
        await self._access.require_profile_edit(profile_id, user_id)
        p = await self._repo.patch_profile(
            profile_id,
            full_name=body.full_name,
            dob=body.dob,
            gender=body.gender,
            height_cm=body.height_cm,
            weight_kg=body.weight_kg,
            address=body.address,
            avatar_url=body.avatar_url,
            status=body.status.value if body.status is not None else None,
        )
        if p is None:
            raise NotFoundError("Profile not found")
        return p

    async def delete_profile_by_id(self, profile_id: UUID, user_id: UUID) -> None:
        await self._access.require_profile_edit(profile_id, user_id)
        ok = await self._repo.soft_delete_profile(profile_id)
        if not ok:
            raise NotFoundError("Profile not found")

    async def get_profile_by_id(self, profile_id: UUID, user_id: UUID) -> Profile:
        await self._access.require_profile_read(profile_id, user_id)
        p = await self._repo.get_profile(profile_id)
        if p is None:
            raise NotFoundError("Profile not found")
        return p

    async def link_profile_by_id(
        self,
        profile_id: UUID,
        user_id: UUID,
        target_user_id: UUID,
    ) -> Profile:
        await self._access.require_profile_link(profile_id, user_id)
        target_user = await self._users.get_by_id(target_user_id)
        if target_user is None:
            raise NotFoundError("user_id not found")
        try:
            p = await self._repo.link_profile_to_user(profile_id, target_user_id)
        except IntegrityError as e:
            raise ConflictError("Profile already linked or not found") from e
        if p is None:
            raise ConflictError("Profile already linked or not found")
        return p

    async def get_health_by_profile_id(self, profile_id: UUID, user_id: UUID) -> HealthDetail | None:
        await self._access.require_profile_read(profile_id, user_id)
        return await self._repo.get_health(profile_id)

    async def patch_health_by_profile_id(
        self,
        profile_id: UUID,
        user_id: UUID,
        body: PatchHealthDetailRequest,
    ) -> HealthDetail:
        await self._access.require_profile_health_edit(profile_id, user_id)
        return await self._repo.upsert_health(
            profile_id,
            blood_type=body.blood_type,
            chronic_diseases=body.chronic_diseases,
            allergies=body.allergies,
            drug_allergies=body.drug_allergies,
            food_allergies=body.food_allergies,
            emergency_contacts=_emergency_contacts_from_patch(body),
            notes=body.notes,
        )

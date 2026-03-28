from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.application.dtos.family_dto import (
    CreateFamilyRequest,
    CreateProfileInFamilyRequest,
    JoinFamilyRequest,
    PatchFamilyRequest,
    PatchHealthDetailRequest,
    PatchMembershipRoleRequest,
    PatchProfileRequest,
)
from app.application.family_errors import ConflictError, ForbiddenError, NotFoundError
from app.domain.entities.family import Family, FamilyMembership, FamilyRole
from app.domain.entities.health_detail import HealthDetail
from app.domain.entities.profile import Profile
from app.domain.services.family_permission import has_at_least
from app.infrastructure.repositories.family_repository_pg import FamilyRepositoryPG
from app.infrastructure.repositories.user_repository_pg import UserRepositoryPG


class FamiliesService:
    """Application service for families / profiles / health (feature 002)."""

    def __init__(self, repo: FamilyRepositoryPG, users: UserRepositoryPG) -> None:
        self._repo = repo
        self._users = users

    async def _membership_or_404(self, family_id: UUID, user_id: UUID) -> FamilyMembership:
        m = await self._repo.get_user_membership_in_family(family_id, user_id)
        if m is None:
            raise NotFoundError("Family not found or not a member")
        return m

    async def create_family(
        self,
        user_id: UUID,
        body: CreateFamilyRequest,
    ) -> tuple[Family, Profile, FamilyMembership]:
        return await self._repo.create_family_with_owner_profile(
            family_name=body.family_name,
            creator_user_id=user_id,
            creator_full_name=body.full_name,
        )

    async def list_my_families(self, user_id: UUID) -> list[Family]:
        return await self._repo.list_families_for_user(user_id)

    async def get_family(self, family_id: UUID, user_id: UUID) -> Family:
        await self._membership_or_404(family_id, user_id)
        fam = await self._repo.get_family(family_id)
        if fam is None:
            raise NotFoundError("Family not found")
        return fam

    async def patch_family(
        self,
        family_id: UUID,
        user_id: UUID,
        body: PatchFamilyRequest,
    ) -> Family:
        m = await self._membership_or_404(family_id, user_id)
        if not has_at_least(m.role, FamilyRole.ADMIN):
            raise ForbiddenError("OWNER or ADMIN required")
        fam = await self._repo.update_family_name(family_id, body.family_name)
        if fam is None:
            raise NotFoundError("Family not found")
        return fam

    async def join_family(self, user_id: UUID, body: JoinFamilyRequest) -> tuple[Family, Profile]:
        fam = await self._repo.find_family_by_invite_code(body.invite_code)
        if fam is None:
            raise NotFoundError("Invalid or expired invite code")

        prof = await self._repo.find_personal_profile_for_user(user_id)
        if prof is None:
            if not body.full_name or not body.full_name.strip():
                raise ValueError("full_name is required when you have no personal profile yet")
            prof = await self._repo.create_personal_profile(
                user_id=user_id,
                full_name=body.full_name,
            )

        if await self._repo.has_membership(fam.id, prof.id):
            raise ConflictError("Already a member of this family")

        try:
            await self._repo.create_membership(
                family_id=fam.id,
                profile_id=prof.id,
                role=FamilyRole.MEMBER,
                added_by=user_id,
            )
        except IntegrityError as e:
            raise ConflictError("Already a member of this family") from e

        return fam, prof

    async def rotate_invite(self, family_id: UUID, user_id: UUID) -> Family:
        m = await self._membership_or_404(family_id, user_id)
        if m.role != FamilyRole.OWNER:
            raise ForbiddenError("Only OWNER can rotate invite code")
        fam = await self._repo.rotate_invite(family_id)
        if fam is None:
            raise NotFoundError("Family not found")
        return fam

    async def list_members(
        self,
        family_id: UUID,
        user_id: UUID,
    ) -> list[tuple[FamilyMembership, Profile]]:
        await self._membership_or_404(family_id, user_id)
        return await self._repo.list_members_rows(family_id)

    async def patch_membership_role(
        self,
        family_id: UUID,
        membership_id: UUID,
        user_id: UUID,
        body: PatchMembershipRoleRequest,
    ) -> FamilyMembership:
        if not await self._repo.membership_belongs_to_family(membership_id, family_id):
            raise NotFoundError("Membership not found")
        actor = await self._membership_or_404(family_id, user_id)
        if actor.role != FamilyRole.OWNER:
            raise ForbiddenError("Only OWNER can change roles")
        updated = await self._repo.update_membership_role(membership_id, body.role)
        if updated is None:
            raise NotFoundError("Membership not found")
        return updated

    async def delete_membership(
        self,
        family_id: UUID,
        membership_id: UUID,
        user_id: UUID,
    ) -> None:
        if not await self._repo.membership_belongs_to_family(membership_id, family_id):
            raise NotFoundError("Membership not found")
        target = await self._repo.get_membership(membership_id)
        if target is None:
            raise NotFoundError("Membership not found")
        prof = await self._repo.get_profile(target.profile_id)
        actor = await self._membership_or_404(family_id, user_id)
        is_self = prof is not None and prof.linked_user_id == user_id
        if is_self:
            await self._repo.delete_membership(membership_id)
            return
        if not has_at_least(actor.role, FamilyRole.ADMIN):
            raise ForbiddenError("OWNER or ADMIN required to remove other members")
        await self._repo.delete_membership(membership_id)

    async def create_profile(
        self,
        family_id: UUID,
        user_id: UUID,
        body: CreateProfileInFamilyRequest,
    ) -> tuple[Profile, FamilyMembership]:
        m = await self._membership_or_404(family_id, user_id)
        if not has_at_least(m.role, FamilyRole.ADMIN):
            raise ForbiddenError("OWNER or ADMIN required")
        owner = await self._users.get_by_id(body.owner_user_id)
        if owner is None:
            raise NotFoundError("owner_user_id not found")
        return await self._repo.create_profile_in_family(
            family_id=family_id,
            owner_user_id=body.owner_user_id,
            full_name=body.full_name,
            role=body.role,
            added_by=user_id,
            dob=body.dob,
            gender=body.gender,
            linked_user_id=None,
        )

    async def list_profiles(self, family_id: UUID, user_id: UUID) -> list[Profile]:
        m = await self._membership_or_404(family_id, user_id)
        rows = await self._repo.list_profiles_in_family(family_id)
        if not has_at_least(m.role, FamilyRole.ADMIN):
            rows = [p for p in rows if p.linked_user_id == user_id]
        return rows

    async def list_my_linked_profiles(
        self,
        user_id: UUID,
        profile_scope: Literal["all", "without_family", "with_family"] = "all",
    ) -> list[Profile]:
        return await self._repo.list_linked_profiles_for_user(
            user_id,
            profile_scope=profile_scope,
        )

    async def create_my_personal_profile(self, user_id: UUID, full_name: str) -> Profile:
        existing = await self._repo.find_personal_profile_for_user(user_id)
        if existing is not None:
            raise ConflictError("Personal profile already exists")
        try:
            return await self._repo.create_personal_profile(user_id=user_id, full_name=full_name)
        except IntegrityError as e:
            raise ConflictError("Personal profile already exists") from e

    async def preview_invite(self, invite_code: str) -> Family:
        fam = await self._repo.find_family_by_invite_code(invite_code)
        if fam is None:
            raise NotFoundError("Invalid or expired invite code")
        return fam

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
            status=body.status,
        )
        if p is None:
            raise NotFoundError("Profile not found")
        return p

    async def delete_profile(self, family_id: UUID, profile_id: UUID, user_id: UUID) -> None:
        m = await self._membership_or_404(family_id, user_id)
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
        m = await self._membership_or_404(family_id, user_id)
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
            raise ConflictError("User already linked to another profile") from e
        if p is None:
            raise ConflictError("Profile already linked or not found")
        return p

    async def get_health(
        self,
        family_id: UUID,
        profile_id: UUID,
        user_id: UUID,
    ) -> HealthDetail | None:
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
        m = await self._membership_or_404(family_id, user_id)
        if not has_at_least(m.role, FamilyRole.ADMIN):
            raise ForbiddenError("OWNER or ADMIN required to edit health details")
        if not await self._repo.profile_in_family(profile_id, family_id):
            raise NotFoundError("Profile not found")
        return await self._repo.upsert_health(
            profile_id,
            blood_type=body.blood_type,
            chronic_diseases=body.chronic_diseases,
            allergies=body.allergies,
            emergency_contact=body.emergency_contact,
            notes=body.notes,
        )

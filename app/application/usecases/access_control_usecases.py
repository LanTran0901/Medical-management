from __future__ import annotations

from uuid import UUID

from app.application.family_errors import ForbiddenError, NotFoundError
from app.application.ports.access_control_port import (
    AccessControlPort,
    AttachmentAccessContext,
    MedicalRecordAccessContext,
    MembershipAccessContext,
    MedicineItemAccessContext,
    ProfileAccessContext,
    UserVaccinationAccessContext,
    VaccinationDoseAccessContext,
)
from app.domain.entities.family import FamilyMembership, FamilyRole
from app.domain.services.family_permission import has_at_least


class AccessControlService:
    def __init__(self, access: AccessControlPort) -> None:
        self._access = access

    async def require_family_member(
        self,
        family_id: UUID,
        user_id: UUID,
        *,
        not_found_message: str = "Family not found",
    ) -> FamilyMembership:
        membership = await self._access.get_user_membership_in_family(family_id, user_id)
        if membership is None:
            if await self._access.family_exists(family_id):
                raise ForbiddenError("Not a member of this family")
            raise NotFoundError(not_found_message)
        return membership

    async def require_family_admin(self, family_id: UUID, user_id: UUID) -> FamilyMembership:
        membership = await self.require_family_member(family_id, user_id)
        if not has_at_least(membership.role, FamilyRole.ADMIN):
            raise ForbiddenError("OWNER or ADMIN required")
        return membership

    async def require_family_owner(self, family_id: UUID, user_id: UUID) -> FamilyMembership:
        membership = await self.require_family_member(family_id, user_id)
        if membership.role != FamilyRole.OWNER:
            raise ForbiddenError("Only OWNER can perform this action")
        return membership

    async def require_membership_role_edit(
        self,
        membership_id: UUID,
        user_id: UUID,
    ) -> MembershipAccessContext:
        context = await self._access.get_membership_context(membership_id)
        if context is None:
            raise NotFoundError("Membership not found")
        await self.require_family_owner(context.membership.family_id, user_id)
        return context

    async def require_membership_delete(
        self,
        membership_id: UUID,
        user_id: UUID,
    ) -> MembershipAccessContext:
        context = await self._access.get_membership_context(membership_id)
        if context is None:
            raise NotFoundError("Membership not found")
        if context.linked_user_id == user_id or context.owner_user_id == user_id:
            return context
        await self.require_family_admin(context.membership.family_id, user_id)
        return context

    async def require_profile_read(self, profile_id: UUID, user_id: UUID) -> ProfileAccessContext:
        context = await self._access.get_profile_context(profile_id)
        if context is None:
            raise NotFoundError("Profile not found")
        if self._is_self_profile(context, user_id):
            return context
        if await self._has_family_membership(user_id, context.family_ids):
            return context
        raise ForbiddenError("Not allowed to view this profile")

    async def require_profile_edit(self, profile_id: UUID, user_id: UUID) -> ProfileAccessContext:
        context = await self._access.get_profile_context(profile_id)
        if context is None:
            raise NotFoundError("Profile not found")
        if self._is_self_profile(context, user_id):
            return context
        if await self._has_family_admin_membership(user_id, context.family_ids):
            return context
        raise ForbiddenError("Not allowed to update this profile")

    async def require_profile_link(self, profile_id: UUID, user_id: UUID) -> ProfileAccessContext:
        context = await self._access.get_profile_context(profile_id)
        if context is None:
            raise NotFoundError("Profile not found")
        if await self._has_family_admin_membership(user_id, context.family_ids):
            return context
        raise ForbiddenError("OWNER or ADMIN required")

    async def require_profile_health_edit(self, profile_id: UUID, user_id: UUID) -> ProfileAccessContext:
        context = await self._access.get_profile_context(profile_id)
        if context is None:
            raise NotFoundError("Profile not found")
        if await self._has_family_admin_membership(user_id, context.family_ids):
            return context
        raise ForbiddenError("OWNER or ADMIN required to edit health details")

    async def require_medical_profile_view(self, profile_id: UUID, user_id: UUID) -> ProfileAccessContext:
        return await self.require_profile_read(profile_id, user_id)

    async def require_medical_profile_write(self, profile_id: UUID, user_id: UUID) -> ProfileAccessContext:
        context = await self._access.get_profile_context(profile_id)
        if context is None:
            raise NotFoundError("Profile not found")
        if self._is_self_profile(context, user_id):
            return context
        if await self._has_family_admin_membership(user_id, context.family_ids):
            return context
        raise ForbiddenError("Not allowed to manage medical resources for this profile")

    async def require_medicine_item_read(
        self,
        item_id: UUID,
        user_id: UUID,
    ) -> MedicineItemAccessContext:
        context = await self._access.get_medicine_item_context(item_id)
        if context is None:
            raise NotFoundError("Medicine item not found")
        if await self._has_family_membership(user_id, context.family_ids):
            return context
        raise ForbiddenError("Not allowed to view medicine inventory")

    async def require_medicine_item_write(
        self,
        item_id: UUID,
        user_id: UUID,
    ) -> MedicineItemAccessContext:
        context = await self._access.get_medicine_item_context(item_id)
        if context is None:
            raise NotFoundError("Medicine item not found")
        if await self._has_family_admin_membership(user_id, context.family_ids):
            return context
        raise ForbiddenError("Members may only view medicine inventory")

    async def require_medical_record_view(
        self,
        record_id: UUID,
        user_id: UUID,
    ) -> MedicalRecordAccessContext:
        context = await self._access.get_medical_record_context(record_id)
        if context is None or context.record.deleted_at is not None:
            raise NotFoundError("Medical record not found")
        if not await self._can_view_profile_scope(
            context.profile_owner_user_id,
            context.profile_linked_user_id,
            context.family_ids,
            user_id,
        ):
            raise ForbiddenError("Not allowed to view this medical record")
        return context

    async def require_medical_record_write(
        self,
        record_id: UUID,
        user_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> MedicalRecordAccessContext:
        context = await self._access.get_medical_record_context(record_id)
        if context is None or (context.record.deleted_at is not None and not include_deleted):
            raise NotFoundError("Medical record not found")
        if not await self._can_write_profile_scope(
            context.profile_owner_user_id,
            context.profile_linked_user_id,
            context.family_ids,
            user_id,
        ):
            raise ForbiddenError("Not allowed to manage this medical record")
        return context

    async def require_medical_record_hard_delete(
        self,
        record_id: UUID,
        user_id: UUID,
    ) -> MedicalRecordAccessContext:
        context = await self._access.get_medical_record_context(record_id)
        if context is None:
            raise NotFoundError("Medical record not found")
        if not await self._has_family_admin_membership_for_hard_delete(
            user_id,
            context.family_ids,
        ):
            raise ForbiddenError("Hard delete requires OWNER or ADMIN in the family")
        return context

    async def require_attachment_view(
        self,
        attachment_id: UUID,
        user_id: UUID,
    ) -> AttachmentAccessContext:
        context = await self._access.get_attachment_context(attachment_id)
        if context is None or context.record.deleted_at is not None:
            raise NotFoundError("Attachment not found")
        if not await self._can_view_profile_scope(
            context.profile_owner_user_id,
            context.profile_linked_user_id,
            context.family_ids,
            user_id,
        ):
            raise ForbiddenError("Not allowed to view this attachment")
        return context

    async def require_attachment_write(
        self,
        attachment_id: UUID,
        user_id: UUID,
    ) -> AttachmentAccessContext:
        context = await self._access.get_attachment_context(attachment_id)
        if context is None or context.record.deleted_at is not None:
            raise NotFoundError("Attachment not found")
        if not await self._can_write_profile_scope(
            context.profile_owner_user_id,
            context.profile_linked_user_id,
            context.family_ids,
            user_id,
        ):
            raise ForbiddenError("Not allowed to manage this attachment")
        return context

    async def require_user_vaccination_view(
        self,
        user_vaccination_id: UUID,
        user_id: UUID,
    ) -> UserVaccinationAccessContext:
        context = await self._access.get_user_vaccination_context(user_vaccination_id)
        if context is None:
            raise NotFoundError("User vaccination not found")
        if not await self._can_view_profile_scope(
            context.profile_owner_user_id,
            context.profile_linked_user_id,
            context.family_ids,
            user_id,
        ):
            raise ForbiddenError("Not allowed to view this vaccination subscription")
        return context

    async def require_user_vaccination_write(
        self,
        user_vaccination_id: UUID,
        user_id: UUID,
    ) -> UserVaccinationAccessContext:
        context = await self._access.get_user_vaccination_context(user_vaccination_id)
        if context is None:
            raise NotFoundError("User vaccination not found")
        if not await self._can_write_profile_scope(
            context.profile_owner_user_id,
            context.profile_linked_user_id,
            context.family_ids,
            user_id,
        ):
            raise ForbiddenError("Not allowed to manage this vaccination subscription")
        return context

    async def require_vaccination_dose_view(
        self,
        dose_id: UUID,
        user_id: UUID,
    ) -> VaccinationDoseAccessContext:
        context = await self._access.get_vaccination_dose_context(dose_id)
        if context is None:
            raise NotFoundError("Dose not found")
        if not await self._can_view_profile_scope(
            context.profile_owner_user_id,
            context.profile_linked_user_id,
            context.family_ids,
            user_id,
        ):
            raise ForbiddenError("Not allowed to view this vaccination dose")
        return context

    async def require_vaccination_dose_write(
        self,
        dose_id: UUID,
        user_id: UUID,
    ) -> VaccinationDoseAccessContext:
        context = await self._access.get_vaccination_dose_context(dose_id)
        if context is None:
            raise NotFoundError("Dose not found")
        if not await self._can_write_profile_scope(
            context.profile_owner_user_id,
            context.profile_linked_user_id,
            context.family_ids,
            user_id,
        ):
            raise ForbiddenError("Not allowed to manage this vaccination dose")
        return context

    def _is_self_profile(self, context: ProfileAccessContext, user_id: UUID) -> bool:
        return context.profile.owner_user_id == user_id or context.profile.linked_user_id == user_id

    async def _has_family_membership(self, user_id: UUID, family_ids: tuple[UUID, ...]) -> bool:
        memberships = await self._access.list_user_memberships_for_families(user_id, family_ids)
        return bool(memberships)

    async def _has_family_admin_membership(self, user_id: UUID, family_ids: tuple[UUID, ...]) -> bool:
        memberships = await self._access.list_user_memberships_for_families(user_id, family_ids)
        return any(has_at_least(m.role, FamilyRole.ADMIN) for m in memberships)

    async def _has_family_admin_membership_for_hard_delete(
        self,
        user_id: UUID,
        family_ids: tuple[UUID, ...],
    ) -> bool:
        memberships = await self._access.list_user_memberships_for_families(user_id, family_ids)
        return any(m.role in (FamilyRole.OWNER, FamilyRole.ADMIN) for m in memberships)

    def _is_self_profile_scope(
        self,
        owner_user_id: UUID,
        linked_user_id: UUID | None,
        user_id: UUID,
    ) -> bool:
        return owner_user_id == user_id or linked_user_id == user_id

    async def _can_view_profile_scope(
        self,
        owner_user_id: UUID,
        linked_user_id: UUID | None,
        family_ids: tuple[UUID, ...],
        user_id: UUID,
    ) -> bool:
        if self._is_self_profile_scope(owner_user_id, linked_user_id, user_id):
            return True
        return await self._has_family_membership(user_id, family_ids)

    async def _can_write_profile_scope(
        self,
        owner_user_id: UUID,
        linked_user_id: UUID | None,
        family_ids: tuple[UUID, ...],
        user_id: UUID,
    ) -> bool:
        if self._is_self_profile_scope(owner_user_id, linked_user_id, user_id):
            return True
        return await self._has_family_admin_membership(user_id, family_ids)

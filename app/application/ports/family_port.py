from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

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
from app.domain.entities.profile import Profile


class FamilyRepositoryPort(ABC):
    @abstractmethod
    async def get_family(self, family_id: UUID) -> Family | None:
        raise NotImplementedError

    @abstractmethod
    async def find_family_by_invite_code(self, code: str) -> Family | None:
        raise NotImplementedError

    @abstractmethod
    async def create_pending_public_invite(
        self,
        *,
        family_id: UUID,
        invite_code: str,
        expires_at: datetime,
        created_by: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def preview_public_invite(self, code: str) -> PublicInvitePreview | None:
        """Return preview if invite_code exists in family_public_invites; else None."""
        raise NotImplementedError

    @abstractmethod
    async def consume_pending_public_invite(self, code: str, consumed_by: UUID) -> Family | None:
        """Atomically mark token CONSUMED if valid; return family when successful."""
        raise NotImplementedError

    @abstractmethod
    async def revoke_pending_public_invite_for_family(self, family_id: UUID) -> None:
        """Revoke the single PENDING public token for this family (if any)."""
        raise NotImplementedError

    @abstractmethod
    async def update_family_name(self, family_id: UUID, name: str) -> Family | None:
        raise NotImplementedError

    @abstractmethod
    async def rotate_invite(
        self,
        family_id: UUID,
        *,
        public_invite_expires_at: datetime,
        rotated_by: UUID,
    ) -> Family | None:
        raise NotImplementedError

    @abstractmethod
    async def list_families_for_user(self, user_id: UUID) -> list[Family]:
        raise NotImplementedError

    @abstractmethod
    async def get_user_membership_in_family(self, family_id: UUID, user_id: UUID) -> FamilyMembership | None:
        raise NotImplementedError

    @abstractmethod
    async def get_membership(self, membership_id: UUID) -> FamilyMembership | None:
        raise NotImplementedError

    @abstractmethod
    async def membership_belongs_to_family(self, membership_id: UUID, family_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def update_membership_role(self, membership_id: UUID, role: FamilyRole) -> FamilyMembership | None:
        raise NotImplementedError

    @abstractmethod
    async def transfer_family_owner(
        self,
        *,
        family_id: UUID,
        new_owner_membership_id: UUID,
        changed_by: UUID,
    ) -> FamilyMembership | None:
        raise NotImplementedError

    @abstractmethod
    async def delete_membership(self, membership_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def create_family_with_owner_profile(
        self,
        *,
        family_name: str,
        address: str | None,
        avatar_url: str | None,
        creator_user_id: UUID,
        creator_full_name: str,
        public_invite_expires_at: datetime,
    ) -> tuple[Family, Profile, FamilyMembership]:
        raise NotImplementedError

    @abstractmethod
    async def find_personal_profile_for_user(self, user_id: UUID) -> Profile | None:
        raise NotImplementedError

    @abstractmethod
    async def list_linked_profiles_for_user(
        self,
        user_id: UUID,
        *,
        profile_scope: str = "all",
    ) -> list[Profile]:
        raise NotImplementedError

    @abstractmethod
    async def create_personal_profile(self, *, user_id: UUID, full_name: str) -> Profile:
        raise NotImplementedError

    @abstractmethod
    async def create_membership(
        self,
        *,
        family_id: UUID,
        profile_id: UUID,
        role: FamilyRole,
        relation_role: str | None,
        added_by: UUID,
    ) -> FamilyMembership:
        raise NotImplementedError

    @abstractmethod
    async def has_membership(self, family_id: UUID, profile_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_profile(self, profile_id: UUID) -> Profile | None:
        raise NotImplementedError

    @abstractmethod
    async def profile_in_family(self, profile_id: UUID, family_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def list_profiles_in_family(self, family_id: UUID) -> list[Profile]:
        raise NotImplementedError

    @abstractmethod
    async def list_members_rows(self, family_id: UUID) -> list[tuple[FamilyMembership, Profile]]:
        raise NotImplementedError

    @abstractmethod
    async def get_member_row(self, membership_id: UUID) -> tuple[FamilyMembership, Profile] | None:
        raise NotImplementedError

    @abstractmethod
    async def list_health_for_profiles(self, profile_ids: list[UUID]) -> dict[UUID, HealthDetail]:
        raise NotImplementedError

    @abstractmethod
    async def create_profile_in_family(
        self,
        *,
        family_id: UUID,
        owner_user_id: UUID,
        full_name: str,
        role: FamilyRole,
        relation_role: str | None,
        added_by: UUID,
        dob: date | None = None,
        gender: str | None = None,
        height_cm: Decimal | None = None,
        weight_kg: Decimal | None = None,
        address: str | None = None,
        avatar_url: str | None = None,
        linked_user_id: UUID | None = None,
    ) -> tuple[Profile, FamilyMembership]:
        raise NotImplementedError

    @abstractmethod
    async def patch_profile(
        self,
        profile_id: UUID,
        *,
        full_name: str | None = None,
        dob: date | None = None,
        gender: str | None = None,
        height_cm: Decimal | None = None,
        weight_kg: Decimal | None = None,
        address: str | None = None,
        avatar_url: str | None = None,
        status: str | None = None,
    ) -> Profile | None:
        raise NotImplementedError

    @abstractmethod
    async def link_profile_to_user(self, profile_id: UUID, user_id: UUID) -> Profile | None:
        raise NotImplementedError

    @abstractmethod
    async def claim_profile_to_user(self, profile_id: UUID, user_id: UUID) -> Profile | None:
        raise NotImplementedError

    @abstractmethod
    async def soft_delete_profile(self, profile_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_health(self, profile_id: UUID) -> HealthDetail | None:
        raise NotImplementedError

    @abstractmethod
    async def upsert_health(
        self,
        profile_id: UUID,
        *,
        blood_type: str | None = None,
        chronic_diseases: list[str] | None = None,
        allergies: list[str] | None = None,
        drug_allergies: list[str] | None = None,
        food_allergies: list[str] | None = None,
        emergency_contacts: list[EmergencyContactEntry] | None = None,
        notes: str | None = None,
    ) -> HealthDetail:
        raise NotImplementedError

    @abstractmethod
    async def find_pending_invite(
        self,
        *,
        family_id: UUID,
        user_id: UUID | None,
        phone_number: str | None,
    ) -> FamilyInvite | None:
        raise NotImplementedError

    @abstractmethod
    async def create_family_invite(
        self,
        *,
        family_id: UUID,
        user_id: UUID | None,
        phone_number: str | None,
        role: FamilyRole,
        relation_role: str | None,
        invited_by: UUID,
    ) -> FamilyInvite:
        raise NotImplementedError

    @abstractmethod
    async def get_family_invite(self, invite_id: UUID) -> FamilyInvite | None:
        raise NotImplementedError

    @abstractmethod
    async def update_family_invite_status(
        self,
        invite_id: UUID,
        status: FamilyInviteStatus,
    ) -> FamilyInvite | None:
        raise NotImplementedError

    @abstractmethod
    async def list_family_invites(self, family_id: UUID) -> list[FamilyInvite]:
        raise NotImplementedError

    @abstractmethod
    async def list_family_ids_for_profile(self, profile_id: UUID) -> list[UUID]:
        raise NotImplementedError

    @abstractmethod
    async def list_invites_for_user_with_context(
        self,
        *,
        user_id: UUID,
        status: FamilyInviteStatus | None,
        offset: int,
        limit: int,
    ) -> list[FamilyInviteInboxItem]:
        raise NotImplementedError

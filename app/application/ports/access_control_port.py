from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from uuid import UUID

from app.domain.entities.family import FamilyMembership
from app.domain.entities.medical_record import MedicalRecord, MedicalRecordAttachment
from app.domain.entities.medicine_inventory import MedicineInventory
from app.domain.entities.profile import Profile
from app.domain.entities.vaccination import VaccinationDose, UserVaccination


@dataclass(frozen=True, slots=True)
class MembershipAccessContext:
    membership: FamilyMembership
    owner_user_id: UUID
    linked_user_id: UUID | None


@dataclass(frozen=True, slots=True)
class ProfileAccessContext:
    profile: Profile
    family_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class MedicineItemAccessContext:
    item: MedicineInventory
    family_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class MedicalRecordAccessContext:
    record: MedicalRecord
    profile_owner_user_id: UUID
    profile_linked_user_id: UUID | None
    family_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class AttachmentAccessContext:
    attachment: MedicalRecordAttachment
    record: MedicalRecord
    profile_owner_user_id: UUID
    profile_linked_user_id: UUID | None
    family_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class UserVaccinationAccessContext:
    user_vaccination: UserVaccination
    profile_owner_user_id: UUID
    profile_linked_user_id: UUID | None
    family_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class VaccinationDoseAccessContext:
    dose: VaccinationDose
    user_vaccination: UserVaccination
    profile_owner_user_id: UUID
    profile_linked_user_id: UUID | None
    family_ids: tuple[UUID, ...]


class AccessControlPort:
    async def family_exists(self, family_id: UUID) -> bool:
        raise NotImplementedError

    async def get_user_membership_in_family(self, family_id: UUID, user_id: UUID) -> FamilyMembership | None:
        raise NotImplementedError

    async def list_user_memberships_for_families(
        self,
        user_id: UUID,
        family_ids: Sequence[UUID],
    ) -> list[FamilyMembership]:
        raise NotImplementedError

    async def get_membership_context(self, membership_id: UUID) -> MembershipAccessContext | None:
        raise NotImplementedError

    async def get_profile_context(self, profile_id: UUID) -> ProfileAccessContext | None:
        raise NotImplementedError

    async def get_medicine_item_context(self, item_id: UUID) -> MedicineItemAccessContext | None:
        raise NotImplementedError

    async def get_medical_record_context(self, record_id: UUID) -> MedicalRecordAccessContext | None:
        raise NotImplementedError

    async def get_attachment_context(self, attachment_id: UUID) -> AttachmentAccessContext | None:
        raise NotImplementedError

    async def get_user_vaccination_context(
        self,
        user_vaccination_id: UUID,
    ) -> UserVaccinationAccessContext | None:
        raise NotImplementedError

    async def get_vaccination_dose_context(self, dose_id: UUID) -> VaccinationDoseAccessContext | None:
        raise NotImplementedError

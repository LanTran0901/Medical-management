from __future__ import annotations

import sqlalchemy as sa
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.domain.entities.medical_record import MedicalRecord, MedicalRecordAttachment
from app.domain.entities.medicine_inventory import MedicineInventory
from app.domain.entities.profile import Profile
from app.domain.entities.vaccination import VaccinationDose, UserVaccination
from app.infrastructure.config.database.postgres.models.family_models import FamilyMembershipModel, FamilyModel
from app.infrastructure.config.database.postgres.models.medical_record_models import (
    MedicalRecordAttachmentModel,
    MedicalRecordModel,
)
from app.infrastructure.config.database.postgres.models.medicine_inventory_model import (
    MedicineInventoryModel,
)
from app.infrastructure.config.database.postgres.models.profile_models import ProfileModel
from app.infrastructure.config.database.postgres.models.vaccination_models import (
    UserVaccinationModel,
    VaccinationDoseModel,
)


class AccessControlPG(AccessControlPort):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_membership(model: FamilyMembershipModel) -> FamilyMembership:
        return FamilyMembership(
            id=model.id,
            family_id=model.family_id,
            profile_id=model.profile_id,
            role=FamilyRole(model.role),
            added_by=model.added_by,
            created_at=model.created_at,
            relation_role=getattr(model, "relation_role", None),
        )

    @staticmethod
    def _to_profile(model: ProfileModel) -> Profile:
        return Profile(
            id=model.id,
            owner_user_id=model.owner_user_id,
            linked_user_id=model.linked_user_id,
            full_name=model.full_name,
            dob=model.dob,
            gender=model.gender,
            height_cm=model.height_cm,
            weight_kg=model.weight_kg,
            address=model.address,
            avatar_url=model.avatar_url,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def _to_record(model: MedicalRecordModel) -> MedicalRecord:
        return MedicalRecord(
            id=model.id,
            profile_id=model.profile_id,
            created_by=model.created_by,
            title=model.title,
            diagnosis_name=model.diagnosis_name,
            diagnosis_slug=model.diagnosis_slug,
            doctor_name=model.doctor_name,
            hospital_name=model.hospital_name,
            visit_date=model.visit_date,
            specialty=model.specialty,
            symptoms=list(model.symptoms) if model.symptoms is not None else None,
            test_results=model.test_results,
            doctor_advice=model.doctor_advice,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def _to_attachment(model: MedicalRecordAttachmentModel) -> MedicalRecordAttachment:
        return MedicalRecordAttachment(
            id=model.id,
            medical_record_id=model.medical_record_id,
            file_name=model.file_name,
            file_type=model.file_type,
            file_url=model.file_url,
        )

    @staticmethod
    def _to_medicine_item(model: MedicineInventoryModel) -> MedicineInventory:
        return MedicineInventory(
            id=model.id,
            profile_id=model.profile_id,
            medicine_name=model.medicine_name,
            medicine_type=model.medicine_type,
            expiry_date=model.expiry_date,
            quantity_stock=model.quantity_stock,
            unit=model.unit,
            min_stock_alert=model.min_stock_alert,
            instruction=model.instruction,
            dosage_value=model.dosage_value,
            dosage_unit=model.dosage_unit,
            dosage_per_use_value=model.dosage_per_use_value,
            dosage_per_use_unit=model.dosage_per_use_unit,
            use_tags=list(model.use_tags) if model.use_tags is not None else None,
            storage_location=model.storage_location,
            expiry_alert_days_before=model.expiry_alert_days_before,
            low_stock_alert_enabled=model.low_stock_alert_enabled,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_user_vaccination(model: UserVaccinationModel) -> UserVaccination:
        return UserVaccination(
            id=model.id,
            profile_id=model.profile_id,
            recommendation_id=model.recommendation_id,
            user_id=model.user_id,
            status=model.status,
            created_at=model.created_at,
        )

    @staticmethod
    def _to_dose(model: VaccinationDoseModel) -> VaccinationDose:
        return VaccinationDose(
            id=model.id,
            user_vaccination_id=model.user_vaccination_id,
            dose_index=model.dose_index,
            administered_at=model.administered_at,
            scheduled_at=model.scheduled_at,
            location=model.location,
            reaction=model.reaction,
            proof_url=model.proof_url,
            reminder_enabled=model.reminder_enabled,
            remind_before_value=model.remind_before_value,
            remind_before_unit=model.remind_before_unit,
        )

    @staticmethod
    def _role_rank_expr():
        return sa.case(
            (FamilyMembershipModel.role == FamilyRole.OWNER.value, 3),
            (FamilyMembershipModel.role == FamilyRole.ADMIN.value, 2),
            (FamilyMembershipModel.role == FamilyRole.MEMBER.value, 1),
            else_=0,
        )

    @staticmethod
    def _is_actor_profile(user_id: UUID):
        return or_(
            ProfileModel.owner_user_id == user_id,
            ProfileModel.linked_user_id == user_id,
        )

    async def _family_ids_for_profile(self, profile_id: UUID) -> tuple[UUID, ...]:
        stmt = select(FamilyMembershipModel.family_id).where(FamilyMembershipModel.profile_id == profile_id)
        result = await self.session.execute(stmt)
        return tuple(result.scalars().all())

    async def family_exists(self, family_id: UUID) -> bool:
        stmt = select(FamilyModel.id).where(FamilyModel.id == family_id).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_user_membership_in_family(self, family_id: UUID, user_id: UUID) -> FamilyMembership | None:
        rank_expr = self._role_rank_expr()
        stmt = (
            select(FamilyMembershipModel)
            .join(ProfileModel, ProfileModel.id == FamilyMembershipModel.profile_id)
            .where(
                FamilyMembershipModel.family_id == family_id,
                self._is_actor_profile(user_id),
                ProfileModel.deleted_at.is_(None),
            )
            .order_by(rank_expr.desc(), FamilyMembershipModel.created_at.asc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalars().first()
        return self._to_membership(model) if model else None

    async def list_user_memberships_for_families(
        self,
        user_id: UUID,
        family_ids: tuple[UUID, ...] | list[UUID],
    ) -> list[FamilyMembership]:
        if not family_ids:
            return []
        rank_expr = self._role_rank_expr()
        stmt = (
            select(FamilyMembershipModel)
            .join(ProfileModel, ProfileModel.id == FamilyMembershipModel.profile_id)
            .where(
                FamilyMembershipModel.family_id.in_(family_ids),
                self._is_actor_profile(user_id),
                ProfileModel.deleted_at.is_(None),
            )
            .order_by(
                FamilyMembershipModel.family_id.asc(),
                rank_expr.desc(),
                FamilyMembershipModel.created_at.asc(),
            )
        )
        result = await self.session.execute(stmt)
        memberships = [self._to_membership(row) for row in result.scalars().all()]
        highest_by_family: dict[UUID, FamilyMembership] = {}
        for membership in memberships:
            if membership.family_id not in highest_by_family:
                highest_by_family[membership.family_id] = membership
        return list(highest_by_family.values())

    async def get_membership_context(self, membership_id: UUID) -> MembershipAccessContext | None:
        stmt = (
            select(FamilyMembershipModel, ProfileModel)
            .join(ProfileModel, ProfileModel.id == FamilyMembershipModel.profile_id)
            .where(FamilyMembershipModel.id == membership_id)
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        membership, profile = row
        return MembershipAccessContext(
            membership=self._to_membership(membership),
            owner_user_id=profile.owner_user_id,
            linked_user_id=profile.linked_user_id,
        )

    async def get_profile_context(self, profile_id: UUID) -> ProfileAccessContext | None:
        model = await self.session.get(ProfileModel, profile_id)
        if model is None or model.deleted_at is not None:
            return None
        stmt = select(FamilyMembershipModel.family_id).where(FamilyMembershipModel.profile_id == profile_id)
        result = await self.session.execute(stmt)
        family_ids = tuple(result.scalars().all())
        return ProfileAccessContext(
            profile=self._to_profile(model),
            family_ids=family_ids,
        )

    async def get_medicine_item_context(self, item_id: UUID) -> MedicineItemAccessContext | None:
        model = await self.session.get(MedicineInventoryModel, item_id)
        if model is None:
            return None
        family_ids: tuple[UUID, ...] = ()
        if model.profile_id is not None:
            family_ids = await self._family_ids_for_profile(model.profile_id)
        return MedicineItemAccessContext(item=self._to_medicine_item(model), family_ids=family_ids)

    async def get_medical_record_context(self, record_id: UUID) -> MedicalRecordAccessContext | None:
        stmt = (
            select(MedicalRecordModel, ProfileModel)
            .join(ProfileModel, ProfileModel.id == MedicalRecordModel.profile_id)
            .where(MedicalRecordModel.id == record_id)
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        record, profile = row
        family_ids = await self._family_ids_for_profile(profile.id)
        return MedicalRecordAccessContext(
            record=self._to_record(record),
            profile_owner_user_id=profile.owner_user_id,
            profile_linked_user_id=profile.linked_user_id,
            family_ids=family_ids,
        )

    async def get_attachment_context(self, attachment_id: UUID) -> AttachmentAccessContext | None:
        stmt = (
            select(MedicalRecordAttachmentModel, MedicalRecordModel, ProfileModel)
            .join(MedicalRecordModel, MedicalRecordModel.id == MedicalRecordAttachmentModel.medical_record_id)
            .join(ProfileModel, ProfileModel.id == MedicalRecordModel.profile_id)
            .where(MedicalRecordAttachmentModel.id == attachment_id)
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        attachment, record, profile = row
        family_ids = await self._family_ids_for_profile(profile.id)
        return AttachmentAccessContext(
            attachment=self._to_attachment(attachment),
            record=self._to_record(record),
            profile_owner_user_id=profile.owner_user_id,
            profile_linked_user_id=profile.linked_user_id,
            family_ids=family_ids,
        )

    async def get_user_vaccination_context(
        self,
        user_vaccination_id: UUID,
    ) -> UserVaccinationAccessContext | None:
        stmt = (
            select(UserVaccinationModel, ProfileModel)
            .join(ProfileModel, ProfileModel.id == UserVaccinationModel.profile_id)
            .where(UserVaccinationModel.id == user_vaccination_id)
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        user_vaccination, profile = row
        family_ids = await self._family_ids_for_profile(profile.id)
        return UserVaccinationAccessContext(
            user_vaccination=self._to_user_vaccination(user_vaccination),
            profile_owner_user_id=profile.owner_user_id,
            profile_linked_user_id=profile.linked_user_id,
            family_ids=family_ids,
        )

    async def get_vaccination_dose_context(self, dose_id: UUID) -> VaccinationDoseAccessContext | None:
        stmt = (
            select(VaccinationDoseModel, UserVaccinationModel, ProfileModel)
            .join(UserVaccinationModel, UserVaccinationModel.id == VaccinationDoseModel.user_vaccination_id)
            .join(ProfileModel, ProfileModel.id == UserVaccinationModel.profile_id)
            .where(VaccinationDoseModel.id == dose_id)
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        dose, user_vaccination, profile = row
        family_ids = await self._family_ids_for_profile(profile.id)
        return VaccinationDoseAccessContext(
            dose=self._to_dose(dose),
            user_vaccination=self._to_user_vaccination(user_vaccination),
            profile_owner_user_id=profile.owner_user_id,
            profile_linked_user_id=profile.linked_user_id,
            family_ids=family_ids,
        )

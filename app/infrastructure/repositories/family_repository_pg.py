from __future__ import annotations

import secrets
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.family import Family, FamilyMembership, FamilyRole
from app.domain.entities.health_detail import HealthDetail
from app.domain.entities.profile import Profile
from app.infrastructure.config.database.postgres.models.family_models import (
    FamilyMembershipModel,
    FamilyModel,
)
from app.infrastructure.config.database.postgres.models.profile_models import (
    HealthDetailModel,
    ProfileModel,
)


class FamilyRepositoryPG:
    """PostgreSQL implementation for families / profiles / health_details."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _generate_unique_invite_code(self) -> str:
        for _ in range(20):
            code = secrets.token_urlsafe(12)[:16]
            stmt = select(FamilyModel.id).where(FamilyModel.invite_code == code).limit(1)
            r = await self.session.execute(stmt)
            if r.scalar_one_or_none() is None:
                return code
        raise RuntimeError("Could not generate unique invite_code")

    @staticmethod
    def _to_family(m: FamilyModel) -> Family:
        return Family(
            id=m.id,
            family_name=m.family_name,
            invite_code=m.invite_code,
            created_at=m.created_at,
        )

    @staticmethod
    def _to_membership(m: FamilyMembershipModel) -> FamilyMembership:
        return FamilyMembership(
            id=m.id,
            family_id=m.family_id,
            profile_id=m.profile_id,
            role=FamilyRole(m.role),
            added_by=m.added_by,
            created_at=m.created_at,
        )

    @staticmethod
    def _to_profile(m: ProfileModel) -> Profile:
        return Profile(
            id=m.id,
            owner_user_id=m.owner_user_id,
            linked_user_id=m.linked_user_id,
            full_name=m.full_name,
            dob=m.dob,
            gender=m.gender,
            height_cm=m.height_cm,
            weight_kg=m.weight_kg,
            address=m.address,
            avatar_url=m.avatar_url,
            status=m.status,
            created_at=m.created_at,
            updated_at=m.updated_at,
            deleted_at=m.deleted_at,
        )

    @staticmethod
    def _to_health(m: HealthDetailModel) -> HealthDetail:
        return HealthDetail(
            id=m.id,
            profile_id=m.profile_id,
            blood_type=m.blood_type,
            chronic_diseases=list(m.chronic_diseases) if m.chronic_diseases is not None else None,
            allergies=list(m.allergies) if m.allergies is not None else None,
            emergency_contact=m.emergency_contact,
            notes=m.notes,
            updated_at=m.updated_at,
        )

    async def get_family(self, family_id: UUID) -> Family | None:
        m = await self.session.get(FamilyModel, family_id)
        return self._to_family(m) if m else None

    async def find_family_by_invite_code(self, code: str) -> Family | None:
        stmt = select(FamilyModel).where(FamilyModel.invite_code == code.strip())
        r = await self.session.execute(stmt)
        m = r.scalar_one_or_none()
        return self._to_family(m) if m else None

    async def update_family_name(self, family_id: UUID, name: str) -> Family | None:
        m = await self.session.get(FamilyModel, family_id)
        if m is None:
            return None
        m.family_name = name
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_family(m)

    async def rotate_invite(self, family_id: UUID) -> Family | None:
        m = await self.session.get(FamilyModel, family_id)
        if m is None:
            return None
        m.invite_code = await self._generate_unique_invite_code()
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_family(m)

    async def list_families_for_user(self, user_id: UUID) -> list[Family]:
        stmt = (
            select(FamilyModel)
            .join(FamilyMembershipModel, FamilyMembershipModel.family_id == FamilyModel.id)
            .join(ProfileModel, ProfileModel.id == FamilyMembershipModel.profile_id)
            .where(
                ProfileModel.linked_user_id == user_id,
                ProfileModel.deleted_at.is_(None),
            )
            .distinct()
        )
        r = await self.session.execute(stmt)
        return [self._to_family(row) for row in r.scalars().all()]

    async def get_user_membership_in_family(
        self,
        family_id: UUID,
        user_id: UUID,
    ) -> FamilyMembership | None:
        stmt = (
            select(FamilyMembershipModel)
            .join(ProfileModel, ProfileModel.id == FamilyMembershipModel.profile_id)
            .where(
                FamilyMembershipModel.family_id == family_id,
                ProfileModel.linked_user_id == user_id,
                ProfileModel.deleted_at.is_(None),
            )
        )
        r = await self.session.execute(stmt)
        row = r.scalar_one_or_none()
        return self._to_membership(row) if row else None

    async def get_membership(self, membership_id: UUID) -> FamilyMembership | None:
        m = await self.session.get(FamilyMembershipModel, membership_id)
        return self._to_membership(m) if m else None

    async def membership_belongs_to_family(
        self,
        membership_id: UUID,
        family_id: UUID,
    ) -> bool:
        m = await self.session.get(FamilyMembershipModel, membership_id)
        return m is not None and m.family_id == family_id

    async def update_membership_role(
        self,
        membership_id: UUID,
        role: FamilyRole,
    ) -> FamilyMembership | None:
        m = await self.session.get(FamilyMembershipModel, membership_id)
        if m is None:
            return None
        m.role = role.value
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_membership(m)

    async def delete_membership(self, membership_id: UUID) -> bool:
        m = await self.session.get(FamilyMembershipModel, membership_id)
        if m is None:
            return False
        await self.session.delete(m)
        await self.session.flush()
        return True

    async def create_family_with_owner_profile(
        self,
        *,
        family_name: str,
        creator_user_id: UUID,
        creator_full_name: str,
    ) -> tuple[Family, Profile, FamilyMembership]:
        invite = await self._generate_unique_invite_code()
        fam = FamilyModel(family_name=family_name.strip(), invite_code=invite)
        self.session.add(fam)
        await self.session.flush()

        prof = ProfileModel(
            owner_user_id=creator_user_id,
            linked_user_id=creator_user_id,
            full_name=creator_full_name.strip(),
        )
        self.session.add(prof)
        await self.session.flush()

        mem = FamilyMembershipModel(
            family_id=fam.id,
            profile_id=prof.id,
            role=FamilyRole.OWNER.value,
            added_by=creator_user_id,
        )
        self.session.add(mem)
        await self.session.flush()
        await self.session.refresh(fam)
        await self.session.refresh(prof)
        await self.session.refresh(mem)
        return self._to_family(fam), self._to_profile(prof), self._to_membership(mem)

    async def find_personal_profile_for_user(self, user_id: UUID) -> Profile | None:
        stmt = select(ProfileModel).where(
            ProfileModel.linked_user_id == user_id,
            ProfileModel.deleted_at.is_(None),
        )
        r = await self.session.execute(stmt)
        m = r.scalar_one_or_none()
        return self._to_profile(m) if m else None

    async def create_personal_profile(
        self,
        *,
        user_id: UUID,
        full_name: str,
    ) -> Profile:
        prof = ProfileModel(
            owner_user_id=user_id,
            linked_user_id=user_id,
            full_name=full_name.strip(),
        )
        self.session.add(prof)
        await self.session.flush()
        await self.session.refresh(prof)
        return self._to_profile(prof)

    async def create_membership(
        self,
        *,
        family_id: UUID,
        profile_id: UUID,
        role: FamilyRole,
        added_by: UUID,
    ) -> FamilyMembership:
        mem = FamilyMembershipModel(
            family_id=family_id,
            profile_id=profile_id,
            role=role.value,
            added_by=added_by,
        )
        self.session.add(mem)
        await self.session.flush()
        await self.session.refresh(mem)
        return self._to_membership(mem)

    async def has_membership(self, family_id: UUID, profile_id: UUID) -> bool:
        stmt = select(FamilyMembershipModel.id).where(
            FamilyMembershipModel.family_id == family_id,
            FamilyMembershipModel.profile_id == profile_id,
        )
        r = await self.session.execute(stmt)
        return r.scalar_one_or_none() is not None

    async def get_profile(self, profile_id: UUID) -> Profile | None:
        m = await self.session.get(ProfileModel, profile_id)
        if m is None or m.deleted_at is not None:
            return None
        return self._to_profile(m)

    async def profile_in_family(self, profile_id: UUID, family_id: UUID) -> bool:
        stmt = select(FamilyMembershipModel.id).where(
            FamilyMembershipModel.family_id == family_id,
            FamilyMembershipModel.profile_id == profile_id,
        )
        r = await self.session.execute(stmt)
        return r.scalar_one_or_none() is not None

    async def list_profiles_in_family(self, family_id: UUID) -> list[Profile]:
        stmt = (
            select(ProfileModel)
            .join(FamilyMembershipModel, FamilyMembershipModel.profile_id == ProfileModel.id)
            .where(
                FamilyMembershipModel.family_id == family_id,
                ProfileModel.deleted_at.is_(None),
            )
        )
        r = await self.session.execute(stmt)
        return [self._to_profile(x) for x in r.scalars().all()]

    async def list_members_rows(self, family_id: UUID) -> list[tuple[FamilyMembership, Profile]]:
        stmt = (
            select(FamilyMembershipModel, ProfileModel)
            .join(ProfileModel, ProfileModel.id == FamilyMembershipModel.profile_id)
            .where(
                FamilyMembershipModel.family_id == family_id,
                ProfileModel.deleted_at.is_(None),
            )
        )
        r = await self.session.execute(stmt)
        out: list[tuple[FamilyMembership, Profile]] = []
        for mem, prof in r.all():
            out.append((self._to_membership(mem), self._to_profile(prof)))
        return out

    async def create_profile_in_family(
        self,
        *,
        family_id: UUID,
        owner_user_id: UUID,
        full_name: str,
        role: FamilyRole,
        added_by: UUID,
        dob: date | None = None,
        gender: str | None = None,
        linked_user_id: UUID | None = None,
    ) -> tuple[Profile, FamilyMembership]:
        prof = ProfileModel(
            owner_user_id=owner_user_id,
            linked_user_id=linked_user_id,
            full_name=full_name.strip(),
            dob=dob,
            gender=gender,
        )
        self.session.add(prof)
        await self.session.flush()

        mem = FamilyMembershipModel(
            family_id=family_id,
            profile_id=prof.id,
            role=role.value,
            added_by=added_by,
        )
        self.session.add(mem)
        await self.session.flush()
        await self.session.refresh(prof)
        await self.session.refresh(mem)
        return self._to_profile(prof), self._to_membership(mem)

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
        m = await self.session.get(ProfileModel, profile_id)
        if m is None or m.deleted_at is not None:
            return None
        if full_name is not None:
            m.full_name = full_name
        if dob is not None:
            m.dob = dob
        if gender is not None:
            m.gender = gender
        if height_cm is not None:
            m.height_cm = height_cm
        if weight_kg is not None:
            m.weight_kg = weight_kg
        if address is not None:
            m.address = address
        if avatar_url is not None:
            m.avatar_url = avatar_url
        if status is not None:
            m.status = status
        m.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_profile(m)

    async def link_profile_to_user(self, profile_id: UUID, user_id: UUID) -> Profile | None:
        m = await self.session.get(ProfileModel, profile_id)
        if m is None or m.deleted_at is not None:
            return None
        if m.linked_user_id is not None:
            return None
        m.linked_user_id = user_id
        m.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_profile(m)

    async def soft_delete_profile(self, profile_id: UUID) -> bool:
        m = await self.session.get(ProfileModel, profile_id)
        if m is None or m.deleted_at is not None:
            return False
        m.deleted_at = datetime.now(timezone.utc)
        m.updated_at = datetime.now(timezone.utc)
        await self.session.execute(
            delete(FamilyMembershipModel).where(FamilyMembershipModel.profile_id == profile_id)
        )
        await self.session.flush()
        return True

    async def get_health(self, profile_id: UUID) -> HealthDetail | None:
        stmt = select(HealthDetailModel).where(HealthDetailModel.profile_id == profile_id)
        r = await self.session.execute(stmt)
        m = r.scalar_one_or_none()
        return self._to_health(m) if m else None

    async def upsert_health(
        self,
        profile_id: UUID,
        *,
        blood_type: str | None = None,
        chronic_diseases: list[str] | None = None,
        allergies: list[str] | None = None,
        emergency_contact: str | None = None,
        notes: str | None = None,
    ) -> HealthDetail:
        stmt = select(HealthDetailModel).where(HealthDetailModel.profile_id == profile_id)
        r = await self.session.execute(stmt)
        m = r.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if m is None:
            m = HealthDetailModel(
                profile_id=profile_id,
                blood_type=blood_type,
                chronic_diseases=chronic_diseases,
                allergies=allergies,
                emergency_contact=emergency_contact,
                notes=notes,
                updated_at=now,
            )
            self.session.add(m)
        else:
            if blood_type is not None:
                m.blood_type = blood_type
            if chronic_diseases is not None:
                m.chronic_diseases = chronic_diseases
            if allergies is not None:
                m.allergies = allergies
            if emergency_contact is not None:
                m.emergency_contact = emergency_contact
            if notes is not None:
                m.notes = notes
            m.updated_at = now
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_health(m)

from __future__ import annotations

import secrets
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import and_, delete, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.family_port import FamilyRepositoryPort
from app.domain.services.family_permission import has_at_least

from app.domain.entities.family import (
    Family,
    FamilyInvite,
    FamilyInviteInboxItem,
    FamilyInviteStatus,
    FamilyMembership,
    FamilyPublicInviteStatus,
    FamilyRole,
    PublicInvitePreview,
)
from app.domain.entities.health_detail import EmergencyContactEntry, HealthDetail
from app.domain.entities.profile import Profile, ProfileStatus
from app.infrastructure.config.database.postgres.models.family_models import (
    FamilyInviteModel,
    FamilyMembershipModel,
    FamilyModel,
    FamilyPublicInviteModel,
)
from app.infrastructure.config.database.postgres.models.profile_models import (
    HealthDetailModel,
    ProfileModel,
)
from app.infrastructure.config.database.postgres.models.user_model import UserModel


def _parse_emergency_contacts_raw(raw: object) -> list[EmergencyContactEntry]:
    if not isinstance(raw, list):
        return []
    out: list[EmergencyContactEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            continue

        def _s(key: str) -> str | None:
            v = item.get(key)
            if v is None:
                return None
            if isinstance(v, str):
                t = v.strip()
                return t if t else None
            return str(v)

        out.append(EmergencyContactEntry(name=_s("name"), phone=_s("phone"), relationship=_s("relationship")))
    return out


def _dump_emergency_contacts(entries: list[EmergencyContactEntry]) -> list[dict[str, str | None]]:
    return [{"name": e.name, "phone": e.phone, "relationship": e.relationship} for e in entries]


class FamilyRepositoryPG(FamilyRepositoryPort):
    """PostgreSQL implementation for families / profiles / health_details."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _generate_unique_invite_code(self) -> str:
        for _ in range(20):
            code = secrets.token_urlsafe(12)[:16]
            stmt_f = select(FamilyModel.id).where(FamilyModel.invite_code == code).limit(1)
            stmt_p = select(FamilyPublicInviteModel.id).where(FamilyPublicInviteModel.invite_code == code).limit(1)
            rf = await self.session.execute(stmt_f)
            rp = await self.session.execute(stmt_p)
            if rf.scalar_one_or_none() is None and rp.scalar_one_or_none() is None:
                return code
        raise RuntimeError("Could not generate unique invite_code")

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

    @staticmethod
    def _profile_order_columns():
        return (
            ProfileModel.updated_at.desc(),
            ProfileModel.created_at.desc(),
            ProfileModel.id.desc(),
        )

    @staticmethod
    def _to_family(m: FamilyModel) -> Family:
        return Family(
            id=m.id,
            family_name=m.family_name,
            invite_code=m.invite_code,
            created_at=m.created_at,
            created_by=getattr(m, "created_by", None),
            address=getattr(m, "address", None),
            avatar_url=getattr(m, "avatar_url", None),
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
            relation_role=getattr(m, "relation_role", None),
        )

    @staticmethod
    def _to_invite(m: FamilyInviteModel) -> FamilyInvite:
        return FamilyInvite(
            id=m.id,
            family_id=m.family_id,
            role=FamilyRole(m.role),
            status=FamilyInviteStatus(m.status),
            invited_by=m.invited_by,
            invited_at=m.invited_at,
            phone_number=m.phone_number,
            user_id=m.user_id,
            relation_role=getattr(m, "relation_role", None),
            responded_at=m.responded_at,
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
            notes=m.notes,
            updated_at=m.updated_at,
            drug_allergies=list(m.drug_allergies) if m.drug_allergies is not None else None,
            food_allergies=list(m.food_allergies) if m.food_allergies is not None else None,
            emergency_contacts=_parse_emergency_contacts_raw(m.emergency_contacts),
        )

    async def get_family(self, family_id: UUID) -> Family | None:
        m = await self.session.get(FamilyModel, family_id)
        return self._to_family(m) if m else None

    async def find_family_by_invite_code(self, code: str) -> Family | None:
        """Resolve family only when a non-expired PENDING public invite exists for code."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(FamilyModel)
            .join(FamilyPublicInviteModel, FamilyPublicInviteModel.family_id == FamilyModel.id)
            .where(
                FamilyPublicInviteModel.invite_code == code.strip(),
                FamilyPublicInviteModel.status == FamilyPublicInviteStatus.PENDING.value,
                FamilyPublicInviteModel.expires_at > now,
            )
        )
        r = await self.session.execute(stmt)
        m = r.scalar_one_or_none()
        return self._to_family(m) if m else None

    async def create_pending_public_invite(
        self,
        *,
        family_id: UUID,
        invite_code: str,
        expires_at: datetime,
        created_by: UUID,
    ) -> None:
        row = FamilyPublicInviteModel(
            family_id=family_id,
            invite_code=invite_code.strip(),
            expires_at=expires_at,
            status=FamilyPublicInviteStatus.PENDING.value,
            created_by=created_by,
        )
        self.session.add(row)
        await self.session.flush()

    async def preview_public_invite(self, code: str) -> PublicInvitePreview | None:
        stmt = (
            select(FamilyPublicInviteModel, FamilyModel.family_name)
            .join(FamilyModel, FamilyModel.id == FamilyPublicInviteModel.family_id)
            .where(FamilyPublicInviteModel.invite_code == code.strip())
        )
        r = await self.session.execute(stmt)
        row = r.one_or_none()
        if row is None:
            return None
        inv, family_name = row[0], row[1]
        now = datetime.now(timezone.utc)
        status = FamilyPublicInviteStatus(inv.status)
        valid = status == FamilyPublicInviteStatus.PENDING and inv.expires_at > now
        return PublicInvitePreview(
            family_id=inv.family_id,
            family_name=family_name,
            invite_code=inv.invite_code,
            valid=valid,
            expires_at=inv.expires_at,
        )

    async def consume_pending_public_invite(self, code: str, consumed_by: UUID) -> Family | None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(FamilyPublicInviteModel)
            .where(
                FamilyPublicInviteModel.invite_code == code.strip(),
                FamilyPublicInviteModel.status == FamilyPublicInviteStatus.PENDING.value,
                FamilyPublicInviteModel.expires_at > now,
            )
            .values(
                status=FamilyPublicInviteStatus.CONSUMED.value,
                consumed_at=now,
                consumed_by=consumed_by,
            )
            .returning(FamilyPublicInviteModel.family_id)
        )
        res = await self.session.execute(stmt)
        fam_id = res.scalar_one_or_none()
        if fam_id is None:
            return None
        return await self.get_family(fam_id)

    async def revoke_pending_public_invite_for_family(self, family_id: UUID) -> None:
        await self.session.execute(
            update(FamilyPublicInviteModel)
            .where(
                FamilyPublicInviteModel.family_id == family_id,
                FamilyPublicInviteModel.status == FamilyPublicInviteStatus.PENDING.value,
            )
            .values(status=FamilyPublicInviteStatus.REVOKED.value)
        )
        await self.session.flush()

    async def update_family_name(self, family_id: UUID, name: str) -> Family | None:
        m = await self.session.get(FamilyModel, family_id)
        if m is None:
            return None
        m.family_name = name
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_family(m)

    async def rotate_invite(
        self,
        family_id: UUID,
        *,
        public_invite_expires_at: datetime,
        rotated_by: UUID,
    ) -> Family | None:
        m = await self.session.get(FamilyModel, family_id)
        if m is None:
            return None
        await self.revoke_pending_public_invite_for_family(family_id)
        new_code = await self._generate_unique_invite_code()
        m.invite_code = new_code
        await self.session.flush()
        await self.create_pending_public_invite(
            family_id=family_id,
            invite_code=new_code,
            expires_at=public_invite_expires_at,
            created_by=rotated_by,
        )
        await self.session.refresh(m)
        return self._to_family(m)

    async def list_families_for_user(self, user_id: UUID) -> list[Family]:
        stmt = (
            select(FamilyModel)
            .join(FamilyMembershipModel, FamilyMembershipModel.family_id == FamilyModel.id)
            .join(ProfileModel, ProfileModel.id == FamilyMembershipModel.profile_id)
            .where(
                self._is_actor_profile(user_id),
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
        r = await self.session.execute(stmt)
        row = r.scalars().first()
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

    async def transfer_family_owner(
        self,
        *,
        family_id: UUID,
        new_owner_membership_id: UUID,
        changed_by: UUID,
    ) -> FamilyMembership | None:
        _ = changed_by
        stmt = (
            select(FamilyMembershipModel)
            .where(FamilyMembershipModel.family_id == family_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        memberships = list(result.scalars().all())
        if not memberships:
            return None

        target = next((m for m in memberships if m.id == new_owner_membership_id), None)
        if target is None:
            return None

        for membership in memberships:
            if membership.id != target.id and membership.role == FamilyRole.OWNER.value:
                membership.role = FamilyRole.ADMIN.value
        target.role = FamilyRole.OWNER.value

        await self.session.flush()
        await self.session.refresh(target)
        return self._to_membership(target)

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
        address: str | None,
        avatar_url: str | None,
        creator_user_id: UUID,
        creator_full_name: str,
        public_invite_expires_at: datetime,
    ) -> tuple[Family, Profile, FamilyMembership]:
        invite = await self._generate_unique_invite_code()
        fam = FamilyModel(
            family_name=family_name.strip(),
            address=address,
            avatar_url=avatar_url,
            invite_code=invite,
            created_by=creator_user_id,
        )
        self.session.add(fam)
        await self.session.flush()

        await self.create_pending_public_invite(
            family_id=fam.id,
            invite_code=invite,
            expires_at=public_invite_expires_at,
            created_by=creator_user_id,
        )

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
            relation_role=None,
            added_by=creator_user_id,
        )
        self.session.add(mem)
        await self.session.flush()
        await self.session.refresh(fam)
        await self.session.refresh(prof)
        await self.session.refresh(mem)
        return self._to_family(fam), self._to_profile(prof), self._to_membership(mem)

    async def find_personal_profile_for_user(self, user_id: UUID) -> Profile | None:
        stmt = (
            select(ProfileModel)
            .where(
                ProfileModel.linked_user_id == user_id,
                ProfileModel.deleted_at.is_(None),
            )
            .order_by(*self._profile_order_columns())
            .limit(1)
        )
        r = await self.session.execute(stmt)
        m = r.scalar_one_or_none()
        return self._to_profile(m) if m else None

    async def list_linked_profiles_for_user(
        self,
        user_id: UUID,
        *,
        profile_scope: str = "all",
    ) -> list[Profile]:
        """`profile_scope`: all | without_family (không hàng family_memberships) | with_family (có ít nhất một)."""
        mem_exists = exists().where(FamilyMembershipModel.profile_id == ProfileModel.id)
        stmt = select(ProfileModel).where(
            ProfileModel.linked_user_id == user_id,
            ProfileModel.deleted_at.is_(None),
        )
        if profile_scope == "without_family":
            stmt = stmt.where(~mem_exists)
        elif profile_scope == "with_family":
            stmt = stmt.where(mem_exists)
        elif profile_scope != "all":
            raise ValueError(f"Invalid profile_scope: {profile_scope}")
        stmt = stmt.order_by(*self._profile_order_columns())
        r = await self.session.execute(stmt)
        return [self._to_profile(x) for x in r.scalars().all()]

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
        relation_role: str | None,
        added_by: UUID,
    ) -> FamilyMembership:
        mem = FamilyMembershipModel(
            family_id=family_id,
            profile_id=profile_id,
            role=role.value,
            relation_role=relation_role,
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

    async def list_family_ids_for_profile(self, profile_id: UUID) -> list[UUID]:
        stmt = select(FamilyMembershipModel.family_id).where(
            FamilyMembershipModel.profile_id == profile_id,
        )
        r = await self.session.execute(stmt)
        return list(r.scalars().all())

    async def user_can_edit_profile(self, profile_id: UUID, user_id: UUID) -> bool:
        p = await self.get_profile(profile_id)
        if p is None:
            return False
        if p.owner_user_id == user_id or p.linked_user_id == user_id:
            return True
        for fid in await self.list_family_ids_for_profile(profile_id):
            m = await self.get_user_membership_in_family(fid, user_id)
            if m is not None and has_at_least(m.role, FamilyRole.ADMIN):
                return True
        return False

    async def user_has_family_access_to_profile(self, profile_id: UUID, user_id: UUID) -> bool:
        for fid in await self.list_family_ids_for_profile(profile_id):
            m = await self.get_user_membership_in_family(fid, user_id)
            if m is not None:
                return True
        return False

    async def user_can_view_medical_records(self, profile_id: UUID, user_id: UUID) -> bool:
        p = await self.get_profile(profile_id)
        if p is None or p.deleted_at is not None:
            return False
        if p.owner_user_id == user_id or p.linked_user_id == user_id:
            return True
        return await self.user_has_family_access_to_profile(profile_id, user_id)

    async def user_can_write_medical_records(self, profile_id: UUID, user_id: UUID) -> bool:
        p = await self.get_profile(profile_id)
        if p is None or p.deleted_at is not None:
            return False
        if p.owner_user_id == user_id or p.linked_user_id == user_id:
            return True
        for fid in await self.list_family_ids_for_profile(profile_id):
            m = await self.get_user_membership_in_family(fid, user_id)
            if m is not None and has_at_least(m.role, FamilyRole.ADMIN):
                return True
        return False

    async def user_can_hard_delete_medical_record(self, profile_id: UUID, user_id: UUID) -> bool:
        for fid in await self.list_family_ids_for_profile(profile_id):
            m = await self.get_user_membership_in_family(fid, user_id)
            if m is not None and m.role in (FamilyRole.OWNER, FamilyRole.ADMIN):
                return True
        return False

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

    async def get_member_row(self, membership_id: UUID) -> tuple[FamilyMembership, Profile] | None:
        stmt = (
            select(FamilyMembershipModel, ProfileModel)
            .join(ProfileModel, ProfileModel.id == FamilyMembershipModel.profile_id)
            .where(
                FamilyMembershipModel.id == membership_id,
                ProfileModel.deleted_at.is_(None),
            )
        )
        r = await self.session.execute(stmt)
        row = r.one_or_none()
        if row is None:
            return None
        mem, prof = row
        return self._to_membership(mem), self._to_profile(prof)

    async def list_health_for_profiles(self, profile_ids: list[UUID]) -> dict[UUID, HealthDetail]:
        if not profile_ids:
            return {}
        stmt = select(HealthDetailModel).where(HealthDetailModel.profile_id.in_(profile_ids))
        result = await self.session.execute(stmt)
        out: dict[UUID, HealthDetail] = {}
        for row in result.scalars().all():
            out[row.profile_id] = self._to_health(row)
        return out

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
        prof = ProfileModel(
            owner_user_id=owner_user_id,
            linked_user_id=linked_user_id,
            full_name=full_name.strip(),
            dob=dob,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            address=address,
            avatar_url=avatar_url,
            status=(
                ProfileStatus.ACTIVE.value
                if linked_user_id is not None
                else ProfileStatus.SHADOW.value
            ),
        )
        self.session.add(prof)
        await self.session.flush()

        mem = FamilyMembershipModel(
            family_id=family_id,
            profile_id=prof.id,
            role=role.value,
            relation_role=relation_role,
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
        if m.status in (ProfileStatus.SHADOW.value, ProfileStatus.PENDING_LINK.value):
            m.status = ProfileStatus.ACTIVE.value
        m.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_profile(m)

    async def claim_profile_to_user(self, profile_id: UUID, user_id: UUID) -> Profile | None:
        m = await self.session.get(ProfileModel, profile_id)
        if m is None or m.deleted_at is not None:
            return None
        if m.linked_user_id is not None:
            return None
        m.owner_user_id = user_id
        m.linked_user_id = user_id
        if m.status in (ProfileStatus.SHADOW.value, ProfileStatus.PENDING_LINK.value):
            m.status = ProfileStatus.ACTIVE.value
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
        drug_allergies: list[str] | None = None,
        food_allergies: list[str] | None = None,
        emergency_contacts: list[EmergencyContactEntry] | None = None,
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
                drug_allergies=drug_allergies,
                food_allergies=food_allergies,
                emergency_contacts=_dump_emergency_contacts(
                    emergency_contacts if emergency_contacts is not None else []
                ),
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
            if drug_allergies is not None:
                m.drug_allergies = drug_allergies
            if food_allergies is not None:
                m.food_allergies = food_allergies
            if emergency_contacts is not None:
                m.emergency_contacts = _dump_emergency_contacts(emergency_contacts)
            if notes is not None:
                m.notes = notes
            m.updated_at = now
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_health(m)

    async def find_pending_invite(
        self,
        *,
        family_id: UUID,
        user_id: UUID | None,
        phone_number: str | None,
    ) -> FamilyInvite | None:
        conditions = [FamilyInviteModel.family_id == family_id, FamilyInviteModel.status == FamilyInviteStatus.PENDING.value]
        target_match: list = []
        if user_id is not None:
            target_match.append(FamilyInviteModel.user_id == user_id)
        if phone_number is not None:
            target_match.append(FamilyInviteModel.phone_number == phone_number)
        if not target_match:
            return None
        conditions.append(or_(*target_match))

        stmt = (
            select(FamilyInviteModel)
            .where(and_(*conditions))
            .order_by(FamilyInviteModel.invited_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_invite(model) if model else None

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
        invite = FamilyInviteModel(
            family_id=family_id,
            user_id=user_id,
            phone_number=phone_number,
            role=role.value,
            relation_role=relation_role,
            status=FamilyInviteStatus.PENDING.value,
            invited_by=invited_by,
        )
        self.session.add(invite)
        await self.session.flush()
        await self.session.refresh(invite)
        return self._to_invite(invite)

    async def get_family_invite(self, invite_id: UUID) -> FamilyInvite | None:
        model = await self.session.get(FamilyInviteModel, invite_id)
        return self._to_invite(model) if model else None

    async def update_family_invite_status(
        self,
        invite_id: UUID,
        status: FamilyInviteStatus,
    ) -> FamilyInvite | None:
        model = await self.session.get(FamilyInviteModel, invite_id)
        if model is None:
            return None
        model.status = status.value
        model.responded_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_invite(model)

    async def list_family_invites(self, family_id: UUID) -> list[FamilyInvite]:
        stmt = (
            select(FamilyInviteModel)
            .where(FamilyInviteModel.family_id == family_id)
            .order_by(FamilyInviteModel.invited_at.desc())
        )
        result = await self.session.execute(stmt)
        return [self._to_invite(row) for row in result.scalars().all()]

    async def _family_member_count(self, family_id: UUID) -> int:
        stmt = (
            select(func.count(FamilyMembershipModel.id))
            .join(ProfileModel, ProfileModel.id == FamilyMembershipModel.profile_id)
            .where(
                FamilyMembershipModel.family_id == family_id,
                ProfileModel.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def _inviter_name_and_role(
        self,
        *,
        family_id: UUID,
        inviter_user_id: UUID,
    ) -> tuple[str | None, FamilyRole | None]:
        stmt = (
            select(ProfileModel.full_name, FamilyMembershipModel.role)
            .join(FamilyMembershipModel, FamilyMembershipModel.profile_id == ProfileModel.id)
            .where(
                FamilyMembershipModel.family_id == family_id,
                self._is_actor_profile(inviter_user_id),
                ProfileModel.deleted_at.is_(None),
            )
            .order_by(self._role_rank_expr().desc(), FamilyMembershipModel.created_at.asc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None, None
        name, role = row
        return name, FamilyRole(role)

    async def list_invites_for_user_with_context(
        self,
        *,
        user_id: UUID,
        status: FamilyInviteStatus | None,
        offset: int,
        limit: int,
    ) -> list[FamilyInviteInboxItem]:
        user = await self.session.get(UserModel, user_id)
        phone_number = user.phone_number.strip() if user and user.phone_number else None

        predicate = [FamilyInviteModel.user_id == user_id]
        if phone_number:
            predicate.append(
                and_(
                    FamilyInviteModel.user_id.is_(None),
                    FamilyInviteModel.phone_number == phone_number,
                )
            )

        stmt = (
            select(FamilyInviteModel)
            .where(or_(*predicate))
            .order_by(FamilyInviteModel.invited_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(FamilyInviteModel.status == status.value)

        result = await self.session.execute(stmt)
        invites = [self._to_invite(row) for row in result.scalars().all()]

        out: list[FamilyInviteInboxItem] = []
        for invite in invites:
            fam = await self.session.get(FamilyModel, invite.family_id)
            if fam is None:
                continue
            member_count = await self._family_member_count(invite.family_id)
            inviter_name, inviter_role = await self._inviter_name_and_role(
                family_id=invite.family_id,
                inviter_user_id=invite.invited_by,
            )
            out.append(
                FamilyInviteInboxItem(
                    invite=invite,
                    family_name=fam.family_name,
                    family_avatar_url=fam.avatar_url,
                    family_member_count=member_count,
                    inviter_name=inviter_name,
                    inviter_role=inviter_role,
                )
            )
        return out

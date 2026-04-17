from __future__ import annotations

from datetime import date
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.vaccination_port import VaccinationRepositoryPort
from app.domain.entities.vaccination import VaccinationDose, VaccinationRecommendation, UserVaccination
from app.infrastructure.config.database.postgres.models.vaccination_models import (
    UserVaccinationModel,
    VaccinationDoseModel,
    VaccinationRecommendationModel,
)


class VaccinationRepositoryPG(VaccinationRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_recommendation(model: VaccinationRecommendationModel) -> VaccinationRecommendation:
        return VaccinationRecommendation(
            id=model.id,
            code=model.code,
            name=model.name,
            disease_name=model.disease_name,
            total_doses=model.total_doses,
            notes=model.notes,
            created_at=model.created_at,
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

    async def list_recommendations(self) -> list[VaccinationRecommendation]:
        stmt = select(VaccinationRecommendationModel).order_by(
            VaccinationRecommendationModel.name
        )
        r = await self.session.execute(stmt)
        return [self._to_recommendation(row) for row in r.scalars().all()]

    async def get_recommendation(self, recommendation_id: UUID) -> VaccinationRecommendation | None:
        model = await self.session.get(VaccinationRecommendationModel, recommendation_id)
        return self._to_recommendation(model) if model else None

    async def list_user_vaccinations_for_profile(
        self, profile_id: UUID
    ) -> list[tuple[UserVaccination, VaccinationRecommendation]]:
        stmt = (
            select(UserVaccinationModel, VaccinationRecommendationModel)
            .join(
                VaccinationRecommendationModel,
                UserVaccinationModel.recommendation_id == VaccinationRecommendationModel.id,
            )
            .where(UserVaccinationModel.profile_id == profile_id)
            .order_by(VaccinationRecommendationModel.name)
        )
        r = await self.session.execute(stmt)
        return [(self._to_user_vaccination(uv), self._to_recommendation(rec)) for uv, rec in r.all()]

    async def get_user_vaccination_for_profile(
        self, profile_id: UUID, user_vaccination_id: UUID
    ) -> tuple[UserVaccination, VaccinationRecommendation] | None:
        stmt = (
            select(UserVaccinationModel, VaccinationRecommendationModel)
            .join(
                VaccinationRecommendationModel,
                UserVaccinationModel.recommendation_id == VaccinationRecommendationModel.id,
            )
            .where(
                UserVaccinationModel.id == user_vaccination_id,
                UserVaccinationModel.profile_id == profile_id,
            )
        )
        r = await self.session.execute(stmt)
        row = r.one_or_none()
        if row is None:
            return None
        uv, rec = row
        return self._to_user_vaccination(uv), self._to_recommendation(rec)

    async def get_user_vaccination_by_id(
        self,
        user_vaccination_id: UUID,
    ) -> tuple[UserVaccination, VaccinationRecommendation] | None:
        stmt = (
            select(UserVaccinationModel, VaccinationRecommendationModel)
            .join(
                VaccinationRecommendationModel,
                UserVaccinationModel.recommendation_id == VaccinationRecommendationModel.id,
            )
            .where(UserVaccinationModel.id == user_vaccination_id)
        )
        r = await self.session.execute(stmt)
        row = r.one_or_none()
        if row is None:
            return None
        uv, rec = row
        return self._to_user_vaccination(uv), self._to_recommendation(rec)

    async def create_user_vaccination(
        self,
        *,
        profile_id: UUID,
        recommendation_id: UUID,
        user_id: UUID | None,
        status: str | None,
    ) -> UserVaccination:
        m = UserVaccinationModel(
            profile_id=profile_id,
            recommendation_id=recommendation_id,
            user_id=user_id,
            status=status,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_user_vaccination(m)

    async def update_user_vaccination_status(
        self, user_vaccination_id: UUID, status: str | None
    ) -> UserVaccination | None:
        m = await self.session.get(UserVaccinationModel, user_vaccination_id)
        if m is None:
            return None
        m.status = status
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_user_vaccination(m)

    async def count_administered_doses(self, user_vaccination_id: UUID) -> int:
        stmt = (
            select(sa.func.count())
            .select_from(VaccinationDoseModel)
            .where(
                VaccinationDoseModel.user_vaccination_id == user_vaccination_id,
                VaccinationDoseModel.administered_at.isnot(None),
            )
        )
        r = await self.session.execute(stmt)
        return int(r.scalar_one() or 0)

    async def list_doses(self, user_vaccination_id: UUID) -> list[VaccinationDose]:
        stmt = (
            select(VaccinationDoseModel)
            .where(VaccinationDoseModel.user_vaccination_id == user_vaccination_id)
            .order_by(VaccinationDoseModel.dose_index)
        )
        r = await self.session.execute(stmt)
        return [self._to_dose(row) for row in r.scalars().all()]

    async def get_dose_by_id(self, dose_id: UUID) -> VaccinationDose | None:
        model = await self.session.get(VaccinationDoseModel, dose_id)
        return self._to_dose(model) if model else None

    async def dose_index_exists(self, user_vaccination_id: UUID, dose_index: int) -> bool:
        stmt = (
            select(VaccinationDoseModel.id)
            .where(
                VaccinationDoseModel.user_vaccination_id == user_vaccination_id,
                VaccinationDoseModel.dose_index == dose_index,
            )
            .limit(1)
        )
        r = await self.session.execute(stmt)
        return r.scalar_one_or_none() is not None

    async def create_dose(
        self,
        *,
        user_vaccination_id: UUID,
        dose_index: int,
        administered_at: date | None,
        scheduled_at: date | None,
        location: str | None,
        reaction: str | None,
        proof_url: str | None,
        reminder_enabled: bool,
        remind_before_value: int | None,
        remind_before_unit: str | None,
    ) -> VaccinationDose:
        m = VaccinationDoseModel(
            user_vaccination_id=user_vaccination_id,
            dose_index=dose_index,
            administered_at=administered_at,
            scheduled_at=scheduled_at,
            location=location,
            reaction=reaction,
            proof_url=proof_url,
            reminder_enabled=reminder_enabled,
            remind_before_value=remind_before_value,
            remind_before_unit=remind_before_unit,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_dose(m)

    async def update_dose(
        self,
        dose_id: UUID,
        *,
        administered_at: date | None,
        scheduled_at: date | None,
        location: str | None,
        reaction: str | None,
        proof_url: str | None,
        reminder_enabled: bool,
        remind_before_value: int | None,
        remind_before_unit: str | None,
    ) -> VaccinationDose | None:
        dose = await self.session.get(VaccinationDoseModel, dose_id)
        if dose is None:
            return None
        dose.administered_at = administered_at
        dose.scheduled_at = scheduled_at
        dose.location = location
        dose.reaction = reaction
        dose.proof_url = proof_url
        dose.reminder_enabled = reminder_enabled
        dose.remind_before_value = remind_before_value
        dose.remind_before_unit = remind_before_unit
        await self.session.flush()
        await self.session.refresh(dose)
        return self._to_dose(dose)

    async def delete_dose(self, dose_id: UUID) -> bool:
        dose = await self.session.get(VaccinationDoseModel, dose_id)
        if dose is None:
            return False
        await self.session.delete(dose)
        await self.session.flush()
        return True

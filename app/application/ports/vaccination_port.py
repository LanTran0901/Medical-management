from __future__ import annotations

from datetime import date
from uuid import UUID

from app.domain.entities.vaccination import VaccinationDose, VaccinationRecommendation, UserVaccination


class VaccinationRepositoryPort:
    async def list_recommendations(self) -> list[VaccinationRecommendation]:
        raise NotImplementedError

    async def get_recommendation(self, recommendation_id: UUID) -> VaccinationRecommendation | None:
        raise NotImplementedError

    async def list_user_vaccinations_for_profile(
        self,
        profile_id: UUID,
    ) -> list[tuple[UserVaccination, VaccinationRecommendation]]:
        raise NotImplementedError

    async def get_user_vaccination_for_profile(
        self,
        profile_id: UUID,
        user_vaccination_id: UUID,
    ) -> tuple[UserVaccination, VaccinationRecommendation] | None:
        raise NotImplementedError

    async def get_user_vaccination_by_id(
        self,
        user_vaccination_id: UUID,
    ) -> tuple[UserVaccination, VaccinationRecommendation] | None:
        raise NotImplementedError

    async def create_user_vaccination(
        self,
        *,
        profile_id: UUID,
        recommendation_id: UUID,
        user_id: UUID | None,
        status: str | None,
    ) -> UserVaccination:
        raise NotImplementedError

    async def update_user_vaccination_status(
        self,
        user_vaccination_id: UUID,
        status: str | None,
    ) -> UserVaccination | None:
        raise NotImplementedError

    async def count_administered_doses(self, user_vaccination_id: UUID) -> int:
        raise NotImplementedError

    async def list_doses(self, user_vaccination_id: UUID) -> list[VaccinationDose]:
        raise NotImplementedError

    async def get_dose_by_id(self, dose_id: UUID) -> VaccinationDose | None:
        raise NotImplementedError

    async def dose_index_exists(self, user_vaccination_id: UUID, dose_index: int) -> bool:
        raise NotImplementedError

    async def create_dose(
        self,
        *,
        user_vaccination_id: UUID,
        dose_index: int,
        administered_at: date | None,
        scheduled_at: date | None,
        location: str | None,
        proof_url: str | None,
    ) -> VaccinationDose:
        raise NotImplementedError

    async def update_dose(
        self,
        dose_id: UUID,
        *,
        administered_at: date | None,
        scheduled_at: date | None,
        location: str | None,
        proof_url: str | None,
    ) -> VaccinationDose | None:
        raise NotImplementedError

    async def delete_dose(self, dose_id: UUID) -> bool:
        raise NotImplementedError

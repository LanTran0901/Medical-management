from __future__ import annotations

from datetime import date
from typing import cast
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.application.ports.vaccination_port import VaccinationRepositoryPort
from app.application.dtos.vaccination_dto import (
    CreateVaccinationDoseRequest,
    DoseStatusLiteral,
    PatchUserVaccinationRequest,
    PatchVaccinationDoseRequest,
    SubscribeUserVaccinationRequest,
    UserVaccinationResponse,
    VaccinationDoseResponse,
    VaccinationRecommendationResponse,
)
from app.application.family_errors import ConflictError, NotFoundError
from app.application.usecases.access_control_usecases import AccessControlService
from app.domain.entities.vaccination import (
    UserVaccination,
    VaccinationDose,
    VaccinationRecommendation,
)


def _derive_dose_fields(
    d: VaccinationDose,
    today: date,
) -> tuple[str, bool]:
    """Returns (dose_status, is_overdue)."""
    if d.administered_at is not None:
        return "ADMINISTERED", False
    if d.scheduled_at is not None:
        if d.scheduled_at < today:
            return "OVERDUE", True
        return "SCHEDULED", False
    return "UNSCHEDULED", False


class VaccinationService:
    def __init__(
        self,
        vaccination: VaccinationRepositoryPort,
        access: AccessControlService,
    ) -> None:
        self._vac = vaccination
        self._access = access

    def _to_rec_response(self, m: VaccinationRecommendation) -> VaccinationRecommendationResponse:
        return VaccinationRecommendationResponse(
            id=m.id,
            code=m.code,
            name=m.name,
            total_doses=m.total_doses,
            created_at=m.created_at,
        )

    def _to_dose_response(self, d: VaccinationDose, today: date) -> VaccinationDoseResponse:
        status, overdue = _derive_dose_fields(d, today)
        return VaccinationDoseResponse(
            id=d.id,
            user_vaccination_id=d.user_vaccination_id,
            dose_index=d.dose_index,
            administered_at=d.administered_at,
            scheduled_at=d.scheduled_at,
            location=d.location,
            proof_url=d.proof_url,
            dose_status=cast(DoseStatusLiteral, status),
            is_overdue=overdue,
        )

    async def _to_uv_response(
        self,
        uv: UserVaccination,
        rec: VaccinationRecommendation,
    ) -> UserVaccinationResponse:
        count = await self._vac.count_administered_doses(uv.id)
        return UserVaccinationResponse(
            id=uv.id,
            profile_id=uv.profile_id,
            recommendation_id=uv.recommendation_id,
            recommendation_name=rec.name,
            recommendation_total_doses=rec.total_doses,
            user_id=uv.user_id,
            status=uv.status,
            created_at=uv.created_at,
            doses_administered_count=count,
        )

    async def list_recommendations(self) -> list[VaccinationRecommendationResponse]:
        rows = await self._vac.list_recommendations()
        return [self._to_rec_response(m) for m in rows]

    async def list_profile_vaccinations(
        self, profile_id: UUID, user_id: UUID
    ) -> list[UserVaccinationResponse]:
        await self._access.require_medical_profile_view(profile_id, user_id)
        pairs = await self._vac.list_user_vaccinations_for_profile(profile_id)
        out: list[UserVaccinationResponse] = []
        for uv, rec in pairs:
            out.append(await self._to_uv_response(uv, rec))
        return out

    async def subscribe(
        self,
        profile_id: UUID,
        user_id: UUID,
        body: SubscribeUserVaccinationRequest,
    ) -> UserVaccinationResponse:
        await self._access.require_medical_profile_write(profile_id, user_id)
        rec = await self._vac.get_recommendation(body.recommendation_id)
        if rec is None:
            raise NotFoundError("Vaccination recommendation not found")
        try:
            uv = await self._vac.create_user_vaccination(
                profile_id=profile_id,
                recommendation_id=body.recommendation_id,
                user_id=user_id,
                status="in_progress",
            )
        except IntegrityError as e:
            raise ConflictError(
                "This vaccine is already subscribed for this profile."
            ) from e
        return await self._to_uv_response(uv, rec)

    async def get_user_vaccination(
        self, profile_id: UUID, user_vaccination_id: UUID, user_id: UUID
    ) -> UserVaccinationResponse:
        context = await self._access.require_user_vaccination_view(user_vaccination_id, user_id)
        if context.user_vaccination.profile_id != profile_id:
            raise NotFoundError("User vaccination not found")
        pair = await self._vac.get_user_vaccination_by_id(user_vaccination_id)
        if pair is None:
            raise NotFoundError("User vaccination not found")
        uv, rec = pair
        return await self._to_uv_response(uv, rec)

    async def get_user_vaccination_by_id(
        self,
        user_vaccination_id: UUID,
        user_id: UUID,
    ) -> UserVaccinationResponse:
        await self._access.require_user_vaccination_view(user_vaccination_id, user_id)
        pair = await self._vac.get_user_vaccination_by_id(user_vaccination_id)
        if pair is None:
            raise NotFoundError("User vaccination not found")
        uv, rec = pair
        return await self._to_uv_response(uv, rec)

    async def patch_user_vaccination(
        self,
        profile_id: UUID,
        user_vaccination_id: UUID,
        user_id: UUID,
        body: PatchUserVaccinationRequest,
    ) -> UserVaccinationResponse:
        context = await self._access.require_user_vaccination_write(user_vaccination_id, user_id)
        if context.user_vaccination.profile_id != profile_id:
            raise NotFoundError("User vaccination not found")
        pair = await self._vac.get_user_vaccination_by_id(user_vaccination_id)
        if pair is None:
            raise NotFoundError("User vaccination not found")
        uv, rec = pair
        patch = body.model_dump(exclude_unset=True)
        if "status" in patch:
            updated = await self._vac.update_user_vaccination_status(
                user_vaccination_id, patch["status"]
            )
            if updated is None:
                raise NotFoundError("User vaccination not found")
            uv = updated
        return await self._to_uv_response(uv, rec)

    async def patch_user_vaccination_by_id(
        self,
        user_vaccination_id: UUID,
        user_id: UUID,
        body: PatchUserVaccinationRequest,
    ) -> UserVaccinationResponse:
        await self._access.require_user_vaccination_write(user_vaccination_id, user_id)
        pair = await self._vac.get_user_vaccination_by_id(user_vaccination_id)
        if pair is None:
            raise NotFoundError("User vaccination not found")
        uv, rec = pair
        patch = body.model_dump(exclude_unset=True)
        if "status" in patch:
            updated = await self._vac.update_user_vaccination_status(
                user_vaccination_id, patch["status"]
            )
            if updated is None:
                raise NotFoundError("User vaccination not found")
            uv = updated
        return await self._to_uv_response(uv, rec)

    async def list_doses(
        self, profile_id: UUID, user_vaccination_id: UUID, user_id: UUID
    ) -> list[VaccinationDoseResponse]:
        context = await self._access.require_user_vaccination_view(user_vaccination_id, user_id)
        if context.user_vaccination.profile_id != profile_id:
            raise NotFoundError("User vaccination not found")
        today = date.today()
        rows = await self._vac.list_doses(user_vaccination_id)
        return [self._to_dose_response(d, today) for d in rows]

    async def list_doses_by_user_vaccination(
        self,
        user_vaccination_id: UUID,
        user_id: UUID,
    ) -> list[VaccinationDoseResponse]:
        await self._access.require_user_vaccination_view(user_vaccination_id, user_id)
        rows = await self._vac.list_doses(user_vaccination_id)
        today = date.today()
        return [self._to_dose_response(d, today) for d in rows]

    async def create_dose(
        self,
        profile_id: UUID,
        user_vaccination_id: UUID,
        user_id: UUID,
        body: CreateVaccinationDoseRequest,
    ) -> VaccinationDoseResponse:
        context = await self._access.require_user_vaccination_write(user_vaccination_id, user_id)
        if context.user_vaccination.profile_id != profile_id:
            raise NotFoundError("User vaccination not found")
        if await self._vac.dose_index_exists(user_vaccination_id, body.dose_index):
            raise ConflictError(f"Dose index {body.dose_index} already exists for this subscription.")
        d = await self._vac.create_dose(
            user_vaccination_id=user_vaccination_id,
            dose_index=body.dose_index,
            administered_at=body.administered_at,
            scheduled_at=body.scheduled_at,
            location=body.location,
            proof_url=body.proof_url,
        )
        return self._to_dose_response(d, date.today())

    async def create_dose_by_user_vaccination(
        self,
        user_vaccination_id: UUID,
        user_id: UUID,
        body: CreateVaccinationDoseRequest,
    ) -> VaccinationDoseResponse:
        await self._access.require_user_vaccination_write(user_vaccination_id, user_id)
        if await self._vac.dose_index_exists(user_vaccination_id, body.dose_index):
            raise ConflictError(f"Dose index {body.dose_index} already exists for this subscription.")
        d = await self._vac.create_dose(
            user_vaccination_id=user_vaccination_id,
            dose_index=body.dose_index,
            administered_at=body.administered_at,
            scheduled_at=body.scheduled_at,
            location=body.location,
            proof_url=body.proof_url,
        )
        return self._to_dose_response(d, date.today())

    async def patch_dose(
        self,
        profile_id: UUID,
        user_vaccination_id: UUID,
        dose_id: UUID,
        user_id: UUID,
        body: PatchVaccinationDoseRequest,
    ) -> VaccinationDoseResponse:
        context = await self._access.require_vaccination_dose_write(dose_id, user_id)
        if context.user_vaccination.profile_id != profile_id or context.dose.user_vaccination_id != user_vaccination_id:
            raise NotFoundError("Dose not found")
        patch = body.model_dump(exclude_unset=True)
        administered_at = context.dose.administered_at
        scheduled_at = context.dose.scheduled_at
        location = context.dose.location
        proof_url = context.dose.proof_url
        if "administered_at" in patch:
            administered_at = patch["administered_at"]
        if "scheduled_at" in patch:
            scheduled_at = patch["scheduled_at"]
        if "location" in patch:
            location = patch["location"]
        if "proof_url" in patch:
            proof_url = patch["proof_url"]
        d = await self._vac.update_dose(
            dose_id,
            administered_at=administered_at,
            scheduled_at=scheduled_at,
            location=location,
            proof_url=proof_url,
        )
        if d is None:
            raise NotFoundError("Dose not found")
        return self._to_dose_response(d, date.today())

    async def patch_dose_by_id(
        self,
        dose_id: UUID,
        user_id: UUID,
        body: PatchVaccinationDoseRequest,
    ) -> VaccinationDoseResponse:
        context = await self._access.require_vaccination_dose_write(dose_id, user_id)
        patch = body.model_dump(exclude_unset=True)
        administered_at = context.dose.administered_at
        scheduled_at = context.dose.scheduled_at
        location = context.dose.location
        proof_url = context.dose.proof_url
        if "administered_at" in patch:
            administered_at = patch["administered_at"]
        if "scheduled_at" in patch:
            scheduled_at = patch["scheduled_at"]
        if "location" in patch:
            location = patch["location"]
        if "proof_url" in patch:
            proof_url = patch["proof_url"]
        d = await self._vac.update_dose(
            dose_id,
            administered_at=administered_at,
            scheduled_at=scheduled_at,
            location=location,
            proof_url=proof_url,
        )
        if d is None:
            raise NotFoundError("Dose not found")
        return self._to_dose_response(d, date.today())

    async def get_dose(
        self,
        profile_id: UUID,
        user_vaccination_id: UUID,
        dose_id: UUID,
        user_id: UUID,
    ) -> VaccinationDoseResponse:
        context = await self._access.require_vaccination_dose_view(dose_id, user_id)
        if context.user_vaccination.profile_id != profile_id or context.dose.user_vaccination_id != user_vaccination_id:
            raise NotFoundError("Dose not found")
        return self._to_dose_response(context.dose, date.today())

    async def get_dose_by_id(
        self,
        dose_id: UUID,
        user_id: UUID,
    ) -> VaccinationDoseResponse:
        context = await self._access.require_vaccination_dose_view(dose_id, user_id)
        return self._to_dose_response(context.dose, date.today())

    async def delete_dose_by_id(
        self,
        dose_id: UUID,
        user_id: UUID,
    ) -> None:
        await self._access.require_vaccination_dose_write(dose_id, user_id)
        ok = await self._vac.delete_dose(dose_id)
        if not ok:
            raise NotFoundError("Dose not found")

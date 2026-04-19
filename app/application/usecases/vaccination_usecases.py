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
    UserVaccinationWithDosesResponse,
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
from app.domain.remind_before import RemindBeforeUnit


def _finalize_dose_reminder(
    reminder_enabled: bool,
    value: int | None,
    unit: str | None,
) -> tuple[int | None, str | None]:
    if not reminder_enabled:
        return None, None
    if value is None or unit is None:
        raise ConflictError(
            "remind_before_value and remind_before_unit are required when reminder_enabled is true"
        )
    if value < 1:
        raise ConflictError("remind_before_value must be at least 1")
    try:
        u = RemindBeforeUnit(str(unit).upper())
    except ValueError as exc:
        raise ConflictError(f"Invalid remind_before_unit: {unit!r}") from exc
    return value, u.value


def _patch_remind_before_unit_to_str(raw: object) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, RemindBeforeUnit):
        return raw.value
    return str(raw)


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
            disease_name=m.disease_name,
            total_doses=m.total_doses,
            notes=m.notes,
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
            reaction=d.reaction,
            proof_url=d.proof_url,
            reminder_enabled=d.reminder_enabled,
            remind_before_value=d.remind_before_value,
            remind_before_unit=RemindBeforeUnit(d.remind_before_unit) if d.remind_before_unit else None,
            dose_status=cast(DoseStatusLiteral, status),
            is_overdue=overdue,
        )

    def _to_uv_response_with_count(
        self,
        uv: UserVaccination,
        rec: VaccinationRecommendation,
        doses_administered_count: int,
    ) -> UserVaccinationResponse:
        return UserVaccinationResponse(
            id=uv.id,
            profile_id=uv.profile_id,
            recommendation_id=uv.recommendation_id,
            recommendation_name=rec.name,
            recommendation_total_doses=rec.total_doses,
            user_id=uv.user_id,
            status=uv.status,
            created_at=uv.created_at,
            doses_administered_count=doses_administered_count,
        )

    async def _to_uv_response(
        self,
        uv: UserVaccination,
        rec: VaccinationRecommendation,
    ) -> UserVaccinationResponse:
        count = await self._vac.count_administered_doses(uv.id)
        return self._to_uv_response_with_count(uv, rec, count)

    async def list_recommendations(self) -> list[VaccinationRecommendationResponse]:
        rows = await self._vac.list_recommendations()
        return [self._to_rec_response(m) for m in rows]

    async def list_profile_vaccinations(
        self,
        profile_id: UUID,
        user_id: UUID,
        *,
        skip_access_check: bool = False,
    ) -> list[UserVaccinationResponse]:
        if not skip_access_check:
            await self._access.require_medical_profile_view(profile_id, user_id)
        pairs = await self._vac.list_user_vaccinations_for_profile(profile_id)
        if not pairs:
            return []
        uv_ids = [uv.id for uv, _ in pairs]
        counts = await self._vac.count_administered_doses_for_uv_ids(uv_ids)
        return [
            self._to_uv_response_with_count(uv, rec, counts.get(uv.id, 0)) for uv, rec in pairs
        ]

    async def list_profile_vaccinations_with_doses(
        self,
        profile_id: UUID,
        user_id: UUID,
        *,
        skip_access_check: bool = False,
    ) -> list[UserVaccinationWithDosesResponse]:
        if not skip_access_check:
            await self._access.require_medical_profile_view(profile_id, user_id)
        pairs = await self._vac.list_user_vaccinations_for_profile(profile_id)
        if not pairs:
            return []
        today = date.today()
        uv_ids = [uv.id for uv, _ in pairs]
        counts = await self._vac.count_administered_doses_for_uv_ids(uv_ids)
        doses_by_uv = await self._vac.list_doses_for_user_vaccination_ids(uv_ids)
        out: list[UserVaccinationWithDosesResponse] = []
        for uv, rec in pairs:
            base = self._to_uv_response_with_count(uv, rec, counts.get(uv.id, 0))
            dose_rows = doses_by_uv.get(uv.id, [])
            doses = [self._to_dose_response(d, today) for d in dose_rows]
            out.append(UserVaccinationWithDosesResponse(**{**base.model_dump(), "doses": doses}))
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
        rb_value, rb_unit = _finalize_dose_reminder(
            body.reminder_enabled,
            body.remind_before_value,
            body.remind_before_unit.value if body.remind_before_unit else None,
        )
        d = await self._vac.create_dose(
            user_vaccination_id=user_vaccination_id,
            dose_index=body.dose_index,
            administered_at=body.administered_at,
            scheduled_at=body.scheduled_at,
            location=body.location,
            reaction=body.reaction,
            proof_url=body.proof_url,
            reminder_enabled=body.reminder_enabled,
            remind_before_value=rb_value,
            remind_before_unit=rb_unit,
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
        rb_value, rb_unit = _finalize_dose_reminder(
            body.reminder_enabled,
            body.remind_before_value,
            body.remind_before_unit.value if body.remind_before_unit else None,
        )
        d = await self._vac.create_dose(
            user_vaccination_id=user_vaccination_id,
            dose_index=body.dose_index,
            administered_at=body.administered_at,
            scheduled_at=body.scheduled_at,
            location=body.location,
            reaction=body.reaction,
            proof_url=body.proof_url,
            reminder_enabled=body.reminder_enabled,
            remind_before_value=rb_value,
            remind_before_unit=rb_unit,
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
        reaction = context.dose.reaction
        proof_url = context.dose.proof_url
        reminder_enabled = context.dose.reminder_enabled
        remind_before_value = context.dose.remind_before_value
        remind_before_unit = context.dose.remind_before_unit
        if "administered_at" in patch:
            administered_at = patch["administered_at"]
        if "scheduled_at" in patch:
            scheduled_at = patch["scheduled_at"]
        if "location" in patch:
            location = patch["location"]
        if "reaction" in patch:
            reaction = patch["reaction"]
        if "proof_url" in patch:
            proof_url = patch["proof_url"]
        if "reminder_enabled" in patch:
            reminder_enabled = patch["reminder_enabled"]
        if "remind_before_value" in patch:
            remind_before_value = patch["remind_before_value"]
        if "remind_before_unit" in patch:
            remind_before_unit = _patch_remind_before_unit_to_str(patch["remind_before_unit"])
        rb_value, rb_unit = _finalize_dose_reminder(reminder_enabled, remind_before_value, remind_before_unit)
        d = await self._vac.update_dose(
            dose_id,
            administered_at=administered_at,
            scheduled_at=scheduled_at,
            location=location,
            reaction=reaction,
            proof_url=proof_url,
            reminder_enabled=reminder_enabled,
            remind_before_value=rb_value,
            remind_before_unit=rb_unit,
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
        reaction = context.dose.reaction
        proof_url = context.dose.proof_url
        reminder_enabled = context.dose.reminder_enabled
        remind_before_value = context.dose.remind_before_value
        remind_before_unit = context.dose.remind_before_unit
        if "administered_at" in patch:
            administered_at = patch["administered_at"]
        if "scheduled_at" in patch:
            scheduled_at = patch["scheduled_at"]
        if "location" in patch:
            location = patch["location"]
        if "reaction" in patch:
            reaction = patch["reaction"]
        if "proof_url" in patch:
            proof_url = patch["proof_url"]
        if "reminder_enabled" in patch:
            reminder_enabled = patch["reminder_enabled"]
        if "remind_before_value" in patch:
            remind_before_value = patch["remind_before_value"]
        if "remind_before_unit" in patch:
            remind_before_unit = _patch_remind_before_unit_to_str(patch["remind_before_unit"])
        rb_value, rb_unit = _finalize_dose_reminder(reminder_enabled, remind_before_value, remind_before_unit)
        d = await self._vac.update_dose(
            dose_id,
            administered_at=administered_at,
            scheduled_at=scheduled_at,
            location=location,
            reaction=reaction,
            proof_url=proof_url,
            reminder_enabled=reminder_enabled,
            remind_before_value=rb_value,
            remind_before_unit=rb_unit,
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

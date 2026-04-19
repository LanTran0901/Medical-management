from __future__ import annotations

from uuid import UUID

from app.application.dtos.health_metric_reading_dto import (
    CreateHealthMetricReadingRequest,
    PatchHealthMetricReadingRequest,
)
from app.application.dtos.user_dto import HealthMetricReadingResponse
from app.application.family_errors import NotFoundError
from app.application.ports.health_metric_reading_port import HealthMetricReadingRepositoryPort
from app.application.usecases.access_control_usecases import AccessControlService
from app.domain.entities.health_metric_reading import HealthMetricReading


class HealthMetricReadingsService:
    def __init__(
        self,
        repo: HealthMetricReadingRepositoryPort,
        access: AccessControlService,
    ) -> None:
        self._repo = repo
        self._access = access

    @staticmethod
    def _to_response(m: HealthMetricReading) -> HealthMetricReadingResponse:
        return HealthMetricReadingResponse(
            id=m.id,
            profile_id=m.profile_id,
            metric_type=m.metric_type,
            measured_at=m.measured_at,
            systolic=m.systolic,
            diastolic=m.diastolic,
            heart_rate=m.heart_rate,
            weight_kg=m.weight_kg,
            glucose_mmol_l=m.glucose_mmol_l,
            status=m.status,
            notes=m.notes,
            created_at=m.created_at,
        )

    async def list_for_profile(
        self,
        profile_id: UUID,
        user_id: UUID,
        *,
        skip_access_check: bool = False,
    ) -> list[HealthMetricReadingResponse]:
        if not skip_access_check:
            await self._access.require_profile_read(profile_id, user_id)
        rows = await self._repo.list_for_profile(profile_id)
        return [self._to_response(m) for m in rows]

    async def list_for_profiles(
        self,
        profile_ids: list[UUID],
        user_id: UUID,
        *,
        skip_access_check: bool = False,
    ) -> dict[UUID, list[HealthMetricReadingResponse]]:
        if not profile_ids:
            return {}
        if not skip_access_check:
            for pid in profile_ids:
                await self._access.require_profile_read(pid, user_id)
        rows_by = await self._repo.list_for_profiles(profile_ids)
        return {
            pid: [self._to_response(m) for m in rows]
            for pid, rows in rows_by.items()
        }

    async def create(
        self,
        profile_id: UUID,
        user_id: UUID,
        body: CreateHealthMetricReadingRequest,
    ) -> HealthMetricReadingResponse:
        await self._access.require_medical_profile_write(profile_id, user_id)
        row = await self._repo.create(
            profile_id=profile_id,
            metric_type=body.metric_type,
            measured_at=body.measured_at,
            systolic=body.systolic,
            diastolic=body.diastolic,
            heart_rate=body.heart_rate,
            weight_kg=body.weight_kg,
            glucose_mmol_l=body.glucose_mmol_l,
            status=body.status,
            notes=body.notes,
        )
        return self._to_response(row)

    async def get_by_id(self, reading_id: UUID, user_id: UUID) -> HealthMetricReadingResponse:
        row = await self._repo.get_by_id(reading_id)
        if row is None:
            raise NotFoundError("Health metric reading not found")
        await self._access.require_medical_profile_view(row.profile_id, user_id)
        return self._to_response(row)

    async def patch(
        self,
        reading_id: UUID,
        user_id: UUID,
        body: PatchHealthMetricReadingRequest,
    ) -> HealthMetricReadingResponse:
        row = await self._repo.get_by_id(reading_id)
        if row is None:
            raise NotFoundError("Health metric reading not found")
        await self._access.require_medical_profile_write(row.profile_id, user_id)
        data = body.model_dump(exclude_unset=True)
        if not data:
            return self._to_response(row)
        updated = await self._repo.update(reading_id, data)
        if updated is None:
            raise NotFoundError("Health metric reading not found")
        return self._to_response(updated)

    async def delete(self, reading_id: UUID, user_id: UUID) -> None:
        row = await self._repo.get_by_id(reading_id)
        if row is None:
            raise NotFoundError("Health metric reading not found")
        await self._access.require_medical_profile_write(row.profile_id, user_id)
        ok = await self._repo.soft_delete(reading_id)
        if not ok:
            raise NotFoundError("Health metric reading not found")

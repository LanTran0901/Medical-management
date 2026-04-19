from __future__ import annotations

from uuid import UUID

from app.application.dtos.user_dto import HealthMetricReadingResponse
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

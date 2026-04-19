from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.health_metric_reading_port import HealthMetricReadingRepositoryPort
from app.domain.entities.health_metric_reading import HealthMetricReading
from app.infrastructure.config.database.postgres.models.profile_models import HealthMetricReadingModel


class HealthMetricReadingRepositoryPG(HealthMetricReadingRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_entity(model: HealthMetricReadingModel) -> HealthMetricReading:
        return HealthMetricReading(
            id=model.id,
            profile_id=model.profile_id,
            metric_type=model.metric_type,
            measured_at=model.measured_at,
            systolic=model.systolic,
            diastolic=model.diastolic,
            heart_rate=model.heart_rate,
            weight_kg=model.weight_kg,
            glucose_mmol_l=model.glucose_mmol_l,
            status=model.status,
            notes=model.notes,
            created_at=model.created_at,
            deleted_at=model.deleted_at,
        )

    async def list_for_profile(self, profile_id: UUID) -> list[HealthMetricReading]:
        stmt = (
            select(HealthMetricReadingModel)
            .where(
                HealthMetricReadingModel.profile_id == profile_id,
                HealthMetricReadingModel.deleted_at.is_(None),
            )
            .order_by(HealthMetricReadingModel.measured_at.desc())
        )
        r = await self.session.execute(stmt)
        return [self._to_entity(row) for row in r.scalars().all()]

    async def list_for_profiles(
        self, profile_ids: list[UUID]
    ) -> dict[UUID, list[HealthMetricReading]]:
        if not profile_ids:
            return {}
        stmt = (
            select(HealthMetricReadingModel)
            .where(
                HealthMetricReadingModel.profile_id.in_(profile_ids),
                HealthMetricReadingModel.deleted_at.is_(None),
            )
            .order_by(
                HealthMetricReadingModel.profile_id,
                HealthMetricReadingModel.measured_at.desc(),
            )
        )
        r = await self.session.execute(stmt)
        out: dict[UUID, list[HealthMetricReading]] = {pid: [] for pid in profile_ids}
        for row in r.scalars().all():
            ent = self._to_entity(row)
            out[ent.profile_id].append(ent)
        return out

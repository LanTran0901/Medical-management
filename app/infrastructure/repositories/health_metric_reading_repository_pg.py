from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
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

    async def get_by_id(self, reading_id: UUID) -> HealthMetricReading | None:
        m = await self.session.get(HealthMetricReadingModel, reading_id)
        if m is None or m.deleted_at is not None:
            return None
        return self._to_entity(m)

    async def create(
        self,
        *,
        profile_id: UUID,
        metric_type: str,
        measured_at: datetime,
        systolic: int | None,
        diastolic: int | None,
        heart_rate: int | None,
        weight_kg: Decimal | None,
        glucose_mmol_l: Decimal | None,
        status: str | None,
        notes: str | None,
    ) -> HealthMetricReading:
        m = HealthMetricReadingModel(
            profile_id=profile_id,
            metric_type=metric_type,
            measured_at=measured_at,
            systolic=systolic,
            diastolic=diastolic,
            heart_rate=heart_rate,
            weight_kg=weight_kg,
            glucose_mmol_l=glucose_mmol_l,
            status=status,
            notes=notes,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_entity(m)

    async def update(self, reading_id: UUID, fields: dict[str, object]) -> HealthMetricReading | None:
        m = await self.session.get(HealthMetricReadingModel, reading_id)
        if m is None or m.deleted_at is not None:
            return None
        for k, v in fields.items():
            setattr(m, k, v)
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_entity(m)

    async def soft_delete(self, reading_id: UUID) -> bool:
        m = await self.session.get(HealthMetricReadingModel, reading_id)
        if m is None or m.deleted_at is not None:
            return False
        m.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

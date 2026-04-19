from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.entities.health_metric_reading import HealthMetricReading


class HealthMetricReadingRepositoryPort:
    async def list_for_profile(self, profile_id: UUID) -> list[HealthMetricReading]:
        raise NotImplementedError

    async def list_for_profiles(
        self, profile_ids: list[UUID]
    ) -> dict[UUID, list[HealthMetricReading]]:
        """Non-deleted readings for many profiles (single query; GET /users/me optimization)."""
        raise NotImplementedError

    async def get_by_id(self, reading_id: UUID) -> HealthMetricReading | None:
        """Active row only (deleted_at IS NULL)."""
        raise NotImplementedError

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
        raise NotImplementedError

    async def update(self, reading_id: UUID, fields: dict[str, object]) -> HealthMetricReading | None:
        """Patch fields; returns None if row missing or soft-deleted."""
        raise NotImplementedError

    async def soft_delete(self, reading_id: UUID) -> bool:
        """Returns False if row missing or already soft-deleted."""
        raise NotImplementedError

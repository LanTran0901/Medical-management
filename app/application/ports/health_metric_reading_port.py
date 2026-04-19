from __future__ import annotations

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

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VaccinationRecommendation:
    id: UUID
    code: str | None
    name: str
    disease_name: str | None
    total_doses: int
    notes: str | None
    created_at: datetime


@dataclass(slots=True)
class UserVaccination:
    id: UUID
    profile_id: UUID
    recommendation_id: UUID
    user_id: UUID | None
    status: str | None
    created_at: datetime


@dataclass(slots=True)
class VaccinationDose:
    id: UUID
    user_vaccination_id: UUID
    dose_index: int
    administered_at: date | None
    scheduled_at: date | None
    location: str | None
    reaction: str | None
    proof_url: str | None
    reminder_enabled: bool
    remind_before_days: int | None

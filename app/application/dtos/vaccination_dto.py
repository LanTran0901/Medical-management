from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VaccinationRecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str | None
    name: str
    disease_name: str | None
    total_doses: int
    notes: str | None
    created_at: datetime


class SubscribeUserVaccinationRequest(BaseModel):
    recommendation_id: UUID


class PatchUserVaccinationRequest(BaseModel):
    status: str | None = Field(default=None, max_length=32)


class UserVaccinationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: UUID
    recommendation_id: UUID
    recommendation_name: str
    recommendation_total_doses: int
    user_id: UUID | None
    status: str | None
    created_at: datetime
    doses_administered_count: int = 0


class UserVaccinationWithDosesResponse(BaseModel):
    """Subscription + tất cả mũi tiêm (dùng cho bundle /users/me, tab sức khỏe)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: UUID
    recommendation_id: UUID
    recommendation_name: str
    recommendation_total_doses: int
    user_id: UUID | None
    status: str | None
    created_at: datetime
    doses_administered_count: int = 0
    doses: list[VaccinationDoseResponse] = Field(default_factory=list)


class CreateVaccinationDoseRequest(BaseModel):
    dose_index: int = Field(..., ge=1)
    administered_at: date | None = None
    scheduled_at: date | None = None
    location: str | None = None
    reaction: str | None = None
    proof_url: str | None = None
    reminder_enabled: bool = False
    remind_before_days: int | None = Field(None, ge=0)


class PatchVaccinationDoseRequest(BaseModel):
    administered_at: date | None = None
    scheduled_at: date | None = None
    location: str | None = None
    reaction: str | None = None
    proof_url: str | None = None
    reminder_enabled: bool | None = None
    remind_before_days: int | None = Field(None, ge=0)


DoseStatusLiteral = Literal["ADMINISTERED", "OVERDUE", "SCHEDULED", "UNSCHEDULED"]


class VaccinationDoseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    dose_status: DoseStatusLiteral
    is_overdue: bool

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EmergencyContactEntry:
    name: str | None = None
    phone: str | None = None
    relationship: str | None = None


@dataclass(frozen=True, slots=True)
class HealthDetail:
    id: UUID
    profile_id: UUID
    blood_type: str | None
    chronic_diseases: list[str] | None
    allergies: list[str] | None
    notes: str | None
    updated_at: datetime
    drug_allergies: list[str] | None = None
    food_allergies: list[str] | None = None
    emergency_contacts: list[EmergencyContactEntry] = field(default_factory=list)

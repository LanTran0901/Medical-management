from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class HealthDetail:
    id: UUID
    profile_id: UUID
    blood_type: str | None
    chronic_diseases: list[str] | None
    allergies: list[str] | None
    emergency_contact: str | None
    notes: str | None
    updated_at: datetime

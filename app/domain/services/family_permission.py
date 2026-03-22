from __future__ import annotations

from app.domain.entities.family import FamilyRole


def role_rank(role: FamilyRole) -> int:
    return {FamilyRole.OWNER: 3, FamilyRole.ADMIN: 2, FamilyRole.MEMBER: 1}[role]


def has_at_least(actor: FamilyRole, required: FamilyRole) -> bool:
    return role_rank(actor) >= role_rank(required)

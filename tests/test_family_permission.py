"""Pure unit tests — no DB (SC-001 companion / permission helpers)."""

from app.domain.entities.family import FamilyRole
from app.domain.services.family_permission import has_at_least, role_rank


def test_role_rank_order() -> None:
    assert role_rank(FamilyRole.OWNER) > role_rank(FamilyRole.ADMIN)
    assert role_rank(FamilyRole.ADMIN) > role_rank(FamilyRole.MEMBER)


def test_has_at_least() -> None:
    assert has_at_least(FamilyRole.OWNER, FamilyRole.MEMBER)
    assert has_at_least(FamilyRole.ADMIN, FamilyRole.MEMBER)
    assert not has_at_least(FamilyRole.MEMBER, FamilyRole.ADMIN)

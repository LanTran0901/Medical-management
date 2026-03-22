"""Unit tests cho `from_entity` trong family DTOs."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.application.dtos.family_dto import (
    FamilyResponse,
    FamilySummaryResponse,
    HealthDetailResponse,
    MembershipResponse,
    ProfileResponse,
)
from app.domain.entities.family import Family, FamilyMembership, FamilyRole
from app.domain.entities.health_detail import HealthDetail
from app.domain.entities.profile import Profile


def _dt() -> datetime:
    return datetime.now(timezone.utc)


def test_health_detail_response_from_entity() -> None:
    pid = uuid4()
    hd = HealthDetail(
        id=uuid4(),
        profile_id=pid,
        blood_type="A+",
        chronic_diseases=["x"],
        allergies=None,
        emergency_contact="911",
        notes="n",
        updated_at=_dt(),
    )
    r = HealthDetailResponse.from_entity(hd)
    assert r.profile_id == pid
    assert r.blood_type == "A+"


def test_family_response_and_summary_from_entity() -> None:
    f = Family(
        id=uuid4(),
        family_name="F",
        invite_code="code",
        created_at=_dt(),
    )
    fr = FamilyResponse.from_entity(f)
    fs = FamilySummaryResponse.from_entity(f)
    assert fr.id == f.id and fs.family_name == "F"


def test_membership_response_from_entity_with_optional_fields() -> None:
    m = FamilyMembership(
        id=uuid4(),
        family_id=uuid4(),
        profile_id=uuid4(),
        role=FamilyRole.MEMBER,
        added_by=uuid4(),
        created_at=_dt(),
    )
    r = MembershipResponse.from_entity(m, profile_full_name="P", linked_user_id=uuid4())
    assert r.profile_full_name == "P"
    assert r.role == FamilyRole.MEMBER


def test_profile_response_from_entity() -> None:
    now = _dt()
    p = Profile(
        id=uuid4(),
        owner_user_id=uuid4(),
        linked_user_id=None,
        full_name="N",
        dob=date(2000, 1, 1),
        gender="M",
        height_cm=Decimal("170"),
        weight_kg=Decimal("70"),
        address="A",
        avatar_url=None,
        status="ok",
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    r = ProfileResponse.from_entity(p)
    assert r.full_name == "N" and r.height_cm == Decimal("170")

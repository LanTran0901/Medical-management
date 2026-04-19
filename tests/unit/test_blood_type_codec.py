from __future__ import annotations

import pytest

from app.domain.services.blood_type_codec import format_blood_type_for_api, normalize_blood_type_to_db


@pytest.mark.parametrize(
    "raw,expected_db",
    [
        ("O+", "O_POS"),
        ("o+", "O_POS"),
        ("O-", "O_NEG"),
        ("AB+", "AB_POS"),
        ("O_POS", "O_POS"),
        ("o_pos", "O_POS"),
    ],
)
def test_normalize_display_and_slug(raw: str, expected_db: str) -> None:
    assert normalize_blood_type_to_db(raw) == expected_db


def test_normalize_none_and_empty() -> None:
    assert normalize_blood_type_to_db(None) is None
    assert normalize_blood_type_to_db("  ") is None


def test_normalize_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid blood_type"):
        normalize_blood_type_to_db("X+")


@pytest.mark.parametrize(
    "db_val,display",
    [
        ("O_POS", "O+"),
        ("O_NEG", "O-"),
        ("AB_POS", "AB+"),
        (None, None),
    ],
)
def test_format_api(db_val: str | None, display: str | None) -> None:
    assert format_blood_type_for_api(db_val) == display


def test_format_unknown_db_pass_through() -> None:
    assert format_blood_type_for_api("CUSTOM") == "CUSTOM"


def test_patch_health_detail_request_normalizes_o_plus() -> None:
    from app.application.dtos.family_dto import PatchHealthDetailRequest

    body = PatchHealthDetailRequest(blood_type="O+")
    assert body.blood_type == "O_POS"

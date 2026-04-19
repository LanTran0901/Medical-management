"""Map blood type between API display (e.g. O+) and DB enum values (O_POS)."""

from __future__ import annotations

# Must match app.infrastructure...profile_models.blood_type_pg
_DB_VALUES = frozenset(
    {
        "A_POS",
        "A_NEG",
        "B_POS",
        "B_NEG",
        "O_POS",
        "O_NEG",
        "AB_POS",
        "AB_NEG",
    }
)

_DISPLAY_TO_DB: dict[str, str] = {
    "A+": "A_POS",
    "A-": "A_NEG",
    "B+": "B_POS",
    "B-": "B_NEG",
    "O+": "O_POS",
    "O-": "O_NEG",
    "AB+": "AB_POS",
    "AB-": "AB_NEG",
}

_DB_TO_DISPLAY: dict[str, str] = {v: k for k, v in _DISPLAY_TO_DB.items()}


def normalize_blood_type_to_db(raw: str | None) -> str | None:
    """
    Accept DB slugs (O_POS), common display strings (O+, o+), or synonyms.
    Raises ValueError if non-empty and not recognized.
    """
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    upper = s.upper().replace(" ", "")
    if upper in _DB_VALUES:
        return upper
    # Allow lowercase slug e.g. o_pos
    slug = s.strip().upper()
    if slug in _DB_VALUES:
        return slug
    if upper in _DISPLAY_TO_DB:
        return _DISPLAY_TO_DB[upper]
    raise ValueError(
        f"Invalid blood_type: {raw!r}. Use A+, A-, B+, B-, O+, O-, AB+, AB- or *_POS / *_NEG slugs."
    )


def format_blood_type_for_api(db_value: str | None) -> str | None:
    """Expose human-friendly labels in JSON (GET /users/me, profile health)."""
    if db_value is None:
        return None
    return _DB_TO_DISPLAY.get(db_value, db_value)

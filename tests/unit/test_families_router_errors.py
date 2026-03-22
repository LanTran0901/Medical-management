"""Test map lỗi domain → HTTP trong `families_router._handle_family_error`."""

from __future__ import annotations

import pytest
from fastapi import HTTPException, status

from app.api.families_router import _handle_family_error
from app.application.family_errors import ConflictError, ForbiddenError, NotFoundError


def test_handle_not_found_default_detail() -> None:
    with pytest.raises(HTTPException) as ei:
        _handle_family_error(NotFoundError(""))
    assert ei.value.status_code == status.HTTP_404_NOT_FOUND
    assert ei.value.detail == "Not found"


def test_handle_not_found_custom_message() -> None:
    with pytest.raises(HTTPException) as ei:
        _handle_family_error(NotFoundError("x"))
    assert ei.value.status_code == status.HTTP_404_NOT_FOUND
    assert ei.value.detail == "x"


def test_handle_forbidden_and_conflict_and_value() -> None:
    with pytest.raises(HTTPException) as ei:
        _handle_family_error(ForbiddenError("no"))
    assert ei.value.status_code == status.HTTP_403_FORBIDDEN
    assert ei.value.detail == "no"

    with pytest.raises(HTTPException) as ei:
        _handle_family_error(ConflictError("dup"))
    assert ei.value.status_code == status.HTTP_409_CONFLICT
    assert ei.value.detail == "dup"

    with pytest.raises(HTTPException) as ei:
        _handle_family_error(ValueError("bad input"))
    assert ei.value.status_code == status.HTTP_400_BAD_REQUEST
    assert ei.value.detail == "bad input"


def test_handle_unknown_exception_does_not_raise() -> None:
    try:
        _handle_family_error(RuntimeError("surprise"))
    except HTTPException:
        pytest.fail("unexpected HTTPException")

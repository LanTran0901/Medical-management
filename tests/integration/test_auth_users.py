"""
Auth + /users/me — integration (PostgreSQL only, Mongo skipped).
"""

from __future__ import annotations

import pytest

from tests.integration.conftest import integration_disabled
from tests.integration.helpers import auth_headers, login_access_token, register_user, unique_suffix

pytestmark = pytest.mark.skipif(
    integration_disabled(),
    reason="Integration disabled (HOMEDMEDAI_INTEGRATION=0) or no Postgres",
)


def test_register_returns_201_with_user_shape(client) -> None:
    suf = unique_suffix()
    r = client.post(
        "/auth/register",
        json={"email": f"u{suf}@test.local", "password_hash": "password123"},
    )
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["email"] == f"u{suf}@test.local"
    assert "status" in data


def test_register_duplicate_email_returns_400(client) -> None:
    suf = register_user(client)
    r = client.post(
        "/auth/register",
        json={"email": f"u{suf}@test.local", "password_hash": "password123"},
    )
    assert r.status_code == 400


def test_login_returns_token(client) -> None:
    suf = register_user(client)
    token = login_access_token(client, suf)
    assert isinstance(token, str) and len(token) > 10


def test_users_me_returns_current_user(client) -> None:
    suf = register_user(client)
    token = login_access_token(client, suf)
    r = client.get("/users/me", headers=auth_headers(token))
    assert r.status_code == 200
    me = r.json()
    assert me["email"] == f"u{suf}@test.local"
    assert "id" in me


def test_users_me_without_token_returns_401(client) -> None:
    r = client.get("/users/me")
    assert r.status_code == 401

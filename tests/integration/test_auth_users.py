"""
Auth + /users/me — integration (PostgreSQL only, Mongo skipped).
"""

from __future__ import annotations

import pytest

from tests.integration.conftest import integration_disabled
from tests.integration.helpers import auth_headers, login_access_token, register_user, unique_phone, unique_suffix

pytestmark = pytest.mark.skipif(
    integration_disabled(),
    reason="Integration disabled (HOMEDMEDAI_INTEGRATION=0) or no Postgres",
)


def test_register_returns_201_with_user_shape(client) -> None:
    suf = unique_suffix()
    r = client.post(
        "/auth/register",
        json={
            "email": f"u{suf}@test.local",
            "phone_number": unique_phone(),
            "password": "password123",
        },
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
        json={
            "email": f"u{suf}@test.local",
            "phone_number": unique_phone(),
            "password": "password123",
        },
    )
    assert r.status_code == 400


def test_register_duplicate_phone_returns_400(client) -> None:
    phone = unique_phone()
    register_user(client, phone_number=phone)
    suf = unique_suffix()
    r = client.post(
        "/auth/register",
        json={
            "email": f"u{suf}@test.local",
            "phone_number": phone,
            "password": "password123",
        },
    )
    assert r.status_code == 400


def test_register_requires_phone_number(client) -> None:
    suf = unique_suffix()
    r = client.post(
        "/auth/register",
        json={
            "email": f"u{suf}@test.local",
            "password": "password123",
        },
    )
    assert r.status_code == 422


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
    assert me["user"]["email"] == f"u{suf}@test.local"
    assert "id" in me["user"]
    assert me["profiles"] == []
    assert me.get("profile") is None
    assert me.get("health_profile") is None


def test_users_me_bundle_includes_health_profile_after_personal_profile(client) -> None:
    suf = register_user(client)
    token = login_access_token(client, suf)
    created = client.post(
        "/users/me/personal-profile",
        json={"full_name": "Bundle User"},
        headers=auth_headers(token),
    )
    assert created.status_code == 201, created.text
    profile_id = created.json()["id"]
    r = client.get("/users/me", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    me = r.json()
    assert len(me["profiles"]) == 1
    assert me["profiles"][0]["profile"]["id"] == profile_id
    assert me["profiles"][0]["family_ids"] == []
    assert me["profiles"][0]["family_count"] == 0
    assert me["profile"]["id"] == profile_id
    hp = me["health_profile"]
    assert hp["profile_id"] == profile_id
    assert isinstance(hp["medical_records"], list)
    assert isinstance(hp["vaccinations"], list)
    assert hp["medicine_inventory"] == []
    assert hp["appointment_reminders"] == []


def test_users_me_returns_all_linked_profiles(client) -> None:
    suf = register_user(client)
    token = login_access_token(client, suf)

    first = client.post(
        "/users/me/personal-profile",
        json={"full_name": "Bundle User 1"},
        headers=auth_headers(token),
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/users/me/personal-profile",
        json={"full_name": "Bundle User 2"},
        headers=auth_headers(token),
    )
    assert second.status_code == 201, second.text

    r = client.get("/users/me", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    me = r.json()
    ids = [bundle["profile"]["id"] for bundle in me["profiles"]]
    assert first.json()["id"] in ids
    assert second.json()["id"] in ids
    assert len(me["profiles"]) == 2


def test_users_me_without_token_returns_401(client) -> None:
    r = client.get("/users/me")
    assert r.status_code == 401

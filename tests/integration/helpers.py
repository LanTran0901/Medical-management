"""Helpers cho integration tests (PostgreSQL)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def unique_suffix() -> str:
    return uuid.uuid4().hex[:8]


def register_user(client: TestClient, suffix: str | None = None) -> str:
    """Đăng ký user; trả về suffix dùng cho email/login."""
    suf = suffix or unique_suffix()
    r = client.post(
        "/auth/register",
        json={
            "email": f"u{suf}@test.local",
            "password_hash": "password123",
        },
    )
    assert r.status_code == 201, r.text
    return suf


def login_access_token(client: TestClient, suffix: str) -> str:
    r = client.post(
        "/auth/login",
        json={
            "email": f"u{suffix}@test.local",
            "password": "password123",
            "device_id": f"dev-{suffix}",
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

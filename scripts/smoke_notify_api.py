"""Smoke test push-notification HTTP routes against localhost (run inside API container)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("SMOKE_API_BASE", "http://127.0.0.1:8080")


def req(
    method: str,
    path: str,
    body: dict | None = None,
    headers: dict | None = None,
) -> tuple[int, str]:
    h = dict(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h.setdefault("Content-Type", "application/json")
    r = urllib.request.Request(
        BASE + path, data=data, headers=h, method=method
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main() -> None:
    results: list[tuple[str, int, str]] = []

    st, body = req(
        "POST",
        "/notifications/dispatch/schedules",
        headers={"X-Internal-Secret": "wrong-secret"},
    )
    results.append(("POST /notifications/dispatch/schedules (bad secret)", st, body[:300]))

    sec = os.environ.get("INTERNAL_DISPATCH_SECRET") or ""
    st, body = req(
        "POST",
        "/notifications/dispatch/schedules",
        headers={"X-Internal-Secret": sec},
    )
    results.append(("POST /notifications/dispatch/schedules (good secret)", st, body[:500]))

    email = f"push_smoke_{uuid.uuid4().hex[:10]}@test.local"
    st, body = req(
        "POST",
        "/auth/register",
        {
            "email": email,
            "phone_number": "+84901234567",
            "password": "secret12",
        },
    )
    results.append(("POST /auth/register", st, body[:400]))

    if st not in (200, 201):
        for name, code, snippet in results:
            print(f"{name}: HTTP {code} {snippet}")
        raise SystemExit(1)

    st, body = req(
        "POST",
        "/auth/login",
        {
            "email": email,
            "password": "secret12",
            "device_id": "smoke-test-device",
        },
    )
    results.append(("POST /auth/login", st, body[:200]))
    if st != 200:
        for name, code, snippet in results:
            print(f"{name}: HTTP {code} {snippet}")
        raise SystemExit(1)

    tok = json.loads(body)
    access = tok["access_token"]
    auth_h = {"Authorization": f"Bearer {access}"}

    st, body = req("GET", "/notifications/me", headers=auth_h)
    results.append(("GET /notifications/me", st, body[:400]))

    st, body = req(
        "POST",
        "/notifications/send",
        {"title": "Smoke", "body": "Test push"},
        headers=auth_h,
    )
    results.append(("POST /notifications/send", st, body[:400]))

    fake_sid = "00000000-0000-0000-0000-000000000001"
    st, body = req(
        "POST",
        f"/notifications/me/schedules/{fake_sid}/compliance",
        {"outcome": "taken"},
        headers=auth_h,
    )
    results.append(
        (f"POST /notifications/me/schedules/.../compliance (fake id)", st, body[:300])
    )

    for name, code, snippet in results:
        print(f"{name}: HTTP {code}")
        print(f"  {snippet}")
        print()


if __name__ == "__main__":
    main()

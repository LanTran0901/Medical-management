"""One-off smoke test for notification routes (run via pipenv run python scripts/_smoke_notifications_backend.py)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def main() -> None:
    with TestClient(app) as client:
        h = client.get("/health")
        print("GET /health", h.status_code, h.json())

        d = client.post(
            "/notifications/dispatch/schedules",
            headers={"X-Internal-Secret": settings.internal_dispatch_secret or ""},
        )
        print("POST /notifications/dispatch/schedules", d.status_code, d.json())

        bad = client.post(
            "/notifications/dispatch/schedules",
            headers={"X-Internal-Secret": "wrong"},
        )
        print("POST dispatch wrong secret", bad.status_code)

        s = client.post("/notifications/send", json={"title": "smoke", "body": "test"})
        print("POST /notifications/send (no auth)", s.status_code)


if __name__ == "__main__":
    main()

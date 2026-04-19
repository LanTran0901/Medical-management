"""CRUD health_metric_readings — integration (PostgreSQL)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tests.integration.conftest import integration_disabled
from tests.integration.helpers import auth_headers, login_access_token, register_user

pytestmark = pytest.mark.skipif(
    integration_disabled(),
    reason="Integration disabled (HOMEDMEDAI_INTEGRATION=0) or no Postgres",
)


def test_health_metric_readings_crud_soft_delete(client) -> None:
    suf = register_user(client)
    token = login_access_token(client, suf)
    headers = auth_headers(token)

    created_profile = client.post(
        "/users/me/personal-profile",
        json={"full_name": "Metric User"},
        headers=headers,
    )
    assert created_profile.status_code == 201, created_profile.text
    profile_id = created_profile.json()["id"]

    measured = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
    create_body = {
        "metric_type": "BLOOD_PRESSURE",
        "measured_at": measured.isoformat(),
        "systolic": 120,
        "diastolic": 80,
    }
    r = client.post(
        f"/profiles/{profile_id}/health-metric-readings",
        json=create_body,
        headers=headers,
    )
    assert r.status_code == 201, r.text
    row = r.json()
    reading_id = row["id"]
    assert row["profile_id"] == profile_id
    assert row["metric_type"] == "BLOOD_PRESSURE"
    assert row["systolic"] == 120

    listed = client.get(
        f"/profiles/{profile_id}/health-metric-readings",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 1

    one = client.get(f"/health-metric-readings/{reading_id}", headers=headers)
    assert one.status_code == 200, one.text
    assert one.json()["id"] == reading_id

    patched = client.patch(
        f"/health-metric-readings/{reading_id}",
        json={"heart_rate": 72},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["heart_rate"] == 72

    deleted = client.delete(f"/health-metric-readings/{reading_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    missing = client.get(f"/health-metric-readings/{reading_id}", headers=headers)
    assert missing.status_code == 404

    empty = client.get(
        f"/profiles/{profile_id}/health-metric-readings",
        headers=headers,
    )
    assert empty.status_code == 200, empty.text
    assert empty.json() == []

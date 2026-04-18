"""Integration tests for notifications router (list/compliance/snooze)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.integration.conftest import integration_disabled
from tests.integration.helpers import auth_headers, login_access_token, register_user

pytestmark = pytest.mark.skipif(
    integration_disabled(),
    reason="Integration disabled (HOMEDMEDAI_INTEGRATION=0) or no Postgres",
)


def _bootstrap_medicine_schedule(client):
    suffix = register_user(client)
    token = login_access_token(client, suffix)
    headers = auth_headers(token)

    create_family = client.post(
        "/families",
        json={"family_name": f"FamNoti-{suffix}", "full_name": "Owner Notification"},
        headers=headers,
    )
    assert create_family.status_code == 201, create_family.text
    family_payload = create_family.json()

    family_id = family_payload["id"]
    profile_id = family_payload["members"][0]["profile"]["id"]

    create_item = client.post(
        f"/families/{family_id}/medicine-inventory",
        json={
            "medicine_name": "Metformin 500mg",
            "medicine_type": "Viên nén",
            "quantity_stock": 10,
            "expiry_date": (date.today() + timedelta(days=30)).isoformat(),
            "unit": "viên",
        },
        headers=headers,
    )
    assert create_item.status_code == 201, create_item.text
    item_id = create_item.json()["id"]

    create_schedule = client.post(
        f"/medicine-inventory/{item_id}/schedules",
        json={
            "profile_id": profile_id,
            "remind_time": "07:00",
            "dosage_per_time": 1,
        },
        headers=headers,
    )
    assert create_schedule.status_code == 201, create_schedule.text
    schedule_id = create_schedule.json()["id"]

    return headers, schedule_id


def _find_item(items: list[dict], schedule_id: str) -> dict:
    matched = [
        i
        for i in items
        if i.get("id") == schedule_id or i.get("schedule_id") == schedule_id
    ]
    assert matched, f"Schedule {schedule_id} not found in notifications list"
    return matched[0]


def test_notifications_list_includes_schedule_and_occurrence_fields(client) -> None:
    headers, schedule_id = _bootstrap_medicine_schedule(client)

    list_before = client.get("/notifications/me", headers=headers)
    assert list_before.status_code == 200, list_before.text
    item_before = _find_item(list_before.json()["items"], schedule_id)

    assert item_before.get("schedule_id") == schedule_id
    assert item_before.get("lifecycle_status") in {"ACTIVE", "PAUSED", "COMPLETED"}

    mark_taken = client.post(
        f"/notifications/me/schedules/{schedule_id}/compliance",
        json={"outcome": "taken"},
        headers=headers,
    )
    assert mark_taken.status_code == 200, mark_taken.text
    assert mark_taken.json()["success"] is True

    list_after = client.get("/notifications/me", headers=headers)
    assert list_after.status_code == 200, list_after.text
    item_after = _find_item(list_after.json()["items"], schedule_id)

    assert item_after.get("occurrence_status") == "TAKEN"
    assert item_after.get("status") == "COMPLETED"


def test_snooze_endpoint_persists_and_reflects_in_notifications(client) -> None:
    headers, schedule_id = _bootstrap_medicine_schedule(client)

    snooze = client.post(
        f"/notifications/me/schedules/{schedule_id}/snooze",
        json={"minutes": 15},
        headers=headers,
    )
    assert snooze.status_code == 200, snooze.text
    payload = snooze.json()
    assert payload["success"] is True
    assert payload.get("snoozed_until") is not None

    listed = client.get("/notifications/me", headers=headers)
    assert listed.status_code == 200, listed.text
    item = _find_item(listed.json()["items"], schedule_id)

    assert item.get("occurrence_status") == "SNOOZED"
    assert item.get("status") == "SNOOZED"
    assert item.get("snoozed_until") is not None

from __future__ import annotations

import pytest

from tests.integration.conftest import integration_disabled
from tests.integration.helpers import auth_headers, login_access_token, register_user

pytestmark = pytest.mark.skipif(
    integration_disabled(),
    reason="Integration disabled (HOMEDMEDAI_INTEGRATION=0) or no Postgres",
)


def test_sc004_multi_profile_join_requires_profile_id_and_uses_selected_profile(client) -> None:
    suffix = register_user(client)
    token = login_access_token(client, suffix)

    create_personal = client.post(
        "/users/me/personal-profile",
        json={"full_name": "Personal User"},
        headers=auth_headers(token),
    )
    assert create_personal.status_code == 201, create_personal.text
    personal_profile_id = create_personal.json()["id"]

    create_again = client.post(
        "/users/me/personal-profile",
        json={"full_name": "Personal User 2"},
        headers=auth_headers(token),
    )
    assert create_again.status_code == 201, create_again.text
    second_profile_id = create_again.json()["id"]

    owner_suffix = register_user(client)
    owner_token = login_access_token(client, owner_suffix)
    family_resp = client.post(
        "/families",
        json={"family_name": "JoinTargetFamily", "full_name": "Owner"},
        headers=auth_headers(owner_token),
    )
    assert family_resp.status_code == 201, family_resp.text
    invite_code = family_resp.json()["invite_code"]
    family_id = family_resp.json()["id"]

    join_resp = client.post(
        "/families/join",
        json={"invite_code": invite_code},
        headers=auth_headers(token),
    )
    assert join_resp.status_code == 409, join_resp.text

    join_resp = client.post(
        "/families/join",
        json={"invite_code": invite_code, "profile_id": personal_profile_id},
        headers=auth_headers(token),
    )
    assert join_resp.status_code == 200, join_resp.text

    linked_profiles = client.get("/users/me/profiles?profile_scope=all", headers=auth_headers(token))
    assert linked_profiles.status_code == 200, linked_profiles.text
    ids = [row["id"] for row in linked_profiles.json()]
    assert ids.count(personal_profile_id) == 1
    assert ids.count(second_profile_id) == 1

    in_family = client.get("/users/me/profiles?profile_scope=with_family", headers=auth_headers(token))
    assert in_family.status_code == 200, in_family.text
    assert any(row["id"] == personal_profile_id for row in in_family.json())
    assert all(row["id"] != second_profile_id for row in in_family.json())

    outside_family = client.get(
        "/users/me/profiles?profile_scope=without_family",
        headers=auth_headers(token),
    )
    assert outside_family.status_code == 200, outside_family.text
    assert any(row["id"] == second_profile_id for row in outside_family.json())

    list_profiles = client.get(f"/families/{family_id}/profiles", headers=auth_headers(token))
    assert list_profiles.status_code == 200
    assert any(row["id"] == personal_profile_id for row in list_profiles.json())
    assert all(row["id"] != second_profile_id for row in list_profiles.json())


def test_invite_preview_valid_and_invalid(client) -> None:
    owner_suffix = register_user(client)
    owner_token = login_access_token(client, owner_suffix)

    created = client.post(
        "/families",
        json={"family_name": "Preview Family", "full_name": "Owner"},
        headers=auth_headers(owner_token),
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    invite_code = payload["invite_code"]

    ok = client.get(f"/families/invite/preview?invite_code={invite_code}")
    assert ok.status_code == 200, ok.text
    payload = ok.json()
    assert payload["valid"] is True
    assert payload["invite_code"] == invite_code
    assert payload["family_name"] == created.json()["name"]

    bad = client.get("/families/invite/preview?invite_code=invalid_preview_code")
    assert bad.status_code == 404

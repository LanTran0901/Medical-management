from __future__ import annotations

import pytest

from tests.integration.conftest import integration_disabled
from tests.integration.helpers import auth_headers, login_access_token, register_user, unique_phone

pytestmark = pytest.mark.skipif(
    integration_disabled(),
    reason="Integration disabled (HOMEDMEDAI_INTEGRATION=0) or no Postgres",
)


def test_invite_by_phone_success_owner(client) -> None:
    owner_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)

    invited_phone = unique_phone()
    invited_suf = register_user(client, phone_number=invited_phone)
    invited_tok = login_access_token(client, invited_suf)
    me = client.get("/users/me", headers=auth_headers(invited_tok))
    assert me.status_code == 200, me.text
    invited_user_id = me.json()["id"]

    created = client.post(
        "/families",
        json={"family_name": "PhoneInvite", "full_name": "Owner"},
        headers=auth_headers(owner_tok),
    )
    assert created.status_code == 201, created.text
    family_id = created.json()["id"]

    invited = client.post(
        f"/families/{family_id}/invite-by-phone",
        json={"phone_number": invited_phone, "full_name": "Invited Name"},
        headers=auth_headers(owner_tok),
    )
    assert invited.status_code == 200, invited.text
    payload = invited.json()
    assert payload["dry_run"] is False
    assert payload["invite"]["family_id"] == family_id
    assert payload["invite"]["user_id"] == invited_user_id
    assert payload["invite"]["status"] == "pending"

    inbox = client.get(
        "/families/invites",
        headers=auth_headers(invited_tok),
    )
    assert inbox.status_code == 200, inbox.text
    invite_id = inbox.json()[0]["id"]

    accepted = client.post(
        "/families/join",
        json={"action": "accept", "invite_id": invite_id, "full_name": "Invited Name"},
        headers=auth_headers(invited_tok),
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"

    members = client.get(f"/families/{family_id}/members", headers=auth_headers(owner_tok))
    assert members.status_code == 200, members.text
    assert any(m["user_id"] == invited_user_id for m in members.json())


def test_invite_by_phone_forbidden_for_member(client) -> None:
    owner_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)
    member_suf = register_user(client)
    member_tok = login_access_token(client, member_suf)

    target_phone = unique_phone()
    register_user(client, phone_number=target_phone)

    created = client.post(
        "/families",
        json={"family_name": "FamilyA", "full_name": "Owner"},
        headers=auth_headers(owner_tok),
    )
    assert created.status_code == 201, created.text
    family_id = created.json()["id"]
    invite_code = created.json()["invite_code"]

    joined = client.post(
        "/families/join",
        json={"invite_code": invite_code, "full_name": "Member"},
        headers=auth_headers(member_tok),
    )
    assert joined.status_code == 200, joined.text

    invited = client.post(
        f"/families/{family_id}/invite-by-phone",
        json={"phone_number": target_phone, "full_name": "Target"},
        headers=auth_headers(member_tok),
    )
    assert invited.status_code == 403


def test_invite_by_phone_dry_run_user_not_found_returns_found_false(client) -> None:
    owner_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)

    created = client.post(
        "/families",
        json={"family_name": "FamilyB", "full_name": "Owner"},
        headers=auth_headers(owner_tok),
    )
    assert created.status_code == 201, created.text
    family_id = created.json()["id"]

    invited = client.post(
        f"/families/{family_id}/invite-by-phone",
        json={"phone_number": "+19999999999", "dry_run": True},
        headers=auth_headers(owner_tok),
    )
    assert invited.status_code == 200
    assert invited.json()["dry_run"] is True
    assert invited.json()["found"] is False


def test_invite_by_phone_conflict_when_already_member(client) -> None:
    owner_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)

    target_phone = unique_phone()
    register_user(client, phone_number=target_phone)

    created = client.post(
        "/families",
        json={"family_name": "FamilyC", "full_name": "Owner"},
        headers=auth_headers(owner_tok),
    )
    assert created.status_code == 201, created.text
    family_id = created.json()["id"]

    first = client.post(
        f"/families/{family_id}/invite-by-phone",
        json={"phone_number": target_phone, "full_name": "Target"},
        headers=auth_headers(owner_tok),
    )
    assert first.status_code == 200, first.text

    second = client.post(
        f"/families/{family_id}/invite-by-phone",
        json={"phone_number": target_phone, "full_name": "Target"},
        headers=auth_headers(owner_tok),
    )
    assert second.status_code == 409


def test_invite_by_phone_requires_full_name_without_personal_profile(client) -> None:
    owner_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)

    target_phone = unique_phone()
    register_user(client, phone_number=target_phone)

    created = client.post(
        "/families",
        json={"family_name": "FamilyD", "full_name": "Owner"},
        headers=auth_headers(owner_tok),
    )
    assert created.status_code == 201, created.text
    family_id = created.json()["id"]

    dry_run = client.post(
        f"/families/{family_id}/invite-by-phone",
        json={"phone_number": target_phone, "dry_run": True},
        headers=auth_headers(owner_tok),
    )
    assert dry_run.status_code == 200, dry_run.text
    assert dry_run.json()["found"] is True

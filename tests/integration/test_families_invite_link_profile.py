"""Invite link-profile flow for existing SHADOW/PENDING_LINK profiles."""

from __future__ import annotations

import pytest

from tests.integration.conftest import integration_disabled
from tests.integration.helpers import auth_headers, login_access_token, register_user

pytestmark = pytest.mark.skipif(
    integration_disabled(),
    reason="Integration disabled (HOMEDMEDAI_INTEGRATION=0) or no Postgres",
)


def test_list_linkable_profiles_by_invite_returns_unlinked_profiles(client) -> None:
    owner_suf = register_user(client)
    claimant_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)
    claimant_tok = login_access_token(client, claimant_suf)

    cr = client.post(
        "/families",
        json={"family_name": "LinkableFam", "full_name": "Owner"},
        headers=auth_headers(owner_tok),
    )
    assert cr.status_code == 201, cr.text
    family = cr.json()
    family_id = family["id"]
    code = family["invite_code"]

    p1 = client.post(
        f"/families/{family_id}/profiles",
        json={"full_name": "Nguyen Van A"},
        headers=auth_headers(owner_tok),
    )
    assert p1.status_code == 201, p1.text
    p1_id = p1.json()["profile"]["id"]

    p2 = client.post(
        f"/families/{family_id}/profiles",
        json={"full_name": "Nguyen Thi B"},
        headers=auth_headers(owner_tok),
    )
    assert p2.status_code == 201, p2.text
    p2_id = p2.json()["profile"]["id"]

    resp = client.get(
        f"/families/invite/linkable-profiles?invite_code={code}",
        headers=auth_headers(claimant_tok),
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["family_id"] == family_id
    assert payload["invite_code"] == code

    ids = {row["profile_id"] for row in payload["profiles"]}
    assert p1_id in ids
    assert p2_id in ids
    assert all(row["linked_user_id"] is None for row in payload["profiles"])


def test_link_profile_by_invite_links_selected_profile_and_consumes_code(client) -> None:
    owner_suf = register_user(client)
    claimant_suf = register_user(client)
    other_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)
    claimant_tok = login_access_token(client, claimant_suf)
    other_tok = login_access_token(client, other_suf)

    cr = client.post(
        "/families",
        json={"family_name": "ClaimProfileFam", "full_name": "Owner"},
        headers=auth_headers(owner_tok),
    )
    assert cr.status_code == 201, cr.text
    family = cr.json()
    family_id = family["id"]
    code = family["invite_code"]

    created = client.post(
        f"/families/{family_id}/profiles",
        json={"full_name": "Tran Van C"},
        headers=auth_headers(owner_tok),
    )
    assert created.status_code == 201, created.text
    profile_id = created.json()["profile"]["id"]

    link = client.post(
        "/families/invite/link-profile",
        json={"invite_code": code, "profile_id": profile_id},
        headers=auth_headers(claimant_tok),
    )
    assert link.status_code == 200, link.text
    body = link.json()
    assert body["success"] is True
    assert body["family_id"] == family_id
    assert body["profile_id"] == profile_id
    assert body["linked_user_id"] is not None
    assert body["post_login_flow_completed"] is True

    # Invite code is single-use: second claim with same code must fail.
    second = client.post(
        "/families/invite/link-profile",
        json={"invite_code": code, "profile_id": profile_id},
        headers=auth_headers(other_tok),
    )
    assert second.status_code == 410


def test_linkable_profiles_returns_410_for_expired_invite(client, monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "family_public_invite_ttl_seconds", -3600, raising=False)

    owner_suf = register_user(client)
    claimant_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)
    claimant_tok = login_access_token(client, claimant_suf)

    cr = client.post(
        "/families",
        json={"family_name": "ExpiredLinkable", "full_name": "Owner"},
        headers=auth_headers(owner_tok),
    )
    assert cr.status_code == 201, cr.text
    code = cr.json()["invite_code"]

    resp = client.get(
        f"/families/invite/linkable-profiles?invite_code={code}",
        headers=auth_headers(claimant_tok),
    )
    assert resp.status_code == 410

"""Public invite codes: single-use and preview after consume."""

from __future__ import annotations

import pytest

from tests.integration.conftest import integration_disabled
from tests.integration.helpers import auth_headers, login_access_token, register_user

pytestmark = pytest.mark.skipif(
    integration_disabled(),
    reason="Integration disabled (HOMEDMEDAI_INTEGRATION=0) or no Postgres",
)


def test_public_invite_single_use_second_user_gets_404(client) -> None:
    owner_suf = register_user(client)
    m1_suf = register_user(client)
    m2_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)
    m1_tok = login_access_token(client, m1_suf)
    m2_tok = login_access_token(client, m2_suf)

    cr = client.post(
        "/families",
        json={"family_name": "SingleUseFam", "full_name": "Owner"},
        headers=auth_headers(owner_tok),
    )
    assert cr.status_code == 201, cr.text
    code = cr.json()["invite_code"]

    j1 = client.post(
        "/families/join",
        json={"invite_code": code, "full_name": "Member1"},
        headers=auth_headers(m1_tok),
    )
    assert j1.status_code == 200, j1.text

    j2 = client.post(
        "/families/join",
        json={"invite_code": code, "full_name": "Member2"},
        headers=auth_headers(m2_tok),
    )
    assert j2.status_code == 404


def test_invite_preview_valid_false_after_code_consumed(client) -> None:
    owner_suf = register_user(client)
    member_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)
    member_tok = login_access_token(client, member_suf)

    cr = client.post(
        "/families",
        json={"family_name": "PreviewConsume", "full_name": "Owner"},
        headers=auth_headers(owner_tok),
    )
    assert cr.status_code == 201, cr.text
    code = cr.json()["invite_code"]

    ok_before = client.get(f"/families/invite/preview?invite_code={code}")
    assert ok_before.status_code == 200, ok_before.text
    assert ok_before.json()["valid"] is True
    assert "expires_at" in ok_before.json()

    jr = client.post(
        "/families/join",
        json={"invite_code": code, "full_name": "Joiner"},
        headers=auth_headers(member_tok),
    )
    assert jr.status_code == 200, jr.text

    after = client.get(f"/families/invite/preview?invite_code={code}")
    assert after.status_code == 200, after.text
    body = after.json()
    assert body["valid"] is False
    assert body["invite_code"] == code
    assert body["family_name"] == "PreviewConsume"


def test_join_rejects_expired_public_invite(client, monkeypatch) -> None:
    """TTL in the past produces an already-expired token at family creation."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "family_public_invite_ttl_seconds", -7200, raising=False)

    owner_suf = register_user(client)
    join_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)
    join_tok = login_access_token(client, join_suf)

    cr = client.post(
        "/families",
        json={"family_name": "ExpiredTok", "full_name": "Owner"},
        headers=auth_headers(owner_tok),
    )
    assert cr.status_code == 201, cr.text
    code = cr.json()["invite_code"]

    preview = client.get(f"/families/invite/preview?invite_code={code}")
    assert preview.status_code == 200, preview.text
    assert preview.json()["valid"] is False

    jr = client.post(
        "/families/join",
        json={"invite_code": code, "full_name": "Late"},
        headers=auth_headers(join_tok),
    )
    assert jr.status_code == 404

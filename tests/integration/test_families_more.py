"""
Families API — thêm case SC-001 (c)(d), join, rotate (F3–F7).
"""

from __future__ import annotations

import uuid

import pytest

from tests.integration.conftest import integration_disabled
from tests.integration.helpers import auth_headers, login_access_token, register_user

pytestmark = pytest.mark.skipif(
    integration_disabled(),
    reason="Integration disabled (HOMEDMEDAI_INTEGRATION=0) or no Postgres",
)


def test_case_c_member_patch_health_forbidden(client) -> None:
    """SC-001 (c): MEMBER PATCH health → 403."""
    owner_suf = register_user(client)
    member_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)
    member_tok = login_access_token(client, member_suf)

    cr = client.post(
        "/families",
        json={"family_name": "FamH", "full_name": "Owner H"},
        headers=auth_headers(owner_tok),
    )
    assert cr.status_code == 201, cr.text
    family_id = cr.json()["id"]
    owner_profile_id = cr.json()["members"][0]["profile"]["id"]

    jr = client.post(
        "/families/join",
        json={"invite_code": cr.json()["invite_code"], "full_name": "Member H"},
        headers=auth_headers(member_tok),
    )
    assert jr.status_code == 200, jr.text

    patch = client.patch(
        f"/profiles/{owner_profile_id}/health",
        json={"notes": "try"},
        headers=auth_headers(member_tok),
    )
    assert patch.status_code == 403


def test_case_d_profile_not_in_scope_returns_403(client) -> None:
    """SC-001 (d): member family F1 gọi profile chỉ thuộc F2 → 404."""
    u1 = register_user(client)
    u2 = register_user(client)
    tok1 = login_access_token(client, u1)
    tok2 = login_access_token(client, u2)

    c1 = client.post(
        "/families",
        json={"family_name": "F1", "full_name": "U1"},
        headers=auth_headers(tok1),
    )
    assert c1.status_code == 201
    f1 = c1.json()["id"]

    c2 = client.post(
        "/families",
        json={"family_name": "F2", "full_name": "U2"},
        headers=auth_headers(tok2),
    )
    assert c2.status_code == 201
    p2 = c2.json()["members"][0]["profile"]["id"]

    r = client.get(f"/profiles/{p2}", headers=auth_headers(tok1))
    assert r.status_code == 403


def test_join_invalid_invite_code_returns_404(client) -> None:
    suf = register_user(client)
    tok = login_access_token(client, suf)
    r = client.post(
        "/families/join",
        json={"invite_code": "not-a-valid-code-xyz", "full_name": "X"},
        headers=auth_headers(tok),
    )
    assert r.status_code == 404


def test_join_twice_same_family_returns_409(client) -> None:
    owner_suf = register_user(client)
    member_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)
    member_tok = login_access_token(client, member_suf)

    cr = client.post(
        "/families",
        json={"family_name": "FamDup", "full_name": "Own"},
        headers=auth_headers(owner_tok),
    )
    assert cr.status_code == 201
    invite = cr.json()["invite_code"]

    j1 = client.post(
        "/families/join",
        json={"invite_code": invite, "full_name": "Mem"},
        headers=auth_headers(member_tok),
    )
    assert j1.status_code == 200

    j2 = client.post(
        "/families/join",
        json={"invite_code": invite, "full_name": "Mem"},
        headers=auth_headers(member_tok),
    )
    assert j2.status_code == 409


def test_rotate_invite_invalidates_old_code(client) -> None:
    owner_suf = register_user(client)
    joiner_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)
    joiner_tok = login_access_token(client, joiner_suf)

    cr = client.post(
        "/families",
        json={"family_name": "FamRot", "full_name": "Own"},
        headers=auth_headers(owner_tok),
    )
    assert cr.status_code == 201
    family_id = cr.json()["id"]
    old_code = cr.json()["invite_code"]

    rot = client.post(
        f"/families/{family_id}/invite/rotate",
        headers=auth_headers(owner_tok),
    )
    assert rot.status_code == 200
    new_code = rot.json()["invite_code"]
    assert new_code != old_code

    late = register_user(client)
    late_tok = login_access_token(client, late)
    bad = client.post(
        "/families/join",
        json={"invite_code": old_code, "full_name": "Late"},
        headers=auth_headers(late_tok),
    )
    assert bad.status_code == 404

    good = client.post(
        "/families/join",
        json={"invite_code": new_code, "full_name": "Late"},
        headers=auth_headers(late_tok),
    )
    assert good.status_code == 200

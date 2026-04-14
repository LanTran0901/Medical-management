"""
SC-001 integration cases (a)(b) — **PostgreSQL only** (Mongo skipped via `tests/integration/conftest.py`).

Mặc định chạy (xem `tests/integration/conftest.py`). Cần Postgres + `.env`.
Tắt nhanh: `HOMEDMEDAI_INTEGRATION=0 pytest tests/integration/`
"""

from __future__ import annotations

import re
import uuid

import pytest

from tests.integration.conftest import integration_disabled
from tests.integration.helpers import auth_headers, login_access_token, register_user

pytestmark = pytest.mark.skipif(
    integration_disabled(),
    reason="Integration disabled (HOMEDMEDAI_INTEGRATION=0) or no Postgres",
)


def test_case_a_random_family_returns_404(client) -> None:
    suf = register_user(client)
    token = login_access_token(client, suf)
    fid = uuid.uuid4()
    r = client.get(
        f"/families/{fid}",
        headers=auth_headers(token),
    )
    assert r.status_code == 404


def test_case_b_member_cannot_rotate_invite(client) -> None:
    owner_suf = register_user(client)
    member_suf = register_user(client)
    owner_tok = login_access_token(client, owner_suf)
    member_tok = login_access_token(client, member_suf)

    cr = client.post(
        "/families",
        json={"family_name": "Home", "full_name": "Owner Name"},
        headers=auth_headers(owner_tok),
    )
    assert cr.status_code == 201, cr.text
    family_id = cr.json()["id"]
    invite = cr.json()["invite_code"]
    assert re.fullmatch(r"[A-Z0-9]{8}", invite)

    jr = client.post(
        "/families/join",
        json={"invite_code": invite, "full_name": "Member Name"},
        headers=auth_headers(member_tok),
    )
    assert jr.status_code == 200, jr.text

    rot = client.post(
        f"/families/{family_id}/invite/rotate",
        headers=auth_headers(member_tok),
    )
    assert rot.status_code == 403

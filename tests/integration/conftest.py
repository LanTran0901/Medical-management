"""
Integration tests: **PostgreSQL only** — không bật MongoDB trong `app.main` lifespan.

Đặt biến trước khi import `app.main` (pytest load conftest trước test modules).
"""

from __future__ import annotations

import os

# Bỏ qua connect_to_mongo / close_mongo — xem app.main.lifespan + SKIP_MONGO_LIFESPAN
os.environ.setdefault("SKIP_MONGO_LIFESPAN", "1")
# Mặc định chạy integration (không cần export). Tắt: HOMEDMEDAI_INTEGRATION=0
os.environ.setdefault("HOMEDMEDAI_INTEGRATION", "1")


def integration_disabled() -> bool:
    """Trả True nếu muốn skip toàn bộ integration (CI nhanh / không có Postgres)."""
    v = os.getenv("HOMEDMEDAI_INTEGRATION", "1").strip().lower()
    return v in ("0", "false", "no", "off")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    from app.main import app

    with TestClient(app) as c:
        yield c

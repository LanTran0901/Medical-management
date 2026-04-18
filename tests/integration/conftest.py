"""
Integration tests: **PostgreSQL only** — không bật MongoDB trong `app.main` lifespan.

Đặt biến trước khi import `app.main` (pytest load conftest trước test modules).

**DB thử nghiệm (tránh đụng Supabase / .env production):**
- Chạy trên **host** (Windows/macOS): mặc định `DATABASE_URL` trỏ Postgres local (vd. port 5432 sau
  `docker compose -f docker-compose.test.yml up -d postgres`). Có thể ghi đè bằng
  `INTEGRATION_DATABASE_URL` hoặc `INTEGRATION_POSTGRES_*`.
- Chạy **trong** container `docker-compose.test.yml`: giữ `DATABASE_URL` do Compose gán (service `postgres`).
"""

from __future__ import annotations

import os
from urllib.parse import quote_plus

# Bỏ qua connect_to_mongo / close_mongo — xem app.main.lifespan + SKIP_MONGO_LIFESPAN
os.environ.setdefault("SKIP_MONGO_LIFESPAN", "1")
# Mặc định chạy integration (không cần export). Tắt: HOMEDMEDAI_INTEGRATION=0
os.environ.setdefault("HOMEDMEDAI_INTEGRATION", "1")
os.environ.setdefault("FIREBASE_CREDENTIALS_PATH", "")
os.environ.setdefault("EXPO_PUSH_ENABLED", "0")
os.environ.setdefault("SCHEDULE_DISPATCH_ENABLED", "0")


def integration_disabled() -> bool:
    """Trả True nếu muốn skip toàn bộ integration (CI nhanh / không có Postgres)."""
    v = os.getenv("HOMEDMEDAI_INTEGRATION", "1").strip().lower()
    return v in ("0", "false", "no", "off")


def _configure_integration_database_url() -> None:
    """
    pydantic-settings đọc DATABASE_URL từ .env nếu không có biến môi trường — dễ trỏ Supabase.

    - Trong Docker (compose test): không ghi đè khi DATABASE_URL đã có (Compose đã set).
    - Trên host: luôn đặt DATABASE_URL cho bộ test (mặc định localhost + DB `medical` như compose.test).
    """
    if integration_disabled():
        return
    if os.getenv("INTEGRATION_USE_PROJECT_ENV", "").strip().lower() in ("1", "true", "yes"):
        # Cho phép dùng .env (kể cả Supabase) nếu cố ý bật — không khuyến nghị.
        return
    in_container = os.path.exists("/.dockerenv")
    explicit = os.getenv("INTEGRATION_DATABASE_URL", "").strip()
    if in_container:
        if explicit:
            os.environ["DATABASE_URL"] = explicit
        elif not os.getenv("DATABASE_URL", "").strip():
            os.environ["DATABASE_URL"] = (
                "postgresql+asyncpg://postgres:postgres@postgres:5432/medical"
            )
        return
    if explicit:
        os.environ["DATABASE_URL"] = explicit
        return
    host = os.getenv("INTEGRATION_POSTGRES_HOST", "localhost")
    port = os.getenv("INTEGRATION_POSTGRES_PORT", "5432")
    db = os.getenv("INTEGRATION_POSTGRES_DB", "medical")
    user = os.getenv("INTEGRATION_POSTGRES_USER", "postgres")
    password = os.getenv("INTEGRATION_POSTGRES_PASSWORD", "postgres")
    u = quote_plus(user)
    p = quote_plus(password)
    os.environ["DATABASE_URL"] = f"postgresql+asyncpg://{u}:{p}@{host}:{port}/{db}"


_configure_integration_database_url()

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    from app.main import app

    with TestClient(app) as c:
        yield c

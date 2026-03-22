"""
Smoke test: PostgreSQL kết nối qua app (Mongo có thể disconnected khi SKIP_MONGO_LIFESPAN=1).
"""

from __future__ import annotations

import pytest

from tests.integration.conftest import integration_disabled

pytestmark = pytest.mark.skipif(
    integration_disabled(),
    reason="Integration disabled (HOMEDMEDAI_INTEGRATION=0) or no Postgres",
)


def test_health_reports_postgres_connected(client) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("postgres") == "connected", data
    # Mongo intentionally not required for these tests
    assert "mongodb" in data

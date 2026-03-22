"""
Shared pytest notes (feature 002 / SC-001).

- **Unit**: `tests/test_*.py` — không cần DB.
- **Integration** (`tests/integration/`): mặc định **bật** (`HOMEDMEDAI_INTEGRATION` mặc định `1` trong `tests/integration/conftest.py`); cần PostgreSQL. Tắt: `HOMEDMEDAI_INTEGRATION=0`. MongoDB **không** cần — `SKIP_MONGO_LIFESPAN=1`.
"""

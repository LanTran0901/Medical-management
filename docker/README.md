# Docker — chạy test (PostgreSQL)

File **`docker-compose.test.yml`** dựng **PostgreSQL** + container **test** (migrate Alembic rồi chạy `pytest`).

- **Không cần MongoDB** — biến `SKIP_MONGO_LIFESPAN=1` (đồng bộ với `tests/integration/conftest.py`).
- Biến môi trường dùng chung: **`docker/test.env`**.

**Integration** (`tests/integration/`): `test_postgres_smoke.py`, `test_auth_users.py`, `test_families_authz.py`, `test_families_more.py`, `helpers.py`.

## Lệnh

Từ thư mục gốc repo (`Medical-management/`):

```bash
docker compose -f docker-compose.test.yml run --rm --build test
```

- `--build`: build lại image API khi code đổi.
- `--rm`: xóa container sau khi chạy.

## Chỉ chạy một nhóm test

```bash
docker compose -f docker-compose.test.yml run --rm --build test \
  sh -c "pip install --no-cache-dir pytest pytest-asyncio pytest-cov && cd /app/app && alembic --config alembic.ini upgrade head && cd /app && pytest tests/test_family_permission.py -v --no-cov"
```

## Ghi chú

- **`pytest.ini`** dùng `pythonpath = .` để `import app` hoạt động trong container (không cần `pip install -e .`).
- **Coverage**: `pytest-cov` + `.coveragerc` — báo cáo terminal + thư mục `htmlcov/` (mở `htmlcov/index.html`). Tắt coverage: `pytest --no-cov`.
- Image `Dockerfile` cài dependency từ `Pipfile.lock`; **pytest / pytest-asyncio / pytest-cov** được cài thêm trong `command` (để không đổi lock file).
- Nếu port Postgres host bị trùng, có thể thêm `ports: ["5433:5432"]` vào service `postgres` trong `docker-compose.test.yml`.

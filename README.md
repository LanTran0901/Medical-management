# Medical Management API

Du an FastAPI theo **Clean Architecture**, su dung **hai database song song**:
- **PostgreSQL** (SQLAlchemy 2 async + Alembic) — Users, Auth, structured data
- **MongoDB** (Motor async) — Medical records, logs, document data

Xem [CLEAN_ARCHITECTURE.md](./CLEAN_ARCHITECTURE.md) de hieu ro kien truc layered va dual-DB pattern.

## Yeu cau

- Python 3.12
- `pipenv` da duoc cai san
- MongoDB dang chay local hoac remote (Atlas)
- PostgreSQL 15+ (local hoac Docker)

## Cai dat

```powershell
pipenv install
```

## Cau hinh moi truong

Tao file `.env` tu mau:

```powershell
copy .env.example .env
```

Noi dung mau trong `.env.example`:

```env
APP_NAME="Medical Management API"

# MongoDB (document store)
MONGODB_URI="mongodb+srv://<username>:<password>@<cluster-url>/<db-name>?retryWrites=true&w=majority&appName=<app-name>"
MONGODB_DB_NAME=""

# PostgreSQL (relational store)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=medical
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

## Chay ung dung (local, khong Docker)

```powershell
# 1. Apply Alembic migrations (PostgreSQL phai dang chay)
pipenv run alembic --config app/alembic.ini upgrade head

# 2. Start API
pipenv run start
```

## Alembic Migrations (PostgreSQL)

```powershell
# Tao migration moi sau khi them/sua ORM model
pipenv run alembic --config app/alembic.ini revision --autogenerate -m "ten_migration"

# Apply migrations
pipenv run alembic --config app/alembic.ini upgrade head

# Rollback 1 buoc
pipenv run alembic --config app/alembic.ini downgrade -1

# Xem lich su migration
pipenv run alembic --config app/alembic.ini history
```

**Luu y khi them model moi:**
1. Tao file ORM model trong `app/infrastructure/config/database/postgres/models/`
2. Import vao `app/infrastructure/config/database/postgres/models/__init__.py`
3. Chay `alembic revision --autogenerate`

## Chay bang Docker (full stack)

```powershell
# Start: postgres -> migrate (alembic upgrade head) -> api
docker compose up -d --build

# Xem logs
docker compose logs -f api
docker compose logs migrate

# Stop
docker compose down
```

**Thu tu khoi dong:**
1. `postgres` — healthcheck passed
2. `migrate` — chay `alembic upgrade head` roi exit
3. `api` — uvicorn start (doi migrate hoan thanh)

## Kiem tra

- API root: `http://127.0.0.1:8080/`
- Health check: `http://127.0.0.1:8080/health` → `{"status":"ok","mongodb":"connected","postgres":"connected"}`
- Swagger UI: `http://127.0.0.1:8080/docs`

## Kien truc

Xem [CLEAN_ARCHITECTURE.md](./CLEAN_ARCHITECTURE.md)

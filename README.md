# Medical Management API

Du an FastAPI theo **Clean Architecture**, su dung **hai database song song**:
- **PostgreSQL** (SQLAlchemy 2 async + Alembic) — Users, Auth, structured data
- **MongoDB** (Motor async) — Medical records, logs, document data

Xem [CLEAN_ARCHITECTURE.md](./CLEAN_ARCHITECTURE.md) de hieu ro kien truc layered va dual-DB pattern.
Xem [FAMILY_API_FE_GUIDE_VI.md](./FAMILY_API_FE_GUIDE_VI.md) de FE goi Family APIs theo contract backend hien tai.

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
GROQ_API_KEY="gsk_xxx"
GROQ_MODEL="llama-3.1-8b-instant"
RAG_CHAT_HISTORY_COLLECTION="rag_chat_history"
RAG_EMBEDDING_MODEL="intfloat/multilingual-e5-small"
RAG_EMBEDDING_DIMENSIONS=384
RAG_TOP_K=6
RAG_PER_TYPE_LIMIT=3
```

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

- API root: `http://127.0.0.1:7543/`
- Health check: `http://127.0.0.1:7543/health` → `{"status":"ok","mongodb":"connected","postgres":"connected"}`
- Swagger UI: `http://127.0.0.1:7543/docs`

## Pytest bang Docker (PostgreSQL — khong can MongoDB)

Dung `docker-compose.test.yml` + `docker/test.env` (bien `SKIP_MONGO_LIFESPAN=1`).

```powershell
docker compose -f docker-compose.test.yml run --rm --build test
```

Chi tiet: [docker/README.md](./docker/README.md)

### Coverage (do phu code)

Can cai `pytest-cov` (chua co trong Pipfile lock mac dinh):

```powershell
pip install pytest pytest-cov
pytest
# Bao cao HTML: mo htmlcov/index.html
# Bo qua coverage (chay nhanh): pytest --no-cov
```

Cau hinh: `.coveragerc` + `pytest.ini` (`addopts` voi `--cov=app`). Muon dua vao Pipfile: them `pytest`, `pytest-cov` vao `[dev-packages]` roi `pipenv lock`.

## Kien truc

Xem [CLEAN_ARCHITECTURE.md](./CLEAN_ARCHITECTURE.md)

## RAG y te voi PostgreSQL

Chatbot `POST /rag/chat` hien tai truy xuat context tu 3 bang PostgreSQL:
- `diseases`
- `drugs`
- `vaccines`

RAG dung `pgvector` de luu embedding ngay tren cac bang nay (`embedding`) va luu van ban phuc vu truy xuat (`search_document`).

### Khoi tao / cap nhat vector

Sau khi migrate xong, hay seed hoac reindex de sinh embedding:

```powershell
# Seed lai tu file JSON va sinh embedding
pipenv run python -m app.scripts.seed_medical_dictionary_pg --per-type 1000

# Hoac backfill embedding cho du lieu da ton tai trong PostgreSQL
pipenv run python -m app.scripts.reindex_medical_dictionary_vectors --batch-size 64
```

Neu muon bo qua sinh embedding khi seed:

```powershell
pipenv run python -m app.scripts.seed_medical_dictionary_pg --per-type 1000 --skip-embeddings
```

## Test luong RAG

Endpoint:

`POST /rag/chat`

Body:

```json
{
  "question": "Lich tiem Gardasil 9 nhu the nao?"
}
```

Ket qua tra ve:
- `answer`: cau tra loi da duoc tong hop tu context noi bo
- `used_context_count`: so nguon da dua vao prompt
- `sources`: danh sach disease/drug/vaccine da duoc truy xuat

Luu y:
- Lich su hoi dap duoc luu theo `user_id` (lay tu access token), khong can gui `session_id` tu client.
- Neu chua co embedding, he thong se fallback sang keyword search tren 3 bang noi bo.

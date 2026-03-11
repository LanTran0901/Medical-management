# Clean Architecture - Medical Management Backend

## Tổng quan

Project được xây dựng theo **Clean Architecture** (kiến trúc sạch), giúp tách biệt các layer, dễ bảo trì, test và mở rộng.  
Điểm đặc biệt của Medical backend: sử dụng **hai database song song**:

| Database | Driver | Mục đích |
|---|---|---|
| **PostgreSQL** | SQLAlchemy 2 async + asyncpg | Dữ liệu có cấu trúc: Users, Auth, RBAC |
| **MongoDB** | Motor (async) | Dữ liệu tài liệu: Medical records, Logs, Reports |

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                            │
│                    (Controllers/Routers)                    │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                        │
│              (Use Cases, DTOs, Ports)                       │
├─────────────────────────────────────────────────────────────┤
│                      Domain Layer                           │
│       (Entities, Value Objects, Domain Services)            │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                      │
│     (Repositories, External Services, Database)             │
│          ┌──────────────┐  ┌──────────────────┐            │
│          │  PostgreSQL   │  │     MongoDB       │           │
│          │  (SQLAlchemy) │  │     (Motor)       │           │
│          └──────────────┘  └──────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

---

## Cấu trúc thư mục

```
Medical-management/
├── .env                        # Environment variables (gitignored)
├── .env.example                # Template — copy to .env
├── Pipfile                     # pipenv dependencies
├── Pipfile.lock
├── Dockerfile
├── docker-compose.yml          # postgres + migrate + api services
│
└── app/                        # 📦 Application root
    ├── main.py                 # Entry point — FastAPI app + dual-DB lifespan
    │
    ├── core/                   # ⚙️ Cross-cutting concerns (config)
    │   └── config.py           # pydantic-settings: MongoDB + PostgreSQL URLs
    │
    ├── alembic.ini             # 🗄️ Alembic config (run from app/ dir)
    ├── alembic/                # 🗄️ Database migrations (PostgreSQL only)
    │   ├── env.py
    │   ├── script.py.mako
    │   └── versions/           # Generated migration files
    │
    ├── api/                    # 🌐 API Layer
    │   ├── __init__.py
    │   └── health_router.py    # Health check endpoint (MongoDB + PostgreSQL)
    │
    ├── application/            # 📋 Application Layer
    │   ├── dtos/               # Data Transfer Objects (request/response models)
    │   ├── ports/              # Interfaces (abstract repository/service contracts)
    │   └── usecases/           # Business logic use cases
    │
    ├── domain/                 # 💎 Domain Layer (Core)
    │   ├── entities/           # Domain entities
    │   │   └── user.py         # User entity (pure Python dataclass)
    │   ├── events/             # Domain events
    │   ├── exceptions/         # Business exceptions
    │   ├── services/           # Domain services
    │   └── value_objects/      # Immutable value objects
    │
    └── infrastructure/         # 🔧 Infrastructure Layer
        ├── config/
        │   └── database/
        │       ├── base.py     # SQLAlchemy DeclarativeBase
        │       ├── postgres/   # ─── PostgreSQL (relational) ───────────────
        │       │   ├── connection.py  # async engine + get_session() dependency
        │       │   └── models/
        │       │       ├── __init__.py   # auto-import for Alembic discovery
        │       │       └── user_model.py # ORM model → users table
        │       └── mongodb/    # ─── MongoDB (document store) ────────────────
        │           └── connection.py  # Motor client + connect/close helpers
        └── repositories/       # Repository implementations (future)
```

---

## Hai Database và khi nào dùng DB nào

### PostgreSQL — Dữ liệu có cấu trúc, quan hệ

Dùng cho dữ liệu cần:
- **Schema cứng** (ALTER TABLE có migration)
- **Foreign keys** và **joins**
- **ACID transactions**
- **Audit / compliance** (ai làm gì, lúc nào)

```
PostgreSQL Tables (qua Alembic migration):
├── users           ← Authentication, profiles
├── roles           ← RBAC roles
├── permissions     ← RBAC permissions
├── ...             ← Future: appointments, billing
```

**Driver**: `SQLAlchemy 2 async` + `asyncpg` (runtime), `psycopg2-binary` (Alembic sync)  
**Migrations**: `Alembic` — xem [Workflow Alembic](#workflow-alembic)

---

### MongoDB — Dữ liệu dạng document, linh hoạt

Dùng cho dữ liệu cần:
- **Schema linh hoạt** (fields thêm/bớt không cần migration)
- **Nested documents** (test results, vitals, notes)
- **High-write throughput** (logs, telemetry)
- **Full-text search** (medical records, reports)

```
MongoDB Collections (schema-free):
├── medical_records    ← Patient visit records, diagnoses
├── diagnostic_reports ← Lab results, imaging reports
├── audit_logs         ← Application event logs
└── ...
```

**Driver**: `Motor` (async Motor client)

---

## Các Layer chi tiết

### 1. Domain Layer (Core) 💎

Layer trung tâm, chứa business logic thuần túy, **không phụ thuộc** vào bất kỳ layer nào khác.

```
domain/
├── entities/
│   └── user.py        # User entity — id, email, status, soft-delete logic
├── value_objects/      # Immutable: Email, PhoneNumber, ...
├── events/             # Domain events: UserCreated, UserDeleted, ...
├── exceptions/         # Business exceptions: UserNotFound, DuplicateEmail, ...
└── services/           # Pure domain logic spanning multiple entities
```

**Nguyên tắc:**
- Không import từ `application`, `infrastructure`, hay `api`
- Chỉ pure Python — không có FastAPI, SQLAlchemy hay Motor
- Entity chứa business rules (e.g. `user.soft_delete()`, `user.is_active`)

---

### 2. Application Layer 📋

Chứa use cases (business workflows), điều phối giữa domain và infrastructure.

```
application/
├── dtos/
│   └── user_dto.py     # CreateUserRequest, UserResponse, ...
├── ports/
│   ├── user_port.py    # IUserRepository (abstract interface)
│   └── record_port.py  # IMedicalRecordRepository (abstract interface)
└── usecases/
    ├── create_user_usecase.py
    ├── get_user_usecase.py
    └── ...
```

**Nguyên tắc:**
- Use cases chứa application-specific business rules
- Phụ thuộc vào **Ports** (abstract interfaces), không phụ thuộc concrete implementations
- Không biết PostgreSQL hay MongoDB đang được dùng ở đâu — đó là việc của Infrastructure

---

### 3. Infrastructure Layer 🔧

Triển khai các interfaces từ Application layer, kết nối với external systems.

```
infrastructure/
├── config/database/
│   ├── base.py                        # SQLAlchemy DeclarativeBase
│   ├── postgres/
│   │   ├── connection.py              # async engine, AsyncSession, get_session()
│   │   └── models/
│   │       ├── __init__.py            # import all models → Alembic tự detect
│   │       └── user_model.py          # UserModel ORM (maps User entity → users table)
│   └── mongodb/
│       └── connection.py              # Motor client, connect_to_mongo(), close_mongo_connection()
└── repositories/
    ├── user_repository_pg.py          # Implement IUserRepository dùng PostgreSQL
    └── record_repository_mongo.py     # Implement IMedicalRecordRepository dùng MongoDB
```

**Nguyên tắc:**
- Implement các Port interfaces từ Application layer
- Chứa toàn bộ framework-specific code (SQLAlchemy models, Motor queries)
- **PostgreSQL ORM models** chỉ ở `infrastructure/` — Domain entities là pure Python

---

### 4. API Layer 🌐

Xử lý HTTP requests, routing, validation.

```
api/
└── health_router.py    # GET /health → {"mongodb": "connected", "postgres": "connected"}
```

**Nguyên tắc:**
- Chỉ handle HTTP concerns (routing, request validation, auth middleware)
- Gọi Use Cases để xử lý business logic
- Transform DTOs thành HTTP responses

---

## Dependency Rule

```
API → Application → Domain ← Infrastructure
         ↓              ↑
         Ports ──────── Adapters
```

- **Domain** không phụ thuộc vào bất kỳ layer nào
- **Application** chỉ phụ thuộc vào Domain (qua Ports)
- **Infrastructure** implement Ports, biết cả Domain lẫn DB frameworks
- **API** phụ thuộc vào Application (gọi Use Cases)
- **core/** là cross-cutting concern — chứa config, được dùng bởi Infrastructure và API

---

## Workflow Alembic

### Yêu cầu

```powershell
pipenv install    # cài alembic, psycopg2-binary, asyncpg, sqlalchemy
```

### Tạo migration mới

```powershell
# Từ thư mục gốc project (có Pipfile):
cd d:\WDA\Medical-management

# autogenerate so sánh Base.metadata với schema hiện tại của DB
pipenv run alembic --config app/alembic.ini revision --autogenerate -m "create_users_table"
```

Hoặc nếu bạn đã `cd app/`:

```powershell
cd app
pipenv run alembic revision --autogenerate -m "create_users_table"
```

### Apply migrations

```powershell
# Từ thư mục app/ hoặc dùng --config
pipenv run alembic --config app/alembic.ini upgrade head
```

### Rollback

```powershell
pipenv run alembic --config app/alembic.ini downgrade -1
```

### Kiểm tra trạng thái

```powershell
pipenv run alembic --config app/alembic.ini current
pipenv run alembic --config app/alembic.ini history
```

### Thêm ORM model mới → Alembic tự detect

1. Tạo `app/infrastructure/config/database/postgres/models/my_model.py`  
2. Import nó vào `app/infrastructure/config/database/postgres/models/__init__.py`:
   ```python
   from app.infrastructure.config.database.postgres.models.my_model import MyModel  # noqa: F401
   ```
3. Chạy `alembic revision --autogenerate -m "add_my_table"`

---

## Ví dụ Flow: Tạo User

```
1. [API] api/user_router.py
   └── Nhận HTTP POST /users
   └── Validate input với Pydantic DTO
   └── Gọi CreateUserUseCase(user_repo_port)

2. [Application] application/usecases/create_user_usecase.py
   └── Nhận CreateUserRequest DTO
   └── Kiểm tra email trùng (qua IUserRepository.exists_by_email)
   └── Tạo User entity (User.create(...))
   └── Gọi IUserRepository.save(user)

3. [Infrastructure] infrastructure/repositories/user_repository_pg.py
   └── Implement IUserRepository
   └── Convert User entity → UserModel ORM
   └── INSERT INTO users ... (PostgreSQL via AsyncSession)

4. [Domain] domain/entities/user.py
   └── User.create() — validate email, set status=active, generated uuid
```

---

## Ví dụ Flow: Lưu Medical Record (MongoDB)

```
1. [API] api/record_router.py
   └── Nhận HTTP POST /records
   └── Gọi CreateMedicalRecordUseCase(record_repo_port)

2. [Application] application/usecases/create_medical_record_usecase.py
   └── Nhận DTO
   └── Gọi IMedicalRecordRepository.save(record)

3. [Infrastructure] infrastructure/repositories/record_repository_mongo.py
   └── Implement IMedicalRecordRepository
   └── db["medical_records"].insert_one({...})
   └── MongoDB — schema linh hoạt, nested documents

4. [Domain] domain/entities/medical_record.py  (future)
   └── Entity với business validations
```

---

## Chạy ứng dụng

### Local (không Docker)

```powershell
# 1. Tạo .env từ template
copy .env.example .env
# Điền MONGODB_URI, POSTGRES_* vào .env

# 2. Cài dependencies
pipenv install

# 3. Apply migrations (PostgreSQL phải đang chạy)
pipenv run alembic --config app/alembic.ini upgrade head

# 4. Start API
pipenv run start
# → http://localhost:8080/
# → http://localhost:8080/health
# → http://localhost:8080/docs
```

### Docker (full stack)

```powershell
# Build + start: postgres → migrate → api
docker compose up -d --build

# Xem logs
docker compose logs -f api
docker compose logs migrate

# Stop
docker compose down
```

**Thứ tự khởi động Docker:**
1. `postgres` — healthcheck `pg_isready` passed
2. `migrate` — `alembic upgrade head` (one-shot, exit 0)
3. `api` — uvicorn starts (depends_on migrate completed_successfully)

---

## Lợi ích

✅ **Testability**: Mock `IUserRepository` để test use cases độc lập với DB  
✅ **Dual-DB**: PostgreSQL và MongoDB có thể swap độc lập — business logic không đổi  
✅ **Migrations**: Alembic quản lý PostgreSQL schema changes có version history  
✅ **Flexibility**: Thêm table mới → chỉ cần thêm ORM model + `alembic revision --autogenerate`  
✅ **Pipenv**: Dependency locking nhất quán giữa dev và production

---

## Best Practices

1. **Ports/Adapters**: Mỗi external service (PostgreSQL, MongoDB, email, S3) phải có Port (interface) trong `application/ports/` và Adapter (implementation) trong `infrastructure/`
2. **DTOs không expose Domain Entities**: API trả về DTO, không trả `User` entity trực tiếp
3. **Alembic cho PostgreSQL only**: MongoDB là schema-free, không cần migration
4. **Config Isolation**: `core/config.py` được import trong Infrastructure và API layers, **không** trong Domain/Application
5. **Model ≠ Entity**: `UserModel` (SQLAlchemy ORM) ≠ `User` (domain entity) — repository convert giữa hai
6. **Testing**: Unit test Domain + Application layers; Integration test Infrastructure với test DB

---

## References

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic Autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- [Motor (async MongoDB)](https://motor.readthedocs.io/en/stable/)

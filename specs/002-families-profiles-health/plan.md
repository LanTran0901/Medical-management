# Implementation Plan: Families, Profiles & Health Details API

**Branch**: `002-families-profiles-health` | **Date**: 2026-03-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-families-profiles-health/spec.md`  
**Bối cảnh thêm**: DB đã có migration (Alembic) cho `families`, `family_memberships`, `profiles`, `health_details`; auth đăng ký/đăng nhập đã có (`/auth/*`). Kiến trúc: [CLEAN_ARCHITECTURE.md](../../CLEAN_ARCHITECTURE.md).

## Summary

Triển khai **REST API** (FastAPI) cho quản lý **gia đình**, **thành viên (membership)**, **hồ sơ profile** và **health_details**, bảo vệ bằng JWT hiện có. Dữ liệu **chỉ PostgreSQL** (SQLAlchemy 2 async); **không** dùng MongoDB cho cụm này.  
Luồng chính: tạo gia đình + OWNER, mời/rotate `invite_code`, **POST join** bằng mã, CRUD profile + link profile ảo, upsert health_details — tuân **404/403** và soft-delete profile + xử lý membership trong **một transaction** đã chốt trong spec.

## Technical Context

**Language/Version**: Python 3.x (theo Pipfile dự án)  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2 async, asyncpg  
**Storage**: PostgreSQL only cho feature này (bảng đã tồn tại qua Alembic; không migration mới trừ khi phát hiện lệch schema)  
**Testing**: pytest (unit use case + integration API với DB test nếu có)  
**Target Platform**: API server (Docker / local)  
**Project Type**: Backend web-service (mobile consumer)  
**Performance Goals**: p95 < 300ms cho CRUD đơn giản dưới tải MVP  
**Constraints**: Mọi route (trừ public sẵn có) cần user đã xác thực; phân quyền theo `family_role` trên membership  
**Scale/Scope**: MVP — số gia đình/profile theo user hợp lý (<100 profile/user)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá |
|-------------|----------|
| **I. Profile-centric** | Đạt — mọi API health/membership gắn `profile_id` / `family_id`; `owner_user_id` trên profile. |
| **II. Medical safety & privacy** | Đạt — auth bắt buộc; 404/403 theo phạm vi; không lộ tài nguyên ngoài gia đình. |
| **III. Reminder reliability** | N/A cho spec 002 (thuộc 005). |
| **IV. Clean Architecture + DB** | Đạt — PostgreSQL cho quan hệ; MongoDB **không** dùng cho cụm này (ghi rõ trong plan/research). |
| **V. MVP-first** | Đạt — phạm vi chỉ family/profile/health; không mở rộng tủ thuốc/lịch. |

**Kết luận gate**: **PASS** — không cần Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/002-families-profiles-health/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── README.md
└── tasks.md              # /speckit.tasks
```

### Source Code (repository root)

```text
Medical-management/app/
├── api/
│   ├── user_router.py              # Bổ sung GET /users/me (FR-013 / T037) trước /{user_id}
│   └── families_router.py          # NEW: prefix /families (hoặc tách profiles_router)
├── application/
│   ├── dtos/
│   │   └── family_dto.py           # NEW
│   ├── ports/
│   │   └── family_port.py          # NEW — repository interfaces
│   └── usecases/
│       └── family_usecases.py      # NEW — orchestration
├── domain/
│   ├── entities/
│   │   ├── family.py               # NEW
│   │   ├── profile.py              # NEW
│   │   └── health_detail.py        # NEW (hoặc gộp value object)
│   └── services/
│       └── family_permission.py    # NEW — optional pure rules
└── infrastructure/
    └── config/database/postgres/models/
        ├── family_models.py        # NEW — Family, FamilyMembership ORM
        ├── profile_models.py       # NEW — Profile, HealthDetail ORM
        └── __init__.py             # import models cho Alembic
    └── repositories/
        └── family_repository_pg.py # NEW
```

**Structure Decision**: Một router nhóm **`/families`** làm trục (nested `/families/{id}/profiles` tùy chọn) hoặc tách **`/profiles`** riêng — chốt trong `research.md` (đề xuất: `/families` + resource con để mirror domain). Giữ đúng **CLEAN_ARCHITECTURE**: router mỏng → use case → port → repository PG.

## Phase 0 — Research (tóm tắt)

Xem [research.md](./research.md) — không còn NEEDS CLARIFICATION chặn triển khai.

## Phase 1 — Design outputs

- [data-model.md](./data-model.md) — entity, quan hệ, rule validation.
- [contracts/README.md](./contracts/README.md) — danh sách endpoint + mã lỗi.
- [quickstart.md](./quickstart.md) — gọi API sau khi có token.

## Phase 2

**Không** tạo `tasks.md` trong bước plan — dùng **`/speckit.tasks`** sau.

## Post-design Constitution Check

Thiết kế giữ PostgreSQL cho toàn bộ dữ liệu quan hệ; không thêm Mongo cho feature này. **PASS**.

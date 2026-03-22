# Tasks: Families, Profiles & Health (002)

**Input**: `spec.md`, `plan.md`, `data-model.md`, `contracts/README.md`, `research.md`, `quickstart.md`  
**Prerequisites**: Alembic migration `20260321_120000_homemedai_core_schema` (families, profiles, health_details, memberships).

**Tests**: **SC-001** bắt buộc **pytest integration** cho các case phân quyền đã liệt kê trong `spec.md`. Luồng nghiệp vụ vẫn có thể bổ sung kiểm thử thủ công theo `quickstart.md`.

**Organization**: Tasks được nhóm theo user story để triển khai và kiểm thử độc lập.

## Format

- `[P]` — có thể song song (file/domain khác nhau).
- `[US1]` / `[US2]` / `[US3]` — gắn user story từ spec.
- Mỗi task có ID `Txxx` để tham chiếu.

---

## Phase 1: Setup (xác nhận schema & cấu trúc)

**Purpose**: Đảm bảo DB và cấu trúc thư mục sẵn sàng trước khi code domain.

- [ ] **T001** Xác nhận migration head bao gồm bảng `families`, `profiles`, `family_memberships`, `health_details` (đối chiếu `alembic/versions/20260321_120000_homemedai_core_schema.py` với `data-model.md`).
- [ ] **T002** Đối chiếu ORM `UserModel` / `user_devices` / `refresh_tokens` với migration hiện tại (đã chỉnh trong thread trước); ghi chú nếu còn drift.
- [X] **T003** [P] Tạo stub package nếu thiếu: `app/domain/entities/`, `app/application/ports/`, `app/application/dtos/`, `app/infrastructure/repositories/` (theo `CLEAN_ARCHITECTURE.md`).

---

## Phase 2: Foundational (blocking — phải xong trước user stories)

**Purpose**: Domain types, ports, ORM, repository, quyền — nền cho mọi endpoint.

- [X] **T004** [P] Tạo `app/domain/entities/family.py` — dataclass/entity: `Family`, `FamilyMembership`, role enum (OWNER/ADMIN/MEMBER), invite fields.
- [X] **T005** [P] Tạo `app/domain/entities/profile.py` — `Profile`, `kind` (PERSONAL/VIRTUAL), `linked_user_id`, soft-delete flag.
- [X] **T006** [P] Tạo `app/domain/entities/health_detail.py` — `HealthDetail` (profile_id, allergies, conditions, medications, notes, updated_at).
- [X] **T007** Tạo `app/application/ports/family_port.py` — `IFamilyRepository` (async): families, memberships, profiles, health CRUD + join/invite/rotate + soft-delete profile (theo `plan.md`).
- [X] **T008** Tạo `app/infrastructure/config/database/postgres/models/family_models.py` — SQLAlchemy `FamilyModel`, `FamilyMembershipModel` map đúng cột migration (UUID, enums text/jsonb).
- [X] **T009** Tạo `app/infrastructure/config/database/postgres/models/profile_models.py` — `ProfileModel`, `HealthDetailModel` + quan hệ tới `UserModel` / `FamilyModel` như migration.
- [X] **T010** Cập nhật `app/infrastructure/config/database/postgres/models/__init__.py` export models mới (để metadata/Alembic autogenerate nhất quán nếu dùng).
- [X] **T011** Tạo `app/infrastructure/repositories/family_repository_pg.py` — implement `IFamilyRepository` (async session), map ORM ↔ entity; transaction cho soft-delete profile + cập nhật membership.
- [X] **T012** Tạo `app/domain/services/family_permission.py` — pure helpers: kiểm tra role (OWNER/ADMIN/MEMBER), quy tắc 403 vs 404 (không trong scope → 404; trong scope thiếu quyền → 403).
- [X] **T013** Tạo `app/application/dtos/family_dto.py` — Pydantic request/response: create family, join, rotate invite, profile create, link shadow, health PATCH (khớp `contracts/README.md`).
- [X] **T014** Mở rộng `app/api/dependencies.py` — `get_family_repository()` (hoặc inject qua `Annotated`), helper `get_current_user` đã có; thêm dependency parse `family_id` + kiểm tra membership khi cần.
- [X] **T037** [P] **`GET /users/me`** trong `app/api/user_router.py` — `Depends(get_current_user)`, response giống `GET /users/{user_id}` (reuse `GetUserUseCase` hoặc map `UserResponse.from_entity`); **đặt handler `/me` trước** `/{user_id}`; khớp **FR-013** + bảng Users trong `contracts/README.md`.

**Checkpoint**: Foundation compile/import; repository gọi được DB (có thể smoke test một query đơn giản).

---

## Phase 3: User Story 1 — Tạo gia đình, mã mời, tham gia (Priority: P1) 🎯 MVP

**Goal**: User tạo family, nhận `invite_code`, tham gia bằng code; OWNER xoay mã.

**Independent test**: Tạo 2 user → user A tạo family → user B join bằng code → B thấy family trong danh sách.

- [X] **T015** [US1] Trong `app/application/usecases/family_usecases.py` (hoặc `family_usecases/`): `CreateFamilyUseCase` — tạo family, sinh `invite_code` (research: secrets token_urlsafe), OWNER membership, optional tạo PERSONAL profile + membership (theo spec).
- [X] **T016** [US1] `RotateInviteUseCase` — chỉ OWNER; cập nhật `invite_code` + `invite_rotated_at`; mã cũ vô hiệu.
- [X] **T017** [US1] `JoinFamilyByCodeUseCase` — validate code; nếu đã có PERSONAL profile với `linked_user_id` → reuse + thêm membership; else tạo profile + membership (MEMBER).
- [X] **T018** [US1] Tạo `app/api/families_router.py` — `POST /families`, `POST /families/join`, `POST /families/{family_id}/invite/rotate` (response/error theo `contracts/README.md`).
- [X] **T019** [US1] Đăng ký router trong `app/main.py` — `app.include_router(families_router, prefix=settings.API_V1_PREFIX)` (hoặc prefix đã dùng trong project).
- [X] **T020** [US1] Xử lý lỗi thống nhất: 401 (auth), 404 (family/code/membership), 403 (role), 409 nếu có conflict (document trong contracts).

**Checkpoint**: US1 chạy được end-to-end theo `quickstart.md` (phần create/join/rotate).

---

## Phase 4: User Story 2 — Hồ sơ trong gia đình & liên kết (Priority: P2)

**Goal**: CRUD profile trong family, membership, OWNER/ADMIN link shadow profile tới user.

**Independent test**: ADMIN tạo VIRTUAL profile → link tới user B → B thấy đúng `linked_user_id`; soft-delete gỡ membership.

- [X] **T021** [US2] Use cases: `ListFamiliesForUser`, `GetFamily` (detail + members list theo spec visibility).
- [X] **T022** [US2] `CreateProfileInFamilyUseCase` — PERSONAL vs VIRTUAL rules; ADMIN/OWNER tạo VIRTUAL; user tạo PERSONAL cho chính mình nếu spec cho phép.
- [X] **T023** [US2] `AddOrUpdateMembershipUseCase` — thay đổi role (OWNER/ADMIN) cho `membership_id` (khóa `family_memberships.id`); khớp `PATCH /families/{family_id}/members/{membership_id}` trong contracts.
- [X] **T024** [US2] `LinkShadowProfileUseCase` — PATCH link; kiểm tra `linked_user_id` global unique; chỉ OWNER/ADMIN.
- [X] **T025** [US2] `SoftDeleteProfileUseCase` — transaction: soft-delete profile + remove/suspend memberships liên quan.
- [X] **T026** [US2] Mở rộng `families_router.py` **đúng bảng** `contracts/README.md` (segment **`members`**, param **`membership_id`**): `GET /families`, `GET /families/{family_id}`, `PATCH /families/{family_id}` (đổi tên, OWNER/ADMIN), `GET /families/{family_id}/members`, `PATCH /families/{family_id}/members/{membership_id}`, `DELETE /families/{family_id}/members/{membership_id}`, `POST /families/{family_id}/profiles`, `GET /families/{family_id}/profiles`, `GET /families/{family_id}/profiles/{profile_id}`, `PATCH /families/{family_id}/profiles/{profile_id}`, `DELETE /families/{family_id}/profiles/{profile_id}`, `PATCH /families/{family_id}/profiles/{profile_id}/link`.

**Checkpoint**: US2 scenarios trong `quickstart.md` (profiles, link, soft-delete).

---

## Phase 5: User Story 3 — Chi tiết sức khỏe (Priority: P3)

**Goal**: GET/PATCH health_details theo profile trong family.

**Independent test**: MEMBER xem/sửa health của profile mình; ADMIN xem/sửa theo quyền; VIRTUAL do ADMIN/OWNER quản lý.

- [X] **T027** [US3] `GetHealthDetailsUseCase` / `UpsertHealthDetailsUseCase` — enforce permission qua `family_permission` + membership.
- [X] **T028** [US3] Routes: `GET/PATCH /families/{family_id}/profiles/{profile_id}/health` trong `families_router.py` (hoặc `health_router` con cùng prefix).
- [X] **T029** [US3] Map JSON fields ↔ `HealthDetail` entity; `updated_at` cập nhật khi PATCH.

**Checkpoint**: US3 trong `quickstart.md` (health read/update).

---

## Phase 6: Polish & cross-cutting

**Purpose**: Tài liệu API, nhất quán error model, dọn code.

- [ ] **T030** [P] Mô tả `summary`/`description` trên các endpoint FastAPI để OpenAPI rõ ràng (tiếng Anh hoặc theo convention project).
- [X] **T031** Đảm bảo mọi response lỗi dùng cùng schema với routers hiện có (`HTTPException` + detail format).
- [ ] **T032** [P] Cập nhật `specs/002-families-profiles-health/quickstart.md` nếu path/param thực tế lệch so với bản nháp.
- [ ] **T033** Rà soát `research.md` (invite entropy, transaction) đã phản ánh trong code (comment ngắn nếu cần).

---

## Phase 7: Automated integration tests (SC-001)

**Purpose**: Đáp ứng **SC-001** — suite pytest cố định các case 403/404 cốt lõi (không thay thế toàn bộ manual QA).

- [X] **T034** [P] Thêm `tests/conftest.py` (và tùy chọn `tests/integration/`): fixture `AsyncClient` + app FastAPI, session DB test (transaction/rollback hoặc DB riêng theo hướng dẫn deploy local trong repo).
- [X] **T035** Tạo `tests/integration/test_families_authz.py`: implement đủ các case (a)–(d) trong **SC-001** `spec.md` (bổ sung (c)(d) sau khi T028 xong nếu chạy suite theo phase); tối thiểu sau US1 phải có (a) + (b).
- [X] **T036** [P] Ghi trong `README.md` hoặc `quickstart.md` lệnh chạy `pytest tests/`; đảm bảo `pytest.ini` (`testpaths = tests`) khớp cấu trúc.

---

## Dependencies & execution order

```text
Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6
         → Phase 7 (T035 mở rộng dần; T034 sớm sau khi có app testable)
```

**Parallel opportunities**:

- T004–T006 có thể song song (entities khác file).
- T008–T009 song song (family_models vs profile_models) sau T007 interface sketch.
- T030–T032 song song ở Phase 6.
- T034, T036 song song khi bắt đầu Phase 7.

---

## Implementation strategy

### MVP first (chỉ US1)

1. Hoàn thành Phase 1–2.  
2. Phase 3 (US1) — ship tạo family + join + rotate.  
3. Phase 7 tối thiểu: **T034** + **T035** với case (a)(b) SC-001.  
4. Phase 6 tối thiểu (T031 error consistency).

### Incremental delivery

1. US1 → deploy / demo.  
2. US2 → profiles & link.  
3. US3 → health.  
4. Mở rộng **T035** (case (c)(d) SC-001) khi có route health / profile cross-family.  
5. Polish.

---

## Summary

| Metric | Value |
|--------|--------|
| **Total tasks** | 37 |
| **US1 tasks** | 6 (T015–T020) |
| **US2 tasks** | 6 (T021–T026) |
| **US3 tasks** | 3 (T027–T029) |
| **SC-001 / tests** | 3 (T034–T036) |
| **Users / session** | 1 (T037 — `GET /users/me`) |
| **Parallelizable** | ~12 tasks (marked [P]) |

**Suggested MVP scope**: Phase 1 + Phase 2 + Phase 3 + Phase 7 (T034, T035 tối thiểu) + T031.

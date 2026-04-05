# Hướng dẫn chạy test

Thư mục `tests/` gồm **unit** và **integration** (PostgreSQL). Integration được bật mặc định qua biến môi trường; xem `tests/integration/conftest.py`.

## Một lệnh chạy hết (khuyến nghị)

**Trên host** (đã có Postgres phù hợp `DATABASE_URL` / `INTEGRATION_*` trong `tests/integration/conftest.py`):

```bash
python scripts/run_all_tests.py
```

Hoặc qua Pipenv:

```bash
pipenv run test-all
```

Script sẽ **lần lượt**: `alembic upgrade head` (trong thư mục `app/`) → `pytest tests/ -v --tb=short --no-cov` (từ thư mục gốc repo). Không cần chạy riêng Alembic rồi mới pytest.

- Thêm coverage (theo `pytest.ini`): `python scripts/run_all_tests.py --cov`
- Truyền thêm cho pytest: `python scripts/run_all_tests.py -- -k smoke -x`

**Docker** (Postgres + migrate + full suite trong một `run`):

```bash
docker compose -f docker-compose.test.yml run --rm test
```

Container gọi cùng `scripts/run_all_tests.py`.

**Lưu ý skip:** mỗi file `tests/integration/*` dùng `skipif(integration_disabled())`. Chỉ khi `HOMEDMEDAI_INTEGRATION=0` thì integration bị bỏ qua. Xem lý do skip: `pytest tests/ -q --no-cov -rs`.

## Kịch bản test (theo file)

| File | Loại | Kịch bản chính |
|------|------|----------------|
| `tests/test_family_permission.py` | Unit | Thứ tự rank role family; `has_at_least`. |
| `tests/unit/test_auth_register_usecase.py` | Unit | Register: trùng SĐT; lưu `phone_number`. |
| `tests/unit/test_family_dto.py` | Unit | DTO `HealthDetail`, `Family`, `Membership`, `Profile` map từ entity. |
| `tests/unit/test_families_router_errors.py` | Unit | `_handle_family_error` → HTTP 404/403/409/400. |
| `tests/unit/test_families_service.py` | Unit | `FamiliesService` + `AccessControlService` (mock `FamilyRepositoryPort` + `AccessControlPort`): join/preview/consume public invite, invite by phone, profiles, health, patch/delete membership & profile. |
| `tests/unit/test_owner_access_rules.py` | Unit | Access control: member family, xóa membership, đọc profile, transfer OWNER. |
| `tests/unit/test_rag_route.py` | Unit | Route RAG chat trả `sources`. |
| `tests/unit/test_rag_support.py` | Unit | `build_search_document`, format context RAG. |
| `tests/integration/test_auth_users.py` | Integration | Đăng ký/đăng nhập; `GET /users/me` (bundle user + profile + health); 401 không token. |
| `tests/integration/test_postgres_smoke.py` | Integration | Health check app báo Postgres kết nối được. |
| `tests/integration/test_families_authz.py` | Integration | SC-001: family không tồn tại → 404; MEMBER không rotate invite. |
| `tests/integration/test_families_more.py` | Integration | Member sửa health người khác forbidden; đọc health của mình; join/rotate invite; profile ngoài scope 403. |
| `tests/integration/test_families_personal_preview.py` | Integration | Personal profile + join không tạo profile trùng; preview invite hợp lệ / không hợp lệ. |
| `tests/integration/test_families_public_invite_tokens.py` | Integration | Mã mời public single-use; preview sau consume; join khi token hết hạn (TTL). |
| `tests/integration/test_families_invite_by_phone.py` | Integration | Mời theo SĐT (dry_run, conflict, quyền OWNER/MEMBER, full_name khi chưa có profile). |
| `tests/integration/test_families_invite_link_profile.py` | Integration | `linkable-profiles` + `link-profile` theo invite; consume mã; 410 khi hết hạn. |

## Cách 1: Docker (Postgres + full suite một lần)

Từ **thư mục gốc** repo `Medical-management` (nơi có `docker-compose.test.yml`):

```bash
# Build lại image test nếu đổi Pipfile / Dockerfile / thiếu dependency (vd. pgvector)
docker compose -f docker-compose.test.yml build --no-cache test

# Một lần: migrate + toàn bộ pytest (qua scripts/run_all_tests.py)
docker compose -f docker-compose.test.yml run --rm test
```

- Service **postgres** dùng image `pgvector/pgvector:pg16` vì migration có `CREATE EXTENSION vector`.
- Image **test** cài dependency từ `Pipfile.lock` và **pin thêm** `pgvector` (Python) để Alembic import được `pgvector.sqlalchemy.VECTOR`.

Xóa volume DB test khi cần DB trống:

```bash
docker compose -f docker-compose.test.yml down -v --remove-orphans
```

Chỉ chạy một file (ví dụ unit, không cần nâng full stack nếu test không đụng DB):

```bash
docker compose -f docker-compose.test.yml run --rm test \
  sh -c "cd /app && pytest tests/test_family_permission.py -v --tb=short --no-cov"
```

Chỉ một phần (ví dụ chỉ integration — vẫn chạy Alembic một lần trước):

```bash
docker compose -f docker-compose.test.yml run --rm test \
  sh -c "cd /app && python scripts/run_all_tests.py -- tests/integration/"
```

## Cách 2: Trên máy (host) với Postgres local

1. Cài dependency: `pipenv install` (hoặc theo README dự án).
2. Chạy Postgres local (port 5432, DB `medical`, …) hoặc `docker compose -f docker-compose.test.yml up -d postgres`.
3. `conftest` integration mặc định **ghi đè** `DATABASE_URL` — xem `INTEGRATION_POSTGRES_*` và `INTEGRATION_DATABASE_URL` trong `tests/integration/conftest.py`.
4. **Một lệnh** migrate + pytest: `python scripts/run_all_tests.py` hoặc `pipenv run test-all`.

Tắt integration (chỉ chạy test không cần DB):

```bash
set HOMEDMEDAI_INTEGRATION=0
pytest tests/ -v --no-cov
```

(Trên Linux/macOS: `export HOMEDMEDAI_INTEGRATION=0`.)

## Biến môi trường quan trọng

| Biến | Ý nghĩa |
|------|--------|
| `HOMEDMEDAI_INTEGRATION` | `0` / `false` — bỏ qua toàn bộ integration cần Postgres. |
| `SKIP_MONGO_LIFESPAN` | Đặt `1` khi chạy test (conftest đã set mặc định). |
| `INTEGRATION_DATABASE_URL` | URL Postgres đầy đủ cho integration trên host. |
| `INTEGRATION_USE_PROJECT_ENV=1` | Dùng `DATABASE_URL` từ `.env` (kể cả remote); **không khuyến nghị** cho DB production. |

## Sự cố thường gặp

- **`ModuleNotFoundError: No module named 'pgvector'`** khi chạy Alembic trong container: build lại image test **`--no-cache`**; Dockerfile đã cài thêm `pgvector==0.4.2` sau `pipenv`.
- **Lỗi extension `vector` trên Postgres**: dùng đúng image `pgvector/pgvector` trong `docker-compose.test.yml`, không thay bằng `postgres:alpine` thuần nếu chạy full migration.
- **Coverage chậm**: `run_all_tests.py` mặc định có `--no-cov`; bật coverage: `python scripts/run_all_tests.py --cov`.

## Cấu trúc nhanh

- `tests/integration/` — API + DB thật, client `TestClient`.
- `tests/unit/` hoặc file `tests/test_*.py` — logic không cần DB (tùy repo).

Helper đăng ký / login: `tests/integration/helpers.py`.

---

## Phụ lục: Danh mục testcase chi tiết (theo file)

Mục **Kịch bản test (theo file)** ở đầu tài liệu là **bảng tóm tắt** theo file. Phần dưới liệt kê **từng hàm `test_*`**: tên test và hành vi / kết quả kỳ vọng. Khi thêm hoặc đổi tên test, cập nhật mục này hoặc đối chiếu:

```bash
pytest tests/ --collect-only -q
```

### `tests/test_family_permission.py` (unit — không DB)

- **`test_role_rank_order`** — `role_rank(OWNER) > ADMIN > MEMBER`.
- **`test_has_at_least`** — OWNER/ADMIN đủ quyền so với MEMBER; MEMBER không đủ quyền so với ADMIN.

### `tests/unit/test_auth_register_usecase.py` (unit)

- **`test_register_usecase_rejects_duplicate_phone`** — `RegisterUseCase` từ chối khi SĐT đã tồn tại (`ValueError` khớp “phone number”).
- **`test_register_usecase_persists_phone_number`** — Đăng ký mới: user được tạo kèm `phone_number` đúng request.

### `tests/unit/test_family_dto.py` (unit)

- **`test_health_detail_response_from_entity`** — DTO health map từ entity.
- **`test_family_response_and_summary_from_entity`** — Response/summary family map từ entity.
- **`test_membership_response_from_entity_with_optional_fields`** — Membership DTO, gồm field tùy chọn.
- **`test_profile_response_from_entity`** — Profile DTO map từ entity.

### `tests/unit/test_families_router_errors.py` (unit)

- **`test_handle_not_found_default_detail`** — `NotFoundError` rỗng → HTTP 404, detail mặc định `"Not found"`.
- **`test_handle_not_found_custom_message`** — `NotFoundError` có message → 404, detail đúng message.
- **`test_handle_forbidden_and_conflict_and_value`** — `ForbiddenError` → 403; `ConflictError` → 409; `ValueError` → 400.
- **`test_handle_unknown_exception_does_not_raise`** — Exception không map → không ném `HTTPException`.

### `tests/unit/test_families_service.py` (unit — mock repo + `AccessControlService`)

**Gia đình & quyền cơ bản**

- **`test_create_family_delegates`** — `create_family` ủy quyền `create_family_with_owner_profile`, trả tuple đúng.
- **`test_get_family_raises_when_family_missing`** — Đã là member nhưng `get_family` trả `None` → `NotFoundError` “Family not found”.
- **`test_get_family_not_found_when_family_row_missing`** — Cùng kịch bản inconsistency membership vs row family.
- **`test_get_family_ok`** — Member hợp lệ + có family → trả `Family`.
- **`test_membership_or_404_raises_forbidden_when_family_exists`** — Không membership nhưng family tồn tại → `ForbiddenError` “Not a member”.
- **`test_patch_family_forbidden_for_member`** — MEMBER không được `patch_family`.
- **`test_patch_family_ok`** — ADMIN cập nhật tên family thành công.
- **`test_patch_family_not_found_after_update`** — `update_family_name` trả `None` → `NotFoundError`.
- **`test_list_my_families`** — Ủy quyền `list_families_for_user`.

**Join bằng mã public invite**

- **`test_join_invalid_code`** — `preview_public_invite` không có → `NotFoundError` (invalid code).
- **`test_join_requires_full_name_when_no_profile`** — Chưa có personal profile, thiếu `full_name` → `ValueError`.
- **`test_join_conflict_when_already_member`** — Đã có membership → `ConflictError`.
- **`test_join_conflict_on_integrity`** — `create_membership` ném `IntegrityError` → `ConflictError`.
- **`test_join_creates_personal_profile`** — Chưa profile: tạo personal, consume invite, tạo membership; response dict đúng field; `create_personal_profile` được gọi.

**Mời theo SĐT**

- **`test_invite_by_phone_forbidden_for_member`** — MEMBER không được mời.
- **`test_invite_by_phone_unknown_number_creates_invite_without_user_id`** — Số chưa có user → tạo invite, `user_id` có thể `None`; response dict.
- **`test_invite_by_phone_requires_full_name_when_no_personal_profile`** — User được mời đã tồn tại nhưng chưa có personal profile, request thiếu `full_name` → `ValueError` (khớp `full_name`).
- **`test_invite_by_phone_conflict_when_already_member`** — User đã là member → `ConflictError`.
- **`test_invite_by_phone_success`** — OWNER, user tồn tại, chưa member → dict `dry_run`/`invite`/`family`; `create_family_invite` được gọi.

**Rotate invite**

- **`test_rotate_forbidden_not_owner`** — MEMBER không rotate.
- **`test_rotate_invite_ok`** — OWNER, `rotate_invite` trả family.
- **`test_rotate_invite_family_missing`** — `rotate_invite` repo trả `None` → `NotFoundError`.

**Membership (đổi role / xóa)**

- **`test_patch_membership_not_owner`** — ADMIN (không phải OWNER) không được sửa role membership → `ForbiddenError`.
- **`test_patch_membership_ok`** — OWNER đổi role (không phải transfer) → membership cập nhật.
- **`test_patch_membership_not_found_wrong_family`** — `get_membership` `None` → `NotFoundError`.
- **`test_patch_membership_update_returns_none`** — `update_membership_role` trả `None` → `NotFoundError`.
- **`test_delete_membership_self`** — User xóa membership của chính mình (linked profile khớp).
- **`test_delete_membership_not_in_family`** / **`test_delete_membership_target_missing`** — Không tìm thấy membership → `NotFoundError`.
- **`test_delete_membership_admin_removes_other`** — ADMIN xóa membership người khác.
- **`test_delete_membership_forbidden_non_admin_non_self`** — MEMBER không xóa được membership người khác.

**Thành viên danh sách**

- **`test_list_members_delegates`** — Sau `require_family_member`, gọi `list_members_rows`.

**Profile: tạo / xem / sửa / xóa / link**

- **`test_create_profile_delegates`** — ADMIN/OWNER tạo profile trong family (mock đủ).
- **`test_create_profile_forbidden_member`** — MEMBER không tạo profile.
- **`test_create_profile_owner_not_found`** — `owner_user_id` không tồn tại trong user repo → `NotFoundError`.
- **`test_get_profile_ok`** — Đọc profile trong family thành công.
- **`test_get_profile_member_forbidden_not_self`** — MEMBER xem profile không link với mình → `ForbiddenError`.
- **`test_get_profile_repo_returns_none`** — `get_profile` `None` → `NotFoundError`.
- **`test_patch_profile_ok`** — OWNER sửa profile (đủ quyền admin gate).
- **`test_patch_profile_forbidden`** — MEMBER bị chặn ở `require_family_admin` → `ForbiddenError`.
- **`test_patch_profile_member_unlinked_profile_forbidden`** — MEMBER không đủ quyền admin để patch.
- **`test_patch_profile_admin_edits_self_linked_profile_ok`** — ADMIN sửa profile đã link với chính mình.
- **`test_patch_profile_not_in_family`** — Profile không thuộc family → `NotFoundError`.
- **`test_patch_profile_repo_none`** / **`test_patch_profile_admin_self_linked_repo_none`** — `patch_profile` trả `None` → `NotFoundError`.
- **`test_delete_profile_ok`** — ADMIN soft delete thành công.
- **`test_delete_profile_soft_delete_fails`** — `soft_delete_profile` false → `NotFoundError`.
- **`test_link_profile_ok`** — Link profile tới user hợp lệ.
- **`test_link_profile_forbidden`** — MEMBER không link.
- **`test_link_profile_user_not_found`** — `target_user_id` không tồn tại.
- **`test_link_profile_not_in_family`** — Profile không trong family.
- **`test_link_profile_integrity_conflict`** — `IntegrityError` khi link → `ConflictError`.
- **`test_link_profile_returns_none_conflict`** — Repo trả `None` → `ConflictError`.

**Health**

- **`test_get_health_raises_profile_not_in_family`** — Profile không trong family → `NotFoundError`.
- **`test_get_health_returns_none_from_repo`** — Member đọc health profile của mình, repo `get_health` `None`.
- **`test_get_health_member_forbidden_other_profile`** — MEMBER đọc health profile người khác → `ForbiddenError`.
- **`test_get_health_admin_reads_any_profile`** — ADMIN không cần `get_profile` để kiểm tra self-link.
- **`test_patch_health_ok`** — ADMIN patch health thành công.
- **`test_patch_health_member_forbidden`** — MEMBER không patch health.
- **`test_patch_health_profile_not_in_family`** — Profile không trong scope family → `NotFoundError`.

**Danh sách profile**

- **`test_list_profiles_delegates`** — Gọi `list_profiles_in_family` sau khi là member.
- **`test_list_profiles_member_sees_full_family_list`** — MEMBER nhận full list (không filter chỉ self).
- **`test_list_profiles_admin_sees_all`** — ADMIN thấy tất cả profile trả về repo.
- **`test_list_my_linked_profiles_delegates`** — Ủy quyền `list_linked_profiles_for_user` với `profile_scope`.

### `tests/unit/test_owner_access_rules.py` (unit — `AccessControlService` / `FamiliesService` với access mock)

- **`test_require_family_member_returns_forbidden_when_family_exists_but_user_not_member`** — Có family, không membership → `ForbiddenError`.
- **`test_require_family_member_returns_not_found_when_family_missing`** — Không family → `NotFoundError` “Family not found”.
- **`test_require_membership_delete_allows_self_when_owner_user_matches`** — `owner_user_id` trùng user → cho phép delete context.
- **`test_require_profile_read_allows_owner_even_without_linked_user`** — Chủ profile (owner) đọc được dù chưa link user.
- **`test_admin_cannot_create_profile_with_owner_role`** — ADMIN không tạo profile với `role=OWNER` trong request.
- **`test_owner_transfer_uses_transactional_transfer_method`** — Patch role → OWNER gọi `transfer_family_owner` đúng tham số.
- **`test_cannot_demote_current_owner_without_transfer`** — Hạ OWNER hiện tại xuống ADMIN mà không transfer → `ForbiddenError`.

### `tests/unit/test_rag_route.py` (unit)

- **`test_rag_chat_returns_sources`** — Endpoint RAG chat (mock) trả payload có `sources`.

### `tests/unit/test_rag_support.py` (unit)

- **`test_build_search_document_includes_core_fields`** — Chuỗi tìm kiếm RAG gồm các field lõi.
- **`test_format_entry_context_prioritizes_matching_fields`** — Format context ưu tiên field khớp tìm kiếm.

### `tests/integration/test_postgres_smoke.py` (integration — DB)

- **`test_health_reports_postgres_connected`** — `GET` health (hoặc tương đương) cho thấy Postgres kết nối được.

### `tests/integration/test_auth_users.py` (integration — DB)

- **`test_register_returns_201_with_user_shape`** — Đăng ký thành công, body user đúng dạng.
- **`test_register_duplicate_email_returns_400`** — Email trùng → 400.
- **`test_register_duplicate_phone_returns_400`** — SĐT trùng → 400.
- **`test_register_requires_phone_number`** — Thiếu phone → lỗi validation/400.
- **`test_login_returns_token`** — Login trả token.
- **`test_users_me_returns_current_user`** — `GET /users/me` với token trả user hiện tại.
- **`test_users_me_bundle_includes_health_profile_after_personal_profile`** — Bundle `me` gồm health khi đã có personal profile + health.
- **`test_users_me_without_token_returns_401`** — Không token → 401.

### `tests/integration/test_families_authz.py` (integration — DB)

- **`test_case_a_random_family_returns_404`** — SC-001(a): family ID không tồn tại → 404.
- **`test_case_b_member_cannot_rotate_invite`** — SC-001(b): MEMBER gọi rotate invite → 403.

### `tests/integration/test_families_more.py` (integration — DB)

- **`test_case_c_member_patch_health_forbidden`** — MEMBER patch health hộ người khác → forbidden.
- **`test_case_e_member_get_own_health_ok`** — MEMBER đọc health của profile mình → OK.
- **`test_case_d_profile_not_in_scope_returns_403`** — Profile ngoài phạm vi family/ngữ cảnh → 403.
- **`test_join_invalid_invite_code_returns_404`** — Join mã sai → 404.
- **`test_join_twice_same_family_returns_409`** — Join lần hai cùng family → 409.
- **`test_rotate_invite_invalidates_old_code`** — Sau rotate, mã cũ không còn dùng join (hoặc preview invalid theo logic app).

### `tests/integration/test_families_personal_preview.py` (integration — DB)

- **`test_sc004_personal_profile_then_join_reuses_linked_profile`** — Đã có personal profile + join: tái dùng profile đã link, không tạo trùng.
- **`test_invite_preview_valid_and_invalid`** — Preview mã hợp lệ vs không hợp lệ (404/`valid=false` tùy contract).

### `tests/integration/test_families_public_invite_tokens.py` (integration — DB)

- **`test_public_invite_single_use_second_user_gets_404`** — User thứ hai join cùng mã sau khi đã consume → 404 (single-use).
- **`test_invite_preview_valid_false_after_code_consumed`** — Sau consume, preview báo không hợp lệ.
- **`test_join_rejects_expired_public_invite`** — Token hết hạn (TTL, monkeypatch) → join bị từ chối.

### `tests/integration/test_families_invite_by_phone.py` (integration — DB)

- **`test_invite_by_phone_success_owner`** — OWNER mời SĐT thành công (có user / đủ điều kiện).
- **`test_invite_by_phone_forbidden_for_member`** — MEMBER → 403.
- **`test_invite_by_phone_dry_run_user_not_found_returns_found_false`** — Dry run, user không tồn tại → `found=false` (hoặc tương đương API).
- **`test_invite_by_phone_conflict_when_already_member`** — Đã member → 409.
- **`test_invite_by_phone_requires_full_name_without_personal_profile`** — User được mời chưa có personal profile → bắt buộc full_name.

### `tests/integration/test_families_invite_link_profile.py` (integration — DB)

- **`test_list_linkable_profiles_by_invite_returns_unlinked_profiles`** — Liệt kê profile có thể link theo invite (chưa link user).
- **`test_link_profile_by_invite_links_selected_profile_and_consumes_code`** — Link profile chọn + consume mã invite.
- **`test_linkable_profiles_returns_410_for_expired_invite`** — Invite hết hạn → 410 (Gone).

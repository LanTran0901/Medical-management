# Quickstart: test API Families / Profiles (002)

Giả định: API chạy tại `http://localhost:8080`, đã có user và **access token** từ `/auth/login` hoặc `/auth/register`.

## 1. Lấy token

```http
POST /auth/login
Content-Type: application/json

{ "email": "...", "password": "...", "device_id": "dev-1", "device_name": "cli", "platform": "test" }
```

Lưu `access_token` → header sau:

```http
Authorization: Bearer <access_token>
```

## 1b. Xác nhận user hiện tại (FR-013 / T037)

```http
GET /users/me
Authorization: Bearer <access_token>
```

Trả về cùng dạng `GET /users/{user_id}` khi gọi đúng user của token — tiện cho app không cần lưu UUID sẵn.

## 2. Luồng tối thiểu (sau khi implement router 002)

1. `POST /families` — tạo gia đình; response có `id`, `invite_code`.
2. `POST /families/join` — body `{ "invite_code": "...", "full_name": "..." }` (`full_name` bắt buộc nếu user chưa có profile cá nhân / `linked_user_id`).
3. `POST /families/{family_id}/profiles` — OWNER/ADMIN tạo profile ảo / thành viên.
4. `PATCH /families/{family_id}/profiles/{profile_id}/health` (hoặc tương đương) — cập nhật health_details.
5. `POST /families/{family_id}/invite/rotate` — làm mới mã; thử join bằng mã cũ → phải lỗi.

*(Đường dẫn chính xác lấy theo `contracts/README.md` sau khi code merge.)*

## 3. Kiểm tra 403/404

- Gọi `GET /families/{id}` với `id` random → **404**.
- User MEMBER gọi rotate invite → **403** (nếu chỉ OWNER được rotate).

## 4. Database

Không cần migrate mới nếu đã `alembic upgrade head` bản có `families` / `profiles`. Nếu thiếu bảng, chạy:

```powershell
cd d:\WDA\Medical-management
pipenv run alembic --config app/alembic.ini upgrade head
```

## 5. Pytest (SC-001 / T035–T036)

- **Unit (không cần DB)**: `pytest tests/test_family_permission.py -v`
- **Integration (chỉ cần PostgreSQL)** — MongoDB **không** bắt buộc: `tests/integration/conftest.py` bật `SKIP_MONGO_LIFESPAN=1` và mặc định **`HOMEDMEDAI_INTEGRATION=1`** (không cần export). Tắt nhanh khi không có DB: `set HOMEDMEDAI_INTEGRATION=0` rồi `pytest tests/integration/ -q`.
  - `pytest tests/integration/ -v`  
  - hoặc `pytest tests/integration/test_families_authz.py -v`

### 5b. Chạy test bằng Docker (Postgres trong Compose)

Không cần MongoDB; dùng `docker-compose.test.yml` + `docker/test.env`:

```bash
docker compose -f docker-compose.test.yml run --rm --build test
```

Chi tiết: `docker/README.md`.

### 5c. Coverage (độ phủ code)

Cần `pytest-cov` (`pip install pytest-cov`). Mặc định `pytest.ini` bật `--cov=app` + báo cáo HTML `htmlcov/`. Tắt: `pytest --no-cov`.

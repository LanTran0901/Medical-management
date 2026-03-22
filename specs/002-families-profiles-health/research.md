# Research: 002-families-profiles-health

## 1. Lưu trữ: PostgreSQL vs MongoDB

**Decision**: Chỉ **PostgreSQL** + SQLAlchemy ORM cho `families`, `family_memberships`, `profiles`, `health_details`.

**Rationale**: Dữ liệu quan hệ, FK, unique `(family_id, profile_id)`, `invite_code` unique — khớp constitution IV và migration hiện có.

**Alternatives considered**: Mongo cho profile linh hoạt — từ chối vì đã có schema Alembic và cần join/transaction.

---

## 2. Định nghĩa “profile cá nhân” để join (FR-008)

**Decision**: Profile **cá nhân** của user \(U\) là bản ghi `profiles` có `linked_user_id = U.id` (tối đa **một** bản ghi do unique constraint DB). Khi join: nếu tồn tại thì **tái sử dụng** `profile_id` đó để tạo `family_memberships` (nếu chưa có cặp family+profile); nếu **chưa** có thì **tạo** profile mới với `owner_user_id = U`, `linked_user_id = U`, `full_name` từ body join hoặc default hợp lệ (plan implementation: bắt buộc `display_name` trong POST join nếu cần).

**Rationale**: Khớp unique `linked_user_id` và clarify spec.

**Alternatives considered**: “Profile đầu tiên của owner_user_id” — mơ hồ khi có nhiều profile do quản trị viên tạo; không dùng.

---

## 3. Cấu trúc URL API

**Decision**: Base **`/families`**; các thao tác profile/health trong family dùng prefix  
`/families/{family_id}/profiles/...`  
Hoặc song song **`/profiles/{profile_id}`** với kiểm tra membership — **MVP đề xuất**: ưu tiên nested dưới `family_id` để kiểm tra phạm vi một lần.

**Rationale**: Dễ enforce “user thuộc family” trước khi đọc profile.

**Alternatives considered**: Chỉ flat `/profiles` — hợp lệ nhưng filter phức tạp hơn; có thể phase 2.

---

## 4. Sinh và rotate `invite_code`

**Decision**: Chuỗi ngẫu nhiên đủ dài (ví dụ 8–12 ký tự base32/url-safe), **unique** toàn bảng `families`. Rotate = `UPDATE` cột `invite_code` = giá trị mới; join chỉ so khớp giá trị hiện tại (FR-012).

**Rationale**: Đơn giản, không cần bảng lịch sử mã trong MVP.

---

## 5. Soft-delete profile + membership (FR-011)

**Decision**: Trong **một transaction**: set `profiles.deleted_at` (hoặc flag tương đương nếu migration dùng cột này); **DELETE** hàng `family_memberships` liên quan `profile_id` (hoặc soft membership nếu sau này có cột — hiện schema cứng delete CASCADE-friendly).

**Rationale**: Spec yêu cầu không membership “treo”.

**Alternatives considered**: Chỉ soft membership — cần thêm cột; chỉ dùng nếu migration bổ sung.

---

## 6. Khóa bản ghi (đồng thời)

**Decision**: **MVP**: optimistic — so sánh `updated_at` client gửi với DB; nếu lệch → **409 Conflict**. Có thể bổ sung cột `version` integer sau.

**Rationale**: Constitution đã chốt khóa chỉnh sửa; không cần hàng đợi distributed lock trong MVP.

---

## 7. Join trùng gia đình

**Decision**: Nếu user đã có `family_memberships` cho `profile_id` đang dùng và cùng `family_id` → **409 Conflict** (hoặc idempotent **200** nếu product muốn — MVP chọn **409** để rõ ràng).

**Rationale**: FR-007 “trừ khi user đã thuộc gia đình”.

---

## 8. Liên kết profile ảo → user (FR-009)

**Decision**: Endpoint dành cho OWNER/ADMIN: ví dụ `PATCH /families/{family_id}/profiles/{profile_id}/link` body `{ "user_id": "uuid" }` — set `linked_user_id` nếu null, kiểm tra unique globally, và user đích chưa có profile linked khác.

**Rationale**: Tách rõ khỏi join-by-code.

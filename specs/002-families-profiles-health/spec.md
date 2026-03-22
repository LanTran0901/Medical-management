# Feature Specification: API Gia đình, Hồ sơ & Chi tiết sức khỏe

**Feature Branch**: `002-families-profiles-health` *(tạo branch khi bắt đầu implement)*  
**Created**: 2026-03-21  
**Status**: Draft  
**Input**: Cụm REST cho `families`, `family_memberships`, `profiles`, `health_details` — sau khi user đã đăng nhập.

**Phụ thuộc**: Auth + schema DB đã có (xem `specs/README.md`). Spec này **không** mô tả đăng ký/đăng nhập.

## Clarifications

### Session 2026-03-21

- Q: User đã đăng nhập tham gia gia đình bằng `invite_code` như thế nào trong MVP? → A: Có API **POST join** với `invite_code` để tạo `family_memberships` cho người dùng hiện tại.
- Q: Join gắn `profile_id` thế nào? → A: Nếu user đã có profile “cá nhân” (định nghĩa trong plan, ví dụ `linked_user_id` = user) thì **tái sử dụng**; nếu chưa có thì **tạo profile mới** rồi gắn membership.
- Q: Profile ảo trong gia đình (`linked_user_id` null) khi có member mới? → A: **OWNER hoặc ADMIN** có thể **chỉ định** profile ảo đó cho user (cập nhật `linked_user_id`) và/hoặc điều chỉnh membership — chi tiết API trong plan, tuân unique `linked_user_id` toàn hệ thống.
- Q: Truy cập sai quyền / ID không thuộc phạm vi — dùng 403 hay 404? → A: **404** khi tài nguyên không tồn tại hoặc user **không thuộc phạm vi** (coi như không thấy); **403** khi tài nguyên **tồn tại và thuộc phạm vi** nhưng **vai trò không đủ** để thao tác.
- Q: Soft-delete `profiles` khi vẫn còn `family_memberships`? → A: **Cho phép** soft-delete; trong **cùng giao dịch** hệ thống MUST **gỡ hoặc đình chỉ** mọi membership (và quy tắc liên quan) gắn profile đó — chi tiết trong plan.
- Q: Khi OWNER làm mới `invite_code`, mã cũ còn hiệu lực không? → A: **Không** — chỉ **mã hiện tại** lưu trên `families` là hợp lệ; mã cũ **vô hiệu ngay** sau khi đổi.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tạo gia đình và mã mời (Priority: P1)

Là user đã đăng nhập, tôi có thể tạo nhóm gia đình và nhận mã/đường dẫn mời để thêm người khác.

**Why this priority**: Không có `family` thì không gắn được membership và dữ liệu chung.

**Independent Test**: Tạo gia đình → trả về `family_id` + `invite_code` (hoặc tương đương); chỉ user có quyền mới tạo được.

**Acceptance Scenarios**:

1. **Given** user đã xác thực, **When** tạo gia đình với tên hợp lệ, **Then** hệ thống tạo bản ghi `families` và gán người tạo là OWNER (qua membership hoặc quy ước rõ trong API).
2. **Given** gia đình đã tồn tại, **When** OWNER yêu cầu làm mới/lấy mã mời, **Then** mã mới unique và **mã cũ không còn dùng join được** (chỉ mã hiện tại hợp lệ).
3. **Given** user đã đăng nhập có `invite_code` hợp lệ, **When** gọi API join, **Then** user được thêm vào gia đình tương ứng (theo quy tắc gắn `profile_id` đã chốt).

---

### User Story 2 - Thêm hồ sơ & gắn vào gia đình (Priority: P1)

Là OWNER/ADMIN, tôi có thể tạo `profile` cho thành viên và gán vào gia đình với vai trò (OWNER/ADMIN/MEMBER).

**Independent Test**: Tạo 2 profile, gán vào cùng một `family_id` với role khác nhau; MEMBER chỉ thấy/ghi được theo quy ước phân quyền đã chốt ở tổng quan.

**Acceptance Scenarios**:

1. **Given** user là OWNER/ADMIN của gia đình, **When** tạo profile với `owner_user_id`/`full_name` bắt buộc, **Then** tạo `profiles` + (tuỳ chọn) `health_details` rỗng.
2. **Given** profile đã có, **When** thêm `family_memberships` (family_id, profile_id, role), **Then** không trùng cặp (family_id, profile_id).
3. **Given** profile đại diện người chưa có tài khoản, **When** để `linked_user_id` null, **Then** vẫn quản lý được trong gia đình.
4. **Given** có profile ảo trong gia đình (`linked_user_id` null), **When** OWNER/ADMIN chỉ định profile đó cho user đã có tài khoản, **Then** `linked_user_id` được cập nhật hợp lệ và user có thể thấy đúng hồ sơ (không trùng với profile đã link user khác).

---

### User Story 3 - Cập nhật health_details (Priority: P2)

Là OWNER/ADMIN, tôi có thể cập nhật nhóm máu, bệnh nền, dị ứng, liên hệ khẩn cấp cho một profile.

**Acceptance Scenarios**:

1. **Given** profile thuộc gia đình của tôi, **When** PATCH health_details, **Then** dữ liệu 1-1 với profile được lưu đúng.
2. **Given** MEMBER không có quyền sửa, **When** gọi PATCH, **Then** 403.

---

### Edge Cases

- Truy cập `family_id`/`profile_id`: **404** nếu không tồn tại hoặc không thuộc phạm vi user; **403** nếu thuộc phạm vi nhưng role không đủ (theo Clarifications).
- Khóa bản ghi khi chỉnh sửa đồng thời (theo quyết định tổng quan).
- Soft-delete profile: **được phép** khi còn membership — membership được **xử lý tự động** trong cùng transaction (theo Clarifications).
- Join bằng `invite_code` đã bị **thay thế** sau khi OWNER làm mới mã → **404** hoặc lỗi “mã không hợp lệ” (theo Clarifications).

## Assumptions

- Phân quyền OWNER/ADMIN/MEMBER như đã ghi trong `specs/001-homemedai-mvp/spec.md`.
- UUID và kiểu enum trong DB (`gender_type`, `blood_type_enum`, `family_role`) đã khớp migration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: API MUST cho phép tạo/đọc/cập nhật `families` trong phạm vi user có quyền.
- **FR-002**: API MUST quản lý `family_memberships` (thêm/sửa role/đình chỉ) theo OWNER/ADMIN.
- **FR-003**: API MUST CRUD `profiles` với `owner_user_id` và trường bắt buộc theo schema.
- **FR-004**: API MUST cho phép gán `linked_user_id` khi người đó đã có tài khoản (unique).
- **FR-005**: API MUST upsert `health_details` theo `profile_id` (1-1).
- **FR-006**: API MUST từ chối thao tác khi không đủ quyền vai trò trong gia đình.
- **FR-007**: API MUST cho phép user đã xác thực **gia nhập gia đình bằng `invite_code`** (POST join) và tạo bản ghi membership hợp lệ, trừ khi mã sai hoặc user đã thuộc gia đình (quy tắc chi tiết trong plan).
- **FR-008**: Khi join, hệ thống MUST **tái sử dụng** profile cá nhân của user nếu đã tồn tại theo quy ước trong plan; nếu chưa thì MUST **tạo profile mới** rồi tạo membership.
- **FR-009**: OWNER hoặc ADMIN MUST có thể **liên kết** một profile ảo trong gia đình (`linked_user_id` null) với user tương ứng (và xử lý xung đột membership/profile theo plan).
- **FR-010**: API MUST trả **404** khi ID không tồn tại hoặc không nằm trong phạm vi gia đình mà user được phép biết; MUST trả **403** khi tài nguyên thuộc phạm vi nhưng **không đủ quyền** thao tác.
- **FR-011**: Khi soft-delete một `profile`, hệ thống MUST trong **cùng transaction** cập nhật hoặc xóa các `family_memberships` (hoặc trạng thái tương đương) gắn profile đó để không còn membership “treo”.
- **FR-012**: Khi OWNER (hoặc quyền tương đương) **làm mới** `invite_code` của gia đình, hệ thống MUST **vô hiệu hóa ngay** mã trước đó; join MUST chỉ chấp nhận **giá trị `invite_code` hiện tại** trên bản ghi `families`.
- **FR-013**: API MUST cung cấp **`GET /users/me`** (alias “current user”) trả về thông tin user đang xác thực — tương đương `GET /users/{user_id}` với `user_id` = JWT `sub`, **không** cần biết UUID trước. *(Hợp đồng: `contracts/README.md` — mục Users.)*

### Key Entities

- **Family**, **FamilyMembership**, **Profile**, **HealthDetail** — như định nghĩa trong migration / schema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: **Bộ test tích hợp tự động** (`pytest`, thư mục `tests/`) MUST bao phủ các **case phân quyền cốt lõi** sau và mọi assertion trong file đó pass: (a) truy cập `family_id` **không** thuộc membership của user → **404**; (b) user là MEMBER gọi thao tác **chỉ OWNER** (ví dụ `POST /families/{family_id}/invite/rotate`) → **403**; (c) sau khi có route health: MEMBER gọi **PATCH** health khi spec cấm → **403**; (d) user **trong** family nhưng truy cập `profile_id` không thuộc family đó → **404**. Mở rộng thêm case tương tự SHOULD theo `contracts/README.md`. *“100%”* hiểu là **100% các case đã liệt kê trong suite SC-001**, không phải mọi endpoint tương lai.
- **SC-002**: Luồng tạo gia đình + 1 profile + health_details hoàn tất trong dưới 10 thao tác API (không kể auth).
- **SC-003**: Không tồn tại hai membership trùng (family_id, profile_id) sau mọi thao tác hợp lệ.

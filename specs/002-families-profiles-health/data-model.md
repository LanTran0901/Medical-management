# Data Model: 002-families-profiles-health

Nguồn sự thật: migration Alembic (`families`, `family_memberships`, `profiles`, `health_details`). Dưới đây là mapping logic + rule nghiệp vụ.

## Entity: Family

| Field | Kiểu | Ghi chú |
|-------|------|---------|
| id | UUID | PK |
| family_name | string | Bắt buộc khi tạo |
| invite_code | string | Unique; rotate thay thế hoàn toàn giá trị cũ |
| created_at | timestamptz | Server |

**Quan hệ**: 1 family — N memberships.

---

## Entity: FamilyMembership

| Field | Kiểu | Ghi chú |
|-------|------|---------|
| id | UUID | PK |
| family_id | UUID | FK → families |
| profile_id | UUID | FK → profiles |
| role | enum | OWNER, ADMIN, MEMBER |
| added_by | UUID | FK → users |
| created_at | timestamptz | |

**Ràng buộc**: Unique **(family_id, profile_id)**.

**Quy tắc role (MVP)**:

- Mỗi family có **ít nhất một** OWNER (người tạo family nhận OWNER khi tạo membership đầu tiên).
- Chỉ OWNER có thể **rotate** `invite_code` (có thể mở cho ADMIN — tùy implement, mặc định OWNER only nếu spec không yêu cầu ADMIN).

---

## Entity: Profile

| Field | Kiểu | Ghi chú |
|-------|------|---------|
| id | UUID | PK |
| owner_user_id | UUID | User quản lý hồ sơ |
| linked_user_id | UUID? | Unique nullable — tài khoản gắn thật |
| full_name | string | Required |
| dob, gender, height_cm, weight_kg, address, avatar_url, status | optional | |
| deleted_at | timestamptz? | Soft delete |

**“Profile cá nhân”**: `linked_user_id = <current_user.id>`.

---

## Entity: HealthDetail

| Field | Kiểu | Ghi chú |
|-------|------|---------|
| id | UUID | PK |
| profile_id | UUID | Unique FK — 1-1 profile |
| blood_type | enum? | |
| chronic_diseases, allergies | text[] | |
| emergency_contact, notes | text | |
| updated_at | timestamptz | |

---

## Validation (API)

- Tạo family: `family_name` không rỗng.
- Tạo profile trong family: `owner_user_id` thường là OWNER/ADMIN đang thao tác hoặc chỉ định hợp lệ; `full_name` bắt buộc.
- Join: `invite_code` khớp bản ghi family; xử lý profile reuse/create như [research.md](./research.md).
- Link profile ảo: `linked_user_id` phải null trước khi gán; user đích chưa có profile khác với `linked_user_id` trùng.

## State transitions

- **Profile soft-delete**: transaction xóa/đình chỉ memberships liên quan (xem research).
- **Invite rotate**: chỉ giá trị mới hợp lệ.

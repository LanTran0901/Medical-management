# API Contracts: 002-families-profiles-health

Tất cả endpoint (trừ ghi chú) yêu cầu header:

`Authorization: Bearer <access_token>`

## Users — session (tiện cho app; FR-013)

| Method | Path | Mô tả | Role |
|--------|------|--------|------|
| GET | `/users/me` | Trả về user đang đăng nhập (cùng schema `UserResponse` như `GET /users/{user_id}` khi self) | authenticated |

**Lưu ý implement (FastAPI)**: Khai báo route **`/me` trước** route `/{user_id}` để `me` không bị parse thành UUID.

> Không dùng **`GET /me`** tại root trừ khi project thống nhất prefix riêng; chuẩn trong repo này là **`GET /users/me`**.

## Lỗi chuẩn (theo spec)

| HTTP | Khi nào |
|------|---------|
| 404 | Resource không tồn tại hoặc **không thuộc phạm vi** gia đình user được phép biết |
| 403 | Thuộc phạm vi nhưng **role không đủ** |
| 409 | Vi phạm unique (membership trùng, `linked_user_id` trùng, join trùng family, optimistic conflict) |
| 422 | Validation body |
| 401 | Thiếu/sai token |

## Quy ước path (canonical — tránh lệch implement)

- Segment cho bản ghi gia đình–hồ sơ là **`/members`**, **không** dùng `/memberships`.
- Tham số đường dẫn là **`{membership_id}`** = UUID khóa chính bảng `family_memberships` (`id`), **không** đặt `{user_id}` trong path (tránh nhầm với `users.id`). Thao tác “rời nhóm” vẫn là `DELETE .../members/{membership_id}` (đủ quyền hoặc self).

## Endpoints đề xuất (MVP)

| Method | Path | Mô tả | Role |
|--------|------|--------|------|
| POST | `/families` | Tạo family + membership OWNER cho profile cá nhân hoặc profile tạo kèm | authenticated |
| GET | `/families` | Danh sách gia đình user là thành viên | authenticated |
| GET | `/families/{family_id}` | Chi tiết (nếu thuộc family) | member+ |
| PATCH | `/families/{family_id}` | Đổi tên (OWNER/ADMIN) | OWNER/ADMIN |
| POST | `/families/join` | Body `{ "invite_code", "full_name"? }` — join + membership | authenticated |
| POST | `/families/{family_id}/invite/rotate` | Mã mới, vô hiệu mã cũ | OWNER |
| GET | `/families/{family_id}/members` | List memberships + role | member+ |
| PATCH | `/families/{family_id}/members/{membership_id}` | Đổi role | OWNER (hoặc ADMIN theo policy) |
| DELETE | `/families/{family_id}/members/{membership_id}` | Rời / xóa membership | OWNER/ADMIN / self |
| POST | `/families/{family_id}/profiles` | Tạo profile + optional gắn membership | OWNER/ADMIN |
| GET | `/families/{family_id}/profiles` | List profiles trong family | theo policy MEMBER |
| GET | `/families/{family_id}/profiles/{profile_id}` | Chi tiết | theo policy |
| PATCH | `/families/{family_id}/profiles/{profile_id}` | Cập nhật profile | OWNER/ADMIN (+ MEMBER nếu chỉ sửa self-linked — defer) |
| DELETE | `/families/{family_id}/profiles/{profile_id}` | Soft-delete + xóa memberships | OWNER/ADMIN |
| PATCH | `/families/{family_id}/profiles/{profile_id}/link` | Body `{ "user_id" }` — gán profile ảo | OWNER/ADMIN |
| GET | `/families/{family_id}/profiles/{profile_id}/health` | Lấy health_details | theo policy |
| PUT/PATCH | `/families/{family_id}/profiles/{profile_id}/health` | Upsert health_details | OWNER/ADMIN |

> **Lưu ý**: Đường dẫn có thể tinh gọn (ví dụ bỏ `family_id` nếu dùng scope middleware); bảng trên là hợp đồng logic để implement và test.

## OpenAPI

Sau khi implement, schema nguồn sự thật là **`/docs`** (FastAPI tự sinh). Có thể export OpenAPI JSON đặt tại `contracts/openapi-snippet.json` trong PR sau.

# HomeMedAI — Tổng quan sản phẩm (không gom chi tiết API)

**Feature Branch**: `001-homemedai-mvp`  
**Created**: 2026-03-21  
**Status**: Active (tài liệu tham chiếu)  
**Input**: Định hướng MVP HomeMedAI — quản lý gia đình, hồ sơ profile-centric, tủ thuốc, lịch nhắc, tuân thủ.

## Mục đích tài liệu này

File này giữ **tầm nhìn**, **giả định chung** và **quyết định đã chốt** (clarifications) để đồng bộ giữa các spec nhỏ.  
**Chi tiết từng cụm API** nằm trong:

- [`../README.md`](../README.md) — bảng lộ trình feature
- `002-` … `005-` — spec theo từng bước triển khai backend

## Phạm vi đã có trong codebase (không lặp lại trong spec con)

- **Xác thực & phiên**: email/mật khẩu, Google, refresh token, thiết bị + FCM token.
- **Cơ sở dữ liệu**: PostgreSQL + Alembic (schema đã migration theo từng bảng).

Các spec `002+` chỉ mô tả **hành vi API và nghiệp vụ** phía trên lớp này.

## Clarifications (áp dụng toàn sản phẩm)

### Session 2026-03-21

- Phân quyền gia đình: **OWNER** toàn quyền; **ADMIN** quản lý hồ sơ/thuốc/lịch; **MEMBER** chỉ xem và xác nhận lịch trên hồ sơ được gán.
- Nhắc lịch khi mất mạng: chỉ phát khi kết nối ổn định; nếu lỡ nhắc thì **phát bù** khi mạng trở lại.
- **Khóa bản ghi** khi nhiều người sửa cùng một hồ sơ/thuốc/lịch (ai mở trước thì người khác chờ).
- Đăng nhập MVP: **email/mật khẩu + Google** (đã có trong codebase).
- Kênh nhắc MVP: **Push Notification (Firebase)**; không SMS/Email trong MVP.

## Nguyên tắc chung cho mọi spec con

- **Profile-centric**: mọi dữ liệu y tế gắn `profile_id` / phạm vi gia đình đúng quyền.
- **Không** chatbot / từ điển y tế trong các spec backend hiện tại (có thể để phase sau).
- Mỗi spec feature phải có **success criteria đo lường được** chỉ cho phạm vi cụm đó.

## Liên kết nhanh

| Spec | Mục đích |
|------|----------|
| [002-families-profiles-health](../002-families-profiles-health/spec.md) | Gia đình, membership, profile, health_details |
| [003-medicine-inventory-api](../003-medicine-inventory-api/spec.md) | Tủ thuốc |
| [004-clinical-activity-api](../004-clinical-activity-api/spec.md) | Bệnh án, vaccine, tăng trưởng, activity log |
| [005-schedules-reminders-api](../005-schedules-reminders-api/spec.md) | Lịch nhắc, log tuân thủ, **thông báo push** (Firebase) — **làm sau cùng** |

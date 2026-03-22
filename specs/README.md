# Spec Kit — HomeMedAI Backend

Cách dùng: **mỗi cụm API = một thư mục `specs/NNN-short-name/`** với `spec.md` + `checklists/`.  
Không gom toàn bộ MVP vào một spec duy nhất; làm **từng bước**, `/speckit.plan` và `/speckit.tasks` theo **đúng feature đang mở**.

## Đã có sẵn (không cần spec triển khai lại)

| Hạng mục | Ghi chú |
|----------|---------|
| **Auth** | Đăng ký/đăng nhập, refresh token, thiết bị (FCM token đăng ký), JWT — đã implement trong codebase |
| **PostgreSQL + Alembic** | Migration baseline + schema mở rộng (users, devices, tokens, profiles, families, …) — đã có |

Các spec dưới đây **giả định** request đã có `Authorization` (user đã đăng nhập) trừ khi ghi rõ public.

## Lộ trình feature (theo thứ tự gợi ý)

**Lưu ý:** Cụm **lịch nhắc & thông báo push (Firebase)** để **cuối cùng** — sau khi đã có dữ liệu gia đình, thuốc và bệnh án để gắn lịch.

| # | Thư mục | Nội dung API / cụm | Trạng thái |
|---|---------|-------------------|------------|
| 001 | [`001-homemedai-mvp`](001-homemedai-mvp/spec.md) | **Tổng quan sản phẩm** + nguyên tắc chung (không chi tiết từng endpoint) | Tài liệu |
| 002 | [`002-families-profiles-health`](002-families-profiles-health/spec.md) | Gia đình, thành viên (`family_memberships`), hồ sơ (`profiles`), chi tiết sức khỏe (`health_details`) | Chưa code API |
| 003 | [`003-medicine-inventory-api`](003-medicine-inventory-api/spec.md) | Tủ thuốc (`medicine_inventory`) | Chưa code API |
| 004 | [`004-clinical-activity-api`](004-clinical-activity-api/spec.md) | Bệnh án (`medical_records`), tiêm chủng (`vaccine_history`), tăng trưởng (`growth_records`), audit (`activity_logs`) | Chưa code API |
| 005 | [`005-schedules-reminders-api`](005-schedules-reminders-api/spec.md) | **Lịch nhắc** (`schedules`), nhật ký thực hiện (`schedule_logs`), **push Firebase** — **bước cuối** | Chưa code API |

## Quy ước workflow

1. Checkout hoặc tạo branch theo feature: ví dụ `002-families-profiles-health` (script `create-new-feature.ps1` tự tăng số).
2. Chỉnh `specs/NNN-.../spec.md` → `/speckit.clarify` nếu cần → `/speckit.plan` → `/speckit.tasks`.
3. **Không** copy nguyên spec cũ sang spec mới; mỗi file chỉ chứa FR/SC/entity **thuộc cụm đó**, và tham chiếu chéo tới 001 hoặc README nếu cần ngữ cảnh.

## Tham chiếu kiến trúc code

- Clean Architecture: `CLEAN_ARCHITECTURE.md`
- Constitution: `.specify/memory/constitution.md`

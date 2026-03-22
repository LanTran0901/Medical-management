# Feature Specification: API Lịch nhắc & Nhật ký tuân thủ

**Feature Branch**: `005-schedules-reminders-api`  
**Created**: 2026-03-21  
**Status**: Draft  
**Input**: CRUD `schedules`, ghi `schedule_logs`, tích hợp gửi nhắc qua **Firebase Push** (theo đã chốt MVP).

**Phụ thuộc**: `profiles` và (tuỳ loại lịch) `medicine_inventory` đã có. Auth + đăng ký FCM token qua thiết bị đã có.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tạo & quản lý lịch (Priority: P1)

Là OWNER/ADMIN, tôi có thể tạo lịch theo `profile_id`, loại (MEDICINE/VACCINE/CHECKUP/RE_CHECKUP), giờ nhắc, RRULE, liên kết `medicine_id` khi là thuốc.

**Acceptance Scenarios**:

1. **Given** quyền hợp lệ, **When** POST schedule với `category` + `remind_time` (và `medicine_id` nếu MEDICINE), **Then** lưu `schedules` với `status` mặc định ACTIVE.
2. **Given** lịch MEDICINE, **When** không có `medicine_id`, **Then** 422 (hoặc quy tắc rõ trong plan).

---

### User Story 2 - Nhắc & xác nhận tuân thủ (Priority: P1)

Là user có quyền, tôi nhận push đúng giờ (khi mạng ổn định) và **xác nhận** TAKEN/SKIPPED/SNOOZED; hệ thống ghi `schedule_logs`.

**Acceptance Scenarios**:

1. **Given** schedule ACTIVE, **When** đến giờ nhắc và thiết bị online, **Then** nhận push (FCM).
2. **Given** mất mạng tại giờ nhắc, **When** mạng trở lại, **Then** nhắc bù trong khoảng thời gian đã chốt ở tổng quan.
3. **Given** user xác nhận, **When** POST log, **Then** tạo `schedule_logs` với `action_by`, `action_time`, `status`.

---

### Edge Cases

- Trùng giờ nhắc nhiều schedule trên cùng profile → không crash; thứ tự hiển thị có thể ghi trong plan.
- MEMBER chỉ xác nhận lịch trên profile được gán (theo tổng quan).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: API MUST CRUD `schedules` trong phạm vi quyền profile/gia đình.
- **FR-002**: API MUST tạo `schedule_logs` khi xác nhận thực hiện.
- **FR-003**: Hệ thống MUST kích hoạt gửi FCM theo lịch (job/worker hoặc cơ chế đã chọn trong plan).
- **FR-004**: Tuân thủ quy tắc nhắc bù khi mạng không ổn định (mô tả hành vi user-facing, không bắt buộc chi tiết kỹ thuật ở spec).

## Success Criteria *(mandatory)*

- **SC-001**: ≥95% nhắc (trong môi trường mạng ổn định) đến đúng ±1 phút so với cài đặt.
- **SC-002**: ≥95% lượt nhắc bù sau mất mạng được gửi trong khoảng thời gian đã chốt sau khi online lại.

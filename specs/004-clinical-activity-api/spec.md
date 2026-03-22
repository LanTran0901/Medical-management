# Feature Specification: API Bệnh án, Tiêm chủng, Tăng trưởng & Nhật ký hoạt động

**Feature Branch**: `004-clinical-activity-api`  
**Created**: 2026-03-21  
**Status**: Draft  
**Input**: CRUD/read cho `medical_records`, `vaccine_history`, `growth_records`; ghi `activity_logs` cho thao tác quan trọng trong gia đình.

**Phụ thuộc**: `profiles`, `families` đã có; user đã xác thực.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bệnh án & đính kèm (Priority: P1)

Là OWNER/ADMIN, tôi có thể thêm bản ghi khám cho một profile với chẩn đoán, bác sĩ, ngày khám, và URL đính kèm (JSON).

**Acceptance Scenarios**:

1. **Given** quyền sửa profile trong gia đình, **When** POST medical_record, **Then** lưu `created_by` = user hiện tại.
2. **Given** MEMBER không có quyền ghi, **Then** 403.

---

### User Story 2 - Lịch sử tiêm chủng (Priority: P2)

Là OWNER/ADMIN, tôi có thể thêm/cập nhật mũi tiêm, ngày tiêm, mũi tiếp theo.

---

### User Story 3 - Tăng trưởng (Priority: P2)

Là OWNER/ADMIN, tôi có thể ghi nhận chiều cao/cân nặng theo ngày cho profile (trẻ).

---

### User Story 4 - Activity log (Priority: P2)

Hệ thống MUST ghi `activity_logs` (family_id, user_id, action_desc) cho các thao tác quan trọng (tạo/sửa/xóa bản ghi y tế, v.v.) — chi tiết sự kiện trong plan.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: API MUST CRUD `medical_records` theo `profile_id` với kiểm tra quyền.
- **FR-002**: API MUST CRUD `vaccine_history` theo `profile_id`.
- **FR-003**: API MUST CRUD `growth_records` theo `profile_id`.
- **FR-004**: API MUST ghi `activity_logs` cho thao tác được liệt kê trong plan (tối thiểu: thay đổi dữ liệu y tế).

## Success Criteria *(mandatory)*

- **SC-001**: Mọi thao tác ghi dữ liệu y tế đều có thể truy vết qua `activity_logs` hoặc timestamp + `created_by` (nếu không dùng log cho mọi đọc).
- **SC-002**: 100% request trái phạm vi gia đình/profile bị từ chối trong test tự động.

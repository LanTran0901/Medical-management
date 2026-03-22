# Feature Specification: API Tủ thuốc gia đình (Medicine Inventory)

**Feature Branch**: `003-medicine-inventory-api`  
**Created**: 2026-03-21  
**Status**: Draft  
**Input**: CRUD và cảnh báo tồn kho/hạn dùng cho bảng `medicine_inventory` theo `family_id`.

**Phụ thuộc**: User đã đăng nhập; user là thành viên có quyền (OWNER/ADMIN) theo gia đình chứa tủ thuốc.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Quản lý thuốc trong tủ (Priority: P1)

Là OWNER/ADMIN, tôi có thể thêm, sửa, xoá thuốc trong tủ của gia đình, gồm tên, loại, hạn, số lượng, đơn vị, ngưỡng cảnh báo.

**Independent Test**: CRUD đầy đủ trên một `family_id`; MEMBER không sửa được nếu spec không cho phép.

**Acceptance Scenarios**:

1. **Given** quyền ADMIN trên gia đình, **When** POST thuốc với đủ trường bắt buộc, **Then** tạo bản ghi `medicine_inventory`.
2. **Given** thuốc có `expiry_date` trong N ngày tới, **When** GET danh sách hoặc GET cảnh báo, **Then** trả về cờ/section “sắp hết hạn” (N do product chốt trong plan).
3. **Given** `quantity_stock` < `min_stock_alert`, **Then** hiển thị hoặc filter “cần bổ sung”.

---

### Edge Cases

- Truy cập `family_id` không thuộc user → 403/404.
- Thuốc trùng tên trong cùng gia đình → cho phép hay cảnh báo (cần chốt trong clarify/plan).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: API MUST CRUD `medicine_inventory` theo `family_id` với kiểm tra quyền.
- **FR-002**: API MUST hỗ trợ liệt kê thuốc theo gia đình (filter/pagination).
- **FR-003**: API MUST trả về hoặc tính được trạng thái cảnh báo hết hạn và tồn kho thấp (theo ngưỡng lưu trong DB).

## Success Criteria *(mandatory)*

- **SC-001**: 100% thao tác CRUD trái phạm vi gia đình bị từ chối trong test.
- **SC-002**: Người dùng có thể xác định thuốc sắp hết hạn trong một lần đọc danh sách (hoặc endpoint cảnh báo) mà không cần tính tay.

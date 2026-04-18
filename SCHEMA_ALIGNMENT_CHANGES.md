# Schema alignment changes

Ghi chú này tổng hợp các file đã chỉnh để đồng bộ backend với đánh giá trong `All table .md`.

## Migration

### `app/alembic/versions/20260412_2100_align_health_ui_schema.py`

- Tạo migration mới, `down_revision = "20260409_1400"`.
- Thêm cột cho `health_details`: `drug_allergies`, `food_allergies`.
- Thêm cột cho `medical_records`: `title`, `symptoms`, `test_results`, `doctor_advice`, `updated_at`.
- Thêm `created_at` cho `medical_record_attachments`.
- Thêm cột cho `follow_up_appointments`: `facility_name`, `department`, `doctor_name`, `notes`, `reminder_enabled`, `created_at`.
- Thêm cột cho `medicine_inventory`: `profile_id`, `dosage_value`, `dosage_unit`, `dosage_per_use_value`, `dosage_per_use_unit`, `use_tags`, `storage_location`, `low_stock_alert_enabled`, `created_at`, `updated_at`.
- Thêm khóa ngoại và index cho `medicine_inventory.profile_id -> profiles.id`.
- Thêm cột cho `vaccination_recommendations`: `disease_name`, `notes`.
- Thêm cột cho `vaccination_doses`: `reaction`, `reminder_enabled`, `remind_before_days`.
- Tạo bảng mới `medicine_reminders`.
- Tạo bảng mới `health_metric_readings`.
- Có `downgrade()` để xóa các index, bảng và cột đã thêm.

### `app/alembic/versions/20260409_1400_reconcile_managed_schema.py`

- File này đang là migration trước đó và hiện còn untracked.
- Migration mới `20260412_2100` phụ thuộc vào revision này, nên cần giữ file này trong repo nếu commit migration mới.

## Database models

### `app/infrastructure/config/database/postgres/models/profile_models.py`

- Thêm `HealthMetricReadingModel` cho bảng `health_metric_readings`.
- Thêm `drug_allergies`, `food_allergies` vào `HealthDetailModel`.

### `app/infrastructure/config/database/postgres/models/medical_record_models.py`

- Thêm `title`, `symptoms`, `test_results`, `doctor_advice`, `updated_at` vào `MedicalRecordModel`.
- Thêm `created_at` vào `MedicalRecordAttachmentModel`.
- Thêm `facility_name`, `department`, `doctor_name`, `notes`, `reminder_enabled`, `created_at` vào `FollowUpAppointmentModel`.

### `app/infrastructure/config/database/postgres/models/medicine_inventory_model.py`

- Thêm `profile_id`, các trường `dosage_*`, `use_tags`, `storage_location`, `low_stock_alert_enabled`, `created_at`, `updated_at` vào `MedicineInventoryModel`.
- Thêm `MedicineReminderModel` cho bảng `medicine_reminders`.

### `app/infrastructure/config/database/postgres/models/vaccination_models.py`

- Thêm `disease_name`, `notes` vào `VaccinationRecommendationModel`.
- Thêm `reaction`, `reminder_enabled`, `remind_before_days` vào `VaccinationDoseModel`.

### `app/infrastructure/config/database/postgres/models/__init__.py`

- Đăng ký thêm `HealthMetricReadingModel`.
- Đăng ký thêm `MedicineReminderModel`.

## Domain entities

### `app/domain/entities/health_detail.py`

- Thêm `drug_allergies`, `food_allergies` vào entity `HealthDetail`.

### `app/domain/entities/medical_record.py`

- Thêm `title`, `symptoms`, `test_results`, `doctor_advice`, `updated_at` vào entity `MedicalRecord`.

### `app/domain/entities/medicine_inventory.py`

- Thêm `profile_id`, các trường `dosage_*`, `use_tags`, `storage_location`, `low_stock_alert_enabled`, `created_at`, `updated_at` vào entity `MedicineInventory`.

### `app/domain/entities/vaccination.py`

- Thêm `disease_name`, `notes` vào `VaccinationRecommendation`.
- Thêm `reaction`, `reminder_enabled`, `remind_before_days` vào `VaccinationDose`.

### `app/domain/entities/medical_dictionary.py`

- Thêm `source_file` optional vào `MedicalDictionaryEntry`.
- Mục này không thuộc health schema chính, nhưng cần để test RAG hiện có khớp lại với entity.

## DTOs

### `app/application/dtos/family_dto.py`

- Cho phép payload health nhận `drug_allergies`, `food_allergies`.
- Trả `drug_allergies`, `food_allergies` trong health response.
- Trả hai list này trong family member health response.

### `app/application/dtos/user_dto.py`

- Trả `drug_allergies`, `food_allergies` trong `UserMeHealthProfileResponse`.

### `app/application/dtos/medical_dto.py`

- Thêm `title`, `symptoms`, `test_results`, `doctor_advice`, `updated_at` vào `MedicalRecordResponse`.
- Cho phép create/patch medical record nhận `title`, `symptoms`, `test_results`, `doctor_advice`.

### `app/application/dtos/medicine_dto.py`

- Thêm `profile_id`, `dosage_*`, `use_tags`, `storage_location`, `low_stock_alert_enabled`, `created_at`, `updated_at` vào `MedicineInventoryResponse`.
- Cho phép create/patch medicine inventory nhận các trường mới.

### `app/application/dtos/vaccination_dto.py`

- Thêm `disease_name`, `notes` vào response vaccine recommendation.
- Cho phép create/patch vaccination dose nhận `reaction`, `reminder_enabled`, `remind_before_days`.
- Trả các trường này trong `VaccinationDoseResponse`.

## Ports

### `app/application/ports/family_port.py`

- Mở rộng `upsert_health()` để truyền `drug_allergies`, `food_allergies`.

### `app/application/ports/medical_record_port.py`

- Mở rộng `create_record()` để truyền `title`, `symptoms`, `test_results`, `doctor_advice`.

### `app/application/ports/medicine_inventory_port.py`

- Mở rộng `create()` để truyền các field medicine inventory mới.

### `app/application/ports/vaccination_port.py`

- Mở rộng `create_dose()` và `update_dose()` để truyền `reaction`, `reminder_enabled`, `remind_before_days`.

## Use cases

### `app/application/usecases/family_usecases.py`

- Truyền `drug_allergies`, `food_allergies` từ request xuống repository khi tạo/cập nhật health.

### `app/application/usecases/medical_records_usecases.py`

- Trả các field medical record mới trong response.
- Truyền các field mới khi tạo medical record.

### `app/application/usecases/medicine_inventory_usecases.py`

- Trả các field medicine inventory mới trong response.
- Truyền các field mới khi tạo medicine item.
- Cập nhật logic `alert_low_stock` để tôn trọng `low_stock_alert_enabled`.

### `app/application/usecases/vaccination_usecases.py`

- Trả `disease_name`, `notes` trong recommendation response.
- Trả và cập nhật `reaction`, `reminder_enabled`, `remind_before_days` trong dose response/create/patch.

## Repositories

### `app/infrastructure/repositories/family_repository_pg.py`

- Map `drug_allergies`, `food_allergies` từ `HealthDetailModel` sang `HealthDetail`.
- Lưu/cập nhật hai field này trong `upsert_health()`.

### `app/infrastructure/repositories/medical_record_repository_pg.py`

- Map các field medical record mới từ ORM sang entity.
- Ghi các field mới khi tạo record.
- Cập nhật `updated_at` khi patch record.

### `app/infrastructure/repositories/medicine_inventory_repository_pg.py`

- Map các field medicine inventory mới từ ORM sang entity.
- Ghi các field mới khi tạo item.
- Cập nhật `updated_at` khi patch item.
- Cập nhật logic lọc `low_stock` theo `low_stock_alert_enabled`.

### `app/infrastructure/repositories/vaccination_repository_pg.py`

- Map `disease_name`, `notes` của recommendation.
- Map, tạo và cập nhật `reaction`, `reminder_enabled`, `remind_before_days` của dose.

### `app/infrastructure/repositories/access_control_pg.py`

- Cập nhật mapping entity dùng trong access context cho medical record, medicine inventory và vaccination dose để không mất field mới.

### `app/infrastructure/repositories/medical_dictionary_repository.py`

- Map `source_file` vào `MedicalDictionaryEntry` nếu model có field này.
- Mục này phục vụ test RAG và tương thích với migration dictionary hiện tại.

## Verification

- `python -m compileall app`: passed.
- `.venv\Scripts\python.exe -m pytest tests/unit`: passed, `87 passed`.
- Pytest có warning quyền ghi `.pytest_cache`, nhưng test không fail.

## Ngoài phạm vi thay đổi

- Không tạo luồng `prescriptions` riêng vì file đánh giá ghi phần này là `maybe` không cần và backend hiện đang dùng `medicine_inventory` cho luồng thuốc chính.
- Không xử lý các mục untracked không liên quan: `python-3.12.10-amd64.exe`, `tmp/`, `pytest-cache-files-*`.

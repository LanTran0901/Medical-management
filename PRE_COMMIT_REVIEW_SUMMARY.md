# Pre-Commit Review Summary

This file summarizes current Git changes so you can review quickly before commit.

## 1) Database & Migration Changes

- Added migration chain for schema alignment and hardening:
  - `app/alembic/versions/20260412_2100_align_health_ui_schema.py`
  - `app/alembic/versions/20260413_1200_health_details_emergency_contacts_jsonb.py`
  - `app/alembic/versions/20260413_1400_drop_follow_up_appointments_department.py`
  - `app/alembic/versions/20260413_1500_align_medicine_tables_defaults.py`
  - `app/alembic/versions/20260413_1600_drop_medicine_inventory_family_relation.py`
  - `app/alembic/versions/20260413_1700_create_family_medicine_inventory.py`
  - `app/alembic/versions/20260413_1800_harden_family_invites_constraints.py`
  - `app/alembic/versions/20260413_1900_backfill_family_medicine_inventory.py`
- Main intent:
  - Drop old follow-up column `department`.
  - Harden `family_invites` with required target + pending uniqueness.
  - Shift family medicine flow to `family_medicine_inventory`.
  - Backfill data into new family-scoped medicine table.

## 2) ORM/Model Layer

- Updated models:
  - `app/infrastructure/config/database/postgres/models/family_models.py`
  - `app/infrastructure/config/database/postgres/models/medical_record_models.py`
  - `app/infrastructure/config/database/postgres/models/medicine_inventory_model.py`
  - `app/infrastructure/config/database/postgres/models/profile_models.py`
  - `app/infrastructure/config/database/postgres/models/vaccination_models.py`
  - `app/infrastructure/config/database/postgres/models/__init__.py`
- Added new family medicine model wiring:
  - `FamilyMedicineInventoryModel` export and registration.

## 3) API / Usecase / Repository Updates

- Family medicine endpoints now use family-scoped table:
  - `app/api/families_router.py`
  - `app/api/dependencies.py`
  - `app/application/usecases/family_medicine_inventory_usecases.py` (new)
  - `app/infrastructure/repositories/family_medicine_inventory_repository_pg.py` (new)
  - `app/application/ports/family_medicine_inventory_port.py` (new)
  - `app/domain/entities/family_medicine_inventory.py` (new)
- Medicine create validation hardening:
  - `app/application/usecases/medicine_inventory_usecases.py`
  - Enforces `profile_id` presence and membership in target family.
- Invite conflict handling hardened:
  - `app/application/usecases/family_usecases.py`
  - Maps DB unique violation to domain `ConflictError`.

## 4) DTO / Domain Contract Changes

- Updated contracts and mappings:
  - `app/application/dtos/family_dto.py`
  - `app/application/dtos/medical_dto.py`
  - `app/application/dtos/medicine_dto.py`
  - `app/application/dtos/user_dto.py`
  - `app/application/dtos/vaccination_dto.py`
  - `app/domain/entities/health_detail.py`
  - `app/domain/entities/medical_record.py`
  - `app/domain/entities/medicine_inventory.py`
  - `app/domain/entities/vaccination.py`
  - `app/domain/entities/medical_dictionary.py`

## 5) Seed & Docs

- Seed scripts updated for new family medicine table:
  - `app/scripts/seed_vietnam_families_demo.sql`
  - `app/scripts/seed_vietnam_families_demo_static.sql`
  - `app/scripts/seed_vietnam_families_demo_pg.py`
- Schema docs updated:
  - `docs/app_schema.mmd`
- Additional schema notes:
  - `SCHEMA_ALIGNMENT_CHANGES.md` (untracked)

## 6) Tests Added/Changed

- New unit tests:
  - `tests/unit/test_medicine_inventory_service.py`
  - `tests/unit/test_family_invite_constraint_handling.py`
- Existing tests adjusted:
  - `tests/unit/test_families_service.py`
  - `tests/unit/test_family_dto.py`

## 7) Other Untracked Files (non-code/noise)

- Installer/log/temp artifacts:
  - `python-3.12.10-amd64.exe`
  - `tmp/api-7543.err.log`
  - `tmp/api-7543.out.log`
  - `tmp/app.stderr.log`
  - `tmp/app.stdout.log`
  - `tmp/local-openapi.json`
  - `tmp/prod-openapi.json`

Recommendation: avoid committing these noise artifacts unless explicitly needed.

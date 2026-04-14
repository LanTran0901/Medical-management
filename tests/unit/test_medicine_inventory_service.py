from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.dtos.medicine_dto import CreateMedicineInventoryRequest
from app.application.family_errors import ForbiddenError
from app.application.usecases.medicine_inventory_usecases import MedicineInventoryService
from app.domain.entities.medicine_inventory import MedicineInventory


def _medicine_entity() -> MedicineInventory:
    now = datetime.now(timezone.utc)
    return MedicineInventory(
        id=uuid4(),
        profile_id=uuid4(),
        medicine_name="Paracetamol",
        medicine_type=None,
        expiry_date=date.today(),
        quantity_stock=Decimal("10"),
        unit="vien",
        min_stock_alert=Decimal("2"),
        instruction=None,
        dosage_value=None,
        dosage_unit=None,
        dosage_per_use_value=None,
        dosage_per_use_unit=None,
        use_tags=[],
        storage_location=None,
        expiry_alert_days_before=30,
        low_stock_alert_enabled=True,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_create_item_requires_profile_id() -> None:
    repo = AsyncMock()
    access = AsyncMock()
    family_repo = AsyncMock()
    svc = MedicineInventoryService(repo, access, family_repo)

    with pytest.raises(ForbiddenError, match="profile_id is required"):
        await svc.create_item(
            uuid4(),
            uuid4(),
            CreateMedicineInventoryRequest(
                profile_id=None,
                medicine_name="Paracetamol",
            ),
        )


@pytest.mark.asyncio
async def test_create_item_rejects_profile_outside_family() -> None:
    repo = AsyncMock()
    access = AsyncMock()
    family_repo = AsyncMock()
    family_repo.profile_in_family = AsyncMock(return_value=False)
    svc = MedicineInventoryService(repo, access, family_repo)

    with pytest.raises(ForbiddenError, match="does not belong"):
        await svc.create_item(
            uuid4(),
            uuid4(),
            CreateMedicineInventoryRequest(
                profile_id=uuid4(),
                medicine_name="Paracetamol",
            ),
        )


@pytest.mark.asyncio
async def test_create_item_success_with_valid_profile() -> None:
    repo = AsyncMock()
    access = AsyncMock()
    family_repo = AsyncMock()
    family_repo.profile_in_family = AsyncMock(return_value=True)
    entity = _medicine_entity()
    repo.create = AsyncMock(return_value=entity)
    svc = MedicineInventoryService(repo, access, family_repo)

    out = await svc.create_item(
        uuid4(),
        uuid4(),
        CreateMedicineInventoryRequest(
            profile_id=entity.profile_id,
            medicine_name="Paracetamol",
        ),
    )

    assert out.id == entity.id
    repo.create.assert_awaited_once()

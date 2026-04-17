from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.family_medicine_inventory_port import FamilyMedicineInventoryRepositoryPort
from app.domain.entities.family_medicine_inventory import FamilyMedicineInventory
from app.infrastructure.config.database.postgres.models.medicine_inventory_model import (
    FamilyMedicineInventoryModel,
    MedicineInventoryModel,
)


class FamilyMedicineInventoryRepositoryPG(FamilyMedicineInventoryRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_entity(model: FamilyMedicineInventoryModel) -> FamilyMedicineInventory:
        return FamilyMedicineInventory(
            id=model.id,
            family_id=model.family_id,
            created_by_user_id=model.created_by_user_id,
            medicine_name=model.medicine_name,
            quantity_stock=model.quantity_stock,
            unit=model.unit,
            expiry_date=model.expiry_date,
            storage_location=model.storage_location,
            note=model.note,
            min_stock_alert=model.min_stock_alert,
            low_stock_alert_enabled=model.low_stock_alert_enabled,
            expiry_alert_days_before=model.expiry_alert_days_before,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def list_by_family(self, family_id: UUID) -> list[FamilyMedicineInventory]:
        stmt = (
            select(FamilyMedicineInventoryModel)
            .where(FamilyMedicineInventoryModel.family_id == family_id)
            .order_by(FamilyMedicineInventoryModel.medicine_name.asc())
        )
        result = await self.session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def create(
        self,
        *,
        family_id: UUID,
        created_by_user_id: UUID,
        profile_id: UUID,
        medicine_name: str,
        quantity_stock: Decimal,
        unit: str,
        expiry_date: date,
        storage_location: str | None,
        note: str | None,
        min_stock_alert: Decimal,
        low_stock_alert_enabled: bool,
        expiry_alert_days_before: int,
    ) -> FamilyMedicineInventory:
        normalized_name = medicine_name.strip()
        shared_item_id = uuid.uuid4()
        family_model = FamilyMedicineInventoryModel(
            id=shared_item_id,
            family_id=family_id,
            created_by_user_id=created_by_user_id,
            medicine_name=normalized_name,
            quantity_stock=quantity_stock,
            unit=unit,
            expiry_date=expiry_date,
            storage_location=storage_location,
            note=note,
            min_stock_alert=min_stock_alert,
            low_stock_alert_enabled=low_stock_alert_enabled,
            expiry_alert_days_before=expiry_alert_days_before,
        )
        medicine_model = MedicineInventoryModel(
            id=shared_item_id,
            profile_id=profile_id,
            medicine_name=normalized_name,
            medicine_type=None,
            expiry_date=expiry_date,
            quantity_stock=quantity_stock,
            unit=unit,
            min_stock_alert=min_stock_alert,
            instruction=note,
            dosage_value=None,
            dosage_unit=None,
            dosage_per_use_value=None,
            dosage_per_use_unit=None,
            storage_location=storage_location,
            expiry_alert_days_before=expiry_alert_days_before,
            low_stock_alert_enabled=low_stock_alert_enabled,
        )
        self.session.add(family_model)
        self.session.add(medicine_model)
        await self.session.flush()
        await self.session.refresh(family_model)
        return self._to_entity(family_model)

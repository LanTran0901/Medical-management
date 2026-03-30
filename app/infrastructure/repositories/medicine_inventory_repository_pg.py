from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.medicine_inventory_port import MedicineInventoryRepositoryPort
from app.domain.entities.medicine_inventory import MedicineInventory
from app.infrastructure.config.database.postgres.models.medicine_inventory_model import (
    MedicineInventoryModel,
)


def _alert_flags(m: MedicineInventoryModel, today: date) -> tuple[bool, bool, bool]:
    """Returns (low_stock, expiring, expired)."""
    low = False
    if m.min_stock_alert is not None and m.quantity_stock is not None:
        low = m.quantity_stock <= m.min_stock_alert

    expired = False
    expiring = False
    if m.expiry_date is not None:
        if m.expiry_date < today:
            expired = True
        elif m.expiry_date == today:
            expiring = True
        elif m.expiry_alert_days_before is not None:
            start = m.expiry_date - timedelta(days=int(m.expiry_alert_days_before))
            if start <= today <= m.expiry_date:
                expiring = True
    return low, expiring, expired


class MedicineInventoryRepositoryPG(MedicineInventoryRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_entity(model: MedicineInventoryModel) -> MedicineInventory:
        return MedicineInventory(
            id=model.id,
            family_id=model.family_id,
            medicine_name=model.medicine_name,
            medicine_type=model.medicine_type,
            expiry_date=model.expiry_date,
            quantity_stock=model.quantity_stock,
            unit=model.unit,
            min_stock_alert=model.min_stock_alert,
            instruction=model.instruction,
            expiry_alert_days_before=model.expiry_alert_days_before,
        )

    async def list_by_family(
        self,
        family_id: UUID,
        *,
        alert: str | None,
    ) -> list[MedicineInventory]:
        stmt = (
            select(MedicineInventoryModel)
            .where(MedicineInventoryModel.family_id == family_id)
            .order_by(MedicineInventoryModel.medicine_name)
        )
        r = await self.session.execute(stmt)
        rows = list(r.scalars().all())
        today = date.today()
        if alert == "low_stock":
            rows = [m for m in rows if _alert_flags(m, today)[0]]
        elif alert == "expiring":
            rows = [m for m in rows if _alert_flags(m, today)[1] or _alert_flags(m, today)[2]]
        return [self._to_entity(row) for row in rows]

    async def get_by_id(self, item_id: UUID) -> MedicineInventory | None:
        model = await self.session.get(MedicineInventoryModel, item_id)
        return self._to_entity(model) if model else None

    async def create(
        self,
        *,
        family_id: UUID,
        medicine_name: str,
        medicine_type: str | None,
        expiry_date: date | None,
        quantity_stock: Decimal | None,
        unit: str | None,
        min_stock_alert: Decimal | None,
        instruction: str | None,
        expiry_alert_days_before: int | None,
    ) -> MedicineInventory:
        m = MedicineInventoryModel(
            family_id=family_id,
            medicine_name=medicine_name.strip(),
            medicine_type=medicine_type,
            expiry_date=expiry_date,
            quantity_stock=quantity_stock,
            unit=unit,
            min_stock_alert=min_stock_alert,
            instruction=instruction,
            expiry_alert_days_before=expiry_alert_days_before,
        )
        self.session.add(m)
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_entity(m)

    async def apply_patch(
        self,
        item_id: UUID,
        fields: dict[str, object],
    ) -> MedicineInventory | None:
        m = await self.session.get(MedicineInventoryModel, item_id)
        if m is None:
            return None
        for key, value in fields.items():
            if key == "medicine_name" and isinstance(value, str):
                setattr(m, key, value.strip())
            else:
                setattr(m, key, value)
        await self.session.flush()
        await self.session.refresh(m)
        return self._to_entity(m)

    async def delete(self, item_id: UUID) -> bool:
        m = await self.session.get(MedicineInventoryModel, item_id)
        if m is None:
            return False
        await self.session.delete(m)
        await self.session.flush()
        return True

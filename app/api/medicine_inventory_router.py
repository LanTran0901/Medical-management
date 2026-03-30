from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_medicine_inventory_service
from app.application.dtos.medicine_dto import MedicineInventoryResponse, PatchMedicineInventoryRequest
from app.application.family_errors import ForbiddenError, NotFoundError
from app.application.usecases.medicine_inventory_usecases import MedicineInventoryService
from app.domain.entities.user import User

router = APIRouter(prefix="/medicine-inventory", tags=["medicine-inventory"])


def _handle_error(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message or "Not found") from exc
    if isinstance(exc, ForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message or "Forbidden") from exc


@router.get("/{item_id}", response_model=MedicineInventoryResponse, summary="Get one medicine item")
async def get_medicine_inventory(
    item_id: UUID,
    user: User = Depends(get_current_user),
    svc: MedicineInventoryService = Depends(get_medicine_inventory_service),
) -> MedicineInventoryResponse:
    try:
        return await svc.get_item_by_id(item_id, user.id)
    except Exception as exc:
        _handle_error(exc)
        raise


@router.patch("/{item_id}", response_model=MedicineInventoryResponse, summary="Update medicine item")
async def patch_medicine_inventory(
    item_id: UUID,
    body: PatchMedicineInventoryRequest,
    user: User = Depends(get_current_user),
    svc: MedicineInventoryService = Depends(get_medicine_inventory_service),
) -> MedicineInventoryResponse:
    try:
        return await svc.patch_item(item_id, user.id, body)
    except Exception as exc:
        _handle_error(exc)
        raise


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete medicine item")
async def delete_medicine_inventory(
    item_id: UUID,
    user: User = Depends(get_current_user),
    svc: MedicineInventoryService = Depends(get_medicine_inventory_service),
) -> None:
    try:
        await svc.delete_item(item_id, user.id)
    except Exception as exc:
        _handle_error(exc)
        raise

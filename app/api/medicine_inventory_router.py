from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_current_user,
    get_medicine_inventory_service,
    get_medicine_schedule_service,
)
from app.application.dtos.medicine_dto import MedicineInventoryResponse, PatchMedicineInventoryRequest
from app.application.dtos.medicine_schedule_dto import (
    CreateMedicineScheduleRequest,
    MedicineScheduleResponse,
    PatchMedicineScheduleRequest,
)
from app.application.family_errors import ConflictError, ForbiddenError, NotFoundError
from app.application.usecases.medicine_inventory_usecases import MedicineInventoryService
from app.application.usecases.medicine_schedule_usecases import MedicineScheduleService
from app.domain.entities.user import User

router = APIRouter(prefix="/medicine-inventory", tags=["medicine-inventory"])


def _handle_error(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message or "Not found") from exc
    if isinstance(exc, ForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message or "Forbidden") from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message or "Conflict") from exc


# --- Schedules: flat paths (align with /medicine-inventory/{item_id}); no /families nesting ---


@router.patch(
    "/schedules/{schedule_id}",
    response_model=MedicineScheduleResponse,
    summary="Update or pause a medicine schedule",
)
async def patch_medicine_schedule(
    schedule_id: UUID,
    body: PatchMedicineScheduleRequest,
    user: User = Depends(get_current_user),
    svc: MedicineScheduleService = Depends(get_medicine_schedule_service),
) -> MedicineScheduleResponse:
    try:
        return await svc.patch(schedule_id, user.id, body)
    except Exception as exc:
        _handle_error(exc)
        raise


@router.delete(
    "/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a medicine schedule",
)
async def delete_medicine_schedule(
    schedule_id: UUID,
    user: User = Depends(get_current_user),
    svc: MedicineScheduleService = Depends(get_medicine_schedule_service),
) -> None:
    try:
        await svc.delete(schedule_id, user.id)
    except Exception as exc:
        _handle_error(exc)
        raise


@router.get(
    "/{item_id}/schedules",
    response_model=list[MedicineScheduleResponse],
    summary="List MEDICINE reminder schedules for an inventory item",
)
async def list_medicine_schedules(
    item_id: UUID,
    user: User = Depends(get_current_user),
    svc: MedicineScheduleService = Depends(get_medicine_schedule_service),
) -> list[MedicineScheduleResponse]:
    try:
        return await svc.list_for_medicine(item_id, user.id)
    except Exception as exc:
        _handle_error(exc)
        raise


@router.post(
    "/{item_id}/schedules",
    response_model=MedicineScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a MEDICINE reminder schedule (UTC remind_time; one row per daily time)",
)
async def create_medicine_schedule(
    item_id: UUID,
    body: CreateMedicineScheduleRequest,
    user: User = Depends(get_current_user),
    svc: MedicineScheduleService = Depends(get_medicine_schedule_service),
) -> MedicineScheduleResponse:
    try:
        return await svc.create(item_id, user.id, body)
    except Exception as exc:
        _handle_error(exc)
        raise


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

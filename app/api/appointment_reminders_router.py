"""CRUD for appointment_reminders (tái khám / vaccine)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_appointment_reminder_service, get_current_user
from app.application.dtos.appointment_reminder_dto import (
    AppointmentReminderResponse,
    CreateAppointmentReminderRequest,
    PatchAppointmentReminderRequest,
)
from app.application.family_errors import ForbiddenError, NotFoundError
from app.application.usecases.appointment_reminder_usecases import AppointmentReminderService
from app.domain.entities.user import User

router = APIRouter(tags=["appointment-reminders"])


def _nf(e: NotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=e.message or "Not found",
    )


@router.get(
    "/profiles/{profile_id}/appointment-reminders",
    response_model=list[AppointmentReminderResponse],
    summary="List appointment reminders for a profile",
)
async def list_appointment_reminders(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    svc: AppointmentReminderService = Depends(get_appointment_reminder_service),
) -> list[AppointmentReminderResponse]:
    try:
        return await svc.list_for_profile(profile_id, user.id)
    except NotFoundError as e:
        raise _nf(e) from e
    except ForbiddenError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message or "Forbidden",
        ) from e


@router.post(
    "/profiles/{profile_id}/appointment-reminders",
    response_model=AppointmentReminderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create appointment reminder",
)
async def create_appointment_reminder(
    profile_id: UUID,
    body: CreateAppointmentReminderRequest,
    user: User = Depends(get_current_user),
    svc: AppointmentReminderService = Depends(get_appointment_reminder_service),
) -> AppointmentReminderResponse:
    return await svc.create(profile_id, user.id, body)


@router.patch(
    "/appointment-reminders/{reminder_id}",
    response_model=AppointmentReminderResponse,
    summary="Update appointment reminder",
)
async def patch_appointment_reminder(
    reminder_id: UUID,
    body: PatchAppointmentReminderRequest,
    user: User = Depends(get_current_user),
    svc: AppointmentReminderService = Depends(get_appointment_reminder_service),
) -> AppointmentReminderResponse:
    try:
        return await svc.patch(reminder_id, user.id, body)
    except NotFoundError as e:
        raise _nf(e) from e


@router.delete(
    "/appointment-reminders/{reminder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete appointment reminder",
)
async def delete_appointment_reminder(
    reminder_id: UUID,
    user: User = Depends(get_current_user),
    svc: AppointmentReminderService = Depends(get_appointment_reminder_service),
) -> None:
    try:
        await svc.delete(reminder_id, user.id)
    except NotFoundError as e:
        raise _nf(e) from e

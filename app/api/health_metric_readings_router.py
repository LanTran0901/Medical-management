"""CRUD for health_metric_readings (profile-scoped vitals)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_health_metric_readings_service
from app.application.dtos.health_metric_reading_dto import (
    CreateHealthMetricReadingRequest,
    PatchHealthMetricReadingRequest,
)
from app.application.dtos.user_dto import HealthMetricReadingResponse
from app.application.family_errors import ForbiddenError, NotFoundError
from app.application.usecases.health_metric_reading_usecases import HealthMetricReadingsService
from app.domain.entities.user import User

router = APIRouter(tags=["health-metric-readings"])


def _nf(exc: NotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=exc.message or "Not found",
    )


def _fb(exc: ForbiddenError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=exc.message or "Forbidden",
    )


@router.get(
    "/profiles/{profile_id}/health-metric-readings",
    response_model=list[HealthMetricReadingResponse],
    summary="List health metric readings for profile",
)
async def list_health_metric_readings(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    svc: HealthMetricReadingsService = Depends(get_health_metric_readings_service),
) -> list[HealthMetricReadingResponse]:
    try:
        return await svc.list_for_profile(profile_id, user.id)
    except ForbiddenError as exc:
        raise _fb(exc) from exc
    except NotFoundError as exc:
        raise _nf(exc) from exc


@router.post(
    "/profiles/{profile_id}/health-metric-readings",
    response_model=HealthMetricReadingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a health metric reading",
)
async def create_health_metric_reading(
    profile_id: UUID,
    body: CreateHealthMetricReadingRequest,
    user: User = Depends(get_current_user),
    svc: HealthMetricReadingsService = Depends(get_health_metric_readings_service),
) -> HealthMetricReadingResponse:
    try:
        return await svc.create(profile_id, user.id, body)
    except ForbiddenError as exc:
        raise _fb(exc) from exc
    except NotFoundError as exc:
        raise _nf(exc) from exc


@router.get(
    "/health-metric-readings/{reading_id}",
    response_model=HealthMetricReadingResponse,
    summary="Get one health metric reading",
)
async def get_health_metric_reading(
    reading_id: UUID,
    user: User = Depends(get_current_user),
    svc: HealthMetricReadingsService = Depends(get_health_metric_readings_service),
) -> HealthMetricReadingResponse:
    try:
        return await svc.get_by_id(reading_id, user.id)
    except ForbiddenError as exc:
        raise _fb(exc) from exc
    except NotFoundError as exc:
        raise _nf(exc) from exc


@router.patch(
    "/health-metric-readings/{reading_id}",
    response_model=HealthMetricReadingResponse,
    summary="Update a health metric reading",
)
async def patch_health_metric_reading(
    reading_id: UUID,
    body: PatchHealthMetricReadingRequest,
    user: User = Depends(get_current_user),
    svc: HealthMetricReadingsService = Depends(get_health_metric_readings_service),
) -> HealthMetricReadingResponse:
    try:
        return await svc.patch(reading_id, user.id, body)
    except ForbiddenError as exc:
        raise _fb(exc) from exc
    except NotFoundError as exc:
        raise _nf(exc) from exc


@router.delete(
    "/health-metric-readings/{reading_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a health metric reading",
)
async def delete_health_metric_reading(
    reading_id: UUID,
    user: User = Depends(get_current_user),
    svc: HealthMetricReadingsService = Depends(get_health_metric_readings_service),
) -> None:
    try:
        await svc.delete(reading_id, user.id)
    except ForbiddenError as exc:
        raise _fb(exc) from exc
    except NotFoundError as exc:
        raise _nf(exc) from exc

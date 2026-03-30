"""Vaccination catalog + profile subscriptions (US4)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_vaccination_service
from app.application.dtos.vaccination_dto import (
    CreateVaccinationDoseRequest,
    PatchUserVaccinationRequest,
    PatchVaccinationDoseRequest,
    SubscribeUserVaccinationRequest,
    UserVaccinationResponse,
    VaccinationDoseResponse,
    VaccinationRecommendationResponse,
)
from app.application.family_errors import ConflictError, ForbiddenError, NotFoundError
from app.application.usecases.vaccination_usecases import VaccinationService
from app.domain.entities.user import User

router = APIRouter(tags=["vaccinations"])


def _nf(e: NotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=e.message or "Not found",
    )


def _fb(e: ForbiddenError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=e.message or "Forbidden",
    )


def _cf(e: ConflictError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=e.message or "Conflict",
    )


@router.get(
    "/vaccination-recommendations",
    response_model=list[VaccinationRecommendationResponse],
    summary="List vaccination catalog (recommendations)",
)
async def list_vaccination_recommendations(
    _user: User = Depends(get_current_user),
    svc: VaccinationService = Depends(get_vaccination_service),
) -> list[VaccinationRecommendationResponse]:
    return await svc.list_recommendations()


@router.get(
    "/profiles/{profile_id}/vaccinations",
    response_model=list[UserVaccinationResponse],
    summary="List subscribed vaccinations for profile",
)
async def list_profile_vaccinations(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    svc: VaccinationService = Depends(get_vaccination_service),
) -> list[UserVaccinationResponse]:
    try:
        return await svc.list_profile_vaccinations(profile_id, user.id)
    except ForbiddenError as e:
        raise _fb(e) from e
    except NotFoundError as e:
        raise _nf(e) from e


@router.post(
    "/profiles/{profile_id}/vaccinations",
    response_model=UserVaccinationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe profile to a vaccine from catalog",
)
async def subscribe_profile_vaccination(
    profile_id: UUID,
    body: SubscribeUserVaccinationRequest,
    user: User = Depends(get_current_user),
    svc: VaccinationService = Depends(get_vaccination_service),
) -> UserVaccinationResponse:
    try:
        return await svc.subscribe(profile_id, user.id, body)
    except ForbiddenError as e:
        raise _fb(e) from e
    except NotFoundError as e:
        raise _nf(e) from e
    except ConflictError as e:
        raise _cf(e) from e


@router.get(
    "/user-vaccinations/{user_vaccination_id}",
    response_model=UserVaccinationResponse,
    summary="Get one user vaccination subscription",
)
async def get_user_vaccination(
    user_vaccination_id: UUID,
    user: User = Depends(get_current_user),
    svc: VaccinationService = Depends(get_vaccination_service),
) -> UserVaccinationResponse:
    try:
        return await svc.get_user_vaccination_by_id(user_vaccination_id, user.id)
    except ForbiddenError as e:
        raise _fb(e) from e
    except NotFoundError as e:
        raise _nf(e) from e


@router.patch(
    "/user-vaccinations/{user_vaccination_id}",
    response_model=UserVaccinationResponse,
    summary="Update subscription status",
)
async def patch_user_vaccination(
    user_vaccination_id: UUID,
    body: PatchUserVaccinationRequest,
    user: User = Depends(get_current_user),
    svc: VaccinationService = Depends(get_vaccination_service),
) -> UserVaccinationResponse:
    try:
        return await svc.patch_user_vaccination_by_id(user_vaccination_id, user.id, body)
    except ForbiddenError as e:
        raise _fb(e) from e
    except NotFoundError as e:
        raise _nf(e) from e


@router.get(
    "/user-vaccinations/{user_vaccination_id}/doses",
    response_model=list[VaccinationDoseResponse],
    summary="List doses for a subscription",
)
async def list_vaccination_doses(
    user_vaccination_id: UUID,
    user: User = Depends(get_current_user),
    svc: VaccinationService = Depends(get_vaccination_service),
) -> list[VaccinationDoseResponse]:
    try:
        return await svc.list_doses_by_user_vaccination(user_vaccination_id, user.id)
    except ForbiddenError as e:
        raise _fb(e) from e
    except NotFoundError as e:
        raise _nf(e) from e


@router.post(
    "/user-vaccinations/{user_vaccination_id}/doses",
    response_model=VaccinationDoseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a dose (scheduled or administered)",
)
async def create_vaccination_dose(
    user_vaccination_id: UUID,
    body: CreateVaccinationDoseRequest,
    user: User = Depends(get_current_user),
    svc: VaccinationService = Depends(get_vaccination_service),
) -> VaccinationDoseResponse:
    try:
        return await svc.create_dose_by_user_vaccination(user_vaccination_id, user.id, body)
    except ForbiddenError as e:
        raise _fb(e) from e
    except NotFoundError as e:
        raise _nf(e) from e
    except ConflictError as e:
        raise _cf(e) from e


@router.get(
    "/vaccination-doses/{dose_id}",
    response_model=VaccinationDoseResponse,
    summary="Get one dose",
)
async def get_vaccination_dose(
    dose_id: UUID,
    user: User = Depends(get_current_user),
    svc: VaccinationService = Depends(get_vaccination_service),
) -> VaccinationDoseResponse:
    try:
        return await svc.get_dose_by_id(dose_id, user.id)
    except ForbiddenError as e:
        raise _fb(e) from e
    except NotFoundError as e:
        raise _nf(e) from e


@router.patch(
    "/vaccination-doses/{dose_id}",
    response_model=VaccinationDoseResponse,
    summary="Update a dose",
)
async def patch_vaccination_dose(
    dose_id: UUID,
    body: PatchVaccinationDoseRequest,
    user: User = Depends(get_current_user),
    svc: VaccinationService = Depends(get_vaccination_service),
) -> VaccinationDoseResponse:
    try:
        return await svc.patch_dose_by_id(dose_id, user.id, body)
    except ForbiddenError as e:
        raise _fb(e) from e
    except NotFoundError as e:
        raise _nf(e) from e


@router.delete(
    "/vaccination-doses/{dose_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a dose",
)
async def delete_vaccination_dose(
    dose_id: UUID,
    user: User = Depends(get_current_user),
    svc: VaccinationService = Depends(get_vaccination_service),
) -> None:
    try:
        await svc.delete_dose_by_id(dose_id, user.id)
    except ForbiddenError as e:
        raise _fb(e) from e
    except NotFoundError as e:
        raise _nf(e) from e

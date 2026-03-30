"""Canonical profile item routes."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies import get_current_user, get_families_service
from app.application.dtos.family_dto import (
    HealthDetailResponse,
    LinkProfileRequest,
    PatchHealthDetailRequest,
    PatchProfileRequest,
    ProfileResponse,
)
from app.application.family_errors import ForbiddenError, NotFoundError
from app.application.usecases.family_usecases import FamiliesService
from app.domain.entities.user import User

router = APIRouter(prefix="/profiles", tags=["profiles"])


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


@router.get("/{profile_id}", response_model=ProfileResponse, summary="Get profile")
async def get_profile(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> ProfileResponse:
    try:
        p = await svc.get_profile_by_id(profile_id, user.id)
        return ProfileResponse.from_entity(p)
    except NotFoundError as exc:
        raise _nf(exc) from exc
    except ForbiddenError as exc:
        raise _fb(exc) from exc


@router.patch("/{profile_id}", response_model=ProfileResponse, summary="Update profile (status, fields)")
async def patch_profile(
    profile_id: UUID,
    body: PatchProfileRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> ProfileResponse:
    try:
        p = await svc.patch_profile_by_id(profile_id, user.id, body)
        return ProfileResponse.from_entity(p)
    except NotFoundError as exc:
        raise _nf(exc) from exc
    except ForbiddenError as exc:
        raise _fb(exc) from exc


@router.patch("/{profile_id}/link", response_model=ProfileResponse, summary="Link profile to user")
async def link_profile(
    profile_id: UUID,
    body: LinkProfileRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> ProfileResponse:
    try:
        p = await svc.link_profile_by_id(profile_id, user.id, body.user_id)
        return ProfileResponse.from_entity(p)
    except NotFoundError as exc:
        raise _nf(exc) from exc
    except ForbiddenError as exc:
        raise _fb(exc) from exc


@router.get("/{profile_id}/health", response_model=HealthDetailResponse, summary="Get profile health")
async def get_health(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> HealthDetailResponse:
    try:
        h = await svc.get_health_by_profile_id(profile_id, user.id)
        if h is None:
            return HealthDetailResponse(
                profile_id=profile_id,
                blood_type=None,
                chronic_diseases=None,
                allergies=None,
                emergency_contact=None,
                notes=None,
                updated_at=datetime.now(timezone.utc),
            )
        return HealthDetailResponse.from_entity(h)
    except NotFoundError as exc:
        raise _nf(exc) from exc
    except ForbiddenError as exc:
        raise _fb(exc) from exc


@router.patch("/{profile_id}/health", response_model=HealthDetailResponse, summary="Patch profile health")
async def patch_health(
    profile_id: UUID,
    body: PatchHealthDetailRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> HealthDetailResponse:
    try:
        h = await svc.patch_health_by_profile_id(profile_id, user.id, body)
        return HealthDetailResponse.from_entity(h)
    except NotFoundError as exc:
        raise _nf(exc) from exc
    except ForbiddenError as exc:
        raise _fb(exc) from exc


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete profile and remove family memberships (FR-005)",
)
async def delete_profile(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> Response:
    try:
        await svc.delete_profile_by_id(profile_id, user.id)
    except NotFoundError as exc:
        raise _nf(exc) from exc
    except ForbiddenError as exc:
        raise _fb(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

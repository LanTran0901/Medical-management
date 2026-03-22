from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_families_service
from app.application.dtos.family_dto import (
    CreateFamilyRequest,
    CreateFamilyResponse,
    CreateProfileInFamilyRequest,
    FamilyResponse,
    FamilySummaryResponse,
    HealthDetailResponse,
    JoinFamilyRequest,
    LinkProfileRequest,
    MembershipResponse,
    PatchFamilyRequest,
    PatchHealthDetailRequest,
    PatchMembershipRoleRequest,
    PatchProfileRequest,
    ProfileResponse,
)
from app.application.family_errors import ConflictError, ForbiddenError, NotFoundError
from app.application.usecases.family_usecases import FamiliesService
from app.domain.entities.user import User

router = APIRouter(prefix="/families", tags=["families"])


def _handle_family_error(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message or "Not found",
        ) from exc
    if isinstance(exc, ForbiddenError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.message or "Forbidden",
        ) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.message or "Conflict",
        ) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("", response_model=CreateFamilyResponse, status_code=status.HTTP_201_CREATED)
async def create_family(
    body: CreateFamilyRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> CreateFamilyResponse:
    try:
        fam, prof, mem = await svc.create_family(user.id, body)
        return CreateFamilyResponse(
            family=FamilyResponse.from_entity(fam),
            profile=ProfileResponse.from_entity(prof),
            membership=MembershipResponse.from_entity(mem),
        )
    except Exception as e:
        _handle_family_error(e)
        raise


@router.get("", response_model=list[FamilySummaryResponse])
async def list_families(
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> list[FamilySummaryResponse]:
    families = await svc.list_my_families(user.id)
    return [FamilySummaryResponse.from_entity(f) for f in families]


@router.post("/join", status_code=status.HTTP_200_OK)
async def join_family(
    body: JoinFamilyRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> dict:
    try:
        fam, _prof = await svc.join_family(user.id, body)
        return {
            "family_id": str(fam.id),
            "family_name": fam.family_name,
            "message": "Joined family",
        }
    except Exception as e:
        _handle_family_error(e)
        raise


@router.get("/{family_id}", response_model=FamilyResponse)
async def get_family(
    family_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> FamilyResponse:
    try:
        fam = await svc.get_family(family_id, user.id)
        return FamilyResponse.from_entity(fam)
    except Exception as e:
        _handle_family_error(e)
        raise


@router.patch("/{family_id}", response_model=FamilyResponse)
async def patch_family(
    family_id: UUID,
    body: PatchFamilyRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> FamilyResponse:
    try:
        fam = await svc.patch_family(family_id, user.id, body)
        return FamilyResponse.from_entity(fam)
    except Exception as e:
        _handle_family_error(e)
        raise


@router.post("/{family_id}/invite/rotate", response_model=FamilyResponse)
async def rotate_invite(
    family_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> FamilyResponse:
    try:
        fam = await svc.rotate_invite(family_id, user.id)
        return FamilyResponse.from_entity(fam)
    except Exception as e:
        _handle_family_error(e)
        raise


@router.get("/{family_id}/members", response_model=list[MembershipResponse])
async def list_members(
    family_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> list[MembershipResponse]:
    try:
        rows = await svc.list_members(family_id, user.id)
        return [
            MembershipResponse.from_entity(
                m,
                profile_full_name=p.full_name,
                linked_user_id=p.linked_user_id,
            )
            for m, p in rows
        ]
    except Exception as e:
        _handle_family_error(e)
        raise


@router.patch("/{family_id}/members/{membership_id}", response_model=MembershipResponse)
async def patch_member_role(
    family_id: UUID,
    membership_id: UUID,
    body: PatchMembershipRoleRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> MembershipResponse:
    try:
        m = await svc.patch_membership_role(family_id, membership_id, user.id, body)
        return MembershipResponse.from_entity(m)
    except Exception as e:
        _handle_family_error(e)
        raise


@router.delete("/{family_id}/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    family_id: UUID,
    membership_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> None:
    try:
        await svc.delete_membership(family_id, membership_id, user.id)
    except Exception as e:
        _handle_family_error(e)
        raise


@router.post(
    "/{family_id}/profiles",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile_in_family(
    family_id: UUID,
    body: CreateProfileInFamilyRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> ProfileResponse:
    try:
        prof, _mem = await svc.create_profile(family_id, user.id, body)
        return ProfileResponse.from_entity(prof)
    except Exception as e:
        _handle_family_error(e)
        raise


@router.get("/{family_id}/profiles", response_model=list[ProfileResponse])
async def list_profiles(
    family_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> list[ProfileResponse]:
    try:
        profiles = await svc.list_profiles(family_id, user.id)
        return [ProfileResponse.from_entity(p) for p in profiles]
    except Exception as e:
        _handle_family_error(e)
        raise


@router.get("/{family_id}/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    family_id: UUID,
    profile_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> ProfileResponse:
    try:
        p = await svc.get_profile(family_id, profile_id, user.id)
        return ProfileResponse.from_entity(p)
    except Exception as e:
        _handle_family_error(e)
        raise


@router.patch("/{family_id}/profiles/{profile_id}", response_model=ProfileResponse)
async def patch_profile(
    family_id: UUID,
    profile_id: UUID,
    body: PatchProfileRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> ProfileResponse:
    try:
        p = await svc.patch_profile(family_id, profile_id, user.id, body)
        return ProfileResponse.from_entity(p)
    except Exception as e:
        _handle_family_error(e)
        raise


@router.delete("/{family_id}/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    family_id: UUID,
    profile_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> None:
    try:
        await svc.delete_profile(family_id, profile_id, user.id)
    except Exception as e:
        _handle_family_error(e)
        raise


@router.patch("/{family_id}/profiles/{profile_id}/link", response_model=ProfileResponse)
async def link_profile(
    family_id: UUID,
    profile_id: UUID,
    body: LinkProfileRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> ProfileResponse:
    try:
        p = await svc.link_profile(family_id, profile_id, user.id, body.user_id)
        return ProfileResponse.from_entity(p)
    except Exception as e:
        _handle_family_error(e)
        raise


@router.get("/{family_id}/profiles/{profile_id}/health", response_model=HealthDetailResponse)
async def get_health(
    family_id: UUID,
    profile_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> HealthDetailResponse:
    try:
        h = await svc.get_health(family_id, profile_id, user.id)
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
    except Exception as e:
        _handle_family_error(e)
        raise


@router.patch("/{family_id}/profiles/{profile_id}/health", response_model=HealthDetailResponse)
async def patch_health(
    family_id: UUID,
    profile_id: UUID,
    body: PatchHealthDetailRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> HealthDetailResponse:
    try:
        h = await svc.patch_health(family_id, profile_id, user.id, body)
        return HealthDetailResponse.from_entity(h)
    except Exception as e:
        _handle_family_error(e)
        raise

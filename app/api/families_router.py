from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.dependencies import get_current_user, get_families_service
from app.application.dtos.family_dto import (
    CreateFamilyRequest,
    CreateFamilyResponse,
    CreateProfileInFamilyRequest,
    FamilyResponse,
    FamilySummaryResponse,
    HealthDetailResponse,
    JoinFamilyRequest,
    InvitePreviewResponse,
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
_INVITE_PREVIEW_RATE_WINDOW_SECONDS = 60
_INVITE_PREVIEW_RATE_LIMIT = 30
_invite_preview_hits: dict[str, list[float]] = {}


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


def _enforce_invite_preview_rate_limit(client_ip: str) -> None:
    now = time.time()
    window_start = now - _INVITE_PREVIEW_RATE_WINDOW_SECONDS
    hits = _invite_preview_hits.get(client_ip, [])
    hits = [ts for ts in hits if ts >= window_start]
    if len(hits) >= _INVITE_PREVIEW_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many preview requests, try again later",
        )
    hits.append(now)
    _invite_preview_hits[client_ip] = hits


@router.post(
    "",
    response_model=CreateFamilyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create family",
    description="Create a family and owner membership/profile",
)
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


@router.get(
    "/invite/preview",
    response_model=InvitePreviewResponse,
    summary="Preview invite code",
    description="Public preview for deep-link/QR invite code before login",
)
async def preview_invite(
    request: Request,
    invite_code: str = Query(..., min_length=1, max_length=64),
    svc: FamiliesService = Depends(get_families_service),
) -> InvitePreviewResponse:
    client_ip = request.client.host if request.client else "unknown"
    _enforce_invite_preview_rate_limit(client_ip)
    try:
        fam = await svc.preview_invite(invite_code)
        return InvitePreviewResponse(family_name=fam.family_name, invite_code=fam.invite_code)
    except Exception as e:
        _handle_family_error(e)
        raise


@router.get("", response_model=list[FamilySummaryResponse], summary="List my families", description="List families the current user belongs to")
async def list_families(
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> list[FamilySummaryResponse]:
    families = await svc.list_my_families(user.id)
    return [FamilySummaryResponse.from_entity(f) for f in families]


@router.post(
    "/join",
    status_code=status.HTTP_200_OK,
    summary="Join family by invite code",
    description="Join using invite_code from manual input, deep-link, or QR payload",
)
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


@router.get("/{family_id}", response_model=FamilyResponse, summary="Get family", description="Get family details if current user is in scope")
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


@router.patch("/{family_id}", response_model=FamilyResponse, summary="Update family", description="Update family name (OWNER/ADMIN)")
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


@router.post(
    "/{family_id}/invite/rotate",
    response_model=FamilyResponse,
    summary="Rotate invite code",
    description="Rotate family invite code (OWNER only)",
)
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


@router.get(
    "/{family_id}/members",
    response_model=list[MembershipResponse],
    summary="List family members",
    description="List memberships and linked profile information in a family",
)
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


@router.patch(
    "/{family_id}/members/{membership_id}",
    response_model=MembershipResponse,
    summary="Update member role",
    description="Update membership role (OWNER only)",
)
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


@router.delete(
    "/{family_id}/members/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove member",
    description="Remove a membership from family",
)
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
    summary="Create profile in family",
    description="Create a profile and membership in the family (OWNER/ADMIN)",
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


@router.get(
    "/{family_id}/profiles",
    response_model=list[ProfileResponse],
    summary="List family profiles",
    description="List profiles in a family; MEMBER only sees self-linked profiles",
)
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


@router.get(
    "/{family_id}/profiles/{profile_id}",
    response_model=ProfileResponse,
    summary="Get profile",
    description="Get a profile in family scope with role-based visibility",
)
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


@router.patch(
    "/{family_id}/profiles/{profile_id}",
    response_model=ProfileResponse,
    summary="Patch profile",
    description="Patch profile fields; MEMBER can patch only self-linked profile",
)
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


@router.delete(
    "/{family_id}/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete profile",
    description="Soft-delete profile and clean memberships (OWNER/ADMIN)",
)
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


@router.patch(
    "/{family_id}/profiles/{profile_id}/link",
    response_model=ProfileResponse,
    summary="Link profile to user",
    description="Link a virtual profile to a user (OWNER/ADMIN)",
)
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


@router.get(
    "/{family_id}/profiles/{profile_id}/health",
    response_model=HealthDetailResponse,
    summary="Get profile health details",
    description="Read health details; MEMBER can read only self-linked profile",
)
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


@router.patch(
    "/{family_id}/profiles/{profile_id}/health",
    response_model=HealthDetailResponse,
    summary="Patch profile health details",
    description="Upsert health details (OWNER/ADMIN)",
)
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

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_families_service
from app.application.dtos.family_dto import MembershipResponse, PatchMembershipRoleRequest
from app.application.family_errors import ConflictError, ForbiddenError, NotFoundError
from app.application.usecases.family_usecases import FamiliesService
from app.domain.entities.user import User

router = APIRouter(prefix="/family-memberships", tags=["family-memberships"])


def _handle_error(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message or "Not found") from exc
    if isinstance(exc, ForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message or "Forbidden") from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message or "Conflict") from exc


@router.patch("/{membership_id}", response_model=MembershipResponse)
async def patch_member_role(
    membership_id: UUID,
    body: PatchMembershipRoleRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> MembershipResponse:
    try:
        m = await svc.patch_membership_role(membership_id, user.id, body)
        return MembershipResponse.from_entity(m)
    except Exception as exc:
        _handle_error(exc)
        raise


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    membership_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> None:
    try:
        await svc.delete_membership(membership_id, user.id)
    except Exception as exc:
        _handle_error(exc)
        raise

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_current_user,
    get_families_service,
    get_medicine_inventory_service,
)
from app.application.dtos.medicine_dto import (
    CreateMedicineInventoryRequest,
    MedicineInventoryResponse,
)
from app.application.dtos.family_dto import (
    CreateFamilyRequest,
    CreateProfileInFamilyRequest,
    FamilyContractResponse,
    FamilyInviteInboxResponse,
    FamilyInviteListRequest,
    FamilyInviteResponse,
    FamilyMemberResponse,
    InviteActionResponse,
    InviteByPhoneRequest,
    InviteByPhoneResponse,
    JoinFamilyRequest,
    PatchFamilyRequest,
    ProfileResponse,
    UserSearchByPhoneResponse,
)
from app.application.family_errors import ConflictError, ForbiddenError, NotFoundError
from app.application.usecases.family_usecases import FamiliesService
from app.application.usecases.medicine_inventory_usecases import MedicineInventoryService
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


async def _build_family_contract(
    *,
    svc: FamiliesService,
    family_id: UUID,
    user_id: UUID,
    include_invites: bool = False,
) -> FamilyContractResponse:
    family = await svc.get_family(family_id, user_id)
    member_rows = await svc.list_member_details(family_id, user_id)
    members = [
        FamilyMemberResponse.from_entities(
            membership=membership,
            profile=profile,
            health=health,
            current_user_id=user_id,
        )
        for membership, profile, health in member_rows
    ]
    invites = None
    if include_invites:
        invite_rows = await svc.get_family_invites(family_id, user_id)
        invites = [FamilyInviteResponse.from_entity(invite) for invite in invite_rows]
    return FamilyContractResponse.from_parts(
        family=family,
        members=members,
        invites=invites,
    )


@router.post("", response_model=FamilyContractResponse, status_code=status.HTTP_201_CREATED)
async def create_family(
    body: CreateFamilyRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> FamilyContractResponse:
    try:
        fam, prof, mem = await svc.create_family(user.id, body)
        return FamilyContractResponse.from_parts(
            family=fam,
            members=[
                FamilyMemberResponse.from_entities(
                    membership=mem,
                    profile=prof,
                    health=None,
                    current_user_id=user.id,
                )
            ],
            invites=[],
        )
    except Exception as e:
        _handle_family_error(e)
        raise


@router.get("", response_model=list[FamilyContractResponse])
async def list_families(
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> list[FamilyContractResponse]:
    families = await svc.list_my_families(user.id)
    out: list[FamilyContractResponse] = []
    for family in families:
        out.append(
            await _build_family_contract(
                svc=svc,
                family_id=family.id,
                user_id=user.id,
                include_invites=False,
            )
        )
    return out


@router.get("/invites", response_model=list[FamilyInviteInboxResponse])
async def list_my_family_invites(
    query: FamilyInviteListRequest = Depends(),
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> list[FamilyInviteInboxResponse]:
    try:
        rows = await svc.list_invites_for_user(user.id, query)
        return [FamilyInviteInboxResponse.from_entity(row) for row in rows]
    except Exception as e:
        _handle_family_error(e)
        raise


@router.post("/join", status_code=status.HTTP_200_OK)
async def join_family(
    body: JoinFamilyRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> dict | InviteActionResponse:
    try:
        payload = await svc.join_family(user.id, body)
        if payload.get("mode") == "invite_action":
            return InviteActionResponse(
                success=bool(payload.get("success")),
                invite_id=UUID(str(payload.get("invite_id"))),
                status=str(payload.get("status")),
                family_member_id=UUID(str(payload["family_member_id"])) if payload.get("family_member_id") else None,
            )
        return payload
    except Exception as e:
        _handle_family_error(e)
        raise


@router.post("/{family_id}/invite-by-phone", response_model=InviteByPhoneResponse)
async def invite_member_by_phone(
    family_id: UUID,
    body: InviteByPhoneRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> InviteByPhoneResponse:
    try:
        payload = await svc.invite_member_by_phone(family_id, user.id, body)
        if payload["dry_run"]:
            if not payload["found"]:
                return InviteByPhoneResponse(dry_run=True, found=False, user=None, invite=None)
            return InviteByPhoneResponse(
                dry_run=True,
                found=True,
                user=UserSearchByPhoneResponse(**payload["user"]),
                invite=None,
            )
        return InviteByPhoneResponse(
            dry_run=False,
            found=None,
            user=None,
            invite=FamilyInviteResponse.from_entity(payload["invite"]),
        )
    except Exception as e:
        _handle_family_error(e)
        raise


@router.get("/{family_id}", response_model=FamilyContractResponse)
async def get_family(
    family_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> FamilyContractResponse:
    try:
        return await _build_family_contract(
            svc=svc,
            family_id=family_id,
            user_id=user.id,
            include_invites=True,
        )
    except Exception as e:
        _handle_family_error(e)
        raise


@router.patch("/{family_id}", response_model=FamilyContractResponse)
async def patch_family(
    family_id: UUID,
    body: PatchFamilyRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> FamilyContractResponse:
    try:
        await svc.patch_family(family_id, user.id, body)
        return await _build_family_contract(
            svc=svc,
            family_id=family_id,
            user_id=user.id,
            include_invites=True,
        )
    except Exception as e:
        _handle_family_error(e)
        raise


@router.post("/{family_id}/invite/rotate", response_model=FamilyContractResponse)
async def rotate_invite(
    family_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> FamilyContractResponse:
    try:
        await svc.rotate_invite(family_id, user.id)
        return await _build_family_contract(
            svc=svc,
            family_id=family_id,
            user_id=user.id,
            include_invites=True,
        )
    except Exception as e:
        _handle_family_error(e)
        raise


@router.get("/{family_id}/members", response_model=list[FamilyMemberResponse])
async def list_members(
    family_id: UUID,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> list[FamilyMemberResponse]:
    try:
        rows = await svc.list_member_details(family_id, user.id)
        return [
            FamilyMemberResponse.from_entities(
                membership=m,
                profile=p,
                health=h,
                current_user_id=user.id,
            )
            for m, p, h in rows
        ]
    except Exception as e:
        _handle_family_error(e)
        raise


@router.post(
    "/{family_id}/profiles",
    response_model=FamilyMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile_in_family(
    family_id: UUID,
    body: CreateProfileInFamilyRequest,
    user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> FamilyMemberResponse:
    try:
        prof, mem = await svc.create_profile(family_id, user.id, body)
        health = await svc.get_health_by_profile_id(prof.id, user.id)
        return FamilyMemberResponse.from_entities(
            membership=mem,
            profile=prof,
            health=health,
            current_user_id=user.id,
        )
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

# --- Medicine inventory (US1 / FR-001, FR-002, FR-010) ---


@router.get(
    "/{family_id}/medicine-inventory",
    response_model=list[MedicineInventoryResponse],
    summary="List medicine inventory",
)
async def list_medicine_inventory(
    family_id: UUID,
    alert: str | None = None,
    user: User = Depends(get_current_user),
    svc: MedicineInventoryService = Depends(get_medicine_inventory_service),
) -> list[MedicineInventoryResponse]:
    if alert is not None and alert not in ("low_stock", "expiring"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query 'alert' must be 'low_stock' or 'expiring' if provided",
        )
    try:
        return await svc.list_items(family_id, user.id, alert=alert)
    except Exception as e:
        _handle_family_error(e)
        raise


@router.post(
    "/{family_id}/medicine-inventory",
    response_model=MedicineInventoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add medicine to family inventory",
)
async def create_medicine_inventory(
    family_id: UUID,
    body: CreateMedicineInventoryRequest,
    user: User = Depends(get_current_user),
    svc: MedicineInventoryService = Depends(get_medicine_inventory_service),
) -> MedicineInventoryResponse:
    try:
        return await svc.create_item(family_id, user.id, body)
    except Exception as e:
        _handle_family_error(e)
        raise

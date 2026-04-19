from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.user_dto import (
    PatchUserMeRequest,
    UpdateUserRequest,
    UserMeHealthProfileResponse,
    UserMeProfileBundleResponse,
    UserMeProfileSummaryResponse,
    UserMeResponse,
    UserMeSummaryResponse,
    UserResponse,
)
from app.application.dtos.family_dto import CreatePersonalProfileRequest, ProfileResponse
from app.application.family_errors import ConflictError
from app.application.usecases.user_usecases import (
    DeleteUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    UpdateUserUseCase,
)
from app.infrastructure.config.database.postgres.connection import get_session
from app.infrastructure.repositories.user_repository_pg import UserRepositoryPG
from app.api.dependencies import (
    get_access_control_service,
    get_appointment_reminder_read_service,
    get_current_user,
    get_families_service,
    get_medical_records_service,
    get_medicine_inventory_service,
    get_vaccination_service,
)
from app.application.usecases.access_control_usecases import AccessControlService
from app.application.usecases.appointment_reminder_read_usecases import AppointmentReminderReadService
from app.application.usecases.family_usecases import FamiliesService
from app.application.usecases.medical_records_usecases import MedicalRecordsService
from app.application.usecases.medicine_inventory_usecases import MedicineInventoryService
from app.application.usecases.vaccination_usecases import VaccinationService
from app.domain.entities.user import User

router = APIRouter(prefix="/users", tags=["users"])


def get_user_repository(session: AsyncSession = Depends(get_session)) -> UserRepositoryPG:
    return UserRepositoryPG(session)


@router.get("", response_model=list[UserResponse])
async def list_users(
    repository: UserRepositoryPG = Depends(get_user_repository),
) -> list[UserResponse]:
    users = await ListUsersUseCase(repository).execute()
    return [UserResponse.from_entity(user) for user in users]


@router.get(
    "/me/profiles",
    response_model=list[ProfileResponse],
    summary="List my linked profiles",
    description="List profiles linked to the authenticated user with optional scope filter",
)
async def list_my_profiles(
    profile_scope: Literal["all", "without_family", "with_family"] = Query(
        "all",
        description="all | without_family (chưa có membership) | with_family (đã thuộc ít nhất một gia đình)",
    ),
    current_user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> list[ProfileResponse]:
    """Các profile có `linked_user_id` = user hiện tại; lọc theo đã/chưa gia đình."""
    profiles = await svc.list_my_linked_profiles(current_user.id, profile_scope=profile_scope)
    return [ProfileResponse.from_entity(p) for p in profiles]


@router.post(
    "/me/personal-profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create my personal profile",
    description="Create a PERSONAL profile for the authenticated user without creating membership",
)
async def create_my_personal_profile(
    body: CreatePersonalProfileRequest,
    current_user: User = Depends(get_current_user),
    svc: FamiliesService = Depends(get_families_service),
) -> ProfileResponse:
    try:
        profile = await svc.create_my_personal_profile(current_user.id, body)
        return ProfileResponse.from_entity(profile)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message or "Conflict") from exc
    except (IntegrityError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/me/summary",
    response_model=UserMeSummaryResponse,
    summary="Get current user — lightweight (profiles + families only)",
    description=(
        "Dùng khi cần nhanh: `user` + mỗi profile liên kết + `family_ids`. "
        "Không tải medical_records, vaccinations, medicine, appointment_reminders, health. "
        "Sau đó FE có thể gọi `GET /users/me` để bundle đầy đủ."
    ),
)
async def get_current_user_profile_summary(
    current_user: User = Depends(get_current_user),
    repository: UserRepositoryPG = Depends(get_user_repository),
    access: AccessControlService = Depends(get_access_control_service),
    families: FamiliesService = Depends(get_families_service),
) -> UserMeSummaryResponse:
    try:
        user = await GetUserUseCase(repository).execute(current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    user_resp = UserResponse.from_entity(user)
    profile_entities = await families.list_my_linked_profiles(current_user.id, profile_scope="all")
    if not profile_entities:
        return UserMeSummaryResponse(user=user_resp, profiles=[], profile=None, health_profile=None)

    summaries: list[UserMeProfileSummaryResponse] = []
    for profile_ent in profile_entities:
        await access.require_profile_read(profile_ent.id, current_user.id)
        profile_resp = ProfileResponse.from_entity(profile_ent)
        family_ids = await families.list_family_ids_for_profile(profile_ent.id)
        summaries.append(
            UserMeProfileSummaryResponse(
                profile=profile_resp,
                family_ids=family_ids,
                family_count=len(family_ids),
            )
        )

    return UserMeSummaryResponse(
        user=user_resp,
        profiles=summaries,
        profile=summaries[0].profile,
        health_profile=None,
    )


@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Get current user bundle (cache Home / Health)",
    description=(
        "Trả `user`, `profile` (personal profile nếu có), và `health_profile`: "
        "chi tiết sức khỏe + `medical_records` + `vaccinations` (kèm `doses`) + "
        "`medicine_inventory` (kèm `medicine_reminder` nếu có) + `appointment_reminders`. "
        "Khi chưa có personal profile: `profile` và `health_profile` là null."
    ),
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    repository: UserRepositoryPG = Depends(get_user_repository),
    access: AccessControlService = Depends(get_access_control_service),
    families: FamiliesService = Depends(get_families_service),
    medical: MedicalRecordsService = Depends(get_medical_records_service),
    vaccination: VaccinationService = Depends(get_vaccination_service),
    medicine_inventory: MedicineInventoryService = Depends(get_medicine_inventory_service),
    appointment_reminders: AppointmentReminderReadService = Depends(get_appointment_reminder_read_service),
) -> UserMeResponse:
    try:
        user = await GetUserUseCase(repository).execute(current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    user_resp = UserResponse.from_entity(user)
    profile_entities = await families.list_my_linked_profiles(current_user.id, profile_scope="all")
    if not profile_entities:
        return UserMeResponse(user=user_resp, profiles=[], profile=None, health_profile=None)

    for profile_ent in profile_entities:
        await access.require_profile_read(profile_ent.id, current_user.id)

    profile_ids = [p.id for p in profile_entities]
    records_by_profile = await medical.list_records_for_profiles(
        profile_ids, current_user.id, skip_access_check=True
    )

    bundles: list[UserMeProfileBundleResponse] = []
    for profile_ent in profile_entities:
        profile_resp = ProfileResponse.from_entity(profile_ent)
        records = records_by_profile.get(profile_ent.id, [])
        vaccs = await vaccination.list_profile_vaccinations_with_doses(
            profile_ent.id, current_user.id, skip_access_check=True
        )
        health_ent = await families.get_health_by_profile_id(
            profile_ent.id, current_user.id, skip_access_check=True
        )
        family_ids = await families.list_family_ids_for_profile(profile_ent.id)
        medicine_items = await medicine_inventory.list_for_profile_with_reminders(
            profile_ent.id, current_user.id, skip_access_check=True
        )
        appt_items = await appointment_reminders.list_for_profile(
            profile_ent.id, current_user.id, skip_access_check=True
        )
        health_bundle = UserMeHealthProfileResponse.from_parts(
            profile_id=profile_ent.id,
            health=health_ent,
            medical_records=records,
            vaccinations=vaccs,
            medicine_inventory=medicine_items,
            appointment_reminders=appt_items,
        )
        bundles.append(
            UserMeProfileBundleResponse(
                profile=profile_resp,
                health_profile=health_bundle,
                family_ids=family_ids,
                family_count=len(family_ids),
            )
        )

    return UserMeResponse(
        user=user_resp,
        profiles=bundles,
        profile=bundles[0].profile,
        health_profile=bundles[0].health_profile,
    )


@router.patch("/me", response_model=UserResponse, summary="Update current user (e.g. phone_number)")
async def patch_current_user_me(
    body: PatchUserMeRequest,
    current_user: User = Depends(get_current_user),
    repository: UserRepositoryPG = Depends(get_user_repository),
) -> UserResponse:
    try:
        user = await GetUserUseCase(repository).execute(current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    patch = body.model_dump(exclude_unset=True)
    if "phone_number" in patch:
        user.phone_number = patch["phone_number"]
    updated = await repository.update(user)
    return UserResponse.from_entity(updated)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    repository: UserRepositoryPG = Depends(get_user_repository),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's data")
    try:
        user = await GetUserUseCase(repository).execute(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UserResponse.from_entity(user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update a user by id if requester is the same user",
)
async def update_user(
    user_id: UUID,
    payload: UpdateUserRequest,
    repository: UserRepositoryPG = Depends(get_user_repository),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user's data")
    try:
        user = await UpdateUserUseCase(repository).execute(user_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UserResponse.from_entity(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete a user by id if requester is the same user",
)
async def delete_user(
    user_id: UUID,
    repository: UserRepositoryPG = Depends(get_user_repository),
    current_user: User = Depends(get_current_user),
) -> Response:
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this user")
    try:
        await DeleteUserUseCase(repository).execute(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

"""Medical record routes with flat item endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status

from app.api.dependencies import get_current_user, get_medical_records_service
from app.application.dtos.medical_dto import (
    AttachmentUrlOnlyRequest,
    CreateMedicalRecordRequest,
    MedicalAttachmentResponse,
    MedicalRecordResponse,
    PatchMedicalRecordRequest,
)
from app.application.family_errors import ForbiddenError, NotFoundError
from app.application.usecases.medical_records_usecases import MedicalRecordsService
from app.domain.entities.user import User

router = APIRouter(tags=["medical-records"])


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
    "/profiles/{profile_id}/medical-records",
    response_model=list[MedicalRecordResponse],
    summary="List medical records for profile",
)
async def list_medical_records(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    svc: MedicalRecordsService = Depends(get_medical_records_service),
) -> list[MedicalRecordResponse]:
    try:
        return await svc.list_records(profile_id, user.id)
    except ForbiddenError as exc:
        raise _fb(exc) from exc
    except NotFoundError as exc:
        raise _nf(exc) from exc


@router.post(
    "/profiles/{profile_id}/medical-records",
    response_model=MedicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create medical record",
)
async def create_medical_record(
    profile_id: UUID,
    body: CreateMedicalRecordRequest,
    user: User = Depends(get_current_user),
    svc: MedicalRecordsService = Depends(get_medical_records_service),
) -> MedicalRecordResponse:
    try:
        return await svc.create_record(profile_id, user.id, body)
    except ForbiddenError as exc:
        raise _fb(exc) from exc
    except NotFoundError as exc:
        raise _nf(exc) from exc


@router.get(
    "/medical-records/{record_id}",
    response_model=MedicalRecordResponse,
    summary="Get one medical record",
)
async def get_medical_record(
    record_id: UUID,
    user: User = Depends(get_current_user),
    svc: MedicalRecordsService = Depends(get_medical_records_service),
) -> MedicalRecordResponse:
    try:
        return await svc.get_record_by_id(record_id, user.id)
    except ForbiddenError as exc:
        raise _fb(exc) from exc
    except NotFoundError as exc:
        raise _nf(exc) from exc


@router.patch(
    "/medical-records/{record_id}",
    response_model=MedicalRecordResponse,
    summary="Update one medical record",
)
async def patch_medical_record(
    record_id: UUID,
    body: PatchMedicalRecordRequest,
    user: User = Depends(get_current_user),
    svc: MedicalRecordsService = Depends(get_medical_records_service),
) -> MedicalRecordResponse:
    try:
        return await svc.patch_record_by_id(record_id, user.id, body)
    except ForbiddenError as exc:
        raise _fb(exc) from exc
    except NotFoundError as exc:
        raise _nf(exc) from exc


@router.delete(
    "/medical-records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete record (hard=true for OWNER/ADMIN purge)",
)
async def delete_medical_record(
    record_id: UUID,
    hard: bool = False,
    user: User = Depends(get_current_user),
    svc: MedicalRecordsService = Depends(get_medical_records_service),
) -> None:
    try:
        await svc.delete_record_by_id(record_id, user.id, hard=hard)
    except ForbiddenError as exc:
        raise _fb(exc) from exc
    except NotFoundError as exc:
        raise _nf(exc) from exc


@router.get(
    "/medical-records/{record_id}/attachments",
    response_model=list[MedicalAttachmentResponse],
    summary="List attachments of a medical record",
)
async def list_attachments(
    record_id: UUID,
    user: User = Depends(get_current_user),
    svc: MedicalRecordsService = Depends(get_medical_records_service),
) -> list[MedicalAttachmentResponse]:
    try:
        return await svc.list_attachments_by_record_id(record_id, user.id)
    except ForbiddenError as exc:
        raise _fb(exc) from exc
    except NotFoundError as exc:
        raise _nf(exc) from exc


@router.post(
    "/medical-records/{record_id}/attachments",
    response_model=MedicalAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add attachment (multipart file) or JSON metadata+URL",
)
async def add_attachment(
    record_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    svc: MedicalRecordsService = Depends(get_medical_records_service),
) -> MedicalAttachmentResponse:
    content_type = (request.headers.get("content-type") or "").lower()
    try:
        if "application/json" in content_type:
            body = AttachmentUrlOnlyRequest.model_validate(await request.json())
            return await svc.add_attachment_url_only_by_record_id(record_id, user.id, body)
        if "multipart/form-data" in content_type:
            form = await request.form()
            uploaded = form.get("file")
            if uploaded is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Multipart form must include a 'file' field",
                )
            if not isinstance(uploaded, UploadFile):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file upload",
                )
            return await svc.add_attachment_multipart_by_record_id(record_id, user.id, uploaded)
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Use application/json or multipart/form-data",
        )
    except ForbiddenError as exc:
        raise _fb(exc) from exc
    except NotFoundError as exc:
        raise _nf(exc) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/medical-attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one attachment and its server file if present",
)
async def delete_attachment(
    attachment_id: UUID,
    user: User = Depends(get_current_user),
    svc: MedicalRecordsService = Depends(get_medical_records_service),
) -> None:
    try:
        await svc.delete_attachment_by_id(attachment_id, user.id)
    except ForbiddenError as exc:
        raise _fb(exc) from exc
    except NotFoundError as exc:
        raise _nf(exc) from exc

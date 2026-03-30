"""Serve medical attachment bytes (FR-007) — auth required."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.dependencies import get_current_user, get_medical_records_service
from app.application.family_errors import ForbiddenError, NotFoundError
from app.application.usecases.medical_records_usecases import MedicalRecordsService
from app.domain.entities.user import User

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/medical/{attachment_id}", summary="Download server-stored medical attachment")
async def download_medical_file(
    attachment_id: UUID,
    user: User = Depends(get_current_user),
    svc: MedicalRecordsService = Depends(get_medical_records_service),
) -> FileResponse:
    try:
        a, path = await svc.resolve_file_for_download(attachment_id, user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message or "Not found") from e
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message or "Forbidden") from e
    return FileResponse(
        path,
        media_type=a.file_type,
        filename=a.file_name,
    )

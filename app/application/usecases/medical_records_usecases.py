from __future__ import annotations

import uuid
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from app.application.ports.medical_record_port import MedicalRecordRepositoryPort
from app.application.dtos.medical_dto import (
    AttachmentUrlOnlyRequest,
    CreateMedicalRecordRequest,
    MedicalAttachmentResponse,
    MedicalRecordResponse,
    PatchMedicalRecordRequest,
)
from app.application.family_errors import NotFoundError
from app.application.usecases.access_control_usecases import AccessControlService
from app.core.config import Settings
from app.domain.entities.medical_record import MedicalRecord, MedicalRecordAttachment

FILE_SERVE_PREFIX = "/files/medical"


def disk_path_for_attachment(upload_root: Path, attachment_id: UUID, original_file_name: str) -> Path:
    ext = Path(original_file_name).suffix[:32] or ".bin"
    return upload_root / f"{attachment_id}{ext}"


def is_server_stored_file_url(file_url: str) -> bool:
    return file_url.startswith(f"{FILE_SERVE_PREFIX}/")


class MedicalRecordsService:
    def __init__(
        self,
        medical: MedicalRecordRepositoryPort,
        access: AccessControlService,
        settings: Settings,
    ) -> None:
        self._medical = medical
        self._access = access
        self._settings = settings

    def _to_record_response(self, m: MedicalRecord) -> MedicalRecordResponse:
        return MedicalRecordResponse(
            id=m.id,
            profile_id=m.profile_id,
            created_by=m.created_by,
            title=m.title,
            diagnosis_name=m.diagnosis_name,
            diagnosis_slug=m.diagnosis_slug,
            doctor_name=m.doctor_name,
            hospital_name=m.hospital_name,
            visit_date=m.visit_date,
            specialty=m.specialty,
            symptoms=m.symptoms,
            test_results=m.test_results,
            doctor_advice=m.doctor_advice,
            notes=m.notes,
            created_at=m.created_at,
            updated_at=m.updated_at,
            deleted_at=m.deleted_at,
        )

    def _to_attachment_response(self, m: MedicalRecordAttachment) -> MedicalAttachmentResponse:
        return MedicalAttachmentResponse(
            id=m.id,
            medical_record_id=m.medical_record_id,
            file_name=m.file_name,
            file_type=m.file_type,
            file_url=m.file_url,
        )

    async def list_records(self, profile_id: UUID, user_id: UUID) -> list[MedicalRecordResponse]:
        await self._access.require_medical_profile_view(profile_id, user_id)
        rows = await self._medical.list_records_for_profile(profile_id)
        return [self._to_record_response(m) for m in rows]

    async def create_record(
        self,
        profile_id: UUID,
        user_id: UUID,
        body: CreateMedicalRecordRequest,
    ) -> MedicalRecordResponse:
        await self._access.require_medical_profile_write(profile_id, user_id)
        m = await self._medical.create_record(
            profile_id=profile_id,
            created_by=user_id,
            title=body.title,
            diagnosis_name=body.diagnosis_name,
            diagnosis_slug=body.diagnosis_slug,
            doctor_name=body.doctor_name,
            hospital_name=body.hospital_name,
            visit_date=body.visit_date,
            specialty=body.specialty,
            symptoms=body.symptoms,
            test_results=body.test_results,
            doctor_advice=body.doctor_advice,
            notes=body.notes,
        )
        return self._to_record_response(m)

    async def get_record(
        self,
        profile_id: UUID,
        record_id: UUID,
        user_id: UUID,
    ) -> MedicalRecordResponse:
        context = await self._access.require_medical_record_view(record_id, user_id)
        if context.record.profile_id != profile_id:
            raise NotFoundError("Medical record not found")
        return self._to_record_response(context.record)

    async def get_record_by_id(
        self,
        record_id: UUID,
        user_id: UUID,
    ) -> MedicalRecordResponse:
        context = await self._access.require_medical_record_view(record_id, user_id)
        return self._to_record_response(context.record)

    async def patch_record(
        self,
        profile_id: UUID,
        record_id: UUID,
        user_id: UUID,
        body: PatchMedicalRecordRequest,
    ) -> MedicalRecordResponse:
        context = await self._access.require_medical_record_write(record_id, user_id)
        if context.record.profile_id != profile_id:
            raise NotFoundError("Medical record not found")
        patch = body.model_dump(exclude_unset=True)
        m = await self._medical.apply_patch(record_id, patch)
        if m is None:
            raise NotFoundError("Medical record not found")
        return self._to_record_response(m)

    async def patch_record_by_id(
        self,
        record_id: UUID,
        user_id: UUID,
        body: PatchMedicalRecordRequest,
    ) -> MedicalRecordResponse:
        await self._access.require_medical_record_write(record_id, user_id)
        m = await self._medical.apply_patch(record_id, body.model_dump(exclude_unset=True))
        if m is None or m.deleted_at is not None:
            raise NotFoundError("Medical record not found")
        return self._to_record_response(m)

    async def delete_record(
        self,
        profile_id: UUID,
        record_id: UUID,
        user_id: UUID,
        *,
        hard: bool,
    ) -> None:
        if hard:
            context = await self._access.require_medical_record_hard_delete(record_id, user_id)
        else:
            context = await self._access.require_medical_record_write(record_id, user_id, include_deleted=True)
        if context.record.profile_id != profile_id:
            raise NotFoundError("Medical record not found")

        if hard:
            atts = await self._medical.list_attachments(record_id)
            root = self._settings.resolved_medical_upload_path()
            for a in atts:
                if is_server_stored_file_url(a.file_url):
                    p = disk_path_for_attachment(root, a.id, a.file_name)
                    if p.is_file():
                        p.unlink()
            await self._medical.hard_delete_record(record_id)
        else:
            if context.record.deleted_at is not None:
                raise NotFoundError("Medical record not found")
            await self._medical.soft_delete_record(record_id)

    async def delete_record_by_id(
        self,
        record_id: UUID,
        user_id: UUID,
        *,
        hard: bool,
    ) -> None:
        if hard:
            context = await self._access.require_medical_record_hard_delete(record_id, user_id)
        else:
            context = await self._access.require_medical_record_write(record_id, user_id, include_deleted=True)
            if context.record.deleted_at is not None:
                raise NotFoundError("Medical record not found")
        if hard:
            atts = await self._medical.list_attachments(record_id)
            root = self._settings.resolved_medical_upload_path()
            for a in atts:
                if is_server_stored_file_url(a.file_url):
                    p = disk_path_for_attachment(root, a.id, a.file_name)
                    if p.is_file():
                        p.unlink()
            await self._medical.hard_delete_record(record_id)
        else:
            await self._medical.soft_delete_record(record_id)

    async def list_attachments(
        self,
        profile_id: UUID,
        record_id: UUID,
        user_id: UUID,
    ) -> list[MedicalAttachmentResponse]:
        context = await self._access.require_medical_record_view(record_id, user_id)
        if context.record.profile_id != profile_id:
            raise NotFoundError("Medical record not found")
        rows = await self._medical.list_attachments(record_id)
        return [self._to_attachment_response(x) for x in rows]

    async def list_attachments_by_record_id(
        self,
        record_id: UUID,
        user_id: UUID,
    ) -> list[MedicalAttachmentResponse]:
        await self._access.require_medical_record_view(record_id, user_id)
        rows = await self._medical.list_attachments(record_id)
        return [self._to_attachment_response(x) for x in rows]

    async def add_attachment_multipart(
        self,
        profile_id: UUID,
        record_id: UUID,
        user_id: UUID,
        upload: UploadFile,
    ) -> MedicalAttachmentResponse:
        context = await self._access.require_medical_record_write(record_id, user_id)
        if context.record.profile_id != profile_id:
            raise NotFoundError("Medical record not found")

        max_mb = self._settings.medical_upload_max_mb
        max_bytes = (max_mb * 1024 * 1024) if max_mb is not None else None
        raw = await upload.read()
        if max_bytes is not None and len(raw) > max_bytes:
            raise ValueError(f"File exceeds maximum size ({max_mb} MB)")

        attachment_id = uuid.uuid4()
        safe_name = Path(upload.filename or "upload").name[:512] or "file.bin"
        file_type = upload.content_type or "application/octet-stream"
        root = self._settings.resolved_medical_upload_path()
        root.mkdir(parents=True, exist_ok=True)
        dest = disk_path_for_attachment(root, attachment_id, safe_name)
        dest.write_bytes(raw)

        file_url = f"{FILE_SERVE_PREFIX}/{attachment_id}"
        a = await self._medical.create_attachment(
            attachment_id=attachment_id,
            medical_record_id=record_id,
            file_name=safe_name,
            file_type=file_type[:128],
            file_url=file_url,
        )
        return self._to_attachment_response(a)

    async def add_attachment_multipart_by_record_id(
        self,
        record_id: UUID,
        user_id: UUID,
        upload: UploadFile,
    ) -> MedicalAttachmentResponse:
        await self._access.require_medical_record_write(record_id, user_id)

        max_mb = self._settings.medical_upload_max_mb
        max_bytes = (max_mb * 1024 * 1024) if max_mb is not None else None
        raw = await upload.read()
        if max_bytes is not None and len(raw) > max_bytes:
            raise ValueError(f"File exceeds maximum size ({max_mb} MB)")

        attachment_id = uuid.uuid4()
        safe_name = Path(upload.filename or "upload").name[:512] or "file.bin"
        file_type = upload.content_type or "application/octet-stream"
        root = self._settings.resolved_medical_upload_path()
        root.mkdir(parents=True, exist_ok=True)
        dest = disk_path_for_attachment(root, attachment_id, safe_name)
        dest.write_bytes(raw)

        file_url = f"{FILE_SERVE_PREFIX}/{attachment_id}"
        a = await self._medical.create_attachment(
            attachment_id=attachment_id,
            medical_record_id=record_id,
            file_name=safe_name,
            file_type=file_type[:128],
            file_url=file_url,
        )
        return self._to_attachment_response(a)

    async def add_attachment_url_only(
        self,
        profile_id: UUID,
        record_id: UUID,
        user_id: UUID,
        body: AttachmentUrlOnlyRequest,
    ) -> MedicalAttachmentResponse:
        context = await self._access.require_medical_record_write(record_id, user_id)
        if context.record.profile_id != profile_id:
            raise NotFoundError("Medical record not found")

        attachment_id = uuid.uuid4()
        a = await self._medical.create_attachment(
            attachment_id=attachment_id,
            medical_record_id=record_id,
            file_name=body.file_name[:512],
            file_type=body.file_type[:128],
            file_url=body.file_url[:8192],
        )
        return self._to_attachment_response(a)

    async def add_attachment_url_only_by_record_id(
        self,
        record_id: UUID,
        user_id: UUID,
        body: AttachmentUrlOnlyRequest,
    ) -> MedicalAttachmentResponse:
        await self._access.require_medical_record_write(record_id, user_id)

        attachment_id = uuid.uuid4()
        a = await self._medical.create_attachment(
            attachment_id=attachment_id,
            medical_record_id=record_id,
            file_name=body.file_name[:512],
            file_type=body.file_type[:128],
            file_url=body.file_url[:8192],
        )
        return self._to_attachment_response(a)

    async def delete_attachment(
        self,
        profile_id: UUID,
        record_id: UUID,
        attachment_id: UUID,
        user_id: UUID,
    ) -> None:
        context = await self._access.require_attachment_write(attachment_id, user_id)
        if context.record.profile_id != profile_id or context.attachment.medical_record_id != record_id:
            raise NotFoundError("Attachment not found")
        if is_server_stored_file_url(context.attachment.file_url):
            root = self._settings.resolved_medical_upload_path()
            p = disk_path_for_attachment(root, context.attachment.id, context.attachment.file_name)
            if p.is_file():
                p.unlink()
        await self._medical.delete_attachment(attachment_id)

    async def delete_attachment_by_id(
        self,
        attachment_id: UUID,
        user_id: UUID,
    ) -> None:
        context = await self._access.require_attachment_write(attachment_id, user_id)
        if is_server_stored_file_url(context.attachment.file_url):
            root = self._settings.resolved_medical_upload_path()
            p = disk_path_for_attachment(root, context.attachment.id, context.attachment.file_name)
            if p.is_file():
                p.unlink()
        await self._medical.delete_attachment(attachment_id)

    async def resolve_file_for_download(
        self,
        attachment_id: UUID,
        user_id: UUID,
    ) -> tuple[MedicalRecordAttachment, Path]:
        context = await self._access.require_attachment_view(attachment_id, user_id)
        a = context.attachment
        if not is_server_stored_file_url(a.file_url):
            raise NotFoundError("File not found")
        root = self._settings.resolved_medical_upload_path()
        path = disk_path_for_attachment(root, a.id, a.file_name)
        if not path.is_file():
            raise NotFoundError("File not found")
        return a, path

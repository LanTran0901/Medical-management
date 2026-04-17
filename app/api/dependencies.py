from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.security import decode_token
from app.domain.entities.family import FamilyMembership, FamilyRole
from app.domain.entities.user import User
from app.infrastructure.config.database.postgres.connection import get_session
from app.infrastructure.repositories.user_repository_pg import UserRepositoryPG
from app.infrastructure.repositories.family_repository_pg import FamilyRepositoryPG
from app.infrastructure.repositories.access_control_pg import AccessControlPG
from app.infrastructure.repositories.medical_record_repository_pg import MedicalRecordRepositoryPG
from app.infrastructure.repositories.medicine_inventory_repository_pg import (
    MedicineInventoryRepositoryPG,
)
from app.infrastructure.repositories.vaccination_repository_pg import VaccinationRepositoryPG
from app.infrastructure.repositories.family_medicine_inventory_repository_pg import FamilyMedicineInventoryRepositoryPG
from app.infrastructure.repositories.appointment_reminder_repository_pg import AppointmentReminderRepositoryPG
from app.application.usecases.family_usecases import FamiliesService
from app.application.usecases.access_control_usecases import AccessControlService
from app.application.usecases.appointment_reminder_read_usecases import AppointmentReminderReadService
from app.application.usecases.medical_records_usecases import MedicalRecordsService
from app.application.usecases.medicine_inventory_usecases import MedicineInventoryService
from app.application.usecases.medicine_schedule_usecases import MedicineScheduleService
from app.application.usecases.vaccination_usecases import VaccinationService
from app.application.usecases.appointment_reminder_usecases import AppointmentReminderService
from app.application.usecases.family_medicine_inventory_usecases import FamilyMedicineInventoryService
from app.core.config import settings as app_settings
from app.infrastructure.repositories.medical_dictionary_repository import MedicalDictionaryRepository
from app.application.usecases.medical_dictionary_usecases import MedicalDictionaryService
from app.application.usecases.rag_usecases import MedicalRagService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login/swagger")

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    session: AsyncSession = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    user_repo = UserRepositoryPG(session)
    user = await user_repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user


def get_families_service(
    session: AsyncSession = Depends(get_session),
) -> FamiliesService:
    return FamiliesService(
        FamilyRepositoryPG(session),
        UserRepositoryPG(session),
        AccessControlService(AccessControlPG(session)),
    )


async def get_family_membership(
    family_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FamilyMembership:
    """Current user must be a linked member of the family (403 if not)."""
    repo = FamilyRepositoryPG(session)
    m = await repo.get_user_membership_in_family(family_id, user.id)
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this family",
        )
    return m


async def require_medicine_inventory_editor(
    family_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FamilyMembership:
    """OWNER/ADMIN for medicine CRUD; 422 if user has no families; 403 MEMBER or non-member."""
    repo = FamilyRepositoryPG(session)
    families = await repo.list_families_for_user(user.id)
    if not families:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Create a family before managing medicine inventory.",
        )
    m = await repo.get_user_membership_in_family(family_id, user.id)
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this family",
        )
    if m.role == FamilyRole.MEMBER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Members may only view medicine inventory",
        )
    return m


def get_medicine_inventory_service(
    session: AsyncSession = Depends(get_session),
) -> MedicineInventoryService:
    return MedicineInventoryService(
        MedicineInventoryRepositoryPG(session),
        AccessControlService(AccessControlPG(session)),
        FamilyRepositoryPG(session),
    )


def get_family_medicine_inventory_service(
    session: AsyncSession = Depends(get_session),
) -> FamilyMedicineInventoryService:
    return FamilyMedicineInventoryService(
        FamilyMedicineInventoryRepositoryPG(session),
        AccessControlService(AccessControlPG(session)),
    )


def get_medicine_schedule_service(
    session: AsyncSession = Depends(get_session),
) -> MedicineScheduleService:
    return MedicineScheduleService(
        session,
        AccessControlService(AccessControlPG(session)),
    )


def get_appointment_reminder_read_service(
    session: AsyncSession = Depends(get_session),
) -> AppointmentReminderReadService:
    return AppointmentReminderReadService(
        AppointmentReminderRepositoryPG(session),
        AccessControlService(AccessControlPG(session)),
    )


def get_medical_records_service(
    session: AsyncSession = Depends(get_session),
) -> MedicalRecordsService:
    return MedicalRecordsService(
        MedicalRecordRepositoryPG(session),
        AccessControlService(AccessControlPG(session)),
        app_settings,
    )


def get_vaccination_service(
    session: AsyncSession = Depends(get_session),
) -> VaccinationService:
    return VaccinationService(
        VaccinationRepositoryPG(session),
        AccessControlService(AccessControlPG(session)),
    )


def get_appointment_reminder_service(
    session: AsyncSession = Depends(get_session),
) -> AppointmentReminderService:
    return AppointmentReminderService(
        session,
        AccessControlService(AccessControlPG(session)),
    )


def get_medical_dictionary_service(
    session: AsyncSession = Depends(get_session),
) -> MedicalDictionaryService:
    return MedicalDictionaryService(MedicalDictionaryRepository(session))


def get_rag_service(
    session: AsyncSession = Depends(get_session),
) -> MedicalRagService:
    return MedicalRagService(MedicalDictionaryRepository(session))

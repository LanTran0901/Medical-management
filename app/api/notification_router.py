from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.notification_dto import (
    SendNotificationRequest,
    SendNotificationToDeviceRequest,
    NotificationResponse,
)
from app.application.usecases.notification_usecases import (
    SendNotificationToUserUseCase,
    SendNotificationToDeviceUseCase,
)
from app.infrastructure.config.database.postgres.connection import get_session
from app.infrastructure.repositories.auth_repository_pg import AuthRepositoryPG
from app.infrastructure.services.fcm_service import FCMService
from app.api.dependencies import get_current_user
from app.domain.entities.user import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_auth_repository(session: AsyncSession = Depends(get_session)) -> AuthRepositoryPG:
    return AuthRepositoryPG(session)


def get_fcm_service() -> FCMService:
    return FCMService()


@router.post("/send", response_model=NotificationResponse)
async def send_notification_to_user(
    payload: SendNotificationRequest,
    current_user: User = Depends(get_current_user),
    auth_repo: AuthRepositoryPG = Depends(get_auth_repository),
    fcm_service: FCMService = Depends(get_fcm_service),
) -> NotificationResponse:
    """Send push notification to all devices of a user."""
    use_case = SendNotificationToUserUseCase(auth_repo, fcm_service)
    return await use_case.execute(payload)


@router.post("/send-device", response_model=NotificationResponse)
async def send_notification_to_device(
    payload: SendNotificationToDeviceRequest,
    current_user: User = Depends(get_current_user),
    fcm_service: FCMService = Depends(get_fcm_service),
) -> NotificationResponse:
    """Send push notification to a specific device by FCM token."""
    use_case = SendNotificationToDeviceUseCase(fcm_service)
    return await use_case.execute(payload)

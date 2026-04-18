"""Push and in-app notifications.

Manual E2E (scheduled MEDICINE FCM): run `alembic upgrade head`, ensure an ACTIVE
`schedules` row with `remind_time` matching the current UTC minute, FCM tokens on
`user_devices`, and `FIREBASE_CREDENTIALS_PATH` set. Either set
`SCHEDULE_DISPATCH_ENABLED=true` or call `POST /notifications/dispatch/schedules`
with header `X-Internal-Secret` matching `INTERNAL_DISPATCH_SECRET`. Tap the
push or use `POST /notifications/me/schedules/{schedule_id}/compliance`.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.notification_dto import (
    SendNotificationRequest,
    SendNotificationToDeviceRequest,
    NotificationResponse,
    NotificationsListResponse,
    ScheduleComplianceRequest,
    ScheduleComplianceResponse,
    ScheduleSnoozeRequest,
    ScheduleSnoozeResponse,
    ScheduleDispatchResponse,
)
from app.application.usecases.notification_usecases import (
    SendNotificationToUserUseCase,
    SendNotificationToDeviceUseCase,
    ListNotificationsUseCase,
)
from app.application.usecases.schedule_push_usecases import (
    LogScheduleComplianceUseCase,
    SnoozeScheduleUseCase,
    ProcessDueSchedulePushesUseCase,
)
from app.application.usecases.appointment_reminder_push_usecases import (
    ProcessDueAppointmentReminderPushesUseCase,
)
from app.core.config import settings
from app.infrastructure.config.database.postgres.connection import (
    AsyncSessionLocal,
    get_session,
)
from app.infrastructure.repositories.auth_repository_pg import AuthRepositoryPG
from app.infrastructure.services.hybrid_notification_service import HybridNotificationService
from app.api.dependencies import get_current_user
from app.domain.entities.user import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_auth_repository(session: AsyncSession = Depends(get_session)) -> AuthRepositoryPG:
    return AuthRepositoryPG(session)


def get_push_service() -> HybridNotificationService:
    return HybridNotificationService()


@router.post("/send", response_model=NotificationResponse)
async def send_notification_to_user(
    payload: SendNotificationRequest,
    current_user: User = Depends(get_current_user),
    auth_repo: AuthRepositoryPG = Depends(get_auth_repository),
    push_service: HybridNotificationService = Depends(get_push_service),
) -> NotificationResponse:
    """Send push notification to all devices of a user."""
    use_case = SendNotificationToUserUseCase(auth_repo, push_service)
    return await use_case.execute(payload, current_user.id)


@router.post("/send-device", response_model=NotificationResponse)
async def send_notification_to_device(
    payload: SendNotificationToDeviceRequest,
    current_user: User = Depends(get_current_user),
    auth_repo: AuthRepositoryPG = Depends(get_auth_repository),
    push_service: HybridNotificationService = Depends(get_push_service),
) -> NotificationResponse:
    """Send push notification to a specific device token (FCM or Expo; must belong to caller)."""
    use_case = SendNotificationToDeviceUseCase(auth_repo, push_service)
    try:
        return await use_case.execute(payload, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
    ) from e


@router.get("/me", response_model=NotificationsListResponse)
async def list_my_notifications(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NotificationsListResponse:
    use_case = ListNotificationsUseCase(session)
    return await use_case.execute(current_user.id)


@router.post(
    "/me/schedules/{schedule_id}/compliance",
    response_model=ScheduleComplianceResponse,
)
async def log_schedule_compliance(
    schedule_id: UUID,
    payload: ScheduleComplianceRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ScheduleComplianceResponse:
    use_case = LogScheduleComplianceUseCase(session)
    return await use_case.execute(current_user.id, schedule_id, payload)


@router.post(
    "/me/schedules/{schedule_id}/snooze",
    response_model=ScheduleSnoozeResponse,
)
async def snooze_schedule(
    schedule_id: UUID,
    payload: ScheduleSnoozeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ScheduleSnoozeResponse:
    use_case = SnoozeScheduleUseCase(session)
    return await use_case.execute(current_user.id, schedule_id, payload)


@router.post("/dispatch/schedules", response_model=ScheduleDispatchResponse)
async def dispatch_schedule_pushes(
    x_internal_secret: str | None = Header(None, alias="X-Internal-Secret"),
) -> ScheduleDispatchResponse:
    """Manual or cron trigger: send due MEDICINE schedule FCMs. Requires INTERNAL_DISPATCH_SECRET."""
    if not settings.internal_dispatch_secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not x_internal_secret or x_internal_secret != settings.internal_dispatch_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    async with AsyncSessionLocal() as session:
        try:
            push = HybridNotificationService()
            med = ProcessDueSchedulePushesUseCase(session, push)
            appt = ProcessDueAppointmentReminderPushesUseCase(session, push)
            r1 = await med.execute()
            r2 = await appt.execute()
            await session.commit()
            return ScheduleDispatchResponse(
                processed=r1.processed + r2.processed,
                sent=r1.sent + r2.sent,
                skipped_duplicate=r1.skipped_duplicate + r2.skipped_duplicate,
                errors=r1.errors + r2.errors,
            )
        except Exception:
            await session.rollback()
            raise

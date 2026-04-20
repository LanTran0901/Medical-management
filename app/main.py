import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.api.health_router import router as health_router
from app.api.user_router import router as user_router
from app.api.auth_router import router as auth_router
from app.api.notification_router import router as notification_router
from app.api.appointment_reminders_router import router as appointment_reminders_router
from app.api.families_router import router as families_router
from app.api.family_memberships_router import router as family_memberships_router
from app.api.medicine_inventory_router import router as medicine_inventory_router
from app.api.profile_router import router as profile_router
from app.api.medical_router import router as medical_router
from app.api.vaccination_router import router as vaccination_router
from app.api.files_router import router as files_router
from app.api.medical_dictionary_router import router as medical_dictionary_router
from app.api.health_metric_readings_router import router as health_metric_readings_router
from app.routes.rag import router as rag_router
from app.core.config import settings
from app.infrastructure.config.database.mongodb.connection import (
    close_mongo_connection,
    connect_to_mongo,
)
from app.infrastructure.config.database.postgres.connection import engine

logger = logging.getLogger(__name__)


def _skip_mongo_lifespan() -> bool:
    """Set SKIP_MONGO_LIFESPAN=1 for integration tests that only need PostgreSQL."""
    return os.getenv("SKIP_MONGO_LIFESPAN", "").lower() in ("1", "true", "yes")


def _should_run_schedule_dispatch() -> bool:
    if not settings.schedule_dispatch_enabled:
        return False
    if settings.firebase_credentials_path:
        return True
    if settings.expo_push_enabled:
        return True
    return False


def _is_transient_db_disconnect(exc: Exception) -> bool:
    if isinstance(exc, DBAPIError):
        if exc.connection_invalidated:
            return True
        origin = exc.orig
        if origin is not None:
            msg = str(origin).lower()
            if (
                "connection was closed in the middle of operation" in msg
                or "connection does not exist" in msg
                or "server closed the connection unexpectedly" in msg
            ):
                return True
    msg = str(exc).lower()
    return "connection was closed in the middle of operation" in msg


async def _schedule_dispatch_loop() -> None:
    """Background poll for due MEDICINE schedules + appointment reminders; push via FCM/Expo."""
    from app.application.usecases.appointment_reminder_push_usecases import (
        ProcessDueAppointmentReminderPushesUseCase,
    )
    from app.application.usecases.schedule_push_usecases import (
        ProcessDueSchedulePushesUseCase,
    )
    from app.infrastructure.config.database.postgres.connection import AsyncSessionLocal
    from app.infrastructure.services.hybrid_notification_service import HybridNotificationService

    interval = settings.schedule_dispatch_interval_seconds
    while True:
        await asyncio.sleep(interval)
        if not settings.schedule_dispatch_enabled:
            continue
        if not settings.firebase_credentials_path and not settings.expo_push_enabled:
            continue
        attempts = 2
        for attempt in range(1, attempts + 1):
            try:
                async with AsyncSessionLocal() as session:
                    try:
                        push = HybridNotificationService()
                        med = ProcessDueSchedulePushesUseCase(session, push)
                        appt = ProcessDueAppointmentReminderPushesUseCase(session, push)
                        r1 = await med.execute()
                        r2 = await appt.execute()
                        await session.commit()
                        logger.info("Schedule dispatch: med=%s appt=%s", r1, r2)
                    except Exception:
                        try:
                            await session.rollback()
                        except Exception:
                            logger.exception("Schedule dispatch rollback failed")
                        raise
                break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                is_retryable = _is_transient_db_disconnect(exc) and attempt < attempts
                if is_retryable:
                    logger.warning(
                        "Schedule dispatch hit transient DB disconnect (attempt %s/%s); retrying.",
                        attempt,
                        attempts,
                    )
                    await asyncio.sleep(1)
                    continue
                logger.exception("Schedule dispatch iteration failed")
                break


@asynccontextmanager
async def lifespan(_: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    # 1. MongoDB (optional — skipped when e.g. pytest only exercises Postgres)
    if not _skip_mongo_lifespan():
        await connect_to_mongo()

    # 2. PostgreSQL — verify connectivity (engine is lazy; force a real ping)
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

    # 3. Firebase Admin SDK (optional — only if credentials path is configured)
    if settings.firebase_credentials_path:
        import firebase_admin
        from firebase_admin import credentials as fb_credentials
        if not firebase_admin._apps:
            cred = fb_credentials.Certificate(settings.firebase_credentials_path)
            firebase_admin.initialize_app(cred)

    dispatch_task: asyncio.Task | None = None
    if _should_run_schedule_dispatch():
        dispatch_task = asyncio.create_task(_schedule_dispatch_loop())

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    if dispatch_task is not None:
        dispatch_task.cancel()
        try:
            await dispatch_task
        except asyncio.CancelledError:
            pass
    if not _skip_mongo_lifespan():
        await close_mongo_connection()
    await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(families_router)
app.include_router(family_memberships_router)
app.include_router(medicine_inventory_router)
app.include_router(profile_router)
app.include_router(medical_router)
app.include_router(vaccination_router)
app.include_router(appointment_reminders_router)
app.include_router(files_router)
app.include_router(medical_dictionary_router)
app.include_router(health_metric_readings_router)
app.include_router(notification_router)
app.include_router(rag_router)


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"message": f"Welcome to {settings.app_name}"}


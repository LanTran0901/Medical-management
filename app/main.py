import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.health_router import router as health_router
from app.api.user_router import router as user_router
from app.api.auth_router import router as auth_router
from app.api.notification_router import router as notification_router
from app.api.families_router import router as families_router
from app.api.family_memberships_router import router as family_memberships_router
from app.api.medicine_inventory_router import router as medicine_inventory_router
from app.api.profile_router import router as profile_router
from app.api.medical_router import router as medical_router
from app.api.vaccination_router import router as vaccination_router
from app.api.files_router import router as files_router
from app.api.medical_dictionary_router import router as medical_dictionary_router
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


async def _schedule_dispatch_loop() -> None:
    """Background poll for due MEDICINE schedules and send FCM (optional)."""
    from app.application.usecases.schedule_push_usecases import (
        ProcessDueSchedulePushesUseCase,
    )
    from app.infrastructure.config.database.postgres.connection import AsyncSessionLocal
    from app.infrastructure.services.fcm_service import FCMService

    interval = settings.schedule_dispatch_interval_seconds
    while True:
        await asyncio.sleep(interval)
        if not settings.schedule_dispatch_enabled:
            continue
        if not settings.firebase_credentials_path:
            continue
        try:
            async with AsyncSessionLocal() as session:
                try:
                    uc = ProcessDueSchedulePushesUseCase(session, FCMService())
                    result = await uc.execute()
                    await session.commit()
                    logger.info("Schedule dispatch: %s", result)
                except Exception:
                    await session.rollback()
                    raise
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Schedule dispatch iteration failed")


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
    if settings.schedule_dispatch_enabled and settings.firebase_credentials_path:
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
app.include_router(files_router)
app.include_router(medical_dictionary_router)
app.include_router(notification_router)
app.include_router(rag_router)


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"message": f"Welcome to {settings.app_name}"}


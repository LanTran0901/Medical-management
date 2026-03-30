import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
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
from app.routes.rag import router as rag_router
from app.core.config import settings
from app.infrastructure.config.database.mongodb.connection import (
    close_mongo_connection,
    connect_to_mongo,
)
from app.infrastructure.config.database.postgres.connection import engine


def _skip_mongo_lifespan() -> bool:
    """Set SKIP_MONGO_LIFESPAN=1 for integration tests that only need PostgreSQL."""
    return os.getenv("SKIP_MONGO_LIFESPAN", "").lower() in ("1", "true", "yes")


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

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    if not _skip_mongo_lifespan():
        await close_mongo_connection()
    await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
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
app.include_router(notification_router)
app.include_router(rag_router)


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"message": f"Welcome to {settings.app_name}"}

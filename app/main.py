from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.health_router import router as health_router
from app.api.user_router import router as user_router
from app.routes.health import router as health_router
from app.routes.rag import router as rag_router
from app.core.config import settings
from app.infrastructure.config.database.mongodb.connection import (
    close_mongo_connection,
    connect_to_mongo,
)
from app.infrastructure.config.database.postgres.connection import engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    # 1. MongoDB
    await connect_to_mongo()

    # 2. PostgreSQL — verify connectivity (engine is lazy; force a real ping)
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    await close_mongo_connection()
    await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(health_router)
app.include_router(user_router)
app.include_router(rag_router)


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"message": f"Welcome to {settings.app_name}"}


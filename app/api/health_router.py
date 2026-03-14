from fastapi import APIRouter
from sqlalchemy import text

from app.infrastructure.config.database.mongodb import connection as mongo_conn
from app.infrastructure.config.database.postgres.connection import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    mongo_status = "connected" if mongo_conn.db is not None else "disconnected"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        postgres_status = "connected"
    except Exception:
        postgres_status = "disconnected"

    return {
        "status": "ok",
        "mongodb": mongo_status,
        "postgres": postgres_status,
    }

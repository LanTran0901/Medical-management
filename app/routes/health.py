from fastapi import APIRouter

from app.db.mongodb import db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    mongo_status = "connected" if db is not None else "disconnected"
    return {"status": "ok", "mongodb": mongo_status}

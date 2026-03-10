from fastapi import APIRouter

from app.db import mongodb

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    mongo_status = "connected" if mongodb.db is not None else "disconnected"
    return {"status": "ok", "mongodb": mongo_status}

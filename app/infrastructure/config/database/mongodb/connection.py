from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    global client, db
    client = AsyncIOMotorClient(settings.resolved_mongodb_uri)
    db = client[settings.resolved_mongodb_db_name]
    # Verify connection (raises ServerSelectionTimeoutError if unreachable)
    await client.admin.command("ping")


async def close_mongo_connection() -> None:
    global client, db
    if client is not None:
        client.close()
    client = None
    db = None

"""Seed an auth session for liturgy testing."""
import asyncio
import os
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient

ADMIN_TOKEN = "test_liturgy_admin_001"
ADMIN_USER_ID = "user_ade7a898e281"
ADMIN_EMAIL = "philipwils13@gmail.com"

FREE_TOKEN = "test_liturgy_free_001"
FREE_USER_ID = "user_test_liturgy_free"
FREE_EMAIL = "free.liturgy.tester@example.com"


async def main():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    expires = datetime.now(timezone.utc) + timedelta(hours=4)

    # Admin
    await db.users.update_one(
        {"user_id": ADMIN_USER_ID},
        {"$setOnInsert": {"user_id": ADMIN_USER_ID, "email": ADMIN_EMAIL, "name": "Admin"}},
        upsert=True,
    )
    await db.user_sessions.update_one(
        {"session_token": ADMIN_TOKEN},
        {"$set": {"session_token": ADMIN_TOKEN, "user_id": ADMIN_USER_ID, "expires_at": expires}},
        upsert=True,
    )

    # Free user
    await db.users.update_one(
        {"user_id": FREE_USER_ID},
        {"$setOnInsert": {"user_id": FREE_USER_ID, "email": FREE_EMAIL, "name": "FreeTester"}},
        upsert=True,
    )
    await db.user_sessions.update_one(
        {"session_token": FREE_TOKEN},
        {"$set": {"session_token": FREE_TOKEN, "user_id": FREE_USER_ID, "expires_at": expires}},
        upsert=True,
    )

    print(f"OK admin={ADMIN_TOKEN} free={FREE_TOKEN} expires={expires.isoformat()}")
    client.close()


if __name__ == "__main__":
    # Load env from /app/backend/.env
    from pathlib import Path
    env_file = Path("/app/backend/.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v.strip().strip('"'))
    asyncio.run(main())

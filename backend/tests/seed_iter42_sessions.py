"""Seed Mongo sessions for iter42 (Liturgy daytime + Virtus) testing."""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

cli = MongoClient(os.environ["MONGO_URL"])
db = cli[os.environ["DB_NAME"]]

now = datetime.now(timezone.utc)
exp = now + timedelta(hours=12)

# Admin/Premium user (already exists per credentials doc)
admin_user_id = "user_ade7a898e281"
admin_email = "philipwils13@gmail.com"
db.users.update_one(
    {"user_id": admin_user_id},
    {"$setOnInsert": {"user_id": admin_user_id, "email": admin_email,
                      "name": "Philip Wils", "picture": None,
                      "created_at": now}},
    upsert=True,
)
admin_token = "test_liturgy_probe_001"
db.user_sessions.update_one(
    {"session_token": admin_token},
    {"$set": {"session_token": admin_token, "user_id": admin_user_id,
              "created_at": now, "expires_at": exp}},
    upsert=True,
)

# FREE user
free_user_id = "user_virtus_free"
free_email = "free_virtus@test.com"
db.users.update_one(
    {"user_id": free_user_id},
    {"$set": {"user_id": free_user_id, "email": free_email,
              "name": "Free Virtus", "picture": None,
              "created_at": now}},
    upsert=True,
)
free_token = "test_virtus_free_001"
db.user_sessions.update_one(
    {"session_token": free_token},
    {"$set": {"session_token": free_token, "user_id": free_user_id,
              "created_at": now, "expires_at": exp}},
    upsert=True,
)

print(f"ADMIN  token={admin_token}  user={admin_user_id}  expires={exp.isoformat()}")
print(f"FREE   token={free_token}  user={free_user_id}  expires={exp.isoformat()}")
cli.close()

"""Seed an authenticated user session in MongoDB for Iter 11 UI testing."""
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

USER_ID = "ui_test_user_1"
TOKEN = "TEST_FE_ITER11_TOKEN"

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

db.users.update_one(
    {"user_id": USER_ID},
    {"$set": {
        "user_id": USER_ID,
        "email": "ui_test_user_1@example.com",
        "name": "UI Test User 1",
        "picture": "",
    }},
    upsert=True,
)

db.user_sessions.update_one(
    {"session_token": TOKEN},
    {"$set": {
        "session_token": TOKEN,
        "user_id": USER_ID,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    }},
    upsert=True,
)

print(f"OK token={TOKEN} user_id={USER_ID}")

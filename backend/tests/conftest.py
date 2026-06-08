"""Shared fixtures for Sanctus backend tests."""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or "http://localhost:8001"
).rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

TEST_USER_ID = "test_user_1"
TEST_EMAIL = "test@sanctus.app"
TEST_TOKEN = "test_token_abc"


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def mongo_db():
    cli = MongoClient(MONGO_URL)
    db = cli[DB_NAME]
    yield db
    cli.close()


@pytest.fixture(scope="session")
def seeded_user(mongo_db):
    """Insert a user + session token directly into MongoDB."""
    mongo_db.users.update_one(
        {"user_id": TEST_USER_ID},
        {"$set": {"user_id": TEST_USER_ID, "email": TEST_EMAIL,
                  "name": "Test User", "picture": None,
                  "created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    mongo_db.user_sessions.update_one(
        {"session_token": TEST_TOKEN},
        {"$set": {"session_token": TEST_TOKEN, "user_id": TEST_USER_ID,
                  "created_at": datetime.now(timezone.utc),
                  "expires_at": datetime.now(timezone.utc) + timedelta(days=1)}},
        upsert=True,
    )
    yield {"user_id": TEST_USER_ID, "token": TEST_TOKEN, "email": TEST_EMAIL}
    # Cleanup
    mongo_db.user_sessions.delete_many({"user_id": TEST_USER_ID})
    mongo_db.users.delete_many({"user_id": TEST_USER_ID})
    mongo_db.preferences.delete_many({"user_id": TEST_USER_ID})
    mongo_db.meals.delete_many({"user_id": TEST_USER_ID})
    mongo_db.workouts.delete_many({"user_id": TEST_USER_ID})


@pytest.fixture(scope="session")
def auth_client(seeded_user):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {seeded_user['token']}",
    })
    return s


@pytest.fixture(scope="session")
def anon_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s

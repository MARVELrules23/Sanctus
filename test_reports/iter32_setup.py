"""Iteration 32 — Library Phase 1 setup / teardown.

Mints a session token for admin (philipwils13@gmail.com).
"""
import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
cli = MongoClient(os.environ["MONGO_URL"])
db = cli[os.environ["DB_NAME"]]

ADMIN_EMAIL = "philipwils13@gmail.com"
ADMIN_TOKEN = "TEST_iter32_admin_tok"
NON_ADMIN_EMAIL = "TEST_iter32_user@sanctus.app"
NON_ADMIN_USER_ID = "TEST_iter32_user"
NON_ADMIN_TOKEN = "TEST_iter32_user_tok"


def setup():
    now = datetime.now(timezone.utc)
    admin = db.users.find_one({"email": ADMIN_EMAIL})
    if not admin:
        print(f"FATAL: admin {ADMIN_EMAIL} not in users collection")
        sys.exit(2)
    admin_id = admin["user_id"]
    is_admin = bool(admin.get("is_admin"))
    print(f"admin user_id = {admin_id}, is_admin = {is_admin}")

    db.user_sessions.update_one(
        {"session_token": ADMIN_TOKEN},
        {"$set": {"session_token": ADMIN_TOKEN, "user_id": admin_id,
                  "created_at": now,
                  "expires_at": now + timedelta(days=2)}}, upsert=True,
    )
    print(f"admin session token -> {ADMIN_TOKEN}")

    # Non-admin user for 403 testing
    db.users.update_one(
        {"user_id": NON_ADMIN_USER_ID},
        {"$set": {"user_id": NON_ADMIN_USER_ID, "email": NON_ADMIN_EMAIL,
                  "name": "TEST Iter32 User", "picture": None,
                  "is_admin": False, "created_at": now}},
        upsert=True,
    )
    db.user_sessions.update_one(
        {"session_token": NON_ADMIN_TOKEN},
        {"$set": {"session_token": NON_ADMIN_TOKEN, "user_id": NON_ADMIN_USER_ID,
                  "created_at": now,
                  "expires_at": now + timedelta(days=2)}}, upsert=True,
    )
    print(f"non-admin session token -> {NON_ADMIN_TOKEN}")
    print("SETUP_OK")


def teardown():
    admin = db.users.find_one({"email": ADMIN_EMAIL})
    admin_id = admin["user_id"] if admin else None
    db.user_sessions.delete_many({"session_token": {"$in": [ADMIN_TOKEN, NON_ADMIN_TOKEN]}})
    db.users.delete_many({"user_id": NON_ADMIN_USER_ID})
    db.user_sessions.delete_many({"user_id": NON_ADMIN_USER_ID})
    # Remove any test-classic book + progress
    book = db.library_books.find_one({"slug": "test-classic"})
    if book:
        db.library_reading_progress.delete_many({"book_id": book["book_id"]})
        db.library_books.delete_one({"slug": "test-classic"})
        print("deleted leftover test-classic book")
    # Remove admin's reading progress for seeded books (the test exercises practice-presence-of-god)
    if admin_id:
        ppg = db.library_books.find_one({"slug": "practice-presence-of-god"})
        if ppg:
            db.library_reading_progress.delete_many({"user_id": admin_id, "book_id": ppg["book_id"]})
            print(f"cleaned admin progress for practice-presence-of-god")
    # Remove non-admin progress
    db.library_reading_progress.delete_many({"user_id": NON_ADMIN_USER_ID})
    print("TEARDOWN_OK")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "setup"
    if cmd == "setup":
        setup()
    elif cmd == "teardown":
        teardown()
    else:
        print(f"unknown cmd: {cmd}")
        sys.exit(1)

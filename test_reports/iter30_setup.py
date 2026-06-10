"""Iteration 30 — Challenges Phase 2 frontend setup/teardown.

Seeds:
  - Patches hallowtide start/end dates so today (2026-06-10) falls inside window.
  - Snapshots the original to /tmp/iter30_hw_snapshot.json for clean teardown.
  - Creates a TEST friend user enrolled in hallowtide.
  - Adds accepted friendship between admin (philipwils13@gmail.com) and the test friend.
  - Mints a session token for admin = TEST_iter30_admin_tok.

Usage:
  python /app/test_reports/iter30_setup.py setup
  python /app/test_reports/iter30_setup.py teardown
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
cli = MongoClient(os.environ["MONGO_URL"])
db = cli[os.environ["DB_NAME"]]

SNAP_PATH = Path("/tmp/iter30_hw_snapshot.json")

ADMIN_EMAIL = "philipwils13@gmail.com"
ADMIN_TOKEN = "TEST_iter30_admin_tok"

FRIEND_USER_ID = "TEST_iter30_friend"
FRIEND_TOKEN = "TEST_iter30_friend_tok"
FRIEND_EMAIL = "TEST_iter30_friend@sanctus.app"
FRIEND_NAME = "TEST Iter30 Friend"

# Window covers today (server clock is 2026-06-10).
NEW_START = datetime(2026, 6, 5, tzinfo=timezone.utc)
NEW_END = datetime(2026, 6, 20, tzinfo=timezone.utc)


def _fkey(a, b):
    x, y = sorted([a, b])
    return f"{x}__{y}"


def setup():
    now = datetime.now(timezone.utc)
    admin = db.users.find_one({"email": ADMIN_EMAIL})
    if not admin:
        print(f"FATAL: admin {ADMIN_EMAIL} not in users collection")
        sys.exit(2)
    admin_id = admin["user_id"]
    print(f"admin user_id = {admin_id}")

    hw = db.liturgical_challenges.find_one({"slug": "hallowtide"})
    if not hw:
        print("FATAL: hallowtide challenge missing")
        sys.exit(2)
    # Snapshot
    snap = {
        "start_date": hw["start_date"].isoformat(),
        "end_date": hw["end_date"].isoformat(),
        "status": hw.get("status"),
    }
    SNAP_PATH.write_text(json.dumps(snap))
    print(f"snapshot saved: {snap}")
    db.liturgical_challenges.update_one(
        {"slug": "hallowtide"},
        {"$set": {"start_date": NEW_START, "end_date": NEW_END,
                  "status": "published", "updated_at": now}},
    )
    print(f"patched hallowtide dates -> {NEW_START.date()}..{NEW_END.date()}")

    # Mint admin token
    db.user_sessions.update_one(
        {"session_token": ADMIN_TOKEN},
        {"$set": {"session_token": ADMIN_TOKEN, "user_id": admin_id,
                  "created_at": now,
                  "expires_at": now + timedelta(days=2)}}, upsert=True,
    )
    print(f"admin session token -> {ADMIN_TOKEN}")

    # Friend user
    db.users.update_one(
        {"user_id": FRIEND_USER_ID},
        {"$set": {"user_id": FRIEND_USER_ID, "email": FRIEND_EMAIL,
                  "name": FRIEND_NAME, "picture": None,
                  "is_admin": False, "created_at": now}},
        upsert=True,
    )
    db.user_sessions.update_one(
        {"session_token": FRIEND_TOKEN},
        {"$set": {"session_token": FRIEND_TOKEN, "user_id": FRIEND_USER_ID,
                  "created_at": now,
                  "expires_at": now + timedelta(days=2)}}, upsert=True,
    )
    # Accepted friendship admin <-> friend
    db.community_friendships.update_one(
        {"friendship_id": _fkey(admin_id, FRIEND_USER_ID)},
        {"$set": {
            "friendship_id": _fkey(admin_id, FRIEND_USER_ID),
            "members": sorted([admin_id, FRIEND_USER_ID]),
            "status": "accepted",
            "requested_by": admin_id,
            "created_at": now,
            "accepted_at": now,
        }}, upsert=True,
    )
    # Enroll friend in hallowtide (write directly so we don't need API call)
    enr_id = f"enr_TEST_iter30_friend_hallowtide"
    db.challenge_enrollments.update_one(
        {"user_id": FRIEND_USER_ID, "challenge_id": hw["challenge_id"]},
        {"$set": {
            "enrollment_id": enr_id,
            "user_id": FRIEND_USER_ID,
            "challenge_id": hw["challenge_id"],
            "joined_at": now,
            "current_streak": 3,
            "longest_streak": 3,
            "total_days_completed": 3,
        }}, upsert=True,
    )
    print(f"friend {FRIEND_USER_ID} enrolled + friendship with admin = accepted")
    print("SETUP_OK")


def teardown():
    admin = db.users.find_one({"email": ADMIN_EMAIL})
    admin_id = admin["user_id"] if admin else None
    if SNAP_PATH.exists():
        snap = json.loads(SNAP_PATH.read_text())
        db.liturgical_challenges.update_one(
            {"slug": "hallowtide"},
            {"$set": {
                "start_date": datetime.fromisoformat(snap["start_date"]),
                "end_date": datetime.fromisoformat(snap["end_date"]),
                "status": snap["status"],
            }},
        )
        print(f"restored hallowtide -> {snap}")
        SNAP_PATH.unlink()
    db.user_sessions.delete_many({"session_token": {"$in": [ADMIN_TOKEN, FRIEND_TOKEN]}})
    db.user_sessions.delete_many({"user_id": FRIEND_USER_ID})
    if admin_id:
        db.community_friendships.delete_one({"friendship_id": _fkey(admin_id, FRIEND_USER_ID)})
        # Remove any TEST_iter30 posts authored by admin
        db.community_posts.delete_many({
            "author_id": admin_id, "body": {"$regex": "^TEST_iter30"},
        })
    db.challenge_enrollments.delete_many({"user_id": FRIEND_USER_ID})
    db.challenge_checkins.delete_many({"user_id": FRIEND_USER_ID})
    db.users.delete_many({"user_id": FRIEND_USER_ID})
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

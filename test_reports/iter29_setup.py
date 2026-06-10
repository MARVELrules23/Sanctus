"""Setup MongoDB seed data for iteration_29 frontend tests.

- Mint NON-admin, NON-enrolled test user
- Patch hallowtide start/end dates so today (2026-06-10) is inside window
- Snapshot original dates for restoration
"""
import os
import sys
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pathlib import Path
from pymongo import MongoClient

load_dotenv(Path("/app/backend/.env"))
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

USER_ID = "TEST_iter29_user"
EMAIL = "TEST_iter29@sanctus.app"
TOKEN = "TEST_iter29_tok"

cli = MongoClient(MONGO_URL)
db = cli[DB_NAME]

mode = sys.argv[1] if len(sys.argv) > 1 else "setup"

if mode == "setup":
    db.users.update_one(
        {"user_id": USER_ID},
        {"$set": {"user_id": USER_ID, "email": EMAIL, "name": "TEST iter29 user",
                  "is_admin": False, "created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    db.user_sessions.update_one(
        {"session_token": TOKEN},
        {"$set": {"session_token": TOKEN, "user_id": USER_ID,
                  "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
                  "created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    # Make sure user is NOT enrolled in anything
    db.challenge_enrollments.delete_many({"user_id": USER_ID})
    db.challenge_checkins.delete_many({"user_id": USER_ID})

    # Patch hallowtide dates so today is inside the window
    hw = db.liturgical_challenges.find_one({"slug": "hallowtide"})
    if hw:
        snapshot = {"start_date": hw.get("start_date"), "end_date": hw.get("end_date"), "status": hw.get("status")}
        # save snapshot to a file
        with open("/tmp/iter29_hw_snapshot.json", "w") as f:
            f.write(json.dumps({k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in snapshot.items()}))
        # Set 2026-06-05 → 2026-06-20 (15-day window covering today 2026-06-10)
        db.liturgical_challenges.update_one(
            {"slug": "hallowtide"},
            {"$set": {
                "start_date": datetime(2026, 6, 5, tzinfo=timezone.utc),
                "end_date": datetime(2026, 6, 20, tzinfo=timezone.utc),
                "status": "published",
            }},
        )
        print("Patched hallowtide → 2026-06-05 to 2026-06-20, published")
    print(f"User token={TOKEN} ready (non-admin, non-enrolled)")

elif mode == "teardown":
    db.challenge_enrollments.delete_many({"user_id": USER_ID})
    db.challenge_checkins.delete_many({"user_id": USER_ID})
    db.user_sessions.delete_many({"user_id": USER_ID})
    db.users.delete_many({"user_id": USER_ID})
    # Restore hallowtide
    try:
        with open("/tmp/iter29_hw_snapshot.json") as f:
            snap = json.load(f)
        upd = {}
        for k in ("start_date", "end_date"):
            v = snap.get(k)
            if v:
                upd[k] = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if snap.get("status"):
            upd["status"] = snap["status"]
        if upd:
            db.liturgical_challenges.update_one({"slug": "hallowtide"}, {"$set": upd})
        print("Restored hallowtide snapshot")
    except FileNotFoundError:
        print("No snapshot to restore")
    print("Teardown done")

cli.close()

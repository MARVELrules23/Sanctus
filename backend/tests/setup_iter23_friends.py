"""Seed three users + accepted friendships for the frontend group-DM picker."""
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/backend/.env")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

ME = ("ui_iter23_me", "TEST_FE_ITER23_TOKEN", "Maria UI")
F1 = ("ui_iter23_friend_petra", None, "Petra Friend")
F2 = ("ui_iter23_friend_thomas", None, "Thomas Friend")
F3 = ("ui_iter23_friend_agnes", None, "Agnes Friend")

cli = MongoClient(MONGO_URL)
db = cli[DB_NAME]
now = datetime.now(timezone.utc)

for uid, _tok, name in (ME, F1, F2, F3):
    db.users.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid, "email": f"{uid}@example.com",
                  "name": name, "picture": None, "created_at": now}},
        upsert=True,
    )

# Session only for me
db.user_sessions.update_one(
    {"session_token": ME[1]},
    {"$set": {"session_token": ME[1], "user_id": ME[0],
              "expires_at": now + timedelta(days=7)}},
    upsert=True,
)


def fkey(a, b):
    x, y = sorted([a, b])
    return f"{x}__{y}"


# Friendships me <-> each friend (accepted)
for friend in (F1, F2, F3):
    fid = fkey(ME[0], friend[0])
    db.community_friendships.update_one(
        {"friendship_id": fid},
        {"$set": {
            "friendship_id": fid,
            "members": sorted([ME[0], friend[0]]),
            "status": "accepted",
            "requested_by": ME[0],
            "created_at": now,
            "accepted_at": now,
        }},
        upsert=True,
    )

print(f"OK token={ME[1]} user_id={ME[0]} friends={[F1[0],F2[0],F3[0]]}")
cli.close()

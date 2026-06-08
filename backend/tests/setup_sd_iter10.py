"""Setup script for iteration_10 frontend test: mint a user+session token,
ack disclaimer, and reuse or generate a self-defense session.
Prints SESSION_TOKEN, USER_ID, SD_SESSION_ID for the playwright run.
"""
import os, uuid, datetime, json, sys
from pymongo import MongoClient
import requests

MONGO = os.environ.get("MONGO_URL") or "mongodb://localhost:27017"
DB = os.environ.get("DB_NAME") or "sanctus_db"
BASE = "https://faithful-fitness-3.preview.emergentagent.com"

cli = MongoClient(MONGO)
db = cli[DB]

USER_ID = "TEST_FE_iter10_user"
EMAIL = "test_iter10@example.com"
TOKEN = "TEST_FE_ITERATION10_TOKEN"

# Upsert user
db.users.update_one(
    {"user_id": USER_ID},
    {"$set": {"user_id": USER_ID, "email": EMAIL, "name": "Iter10 Tester"}},
    upsert=True,
)
# Upsert session_token
expires = datetime.datetime.utcnow() + datetime.timedelta(days=2)
db.user_sessions.update_one(
    {"session_token": TOKEN},
    {"$set": {"session_token": TOKEN, "user_id": USER_ID, "expires_at": expires}},
    upsert=True,
)

H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# Ack disclaimer
r = requests.post(f"{BASE}/api/self-defense/disclaimer/acknowledge", headers=H, timeout=20)
print("ack:", r.status_code)

# Try to find existing session
r = requests.get(f"{BASE}/api/self-defense/sessions?limit=5", headers=H, timeout=20)
print("list:", r.status_code)
sid = None
if r.status_code == 200:
    items = r.json().get("items") or r.json().get("sessions") or []
    # Filter for boxing if possible
    boxing = [s for s in items if s.get("discipline_id") == "boxing" and not s.get("completed_at")]
    if boxing:
        sid = boxing[0].get("session_id") or boxing[0].get("id")
    elif items:
        s = items[0]
        sid = s.get("session_id") or s.get("id")

if not sid:
    print("Generating new session...")
    body = {
        "discipline_id": "boxing",
        "duration_minutes": 20,
        "equipment": ["bag"],
        "has_partner": False,
        "include_patron_reflection": True,
    }
    r = requests.post(f"{BASE}/api/self-defense/generate", headers=H, json=body, timeout=120)
    print("generate:", r.status_code)
    if r.status_code != 200:
        print(r.text[:500])
        sys.exit(1)
    j = r.json()
    sid = j.get("session_id") or j.get("id") or (j.get("session") or {}).get("session_id")

print(f"USER_ID={USER_ID}")
print(f"TOKEN={TOKEN}")
print(f"SD_SESSION_ID={sid}")

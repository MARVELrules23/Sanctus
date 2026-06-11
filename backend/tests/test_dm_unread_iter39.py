"""
Iteration 39 — DM Unread Count backend tests.

Tests the new endpoint GET /api/community/dm/unread-count plus
regression on previously passing endpoints.
"""
import os
import time
import datetime
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_TOKEN = "tk_admin_31c13434065bc0cd"   # user_ade7a898e281 (admin/premium)
FREE_TOKEN = "tk_free_41bc267f482dd5a3"     # user_test_nonadmin_001
THIRD_TOKEN = "tk_third_test001session"     # user_test_third_001
ADMIN_UID = "user_ade7a898e281"
FREE_UID = "user_test_nonadmin_001"
THIRD_UID = "user_test_third_001"

H_ADMIN = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
H_FREE = {"Authorization": f"Bearer {FREE_TOKEN}"}
H_THIRD = {"Authorization": f"Bearer {THIRD_TOKEN}"}


# ---------- fixtures ----------

@pytest.fixture(scope="session")
def mongo():
    c = MongoClient("mongodb://localhost:27017")
    yield c.sanctus_db
    c.close()


@pytest.fixture(scope="session", autouse=True)
def ensure_sessions(mongo):
    """Make sure all 3 test sessions are alive (refresh expiry)."""
    now = datetime.datetime.utcnow()
    exp = now + datetime.timedelta(hours=4)
    for tok, uid in [
        (ADMIN_TOKEN, ADMIN_UID),
        (FREE_TOKEN, FREE_UID),
        (THIRD_TOKEN, THIRD_UID),
    ]:
        mongo.user_sessions.update_one(
            {"session_token": tok},
            {"$set": {"session_token": tok, "user_id": uid, "expires_at": exp}},
            upsert=True,
        )
    # Ensure third user exists
    if not mongo.users.find_one({"user_id": THIRD_UID}):
        mongo.users.insert_one({
            "user_id": THIRD_UID,
            "email": "third@example.com",
            "name": "Third Test",
            "is_admin": False,
            "created_at": now,
        })
    yield


@pytest.fixture
def cleanup_dms(mongo):
    """Wipe DM threads & messages that include our test users between tests."""
    def _wipe():
        threads = list(mongo.community_dm_threads.find(
            {"member_ids": {"$in": [ADMIN_UID, FREE_UID, THIRD_UID]}},
            {"_id": 0, "thread_id": 1},
        ))
        tids = [t["thread_id"] for t in threads]
        if tids:
            mongo.community_dm_messages.delete_many({"thread_id": {"$in": tids}})
            mongo.community_dm_threads.delete_many({"thread_id": {"$in": tids}})
    _wipe()
    yield
    _wipe()


# ---------- unread-count auth + empty ----------

class TestUnreadCountAuth:
    def test_requires_bearer_token(self):
        r = requests.get(f"{API}/community/dm/unread-count")
        assert r.status_code == 401, r.text

    def test_invalid_token(self):
        r = requests.get(
            f"{API}/community/dm/unread-count",
            headers={"Authorization": "Bearer not_a_real_token_xxx"},
        )
        assert r.status_code == 401

    def test_empty_user_returns_zero(self, cleanup_dms):
        r = requests.get(f"{API}/community/dm/unread-count", headers=H_FREE)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body == {"total": 0, "threads": []}, body


# ---------- end-to-end 1:1 unread ----------

class TestOneOnOneUnreadFlow:
    def test_full_flow(self, cleanup_dms):
        # (a) admin starts thread with FREE user
        r = requests.post(
            f"{API}/community/dm/threads",
            headers=H_ADMIN,
            json={"user_id": FREE_UID},
        )
        assert r.status_code == 200, r.text
        tid = r.json()["thread_id"]
        assert isinstance(tid, str) and len(tid) > 0

        # (b) admin sends 3 messages
        for i in range(3):
            rr = requests.post(
                f"{API}/community/dm/threads/{tid}/messages",
                headers=H_ADMIN,
                json={"body": f"hello {i}"},
            )
            assert rr.status_code == 200, rr.text
            time.sleep(0.05)

        # Sender's own unread stays 0
        r_admin = requests.get(f"{API}/community/dm/unread-count", headers=H_ADMIN)
        assert r_admin.status_code == 200
        assert r_admin.json()["total"] == 0, r_admin.json()

        # (c) FREE user sees total=3 and the thread in threads array
        r_free = requests.get(f"{API}/community/dm/unread-count", headers=H_FREE)
        assert r_free.status_code == 200, r_free.text
        body = r_free.json()
        assert body["total"] == 3, body
        assert any(t["thread_id"] == tid and t["unread"] == 3 for t in body["threads"]), body

        # (d) FREE user opens messages (this marks read)
        r_open = requests.get(
            f"{API}/community/dm/threads/{tid}/messages",
            headers=H_FREE,
        )
        assert r_open.status_code == 200, r_open.text
        # Response shape is {"thread": {...}, "messages": [...]}
        msgs = r_open.json().get("messages", [])
        assert len(msgs) >= 3, r_open.json()

        # Tiny delay so subsequent created_at queries are deterministic
        time.sleep(0.1)

        # (e) FREE user's count drops back to 0
        r_free2 = requests.get(f"{API}/community/dm/unread-count", headers=H_FREE)
        assert r_free2.status_code == 200
        body2 = r_free2.json()
        assert body2["total"] == 0, body2
        assert body2["threads"] == [], body2


# ---------- group DM unread ----------

class TestGroupDMUnread:
    def test_group_flow(self, cleanup_dms, mongo):
        # admin creates group DM with admin + non-admin + third
        payload = {"member_ids": [FREE_UID, THIRD_UID], "name": "TEST_iter39_group"}
        r = requests.post(
            f"{API}/community/dm/threads/group",
            headers=H_ADMIN,
            json=payload,
        )
        # Some servers require different payload shape — try fallback
        if r.status_code == 422:
            payload = {"user_ids": [FREE_UID, THIRD_UID], "name": "TEST_iter39_group"}
            r = requests.post(
                f"{API}/community/dm/threads/group",
                headers=H_ADMIN,
                json=payload,
            )
        assert r.status_code == 200, f"group create failed: {r.status_code} {r.text}"
        tid = r.json()["thread_id"]

        # Verify membership in mongo
        t = mongo.community_dm_threads.find_one({"thread_id": tid}, {"_id": 0})
        assert t is not None
        assert ADMIN_UID in t["member_ids"]
        assert FREE_UID in t["member_ids"]
        assert THIRD_UID in t["member_ids"]

        # Admin sends 2 messages
        for i in range(2):
            rr = requests.post(
                f"{API}/community/dm/threads/{tid}/messages",
                headers=H_ADMIN,
                json={"body": f"group msg {i}"},
            )
            assert rr.status_code == 200, rr.text
            time.sleep(0.05)

        # non-admin sees 2 unread
        r_free = requests.get(f"{API}/community/dm/unread-count", headers=H_FREE)
        assert r_free.status_code == 200
        body = r_free.json()
        assert body["total"] >= 2, body
        assert any(x["thread_id"] == tid and x["unread"] == 2 for x in body["threads"]), body

        # third user also sees 2 unread
        r_third = requests.get(f"{API}/community/dm/unread-count", headers=H_THIRD)
        assert r_third.status_code == 200
        body3 = r_third.json()
        assert any(x["thread_id"] == tid and x["unread"] == 2 for x in body3["threads"]), body3

        # non-admin opens thread (mark read)
        r_open = requests.get(
            f"{API}/community/dm/threads/{tid}/messages",
            headers=H_FREE,
        )
        assert r_open.status_code == 200
        time.sleep(0.1)

        # non-admin drops to 0 for this thread
        r_free2 = requests.get(f"{API}/community/dm/unread-count", headers=H_FREE)
        assert r_free2.status_code == 200
        body_f2 = r_free2.json()
        free_thread_match = [x for x in body_f2["threads"] if x["thread_id"] == tid]
        assert free_thread_match == [], f"thread should be gone from free unread list: {body_f2}"

        # third user STILL has unread=2 for this thread
        r_third2 = requests.get(f"{API}/community/dm/unread-count", headers=H_THIRD)
        assert r_third2.status_code == 200
        body3b = r_third2.json()
        assert any(x["thread_id"] == tid and x["unread"] == 2 for x in body3b["threads"]), body3b


# ---------- regression suite ----------

class TestRegression:
    def test_dm_threads_list(self):
        r = requests.get(f"{API}/community/dm/threads", headers=H_ADMIN)
        assert r.status_code == 200, r.text
        assert "items" in r.json()

    def test_post_dm_thread_create(self, mongo):
        r = requests.post(
            f"{API}/community/dm/threads",
            headers=H_ADMIN,
            json={"user_id": FREE_UID},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "thread_id" in body

    def test_post_and_get_dm_messages(self):
        r = requests.post(
            f"{API}/community/dm/threads",
            headers=H_ADMIN,
            json={"user_id": FREE_UID},
        )
        assert r.status_code == 200
        tid = r.json()["thread_id"]

        rm = requests.post(
            f"{API}/community/dm/threads/{tid}/messages",
            headers=H_ADMIN,
            json={"body": "regression check"},
        )
        assert rm.status_code == 200, rm.text

        rg = requests.get(
            f"{API}/community/dm/threads/{tid}/messages",
            headers=H_FREE,
        )
        assert rg.status_code == 200, rg.text

    def test_subscriptions_status_admin(self):
        r = requests.get(f"{API}/subscriptions/status", headers=H_ADMIN)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("is_premium") is True

    def test_subscriptions_status_free(self):
        r = requests.get(f"{API}/subscriptions/status", headers=H_FREE)
        assert r.status_code == 200, r.text
        assert r.json().get("is_premium") is False

    def test_auth_me_admin(self):
        r = requests.get(f"{API}/auth/me", headers=H_ADMIN)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("user_id") == ADMIN_UID
        assert body.get("email") == "philipwils13@gmail.com"

    def test_auth_me_free(self):
        r = requests.get(f"{API}/auth/me", headers=H_FREE)
        assert r.status_code == 200
        assert r.json().get("user_id") == FREE_UID

    def test_library_books_list(self):
        r = requests.get(f"{API}/library/books", headers=H_FREE)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body or isinstance(body, list)

    def test_library_films_list(self):
        r = requests.get(f"{API}/library/films", headers=H_FREE)
        assert r.status_code == 200, r.text

    def test_humanae_vitae_free_user_200(self):
        r = requests.get(
            f"{API}/library/books/humanae-vitae/chapters/0",
            headers=H_FREE,
        )
        assert r.status_code == 200, r.text

    def test_confessions_free_user_402(self):
        r = requests.get(
            f"{API}/library/books/confessions-augustine/chapters/0",
            headers=H_FREE,
        )
        assert r.status_code == 402, r.text

"""Phase 3 — Community (Parish feed, topical rooms, DMs, reports, blocks) tests.

Covers:
- /api/community/topics
- /api/community/feed
- /api/community/posts (CRUD)
- /api/community/posts/{id}/like
- /api/community/posts/{id}/replies (+ DELETE)
- /api/community/users/search & /users/recommended & /users/{id}
- /api/community/dm/threads (open / list / messages / send / read state)
- /api/community/report
- /api/community/block/{id} (POST/DELETE)
- Block-blocks-DM behaviour
- Regression smoke: /auth/me, /bible/books, /bible/chapter/john/3
"""
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

# User #1 — the existing seeded UI tester
TOKEN_A = "ui_test_token_xyz"
USER_A_ID = "ui_test_user_1"

# User #2 — fresh seeded for Phase 3 (DM + search counterparts)
TOKEN_B = "ui_test_token_phase3_b"
USER_B_ID = "ui_test_user_phase3_b"
USER_B_EMAIL = "phase3b@sanctus.app"

HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}", "Content-Type": "application/json"}
HEADERS_B = {"Authorization": f"Bearer {TOKEN_B}", "Content-Type": "application/json"}


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def db():
    cli = MongoClient(MONGO_URL)
    yield cli[DB_NAME]
    cli.close()


@pytest.fixture(scope="module", autouse=True)
def seed_users(db):
    """Seed user A (already exists) and a second user B + session token."""
    now = datetime.now(timezone.utc)
    # Ensure A exists (existing seed)
    db.users.update_one(
        {"user_id": USER_A_ID},
        {"$setOnInsert": {"user_id": USER_A_ID, "email": "ui_test@sanctus.app",
                          "name": "Brother UI", "picture": None,
                          "created_at": now - timedelta(days=2)}},
        upsert=True,
    )
    db.user_sessions.update_one(
        {"session_token": TOKEN_A},
        {"$set": {"session_token": TOKEN_A, "user_id": USER_A_ID,
                  "created_at": now, "expires_at": now + timedelta(days=7)}},
        upsert=True,
    )
    # Seed B
    db.users.update_one(
        {"user_id": USER_B_ID},
        {"$set": {"user_id": USER_B_ID, "email": USER_B_EMAIL,
                  "name": "Sister Phase3B", "picture": None,
                  "created_at": now}},
        upsert=True,
    )
    db.user_sessions.update_one(
        {"session_token": TOKEN_B},
        {"$set": {"session_token": TOKEN_B, "user_id": USER_B_ID,
                  "created_at": now, "expires_at": now + timedelta(days=7)}},
        upsert=True,
    )
    yield
    # Cleanup B's data
    db.users.delete_one({"user_id": USER_B_ID})
    db.user_sessions.delete_many({"user_id": USER_B_ID})
    db.community_posts.delete_many({"author_id": {"$in": [USER_A_ID, USER_B_ID]}})
    db.community_replies.delete_many({"author_id": {"$in": [USER_A_ID, USER_B_ID]}})
    db.community_dm_threads.delete_many({"member_ids": USER_B_ID})
    db.community_dm_messages.delete_many({"sender_id": {"$in": [USER_A_ID, USER_B_ID]}})
    db.community_blocks.delete_many({"$or": [{"user_id": USER_B_ID}, {"blocked_id": USER_B_ID},
                                              {"user_id": USER_A_ID}, {"blocked_id": USER_A_ID}]})
    db.community_post_likes.delete_many({"user_id": {"$in": [USER_A_ID, USER_B_ID]}})
    db.community_reports.delete_many({"reporter_id": {"$in": [USER_A_ID, USER_B_ID]}})


@pytest.fixture(scope="module")
def s():
    return requests.Session()


# ---------- Topics ----------
class TestTopics:
    def test_topics_requires_auth(self, s):
        r = s.get(f"{BASE_URL}/api/community/topics")
        assert r.status_code == 401

    def test_topics_returns_items_and_reasons(self, s):
        r = s.get(f"{BASE_URL}/api/community/topics", headers=HEADERS_A)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "items" in d and "report_reasons" in d
        slugs = [t["slug"] for t in d["items"]]
        assert None in slugs  # parish global
        assert "rosary" in slugs and "scripture" in slugs
        assert len(d["report_reasons"]) >= 3


# ---------- Posts ----------
class TestPostCRUD:
    post_id_a = None
    post_id_b = None

    def test_create_post_empty_body_400(self, s):
        r = s.post(f"{BASE_URL}/api/community/posts", headers=HEADERS_A,
                   json={"body": "   "})
        assert r.status_code == 400

    def test_create_post_unknown_topic_400(self, s):
        r = s.post(f"{BASE_URL}/api/community/posts", headers=HEADERS_A,
                   json={"body": "hi", "topic": "not-a-real-topic"})
        assert r.status_code == 400

    def test_create_post_a(self, s):
        r = s.post(f"{BASE_URL}/api/community/posts", headers=HEADERS_A,
                   json={"body": "Glory be to God [A]", "topic": "rosary"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["body"].startswith("Glory be")
        assert d["topic"] == "rosary"
        assert d["author"]["user_id"] == USER_A_ID
        # liturgical color/season may or may not be present depending on calendar code
        assert "liturgical_color" in d
        assert d["like_count"] == 0 and d["reply_count"] == 0
        TestPostCRUD.post_id_a = d["post_id"]

    def test_create_post_b(self, s):
        r = s.post(f"{BASE_URL}/api/community/posts", headers=HEADERS_B,
                   json={"body": "Ave Maria [B]", "topic": "scripture"})
        assert r.status_code == 200, r.text
        TestPostCRUD.post_id_b = r.json()["post_id"]

    def test_get_post_by_id(self, s):
        r = s.get(f"{BASE_URL}/api/community/posts/{TestPostCRUD.post_id_a}", headers=HEADERS_A)
        assert r.status_code == 200
        d = r.json()
        assert d["post_id"] == TestPostCRUD.post_id_a
        assert d["liked_by_me"] is False

    def test_get_post_missing_404(self, s):
        r = s.get(f"{BASE_URL}/api/community/posts/post_doesnotexist", headers=HEADERS_A)
        assert r.status_code == 404

    def test_delete_post_non_author_403(self, s):
        # A tries to delete B's post
        r = s.delete(f"{BASE_URL}/api/community/posts/{TestPostCRUD.post_id_b}", headers=HEADERS_A)
        assert r.status_code == 403

    def test_delete_post_missing_404(self, s):
        r = s.delete(f"{BASE_URL}/api/community/posts/post_nope", headers=HEADERS_A)
        assert r.status_code == 404


# ---------- Feed ----------
class TestFeed:
    def test_feed_global(self, s):
        r = s.get(f"{BASE_URL}/api/community/feed", headers=HEADERS_A)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and isinstance(d["items"], list)
        assert d["topic"] is None
        # Both posts should be present
        ids = [p["post_id"] for p in d["items"]]
        assert TestPostCRUD.post_id_a in ids
        assert TestPostCRUD.post_id_b in ids

    def test_feed_sorted_desc(self, s):
        items = s.get(f"{BASE_URL}/api/community/feed", headers=HEADERS_A).json()["items"]
        ts = [p["created_at"] for p in items]
        assert ts == sorted(ts, reverse=True)

    def test_feed_topic_filter(self, s):
        r = s.get(f"{BASE_URL}/api/community/feed?topic=rosary", headers=HEADERS_A)
        assert r.status_code == 200
        d = r.json()
        assert d["topic"] == "rosary"
        for p in d["items"]:
            assert p["topic"] == "rosary"
        # A's post (rosary) is present, B's (scripture) is not
        ids = [p["post_id"] for p in d["items"]]
        assert TestPostCRUD.post_id_a in ids
        assert TestPostCRUD.post_id_b not in ids

    def test_feed_unknown_topic_400(self, s):
        r = s.get(f"{BASE_URL}/api/community/feed?topic=banana", headers=HEADERS_A)
        assert r.status_code == 400

    def test_feed_limit_clamped(self, s):
        r = s.get(f"{BASE_URL}/api/community/feed?limit=1", headers=HEADERS_A)
        assert r.status_code == 200
        assert len(r.json()["items"]) == 1

    def test_feed_before_cursor(self, s):
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        # Use params= so requests URL-encodes the + in the offset properly
        r = s.get(f"{BASE_URL}/api/community/feed", headers=HEADERS_A,
                  params={"before": future})
        assert r.status_code == 200, r.text
        # all posts are before the future cursor (in the full-suite run,
        # the TestPostCRUD class will have created two posts by now)
        assert isinstance(r.json()["items"], list)

    def test_feed_invalid_before_400(self, s):
        r = s.get(f"{BASE_URL}/api/community/feed?before=not-an-iso", headers=HEADERS_A)
        assert r.status_code == 400


# ---------- Like ----------
class TestLike:
    def test_like_then_unlike(self, s):
        pid = TestPostCRUD.post_id_b
        # First like by A
        r = s.post(f"{BASE_URL}/api/community/posts/{pid}/like", headers=HEADERS_A)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["liked"] is True
        assert d["like_count"] >= 1
        # Toggle off
        r2 = s.post(f"{BASE_URL}/api/community/posts/{pid}/like", headers=HEADERS_A)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["liked"] is False
        assert d2["like_count"] >= 0
        # Verify GET reflects
        g = s.get(f"{BASE_URL}/api/community/posts/{pid}", headers=HEADERS_A).json()
        assert g["liked_by_me"] is False

    def test_like_missing_post_404(self, s):
        r = s.post(f"{BASE_URL}/api/community/posts/post_nope/like", headers=HEADERS_A)
        assert r.status_code == 404


# ---------- Replies ----------
class TestReplies:
    reply_id = None

    def test_reply_empty_400(self, s):
        r = s.post(f"{BASE_URL}/api/community/posts/{TestPostCRUD.post_id_a}/replies",
                   headers=HEADERS_B, json={"body": "  "})
        assert r.status_code == 400

    def test_reply_post_missing_404(self, s):
        r = s.post(f"{BASE_URL}/api/community/posts/post_missing/replies",
                   headers=HEADERS_A, json={"body": "hi"})
        assert r.status_code == 404

    def test_create_reply(self, s):
        r = s.post(f"{BASE_URL}/api/community/posts/{TestPostCRUD.post_id_a}/replies",
                   headers=HEADERS_B, json={"body": "Amen, brother!"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["post_id"] == TestPostCRUD.post_id_a
        assert d["body"] == "Amen, brother!"
        assert d["author"]["user_id"] == USER_B_ID
        TestReplies.reply_id = d["reply_id"]

    def test_list_replies(self, s):
        r = s.get(f"{BASE_URL}/api/community/posts/{TestPostCRUD.post_id_a}/replies",
                  headers=HEADERS_A)
        assert r.status_code == 200
        bodies = [x["body"] for x in r.json()["items"]]
        assert "Amen, brother!" in bodies

    def test_reply_count_incremented(self, s):
        d = s.get(f"{BASE_URL}/api/community/posts/{TestPostCRUD.post_id_a}", headers=HEADERS_A).json()
        assert d["reply_count"] >= 1

    def test_delete_reply_non_author_403(self, s):
        # A is not author of the reply (B is)
        r = s.delete(f"{BASE_URL}/api/community/replies/{TestReplies.reply_id}", headers=HEADERS_A)
        assert r.status_code == 403

    def test_delete_reply_by_author(self, s):
        r = s.delete(f"{BASE_URL}/api/community/replies/{TestReplies.reply_id}", headers=HEADERS_B)
        assert r.status_code == 200
        # No longer in list
        items = s.get(f"{BASE_URL}/api/community/posts/{TestPostCRUD.post_id_a}/replies",
                      headers=HEADERS_A).json()["items"]
        assert all(it["reply_id"] != TestReplies.reply_id for it in items)


# ---------- People search / recommended / profile ----------
class TestPeople:
    def test_search_prefix(self, s):
        r = s.get(f"{BASE_URL}/api/community/users/search?q=Sister", headers=HEADERS_A)
        assert r.status_code == 200
        ids = [u["user_id"] for u in r.json()["items"]]
        assert USER_B_ID in ids
        # Does NOT include self
        assert USER_A_ID not in ids

    def test_search_empty_returns_empty(self, s):
        r = s.get(f"{BASE_URL}/api/community/users/search?q=", headers=HEADERS_A)
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_search_by_email(self, s):
        r = s.get(f"{BASE_URL}/api/community/users/search?q=phase3b", headers=HEADERS_A)
        assert r.status_code == 200
        ids = [u["user_id"] for u in r.json()["items"]]
        assert USER_B_ID in ids

    def test_recommended_excludes_self_and_max_12(self, s):
        r = s.get(f"{BASE_URL}/api/community/users/recommended", headers=HEADERS_A)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) <= 12
        ids = [u["user_id"] for u in items]
        assert USER_A_ID not in ids
        # B is a recent poster — should appear
        assert USER_B_ID in ids

    def test_user_profile(self, s):
        r = s.get(f"{BASE_URL}/api/community/users/{USER_B_ID}", headers=HEADERS_A)
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["user_id"] == USER_B_ID
        assert d["is_self"] is False
        post_ids = [p["post_id"] for p in d["posts"]]
        assert TestPostCRUD.post_id_b in post_ids

    def test_user_profile_self_flag(self, s):
        r = s.get(f"{BASE_URL}/api/community/users/{USER_A_ID}", headers=HEADERS_A)
        assert r.status_code == 200
        assert r.json()["is_self"] is True

    def test_user_profile_404(self, s):
        r = s.get(f"{BASE_URL}/api/community/users/nope_user", headers=HEADERS_A)
        assert r.status_code == 404


# ---------- DMs ----------
class TestDMs:
    thread_id = None

    def test_dm_open_thread_self_400(self, s):
        r = s.post(f"{BASE_URL}/api/community/dm/threads",
                   headers=HEADERS_A, json={"user_id": USER_A_ID})
        assert r.status_code == 400

    def test_dm_open_thread_unknown_404(self, s):
        r = s.post(f"{BASE_URL}/api/community/dm/threads",
                   headers=HEADERS_A, json={"user_id": "ghost_user"})
        assert r.status_code == 404

    def test_dm_open_thread_a_to_b(self, s):
        r = s.post(f"{BASE_URL}/api/community/dm/threads",
                   headers=HEADERS_A, json={"user_id": USER_B_ID})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["thread_id"]
        assert d["other"]["user_id"] == USER_B_ID
        TestDMs.thread_id = d["thread_id"]

    def test_dm_thread_idempotent_deterministic_key(self, s):
        # Re-open from B's side -> same thread_id
        r = s.post(f"{BASE_URL}/api/community/dm/threads",
                   headers=HEADERS_B, json={"user_id": USER_A_ID})
        assert r.status_code == 200
        assert r.json()["thread_id"] == TestDMs.thread_id

    def test_dm_send_message_empty_400(self, s):
        r = s.post(f"{BASE_URL}/api/community/dm/threads/{TestDMs.thread_id}/messages",
                   headers=HEADERS_A, json={"body": "   "})
        assert r.status_code == 400

    def test_dm_send_message_non_member_404(self, s):
        # Use a fake thread id that B is not part of
        r = s.post(f"{BASE_URL}/api/community/dm/threads/nope_thread/messages",
                   headers=HEADERS_B, json={"body": "hi"})
        assert r.status_code == 404

    def test_dm_send_message(self, s):
        r = s.post(f"{BASE_URL}/api/community/dm/threads/{TestDMs.thread_id}/messages",
                   headers=HEADERS_A, json={"body": "Pax tecum!"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["sender_id"] == USER_A_ID
        assert d["body"] == "Pax tecum!"
        assert d["thread_id"] == TestDMs.thread_id

    def test_dm_threads_inbox_has_unread_for_b(self, s):
        r = s.get(f"{BASE_URL}/api/community/dm/threads", headers=HEADERS_B)
        assert r.status_code == 200
        items = r.json()["items"]
        mine = next((t for t in items if t["thread_id"] == TestDMs.thread_id), None)
        assert mine is not None
        assert mine["unread"] >= 1
        assert mine["last_message"] == "Pax tecum!"

    def test_dm_messages_marks_read(self, s):
        r = s.get(f"{BASE_URL}/api/community/dm/threads/{TestDMs.thread_id}/messages",
                  headers=HEADERS_B)
        assert r.status_code == 200
        d = r.json()
        assert d["thread"]["thread_id"] == TestDMs.thread_id
        assert any(m["body"] == "Pax tecum!" for m in d["messages"])
        # After reading, unread becomes 0
        time.sleep(0.3)
        items = s.get(f"{BASE_URL}/api/community/dm/threads", headers=HEADERS_B).json()["items"]
        mine = next(t for t in items if t["thread_id"] == TestDMs.thread_id)
        assert mine["unread"] == 0

    def test_dm_messages_non_member_404(self, s):
        # Create an unrelated user-context: use a 3rd token? simulate via wrong thread id
        r = s.get(f"{BASE_URL}/api/community/dm/threads/nonexistent_thread/messages",
                  headers=HEADERS_A)
        assert r.status_code == 404


# ---------- Reports ----------
class TestReports:
    def test_report_valid(self, s):
        r = s.post(f"{BASE_URL}/api/community/report", headers=HEADERS_A,
                   json={"target_type": "post", "target_id": TestPostCRUD.post_id_b,
                         "reason": "Spam or misleading", "detail": "test"})
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True and d["report_id"].startswith("rep_")

    def test_report_invalid_target_400(self, s):
        r = s.post(f"{BASE_URL}/api/community/report", headers=HEADERS_A,
                   json={"target_type": "blog", "target_id": "x",
                         "reason": "Spam or misleading"})
        assert r.status_code == 400

    def test_report_invalid_reason_400(self, s):
        r = s.post(f"{BASE_URL}/api/community/report", headers=HEADERS_A,
                   json={"target_type": "post", "target_id": "x", "reason": "Bad vibes"})
        assert r.status_code == 400


# ---------- Block / Unblock & DM gating ----------
class TestBlocking:
    def test_block_user(self, s):
        r = s.post(f"{BASE_URL}/api/community/block/{USER_B_ID}", headers=HEADERS_A)
        assert r.status_code == 200

    def test_block_blocks_dm_send(self, s):
        # A blocked B in test above. A tries to send -> 403 (block is reciprocal)
        r = s.post(f"{BASE_URL}/api/community/dm/threads/{TestDMs.thread_id}/messages",
                   headers=HEADERS_A, json={"body": "still there?"})
        assert r.status_code == 403
        # B also blocked from sending to A
        r2 = s.post(f"{BASE_URL}/api/community/dm/threads/{TestDMs.thread_id}/messages",
                    headers=HEADERS_B, json={"body": "hello back"})
        assert r2.status_code == 403

    def test_block_self_400(self, s):
        r = s.post(f"{BASE_URL}/api/community/block/{USER_A_ID}", headers=HEADERS_A)
        assert r.status_code == 400

    def test_unblock(self, s):
        r = s.delete(f"{BASE_URL}/api/community/block/{USER_B_ID}", headers=HEADERS_A)
        assert r.status_code == 200
        # DM should work again
        r2 = s.post(f"{BASE_URL}/api/community/dm/threads/{TestDMs.thread_id}/messages",
                    headers=HEADERS_A, json={"body": "we good"})
        assert r2.status_code == 200


# ---------- Delete post (cleanup + author rule positive) ----------
class TestPostDeleteOwn:
    def test_delete_own_post(self, s):
        r = s.delete(f"{BASE_URL}/api/community/posts/{TestPostCRUD.post_id_a}",
                     headers=HEADERS_A)
        assert r.status_code == 200
        # Verify gone
        g = s.get(f"{BASE_URL}/api/community/posts/{TestPostCRUD.post_id_a}",
                  headers=HEADERS_A)
        assert g.status_code == 404


# ---------- Regression smoke ----------
class TestRegression:
    def test_auth_me(self, s):
        r = s.get(f"{BASE_URL}/api/auth/me", headers=HEADERS_A)
        assert r.status_code == 200
        assert r.json()["user_id"] == USER_A_ID

    def test_bible_books_73(self, s):
        r = s.get(f"{BASE_URL}/api/bible/books")
        assert r.status_code == 200
        assert len(r.json()["items"]) == 73

    def test_bible_chapter_john_3(self, s):
        r = s.get(f"{BASE_URL}/api/bible/chapter/john/3", headers=HEADERS_A)
        assert r.status_code == 200
        d = r.json()
        v16 = next((v for v in d["verses"] if v["n"] == 16), None)
        assert v16 and "may not perish" in v16["text"].lower()

    def test_wellness_profile(self, s):
        r = s.get(f"{BASE_URL}/api/wellness/profile", headers=HEADERS_A)
        assert r.status_code == 200

    def test_churches_nearby(self, s):
        r = s.get(f"{BASE_URL}/api/churches/nearby?lat=41.9029&lng=12.4534&radius_m=5000&enrich=false",
                  headers=HEADERS_A)
        assert r.status_code == 200
        assert "items" in r.json()

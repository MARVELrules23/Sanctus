"""
Friends + Group DMs backend tests (iteration 23).

Covers:
- /api/community/friends/{status, request, accept, decline, list} + DELETE /friends/{id}
- /api/community/dm/threads/group, /name, /members (add/remove)
- /api/community/dm/threads/{id}/messages for groups
- /api/community/dm/threads inbox group projection
"""
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

# Test cohort — 4 users so we can do friend graphs + groups
USERS = [
    ("TEST_fg_alpha", "TEST_fg_token_a", "TEST Alpha"),
    ("TEST_fg_bravo", "TEST_fg_token_b", "TEST Bravo"),
    ("TEST_fg_charlie", "TEST_fg_token_c", "TEST Charlie"),
    ("TEST_fg_delta", "TEST_fg_token_d", "TEST Delta"),
]


@pytest.fixture(scope="module")
def db():
    cli = MongoClient(MONGO_URL)
    yield cli[DB_NAME]
    cli.close()


@pytest.fixture(scope="module", autouse=True)
def seed(db):
    now = datetime.now(timezone.utc)
    for uid, tok, name in USERS:
        db.users.update_one(
            {"user_id": uid},
            {"$set": {"user_id": uid, "email": f"{uid}@example.com",
                      "name": name, "picture": None, "created_at": now}},
            upsert=True,
        )
        db.user_sessions.update_one(
            {"session_token": tok},
            {"$set": {"session_token": tok, "user_id": uid,
                      "created_at": now,
                      "expires_at": now + timedelta(days=7)}},
            upsert=True,
        )
    yield
    # Cleanup
    uids = [u[0] for u in USERS]
    db.user_sessions.delete_many({"user_id": {"$in": uids}})
    db.users.delete_many({"user_id": {"$in": uids}})
    db.community_friendships.delete_many({"members": {"$in": uids}})
    # Delete any threads we created (where created_by is one of ours, or
    # member_ids contains one of ours)
    threads = list(db.community_dm_threads.find(
        {"member_ids": {"$in": uids}}, {"thread_id": 1, "_id": 0}
    ))
    tids = [t["thread_id"] for t in threads]
    if tids:
        db.community_dm_threads.delete_many({"thread_id": {"$in": tids}})
        db.community_dm_messages.delete_many({"thread_id": {"$in": tids}})


def _client(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    })
    return s


@pytest.fixture(scope="module")
def alpha():
    return _client(USERS[0][1])


@pytest.fixture(scope="module")
def bravo():
    return _client(USERS[1][1])


@pytest.fixture(scope="module")
def charlie():
    return _client(USERS[2][1])


@pytest.fixture(scope="module")
def delta():
    return _client(USERS[3][1])


UID = {u[0]: u[0] for u in USERS}
A, B, C, D = USERS[0][0], USERS[1][0], USERS[2][0], USERS[3][0]


# ---------- Friend status & lifecycle -----------------------------------

class TestFriendStatusAndLifecycle:
    def test_status_none_initially(self, alpha):
        # Clean slate
        r = alpha.get(f"{BASE_URL}/api/community/friends/status/{B}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] in ("none", "pending", "accepted")  # if leftover, will be reset by next test
        # If leftover from prior runs, clean
        if body["status"] != "none":
            alpha.delete(f"{BASE_URL}/api/community/friends/{B}")
            r = alpha.get(f"{BASE_URL}/api/community/friends/status/{B}")
            assert r.json()["status"] == "none"

    def test_self_status(self, alpha):
        r = alpha.get(f"{BASE_URL}/api/community/friends/status/{A}")
        assert r.status_code == 200
        assert r.json() == {"status": "self", "requested_by": None}

    def test_request_friend_self_400(self, alpha):
        r = alpha.post(f"{BASE_URL}/api/community/friends/request",
                       json={"user_id": A})
        assert r.status_code == 400

    def test_request_unknown_user_404(self, alpha):
        r = alpha.post(f"{BASE_URL}/api/community/friends/request",
                       json={"user_id": "TEST_does_not_exist_999"})
        assert r.status_code == 404

    def test_request_creates_pending(self, alpha, bravo):
        r = alpha.post(f"{BASE_URL}/api/community/friends/request",
                       json={"user_id": B})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "pending"
        assert body["requested_by"] == A
        # Status visible to both sides
        assert alpha.get(f"{BASE_URL}/api/community/friends/status/{B}").json() == {
            "status": "pending", "requested_by": A
        }
        assert bravo.get(f"{BASE_URL}/api/community/friends/status/{A}").json() == {
            "status": "pending", "requested_by": A
        }

    def test_request_idempotent(self, alpha):
        r = alpha.post(f"{BASE_URL}/api/community/friends/request",
                       json={"user_id": B})
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    def test_sender_cannot_accept(self, alpha):
        r = alpha.post(f"{BASE_URL}/api/community/friends/accept",
                       json={"user_id": B})
        assert r.status_code == 400

    def test_recipient_accepts(self, bravo, alpha):
        r = bravo.post(f"{BASE_URL}/api/community/friends/accept",
                       json={"user_id": A})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "accepted"
        assert body["accepted_at"] is not None
        # Status both ways
        assert alpha.get(f"{BASE_URL}/api/community/friends/status/{B}").json()["status"] == "accepted"

    def test_request_after_accepted_400(self, alpha):
        r = alpha.post(f"{BASE_URL}/api/community/friends/request",
                       json={"user_id": B})
        assert r.status_code == 400

    def test_decline_accepted_400(self, alpha):
        r = alpha.post(f"{BASE_URL}/api/community/friends/decline",
                       json={"user_id": B})
        assert r.status_code == 400

    def test_list_accepted_scoped(self, alpha, bravo):
        ra = alpha.get(f"{BASE_URL}/api/community/friends/list?status=accepted")
        rb = bravo.get(f"{BASE_URL}/api/community/friends/list?status=accepted")
        assert ra.status_code == 200 and rb.status_code == 200
        a_items = ra.json()["items"]
        b_items = rb.json()["items"]
        assert any(it["user"]["user_id"] == B for it in a_items)
        assert any(it["user"]["user_id"] == A for it in b_items)

    def test_unfriend_idempotent(self, alpha, bravo):
        r = alpha.delete(f"{BASE_URL}/api/community/friends/{B}")
        assert r.status_code == 200
        # Second call still 200
        r2 = alpha.delete(f"{BASE_URL}/api/community/friends/{B}")
        assert r2.status_code == 200
        assert alpha.get(f"{BASE_URL}/api/community/friends/status/{B}").json()["status"] == "none"

    def test_decline_cancels_outgoing(self, alpha, bravo):
        # Alpha sends a fresh request
        alpha.post(f"{BASE_URL}/api/community/friends/request", json={"user_id": B})
        # Alpha (sender) declines/cancels own outgoing
        r = alpha.post(f"{BASE_URL}/api/community/friends/decline",
                       json={"user_id": B})
        assert r.status_code == 200
        assert alpha.get(f"{BASE_URL}/api/community/friends/status/{B}").json()["status"] == "none"

    def test_decline_noop_when_no_edge(self, alpha):
        r = alpha.post(f"{BASE_URL}/api/community/friends/decline",
                       json={"user_id": B})
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    def test_incoming_outgoing_lists(self, alpha, bravo, charlie):
        # Alpha sends to Charlie
        alpha.post(f"{BASE_URL}/api/community/friends/request", json={"user_id": C})
        out = alpha.get(f"{BASE_URL}/api/community/friends/list?status=outgoing").json()
        assert any(it["user"]["user_id"] == C for it in out["items"])
        inc = charlie.get(f"{BASE_URL}/api/community/friends/list?status=incoming").json()
        assert any(it["user"]["user_id"] == A for it in inc["items"])
        # Cleanup
        alpha.post(f"{BASE_URL}/api/community/friends/decline", json={"user_id": C})

    def test_list_invalid_status_400(self, alpha):
        r = alpha.get(f"{BASE_URL}/api/community/friends/list?status=garbage")
        assert r.status_code == 400


# ---------- Group DM lifecycle ------------------------------------------

GROUP_STATE = {}  # store thread_id across class methods


class TestGroupDMs:
    def _accept_friend(self, requester, recipient_token, target_uid):
        """Helper: make a friendship between requester (session) and target."""
        requester.post(f"{BASE_URL}/api/community/friends/request",
                       json={"user_id": target_uid})
        rec = _client(recipient_token)
        rec.post(f"{BASE_URL}/api/community/friends/accept",
                 json={"user_id": _user_of(requester)})

    def test_create_group_requires_2_others(self, alpha):
        r = alpha.post(f"{BASE_URL}/api/community/dm/threads/group",
                       json={"member_ids": []})
        assert r.status_code == 400

    def test_create_group_unknown_user_404(self, alpha):
        r = alpha.post(f"{BASE_URL}/api/community/dm/threads/group",
                       json={"member_ids": ["TEST_unknown_user_xyz", B]})
        assert r.status_code == 404

    def test_create_group_success(self, alpha):
        r = alpha.post(f"{BASE_URL}/api/community/dm/threads/group",
                       json={"member_ids": [B, C]})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["is_group"] is True
        assert body["created_by"] == A
        assert body["name"] is None
        assert body["auto_name"]  # should contain Bravo + Charlie names
        # Members include all 3, with public user shapes
        mids = sorted(m["user_id"] for m in body["members"])
        assert mids == sorted([A, B, C])
        # Auto name excludes the viewer (Alpha) — so should mention Bravo/Charlie
        assert "Alpha" not in body["auto_name"]
        assert "Bravo" in body["auto_name"] and "Charlie" in body["auto_name"]
        GROUP_STATE["tid"] = body["thread_id"]
        assert body["thread_id"].startswith("group:")

    def test_create_group_with_name(self, alpha):
        r = alpha.post(f"{BASE_URL}/api/community/dm/threads/group",
                       json={"member_ids": [B, C], "name": "  Holy Hour Crew  "})
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Holy Hour Crew"
        # cleanup this throwaway group
        for uid in [A, B, C]:
            tok = next(u[1] for u in USERS if u[0] == uid)
            _client(tok).delete(f"{BASE_URL}/api/community/dm/threads/{body['thread_id']}/members/{uid}")

    def test_create_group_creator_auto_added_even_if_duplicated(self, alpha):
        r = alpha.post(f"{BASE_URL}/api/community/dm/threads/group",
                       json={"member_ids": [A, B, C]})
        assert r.status_code == 200
        body = r.json()
        assert sorted(m["user_id"] for m in body["members"]) == sorted([A, B, C])
        # cleanup
        _client(USERS[0][1]).delete(
            f"{BASE_URL}/api/community/dm/threads/{body['thread_id']}/members/{A}")
        for uid in [B, C]:
            tok = next(u[1] for u in USERS if u[0] == uid)
            _client(tok).delete(f"{BASE_URL}/api/community/dm/threads/{body['thread_id']}/members/{uid}")

    def test_group_appears_in_inbox(self, alpha, bravo):
        tid = GROUP_STATE["tid"]
        for client_ in (alpha, bravo):
            inbox = client_.get(f"{BASE_URL}/api/community/dm/threads").json()
            found = [t for t in inbox["items"] if t["thread_id"] == tid]
            assert found, f"group not in inbox of {_user_of(client_)}"
            t = found[0]
            assert t["is_group"] is True
            assert t["auto_name"]
            assert isinstance(t["members"], list) and len(t["members"]) == 3

    def test_rename_group_by_member(self, bravo):
        tid = GROUP_STATE["tid"]
        r = bravo.put(f"{BASE_URL}/api/community/dm/threads/{tid}/name",
                      json={"name": "Lectio Group"})
        assert r.status_code == 200
        assert r.json()["name"] == "Lectio Group"

    def test_rename_group_clear_returns_to_auto(self, alpha):
        tid = GROUP_STATE["tid"]
        r = alpha.put(f"{BASE_URL}/api/community/dm/threads/{tid}/name",
                      json={"name": None})
        assert r.status_code == 200
        body = r.json()
        assert body["name"] is None
        assert body["auto_name"]

    def test_rename_404_for_non_member(self, delta):
        tid = GROUP_STATE["tid"]
        r = delta.put(f"{BASE_URL}/api/community/dm/threads/{tid}/name",
                      json={"name": "hijack"})
        assert r.status_code == 404

    def test_add_member(self, alpha):
        tid = GROUP_STATE["tid"]
        r = alpha.post(f"{BASE_URL}/api/community/dm/threads/{tid}/members",
                       json={"user_id": D})
        assert r.status_code == 200
        mids = sorted(m["user_id"] for m in r.json()["members"])
        assert D in mids and len(mids) == 4

    def test_add_member_idempotent(self, alpha):
        tid = GROUP_STATE["tid"]
        r = alpha.post(f"{BASE_URL}/api/community/dm/threads/{tid}/members",
                       json={"user_id": D})
        assert r.status_code == 200
        assert len([m for m in r.json()["members"] if m["user_id"] == D]) == 1

    def test_add_member_404_unknown(self, alpha):
        tid = GROUP_STATE["tid"]
        r = alpha.post(f"{BASE_URL}/api/community/dm/threads/{tid}/members",
                       json={"user_id": "TEST_no_such_user"})
        assert r.status_code == 404

    def test_add_member_404_non_member(self, delta):
        # Delta is now a member after test_add_member, so create a fresh
        # non-member scenario with a brand-new outsider
        tid = GROUP_STATE["tid"]
        # Seed an unrelated user that's NOT in the group
        outsider_token = "TEST_fg_token_outsider"
        outsider_uid = "TEST_fg_outsider"
        cli = MongoClient(MONGO_URL)
        db = cli[DB_NAME]
        now = datetime.now(timezone.utc)
        db.users.update_one({"user_id": outsider_uid},
                            {"$set": {"user_id": outsider_uid, "name": "Outsider",
                                      "email": "outsider@example.com"}}, upsert=True)
        db.user_sessions.update_one({"session_token": outsider_token},
                                    {"$set": {"session_token": outsider_token,
                                              "user_id": outsider_uid,
                                              "expires_at": now + timedelta(days=1)}},
                                    upsert=True)
        cli.close()
        outsider = _client(outsider_token)
        r = outsider.post(f"{BASE_URL}/api/community/dm/threads/{tid}/members",
                          json={"user_id": outsider_uid})
        assert r.status_code == 404
        # Cleanup outsider
        cli = MongoClient(MONGO_URL)
        cli[DB_NAME].users.delete_one({"user_id": outsider_uid})
        cli[DB_NAME].user_sessions.delete_one({"session_token": outsider_token})
        cli.close()

    def test_send_and_read_group_message(self, alpha, charlie):
        tid = GROUP_STATE["tid"]
        r = alpha.post(f"{BASE_URL}/api/community/dm/threads/{tid}/messages",
                       json={"body": "Pax vobiscum, group!"})
        assert r.status_code == 200, r.text
        msg = r.json()
        assert msg["body"] == "Pax vobiscum, group!"
        # Charlie reads
        rg = charlie.get(f"{BASE_URL}/api/community/dm/threads/{tid}/messages")
        assert rg.status_code == 200
        body = rg.json()
        # thread.members[] should be present for groups
        assert body["thread"]["is_group"] is True
        assert isinstance(body["thread"]["members"], list)
        assert len(body["thread"]["members"]) >= 3
        # Message is visible
        assert any(m["message_id"] == msg["message_id"] for m in body["messages"])

    def test_inbox_shows_unread_for_non_sender(self, bravo):
        tid = GROUP_STATE["tid"]
        inbox = bravo.get(f"{BASE_URL}/api/community/dm/threads").json()
        t = next(t for t in inbox["items"] if t["thread_id"] == tid)
        # Bravo hasn't read yet (alpha sent the message)
        assert t["unread"] >= 1
        assert t["last_message"] == "Pax vobiscum, group!"

    def test_non_member_cannot_send(self, delta):
        # Wait — delta IS a member at this point. Use outsider instead.
        # Make sure outsider cannot send.
        tid = GROUP_STATE["tid"]
        outsider_token = "TEST_fg_token_outsider2"
        outsider_uid = "TEST_fg_outsider2"
        cli = MongoClient(MONGO_URL)
        db = cli[DB_NAME]
        now = datetime.now(timezone.utc)
        db.users.update_one({"user_id": outsider_uid},
                            {"$set": {"user_id": outsider_uid, "name": "X", "email": "x@e.com"}},
                            upsert=True)
        db.user_sessions.update_one({"session_token": outsider_token},
                                    {"$set": {"session_token": outsider_token,
                                              "user_id": outsider_uid,
                                              "expires_at": now + timedelta(days=1)}},
                                    upsert=True)
        cli.close()
        outsider = _client(outsider_token)
        r = outsider.post(f"{BASE_URL}/api/community/dm/threads/{tid}/messages",
                          json={"body": "intruder"})
        assert r.status_code == 404
        cli = MongoClient(MONGO_URL)
        cli[DB_NAME].users.delete_one({"user_id": outsider_uid})
        cli[DB_NAME].user_sessions.delete_one({"session_token": outsider_token})
        cli.close()

    def test_remove_member_creator_only(self, bravo):
        # Bravo is NOT the creator; cannot remove Charlie
        tid = GROUP_STATE["tid"]
        r = bravo.delete(f"{BASE_URL}/api/community/dm/threads/{tid}/members/{C}")
        assert r.status_code == 403

    def test_self_leave(self, delta):
        tid = GROUP_STATE["tid"]
        r = delta.delete(f"{BASE_URL}/api/community/dm/threads/{tid}/members/{D}")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_last_member_deletes_thread(self, alpha, bravo, charlie):
        tid = GROUP_STATE["tid"]
        # Each remaining (alpha, bravo, charlie) leaves
        for cli, uid in ((charlie, C), (bravo, B), (alpha, A)):
            r = cli.delete(f"{BASE_URL}/api/community/dm/threads/{tid}/members/{uid}")
            assert r.status_code == 200, f"{uid} leave failed: {r.text}"
        # Final leaver should report deleted=True; verify thread really gone
        cli = MongoClient(MONGO_URL)
        gone = cli[DB_NAME].community_dm_threads.find_one({"thread_id": tid})
        assert gone is None
        msgs = cli[DB_NAME].community_dm_messages.count_documents({"thread_id": tid})
        assert msgs == 0
        cli.close()

    def test_max_group_members_cap(self, alpha):
        # Create group with > 50 total to hit the 400. Synthesize 50 dummy users.
        cli = MongoClient(MONGO_URL)
        dbh = cli[DB_NAME]
        dummy_ids = [f"TEST_fg_dummy_{i}" for i in range(50)]
        for did in dummy_ids:
            dbh.users.update_one({"user_id": did},
                                 {"$set": {"user_id": did, "name": did, "email": f"{did}@e.com"}},
                                 upsert=True)
        cli.close()
        # 50 others + Alpha = 51 → 400
        r = alpha.post(f"{BASE_URL}/api/community/dm/threads/group",
                       json={"member_ids": dummy_ids})
        assert r.status_code == 400, r.text
        cli = MongoClient(MONGO_URL)
        cli[DB_NAME].users.delete_many({"user_id": {"$in": dummy_ids}})
        cli.close()


def _user_of(client_: requests.Session) -> str:
    """Reverse-look up the user_id from a session by Authorization header."""
    tok = client_.headers["Authorization"].split(" ", 1)[1]
    for uid, t, _ in USERS:
        if t == tok:
            return uid
    return ""

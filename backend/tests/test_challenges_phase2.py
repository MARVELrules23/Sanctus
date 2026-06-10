"""Backend tests for Liturgical Challenges Phase 2.

Coverage:
  - GET /api/challenges/{slug}/companions  (auth required, shape, friend-only filtering)
  - POST /api/community/posts with optional `challenge` ref
  - GET /api/community/feed includes `challenge`
  - GET /api/community/posts/{post_id} includes `challenge`
"""
from datetime import datetime, timedelta, timezone

import pytest
import requests

from conftest import BASE_URL  # type: ignore


# --- Two users + one accepted friendship + one stranger user ----------------
A_USER_ID = "TEST_p2_userA"
A_TOKEN = "TEST_p2_tokA"
B_USER_ID = "TEST_p2_userB"
B_TOKEN = "TEST_p2_tokB"
C_USER_ID = "TEST_p2_userC"   # stranger (not friend with A)
C_TOKEN = "TEST_p2_tokC"
LONELY_USER_ID = "TEST_p2_lonely"  # has no friends at all
LONELY_TOKEN = "TEST_p2_tok_lonely"

ADMIN_USER_ID = "TEST_p2_admin"
ADMIN_TOKEN = "TEST_p2_admin_tok"


def _hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _friendship_key(a, b):
    x, y = sorted([a, b])
    return f"{x}__{y}"


@pytest.fixture(scope="module")
def seed_phase2(mongo_db):
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=1)

    users = [
        (A_USER_ID, "TEST_p2_a@sanctus.app", "TEST P2 A", False),
        (B_USER_ID, "TEST_p2_b@sanctus.app", "TEST P2 B", False),
        (C_USER_ID, "TEST_p2_c@sanctus.app", "TEST P2 C", False),
        (LONELY_USER_ID, "TEST_p2_lonely@sanctus.app", "TEST P2 Lonely", False),
        (ADMIN_USER_ID, "TEST_p2_admin@sanctus.app", "TEST P2 Admin", True),
    ]
    tokens = [
        (A_TOKEN, A_USER_ID),
        (B_TOKEN, B_USER_ID),
        (C_TOKEN, C_USER_ID),
        (LONELY_TOKEN, LONELY_USER_ID),
        (ADMIN_TOKEN, ADMIN_USER_ID),
    ]

    for uid, email, name, is_admin in users:
        mongo_db.users.update_one(
            {"user_id": uid},
            {"$set": {
                "user_id": uid, "email": email, "name": name,
                "picture": None, "is_admin": is_admin, "created_at": now,
            }}, upsert=True,
        )
    for tok, uid in tokens:
        mongo_db.user_sessions.update_one(
            {"session_token": tok},
            {"$set": {"session_token": tok, "user_id": uid,
                      "created_at": now, "expires_at": exp}}, upsert=True,
        )

    # Accepted friendship A <-> B; pending friendship A <-> C (not accepted).
    mongo_db.community_friendships.update_one(
        {"friendship_id": _friendship_key(A_USER_ID, B_USER_ID)},
        {"$set": {
            "friendship_id": _friendship_key(A_USER_ID, B_USER_ID),
            "members": sorted([A_USER_ID, B_USER_ID]),
            "status": "accepted",
            "requested_by": A_USER_ID,
            "created_at": now,
            "accepted_at": now,
        }}, upsert=True,
    )
    mongo_db.community_friendships.update_one(
        {"friendship_id": _friendship_key(A_USER_ID, C_USER_ID)},
        {"$set": {
            "friendship_id": _friendship_key(A_USER_ID, C_USER_ID),
            "members": sorted([A_USER_ID, C_USER_ID]),
            "status": "pending",
            "requested_by": A_USER_ID,
            "created_at": now,
        }}, upsert=True,
    )

    # Make sure hallowtide is published so list/detail are 200 for non-admin.
    requests.post(f"{BASE_URL}/api/challenges/admin/hallowtide/publish",
                  headers=_hdr(ADMIN_TOKEN), timeout=15)

    # Enroll B and C in hallowtide. A is intentionally NOT enrolled — we are
    # testing A's "friends walking with me" view.
    for tok in (B_TOKEN, C_TOKEN):
        requests.post(f"{BASE_URL}/api/challenges/hallowtide/enroll",
                      headers=_hdr(tok), timeout=15)

    yield {"A": A_USER_ID, "B": B_USER_ID, "C": C_USER_ID}

    # Teardown
    uids = [A_USER_ID, B_USER_ID, C_USER_ID, LONELY_USER_ID, ADMIN_USER_ID]
    mongo_db.community_friendships.delete_many({
        "friendship_id": {"$in": [
            _friendship_key(A_USER_ID, B_USER_ID),
            _friendship_key(A_USER_ID, C_USER_ID),
        ]}
    })
    mongo_db.challenge_enrollments.delete_many({"user_id": {"$in": uids}})
    mongo_db.challenge_checkins.delete_many({"user_id": {"$in": uids}})
    mongo_db.community_posts.delete_many({"author_id": {"$in": uids}})
    mongo_db.community_post_likes.delete_many({"user_id": {"$in": uids}})
    mongo_db.user_sessions.delete_many({"user_id": {"$in": uids}})
    mongo_db.users.delete_many({"user_id": {"$in": uids}})


# =============== /companions ================================================

class TestCompanions:
    def test_requires_auth(self, seed_phase2):
        r = requests.get(f"{BASE_URL}/api/challenges/hallowtide/companions",
                         timeout=15)
        assert r.status_code in (401, 403), r.text

    def test_shape_for_user_with_enrolled_friend(self, seed_phase2):
        r = requests.get(
            f"{BASE_URL}/api/challenges/hallowtide/companions?limit=20",
            headers=_hdr(A_TOKEN), timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("items"), list)
        assert isinstance(d.get("total"), int)
        ids = [it["user_id"] for it in d["items"]]
        # B is an accepted friend AND enrolled -> must be present
        assert B_USER_ID in ids, f"expected B in companions, got {ids}"
        # C is enrolled but only a *pending* friendship — must NOT appear
        assert C_USER_ID not in ids, f"C (pending) leaked into companions: {ids}"
        assert d["total"] >= 1
        # Item shape
        item = next(it for it in d["items"] if it["user_id"] == B_USER_ID)
        for k in ("user_id", "name", "picture",
                  "current_streak", "total_days_completed"):
            assert k in item, f"missing key {k} in {item}"
        assert item["name"] == "TEST P2 B"
        assert isinstance(item["current_streak"], int)
        assert isinstance(item["total_days_completed"], int)

    def test_lonely_user_returns_empty(self, seed_phase2):
        """Caller has no friendships at all -> empty items, total 0, NOT an error."""
        r = requests.get(
            f"{BASE_URL}/api/challenges/hallowtide/companions",
            headers=_hdr(LONELY_TOKEN), timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d == {"items": [], "total": 0}

    @pytest.mark.parametrize("slug", ["hallowtide", "advent", "lent"])
    def test_valid_slugs(self, seed_phase2, slug):
        # Ensure slug published first
        requests.post(f"{BASE_URL}/api/challenges/admin/{slug}/publish",
                      headers=_hdr(ADMIN_TOKEN), timeout=15)
        r = requests.get(f"{BASE_URL}/api/challenges/{slug}/companions",
                         headers=_hdr(A_TOKEN), timeout=15)
        assert r.status_code == 200, f"{slug}: {r.text}"
        d = r.json()
        assert "items" in d and "total" in d

    def test_unknown_slug_is_404(self, seed_phase2):
        r = requests.get(
            f"{BASE_URL}/api/challenges/does-not-exist-zzz/companions",
            headers=_hdr(A_TOKEN), timeout=15,
        )
        assert r.status_code == 404


# =============== POST /community/posts with `challenge` =====================

CHALLENGE_REF = {
    "slug": "hallowtide",
    "name": "Hallowtide",
    "day_index": 1,
    "day_title": "Vigil",
    "color": "#7C3AED",
    "icon": "flame",
}


class TestCommunityChallengePosts:
    def test_post_with_challenge_echoes_ref(self, seed_phase2):
        body = "TEST_P2 reflection with challenge"
        r = requests.post(
            f"{BASE_URL}/api/community/posts",
            headers=_hdr(A_TOKEN),
            json={"body": body, "topic": None, "image": None,
                  "challenge": CHALLENGE_REF},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["body"] == body
        ch = d.get("challenge")
        assert ch is not None, f"challenge missing in post response: {d}"
        assert ch["slug"] == "hallowtide"
        assert ch["name"] == "Hallowtide"
        assert ch["day_index"] == 1
        assert ch["day_title"] == "Vigil"
        assert ch["color"] == "#7C3AED"
        assert ch["icon"] == "flame"
        post_id = d["post_id"]

        # GET single post should also echo `challenge`
        g = requests.get(f"{BASE_URL}/api/community/posts/{post_id}",
                         headers=_hdr(A_TOKEN), timeout=15)
        assert g.status_code == 200
        gd = g.json()
        assert gd.get("challenge") is not None
        assert gd["challenge"]["slug"] == "hallowtide"
        assert gd["challenge"]["day_index"] == 1

        # Feed should include it with challenge set
        f = requests.get(f"{BASE_URL}/api/community/feed?limit=30",
                         headers=_hdr(A_TOKEN), timeout=15)
        assert f.status_code == 200
        fd = f.json()
        found = next((p for p in fd["items"] if p["post_id"] == post_id), None)
        assert found is not None, "newly posted item missing from feed"
        assert found.get("challenge") is not None
        assert found["challenge"]["slug"] == "hallowtide"

    def test_post_without_challenge_is_null(self, seed_phase2):
        body = "TEST_P2 plain post no challenge"
        r = requests.post(
            f"{BASE_URL}/api/community/posts",
            headers=_hdr(A_TOKEN),
            json={"body": body, "topic": None, "image": None},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["body"] == body
        assert "challenge" in d, "challenge key missing from post response"
        assert d["challenge"] is None, f"expected null challenge, got {d.get('challenge')}"

    def test_legacy_posts_have_null_challenge_in_feed(self, seed_phase2, mongo_db):
        """Older posts (without `challenge`) must still serialize with challenge:null."""
        # Insert a raw legacy post directly (no `challenge` field at all)
        legacy_id = f"post_TESTp2_legacy"
        mongo_db.community_posts.insert_one({
            "post_id": legacy_id,
            "author_id": A_USER_ID,
            "body": "TEST_P2 legacy raw",
            "topic": None,
            "image": None,
            "liturgical_color": None,
            "liturgical_season": None,
            "created_at": datetime.now(timezone.utc),
            "like_count": 0,
            "reply_count": 0,
            "hidden": False,
            "is_pinned": False,
            # NOTE: no `challenge` field
        })
        try:
            r = requests.get(f"{BASE_URL}/api/community/posts/{legacy_id}",
                             headers=_hdr(A_TOKEN), timeout=15)
            assert r.status_code == 200
            d = r.json()
            assert "challenge" in d, "challenge key missing on legacy post"
            assert d["challenge"] is None
        finally:
            mongo_db.community_posts.delete_one({"post_id": legacy_id})

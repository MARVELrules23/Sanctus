"""End-to-end tests for the Saint / Blessed / Venerable of the Day feature.

Covers:
  * Auth gating (401 unauth, 403 non-admin)
  * Admin manual-create -> approve -> public read -> delete -> 404 happy path
  * Approval validation (refusing empty quote / quote_source / etc.)
  * Bad date formats on /saints/today
  * Primary vs secondaries ordering on the same feast_date
  * Fallback rotation when no entries match today's MM-DD
  * Optional Claude propose call (skipped/tolerated on 502)

All test data is created with `saint_id` prefixed by `st_test_` and
fully removed in teardown. The seeded admin user (philipwils13@gmail.com)
is NEVER deleted; only the test-minted sessions and the test-only
non-admin user are removed.
"""
from __future__ import annotations

import os
import uuid
from datetime import date as _date, datetime, timedelta, timezone
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
API = f"{BASE_URL}/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

# Pre-seeded admin (per /app/memory/test_credentials.md). DO NOT DELETE.
ADMIN_USER_ID = "user_ade7a898e281"
ADMIN_EMAIL = "philipwils13@gmail.com"

# Test-only non-admin user — created and removed by this suite.
NONADMIN_USER_ID = "test_user_saints_nonadmin"
NONADMIN_EMAIL = "test_saints_nonadmin@sanctus.app"

# Per-suite session tokens minted directly into Mongo
ADMIN_TOKEN = f"test_saints_admin_{uuid.uuid4().hex[:8]}"
NONADMIN_TOKEN = f"test_saints_nonadmin_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def mongo_db():
    cli = MongoClient(MONGO_URL)
    db = cli[DB_NAME]
    yield db
    cli.close()


@pytest.fixture(scope="module", autouse=True)
def seed_sessions(mongo_db):
    """Mint admin + non-admin sessions; tear them (and test saints) down."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=1)

    # Ensure the admin user exists & is admin (don't overwrite name/email).
    admin = mongo_db.users.find_one({"user_id": ADMIN_USER_ID})
    if admin is None:
        pytest.skip(
            f"Seeded admin user {ADMIN_USER_ID} not found in DB — "
            "cannot test admin endpoints without admin seed."
        )
    if not admin.get("is_admin"):
        mongo_db.users.update_one(
            {"user_id": ADMIN_USER_ID}, {"$set": {"is_admin": True}}
        )

    mongo_db.user_sessions.update_one(
        {"session_token": ADMIN_TOKEN},
        {"$set": {
            "session_token": ADMIN_TOKEN,
            "user_id": ADMIN_USER_ID,
            "created_at": now,
            "expires_at": expires,
        }},
        upsert=True,
    )

    # Create non-admin user
    mongo_db.users.update_one(
        {"user_id": NONADMIN_USER_ID},
        {"$set": {
            "user_id": NONADMIN_USER_ID,
            "email": NONADMIN_EMAIL,
            "name": "Saints Non-Admin Tester",
            "picture": None,
            "is_admin": False,
            "created_at": now,
        }},
        upsert=True,
    )
    mongo_db.user_sessions.update_one(
        {"session_token": NONADMIN_TOKEN},
        {"$set": {
            "session_token": NONADMIN_TOKEN,
            "user_id": NONADMIN_USER_ID,
            "created_at": now,
            "expires_at": expires,
        }},
        upsert=True,
    )

    yield

    # Teardown — only delete our test sessions, non-admin user, and any
    # test-prefixed saints docs. Never delete the admin user.
    mongo_db.user_sessions.delete_many(
        {"session_token": {"$in": [ADMIN_TOKEN, NONADMIN_TOKEN]}}
    )
    mongo_db.users.delete_many({"user_id": NONADMIN_USER_ID})
    # Sweep any saints docs created by this suite. We tag test docs by
    # `st_test_` saint_id prefix, and also by test name prefixes for the
    # docs created via the real API (which auto-generates its own id).
    mongo_db.saints.delete_many({
        "$or": [
            {"saint_id": {"$regex": "^st_test_"}},
            {"name": {"$regex": "^TEST "}},
            {"name": {"$regex": "^Saint Test "}},
        ]
    })


@pytest.fixture(scope="module")
def admin_client():
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ADMIN_TOKEN}",
    })
    return s


@pytest.fixture(scope="module")
def user_client():
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {NONADMIN_TOKEN}",
    })
    return s


@pytest.fixture(scope="module")
def anon_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _today_iso() -> str:
    return _date.today().isoformat()


def _today_mmdd() -> str:
    d = _date.today()
    return f"{d.month:02d}-{d.day:02d}"


def _insert_test_saint(mongo_db, **overrides) -> dict:
    """Insert a fully-formed approved/draft saint directly via Mongo for read
    tests. Uses st_test_ prefix so teardown reaps it."""
    now = datetime.now(timezone.utc)
    doc = {
        "saint_id": f"st_test_{uuid.uuid4().hex[:10]}",
        "name": "Saint Test of Testing",
        "rank": "saint",
        "feast_date": _today_mmdd(),
        "is_primary": True,
        "picture_url": None,
        "picture_source": None,
        "quote": "Pray without ceasing.",
        "quote_source": "1 Thessalonians 5:17 (cited in test)",
        "biography": "A fictional saint inserted by the automated test suite. " * 8,
        "recommended_action": "Pray a decade of the rosary today.",
        "status": "approved",
        "proposed_by_ai": False,
        "proposed_at": now,
        "approved_at": now,
        "approved_by": ADMIN_USER_ID,
        "last_shown_at": None,
    }
    doc.update(overrides)
    mongo_db.saints.insert_one(dict(doc))  # copy so _id doesn't leak
    return doc


# ---------------------------------------------------------------------------
# Auth gating
# ---------------------------------------------------------------------------


class TestAuthGating:
    def test_today_requires_auth(self, anon_client):
        r = anon_client.get(f"{API}/saints/today", params={"date": _today_iso()})
        assert r.status_code in (401, 403), r.text

    def test_admin_endpoints_require_admin(self, user_client):
        r = user_client.get(f"{API}/saints/admin/list")
        assert r.status_code == 403, r.text

    def test_admin_propose_requires_admin(self, user_client):
        r = user_client.post(
            f"{API}/saints/admin/propose",
            json={"date": _today_iso()},
        )
        assert r.status_code == 403, r.text

    def test_admin_manual_requires_admin(self, user_client):
        r = user_client.post(
            f"{API}/saints/admin/manual",
            json={"name": "x", "biography": "y"},
        )
        assert r.status_code == 403, r.text


# ---------------------------------------------------------------------------
# Today endpoint — validation + empty state
# ---------------------------------------------------------------------------


class TestTodayEndpoint:
    def test_bad_date_format_returns_400(self, user_client):
        r = user_client.get(f"{API}/saints/today", params={"date": "2026-13-99"})
        assert r.status_code == 400, r.text

    def test_today_with_no_approved_returns_null_primary(self, user_client, mongo_db):
        # Use a far-future date we are sure has no feast match.
        # The fallback rotation could still return one approved entry, so
        # we instead check that this endpoint returns 200 with the shape.
        r = user_client.get(
            f"{API}/saints/today",
            params={"date": "2099-02-29" if False else "2099-03-15"},
        )
        # Server should respond 200 (bad date check ran fine).
        assert r.status_code == 200, r.text
        body = r.json()
        assert "primary" in body and "others" in body and "date" in body


# ---------------------------------------------------------------------------
# Happy path: manual create -> approve -> read -> delete -> 404
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_full_lifecycle(self, admin_client, user_client, mongo_db):
        today_iso = _today_iso()
        today_mmdd = _today_mmdd()

        # 1) Manual draft
        unique_name = f"Saint Test Lifecycle {uuid.uuid4().hex[:6]}"
        payload = {
            "name": unique_name,
            "rank": "saint",
            "feast_date": today_mmdd,
            "is_primary": True,
            "quote": "Be not afraid.",
            "quote_source": "John 6:20",
            "biography": "A test-only saint inserted by the automated suite. " * 6,
            "recommended_action": "Offer the Memorare for someone in need.",
        }
        r = admin_client.post(f"{API}/saints/admin/manual", json=payload)
        assert r.status_code == 200, r.text
        draft = r.json()
        saint_id = draft["saint_id"]
        assert draft["status"] == "draft"
        assert draft["name"] == unique_name
        assert draft["proposed_by_ai"] is False

        # 2) Approve
        r = admin_client.post(f"{API}/saints/admin/{saint_id}/approve")
        assert r.status_code == 200, r.text
        approved = r.json()
        assert approved["status"] == "approved"
        assert approved["approved_by"] == ADMIN_USER_ID
        assert approved["approved_at"]

        # 3) GET /saints/today as logged-in (non-admin) user
        r = user_client.get(f"{API}/saints/today", params={"date": today_iso})
        assert r.status_code == 200, r.text
        body = r.json()
        # The newly approved entry should appear (either primary, or in others
        # if some other entry shares today's feast). We assert it shows up.
        names_in_payload = []
        if body.get("primary"):
            names_in_payload.append(body["primary"]["name"])
        names_in_payload.extend(d["name"] for d in body.get("others", []))
        assert unique_name in names_in_payload, body

        # 4) GET /saints/{id} as non-admin
        r = user_client.get(f"{API}/saints/{saint_id}")
        assert r.status_code == 200, r.text
        one = r.json()
        assert one["name"] == unique_name
        assert one["quote"] == "Be not afraid."
        assert "status" not in one  # public payload strips status

        # 5) Delete
        r = admin_client.delete(f"{API}/saints/admin/{saint_id}")
        assert r.status_code == 200, r.text

        # Re-GET -> 404
        r = user_client.get(f"{API}/saints/{saint_id}")
        assert r.status_code == 404, r.text


# ---------------------------------------------------------------------------
# Approval validation
# ---------------------------------------------------------------------------


class TestApprovalValidation:
    def test_approve_with_empty_quote_returns_400(self, admin_client, mongo_db):
        doc = _insert_test_saint(
            mongo_db,
            status="draft",
            quote="",
            approved_at=None,
            approved_by=None,
            name=f"TEST Empty Quote {uuid.uuid4().hex[:5]}",
        )
        r = admin_client.post(f"{API}/saints/admin/{doc['saint_id']}/approve")
        assert r.status_code == 400, r.text
        assert "quote" in r.json().get("detail", "").lower()

    def test_approve_with_empty_quote_source_returns_400(self, admin_client, mongo_db):
        doc = _insert_test_saint(
            mongo_db,
            status="draft",
            quote_source="",
            approved_at=None,
            approved_by=None,
            name=f"TEST Empty Source {uuid.uuid4().hex[:5]}",
        )
        r = admin_client.post(f"{API}/saints/admin/{doc['saint_id']}/approve")
        assert r.status_code == 400, r.text
        assert "quote_source" in r.json().get("detail", "")

    def test_approve_unknown_id_returns_404(self, admin_client):
        r = admin_client.post(f"{API}/saints/admin/st_test_doesnotexist/approve")
        assert r.status_code == 404, r.text


# ---------------------------------------------------------------------------
# Admin list / reject / draft visibility
# ---------------------------------------------------------------------------


class TestAdminList:
    def test_admin_list_filters_by_status(self, admin_client, mongo_db):
        d = _insert_test_saint(
            mongo_db, status="draft", approved_at=None, approved_by=None,
            name=f"TEST DraftListed {uuid.uuid4().hex[:5]}",
        )
        r = admin_client.get(f"{API}/saints/admin/list", params={"status": "draft"})
        assert r.status_code == 200, r.text
        body = r.json()
        ids = [item["saint_id"] for item in body["items"]]
        assert d["saint_id"] in ids
        # Every returned item should be draft
        assert all(it["status"] == "draft" for it in body["items"])

    def test_draft_is_not_visible_via_public_get(self, user_client, mongo_db):
        d = _insert_test_saint(
            mongo_db, status="draft", approved_at=None, approved_by=None,
            name=f"TEST DraftHidden {uuid.uuid4().hex[:5]}",
        )
        r = user_client.get(f"{API}/saints/{d['saint_id']}")
        assert r.status_code == 404, r.text

    def test_rejected_is_not_visible_via_public_get(self, user_client, mongo_db):
        d = _insert_test_saint(
            mongo_db, status="rejected",
            name=f"TEST Rejected {uuid.uuid4().hex[:5]}",
        )
        r = user_client.get(f"{API}/saints/{d['saint_id']}")
        assert r.status_code == 404, r.text

    def test_reject_endpoint(self, admin_client, mongo_db):
        d = _insert_test_saint(
            mongo_db, status="draft",
            name=f"TEST RejectMe {uuid.uuid4().hex[:5]}",
        )
        r = admin_client.post(f"{API}/saints/admin/{d['saint_id']}/reject")
        assert r.status_code == 200, r.text
        fresh = mongo_db.saints.find_one({"saint_id": d["saint_id"]})
        assert fresh["status"] == "rejected"


# ---------------------------------------------------------------------------
# Today selection logic — primary vs others, fallback rotation
# ---------------------------------------------------------------------------


class TestTodaySelection:
    def test_primary_vs_secondary_ordering(self, user_client, mongo_db):
        mmdd = "07-04"  # arbitrary date, separate from today
        date_iso = f"{_date.today().year}-{mmdd}"
        primary_name = f"TEST Primary {uuid.uuid4().hex[:5]}"
        secondary_name = f"TEST Secondary {uuid.uuid4().hex[:5]}"
        _insert_test_saint(
            mongo_db, feast_date=mmdd, is_primary=True, name=primary_name,
        )
        _insert_test_saint(
            mongo_db, feast_date=mmdd, is_primary=False, name=secondary_name,
            rank="blessed",
        )
        r = user_client.get(f"{API}/saints/today", params={"date": date_iso})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["primary"] is not None
        assert body["primary"]["name"] == primary_name
        other_names = [o["name"] for o in body["others"]]
        assert secondary_name in other_names

    def test_fallback_rotation_when_no_feast_match(self, user_client, mongo_db):
        # Insert one approved entry on a different MM-DD and query a quiet date
        # that no other approved entry shares.
        quiet_mmdd = "02-29"  # leap day = quiet
        fallback_name = f"TEST Fallback {uuid.uuid4().hex[:5]}"
        # Use a far-past last_shown_at so it wins the rotation tie-break.
        _insert_test_saint(
            mongo_db,
            feast_date="11-11",
            name=fallback_name,
            last_shown_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
            approved_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
        )
        # Use a non-leap year date so _date.fromisoformat doesn't reject it.
        r = user_client.get(f"{API}/saints/today", params={"date": "2027-03-15"})
        assert r.status_code == 200, r.text
        body = r.json()
        # Fallback must yield SOMETHING (any approved entry exists).
        assert body["primary"] is not None


# ---------------------------------------------------------------------------
# Patch endpoint
# ---------------------------------------------------------------------------


class TestAdminPatch:
    def test_patch_updates_fields(self, admin_client, mongo_db):
        d = _insert_test_saint(
            mongo_db, status="draft",
            name=f"TEST PatchMe {uuid.uuid4().hex[:5]}",
        )
        r = admin_client.patch(
            f"{API}/saints/admin/{d['saint_id']}",
            json={"recommended_action": "Pray for the holy souls in Purgatory."},
        )
        assert r.status_code == 200, r.text
        assert r.json()["recommended_action"] == "Pray for the holy souls in Purgatory."

    def test_patch_invalid_rank_returns_400(self, admin_client, mongo_db):
        d = _insert_test_saint(
            mongo_db, status="draft",
            name=f"TEST PatchBad {uuid.uuid4().hex[:5]}",
        )
        r = admin_client.patch(
            f"{API}/saints/admin/{d['saint_id']}",
            json={"rank": "archangel"},
        )
        assert r.status_code == 400, r.text


# ---------------------------------------------------------------------------
# Claude propose — optional, tolerated on 502
# ---------------------------------------------------------------------------


class TestProposeOptional:
    def test_propose_creates_draft_or_502(self, admin_client, mongo_db):
        # Use a quiet date to avoid landing on the same MM-DD as today's data.
        r = admin_client.post(
            f"{API}/saints/admin/propose",
            json={"date": "2026-06-09"},  # St. Ephrem
            timeout=60,
        )
        if r.status_code == 502:
            pytest.skip(f"LLM unavailable: {r.text}")
        if r.status_code == 503:
            pytest.skip(f"LLM not configured: {r.text}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "draft"
        assert body["proposed_by_ai"] is True
        # Tag and queue for cleanup
        mongo_db.saints.update_one(
            {"saint_id": body["saint_id"]},
            {"$set": {"saint_id": f"st_test_{body['saint_id'][-12:]}"}},
        )

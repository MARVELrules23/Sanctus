"""Backend tests for the Sanctus Charity Hub feature.

Covers:
* Auth gating (401 unauth, 403 non-admin on admin endpoints)
* Non-admin submission -> pending; Admin submission -> auto-approved
* Public listing (only approved), search, category & state filters
* Get detail (pending visible only to submitter/admin)
* Claim flow (pending, idempotent, 409 if claimed by other)
* Contact "I'm interested" creates record
* Admin list / approve / reject
* Approving a claim sets `claimed_by` and supersedes other pending claims
* Duplicate prevention (same name + city)
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or ""
).rstrip("/")
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL/EXPO_BACKEND_URL must be set"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

ADMIN_EMAIL = "philipwils13@gmail.com"
ADMIN_USER_ID = "user_ade7a898e281"

# Test id markers (used for cleanup)
TEST_RUN = uuid.uuid4().hex[:6]
NAME_PREFIX = f"TEST_QA_{TEST_RUN}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db():
    cli = MongoClient(MONGO_URL)
    d = cli[DB_NAME]
    yield d
    # Cleanup created by NAME_PREFIX
    created = list(d.charities.find({"name": {"$regex": f"^{NAME_PREFIX}"}}, {"charity_id": 1}))
    cids = [c["charity_id"] for c in created]
    if cids:
        d.charities.delete_many({"charity_id": {"$in": cids}})
        d.charity_claims.delete_many({"charity_id": {"$in": cids}})
        d.charity_contacts.delete_many({"charity_id": {"$in": cids}})
    cli.close()


@pytest.fixture(scope="module")
def admin_token(db):
    token = f"TEST_admin_{uuid.uuid4().hex}"
    db.user_sessions.insert_one({
        "session_token": token,
        "user_id": ADMIN_USER_ID,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
    })
    db.users.update_one({"user_id": ADMIN_USER_ID}, {"$set": {"is_admin": True}})
    yield token
    db.user_sessions.delete_one({"session_token": token})


def _mk_user(db, label):
    user_id = f"TEST_charity_{label}_{uuid.uuid4().hex[:8]}"
    token = f"TEST_token_{label}_{uuid.uuid4().hex}"
    db.users.insert_one({
        "user_id": user_id,
        "email": f"{user_id}@test.sanctus.app",
        "name": f"Test User {label}",
        "is_admin": False,
        "created_at": datetime.now(timezone.utc),
    })
    db.user_sessions.insert_one({
        "session_token": token,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
    })
    return {"user_id": user_id, "token": token}


@pytest.fixture(scope="module")
def user_a(db):
    u = _mk_user(db, "A")
    yield u
    db.user_sessions.delete_many({"user_id": u["user_id"]})
    db.users.delete_many({"user_id": u["user_id"]})
    db.charity_claims.delete_many({"user_id": u["user_id"]})
    db.charity_contacts.delete_many({"user_id": u["user_id"]})


@pytest.fixture(scope="module")
def user_b(db):
    u = _mk_user(db, "B")
    yield u
    db.user_sessions.delete_many({"user_id": u["user_id"]})
    db.users.delete_many({"user_id": u["user_id"]})
    db.charity_claims.delete_many({"user_id": u["user_id"]})
    db.charity_contacts.delete_many({"user_id": u["user_id"]})


def _auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Auth gating
# ---------------------------------------------------------------------------

class TestAuthGating:
    def test_list_unauth(self):
        r = requests.get(f"{BASE_URL}/api/charities")
        assert r.status_code == 401

    def test_submit_unauth(self):
        r = requests.post(f"{BASE_URL}/api/charities/submit", json={
            "name": "x", "mission": "y" * 20,
        })
        assert r.status_code == 401

    def test_admin_list_unauth(self):
        r = requests.get(f"{BASE_URL}/api/charities/admin/list")
        assert r.status_code == 401

    def test_admin_list_forbidden_for_normal_user(self, user_a):
        r = requests.get(f"{BASE_URL}/api/charities/admin/list", headers=_auth(user_a["token"]))
        assert r.status_code == 403

    def test_admin_approve_forbidden_for_normal_user(self, user_a):
        r = requests.post(f"{BASE_URL}/api/charities/admin/somefakeid/approve", headers=_auth(user_a["token"]))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Submission & status behavior
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pending_charity(user_a):
    """Non-admin submission -> pending."""
    payload = {
        "name": f"{NAME_PREFIX} Pending House",
        "mission": "Helps those in need of food and shelter daily.",
        "category": "food_bank",
        "city": "San Francisco",
        "state": "CA",
        "country": "US",
        "website": "example.org",
        "email": "info@example.org",
        "phone": "+1-555-0100",
    }
    r = requests.post(f"{BASE_URL}/api/charities/submit", json=payload, headers=_auth(user_a["token"]))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "pending"
    assert data["name"] == payload["name"]
    assert data["category"] == "food_bank"
    assert data["website"] == "https://example.org"
    assert data["charity_id"].startswith("chr_")
    return data


@pytest.fixture(scope="module")
def approved_charity(admin_token):
    """Admin submission -> auto-approved."""
    payload = {
        "name": f"{NAME_PREFIX} Approved Mission",
        "mission": "Catholic mission supporting children and elderly globally.",
        "category": "missions",
        "city": "Boston",
        "state": "MA",
        "country": "US",
    }
    r = requests.post(f"{BASE_URL}/api/charities/submit", json=payload, headers=_auth(admin_token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "approved"
    assert data["charity_id"].startswith("chr_")
    return data


class TestSubmission:
    def test_non_admin_pending(self, pending_charity):
        assert pending_charity["status"] == "pending"

    def test_admin_auto_approved(self, approved_charity):
        assert approved_charity["status"] == "approved"

    def test_duplicate_name_city_pending_returns_409(self, user_a, pending_charity):
        payload = {
            "name": pending_charity["name"],
            "mission": "Another mission text with enough length to pass.",
            "city": "San Francisco",
            "state": "CA",
        }
        r = requests.post(f"{BASE_URL}/api/charities/submit", json=payload, headers=_auth(user_a["token"]))
        assert r.status_code == 409, r.text

    def test_validation_short_mission(self, user_a):
        payload = {"name": f"{NAME_PREFIX} short", "mission": "x"}
        r = requests.post(f"{BASE_URL}/api/charities/submit", json=payload, headers=_auth(user_a["token"]))
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Public listing
# ---------------------------------------------------------------------------

class TestPublicListing:
    def test_list_only_approved(self, user_a, approved_charity, pending_charity):
        r = requests.get(f"{BASE_URL}/api/charities", headers=_auth(user_a["token"]))
        assert r.status_code == 200
        data = r.json()
        ids = [c["charity_id"] for c in data["items"]]
        assert approved_charity["charity_id"] in ids
        assert pending_charity["charity_id"] not in ids
        assert "categories" in data

    def test_search_query(self, user_a, approved_charity):
        r = requests.get(f"{BASE_URL}/api/charities", headers=_auth(user_a["token"]),
                         params={"q": "Approved Mission"})
        assert r.status_code == 200
        ids = [c["charity_id"] for c in r.json()["items"]]
        assert approved_charity["charity_id"] in ids

    def test_filter_category(self, user_a, approved_charity):
        r = requests.get(f"{BASE_URL}/api/charities", headers=_auth(user_a["token"]),
                         params={"category": "missions"})
        assert r.status_code == 200
        for c in r.json()["items"]:
            assert c["category"] == "missions"

    def test_filter_state(self, user_a, approved_charity):
        r = requests.get(f"{BASE_URL}/api/charities", headers=_auth(user_a["token"]),
                         params={"state": "MA"})
        assert r.status_code == 200
        for c in r.json()["items"]:
            assert c["state"].upper() == "MA"

    def test_categories_endpoint(self, user_a):
        r = requests.get(f"{BASE_URL}/api/charities/categories", headers=_auth(user_a["token"]))
        assert r.status_code == 200
        cats = r.json()["categories"]
        keys = {c["key"] for c in cats}
        assert "food_bank" in keys and "general" in keys


# ---------------------------------------------------------------------------
# Get detail visibility (pending hidden unless submitter/admin)
# ---------------------------------------------------------------------------

class TestDetailVisibility:
    def test_pending_404_for_other_user(self, user_b, pending_charity):
        r = requests.get(f"{BASE_URL}/api/charities/{pending_charity['charity_id']}",
                         headers=_auth(user_b["token"]))
        assert r.status_code == 404

    def test_pending_visible_to_submitter(self, user_a, pending_charity):
        r = requests.get(f"{BASE_URL}/api/charities/{pending_charity['charity_id']}",
                         headers=_auth(user_a["token"]))
        assert r.status_code == 200
        assert r.json()["charity_id"] == pending_charity["charity_id"]

    def test_pending_visible_to_admin(self, admin_token, pending_charity):
        r = requests.get(f"{BASE_URL}/api/charities/{pending_charity['charity_id']}",
                         headers=_auth(admin_token))
        assert r.status_code == 200

    def test_unknown_404(self, user_a):
        r = requests.get(f"{BASE_URL}/api/charities/chr_does_not_exist",
                         headers=_auth(user_a["token"]))
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Claim flow
# ---------------------------------------------------------------------------

class TestClaim:
    def test_claim_pending_charity_404(self, user_a, pending_charity):
        r = requests.post(
            f"{BASE_URL}/api/charities/{pending_charity['charity_id']}/claim",
            json={"message": "ours"}, headers=_auth(user_a["token"]),
        )
        assert r.status_code == 404

    def test_claim_idempotent_for_same_user(self, user_a, approved_charity):
        r1 = requests.post(
            f"{BASE_URL}/api/charities/{approved_charity['charity_id']}/claim",
            json={"message": "parish rep"}, headers=_auth(user_a["token"]),
        )
        assert r1.status_code == 200, r1.text
        cid1 = r1.json()["claim_id"]
        r2 = requests.post(
            f"{BASE_URL}/api/charities/{approved_charity['charity_id']}/claim",
            json={"message": "again"}, headers=_auth(user_a["token"]),
        )
        assert r2.status_code == 200
        assert r2.json()["claim_id"] == cid1


# ---------------------------------------------------------------------------
# Contact "I'm interested"
# ---------------------------------------------------------------------------

class TestContact:
    def test_contact_creates_record(self, db, user_b, approved_charity):
        r = requests.post(
            f"{BASE_URL}/api/charities/{approved_charity['charity_id']}/contact",
            json={"message": "I want to volunteer Saturdays."},
            headers=_auth(user_b["token"]),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["contact_id"].startswith("cnt_")
        # Persistence check
        rec = db.charity_contacts.find_one({"contact_id": body["contact_id"]})
        assert rec is not None
        assert rec["user_id"] == user_b["user_id"]

    def test_contact_pending_404(self, user_b, pending_charity):
        r = requests.post(
            f"{BASE_URL}/api/charities/{pending_charity['charity_id']}/contact",
            json={"message": "interested"}, headers=_auth(user_b["token"]),
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Admin list / approve / reject
# ---------------------------------------------------------------------------

class TestAdminFlow:
    def test_admin_list_pending(self, admin_token, pending_charity):
        r = requests.get(f"{BASE_URL}/api/charities/admin/list",
                         headers=_auth(admin_token), params={"status": "pending"})
        assert r.status_code == 200
        ids = [c["charity_id"] for c in r.json()["items"]]
        assert pending_charity["charity_id"] in ids

    def test_admin_approve_then_public_list(self, db, admin_token, user_a, pending_charity):
        r = requests.post(
            f"{BASE_URL}/api/charities/admin/{pending_charity['charity_id']}/approve",
            headers=_auth(admin_token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "approved"

        # Now it shows in public list
        r2 = requests.get(f"{BASE_URL}/api/charities", headers=_auth(user_a["token"]),
                          params={"q": pending_charity["name"]})
        assert r2.status_code == 200
        ids = [c["charity_id"] for c in r2.json()["items"]]
        assert pending_charity["charity_id"] in ids

    def test_admin_reject_creates_rejected(self, db, admin_token, user_a):
        # Create new pending then reject it
        payload = {
            "name": f"{NAME_PREFIX} Reject Me",
            "mission": "A charity that will be rejected by admin.",
            "city": "Austin",
            "state": "TX",
        }
        s = requests.post(f"{BASE_URL}/api/charities/submit", json=payload,
                          headers=_auth(user_a["token"]))
        assert s.status_code == 200
        cid = s.json()["charity_id"]
        r = requests.post(f"{BASE_URL}/api/charities/admin/{cid}/reject",
                          headers=_auth(admin_token))
        assert r.status_code == 200
        doc = db.charities.find_one({"charity_id": cid})
        assert doc["status"] == "rejected"


# ---------------------------------------------------------------------------
# Admin claim approval supersedes other pending claims
# ---------------------------------------------------------------------------

class TestAdminClaimApproval:
    def test_approve_claim_sets_claimed_by_and_supersedes_others(
        self, db, admin_token, user_a, user_b
    ):
        # Create a fresh approved charity (admin submission)
        payload = {
            "name": f"{NAME_PREFIX} Claim Target",
            "mission": "A claim target charity for testing claim approval flow.",
            "city": "Denver",
            "state": "CO",
        }
        s = requests.post(f"{BASE_URL}/api/charities/submit", json=payload, headers=_auth(admin_token))
        assert s.status_code == 200
        cid = s.json()["charity_id"]

        # Two users claim it
        r_a = requests.post(f"{BASE_URL}/api/charities/{cid}/claim", json={"message": "I'm the rep"},
                            headers=_auth(user_a["token"]))
        assert r_a.status_code == 200
        claim_a = r_a.json()["claim_id"]
        r_b = requests.post(f"{BASE_URL}/api/charities/{cid}/claim", json={"message": "actually me"},
                            headers=_auth(user_b["token"]))
        assert r_b.status_code == 200
        claim_b = r_b.json()["claim_id"]

        # Admin approves user_a's claim
        ap = requests.post(f"{BASE_URL}/api/charities/admin/claims/{claim_a}/approve",
                           headers=_auth(admin_token))
        assert ap.status_code == 200

        # charity.claimed_by == user_a
        ch = db.charities.find_one({"charity_id": cid})
        assert ch["claimed_by"] == user_a["user_id"]

        # claim_b should now be superseded
        cb = db.charity_claims.find_one({"claim_id": claim_b})
        assert cb["status"] == "superseded"

    def test_claim_after_claimed_returns_409(self, db, admin_token, user_a, user_b):
        # Build claimed scenario
        payload = {
            "name": f"{NAME_PREFIX} Already Claimed",
            "mission": "Charity to test 409 already-claimed flow.",
            "city": "Seattle",
            "state": "WA",
        }
        s = requests.post(f"{BASE_URL}/api/charities/submit", json=payload, headers=_auth(admin_token))
        cid = s.json()["charity_id"]
        # user_a claims
        ra = requests.post(f"{BASE_URL}/api/charities/{cid}/claim", json={"message": "me"},
                           headers=_auth(user_a["token"]))
        claim_a = ra.json()["claim_id"]
        # admin approves
        requests.post(f"{BASE_URL}/api/charities/admin/claims/{claim_a}/approve",
                      headers=_auth(admin_token))
        # user_b now tries to claim -> 409
        rb = requests.post(f"{BASE_URL}/api/charities/{cid}/claim", json={"message": "no me"},
                           headers=_auth(user_b["token"]))
        assert rb.status_code == 409

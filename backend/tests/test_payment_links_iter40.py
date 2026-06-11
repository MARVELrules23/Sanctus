"""Iteration 40 — Sanctus Premium Stripe Payment Link refactor.

Validates the refactor in `/app/backend/subscriptions.py` that prefers
hosted Stripe Payment Links over dynamic Checkout Sessions.

Environment assumption: STRIPE_API_KEY is the placeholder `sk_test_emergent`
(SDK NOT ready) but Payment Links ARE configured (defaults).

What we verify:
  1. GET /api/subscriptions/status returns the new payment_links flag and
     `checkout_ready`/`stripe_ready` (legacy alias) are now both true even
     though `portal_ready` is false.
  2. POST /api/subscriptions/create-checkout-session returns a Payment Link
     URL (not a Stripe Checkout Session URL) with `client_reference_id` and
     `prefilled_email` query params appended.
  3. The Mongo user document is annotated with `stripe.last_plan_selected`
     and `stripe.last_checkout_kind == "payment_link"`.
  4. /customer-portal still returns 503 (needs real STRIPE_API_KEY).
  5. /webhook still returns 503 (needs real STRIPE_API_KEY).
  6. Pydantic validation rejects bad plans / bad return_origin (422).
  7. Premium gating regressions are unchanged.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

# ----------------------------------------------------------------------
# Setup — load env from backend/.env to find Mongo + base URL
# ----------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = (
    os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or os.environ.get("EXPO_BACKEND_URL")
    or "http://localhost:8001"
).rstrip("/")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

ADMIN_TOKEN = "test_premium_2453a541f1e0982d"
FREE_TOKEN = "test_nonadmin_7c1ac6ad1df64b42"
ADMIN_USER_ID = "user_ade7a898e281"
ADMIN_EMAIL = "philipwils13@gmail.com"
NONADMIN_USER_ID = "user_test_nonadmin_001"
NONADMIN_EMAIL = "nonadmin@example.com"

PAYMENT_LINK_MONTHLY = "https://buy.stripe.com/bJe6oG3XJbE0gnw31fb7y00"
PAYMENT_LINK_ANNUAL = "https://buy.stripe.com/dRm4gyam7dM8b3c45jb7y01"


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
def H(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def mongo_db():
    cli = MongoClient(MONGO_URL)
    yield cli[DB_NAME]
    cli.close()


@pytest.fixture(scope="module", autouse=True)
def refresh_sessions(mongo_db):
    """Make sure the pre-minted admin + non-admin sessions exist with a
    future expires_at on every test run, so the suite is rerunnable.

    Idempotent — uses update_one(..., upsert=True).
    """
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=4)

    mongo_db.user_sessions.update_one(
        {"session_token": ADMIN_TOKEN},
        {"$set": {
            "session_token": ADMIN_TOKEN,
            "user_id": ADMIN_USER_ID,
            "created_at": now,
            "expires_at": future,
        }},
        upsert=True,
    )
    mongo_db.user_sessions.update_one(
        {"session_token": FREE_TOKEN},
        {"$set": {
            "session_token": FREE_TOKEN,
            "user_id": NONADMIN_USER_ID,
            "created_at": now,
            "expires_at": future,
        }},
        upsert=True,
    )

    # Ensure non-admin user exists with the expected email
    mongo_db.users.update_one(
        {"user_id": NONADMIN_USER_ID},
        {"$setOnInsert": {
            "user_id": NONADMIN_USER_ID,
            "email": NONADMIN_EMAIL,
            "name": "Non Admin",
            "is_admin": False,
            "created_at": now,
        }},
        upsert=True,
    )
    yield


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers["Content-Type"] = "application/json"
    return sess


# ----------------------------------------------------------------------
# 1. GET /api/subscriptions/status
# ----------------------------------------------------------------------
class TestSubscriptionsStatus:
    def test_admin_status(self, s):
        r = s.get(f"{BASE_URL}/api/subscriptions/status", headers=H(ADMIN_TOKEN))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_premium"] is True
        assert d["is_admin_premium"] is True
        assert d["checkout_ready"] is True, d
        assert d["stripe_ready"] is True, d  # legacy alias now == checkout_ready
        assert d["payment_links"] is True, d
        assert d["portal_ready"] is False, d
        assert d["trial_days"] == 7
        assert d["pricing"]["monthly"]["amount_cents"] == 499
        assert d["pricing"]["annual"]["amount_cents"] == 3999

    def test_nonadmin_status(self, s):
        r = s.get(f"{BASE_URL}/api/subscriptions/status", headers=H(FREE_TOKEN))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_premium"] is False
        assert d["is_admin_premium"] is False
        assert d["checkout_ready"] is True, d
        assert d["payment_links"] is True, d
        assert d["stripe_ready"] is True, d
        assert d["portal_ready"] is False, d

    def test_unauth_status_401(self, s):
        r = s.get(f"{BASE_URL}/api/subscriptions/status")
        assert r.status_code == 401, r.text


# ----------------------------------------------------------------------
# 2. POST /api/subscriptions/create-checkout-session
# ----------------------------------------------------------------------
class TestCreateCheckoutSession:
    def _assert_payment_link(self, body, expected_base, expected_user_id):
        assert body["kind"] == "payment_link", body
        assert body["session_id"] is None, body
        url = body["url"]
        assert url, body
        # Must start with the configured Payment Link
        assert url.startswith(expected_base), f"URL did not start with {expected_base}: {url}"
        # Query params
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        assert qs.get("client_reference_id") == [expected_user_id], qs
        # `prefilled_email` must be present (even if empty after strip,
        # implementation skips empty — but our non-admin has nonadmin@example.com)
        assert "prefilled_email" in qs, qs

    def test_nonadmin_monthly_returns_payment_link(self, s):
        r = s.post(
            f"{BASE_URL}/api/subscriptions/create-checkout-session",
            headers=H(FREE_TOKEN),
            json={"plan": "monthly", "return_origin": "https://example.com"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["plan"] == "monthly"
        self._assert_payment_link(d, PAYMENT_LINK_MONTHLY, NONADMIN_USER_ID)
        # prefilled_email should equal the non-admin's email
        qs = parse_qs(urlparse(d["url"]).query)
        assert qs.get("prefilled_email") == [NONADMIN_EMAIL], qs

    def test_nonadmin_annual_returns_payment_link(self, s):
        r = s.post(
            f"{BASE_URL}/api/subscriptions/create-checkout-session",
            headers=H(FREE_TOKEN),
            json={"plan": "annual", "return_origin": "https://example.com"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["plan"] == "annual"
        self._assert_payment_link(d, PAYMENT_LINK_ANNUAL, NONADMIN_USER_ID)

    def test_admin_short_circuits_already_premium(self, s):
        r = s.post(
            f"{BASE_URL}/api/subscriptions/create-checkout-session",
            headers=H(ADMIN_TOKEN),
            json={"plan": "monthly", "return_origin": "https://example.com"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("already_premium") is True, d
        assert d.get("url") is None, d

    def test_invalid_plan_422(self, s):
        r = s.post(
            f"{BASE_URL}/api/subscriptions/create-checkout-session",
            headers=H(FREE_TOKEN),
            json={"plan": "weekly", "return_origin": "https://example.com"},
        )
        assert r.status_code == 422, r.text

    def test_invalid_return_origin_422(self, s):
        r = s.post(
            f"{BASE_URL}/api/subscriptions/create-checkout-session",
            headers=H(FREE_TOKEN),
            json={"plan": "monthly", "return_origin": "not-a-url"},
        )
        assert r.status_code == 422, r.text

    def test_unauth_401(self, s):
        r = s.post(
            f"{BASE_URL}/api/subscriptions/create-checkout-session",
            json={"plan": "monthly", "return_origin": "https://example.com"},
        )
        assert r.status_code == 401, r.text


# ----------------------------------------------------------------------
# 3. Mongo annotation after successful checkout call
# ----------------------------------------------------------------------
class TestMongoAnnotation:
    def test_user_doc_annotated_after_checkout(self, s, mongo_db):
        # Trigger annual checkout so we can assert "annual"
        r = s.post(
            f"{BASE_URL}/api/subscriptions/create-checkout-session",
            headers=H(FREE_TOKEN),
            json={"plan": "annual", "return_origin": "https://example.com"},
        )
        assert r.status_code == 200, r.text
        doc = mongo_db.users.find_one({"user_id": NONADMIN_USER_ID}, {"_id": 0})
        assert doc is not None
        stripe_block = doc.get("stripe") or {}
        assert stripe_block.get("last_plan_selected") == "annual", stripe_block
        assert stripe_block.get("last_checkout_kind") == "payment_link", stripe_block

        # Re-trigger monthly and confirm overwrite
        r = s.post(
            f"{BASE_URL}/api/subscriptions/create-checkout-session",
            headers=H(FREE_TOKEN),
            json={"plan": "monthly", "return_origin": "https://example.com"},
        )
        assert r.status_code == 200, r.text
        doc = mongo_db.users.find_one({"user_id": NONADMIN_USER_ID}, {"_id": 0})
        stripe_block = doc.get("stripe") or {}
        assert stripe_block.get("last_plan_selected") == "monthly", stripe_block
        assert stripe_block.get("last_checkout_kind") == "payment_link", stripe_block


# ----------------------------------------------------------------------
# 4. /customer-portal still requires real STRIPE_API_KEY → 503
# ----------------------------------------------------------------------
class TestCustomerPortal:
    def test_customer_portal_503_for_nonadmin(self, s):
        r = s.post(
            f"{BASE_URL}/api/subscriptions/customer-portal",
            headers=H(FREE_TOKEN),
            json={"return_origin": "https://example.com"},
        )
        assert r.status_code == 503, r.text
        assert "not configured" in r.json().get("detail", "").lower()

    def test_customer_portal_503_for_admin(self, s):
        r = s.post(
            f"{BASE_URL}/api/subscriptions/customer-portal",
            headers=H(ADMIN_TOKEN),
            json={"return_origin": "https://example.com"},
        )
        assert r.status_code == 503, r.text


# ----------------------------------------------------------------------
# 5. Webhook 503 (Stripe not configured)
# ----------------------------------------------------------------------
class TestWebhook:
    def test_webhook_503(self, s):
        r = s.post(
            f"{BASE_URL}/api/subscriptions/webhook",
            data=b'{"type":"ping"}',
            headers={"Stripe-Signature": "t=0,v1=abc",
                     "Content-Type": "application/json"},
        )
        assert r.status_code == 503, r.text


# ----------------------------------------------------------------------
# 6. Regression — premium gating contract unchanged
# ----------------------------------------------------------------------
class TestRegression:
    def test_humanae_vitae_free(self, s):
        r = s.get(
            f"{BASE_URL}/api/library/books/humanae-vitae/chapters/0",
            headers=H(FREE_TOKEN),
        )
        assert r.status_code == 200, r.text

    def test_confessions_paywalled_for_nonadmin(self, s):
        r = s.get(
            f"{BASE_URL}/api/library/books/confessions-augustine/chapters/0",
            headers=H(FREE_TOKEN),
        )
        assert r.status_code == 402, r.text

    def test_confessions_open_for_admin(self, s):
        r = s.get(
            f"{BASE_URL}/api/library/books/confessions-augustine/chapters/0",
            headers=H(ADMIN_TOKEN),
        )
        assert r.status_code == 200, r.text

    def test_challenge_enroll_paywalled_for_nonadmin(self, s):
        # Pull first active slug
        r = s.get(f"{BASE_URL}/api/challenges", headers=H(FREE_TOKEN))
        assert r.status_code == 200, r.text
        data = r.json()
        items = data if isinstance(data, list) else (
            data.get("items") or data.get("challenges") or []
        )
        assert items, f"no challenges to test against: {data}"
        slug = items[0]["slug"]

        r = s.post(
            f"{BASE_URL}/api/challenges/{slug}/enroll",
            headers=H(FREE_TOKEN),
        )
        assert r.status_code == 402, f"{slug} -> {r.status_code}: {r.text[:200]}"

    def test_group_dm_paywalled_for_nonadmin(self, s):
        r = s.post(
            f"{BASE_URL}/api/community/dm/threads/group",
            headers=H(FREE_TOKEN),
            json={"member_ids": [ADMIN_USER_ID], "name": "regress test grp"},
        )
        assert r.status_code == 402, r.text

    def test_auth_me_admin_premium(self, s):
        r = s.get(f"{BASE_URL}/api/auth/me", headers=H(ADMIN_TOKEN))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("is_premium") is True
        assert d.get("is_admin") is True

    def test_dm_unread_count_for_nonadmin(self, s):
        r = s.get(f"{BASE_URL}/api/community/dm/unread-count",
                  headers=H(FREE_TOKEN))
        assert r.status_code == 200, r.text
        d = r.json()
        assert "total" in d
        assert "threads" in d
        assert isinstance(d["threads"], list)

    def test_dm_unread_count_for_admin(self, s):
        r = s.get(f"{BASE_URL}/api/community/dm/unread-count",
                  headers=H(ADMIN_TOKEN))
        assert r.status_code == 200, r.text
        d = r.json()
        assert "total" in d
        assert "threads" in d

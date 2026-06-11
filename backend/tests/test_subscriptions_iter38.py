"""Iteration 38 — Stripe Recurring Subscriptions + Premium gating.

Validates:
  * /api/subscriptions/status payload + admin vs free differentiation
  * checkout/portal/webhook return 503 when STRIPE_API_KEY is placeholder
  * /api/auth/me now includes is_premium
  * Library/Challenges/Group-DM gating contract (200 vs 402)
  * Regression on pre-existing endpoints
  * 402 detail always contains "Sanctus Premium is required"
"""
from __future__ import annotations

import os
import pytest
import requests

BASE_URL = "http://localhost:8001"

ADMIN_TOKEN = "test_premium_2453a541f1e0982d"   # philipwils13@gmail.com
FREE_TOKEN = "test_nonadmin_7c1ac6ad1df64b42"   # user_test_nonadmin_001
ADMIN_USER_ID = "user_ade7a898e281"

PAPAL_FREE_SLUGS = [
    "humanae-vitae",
    "veritatis-splendor",
    "centesimus-annus",
    "evangelii-nuntiandi",
    "magnifica-humanitas",
]


def H(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers["Content-Type"] = "application/json"
    return sess


# ---------- /api/subscriptions/status ----------

class TestSubscriptionsStatus:
    def test_admin_status_is_premium_true(self, s):
        r = s.get(f"{BASE_URL}/api/subscriptions/status", headers=H(ADMIN_TOKEN))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_premium"] is True
        assert d["is_admin_premium"] is True
        assert d["stripe_ready"] is False
        assert d["trial_days"] == 7
        assert d["pricing"]["monthly"]["amount_cents"] == 499
        assert d["pricing"]["annual"]["amount_cents"] == 3999
        assert d["pricing"]["monthly"]["interval"] == "month"
        assert d["pricing"]["annual"]["interval"] == "year"

    def test_free_status_is_premium_false(self, s):
        r = s.get(f"{BASE_URL}/api/subscriptions/status", headers=H(FREE_TOKEN))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_premium"] is False
        assert d["is_admin_premium"] is False
        assert d["stripe_ready"] is False
        assert d["pricing"]["monthly"]["amount_cents"] == 499
        assert d["pricing"]["annual"]["amount_cents"] == 3999


# ---------- Stripe-config-gated endpoints (placeholder key → 503) ----------

class TestStripeGatedEndpoints:
    def test_create_checkout_503_for_free(self, s):
        r = s.post(
            f"{BASE_URL}/api/subscriptions/create-checkout-session",
            headers=H(FREE_TOKEN),
            json={"plan": "monthly", "return_origin": "http://localhost"},
        )
        assert r.status_code == 503, r.text

    def test_create_checkout_admin_already_premium(self, s):
        # Admin is_premium=True so the endpoint must short-circuit BEFORE
        # the stripe_ready check and return already_premium=True (200).
        r = s.post(
            f"{BASE_URL}/api/subscriptions/create-checkout-session",
            headers=H(ADMIN_TOKEN),
            json={"plan": "monthly", "return_origin": "http://localhost"},
        )
        # If short-circuit happens FIRST → 200 already_premium.
        # If 503 (the implementation gates by stripe_ready first), report it.
        if r.status_code == 503:
            pytest.fail(
                "Admin checkout returns 503 — admin should be short-circuited "
                "to already_premium BEFORE the Stripe-ready check."
            )
        assert r.status_code == 200, r.text
        assert r.json().get("already_premium") is True

    def test_customer_portal_503(self, s):
        r = s.post(
            f"{BASE_URL}/api/subscriptions/customer-portal",
            headers=H(FREE_TOKEN),
            json={"return_origin": "http://localhost"},
        )
        assert r.status_code == 503, r.text

    def test_webhook_503(self, s):
        # Webhook is unauthenticated; placeholder key → 503.
        r = s.post(
            f"{BASE_URL}/api/subscriptions/webhook",
            data=b"{}",
            headers={"Stripe-Signature": "t=0,v1=abc"},
        )
        assert r.status_code == 503, r.text


# ---------- /api/auth/me includes is_premium ----------

class TestAuthMePremiumField:
    def test_admin_me_is_premium_true(self, s):
        r = s.get(f"{BASE_URL}/api/auth/me", headers=H(ADMIN_TOKEN))
        assert r.status_code == 200, r.text
        d = r.json()
        assert "is_premium" in d
        assert d["is_premium"] is True
        assert d["user_id"] == ADMIN_USER_ID
        assert d.get("is_admin") is True

    def test_free_me_is_premium_false(self, s):
        r = s.get(f"{BASE_URL}/api/auth/me", headers=H(FREE_TOKEN))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("is_premium") is False


# ---------- Library gating ----------

class TestLibraryGating:
    def test_books_list_has_is_premium(self, s):
        r = s.get(f"{BASE_URL}/api/library/books", headers=H(FREE_TOKEN))
        assert r.status_code == 200, r.text
        data = r.json()
        books = data if isinstance(data, list) else data.get("items") or data.get("books") or []
        assert books, f"books list empty: {data}"
        for b in books:
            assert "is_premium" in b, f"book missing is_premium: {b.get('slug')}"
            assert isinstance(b["is_premium"], bool)
            if b.get("tradition") == "papal":
                assert b["is_premium"] is False, f"papal book {b.get('slug')} should be free"

    @pytest.mark.parametrize("slug", PAPAL_FREE_SLUGS)
    def test_papal_encyclical_free_for_nonadmin(self, s, slug):
        r = s.get(f"{BASE_URL}/api/library/books/{slug}/chapters/0", headers=H(FREE_TOKEN))
        assert r.status_code == 200, f"{slug} should be FREE for non-admin (got {r.status_code}: {r.text[:200]})"

    def test_confessions_augustine_paywalled_for_nonadmin(self, s):
        r = s.get(
            f"{BASE_URL}/api/library/books/confessions-augustine/chapters/0",
            headers=H(FREE_TOKEN),
        )
        assert r.status_code == 402, r.text
        detail = r.json().get("detail", "")
        assert "Sanctus Premium is required" in detail, f"bad 402 detail: {detail}"

    def test_confessions_augustine_open_for_admin(self, s):
        r = s.get(
            f"{BASE_URL}/api/library/books/confessions-augustine/chapters/0",
            headers=H(ADMIN_TOKEN),
        )
        assert r.status_code == 200, r.text


# ---------- Challenges gating ----------

class TestChallengesGating:
    @pytest.fixture(scope="class")
    def first_slug(self, s):
        r = s.get(f"{BASE_URL}/api/challenges", headers=H(FREE_TOKEN))
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("items") or data.get("challenges") or []
        assert items, f"no challenges to test: {data}"
        return items[0]["slug"]

    def test_list_open_for_nonadmin(self, s):
        r = s.get(f"{BASE_URL}/api/challenges", headers=H(FREE_TOKEN))
        assert r.status_code == 200

    def test_detail_open_for_nonadmin(self, s, first_slug):
        r = s.get(f"{BASE_URL}/api/challenges/{first_slug}", headers=H(FREE_TOKEN))
        # Some apps only have /challenges (no detail). Accept 404 only if list is the only endpoint.
        assert r.status_code in (200, 404), r.text
        if r.status_code == 404:
            pytest.skip(f"no detail endpoint for {first_slug}")

    def test_enroll_402_for_nonadmin(self, s, first_slug):
        r = s.post(f"{BASE_URL}/api/challenges/{first_slug}/enroll", headers=H(FREE_TOKEN))
        assert r.status_code == 402, r.text
        assert "Sanctus Premium is required" in r.json().get("detail", "")

    def test_enroll_200_for_admin(self, s, first_slug):
        r = s.post(f"{BASE_URL}/api/challenges/{first_slug}/enroll", headers=H(ADMIN_TOKEN))
        # Allow 200/201 — admin should NOT be paywalled.
        assert r.status_code in (200, 201), r.text


# ---------- Group DM gating ----------

class TestGroupDMGating:
    PAYLOAD = {"member_ids": [ADMIN_USER_ID], "name": "test"}

    def test_group_dm_402_for_nonadmin(self, s):
        r = s.post(
            f"{BASE_URL}/api/community/dm/threads/group",
            headers=H(FREE_TOKEN),
            json=self.PAYLOAD,
        )
        assert r.status_code == 402, r.text
        assert "Sanctus Premium is required" in r.json().get("detail", "")

    def test_group_dm_open_for_admin(self, s):
        r = s.post(
            f"{BASE_URL}/api/community/dm/threads/group",
            headers=H(ADMIN_TOKEN),
            json={"member_ids": ["user_test_nonadmin_001"], "name": "test_admin_group"},
        )
        assert r.status_code in (200, 201), r.text


# ---------- Regression ----------

class TestRegression:
    REG_ENDPOINTS = [
        "/api/library/books",
        "/api/library/films",
        "/api/library/radio",
        "/api/challenges",
        # These require ?date= query param (pre-existing behavior).
        "/api/saints/today?date=2026-01-15",
        "/api/daily-practice?date=2026-01-15",
    ]

    @pytest.mark.parametrize("path", REG_ENDPOINTS)
    def test_endpoint_200(self, s, path):
        r = s.get(f"{BASE_URL}{path}", headers=H(FREE_TOKEN))
        assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:200]}"

    def test_film_detail_youtube_id(self, s):
        r = s.get(f"{BASE_URL}/api/library/films/ccc-bernadette-anim", headers=H(FREE_TOKEN))
        assert r.status_code == 200, r.text
        d = r.json()
        # Look for youtube_id at top-level or nested
        yt = d.get("youtube_id") or (d.get("film") or {}).get("youtube_id")
        assert yt == "ACBWU4ug-rc", f"unexpected youtube_id: {yt}"

    def test_community_feed(self, s):
        # Try common variants
        for path in ["/api/community/feed", "/api/community/posts"]:
            r = s.get(f"{BASE_URL}{path}", headers=H(FREE_TOKEN))
            if r.status_code == 200:
                return
        pytest.skip("no community feed endpoint found")

    def test_shop_products_optional(self, s):
        r = s.get(f"{BASE_URL}/api/shop/products", headers=H(FREE_TOKEN))
        # Optional — if it exists must be 200
        if r.status_code == 404:
            pytest.skip("no shop endpoint")
        assert r.status_code == 200, r.text

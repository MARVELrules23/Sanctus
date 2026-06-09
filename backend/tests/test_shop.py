"""Backend tests for the Sanctus Shop feature.

Stripe is intentionally not configured in this environment (placeholder key),
so /shop/checkout and /shop/reconcile must return 503. We test:

* Public catalog (list + detail) with archived exclusion
* Admin product CRUD (create / patch / delete-as-archive) with validation
* Admin gating (403 for non-admin)
* Auth gating (401 for unauthenticated)
* Checkout returns 503 (stripe disabled)
* Reconcile returns 503
* Webhook returns 503
* Orders flow with directly-seeded "paid" order
* Admin tracking update with validation

All test data is cleaned up at the end.
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db():
    cli = MongoClient(MONGO_URL)
    d = cli[DB_NAME]
    yield d
    cli.close()


@pytest.fixture(scope="module")
def admin_token(db):
    """Mint a session token for the seeded admin user."""
    token = f"TEST_admin_{uuid.uuid4().hex}"
    db.user_sessions.insert_one({
        "session_token": token,
        "user_id": ADMIN_USER_ID,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
    })
    # Ensure the seeded admin user is actually flagged as admin (defensive).
    db.users.update_one({"user_id": ADMIN_USER_ID}, {"$set": {"is_admin": True}})
    yield token
    db.user_sessions.delete_one({"session_token": token})


@pytest.fixture(scope="module")
def user_a(db):
    user_id = f"TEST_user_a_{uuid.uuid4().hex[:8]}"
    token = f"TEST_token_a_{uuid.uuid4().hex}"
    db.users.insert_one({
        "user_id": user_id,
        "email": f"{user_id}@test.sanctus.app",
        "name": "Test User A",
        "is_admin": False,
        "created_at": datetime.now(timezone.utc),
    })
    db.user_sessions.insert_one({
        "session_token": token,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
    })
    yield {"user_id": user_id, "token": token}
    db.user_sessions.delete_many({"user_id": user_id})
    db.users.delete_many({"user_id": user_id})
    db.shop_orders.delete_many({"user_id": user_id})


@pytest.fixture(scope="module")
def user_b(db):
    user_id = f"TEST_user_b_{uuid.uuid4().hex[:8]}"
    token = f"TEST_token_b_{uuid.uuid4().hex}"
    db.users.insert_one({
        "user_id": user_id,
        "email": f"{user_id}@test.sanctus.app",
        "name": "Test User B",
        "is_admin": False,
        "created_at": datetime.now(timezone.utc),
    })
    db.user_sessions.insert_one({
        "session_token": token,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
    })
    yield {"user_id": user_id, "token": token}
    db.user_sessions.delete_many({"user_id": user_id})
    db.users.delete_many({"user_id": user_id})
    db.shop_orders.delete_many({"user_id": user_id})


def _auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Auth-gating tests
# ---------------------------------------------------------------------------

class TestAuthGating:
    def test_unauth_products_list(self):
        r = requests.get(f"{BASE_URL}/api/shop/products")
        assert r.status_code == 401

    def test_unauth_admin_products(self):
        r = requests.get(f"{BASE_URL}/api/shop/admin/products")
        assert r.status_code == 401

    def test_unauth_checkout(self):
        r = requests.post(f"{BASE_URL}/api/shop/checkout", json={
            "product_id": "x", "quantity": 1, "return_origin": "https://x.test"
        })
        assert r.status_code == 401

    def test_unauth_orders(self):
        r = requests.get(f"{BASE_URL}/api/shop/orders")
        assert r.status_code == 401

    def test_nonadmin_admin_list_products(self, user_a):
        r = requests.get(f"{BASE_URL}/api/shop/admin/products", headers=_auth(user_a["token"]))
        assert r.status_code == 403

    def test_nonadmin_admin_create_product(self, user_a):
        # Use a valid body so the failure is from admin gating, not validation.
        r = requests.post(f"{BASE_URL}/api/shop/admin/products",
                          json={"name": "TEST_Valid", "price_cents": 1000},
                          headers=_auth(user_a["token"]))
        assert r.status_code == 403

    def test_nonadmin_admin_orders(self, user_a):
        r = requests.get(f"{BASE_URL}/api/shop/admin/orders", headers=_auth(user_a["token"]))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Admin product CRUD
# ---------------------------------------------------------------------------

class TestAdminProductCRUD:
    created_ids = []

    def test_create_product_success(self, admin_token, db):
        payload = {
            "name": "TEST_Rosary",
            "description": "A blessed test rosary",
            "price_cents": 2500,
            "image_url": "https://example.com/rosary.png",
            "stock": 10,
        }
        r = requests.post(f"{BASE_URL}/api/shop/admin/products",
                          json=payload, headers=_auth(admin_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == "TEST_Rosary"
        assert data["price_cents"] == 2500
        assert data["status"] == "active"
        assert data["shipping_amount_cents"] == 500
        assert data["currency"] == "usd"
        assert data["product_id"].startswith("prod_")
        TestAdminProductCRUD.created_ids.append(data["product_id"])
        # Verify persistence
        doc = db.shop_products.find_one({"product_id": data["product_id"]})
        assert doc is not None
        assert doc["price_cents"] == 2500

    def test_create_product_short_name_422(self, admin_token):
        r = requests.post(f"{BASE_URL}/api/shop/admin/products",
                          json={"name": "x", "price_cents": 1000},
                          headers=_auth(admin_token))
        assert r.status_code == 422, r.text

    def test_create_product_low_price_422(self, admin_token):
        r = requests.post(f"{BASE_URL}/api/shop/admin/products",
                          json={"name": "TEST_Cheap", "price_cents": 50},
                          headers=_auth(admin_token))
        assert r.status_code == 422, r.text

    def test_patch_product(self, admin_token):
        pid = TestAdminProductCRUD.created_ids[0]
        r = requests.patch(f"{BASE_URL}/api/shop/admin/products/{pid}",
                           json={"description": "Updated desc", "price_cents": 3000},
                           headers=_auth(admin_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["description"] == "Updated desc"
        assert data["price_cents"] == 3000

    def test_patch_invalid_status(self, admin_token):
        pid = TestAdminProductCRUD.created_ids[0]
        r = requests.patch(f"{BASE_URL}/api/shop/admin/products/{pid}",
                           json={"status": "bogus"},
                           headers=_auth(admin_token))
        assert r.status_code == 400, r.text
        assert "status" in r.json().get("detail", "").lower()

    def test_patch_invalid_price(self, admin_token):
        pid = TestAdminProductCRUD.created_ids[0]
        r = requests.patch(f"{BASE_URL}/api/shop/admin/products/{pid}",
                           json={"price_cents": 50},
                           headers=_auth(admin_token))
        assert r.status_code == 422, r.text

    def test_patch_nonexistent_404(self, admin_token):
        r = requests.patch(f"{BASE_URL}/api/shop/admin/products/prod_nonexistent",
                           json={"description": "x"},
                           headers=_auth(admin_token))
        assert r.status_code == 404, r.text

    def test_public_list_excludes_archived(self, admin_token, user_a, db):
        # Create a second product that we'll archive
        r = requests.post(f"{BASE_URL}/api/shop/admin/products",
                          json={"name": "TEST_Archived", "price_cents": 1500},
                          headers=_auth(admin_token))
        assert r.status_code == 200
        pid = r.json()["product_id"]
        TestAdminProductCRUD.created_ids.append(pid)

        # Should appear in public list pre-archive
        r = requests.get(f"{BASE_URL}/api/shop/products", headers=_auth(user_a["token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["shipping_amount_cents"] == 500
        assert body["currency"] == "usd"
        ids = [p["product_id"] for p in body["products"]]
        assert pid in ids

        # Patch status to archived
        r = requests.patch(f"{BASE_URL}/api/shop/admin/products/{pid}",
                           json={"status": "archived"},
                           headers=_auth(admin_token))
        assert r.status_code == 200
        assert r.json()["status"] == "archived"

        # Now excluded from public list
        r = requests.get(f"{BASE_URL}/api/shop/products", headers=_auth(user_a["token"]))
        ids = [p["product_id"] for p in r.json()["products"]]
        assert pid not in ids

        # Detail returns 404 for archived
        r = requests.get(f"{BASE_URL}/api/shop/products/{pid}", headers=_auth(user_a["token"]))
        assert r.status_code == 404

        # But admin list still includes it
        r = requests.get(f"{BASE_URL}/api/shop/admin/products", headers=_auth(admin_token))
        assert r.status_code == 200
        admin_ids = [p["product_id"] for p in r.json()["products"]]
        assert pid in admin_ids

    def test_delete_archives(self, admin_token, db):
        # Create then DELETE; should be archived not removed
        r = requests.post(f"{BASE_URL}/api/shop/admin/products",
                          json={"name": "TEST_ToDelete", "price_cents": 2000},
                          headers=_auth(admin_token))
        assert r.status_code == 200
        pid = r.json()["product_id"]
        TestAdminProductCRUD.created_ids.append(pid)

        r = requests.delete(f"{BASE_URL}/api/shop/admin/products/{pid}",
                            headers=_auth(admin_token))
        assert r.status_code == 200, r.text

        doc = db.shop_products.find_one({"product_id": pid})
        assert doc is not None  # NOT removed
        assert doc["status"] == "archived"

    def test_delete_nonexistent_404(self, admin_token):
        r = requests.delete(f"{BASE_URL}/api/shop/admin/products/prod_xxx",
                            headers=_auth(admin_token))
        assert r.status_code == 404

    def test_get_product_detail(self, admin_token, user_a):
        pid = TestAdminProductCRUD.created_ids[0]
        r = requests.get(f"{BASE_URL}/api/shop/products/{pid}", headers=_auth(user_a["token"]))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["product_id"] == pid
        assert data["shipping_amount_cents"] == 500


# ---------------------------------------------------------------------------
# Checkout / Reconcile / Webhook — all should be 503 (Stripe unconfigured)
# ---------------------------------------------------------------------------

class TestStripeDisabled:
    def test_checkout_returns_503(self, user_a):
        r = requests.post(f"{BASE_URL}/api/shop/checkout", json={
            "product_id": "prod_anything",
            "quantity": 1,
            "return_origin": "https://app.example.com",
        }, headers=_auth(user_a["token"]))
        assert r.status_code == 503, r.text
        detail = (r.json().get("detail") or "").lower()
        assert "payment" in detail or "configured" in detail

    def test_reconcile_returns_503(self, user_a):
        r = requests.post(f"{BASE_URL}/api/shop/reconcile/cs_test_dummy",
                          headers=_auth(user_a["token"]))
        assert r.status_code == 503, r.text

    def test_webhook_returns_503(self):
        # Webhook does not require bearer; should still 503 since stripe disabled.
        r = requests.post(f"{BASE_URL}/api/shop/webhook", json={"type": "ping"},
                          headers={"Content-Type": "application/json",
                                   "Stripe-Signature": "t=0,v1=fake"})
        assert r.status_code == 503, r.text


# ---------------------------------------------------------------------------
# Orders flow (seeded paid order directly in DB)
# ---------------------------------------------------------------------------

class TestOrdersFlow:
    order_id = None

    def test_seed_paid_order(self, db, user_a):
        TestOrdersFlow.order_id = f"TEST_ord_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)
        db.shop_orders.insert_one({
            "order_id": TestOrdersFlow.order_id,
            "user_id": user_a["user_id"],
            "product_id": "prod_seeded",
            "product_name": "TEST Seeded Product",
            "product_image_url": None,
            "quantity": 2,
            "currency": "usd",
            "unit_amount_cents": 2500,
            "shipping_amount_cents": 500,
            "total_cents": 5500,
            "status": "paid",
            "client_token": None,
            "stripe_session_id": "cs_test_seeded",
            "stripe_session_url": None,
            "stripe_payment_intent": "pi_test_seeded",
            "shipping_details": None,
            "customer_details": {"email": "buyer@test.com"},
            "tracking_number": None,
            "created_at": now,
            "updated_at": now,
            "paid_at": now,
        })
        # Sanity
        assert db.shop_orders.find_one({"order_id": TestOrdersFlow.order_id}) is not None

    def test_user_lists_own_orders(self, user_a):
        r = requests.get(f"{BASE_URL}/api/shop/orders", headers=_auth(user_a["token"]))
        assert r.status_code == 200, r.text
        orders = r.json()["orders"]
        ids = [o["order_id"] for o in orders]
        assert TestOrdersFlow.order_id in ids
        my = next(o for o in orders if o["order_id"] == TestOrdersFlow.order_id)
        assert my["status"] == "paid"
        assert my["total_cents"] == 5500
        assert my["customer_email"] == "buyer@test.com"

    def test_owner_gets_order_detail(self, user_a):
        r = requests.get(f"{BASE_URL}/api/shop/orders/{TestOrdersFlow.order_id}",
                         headers=_auth(user_a["token"]))
        assert r.status_code == 200, r.text
        assert r.json()["order_id"] == TestOrdersFlow.order_id

    def test_other_user_gets_403_not_404(self, user_b):
        r = requests.get(f"{BASE_URL}/api/shop/orders/{TestOrdersFlow.order_id}",
                         headers=_auth(user_b["token"]))
        assert r.status_code == 403, r.text

    def test_order_not_found_404(self, user_a):
        r = requests.get(f"{BASE_URL}/api/shop/orders/ord_does_not_exist",
                         headers=_auth(user_a["token"]))
        assert r.status_code == 404, r.text

    def test_admin_can_read_any_order(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/shop/orders/{TestOrdersFlow.order_id}",
                         headers=_auth(admin_token))
        assert r.status_code == 200, r.text

    def test_admin_list_orders_filter_paid(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/shop/admin/orders?status=paid",
                         headers=_auth(admin_token))
        assert r.status_code == 200, r.text
        ids = [o["order_id"] for o in r.json()["orders"]]
        assert TestOrdersFlow.order_id in ids
        # All returned orders should have status paid
        for o in r.json()["orders"]:
            assert o["status"] == "paid"

    def test_admin_set_tracking_empty_400(self, admin_token):
        r = requests.post(
            f"{BASE_URL}/api/shop/admin/orders/{TestOrdersFlow.order_id}/tracking",
            json={"tracking_number": "   "},
            headers=_auth(admin_token),
        )
        # field_validator raises ValueError -> 422 from Pydantic
        assert r.status_code in (400, 422), r.text

    def test_admin_set_tracking_success(self, admin_token, db):
        r = requests.post(
            f"{BASE_URL}/api/shop/admin/orders/{TestOrdersFlow.order_id}/tracking",
            json={"tracking_number": "1ZTEST123456"},
            headers=_auth(admin_token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["tracking_number"] == "1ZTEST123456"
        doc = db.shop_orders.find_one({"order_id": TestOrdersFlow.order_id})
        assert doc["tracking_number"] == "1ZTEST123456"

    def test_admin_set_tracking_missing_order_404(self, admin_token):
        r = requests.post(
            f"{BASE_URL}/api/shop/admin/orders/ord_missing/tracking",
            json={"tracking_number": "X"},
            headers=_auth(admin_token),
        )
        assert r.status_code == 404, r.text

    def test_nonadmin_set_tracking_403(self, user_a):
        r = requests.post(
            f"{BASE_URL}/api/shop/admin/orders/{TestOrdersFlow.order_id}/tracking",
            json={"tracking_number": "X"},
            headers=_auth(user_a["token"]),
        )
        assert r.status_code == 403, r.text


# ---------------------------------------------------------------------------
# Final cleanup of any products created
# ---------------------------------------------------------------------------

def test_cleanup_products(db):
    db.shop_products.delete_many({"name": {"$regex": "^TEST_"}})
    db.shop_orders.delete_many({"order_id": {"$regex": "^TEST_"}})
    # Sanity check: admin user still intact
    u = db.users.find_one({"email": ADMIN_EMAIL})
    assert u is not None
    assert u.get("is_admin") is True

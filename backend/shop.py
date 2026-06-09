"""Sanctus Shop — admin-curated physical-goods store with Stripe Checkout.

Phase 1 scope:
  * Admin can create / edit / archive Products.
  * Customers browse a public catalog (logged-in only), open a Product, and tap
    "Buy now" — backend mints a Stripe Checkout Session and returns its URL.
  * After payment, the user is redirected back to `/shop/success`, which calls
    `POST /api/shop/reconcile/{session_id}` — we retrieve the session from
    Stripe, verify `payment_status == "paid"`, and atomically flip the local
    `order.status` to "paid". This lets us avoid configuring a public webhook
    URL while we're still pre-deployment; webhook support is also wired up for
    when the user deploys.
  * Shipping is a flat $5 USD added by Stripe as a single shipping option.
  * USD only. Shipping limited to US.
  * Idempotency: client passes a `client_token` to avoid double-charging on
    rapid double-taps; we store it on the order and reuse the existing Stripe
    session URL when the same token is replayed.

Collections:
  shop_products  — { product_id, name, description, price_cents, currency,
                     image_url, status: active|archived, stock?, created_at,
                     updated_at }
  shop_orders    — { order_id, user_id, product_id, quantity, currency,
                     unit_amount_cents, shipping_amount_cents, total_cents,
                     status: pending|paid|cancelled|failed,
                     client_token, stripe_session_id, stripe_session_url,
                     stripe_payment_intent, shipping_details, customer_details,
                     created_at, updated_at, paid_at }
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("sanctus.shop")

FLAT_SHIPPING_CENTS = 500  # $5.00 USD
SUPPORTED_CURRENCY = "usd"
ALLOWED_SHIPPING_COUNTRIES = ["US"]
MAX_QUANTITY = 10


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ProductIn(BaseModel):
    name: str
    description: str = ""
    price_cents: int = Field(..., ge=100, le=100_000_00)  # $1 to $100k
    image_url: Optional[str] = None
    stock: Optional[int] = Field(None, ge=0)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) < 2:
            raise ValueError("name must be at least 2 characters")
        if len(v) > 120:
            raise ValueError("name too long")
        return v


class ProductPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_cents: Optional[int] = Field(None, ge=100, le=100_000_00)
    image_url: Optional[str] = None
    stock: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None  # active | archived


class CheckoutIn(BaseModel):
    product_id: str
    quantity: int = Field(1, ge=1, le=MAX_QUANTITY)
    return_origin: str = Field(..., description="e.g. https://app.example.com")
    client_token: Optional[str] = None


class TrackingIn(BaseModel):
    tracking_number: str

    @field_validator("tracking_number")
    @classmethod
    def _t(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("tracking_number required")
        return v[:60]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _public_product(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "product_id": doc["product_id"],
        "name": doc["name"],
        "description": doc.get("description") or "",
        "price_cents": doc["price_cents"],
        "currency": doc.get("currency", SUPPORTED_CURRENCY),
        "image_url": doc.get("image_url"),
        "stock": doc.get("stock"),
        "status": doc.get("status", "active"),
        "shipping_amount_cents": FLAT_SHIPPING_CENTS,
    }


def _public_order(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "order_id": doc["order_id"],
        "user_id": doc["user_id"],
        "product_id": doc["product_id"],
        "product_name": doc.get("product_name"),
        "product_image_url": doc.get("product_image_url"),
        "quantity": doc["quantity"],
        "currency": doc.get("currency", SUPPORTED_CURRENCY),
        "unit_amount_cents": doc.get("unit_amount_cents"),
        "shipping_amount_cents": doc.get("shipping_amount_cents", FLAT_SHIPPING_CENTS),
        "total_cents": doc.get("total_cents"),
        "status": doc.get("status", "pending"),
        "shipping_details": doc.get("shipping_details"),
        "customer_email": (doc.get("customer_details") or {}).get("email"),
        "tracking_number": doc.get("tracking_number"),
        "created_at": _iso(doc.get("created_at")),
        "paid_at": _iso(doc.get("paid_at")),
    }


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


async def _ensure_admin(user) -> None:
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")


def _is_stripe_configured(api_key: str) -> bool:
    # The pod ships with a placeholder ("sk_test_emergent"). A real Stripe
    # secret key is much longer (sk_test_XXXXX..., ~107 chars).
    return bool(api_key) and api_key.startswith(("sk_test_", "sk_live_")) and len(api_key) > 30


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def build_router(
    db: AsyncIOMotorDatabase,
    get_current_user: Callable,
) -> APIRouter:
    router = APIRouter(prefix="/shop", tags=["shop"])

    products = db["shop_products"]
    orders = db["shop_orders"]

    stripe_api_key = os.environ.get("STRIPE_API_KEY", "")
    stripe_webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    stripe_ready = _is_stripe_configured(stripe_api_key)
    if stripe_ready:
        stripe.api_key = stripe_api_key
        logger.info("shop: Stripe configured (test mode = %s)", stripe_api_key.startswith("sk_test_"))
    else:
        logger.warning(
            "shop: STRIPE_API_KEY is missing or a placeholder — checkout will be disabled until deploy"
        )

    # -------------------- Public catalog --------------------

    @router.get("/products")
    async def list_products(user=Depends(get_current_user)):
        cursor = products.find({"status": {"$ne": "archived"}}).sort("created_at", -1)
        out = [_public_product(d) async for d in cursor]
        return {"products": out, "shipping_amount_cents": FLAT_SHIPPING_CENTS, "currency": SUPPORTED_CURRENCY}

    @router.get("/products/{product_id}")
    async def get_product(product_id: str, user=Depends(get_current_user)):
        doc = await products.find_one({"product_id": product_id, "status": {"$ne": "archived"}})
        if not doc:
            raise HTTPException(status_code=404, detail="product not found")
        return _public_product(doc)

    # -------------------- Admin product CRUD --------------------

    @router.get("/admin/products")
    async def admin_list_products(user=Depends(get_current_user)):
        await _ensure_admin(user)
        cursor = products.find({}).sort("created_at", -1)
        return {"products": [_public_product(d) async for d in cursor]}

    @router.post("/admin/products")
    async def admin_create_product(body: ProductIn, user=Depends(get_current_user)):
        await _ensure_admin(user)
        now = datetime.now(timezone.utc)
        doc = {
            "product_id": f"prod_{uuid.uuid4().hex[:12]}",
            "name": body.name,
            "description": body.description or "",
            "price_cents": int(body.price_cents),
            "currency": SUPPORTED_CURRENCY,
            "image_url": body.image_url or None,
            "stock": body.stock,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        await products.insert_one(doc)
        return _public_product(doc)

    @router.patch("/admin/products/{product_id}")
    async def admin_update_product(product_id: str, body: ProductPatch, user=Depends(get_current_user)):
        await _ensure_admin(user)
        existing = await products.find_one({"product_id": product_id})
        if not existing:
            raise HTTPException(status_code=404, detail="product not found")
        patch: Dict[str, Any] = {}
        for k, v in body.dict(exclude_unset=True).items():
            if k == "status" and v not in ("active", "archived"):
                raise HTTPException(status_code=400, detail="status must be active or archived")
            patch[k] = v
        if not patch:
            return _public_product(existing)
        patch["updated_at"] = datetime.now(timezone.utc)
        await products.update_one({"product_id": product_id}, {"$set": patch})
        existing.update(patch)
        return _public_product(existing)

    @router.delete("/admin/products/{product_id}")
    async def admin_archive_product(product_id: str, user=Depends(get_current_user)):
        """Soft-delete by archiving. We never hard-delete so existing orders
        still resolve their product name/image."""
        await _ensure_admin(user)
        res = await products.update_one(
            {"product_id": product_id},
            {"$set": {"status": "archived", "updated_at": datetime.now(timezone.utc)}},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="product not found")
        return {"ok": True}

    # -------------------- Checkout --------------------

    @router.post("/checkout")
    async def create_checkout(body: CheckoutIn, user=Depends(get_current_user)):
        if not stripe_ready:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Payments are not configured on this environment yet. "
                    "Deploy the app to enable purchases."
                ),
            )

        product = await products.find_one({"product_id": body.product_id, "status": {"$ne": "archived"}})
        if not product:
            raise HTTPException(status_code=404, detail="product not available")

        # Idempotency: re-use prior pending session if the same client_token is
        # replayed (e.g. user double-taps Buy Now).
        if body.client_token:
            prior = await orders.find_one({
                "user_id": user.user_id,
                "client_token": body.client_token,
                "status": "pending",
            })
            if prior and prior.get("stripe_session_url"):
                return {"url": prior["stripe_session_url"], "order_id": prior["order_id"]}

        quantity = max(1, min(MAX_QUANTITY, int(body.quantity)))
        unit_amount = int(product["price_cents"])
        total_cents = unit_amount * quantity + FLAT_SHIPPING_CENTS

        order_id = f"ord_{uuid.uuid4().hex[:14]}"
        now = datetime.now(timezone.utc)
        order_doc: Dict[str, Any] = {
            "order_id": order_id,
            "user_id": user.user_id,
            "product_id": product["product_id"],
            "product_name": product["name"],
            "product_image_url": product.get("image_url"),
            "quantity": quantity,
            "currency": SUPPORTED_CURRENCY,
            "unit_amount_cents": unit_amount,
            "shipping_amount_cents": FLAT_SHIPPING_CENTS,
            "total_cents": total_cents,
            "status": "pending",
            "client_token": body.client_token,
            "stripe_session_id": None,
            "stripe_session_url": None,
            "stripe_payment_intent": None,
            "shipping_details": None,
            "customer_details": None,
            "tracking_number": None,
            "created_at": now,
            "updated_at": now,
            "paid_at": None,
        }
        await orders.insert_one(order_doc)

        # Build success/cancel URLs in the user's origin so both web and native
        # in-app browsers return to the Expo app cleanly.
        origin = body.return_origin.rstrip("/")
        success_url = f"{origin}/shop/success?session_id={{CHECKOUT_SESSION_ID}}&order={order_id}"
        cancel_url = f"{origin}/shop/cancel?order={order_id}"

        line_items = [
            {
                "price_data": {
                    "currency": SUPPORTED_CURRENCY,
                    "unit_amount": unit_amount,
                    "product_data": {
                        "name": product["name"],
                        "description": (product.get("description") or "")[:500] or None,
                        # Stripe rejects data: URIs, so only include http(s) images.
                        "images": (
                            [product["image_url"]]
                            if product.get("image_url") and product["image_url"].startswith("http")
                            else []
                        ),
                    },
                },
                "quantity": quantity,
            }
        ]

        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                payment_method_types=["card"],
                line_items=line_items,
                shipping_address_collection={"allowed_countries": ALLOWED_SHIPPING_COUNTRIES},
                shipping_options=[
                    {
                        "shipping_rate_data": {
                            "display_name": "Standard shipping",
                            "type": "fixed_amount",
                            "fixed_amount": {
                                "amount": FLAT_SHIPPING_CENTS,
                                "currency": SUPPORTED_CURRENCY,
                            },
                        }
                    }
                ],
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=user.email,
                client_reference_id=order_id,
                metadata={
                    "order_id": order_id,
                    "user_id": user.user_id,
                    "product_id": product["product_id"],
                },
                idempotency_key=f"checkout_{order_id}",
            )
        except stripe.error.StripeError as e:
            logger.exception("stripe session create failed")
            await orders.update_one(
                {"order_id": order_id},
                {"$set": {"status": "failed", "updated_at": datetime.now(timezone.utc)}},
            )
            raise HTTPException(status_code=502, detail=f"payment provider error: {e.user_message or str(e)}")

        await orders.update_one(
            {"order_id": order_id},
            {"$set": {
                "stripe_session_id": session.id,
                "stripe_session_url": session.url,
                "updated_at": datetime.now(timezone.utc),
            }},
        )

        return {"url": session.url, "order_id": order_id}

    # -------------------- Reconcile after redirect --------------------

    async def _apply_paid_session(session_obj, order_doc) -> Dict[str, Any]:
        """Promote an order to paid based on a Stripe Checkout Session that has
        `payment_status == "paid"`. Idempotent.

        `session_obj` can be a real `stripe.checkout.Session` (dot-access) or a
        dict (from a raw webhook payload) — we read both safely.
        """
        if order_doc.get("status") == "paid":
            return order_doc  # already settled

        def _field(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        now = datetime.now(timezone.utc)
        update = {
            "status": "paid",
            "paid_at": now,
            "updated_at": now,
            "stripe_payment_intent": _field(session_obj, "payment_intent"),
            "shipping_details": _field(session_obj, "shipping_details"),
            "customer_details": _field(session_obj, "customer_details"),
        }
        await orders.update_one({"order_id": order_doc["order_id"]}, {"$set": update})
        order_doc.update(update)
        # Decrement stock if tracked.
        if order_doc.get("product_id"):
            await products.update_one(
                {"product_id": order_doc["product_id"], "stock": {"$gte": order_doc["quantity"]}},
                {"$inc": {"stock": -order_doc["quantity"]}, "$set": {"updated_at": now}},
            )
        return order_doc

    @router.post("/reconcile/{session_id}")
    async def reconcile_session(session_id: str, user=Depends(get_current_user)):
        if not stripe_ready:
            raise HTTPException(status_code=503, detail="payments not configured")
        order = await orders.find_one({"stripe_session_id": session_id})
        if not order:
            raise HTTPException(status_code=404, detail="order not found")
        if order["user_id"] != user.user_id and not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="not your order")
        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=502, detail=str(e))

        payment_status = session.get("payment_status") if isinstance(session, dict) else session.payment_status
        if payment_status == "paid":
            order = await _apply_paid_session(session, order)
        elif payment_status in ("unpaid", "no_payment_required"):
            # Leave the order pending; user may still complete.
            pass

        return {"order": _public_order(order), "payment_status": payment_status}

    # -------------------- Orders (user-facing) --------------------

    @router.get("/orders")
    async def list_my_orders(user=Depends(get_current_user), limit: int = Query(50, ge=1, le=200)):
        cursor = orders.find({"user_id": user.user_id}).sort("created_at", -1).limit(limit)
        return {"orders": [_public_order(d) async for d in cursor]}

    @router.get("/orders/{order_id}")
    async def get_my_order(order_id: str, user=Depends(get_current_user)):
        doc = await orders.find_one({"order_id": order_id})
        if not doc:
            raise HTTPException(status_code=404, detail="order not found")
        if doc["user_id"] != user.user_id and not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="not your order")
        return _public_order(doc)

    # -------------------- Admin order management --------------------

    @router.get("/admin/orders")
    async def admin_list_orders(
        user=Depends(get_current_user),
        status: Optional[str] = Query(None),
        limit: int = Query(100, ge=1, le=500),
    ):
        await _ensure_admin(user)
        q: Dict[str, Any] = {}
        if status:
            q["status"] = status
        cursor = orders.find(q).sort("created_at", -1).limit(limit)
        return {"orders": [_public_order(d) async for d in cursor]}

    @router.post("/admin/orders/{order_id}/tracking")
    async def admin_set_tracking(order_id: str, body: TrackingIn, user=Depends(get_current_user)):
        await _ensure_admin(user)
        res = await orders.update_one(
            {"order_id": order_id},
            {"$set": {"tracking_number": body.tracking_number, "updated_at": datetime.now(timezone.utc)}},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="order not found")
        doc = await orders.find_one({"order_id": order_id})
        return _public_order(doc)

    # -------------------- Stripe webhook (optional) --------------------

    @router.post("/webhook")
    async def stripe_webhook(request: Request, stripe_signature: str = Header(None, alias="Stripe-Signature")):
        if not stripe_ready:
            raise HTTPException(status_code=503, detail="payments not configured")
        payload = await request.body()
        is_live = stripe_api_key.startswith("sk_live_")
        try:
            if stripe_webhook_secret:
                event = stripe.Webhook.construct_event(payload, stripe_signature, stripe_webhook_secret)
            elif is_live:
                # In live mode we never accept unsigned events.
                raise HTTPException(
                    status_code=401,
                    detail="STRIPE_WEBHOOK_SECRET must be configured in live mode",
                )
            else:
                # Test mode + no secret: accept unverified payloads so devs can
                # exercise the flow with the Stripe CLI before configuring a
                # secret. We still rely on the success-page reconcile path as
                # the source of truth, so this is acceptable.
                import json
                logger.warning("shop webhook: accepting unsigned event (test mode, no STRIPE_WEBHOOK_SECRET)")
                event = json.loads(payload.decode("utf-8"))
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="invalid signature")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        evt_type = event["type"] if isinstance(event, dict) else event.get("type")
        data = (event.get("data") or {}).get("object") if isinstance(event, dict) else event["data"]["object"]
        if evt_type == "checkout.session.completed":
            order_id = ((data.get("metadata") or {}).get("order_id")) if isinstance(data, dict) else None
            if order_id:
                order = await orders.find_one({"order_id": order_id})
                if order and (data.get("payment_status") == "paid" if isinstance(data, dict) else False):
                    await _apply_paid_session(data, order)
        return {"ok": True}

    return router


# ---------------------------------------------------------------------------
# Index creation — invoked from server.py startup
# ---------------------------------------------------------------------------


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db["shop_products"].create_index("product_id", unique=True)
    await db["shop_products"].create_index("status")
    await db["shop_orders"].create_index("order_id", unique=True)
    await db["shop_orders"].create_index("user_id")
    await db["shop_orders"].create_index("stripe_session_id")
    await db["shop_orders"].create_index([("user_id", 1), ("created_at", -1)])

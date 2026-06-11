"""Sanctus Premium — Stripe Recurring Subscriptions.

Pricing tiers:
  * Monthly — $4.99 USD / month
  * Annual  — $39.99 USD / year (saves ~33% vs. monthly)
Both tiers include a 7-day free trial (no charge during trial).

Flow (matches the pattern used by `shop.py`):
  1. `POST /api/subscriptions/create-checkout-session` — backend creates a
     Stripe Checkout Session in `subscription` mode with `price_data` inline
     (no need to pre-provision a Product/Price in the Stripe dashboard) and
     returns its `url`.
  2. Client opens that URL in a system browser via `expo-web-browser` (mobile)
     or `window.location` (web). Stripe handles SCA + card entry.
  3. Stripe redirects to `<origin>/premium/success?session_id={CHECKOUT_SESSION_ID}`
     which calls `POST /api/subscriptions/reconcile/{session_id}` to mark the
     user as premium immediately (we don't depend on the webhook for the
     happy-path success update — webhook is the long-term source of truth for
     renewals / cancellations).
  4. `POST /api/subscriptions/webhook` accepts `customer.subscription.updated`
     / `customer.subscription.deleted` / `invoice.payment_failed` events to
     keep `premium.active` accurate.
  5. `POST /api/subscriptions/customer-portal` mints a Stripe Billing Portal
     session URL so the user can self-manage / cancel.

The user document is annotated like:

    users.<doc>.stripe = { customer_id, subscription_id }
    users.<doc>.premium = { active, tier, status, current_period_end,
                             cancel_at_period_end, trial_end, updated_at }

`is_premium_user()` in `premium.py` reads this subdoc and also auto-grants
premium to admin emails.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from urllib.parse import quote, urlencode, urlparse, urlunparse, parse_qsl

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

from premium import (
    ADMIN_PREMIUM_EMAILS,
    PREMIUM_PRICING,
    PREMIUM_PRODUCT_NAME,
    PREMIUM_TRIAL_DAYS,
    is_premium_user,
)

logger = logging.getLogger("sanctus.subscriptions")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_stripe_configured(api_key: str) -> bool:
    return bool(api_key) and api_key.startswith(("sk_test_", "sk_live_")) and len(api_key) > 30


def _is_payment_link(url: str) -> bool:
    """Validate that a configured value looks like a hosted Stripe
    Payment Link (https://buy.stripe.com/...). Anything else is
    rejected so we don't accidentally redirect to a typo."""
    if not url:
        return False
    return url.startswith("https://buy.stripe.com/") and len(url) > 24


def _append_payment_link_params(url: str, params: Dict[str, str]) -> str:
    """Append/override query params on a Stripe Payment Link URL.

    Stripe Payment Links accept reserved query params:
      * `client_reference_id` — surfaces on the `checkout.session.completed`
        webhook so we can map the payment back to a Sanctus user even though
        we never created the session ourselves.
      * `prefilled_email` — pre-populates the email field, which also helps
        webhook reconciliation as a secondary fallback.

    Values that already exist on the URL are preserved unless we explicitly
    override them. We also `quote` values to be safe with characters like
    `@` in emails.
    """
    if not url:
        return url
    parsed = urlparse(url)
    existing = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for k, v in params.items():
        if v is None:
            continue
        v = str(v).strip()
        if not v:
            continue
        # Stripe's reserved params have strict character sets; the safest
        # thing is to URL-encode aggressively.
        existing[k] = v
    new_query = urlencode(existing, quote_via=quote)
    return urlunparse(parsed._replace(query=new_query))


# Hosted Stripe Payment Links — set by user. Defaults to the URLs the
# founder provided so the preview environment can also send users to
# real checkout. Override in env if Stripe links are rotated.
PAYMENT_LINK_MONTHLY_DEFAULT = "https://buy.stripe.com/bJe6oG3XJbE0gnw31fb7y00"
PAYMENT_LINK_ANNUAL_DEFAULT = "https://buy.stripe.com/dRm4gyam7dM8b3c45jb7y01"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_ts(value: Any) -> Optional[int]:
    """Coerce Stripe timestamp fields (which arrive as int) into ints."""
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class CreateCheckoutRequest(BaseModel):
    plan: str = Field(..., description="'monthly' or 'annual'")
    return_origin: str = Field(..., description="e.g. https://app.example.com")

    @field_validator("plan")
    @classmethod
    def _plan(cls, v: str) -> str:
        if v not in PREMIUM_PRICING:
            raise ValueError("plan must be 'monthly' or 'annual'")
        return v

    @field_validator("return_origin")
    @classmethod
    def _origin(cls, v: str) -> str:
        v = (v or "").strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("return_origin must be an http(s) URL")
        return v.rstrip("/")


class CustomerPortalRequest(BaseModel):
    return_origin: str

    @field_validator("return_origin")
    @classmethod
    def _origin(cls, v: str) -> str:
        v = (v or "").strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("return_origin must be an http(s) URL")
        return v.rstrip("/")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def build_subscriptions_router(
    db: AsyncIOMotorDatabase,
    get_current_user: Callable,
) -> APIRouter:
    router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

    users = db["users"]

    stripe_api_key = os.environ.get("STRIPE_API_KEY", "")
    stripe_webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    stripe_ready = _is_stripe_configured(stripe_api_key)
    if stripe_ready:
        stripe.api_key = stripe_api_key
        logger.info(
            "subscriptions: Stripe configured (test mode = %s)",
            stripe_api_key.startswith("sk_test_"),
        )
    else:
        logger.warning(
            "subscriptions: STRIPE_API_KEY missing/placeholder — Stripe API (portal/reconcile/webhook) disabled until deploy"
        )

    # Hosted Stripe Payment Links — these power the buy flow even without a
    # real STRIPE_API_KEY in the preview environment, since Stripe hosts
    # the entire checkout page. The webhook + customer portal still need
    # a real API key once you deploy.
    payment_link_monthly = (
        os.environ.get("STRIPE_PAYMENT_LINK_MONTHLY") or PAYMENT_LINK_MONTHLY_DEFAULT
    ).strip()
    payment_link_annual = (
        os.environ.get("STRIPE_PAYMENT_LINK_ANNUAL") or PAYMENT_LINK_ANNUAL_DEFAULT
    ).strip()
    payment_links_ready = (
        _is_payment_link(payment_link_monthly) and _is_payment_link(payment_link_annual)
    )
    if payment_links_ready:
        logger.info(
            "subscriptions: Payment Links configured (monthly=%s, annual=%s)",
            payment_link_monthly[:40] + "...",
            payment_link_annual[:40] + "...",
        )

    checkout_ready = payment_links_ready or stripe_ready

    # ----------------------------- Premium status -------------------------

    async def _user_doc(user_id: str) -> Optional[Dict[str, Any]]:
        return await users.find_one({"user_id": user_id}, {"_id": 0})

    def _public_status(user_doc: Optional[Dict[str, Any]], current_user) -> Dict[str, Any]:
        prem = (user_doc or {}).get("premium") or {}
        is_admin_premium = (
            (getattr(current_user, "email", "") or "").lower() in ADMIN_PREMIUM_EMAILS
            or bool(getattr(current_user, "is_admin", False))
        )
        active = is_admin_premium or is_premium_user(current_user, prem)
        return {
            "is_premium": active,
            "is_admin_premium": is_admin_premium,
            "tier": prem.get("tier"),
            "status": prem.get("status"),
            "current_period_end": prem.get("current_period_end"),
            "cancel_at_period_end": bool(prem.get("cancel_at_period_end")),
            "trial_end": prem.get("trial_end"),
            "pricing": PREMIUM_PRICING,
            "trial_days": PREMIUM_TRIAL_DAYS,
            # `stripe_ready` is kept for backwards compatibility — it now
            # means "anything we can use to send the user to Stripe", which
            # is true when either payment links or the API key are set.
            "stripe_ready": checkout_ready,
            "checkout_ready": checkout_ready,
            "portal_ready": stripe_ready,
            "payment_links": payment_links_ready,
        }

    @router.get("/status")
    async def get_status(user=Depends(get_current_user)):
        doc = await _user_doc(user.user_id)
        return _public_status(doc, user)

    # ----------------------------- Checkout -------------------------------

    @router.post("/create-checkout-session")
    async def create_checkout(body: CreateCheckoutRequest,
                              user=Depends(get_current_user)):
        # Admin / override accounts never need to pay — short-circuit
        # BEFORE checking whether Stripe is configured, so the founder /
        # admin always sees a clean "already premium" response (even in
        # the placeholder-key preview environment).
        if is_premium_user(user):
            return {
                "already_premium": True,
                "url": None,
            }

        # ------------------------------------------------------------------
        # Primary path: hosted Stripe Payment Links
        # ------------------------------------------------------------------
        # These are pre-built Stripe checkout pages that work even when our
        # backend doesn't have a STRIPE_API_KEY (e.g. preview environment).
        # We append `client_reference_id` so the webhook can map the
        # payment back to a Sanctus user.
        if payment_links_ready:
            tier = body.plan
            base_url = (
                payment_link_annual if tier == "annual" else payment_link_monthly
            )
            email = (getattr(user, "email", "") or "").strip()
            checkout_url = _append_payment_link_params(
                base_url,
                {
                    "client_reference_id": user.user_id,
                    "prefilled_email": email,
                },
            )

            # Record selection for later reconciliation/debugging. We don't
            # have a Checkout Session ID yet (Stripe will mint one when the
            # user actually clicks "Pay") — the webhook will fill it in.
            await users.update_one(
                {"user_id": user.user_id},
                {"$set": {
                    "stripe.last_plan_selected": tier,
                    "stripe.last_checkout_kind": "payment_link",
                    "stripe.updated_at": _now(),
                }},
            )

            return {
                "url": checkout_url,
                "session_id": None,
                "plan": tier,
                "kind": "payment_link",
            }

        # ------------------------------------------------------------------
        # Fallback path: dynamic Stripe Checkout Session
        # ------------------------------------------------------------------
        # Kept so we can revert / A-B test without a code change. Requires
        # STRIPE_API_KEY because we call the Stripe SDK here.
        if not stripe_ready:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Payments are not configured on this environment yet. "
                    "Deploy the app to enable Sanctus Premium."
                ),
            )

        tier = body.plan
        pricing = PREMIUM_PRICING[tier]
        unit_amount = int(pricing["amount_cents"])
        interval = pricing["interval"]

        origin = body.return_origin.rstrip("/")
        success_url = f"{origin}/premium/success?session_id={{CHECKOUT_SESSION_ID}}&plan={tier}"
        cancel_url = f"{origin}/premium?cancelled=1"

        # Look up or create a Stripe customer up front so the webhook can map
        # back to the user without relying on metadata alone.
        user_doc = await _user_doc(user.user_id) or {}
        stripe_block = user_doc.get("stripe") or {}
        customer_id = stripe_block.get("customer_id")
        try:
            if not customer_id:
                customer = stripe.Customer.create(
                    email=getattr(user, "email", None),
                    name=getattr(user, "name", None),
                    metadata={"user_id": user.user_id},
                )
                customer_id = customer.id
                await users.update_one(
                    {"user_id": user.user_id},
                    {"$set": {
                        "stripe.customer_id": customer_id,
                        "stripe.updated_at": _now(),
                    }},
                )
        except stripe.error.StripeError as e:
            logger.exception("stripe customer create failed")
            raise HTTPException(status_code=502, detail=str(e))

        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                customer=customer_id,
                client_reference_id=user.user_id,
                line_items=[
                    {
                        "quantity": 1,
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": unit_amount,
                            "recurring": {"interval": interval},
                            "product_data": {
                                "name": f"{PREMIUM_PRODUCT_NAME} — {pricing['label']}",
                            },
                        },
                    }
                ],
                subscription_data={
                    "trial_period_days": PREMIUM_TRIAL_DAYS,
                    "metadata": {
                        "user_id": user.user_id,
                        "plan": tier,
                        "email": getattr(user, "email", "") or "",
                    },
                },
                success_url=success_url,
                cancel_url=cancel_url,
                allow_promotion_codes=True,
                metadata={
                    "user_id": user.user_id,
                    "plan": tier,
                    "email": getattr(user, "email", "") or "",
                },
            )
        except stripe.error.StripeError as e:
            logger.exception("stripe checkout.Session.create failed")
            raise HTTPException(status_code=502, detail=str(e))

        await users.update_one(
            {"user_id": user.user_id},
            {"$set": {
                "stripe.last_checkout_session_id": session.id,
                "stripe.last_plan_selected": tier,
                "stripe.last_checkout_kind": "session",
                "stripe.updated_at": _now(),
            }},
        )

        return {
            "url": session.url,
            "session_id": session.id,
            "plan": tier,
            "kind": "session",
        }

    # ----------------------------- Reconcile ------------------------------

    async def _apply_subscription_to_user(
        user_id: str,
        subscription: Any,
        tier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mirror the live state of a Stripe Subscription into the user
        document and return the resulting premium block."""
        status = (subscription.get("status") if isinstance(subscription, dict)
                  else getattr(subscription, "status", None))
        customer_id = (subscription.get("customer") if isinstance(subscription, dict)
                       else getattr(subscription, "customer", None))
        subscription_id = (subscription.get("id") if isinstance(subscription, dict)
                           else getattr(subscription, "id", None))
        current_period_end = (subscription.get("current_period_end") if isinstance(subscription, dict)
                              else getattr(subscription, "current_period_end", None))
        cancel_at_period_end = (subscription.get("cancel_at_period_end") if isinstance(subscription, dict)
                                else getattr(subscription, "cancel_at_period_end", False))
        trial_end = (subscription.get("trial_end") if isinstance(subscription, dict)
                     else getattr(subscription, "trial_end", None))

        # Derive tier from price.recurring.interval when metadata is missing.
        if not tier:
            try:
                if isinstance(subscription, dict):
                    items = (subscription.get("items") or {}).get("data") or []
                else:
                    items = (subscription.items.data if subscription.items else [])
                first_price = items[0].price if items else None
                if first_price is not None:
                    interval = first_price.recurring.interval if hasattr(first_price.recurring, "interval") else (
                        first_price.get("recurring", {}).get("interval") if isinstance(first_price, dict) else None
                    )
                    if interval == "year":
                        tier = "annual"
                    elif interval == "month":
                        tier = "monthly"
            except Exception:
                tier = None

        active = (status or "").lower() in ("trialing", "active")
        premium_doc = {
            "active": active,
            "tier": tier,
            "status": status,
            "current_period_end": _to_ts(current_period_end),
            "cancel_at_period_end": bool(cancel_at_period_end),
            "trial_end": _to_ts(trial_end),
            "updated_at": _now(),
        }
        await users.update_one(
            {"user_id": user_id},
            {"$set": {
                "premium": premium_doc,
                "stripe.customer_id": customer_id,
                "stripe.subscription_id": subscription_id,
                "stripe.updated_at": _now(),
            }},
        )
        return premium_doc

    @router.post("/reconcile/{session_id}")
    async def reconcile_session(session_id: str, user=Depends(get_current_user)):
        """Called by the frontend after Stripe redirects to /premium/success.
        Pulls the session + subscription from Stripe and flips the user to
        premium if Stripe confirms the subscription is trialing/active."""
        if not stripe_ready:
            raise HTTPException(status_code=503, detail="Payments not configured")
        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError as e:
            logger.exception("stripe session retrieve failed")
            raise HTTPException(status_code=502, detail=str(e))

        # Verify the session belongs to this user (metadata should match)
        meta_user = (session.metadata or {}).get("user_id")
        if meta_user and meta_user != user.user_id:
            raise HTTPException(status_code=403, detail="Session does not belong to this user")

        subscription_id = getattr(session, "subscription", None)
        if not subscription_id:
            return {"reconciled": False, "reason": "No subscription on session", "premium": None}

        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
        except stripe.error.StripeError as e:
            logger.exception("stripe subscription retrieve failed")
            raise HTTPException(status_code=502, detail=str(e))

        tier = (session.metadata or {}).get("plan")
        premium_doc = await _apply_subscription_to_user(user.user_id, subscription, tier=tier)
        return {"reconciled": True, "premium": premium_doc}

    # ----------------------------- Customer Portal ------------------------

    @router.post("/customer-portal")
    async def customer_portal(body: CustomerPortalRequest,
                              user=Depends(get_current_user)):
        if not stripe_ready:
            raise HTTPException(status_code=503, detail="Payments not configured")

        user_doc = await _user_doc(user.user_id) or {}
        customer_id = (user_doc.get("stripe") or {}).get("customer_id")
        if not customer_id:
            # Lazily create a customer so the user can be sent to the portal
            # (even if they haven't actually subscribed, it lets them see the
            # empty portal).
            try:
                customer = stripe.Customer.create(
                    email=getattr(user, "email", None),
                    name=getattr(user, "name", None),
                    metadata={"user_id": user.user_id},
                )
                customer_id = customer.id
                await users.update_one(
                    {"user_id": user.user_id},
                    {"$set": {"stripe.customer_id": customer_id, "stripe.updated_at": _now()}},
                )
            except stripe.error.StripeError as e:
                logger.exception("stripe customer create failed (portal)")
                raise HTTPException(status_code=502, detail=str(e))

        return_url = body.return_origin.rstrip("/") + "/premium"
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
        except stripe.error.StripeError as e:
            logger.exception("stripe portal session create failed")
            # Stripe requires the merchant to first activate the portal in
            # the dashboard. Surface that hint to admins clearly.
            raise HTTPException(status_code=502, detail=str(e))
        return {"url": session.url}

    # ----------------------------- Webhook --------------------------------

    @router.post("/webhook")
    async def subscriptions_webhook(
        request: Request,
        stripe_signature: str = Header(None, alias="Stripe-Signature"),
    ):
        if not stripe_ready:
            raise HTTPException(status_code=503, detail="Stripe not configured")

        payload = await request.body()
        event: Dict[str, Any]
        if stripe_webhook_secret:
            try:
                event = stripe.Webhook.construct_event(
                    payload=payload,
                    sig_header=stripe_signature or "",
                    secret=stripe_webhook_secret,
                )
            except (ValueError, stripe.error.SignatureVerificationError) as e:
                logger.warning("subscriptions webhook signature invalid: %s", e)
                raise HTTPException(status_code=400, detail="bad signature")
        else:
            # No signing secret configured (pre-deploy). Best-effort parse;
            # in production this branch is unreachable.
            try:
                event = await request.json()
            except Exception:
                raise HTTPException(status_code=400, detail="bad payload")

        event_type = event.get("type", "")
        data_object = (event.get("data") or {}).get("object") or {}

        async def _user_id_from_object(obj: Dict[str, Any]) -> Optional[str]:
            # 1) Explicit metadata (we set this when we create dynamic
            #    Checkout Sessions ourselves).
            uid = (obj.get("metadata") or {}).get("user_id")
            if uid:
                return uid
            # 2) `client_reference_id` — set on the Payment Link URL we hand
            #    out. Stripe surfaces it on the `checkout.session.completed`
            #    object.
            cref = obj.get("client_reference_id")
            if cref:
                return cref
            # 3) Map by Stripe customer id (set after first payment).
            cid = obj.get("customer")
            if cid:
                doc = await users.find_one({"stripe.customer_id": cid}, {"user_id": 1, "_id": 0})
                if doc:
                    return doc.get("user_id")
            # 4) Last-resort fallback: customer_email / customer_details.email.
            email = (
                obj.get("customer_email")
                or (obj.get("customer_details") or {}).get("email")
            )
            if email:
                email = str(email).strip().lower()
                doc = await users.find_one(
                    {"email": {"$regex": f"^{email}$", "$options": "i"}},
                    {"user_id": 1, "_id": 0},
                )
                if doc:
                    return doc.get("user_id")
            return None

        try:
            if event_type == "checkout.session.completed":
                if (data_object.get("mode") == "subscription"
                        and data_object.get("subscription")):
                    uid = await _user_id_from_object(data_object)
                    if uid:
                        try:
                            subscription = stripe.Subscription.retrieve(
                                data_object["subscription"]
                            )
                            tier = (data_object.get("metadata") or {}).get("plan")
                            await _apply_subscription_to_user(uid, subscription, tier=tier)
                        except stripe.error.StripeError:
                            logger.exception("subscription retrieve in webhook failed")

            elif event_type in (
                "customer.subscription.created",
                "customer.subscription.updated",
                "customer.subscription.trial_will_end",
            ):
                uid = await _user_id_from_object(data_object)
                if uid:
                    tier = (data_object.get("metadata") or {}).get("plan")
                    await _apply_subscription_to_user(uid, data_object, tier=tier)

            elif event_type == "customer.subscription.deleted":
                uid = await _user_id_from_object(data_object)
                if uid:
                    await users.update_one(
                        {"user_id": uid},
                        {"$set": {
                            "premium.active": False,
                            "premium.status": data_object.get("status") or "canceled",
                            "premium.cancel_at_period_end": False,
                            "premium.updated_at": _now(),
                        }},
                    )

            elif event_type == "invoice.payment_failed":
                # Move user out of premium if Stripe is going to dunning.
                cid = data_object.get("customer")
                if cid:
                    doc = await users.find_one({"stripe.customer_id": cid}, {"user_id": 1, "_id": 0})
                    if doc:
                        await users.update_one(
                            {"user_id": doc["user_id"]},
                            {"$set": {
                                "premium.status": "past_due",
                                "premium.updated_at": _now(),
                            }},
                        )
        except Exception:
            logger.exception("subscriptions webhook handler crashed for event %s", event_type)
            # Still return 200 so Stripe doesn't endlessly retry on a bad row.

        return {"received": True}

    return router

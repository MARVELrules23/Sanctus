"""Sanctus Premium — gating helpers used by routers (library, challenges,
community) to decide whether a user is allowed to access a premium feature.

Premium is granted when ANY of the following is true:
  * the user's email is in `ADMIN_PREMIUM_EMAILS`           (free admin override)
  * the user has `is_admin == True`                          (test/seed admins)
  * the user has `premium.active == True`                    (paid via Stripe)

The `premium` subdocument on a user is populated by the Stripe webhook /
reconcile flow in `subscriptions.py`. Shape:

    {
        "premium": {
            "active": True,
            "tier": "monthly" | "annual",
            "status": "trialing" | "active" | "past_due" | "canceled",
            "current_period_end": <unix ts int or None>,
            "cancel_at_period_end": False,
            "trial_end": <unix ts int or None>,
        },
        "stripe": {
            "customer_id": "cus_...",
            "subscription_id": "sub_...",
        }
    }
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException

# Emails that always have premium access for free (super-admin / founder).
ADMIN_PREMIUM_EMAILS = {
    "philipwils13@gmail.com",
}


def _email_of(user: Any) -> str:
    if user is None:
        return ""
    if isinstance(user, dict):
        return (user.get("email") or "").strip().lower()
    return (getattr(user, "email", "") or "").strip().lower()


def _is_admin(user: Any) -> bool:
    if user is None:
        return False
    if isinstance(user, dict):
        return bool(user.get("is_admin"))
    return bool(getattr(user, "is_admin", False))


def is_premium_user(user: Any, premium_doc: Optional[Dict[str, Any]] = None) -> bool:
    """Decide whether the given user is currently entitled to premium features.

    `premium_doc` is the `premium` subdocument from MongoDB (if already
    fetched). If not provided, we fall back to anything attached to the user
    model under `premium_active` / `is_premium`.
    """
    if _email_of(user) in ADMIN_PREMIUM_EMAILS:
        return True
    if _is_admin(user):
        return True
    if isinstance(user, dict):
        prem = user.get("premium") or premium_doc or {}
    else:
        prem = premium_doc or {}
        if not prem:
            attr = getattr(user, "premium", None)
            if isinstance(attr, dict):
                prem = attr
    if prem and bool(prem.get("active")):
        # Only count as active if Stripe-reported status is trialing/active
        # (we still flip premium.active=false on subscription cancelation
        # via webhook, but be safe and double-check).
        status = (prem.get("status") or "").lower()
        if status in ("trialing", "active") or not status:
            return True
    return False


def require_premium(user: Any, *, feature: str = "this feature") -> None:
    """Raise 402 Payment Required if the user is not a premium subscriber.

    402 is used (rather than 403) so the frontend can cleanly distinguish a
    paywall from an unrelated authorization error and route the user to the
    Premium upgrade screen.
    """
    if not is_premium_user(user):
        raise HTTPException(
            status_code=402,
            detail=f"Sanctus Premium is required to use {feature}.",
        )


# Pricing — keep in sync with subscriptions.py and the Premium screen UI.
PREMIUM_PRICING = {
    "monthly": {"amount_cents": 499, "interval": "month", "label": "Monthly"},
    "annual": {"amount_cents": 3999, "interval": "year", "label": "Annual"},
}
PREMIUM_TRIAL_DAYS = 7
PREMIUM_PRODUCT_NAME = "Sanctus Premium"

"""Sanctus Charity Hub — Catholic charities + volunteer opportunities.

Phase 1 scope (this iteration):
  * Anyone (logged-in) can submit a charity. New entries land as
    `status="pending"` and must be admin-approved before showing on the public
    listing.
  * Public listing supports text search (name / mission) and category + state
    filters.
  * Charity detail page shows mission, contact CTAs (website, email, phone),
    address, social links, logo.
  * "Claim" flow groundwork: a logged-in user can request to claim ownership
    of an approved charity. Admin reviews and approves, which sets
    `claimed_by` on the charity. Once claimed, the claiming user can edit a
    subset of fields. (Phase 2 will add the in-app editor; for now the admin
    can edit any charity.)
  * "I'm interested" contact: stored as a `charity_contacts` document so the
    charity (and admin) can see interest even before SendGrid is wired. Once
    email is configured, this row will trigger an email to the charity.

Collections:
  charities          — { charity_id, name, mission, category, city, state,
                          country, website, email, phone, logo_url, status,
                          submitted_by, approved_by, approved_at,
                          claimed_by, claim_status, created_at, updated_at }
  charity_claims     — { claim_id, charity_id, user_id, message, status,
                          requested_at, decided_at, decided_by }
  charity_contacts   — { contact_id, charity_id, user_id, user_email,
                          user_name, message, created_at }
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field, field_validator

logger = logging.getLogger("sanctus.charity")

ALLOWED_CATEGORIES = [
    "food_bank",
    "homeless",
    "pro_life",
    "education",
    "missions",
    "youth",
    "elderly",
    "refugees",
    "healthcare",
    "disability",
    "addiction_recovery",
    "prison_ministry",
    "general",
]
DEFAULT_CATEGORY = "general"
ALLOWED_COUNTRIES = ["US", "CA", "MX", "UK", "IE", "AU", "OTHER"]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


def _clean(s: Optional[str], *, max_len: int = 240, lower: bool = False) -> str:
    s = (s or "").strip()
    if lower:
        s = s.lower()
    return s[:max_len]


def _is_http_url(v: Optional[str]) -> bool:
    if not v:
        return False
    return v.startswith("http://") or v.startswith("https://")


class CharityIn(BaseModel):
    name: str
    mission: str
    category: str = DEFAULT_CATEGORY
    city: str = ""
    state: str = ""
    country: str = "US"
    website: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    logo_url: Optional[str] = None  # accepts http(s) or data: URI

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = _clean(v, max_len=140)
        if len(v) < 2:
            raise ValueError("name must be at least 2 characters")
        return v

    @field_validator("mission")
    @classmethod
    def _mission(cls, v: str) -> str:
        v = _clean(v, max_len=1200)
        if len(v) < 10:
            raise ValueError("mission must be at least 10 characters")
        return v

    @field_validator("category")
    @classmethod
    def _cat(cls, v: str) -> str:
        v = _clean(v, max_len=40, lower=True)
        return v if v in ALLOWED_CATEGORIES else DEFAULT_CATEGORY

    @field_validator("city")
    @classmethod
    def _city(cls, v: str) -> str:
        return _clean(v, max_len=80)

    @field_validator("state")
    @classmethod
    def _state(cls, v: str) -> str:
        return _clean(v, max_len=40)

    @field_validator("country")
    @classmethod
    def _country(cls, v: str) -> str:
        v = _clean(v, max_len=8, lower=False).upper()
        return v if v in ALLOWED_COUNTRIES else "US"

    @field_validator("website")
    @classmethod
    def _web(cls, v: Optional[str]) -> Optional[str]:
        v = _clean(v, max_len=300)
        if not v:
            return None
        if not _is_http_url(v):
            v = "https://" + v
        return v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: Optional[str]) -> Optional[str]:
        v = _clean(v, max_len=40)
        return v or None


class CharityPatch(BaseModel):
    name: Optional[str] = None
    mission: Optional[str] = None
    category: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    logo_url: Optional[str] = None
    status: Optional[str] = None  # pending | approved | archived | rejected


class ClaimIn(BaseModel):
    message: str = ""

    @field_validator("message")
    @classmethod
    def _msg(cls, v: str) -> str:
        return _clean(v, max_len=800)


class InterestIn(BaseModel):
    message: str = ""

    @field_validator("message")
    @classmethod
    def _msg(cls, v: str) -> str:
        return _clean(v, max_len=800)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _public_charity(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "charity_id": doc["charity_id"],
        "name": doc["name"],
        "mission": doc.get("mission") or "",
        "category": doc.get("category") or DEFAULT_CATEGORY,
        "city": doc.get("city") or "",
        "state": doc.get("state") or "",
        "country": doc.get("country") or "US",
        "website": doc.get("website") or None,
        "email": doc.get("email") or None,
        "phone": doc.get("phone") or None,
        "logo_url": doc.get("logo_url") or None,
        "status": doc.get("status") or "pending",
        "claimed_by": doc.get("claimed_by") or None,
        "created_at": _iso(doc.get("created_at")),
        "approved_at": _iso(doc.get("approved_at")),
    }


def _admin_charity(doc: Dict[str, Any]) -> Dict[str, Any]:
    base = _public_charity(doc)
    base.update({
        "submitted_by": doc.get("submitted_by"),
        "approved_by": doc.get("approved_by"),
        "claim_status": doc.get("claim_status"),
        "updated_at": _iso(doc.get("updated_at")),
    })
    return base


async def _ensure_admin(user) -> None:
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def build_router(
    db: AsyncIOMotorDatabase,
    get_current_user: Callable,
) -> APIRouter:
    router = APIRouter(prefix="/charities", tags=["charities"])

    charities = db["charities"]
    claims = db["charity_claims"]
    contacts = db["charity_contacts"]

    # -------------------- Public listing --------------------

    @router.get("")
    async def list_charities(
        user=Depends(get_current_user),
        q: Optional[str] = Query(None, description="Search by name or mission"),
        category: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        country: Optional[str] = Query(None),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0, le=10_000),
    ):
        query: Dict[str, Any] = {"status": "approved"}
        if category and category in ALLOWED_CATEGORIES:
            query["category"] = category
        if state:
            query["state"] = {"$regex": f"^{re.escape(state)}$", "$options": "i"}
        if country and country.upper() in ALLOWED_COUNTRIES:
            query["country"] = country.upper()
        if q:
            esc = re.escape(q.strip())
            query["$or"] = [
                {"name": {"$regex": esc, "$options": "i"}},
                {"mission": {"$regex": esc, "$options": "i"}},
                {"city": {"$regex": esc, "$options": "i"}},
            ]
        cursor = charities.find(query).sort([("approved_at", -1), ("created_at", -1)]).skip(offset).limit(limit)
        items = [_public_charity(d) async for d in cursor]
        total = await charities.count_documents(query)
        return {"items": items, "total": total, "categories": ALLOWED_CATEGORIES}

    @router.get("/categories")
    async def list_categories(user=Depends(get_current_user)):
        # Returns categories with friendly labels (kept in code, not DB).
        labels = {
            "food_bank": "Food banks",
            "homeless": "Homeless outreach",
            "pro_life": "Pro-life",
            "education": "Catholic education",
            "missions": "Missions",
            "youth": "Youth ministry",
            "elderly": "Elderly care",
            "refugees": "Refugees & immigrants",
            "healthcare": "Healthcare",
            "disability": "Disability ministry",
            "addiction_recovery": "Addiction recovery",
            "prison_ministry": "Prison ministry",
            "general": "General",
        }
        return {
            "categories": [{"key": k, "label": labels.get(k, k.replace("_", " ").title())} for k in ALLOWED_CATEGORIES],
        }

    @router.get("/{charity_id}")
    async def get_charity(charity_id: str, user=Depends(get_current_user)):
        doc = await charities.find_one({"charity_id": charity_id})
        if not doc:
            raise HTTPException(status_code=404, detail="charity not found")
        if doc.get("status") != "approved":
            # Non-public unless the requester is admin or the submitter.
            if not getattr(user, "is_admin", False) and doc.get("submitted_by") != user.user_id:
                raise HTTPException(status_code=404, detail="charity not found")
        return _public_charity(doc)

    # -------------------- User submission --------------------

    @router.post("/submit")
    async def submit_charity(body: CharityIn, user=Depends(get_current_user)):
        now = datetime.now(timezone.utc)
        # Prevent obvious duplicates: same name + same city.
        dup = await charities.find_one({
            "name": {"$regex": f"^{re.escape(body.name)}$", "$options": "i"},
            "city": {"$regex": f"^{re.escape(body.city)}$", "$options": "i"} if body.city else "",
            "status": {"$in": ["pending", "approved"]},
        }) if body.city else None
        if dup:
            raise HTTPException(status_code=409, detail="A charity with that name in that city is already submitted")

        # Admin submissions auto-approve.
        auto_approve = bool(getattr(user, "is_admin", False))
        doc = {
            "charity_id": f"chr_{uuid.uuid4().hex[:12]}",
            "name": body.name,
            "mission": body.mission,
            "category": body.category,
            "city": body.city,
            "state": body.state,
            "country": body.country,
            "website": body.website,
            "email": body.email,
            "phone": body.phone,
            "logo_url": body.logo_url,
            "status": "approved" if auto_approve else "pending",
            "submitted_by": user.user_id,
            "approved_by": user.user_id if auto_approve else None,
            "approved_at": now if auto_approve else None,
            "claimed_by": None,
            "claim_status": None,
            "created_at": now,
            "updated_at": now,
        }
        await charities.insert_one(doc)
        return _admin_charity(doc) if auto_approve else _public_charity(doc)

    @router.get("/mine/submissions")
    async def my_submissions(user=Depends(get_current_user)):
        cursor = charities.find({"submitted_by": user.user_id}).sort("created_at", -1)
        out = []
        async for d in cursor:
            row = _public_charity(d)
            row["status"] = d.get("status")
            out.append(row)
        return {"items": out}

    # -------------------- Claim flow --------------------

    @router.post("/{charity_id}/claim")
    async def request_claim(charity_id: str, body: ClaimIn, user=Depends(get_current_user)):
        c = await charities.find_one({"charity_id": charity_id})
        if not c or c.get("status") != "approved":
            raise HTTPException(status_code=404, detail="charity not found")
        if c.get("claimed_by") and c["claimed_by"] != user.user_id:
            raise HTTPException(status_code=409, detail="Charity is already claimed by another user")

        # Prevent double-pending requests for the same user/charity.
        existing = await claims.find_one({
            "charity_id": charity_id,
            "user_id": user.user_id,
            "status": "pending",
        })
        if existing:
            return {"ok": True, "claim_id": existing["claim_id"], "status": "pending"}

        claim_id = f"clm_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        await claims.insert_one({
            "claim_id": claim_id,
            "charity_id": charity_id,
            "user_id": user.user_id,
            "user_email": user.email,
            "user_name": user.name,
            "message": body.message,
            "status": "pending",
            "requested_at": now,
            "decided_at": None,
            "decided_by": None,
        })
        # Mark the charity so the admin can see at-a-glance.
        await charities.update_one(
            {"charity_id": charity_id, "claimed_by": None},
            {"$set": {"claim_status": "pending", "updated_at": now}},
        )
        return {"ok": True, "claim_id": claim_id, "status": "pending"}

    # -------------------- "I'm interested" volunteer contact --------------------

    @router.post("/{charity_id}/contact")
    async def i_am_interested(charity_id: str, body: InterestIn, user=Depends(get_current_user)):
        c = await charities.find_one({"charity_id": charity_id, "status": "approved"})
        if not c:
            raise HTTPException(status_code=404, detail="charity not found")
        now = datetime.now(timezone.utc)
        contact_id = f"cnt_{uuid.uuid4().hex[:12]}"
        await contacts.insert_one({
            "contact_id": contact_id,
            "charity_id": charity_id,
            "user_id": user.user_id,
            "user_email": user.email,
            "user_name": user.name,
            "message": body.message,
            "created_at": now,
        })
        # TODO once SendGrid/Resend is configured: dispatch an email to the
        # charity's `email` with the volunteer's contact info.
        return {
            "ok": True,
            "contact_id": contact_id,
            "charity_email": c.get("email"),
            "note": (
                "Your interest has been recorded. We'll forward your details to the "
                "charity once email delivery is configured."
            ),
        }

    # -------------------- Admin --------------------

    @router.get("/admin/list")
    async def admin_list(
        user=Depends(get_current_user),
        status: Optional[str] = Query(None),
        limit: int = Query(200, ge=1, le=500),
    ):
        await _ensure_admin(user)
        q: Dict[str, Any] = {}
        if status:
            q["status"] = status
        cursor = charities.find(q).sort([("created_at", -1)]).limit(limit)
        return {"items": [_admin_charity(d) async for d in cursor]}

    @router.post("/admin/{charity_id}/approve")
    async def admin_approve(charity_id: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        c = await charities.find_one({"charity_id": charity_id})
        if not c:
            raise HTTPException(status_code=404, detail="charity not found")
        now = datetime.now(timezone.utc)
        await charities.update_one(
            {"charity_id": charity_id},
            {"$set": {
                "status": "approved",
                "approved_by": user.user_id,
                "approved_at": now,
                "updated_at": now,
            }},
        )
        c.update({"status": "approved", "approved_by": user.user_id, "approved_at": now})
        return _admin_charity(c)

    @router.post("/admin/{charity_id}/reject")
    async def admin_reject(charity_id: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        res = await charities.update_one(
            {"charity_id": charity_id},
            {"$set": {"status": "rejected", "updated_at": datetime.now(timezone.utc)}},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="charity not found")
        return {"ok": True}

    @router.patch("/admin/{charity_id}")
    async def admin_patch(charity_id: str, body: CharityPatch, user=Depends(get_current_user)):
        await _ensure_admin(user)
        existing = await charities.find_one({"charity_id": charity_id})
        if not existing:
            raise HTTPException(status_code=404, detail="charity not found")
        patch: Dict[str, Any] = {}
        for k, v in body.dict(exclude_unset=True).items():
            if k == "status":
                if v not in ("pending", "approved", "archived", "rejected"):
                    raise HTTPException(status_code=400, detail="invalid status")
                patch[k] = v
            elif k == "category" and v not in ALLOWED_CATEGORIES:
                patch[k] = DEFAULT_CATEGORY
            elif k == "country" and v not in ALLOWED_COUNTRIES:
                patch[k] = "US"
            else:
                patch[k] = v
        if not patch:
            return _admin_charity(existing)
        patch["updated_at"] = datetime.now(timezone.utc)
        await charities.update_one({"charity_id": charity_id}, {"$set": patch})
        existing.update(patch)
        return _admin_charity(existing)

    @router.delete("/admin/{charity_id}")
    async def admin_archive(charity_id: str, user=Depends(get_current_user)):
        """Soft-delete by archiving (preserves history for claims/contacts)."""
        await _ensure_admin(user)
        res = await charities.update_one(
            {"charity_id": charity_id},
            {"$set": {"status": "archived", "updated_at": datetime.now(timezone.utc)}},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="charity not found")
        return {"ok": True}

    # --- Claims admin ---

    @router.get("/admin/claims")
    async def admin_list_claims(user=Depends(get_current_user), status: Optional[str] = Query("pending")):
        await _ensure_admin(user)
        q: Dict[str, Any] = {}
        if status:
            q["status"] = status
        cursor = claims.find(q).sort("requested_at", -1).limit(500)
        out: List[Dict[str, Any]] = []
        async for d in cursor:
            charity = await charities.find_one({"charity_id": d["charity_id"]}, {"name": 1, "city": 1, "state": 1})
            out.append({
                "claim_id": d["claim_id"],
                "charity_id": d["charity_id"],
                "charity_name": (charity or {}).get("name"),
                "charity_location": ", ".join(filter(None, [(charity or {}).get("city"), (charity or {}).get("state")])),
                "user_id": d["user_id"],
                "user_email": d.get("user_email"),
                "user_name": d.get("user_name"),
                "message": d.get("message"),
                "status": d.get("status"),
                "requested_at": _iso(d.get("requested_at")),
            })
        return {"items": out}

    @router.post("/admin/claims/{claim_id}/approve")
    async def admin_approve_claim(claim_id: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        c = await claims.find_one({"claim_id": claim_id})
        if not c:
            raise HTTPException(status_code=404, detail="claim not found")
        now = datetime.now(timezone.utc)
        await claims.update_one({"claim_id": claim_id}, {"$set": {
            "status": "approved", "decided_at": now, "decided_by": user.user_id,
        }})
        await charities.update_one({"charity_id": c["charity_id"]}, {"$set": {
            "claimed_by": c["user_id"], "claim_status": "approved", "updated_at": now,
        }})
        # Reject all other pending claims for the same charity.
        await claims.update_many(
            {"charity_id": c["charity_id"], "status": "pending", "claim_id": {"$ne": claim_id}},
            {"$set": {"status": "superseded", "decided_at": now, "decided_by": user.user_id}},
        )
        return {"ok": True}

    @router.post("/admin/claims/{claim_id}/reject")
    async def admin_reject_claim(claim_id: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        c = await claims.find_one({"claim_id": claim_id})
        if not c:
            raise HTTPException(status_code=404, detail="claim not found")
        now = datetime.now(timezone.utc)
        await claims.update_one({"claim_id": claim_id}, {"$set": {
            "status": "rejected", "decided_at": now, "decided_by": user.user_id,
        }})
        # Clear pending flag on charity if no other pending claims remain.
        remaining = await claims.count_documents({"charity_id": c["charity_id"], "status": "pending"})
        if remaining == 0:
            await charities.update_one(
                {"charity_id": c["charity_id"], "claimed_by": None},
                {"$set": {"claim_status": None, "updated_at": now}},
            )
        return {"ok": True}

    # --- Volunteer interest admin ---

    @router.get("/admin/contacts")
    async def admin_list_contacts(user=Depends(get_current_user), charity_id: Optional[str] = Query(None)):
        await _ensure_admin(user)
        q: Dict[str, Any] = {}
        if charity_id:
            q["charity_id"] = charity_id
        cursor = contacts.find(q).sort("created_at", -1).limit(500)
        return {"items": [
            {
                "contact_id": d["contact_id"],
                "charity_id": d["charity_id"],
                "user_id": d["user_id"],
                "user_email": d.get("user_email"),
                "user_name": d.get("user_name"),
                "message": d.get("message"),
                "created_at": _iso(d.get("created_at")),
            }
            async for d in cursor
        ]}

    return router


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db["charities"].create_index("charity_id", unique=True)
    await db["charities"].create_index([("status", 1), ("approved_at", -1)])
    await db["charities"].create_index([("category", 1), ("state", 1)])
    await db["charities"].create_index("submitted_by")
    await db["charity_claims"].create_index("claim_id", unique=True)
    await db["charity_claims"].create_index([("charity_id", 1), ("status", 1)])
    await db["charity_claims"].create_index([("user_id", 1), ("status", 1)])
    await db["charity_contacts"].create_index("contact_id", unique=True)
    await db["charity_contacts"].create_index([("charity_id", 1), ("created_at", -1)])

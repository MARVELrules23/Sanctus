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

    # Attach quote-management routes (admin CRUD + public list).
    _attach_quote_routes(router, db, get_current_user)

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

    @router.get("/quotes")
    async def list_quotes_public(user=Depends(get_current_user), limit: int = Query(100, ge=1, le=300)):
        """Logged-in users get the full active quote pool; the frontend picks
        one deterministically per charity_id. Defined here (above
        `/{charity_id}`) so FastAPI's literal-vs-param route matching doesn't
        treat "quotes" as a charity_id."""
        await _seed_quotes_if_empty(db)
        cursor = db["charity_quotes"].find({"active": True}).sort(
            [("sort_order", 1), ("created_at", 1)]
        ).limit(limit)
        return {"items": [_public_quote(d) async for d in cursor]}

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
# Charity Quotes (admin-editable content surfaced on the charity detail page)
# ---------------------------------------------------------------------------


# Initial seed — used the first time the `charity_quotes` collection is empty.
# Admin can edit, deactivate, or add to these freely afterwards.
SEED_CHARITY_QUOTES: List[Dict[str, Optional[str]]] = [
    {"text": "Charity is the bond of perfection. Without it, the rich man is poor; with it, the poor man is rich.", "source": "St. Augustine of Hippo", "context": "Sermon 350"},
    {"text": "Not to enable the poor to share in our goods is to steal from them and deprive them of life. The goods we possess are not ours, but theirs.", "source": "St. John Chrysostom", "context": "Homily on Lazarus"},
    {"text": "The bread which you do not use is the bread of the hungry; the garment hanging in your wardrobe is the garment of the one who is naked.", "source": "St. Basil the Great", "context": "Sermon to the Rich"},
    {"text": "If you wish to be perfect, give what you have to the poor and you will have treasure in heaven.", "source": "St. Ambrose of Milan", "context": None},
    {"text": "Charity is the form of all the virtues. It is the soul of every other virtue.", "source": "St. Thomas Aquinas", "context": "Summa Theologiae II-II, q.23"},
    {"text": "It is not enough to give bread. We must give the bread of love, the bread of dignity.", "source": "St. Vincent de Paul", "context": None},
    {"text": "You will find out that charity is a heavy burden to carry, heavier than the bowl of soup and the full basket. But you will keep your gentleness and your smile.", "source": "St. Vincent de Paul", "context": None},
    {"text": "Spread love everywhere you go. Let no one ever come to you without leaving happier.", "source": "St. Teresa of Calcutta", "context": None},
    {"text": "Not all of us can do great things. But we can do small things with great love.", "source": "St. Teresa of Calcutta", "context": None},
    {"text": "The fruit of love is service, which is compassion in action.", "source": "St. Teresa of Calcutta", "context": None},
    {"text": "Charity is certainly greater than any rule. Moreover, all rules must lead to charity.", "source": "St. Vincent de Paul", "context": None},
    {"text": "He who distributes the milk of human kindness cannot help but receive it again upon his own lips.", "source": "St. Francis de Sales", "context": "Introduction to the Devout Life"},
    {"text": "Charity is patient, is kind. Without it, our works are as nothing.", "source": "St. Paul the Apostle", "context": "1 Corinthians 13:4"},
    {"text": "Remember that you have only one soul; that you have only one death to die; that you have only one life. If you do this, there will be many things about which you care nothing.", "source": "St. Teresa of Ávila", "context": None},
    {"text": "Whenever a Christian sees a poor person, he must see in him the face of Christ.", "source": "St. John Paul II", "context": "Homily, 1985"},
    {"text": "Even the smallest act of love is a stone laid in the foundation of God's Kingdom.", "source": "Bl. Pier Giorgio Frassati", "context": None},
    {"text": "I see Jesus in every human being. I say to myself, this is hungry Jesus, I must feed him.", "source": "St. Teresa of Calcutta", "context": None},
    {"text": "The measure of love is to love without measure.", "source": "St. Francis de Sales", "context": None},
    {"text": "The poor are not a problem; they are a resource from which to draw to welcome and live the essence of the Gospel.", "source": "Pope Francis", "context": "Message for the World Day of the Poor"},
    {"text": "Charity is the cement which binds communities to God and persons to one another.", "source": "Ven. Fulton J. Sheen", "context": None},
    {"text": "Love is repaid by love alone.", "source": "St. Thérèse of Lisieux", "context": None},
    {"text": "I have found the paradox, that if you love until it hurts, there can be no more hurt, only more love.", "source": "St. Teresa of Calcutta", "context": None},
    {"text": "Real charity does the most good to those who receive it, and asks the least in return.", "source": "Ven. Solanus Casey", "context": None},
    {"text": "Do not be afraid of holiness. It will take away none of your energy, vitality, or joy.", "source": "Pope Francis", "context": "Gaudete et Exsultate"},
    {"text": "I would rather make mistakes in kindness than work miracles in unkindness.", "source": "St. Teresa of Calcutta", "context": None},
    {"text": "It is in giving that we receive; it is in pardoning that we are pardoned; it is in dying that we are born to eternal life.", "source": "St. Francis of Assisi", "context": "Peace Prayer"},
    {"text": "Start by doing what's necessary; then do what's possible; and suddenly you are doing the impossible.", "source": "St. Francis of Assisi", "context": None},
    {"text": "If you really want to love Jesus, first learn to suffer, because suffering teaches you to love.", "source": "St. Gemma Galgani", "context": None},
    {"text": "The poor person is a scandal who is also our salvation, for in him Christ comes to meet us.", "source": "Bl. Frédéric Ozanam", "context": "Founder of the Society of St. Vincent de Paul"},
    {"text": "When you have given alms, you have done nothing. You owe a debt of love which only love can repay.", "source": "St. Augustine of Hippo", "context": None},
]


class QuoteCreateModel(BaseModel):
    text: str = Field(..., min_length=4, max_length=800)
    source: str = Field(..., min_length=1, max_length=160)
    context: Optional[str] = Field(None, max_length=240)
    active: bool = True

    @field_validator("text", "source")
    @classmethod
    def _strip(cls, v: str) -> str:  # noqa: D401
        v = (v or "").strip()
        if not v:
            raise ValueError("required")
        return v


class QuotePatchModel(BaseModel):
    text: Optional[str] = Field(None, min_length=4, max_length=800)
    source: Optional[str] = Field(None, min_length=1, max_length=160)
    context: Optional[str] = Field(None, max_length=240)
    active: Optional[bool] = None


def _public_quote(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "quote_id": doc["quote_id"],
        "text": doc.get("text") or "",
        "source": doc.get("source") or "",
        "context": doc.get("context") or None,
    }


def _admin_quote(doc: Dict[str, Any]) -> Dict[str, Any]:
    base = _public_quote(doc)
    base.update({
        "active": bool(doc.get("active", True)),
        "created_by": doc.get("created_by"),
        "created_at": _iso(doc.get("created_at")),
        "updated_at": _iso(doc.get("updated_at")),
        "seed": bool(doc.get("seed", False)),
    })
    return base


async def _seed_quotes_if_empty(db: AsyncIOMotorDatabase) -> int:
    """One-time seed of the curated quotes the first time the collection is
    empty. Returns number of quotes inserted (0 if already populated)."""
    col = db["charity_quotes"]
    n = await col.count_documents({})
    if n > 0:
        return 0
    now = datetime.now(timezone.utc)
    docs = []
    for i, q in enumerate(SEED_CHARITY_QUOTES):
        docs.append({
            "quote_id": f"qte_{uuid.uuid4().hex[:10]}",
            "text": (q.get("text") or "").strip(),
            "source": (q.get("source") or "").strip(),
            "context": (q.get("context") or None),
            "active": True,
            "seed": True,
            "created_by": "system",
            "created_at": now,
            "updated_at": now,
            "sort_order": i,
        })
    if docs:
        await col.insert_many(docs)
    return len(docs)


def _attach_quote_routes(router: APIRouter, db: AsyncIOMotorDatabase, get_current_user: Callable) -> None:
    """Admin CRUD endpoints for `charity_quotes`. The public `GET /quotes`
    endpoint is registered inline in `build_router` to sit above the
    parameterized `/{charity_id}` route."""
    quotes = db["charity_quotes"]

    # --- Admin CRUD ---

    @router.get("/admin/quotes")
    async def admin_list_quotes(user=Depends(get_current_user)):
        await _ensure_admin(user)
        await _seed_quotes_if_empty(db)
        cursor = quotes.find({}).sort([("sort_order", 1), ("created_at", 1)])
        return {"items": [_admin_quote(d) async for d in cursor]}

    @router.post("/admin/quotes")
    async def admin_create_quote(payload: QuoteCreateModel, user=Depends(get_current_user)):
        await _ensure_admin(user)
        now = datetime.now(timezone.utc)
        # Append to the end of the sort order.
        last = await quotes.find_one(sort=[("sort_order", -1)])
        next_order = (last.get("sort_order", -1) + 1) if last else 0
        doc = {
            "quote_id": f"qte_{uuid.uuid4().hex[:10]}",
            "text": payload.text.strip(),
            "source": payload.source.strip(),
            "context": (payload.context or "").strip() or None,
            "active": payload.active,
            "seed": False,
            "created_by": getattr(user, "user_id", None),
            "created_at": now,
            "updated_at": now,
            "sort_order": next_order,
        }
        await quotes.insert_one(doc)
        return _admin_quote(doc)

    @router.patch("/admin/quotes/{quote_id}")
    async def admin_patch_quote(quote_id: str, payload: QuotePatchModel, user=Depends(get_current_user)):
        await _ensure_admin(user)
        doc = await quotes.find_one({"quote_id": quote_id})
        if not doc:
            raise HTTPException(status_code=404, detail="quote not found")
        updates: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        if payload.text is not None:
            updates["text"] = payload.text.strip()
        if payload.source is not None:
            updates["source"] = payload.source.strip()
        if payload.context is not None:
            updates["context"] = (payload.context or "").strip() or None
        if payload.active is not None:
            updates["active"] = bool(payload.active)
        await quotes.update_one({"quote_id": quote_id}, {"$set": updates})
        doc = await quotes.find_one({"quote_id": quote_id})
        return _admin_quote(doc)  # type: ignore[arg-type]

    @router.post("/admin/quotes/{quote_id}/toggle")
    async def admin_toggle_quote(quote_id: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        doc = await quotes.find_one({"quote_id": quote_id})
        if not doc:
            raise HTTPException(status_code=404, detail="quote not found")
        new_active = not bool(doc.get("active", True))
        await quotes.update_one(
            {"quote_id": quote_id},
            {"$set": {"active": new_active, "updated_at": datetime.now(timezone.utc)}},
        )
        doc["active"] = new_active
        return _admin_quote(doc)

    @router.delete("/admin/quotes/{quote_id}")
    async def admin_delete_quote(quote_id: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        r = await quotes.delete_one({"quote_id": quote_id})
        if r.deleted_count == 0:
            raise HTTPException(status_code=404, detail="quote not found")
        return {"ok": True}


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
    await db["charity_quotes"].create_index("quote_id", unique=True)
    await db["charity_quotes"].create_index([("active", 1), ("sort_order", 1)])
    # Seed default quotes once.
    try:
        n = await _seed_quotes_if_empty(db)
        if n:
            logger.info("charity_quotes: seeded %d default quotes", n)
    except Exception as e:  # noqa: BLE001
        logger.warning("charity_quotes seed skipped: %s", e)

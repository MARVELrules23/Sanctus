"""Saint / Blessed / Venerable of the Day.

Surfaces one verified Catholic holy person per calendar day on the Today tab
plus a detail screen with biography and a recommended action in their honor.

Design choices:

  * Three ranks are supported — Saint (canonized), Blessed (beatified), and
    Venerable (heroic-virtue declared). The pool spans all three; the Roman
    Calendar primarily fills Saint feast days, with Blessed/Venerable used
    on quieter days or as secondary commemorations.

  * **Strict approval flow.** AI proposes; an admin reviews each entry; only
    `status="approved"` rows are ever returned to the public API. This
    prevents misattributed quotes (a known Catholic-internet plague) and
    inappropriate or doctrinally weak content from reaching users.

  * Quotes must include a *source* (book, letter, sermon, encyclical) so the
    admin can verify before approval. Claude is instructed to refuse rather
    than fabricate when a verifiable quote isn't available.

  * Picture URLs default to Wikimedia Commons (public-domain, App-Store-safe).
    Admins can swap to an uploaded base64 image. No copyrighted holy cards.

  * "Today's saint" resolution:
      1. Find approved entries whose `feast_date` matches today's MM-DD.
      2. If multiple, prefer `is_primary=True`; then by rank (saint > blessed
         > venerable); ties broken alphabetically for stability.
      3. If none, fall back to a rotating pool of approved entries (oldest
         last-shown first) so quiet days still get content.

Indexes (created in server.py on startup):
  saints: saint_id unique; feast_date; status; (status, feast_date);
          (status, last_shown_at).
"""
from __future__ import annotations

import hashlib  # noqa: F401 — retained in case future seeding logic needs it
import json
import logging
import re
import uuid
from datetime import date as _date, datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("sanctus.saints")


RANKS = {"saint", "blessed", "venerable"}
RANK_ORDER = {"saint": 0, "blessed": 1, "venerable": 2}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SaintModel(BaseModel):
    saint_id: str
    name: str
    rank: str  # saint | blessed | venerable
    feast_date: Optional[str] = None  # "MM-DD" — None for venerables w/ no fixed feast
    is_primary: bool = True

    picture_url: Optional[str] = None
    picture_source: Optional[str] = None  # e.g. "Wikimedia Commons (public domain)"

    quote: str
    quote_source: str  # citation — REQUIRED so reviewers can verify

    biography: str  # 250-450 words
    recommended_action: str

    status: str = "draft"  # draft | approved | rejected
    proposed_by_ai: bool = False
    proposed_at: datetime
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    last_shown_at: Optional[datetime] = None

    @field_validator("rank")
    @classmethod
    def _rank(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if v not in RANKS:
            raise ValueError(f"rank must be one of {sorted(RANKS)}")
        return v

    @field_validator("feast_date")
    @classmethod
    def _feast(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        v = v.strip()
        if not re.match(r"^\d{2}-\d{2}$", v):
            raise ValueError("feast_date must be MM-DD")
        return v


class ProposeRequest(BaseModel):
    """Admin endpoint: ask Claude to propose a Saint/Blessed/Venerable for a date."""
    date: str  # YYYY-MM-DD — we extract MM-DD for the feast match
    rank_hint: Optional[str] = None  # optional preferred rank
    name_hint: Optional[str] = None  # optional explicit name to research
    is_primary: bool = True


class SaintUpdate(BaseModel):
    name: Optional[str] = None
    rank: Optional[str] = None
    feast_date: Optional[str] = None
    is_primary: Optional[bool] = None
    picture_url: Optional[str] = None
    picture_source: Optional[str] = None
    quote: Optional[str] = None
    quote_source: Optional[str] = None
    biography: Optional[str] = None
    recommended_action: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mmdd(yyyymmdd: str) -> str:
    """Extract MM-DD from a YYYY-MM-DD string. Raises if malformed."""
    try:
        d = _date.fromisoformat(yyyymmdd)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"bad date: {e}")
    return f"{d.month:02d}-{d.day:02d}"


def _public(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Strip internal-only fields when returning to clients."""
    return {
        "saint_id": doc["saint_id"],
        "name": doc["name"],
        "rank": doc["rank"],
        "feast_date": doc.get("feast_date"),
        "is_primary": doc.get("is_primary", True),
        "picture_url": doc.get("picture_url"),
        "picture_source": doc.get("picture_source"),
        "quote": doc["quote"],
        "quote_source": doc["quote_source"],
        "biography": doc["biography"],
        "recommended_action": doc["recommended_action"],
    }


def _admin_public(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Like _public but also includes review metadata. Admin only."""
    base = _public(doc)
    base.update({
        "status": doc.get("status", "draft"),
        "proposed_by_ai": bool(doc.get("proposed_by_ai")),
        "proposed_at": _iso(doc.get("proposed_at")),
        "approved_at": _iso(doc.get("approved_at")),
        "approved_by": doc.get("approved_by"),
        "last_shown_at": _iso(doc.get("last_shown_at")),
    })
    return base


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _rank_priority(doc: Dict[str, Any]) -> int:
    return RANK_ORDER.get(doc.get("rank", "venerable"), 99)


async def _ensure_admin(user) -> None:
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")


# ---------------------------------------------------------------------------
# Claude proposal
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a careful Catholic researcher preparing a "Saint/Blessed/Venerable of the Day" \
entry for a reverent Catholic mobile app. Output ONLY a single valid JSON object, no \
markdown fencing, no commentary.

Required JSON schema:
{
  "name": "Saint Ephrem the Syrian",       // full canonical name with title prefix
  "rank": "saint" | "blessed" | "venerable",
  "feast_date": "MM-DD" or null,            // Roman Calendar feast date if any
  "quote": "...",                            // verbatim 1-3 sentence quotation by the person
  "quote_source": "Hymns on Faith 5.17",     // SPECIFIC citation; refuse if no verifiable source
  "biography": "...",                        // 250-400 words, third person, plain prose
  "recommended_action": "...",               // 1-2 sentences: concrete devotional or charitable act in their honor
  "picture_url": "https://upload.wikimedia.org/..." or null,  // Wikimedia Commons public-domain image only
  "picture_source": "Wikimedia Commons (public domain)" or null
}

Hard rules:
  - The quote MUST be one the person actually said or wrote. If you are not >95% certain \
    of the quote AND its specific source, do NOT make one up — instead set "quote" to an \
    empty string and explain in the biography that a verifiable quotation is pending.
  - Do not use the apocryphal "Preach the gospel, use words if necessary" or similar \
    widely-misattributed quotes.
  - Biography: factual, doctrinally faithful, no flowery hagiography. Include life dates, \
    works, path to canonization/beatification/declaration of heroic virtue.
  - Recommended action: a single, concrete invitation appropriate to the person's charism \
    (almsgiving, contemplative prayer, fasting, corporal/spiritual works of mercy, etc.).
  - Picture URL must be on upload.wikimedia.org or commons.wikimedia.org and depict \
    public-domain artwork — no copyrighted holy cards. If unsure, leave null.
  - Output JSON only. No prose around it. No code fences.
"""


def _build_user_block(req: ProposeRequest, exclude_names: Optional[List[str]] = None) -> str:
    """Compose the per-call user prompt for Claude.

    `exclude_names` is the list of already-proposed/approved saints for the
    same MM-DD; we ask the model to pick someone *different* so admins don't
    keep getting the same headline saint on every "Propose" click.
    """
    mmdd = _mmdd(req.date)
    lines = [
        f"Prepare an entry for the Roman Catholic feast day {mmdd} (MM-DD).",
    ]
    if req.name_hint:
        lines.append(f"Specifically research: {req.name_hint.strip()}.")
    else:
        lines.append("Choose the most prominent Saint/Blessed/Venerable with a feast on that date.")
    if req.rank_hint:
        lines.append(f"Prefer rank: {req.rank_hint.strip().lower()}.")
    if not req.is_primary:
        lines.append(
            "This is a SECONDARY commemoration for that date — feel free to pick a "
            "lesser-known holy person whose feast also falls on this day."
        )
    # Exclusion list — the most important fix for "the AI keeps regurgitating
    # the same Saint". Without this, every call from the admin's perspective
    # tends to land on the headline saint of the day (e.g., St. Barnabas on
    # 06-11). With it, the model is forced to surface other commemorations.
    if exclude_names and not req.name_hint:
        formatted = ", ".join(f'"{n}"' for n in exclude_names[:25])
        lines.append(
            "IMPORTANT — Do NOT propose any of these (they are already in the "
            f"library for {mmdd}): {formatted}. Pick a DIFFERENT holy person "
            "whose feast or memorial also falls on this date — older or modern, "
            "Eastern Catholic, regional, religious-order patron, or a Blessed "
            "/ Venerable whose cause is still open. Confirm the date in your "
            "biography text."
        )
    # Final reminders that have measurably improved field completeness.
    lines.append(
        "REQUIRED: `quote_source` must always be filled when `quote` is "
        "filled (cite a primary text, papal document, scripture, or hagiography). "
        "If you cannot cite a real source, leave BOTH `quote` and `quote_source` "
        "as empty strings — never a quote without a source."
    )
    lines.append("Return JSON only.")
    return "\n".join(lines)


def _extract_json(raw: str) -> Dict[str, Any]:
    """Tolerate Claude occasionally wrapping JSON in prose or code fences."""
    text = (raw or "").strip()
    # Remove ```json ... ``` fences if present
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    # Find first { ... last }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output")
    return json.loads(text[start : end + 1])


# ---------------------------------------------------------------------------
# Public selection logic
# ---------------------------------------------------------------------------


async def _resolve_today(
    db: AsyncIOMotorDatabase, mmdd: str
) -> tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Returns (primary, secondaries) for the given MM-DD.

    Primary is the headline card. Secondaries are the "more from today"
    expandable list. Both contain only approved entries.

    Falls back to a rotation of approved-but-undated entries if no feast match.
    """
    cursor = db.saints.find(
        {"status": "approved", "feast_date": mmdd},
        {"_id": 0},
    )
    matches = [doc async for doc in cursor]
    if matches:
        matches.sort(
            key=lambda d: (
                0 if d.get("is_primary") else 1,
                _rank_priority(d),
                d.get("name", "").lower(),
            )
        )
        primary, *rest = matches
        return primary, rest

    # Fallback rotation: oldest last_shown_at first, ignore feast_date.
    cursor = (
        db.saints.find(
            {"status": "approved"},
            {"_id": 0},
        )
        .sort([("last_shown_at", 1), ("approved_at", 1)])
        .limit(1)
    )
    fallback = [doc async for doc in cursor]
    if fallback:
        return fallback[0], []
    return None, []


# ---------------------------------------------------------------------------
# Router builder
# ---------------------------------------------------------------------------


def build_router(
    db: AsyncIOMotorDatabase,
    get_user: Callable,
    emergent_llm_key: str,
) -> APIRouter:
    from emergentintegrations.llm.chat import LlmChat, UserMessage  # local import (matches catechism.py pattern)

    router = APIRouter(prefix="/saints", tags=["saints"])

    # ----- Public endpoints -----

    @router.get("/today")
    async def today(
        date: str = Query(..., description="YYYY-MM-DD"),
        user=Depends(get_user),
    ):
        mmdd = _mmdd(date)
        primary, rest = await _resolve_today(db, mmdd)
        if not primary:
            return {"date": date, "primary": None, "others": []}

        # Touch last_shown_at so the rotation pool stays fair.
        await db.saints.update_one(
            {"saint_id": primary["saint_id"]},
            {"$set": {"last_shown_at": _now()}},
        )
        return {
            "date": date,
            "primary": _public(primary),
            "others": [_public(d) for d in rest],
        }

    @router.get("/{saint_id}")
    async def get_one(saint_id: str, user=Depends(get_user)):
        doc = await db.saints.find_one({"saint_id": saint_id}, {"_id": 0})
        if not doc or doc.get("status") != "approved":
            # Admins can read drafts via the admin endpoints below.
            raise HTTPException(status_code=404, detail="saint not found")
        return _public(doc)

    # ----- Admin endpoints -----

    @router.get("/admin/list")
    async def admin_list(
        status: Optional[str] = Query(None, description="draft|approved|rejected"),
        limit: int = Query(100, ge=1, le=500),
        user=Depends(get_user),
    ):
        await _ensure_admin(user)
        q: Dict[str, Any] = {}
        if status:
            q["status"] = status
        cursor = (
            db.saints.find(q, {"_id": 0})
            .sort([("status", 1), ("feast_date", 1), ("proposed_at", -1)])
            .limit(limit)
        )
        items = [_admin_public(doc) async for doc in cursor]
        return {"items": items, "count": len(items)}

    @router.post("/admin/propose")
    async def admin_propose(req: ProposeRequest, user=Depends(get_user)):
        await _ensure_admin(user)
        if not emergent_llm_key:
            raise HTTPException(status_code=503, detail="LLM unavailable")

        mmdd = _mmdd(req.date)

        # Pull existing saint names for the same MM-DD (any status) so we can
        # ask the model NOT to repeat them. This is the primary fix for "AI
        # keeps regurgitating the same Saint each time". The previous version
        # used a deterministic session_id derived from (date, hint, rank) and
        # no exclusion list, so Claude returned the same headline saint over
        # and over until the admin manually edited the hint.
        existing_cursor = db.saints.find(
            {"feast_date": mmdd},
            {"_id": 0, "name": 1, "status": 1},
        )
        existing_names: List[str] = []
        async for d in existing_cursor:
            nm = (d.get("name") or "").strip()
            if nm and nm not in existing_names:
                existing_names.append(nm)

        user_block = _build_user_block(req, exclude_names=existing_names)

        # FRESH session per call — uuid4-based, no caching. Previously this
        # was a sha1 hash of (date, hint, rank, primary), which meant repeat
        # clicks landed in the SAME Claude session and the SDK happily
        # replayed the same answer.
        session_id = f"saints-propose-{uuid.uuid4().hex[:12]}"

        try:
            chat = LlmChat(
                api_key=emergent_llm_key,
                session_id=session_id,
                system_message=SYSTEM_PROMPT,
            ).with_model("anthropic", "claude-sonnet-4-5-20250929")
            response = await chat.send_message(UserMessage(text=user_block))
        except Exception as e:
            logger.exception("saints propose LLM call failed: %s", e)
            raise HTTPException(status_code=502, detail="LLM proposal failed; please retry.")

        try:
            data = _extract_json(response or "")
        except Exception as e:
            logger.warning("saints propose: bad JSON from model — %s\n%s", e, response)
            raise HTTPException(status_code=502, detail="Model returned malformed JSON.")

        # Coerce + validate.
        try:
            doc = SaintModel(
                saint_id=f"st_{uuid.uuid4().hex[:14]}",
                name=str(data.get("name") or "").strip(),
                rank=str(data.get("rank") or "saint").strip().lower(),
                feast_date=(data.get("feast_date") or mmdd),
                is_primary=bool(req.is_primary),
                picture_url=(data.get("picture_url") or None),
                picture_source=(data.get("picture_source") or None),
                quote=str(data.get("quote") or "").strip(),
                quote_source=str(data.get("quote_source") or "").strip(),
                biography=str(data.get("biography") or "").strip(),
                recommended_action=str(data.get("recommended_action") or "").strip(),
                status="draft",
                proposed_by_ai=True,
                proposed_at=_now(),
            )
        except Exception as e:
            logger.warning("saints propose: validation failed — %s", e)
            raise HTTPException(status_code=502, detail=f"Model output invalid: {e}")

        if not doc.name or not doc.biography or not doc.recommended_action:
            raise HTTPException(
                status_code=502,
                detail="Model returned incomplete entry; please retry.",
            )

        await db.saints.insert_one(doc.model_dump())
        return _admin_public(doc.model_dump())

    @router.post("/admin/manual")
    async def admin_manual_create(body: SaintUpdate, user=Depends(get_user)):
        """Create a saint entry directly without AI (for fully hand-curated entries)."""
        await _ensure_admin(user)
        try:
            doc = SaintModel(
                saint_id=f"st_{uuid.uuid4().hex[:14]}",
                name=(body.name or "").strip(),
                rank=(body.rank or "saint").strip().lower(),
                feast_date=body.feast_date,
                is_primary=bool(body.is_primary) if body.is_primary is not None else True,
                picture_url=body.picture_url,
                picture_source=body.picture_source,
                quote=(body.quote or "").strip(),
                quote_source=(body.quote_source or "").strip(),
                biography=(body.biography or "").strip(),
                recommended_action=(body.recommended_action or "").strip(),
                status="draft",
                proposed_by_ai=False,
                proposed_at=_now(),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        if not doc.name or not doc.biography:
            raise HTTPException(status_code=400, detail="name and biography are required")
        await db.saints.insert_one(doc.model_dump())
        return _admin_public(doc.model_dump())

    @router.patch("/admin/{saint_id}")
    async def admin_update(saint_id: str, body: SaintUpdate, user=Depends(get_user)):
        await _ensure_admin(user)
        existing = await db.saints.find_one({"saint_id": saint_id}, {"_id": 0})
        if not existing:
            raise HTTPException(status_code=404, detail="saint not found")
        patch: Dict[str, Any] = {}
        for field, value in body.model_dump(exclude_none=True).items():
            patch[field] = value
        # Validate the merged doc against the model so bad updates fail loudly.
        merged = {**existing, **patch}
        try:
            SaintModel(**{
                k: merged.get(k) for k in SaintModel.model_fields.keys() if k in merged or k in SaintModel.model_fields
            })
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"validation failed: {e}")
        if patch:
            await db.saints.update_one({"saint_id": saint_id}, {"$set": patch})
        doc = await db.saints.find_one({"saint_id": saint_id}, {"_id": 0})
        return _admin_public(doc)

    @router.post("/admin/{saint_id}/approve")
    async def admin_approve(saint_id: str, user=Depends(get_user)):
        await _ensure_admin(user)
        existing = await db.saints.find_one({"saint_id": saint_id}, {"_id": 0})
        if not existing:
            raise HTTPException(status_code=404, detail="saint not found")
        # Refuse to approve obviously incomplete entries.
        for required in ("name", "biography", "recommended_action", "quote_source"):
            if not (existing.get(required) or "").strip():
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot approve — '{required}' is empty",
                )
        if not (existing.get("quote") or "").strip():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Cannot approve — quote field is empty. Fill in a verified "
                    "quote or use the manual edit endpoint to set one."
                ),
            )
        patch = {
            "status": "approved",
            "approved_at": _now(),
            "approved_by": user.user_id,
        }
        await db.saints.update_one({"saint_id": saint_id}, {"$set": patch})
        doc = await db.saints.find_one({"saint_id": saint_id}, {"_id": 0})
        return _admin_public(doc)

    @router.post("/admin/{saint_id}/reject")
    async def admin_reject(saint_id: str, user=Depends(get_user)):
        await _ensure_admin(user)
        r = await db.saints.update_one(
            {"saint_id": saint_id},
            {"$set": {"status": "rejected"}},
        )
        if r.matched_count == 0:
            raise HTTPException(status_code=404, detail="saint not found")
        return {"ok": True}

    @router.delete("/admin/{saint_id}")
    async def admin_delete(saint_id: str, user=Depends(get_user)):
        await _ensure_admin(user)
        r = await db.saints.delete_one({"saint_id": saint_id})
        if r.deleted_count == 0:
            raise HTTPException(status_code=404, detail="saint not found")
        return {"ok": True}

    return router

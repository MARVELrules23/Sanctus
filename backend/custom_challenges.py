"""User-created ("custom") challenges.

A personal challenge the user builds themselves: a title, a colour, a length
(7 / 14 / 30 / 60 days), a start date, and PER-DAY entries. Each day of the
span holds its own list of items across five kinds:

    abstinence · prayer · charity · adoration · virtue  (+ 'other')

These overlay the liturgical calendar just like the built-in liturgical
challenges (always shown, independent of the master toggle) and can be opened
to see and check off each day's practices.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, field_validator

ALLOWED_LENGTHS = {7, 14, 30, 60}
ALLOWED_CATEGORIES = {"abstinence", "prayer", "charity", "adoration", "virtue", "other"}
DEFAULT_COLOR = "#B08D3F"  # Sanctus gold


class ChallengeItem(BaseModel):
    category: str
    text: str

    @field_validator("category")
    @classmethod
    def _cat(cls, v: str) -> str:
        v = (v or "other").strip().lower()
        return v if v in ALLOWED_CATEGORIES else "other"

    @field_validator("text")
    @classmethod
    def _text(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("item text cannot be empty")
        return v[:280]


class ChallengeDay(BaseModel):
    day: int
    items: List[ChallengeItem] = []


class CustomChallengeCreate(BaseModel):
    title: str
    color: Optional[str] = None
    length_days: int
    start_date: str  # YYYY-MM-DD
    days: List[ChallengeDay] = []

    @field_validator("title")
    @classmethod
    def _title(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("title is required")
        return v[:120]

    @field_validator("length_days")
    @classmethod
    def _len(cls, v: int) -> int:
        if v not in ALLOWED_LENGTHS:
            raise ValueError("length_days must be one of 7, 14, 30, 60")
        return v


def _parse_date(v: str) -> date:
    try:
        return datetime.strptime(v, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="start_date must be YYYY-MM-DD")


def _iso(dt: Any) -> Optional[str]:
    if isinstance(dt, datetime):
        return dt.date().isoformat()
    if isinstance(dt, date):
        return dt.isoformat()
    return dt


def _public(doc: Dict[str, Any]) -> Dict[str, Any]:
    start = doc.get("start_date")
    start_d = start.date() if isinstance(start, datetime) else start
    length = int(doc.get("length_days") or 7)
    end_d = (start_d + timedelta(days=length - 1)) if start_d else None
    return {
        "challenge_id": doc["challenge_id"],
        "title": doc.get("title", ""),
        "color": doc.get("color") or DEFAULT_COLOR,
        "length_days": length,
        "start_date": _iso(start_d),
        "end_date": end_d.isoformat() if end_d else None,
        "days": doc.get("days", []),
        "completed": doc.get("completed", {}),
        "created_at": _iso(doc.get("created_at")),
    }


def _window(doc: Dict[str, Any]) -> Dict[str, Any]:
    """ChallengeWindow-shaped payload for the calendar overlay."""
    p = _public(doc)
    return {
        "challenge_id": f"custom-{p['challenge_id']}",
        "slug": p["challenge_id"],
        "name": p["title"],
        "subtitle": "My challenge",
        "color": p["color"],
        "icon": "create-outline",
        "start_date": p["start_date"],
        "end_date": p["end_date"],
        "total_days": p["length_days"],
        "status": "custom",
    }


def build_router(db: AsyncIOMotorDatabase, get_current_user, *_ignore) -> APIRouter:
    router = APIRouter(prefix="/custom-challenges", tags=["custom-challenges"])
    col = db["custom_challenges"]

    @router.post("")
    async def create(payload: CustomChallengeCreate, user=Depends(get_current_user)):
        start_d = _parse_date(payload.start_date)
        # Normalise the days list to exactly length_days, 1-indexed.
        by_day = {d.day: [i.model_dump() for i in d.items] for d in payload.days}
        days = [{"day": n, "items": by_day.get(n, [])} for n in range(1, payload.length_days + 1)]
        doc = {
            "challenge_id": uuid.uuid4().hex[:12],
            "user_id": user.user_id,
            "title": payload.title,
            "color": (payload.color or DEFAULT_COLOR).strip() or DEFAULT_COLOR,
            "length_days": payload.length_days,
            "start_date": datetime.combine(start_d, time.min, tzinfo=timezone.utc),
            "days": days,
            "completed": {},
            "created_at": datetime.now(timezone.utc),
        }
        await col.insert_one(doc)
        return _public(doc)

    @router.get("")
    async def list_mine(user=Depends(get_current_user)):
        cur = col.find({"user_id": user.user_id}).sort([("start_date", 1)])
        return {"items": [_public(d) async for d in cur]}

    @router.get("/windows")
    async def windows(year: int, user=Depends(get_current_user)):
        y0 = f"{year}-01-01"
        y1 = f"{year}-12-31"
        items: List[Dict[str, Any]] = []
        async for d in col.find({"user_id": user.user_id}):
            w = _window(d)
            # keep only challenges whose span intersects the requested year
            if w["start_date"] and w["end_date"] and w["start_date"] <= y1 and w["end_date"] >= y0:
                items.append(w)
        return {"items": items}

    @router.get("/{challenge_id}")
    async def detail(challenge_id: str, user=Depends(get_current_user)):
        doc = await col.find_one({"challenge_id": challenge_id, "user_id": user.user_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Challenge not found")
        return _public(doc)

    @router.post("/{challenge_id}/checkin")
    async def checkin(challenge_id: str, payload: Dict[str, Any], user=Depends(get_current_user)):
        doc = await col.find_one({"challenge_id": challenge_id, "user_id": user.user_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Challenge not found")
        day = int(payload.get("day") or 0)
        idx = int(payload.get("item_index") or 0)
        done = bool(payload.get("done"))
        key = f"{day}:{idx}"
        completed = doc.get("completed", {}) or {}
        if done:
            completed[key] = True
        else:
            completed.pop(key, None)
        await col.update_one({"_id": doc["_id"]}, {"$set": {"completed": completed}})
        doc["completed"] = completed
        return _public(doc)

    @router.delete("/{challenge_id}")
    async def delete(challenge_id: str, user=Depends(get_current_user)):
        res = await col.delete_one({"challenge_id": challenge_id, "user_id": user.user_id})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Challenge not found")
        return {"ok": True}

    return router

"""Sanctus — Schedule.

A personal weekly/one-off schedule that the user layers on top of the
liturgical calendar. Each item repeats on chosen days of the week (or falls on
a single date), with an optional time of day. Items can be meals, workouts,
an active virtue plan, an enrolled liturgical challenge, or a free-typed custom
entry.

Reminders are scheduled on-device by the client (expo-notifications); the
client stores the returned notification IDs here so they can be cancelled and
rescheduled on edit/delete. The backend is the source of truth for the schedule
itself and does not send notifications.

All endpoints are prefixed `/api/schedule` and require auth. Free for all.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone, date as _date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

KINDS = {"meal", "workout", "virtue", "challenge", "custom"}
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")  # 24h HH:MM
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

DEFAULTS = {
    "meal":      {"icon": "restaurant-outline", "color": "#C99A4A"},
    "workout":   {"icon": "barbell-outline",    "color": "#3E5C76"},
    "virtue":    {"icon": "sparkles-outline",   "color": "#8A4A6C"},
    "challenge": {"icon": "flame-outline",       "color": "#9C3B2E"},
    "custom":    {"icon": "ellipse-outline",     "color": "#5B7553"},
}


def _dow_of(date_str: str) -> int:
    """Sunday=0 .. Saturday=6 for a YYYY-MM-DD string."""
    d = _date.fromisoformat(date_str)
    return d.isoweekday() % 7  # Mon=1..Sun=7 -> Mon=1..Sat=6, Sun=0


class ScheduleItemBody(BaseModel):
    kind: str = "custom"
    title: str
    note: Optional[str] = None
    recurrence: str = "weekly"          # "weekly" | "once"
    days_of_week: List[int] = Field(default_factory=list)  # 0=Sun..6=Sat
    date: Optional[str] = None          # YYYY-MM-DD for "once"
    time: Optional[str] = None          # 24h HH:MM, or null for all-day
    ref_slug: Optional[str] = None      # challenge slug
    ref_id: Optional[str] = None        # virtue plan id
    icon: Optional[str] = None
    color: Optional[str] = None
    notify: bool = False
    notif_ids: Optional[List[str]] = None


def _validate(body: ScheduleItemBody) -> Dict[str, Any]:
    kind = body.kind if body.kind in KINDS else "custom"
    title = (body.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="A title is required.")
    rec = "once" if body.recurrence == "once" else "weekly"
    dows: List[int] = []
    date_val: Optional[str] = None
    if rec == "weekly":
        dows = sorted({int(d) for d in (body.days_of_week or []) if 0 <= int(d) <= 6})
        if not dows:
            raise HTTPException(status_code=400, detail="Pick at least one day of the week.")
    else:
        date_val = (body.date or "").strip()
        if not _DATE_RE.match(date_val or ""):
            raise HTTPException(status_code=400, detail="A valid date is required for a one-off item.")
    time_val: Optional[str] = None
    if body.time:
        t = body.time.strip()
        if not _TIME_RE.match(t):
            raise HTTPException(status_code=400, detail="Time must be HH:MM (24-hour).")
        time_val = t
    d = DEFAULTS.get(kind, DEFAULTS["custom"])
    return {
        "kind": kind,
        "title": title[:120],
        "note": (body.note or "").strip()[:500] or None,
        "recurrence": rec,
        "days_of_week": dows,
        "date": date_val,
        "time": time_val,
        "ref_slug": body.ref_slug,
        "ref_id": body.ref_id,
        "icon": body.icon or d["icon"],
        "color": body.color or d["color"],
        "notify": bool(body.notify),
        "notif_ids": [str(x) for x in (body.notif_ids or [])][:31],
    }


def _shape(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": doc["id"],
        "kind": doc.get("kind", "custom"),
        "title": doc.get("title", ""),
        "note": doc.get("note"),
        "recurrence": doc.get("recurrence", "weekly"),
        "days_of_week": doc.get("days_of_week", []),
        "date": doc.get("date"),
        "time": doc.get("time"),
        "ref_slug": doc.get("ref_slug"),
        "ref_id": doc.get("ref_id"),
        "icon": doc.get("icon"),
        "color": doc.get("color"),
        "notify": bool(doc.get("notify")),
        "notif_ids": doc.get("notif_ids", []),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def _occurs_on(item: Dict[str, Any], date_str: str, dow: int) -> bool:
    if item.get("recurrence") == "once":
        return item.get("date") == date_str
    return dow in (item.get("days_of_week") or [])


def _time_sort_key(item: Dict[str, Any]):
    # timed items first (sorted by time), all-day items last
    t = item.get("time")
    return (1, "99:99") if not t else (0, t)


def build_router(db: AsyncIOMotorDatabase, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/schedule", tags=["schedule"])
    col = db["schedule_items"]

    @router.get("")
    async def list_items(user=Depends(get_current_user)):
        cur = col.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", 1)
        items = [_shape(d) async for d in cur]
        return {"items": items}

    @router.get("/day/{date_str}")
    async def items_for_day(date_str: str, user=Depends(get_current_user)):
        if not _DATE_RE.match(date_str):
            raise HTTPException(status_code=400, detail="Bad date")
        dow = _dow_of(date_str)
        cur = col.find({"user_id": user.user_id}, {"_id": 0})
        items = [d async for d in cur if _occurs_on(d, date_str, dow)]
        items.sort(key=_time_sort_key)
        return {"date": date_str, "items": [_shape(d) for d in items]}

    @router.get("/sources")
    async def sources(user=Depends(get_current_user)):
        """Active virtue plans + enrolled liturgical challenges to schedule."""
        today = _date.today().isoformat()
        # Active virtue plans
        plans: List[Dict[str, Any]] = []
        async for p in db.virtue_plans.find({"user_id": user.user_id}, {"_id": 0}):
            if (p.get("end_date") or today) >= today:
                names = ", ".join(
                    s.replace("-", " ").title() for s in (p.get("virtue_slugs") or [])
                )
                plans.append({
                    "ref_id": p["id"],
                    "title": names or "Virtue plan",
                    "end_date": p.get("end_date"),
                })
        # Enrolled challenges
        chals: List[Dict[str, Any]] = []
        async for enr in db.challenge_enrollments.find({"user_id": user.user_id}, {"_id": 0}):
            slug = enr.get("challenge_slug")
            if not slug:
                continue
            ch = await db.challenges.find_one({"slug": slug}, {"_id": 0})
            if not ch:
                continue
            chals.append({
                "ref_slug": slug,
                "title": ch.get("name") or slug,
                "color": ch.get("color"),
                "icon": ch.get("icon"),
                "patron_saint": ch.get("patron_saint"),
            })
        return {"virtue_plans": plans, "challenges": chals}

    @router.post("")
    async def create_item(body: ScheduleItemBody, user=Depends(get_current_user)):
        data = _validate(body)
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "id": f"sch_{uuid.uuid4().hex[:12]}",
            "user_id": user.user_id,
            **data,
            "created_at": now,
            "updated_at": now,
        }
        await col.insert_one(doc)
        return _shape(doc)

    @router.put("/{item_id}")
    async def update_item(item_id: str, body: ScheduleItemBody, user=Depends(get_current_user)):
        existing = await col.find_one({"id": item_id, "user_id": user.user_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Schedule item not found")
        data = _validate(body)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await col.update_one({"id": item_id}, {"$set": data})
        merged = {**existing, **data}
        return _shape(merged)

    @router.put("/{item_id}/notif-ids")
    async def set_notif_ids(item_id: str, payload: Dict[str, Any], user=Depends(get_current_user)):
        ids = [str(x) for x in (payload.get("notif_ids") or [])][:31]
        res = await col.update_one(
            {"id": item_id, "user_id": user.user_id},
            {"$set": {"notif_ids": ids, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Schedule item not found")
        return {"ok": True, "notif_ids": ids}

    @router.delete("/{item_id}")
    async def delete_item(item_id: str, user=Depends(get_current_user)):
        doc = await col.find_one({"id": item_id, "user_id": user.user_id}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Schedule item not found")
        await col.delete_one({"id": item_id})
        # return the deleted item's notif_ids so the client can cancel them
        return {"ok": True, "notif_ids": doc.get("notif_ids", [])}

    return router

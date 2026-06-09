"""
Parish Events — community-submitted Catholic events tied to churches.

Design choices that shaped this module:

  * Any signed-in user can submit an event tied to either a saved church or a
    free-floating geo coordinate (some events — outdoor processions, retreats
    at private venues — have no formal parish "church_id"). Both shapes are
    stored uniformly.
  * Visibility is open to anyone whose `lat/lng` is within radius_m of the
    event, OR who has the event's church saved. We do NOT require following
    or friending — Catholic events are inherently public.
  * Reporting is lightweight: a single `POST /flag` increments a counter and
    records the reporter, with auto-hide at 3 unique flags. No moderator
    panel yet — keep things small until we see the volume.
  * The submitter owns their event (`DELETE` allowed only by author).
  * Times are stored as ISO-8601 UTC; the client is responsible for showing
    in local timezone. We never trust the client's clock for `created_at`.

Indexes (created on startup in server.py):
  parish_events: (lat,lng) 2dsphere; (church_id, start_at); (created_at);
                 (organizer_user_id, created_at); (removed, start_at).
"""
from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("sanctus.parish_events")


EVENT_TYPES = {
    "mass",          # Special Masses (vigils, feast days, healing Masses)
    "confession",    # Reconciliation availability
    "adoration",     # Eucharistic adoration / holy hour
    "talk",          # Catechetical talk, speaker, parish mission night
    "retreat",       # Day-of-recollection or multi-day retreat
    "service",       # Service / works-of-mercy projects
    "young_adult",   # Young-adult specific gathering
    "social",        # Parish potluck, festival, fish fry
    "rosary",        # Public rosary, rosary rally
    "other",
}

EVENT_TYPE_LABELS = {
    "mass": "Mass",
    "confession": "Confession",
    "adoration": "Adoration",
    "talk": "Talk / Speaker",
    "retreat": "Retreat",
    "service": "Service",
    "young_adult": "Young Adults",
    "social": "Parish Social",
    "rosary": "Rosary",
    "other": "Other",
}

AUTO_HIDE_FLAG_COUNT = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _parse_iso(s: str) -> datetime:
    # Accept "...Z" or "+00:00"
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid datetime: {s} ({e})")


def _haversine_km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    """Rough great-circle distance, used for the response payload (the actual
    radius filter uses MongoDB's $geoWithin centerSphere)."""
    R = 6371.0
    p1 = math.radians(a_lat)
    p2 = math.radians(b_lat)
    dp = math.radians(b_lat - a_lat)
    dl = math.radians(b_lng - a_lng)
    s = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(s))


def _shape(doc: Dict[str, Any], viewer_user_id: Optional[str] = None) -> Dict[str, Any]:
    out = {
        "id": doc.get("id"),
        "type": doc.get("type"),
        "type_label": EVENT_TYPE_LABELS.get(doc.get("type", ""), "Event"),
        "title": doc.get("title"),
        "description": doc.get("description") or "",
        "start_at": _iso(doc.get("start_at")),
        "end_at": _iso(doc.get("end_at")),
        "church_id": doc.get("church_id"),
        "church_name": doc.get("church_name"),
        "address": doc.get("address") or "",
        "lat": doc.get("lat"),
        "lng": doc.get("lng"),
        "organizer_user_id": doc.get("organizer_user_id"),
        "organizer_name": doc.get("organizer_name"),
        "created_at": _iso(doc.get("created_at")),
        "flag_count": int(doc.get("flag_count", 0) or 0),
        "is_owner": bool(viewer_user_id and viewer_user_id == doc.get("organizer_user_id")),
        "has_flagged": bool(
            viewer_user_id and viewer_user_id in (doc.get("flagged_by") or [])
        ),
    }
    return out


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class CreateEventRequest(BaseModel):
    type: str
    title: str = Field(..., min_length=3, max_length=120)
    description: Optional[str] = Field(None, max_length=2000)
    start_at: str
    end_at: Optional[str] = None
    church_id: Optional[str] = None
    church_name: Optional[str] = Field(None, max_length=160)
    address: Optional[str] = Field(None, max_length=240)
    lat: float
    lng: float

    @field_validator("type")
    @classmethod
    def _type_known(cls, v: str) -> str:
        if v not in EVENT_TYPES:
            raise ValueError(f"unknown type '{v}'")
        return v

    @field_validator("lat")
    @classmethod
    def _lat_range(cls, v: float) -> float:
        if not (-90.0 <= v <= 90.0):
            raise ValueError("lat out of range")
        return v

    @field_validator("lng")
    @classmethod
    def _lng_range(cls, v: float) -> float:
        if not (-180.0 <= v <= 180.0):
            raise ValueError("lng out of range")
        return v


class FlagRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=240)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def build_router(db: AsyncIOMotorDatabase, get_user) -> APIRouter:
    router = APIRouter(prefix="/parish-events", tags=["parish-events"])

    # ------------------------- list -----------------------------------------
    @router.get("")
    async def list_events(
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_m: int = Query(40000, ge=1000, le=400000),
        church_id: Optional[str] = None,
        event_type: Optional[str] = None,
        days: int = Query(30, ge=1, le=180),
        user=Depends(get_user),
    ):
        now = _now()
        until = now + timedelta(days=days)

        filt: Dict[str, Any] = {
            "removed": {"$ne": True},
            "start_at": {"$gte": now - timedelta(hours=2), "$lte": until},
        }

        # If `church_id` provided, exact-match it. Otherwise prefer
        # proximity-based search via 2dsphere `centerSphere`.
        if church_id:
            filt["church_id"] = church_id
        elif lat is not None and lng is not None:
            # centerSphere expects [[lng, lat], radius_in_radians].
            # 1 radian ≈ 6378.1 km on Earth, so divide meters by 6378137.
            radius_rad = radius_m / 6378137.0
            filt["loc"] = {
                "$geoWithin": {
                    "$centerSphere": [[lng, lat], radius_rad]
                }
            }

        if event_type:
            if event_type not in EVENT_TYPES:
                raise HTTPException(status_code=400, detail="unknown event_type")
            filt["type"] = event_type

        cursor = db.parish_events.find(filt).sort("start_at", 1).limit(200)
        rows = await cursor.to_list(length=200)

        items = []
        for r in rows:
            shaped = _shape(r, viewer_user_id=user.user_id)
            if lat is not None and lng is not None and r.get("lat") and r.get("lng"):
                shaped["distance_km"] = round(
                    _haversine_km(lat, lng, float(r["lat"]), float(r["lng"])), 1
                )
            items.append(shaped)
        return {"items": items, "count": len(items)}

    # ------------------------- create --------------------------------------
    @router.post("")
    async def create_event(payload: CreateEventRequest, user=Depends(get_user)):
        start_dt = _parse_iso(payload.start_at)
        end_dt = _parse_iso(payload.end_at) if payload.end_at else None

        if end_dt and end_dt <= start_dt:
            raise HTTPException(status_code=400, detail="end_at must be after start_at")
        if start_dt < _now() - timedelta(days=1):
            raise HTTPException(
                status_code=400,
                detail="start_at is in the past — please choose a future time.",
            )

        # Anti-spam: cap a user at 10 active events at once.
        active_n = await db.parish_events.count_documents({
            "organizer_user_id": user.user_id,
            "removed": {"$ne": True},
            "start_at": {"$gte": _now()},
        })
        if active_n >= 10:
            raise HTTPException(
                status_code=429,
                detail="You already have 10 active events — cancel one first.",
            )

        doc = {
            "id": f"pe_{uuid.uuid4().hex[:14]}",
            "type": payload.type,
            "title": payload.title.strip(),
            "description": (payload.description or "").strip() or None,
            "start_at": start_dt,
            "end_at": end_dt,
            "church_id": payload.church_id,
            "church_name": (payload.church_name or "").strip() or None,
            "address": (payload.address or "").strip() or None,
            "lat": float(payload.lat),
            "lng": float(payload.lng),
            # GeoJSON for $geoWithin/$nearSphere on the 2dsphere index.
            "loc": {"type": "Point", "coordinates": [float(payload.lng), float(payload.lat)]},
            "organizer_user_id": user.user_id,
            "organizer_name": getattr(user, "name", None) or "Anonymous",
            "created_at": _now(),
            "updated_at": _now(),
            "flag_count": 0,
            "flagged_by": [],
            "removed": False,
        }
        await db.parish_events.insert_one(doc)
        return _shape(doc, viewer_user_id=user.user_id)

    # ------------------------- detail --------------------------------------
    @router.get("/{event_id}")
    async def get_event(event_id: str, user=Depends(get_user)):
        doc = await db.parish_events.find_one({"id": event_id, "removed": {"$ne": True}})
        if not doc:
            raise HTTPException(status_code=404, detail="event not found")
        return _shape(doc, viewer_user_id=user.user_id)

    # ------------------------- delete (owner) ------------------------------
    @router.delete("/{event_id}")
    async def delete_event(event_id: str, user=Depends(get_user)):
        doc = await db.parish_events.find_one({"id": event_id})
        if not doc:
            raise HTTPException(status_code=404, detail="event not found")
        if doc.get("organizer_user_id") != user.user_id:
            raise HTTPException(status_code=403, detail="only the organizer can delete this event")
        await db.parish_events.update_one(
            {"id": event_id}, {"$set": {"removed": True, "removed_at": _now()}}
        )
        return {"ok": True}

    # ------------------------- flag ----------------------------------------
    @router.post("/{event_id}/flag")
    async def flag_event(event_id: str, payload: FlagRequest, user=Depends(get_user)):
        doc = await db.parish_events.find_one({"id": event_id})
        if not doc:
            raise HTTPException(status_code=404, detail="event not found")
        if doc.get("organizer_user_id") == user.user_id:
            raise HTTPException(status_code=400, detail="you can't flag your own event")
        if user.user_id in (doc.get("flagged_by") or []):
            return {"ok": True, "already_flagged": True}

        new_count = int(doc.get("flag_count", 0) or 0) + 1
        update: Dict[str, Any] = {
            "$addToSet": {"flagged_by": user.user_id},
            "$inc": {"flag_count": 1},
            "$push": {
                "flag_reasons": {
                    "user_id": user.user_id,
                    "reason": (payload.reason or "").strip() or None,
                    "at": _now(),
                }
            },
        }
        if new_count >= AUTO_HIDE_FLAG_COUNT:
            update["$set"] = {"removed": True, "removed_at": _now()}
        await db.parish_events.update_one({"id": event_id}, update)
        return {"ok": True, "auto_hidden": new_count >= AUTO_HIDE_FLAG_COUNT}

    # ------------------------- my events -----------------------------------
    @router.get("/me/list")
    async def my_events(user=Depends(get_user)):
        cursor = db.parish_events.find({
            "organizer_user_id": user.user_id,
            "removed": {"$ne": True},
        }).sort("start_at", 1).limit(50)
        rows = await cursor.to_list(length=50)
        return {"items": [_shape(r, viewer_user_id=user.user_id) for r in rows]}

    return router

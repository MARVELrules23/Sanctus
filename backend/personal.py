"""Personal (user-authored) prayers & devotionals.

Two lightweight, per-user content types:

  * Custom PRAYER      – a title + free-form prayer text the user writes.
  * Custom DEVOTIONAL  – the user picks a saint/angel (from the companions list
                         or free text) and writes their own criteria: an intro
                         plus a list of practices. Rendered companion-style.

Stored in the `custom_prayers` and `custom_devotions` collections.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, field_validator


def _iso(dt: Any) -> Optional[str]:
    if isinstance(dt, datetime):
        return dt.isoformat()
    return dt


# --------------------------------------------------------------------------- #
# Prayers
# --------------------------------------------------------------------------- #
class PrayerCreate(BaseModel):
    title: str
    body: str

    @field_validator("title")
    @classmethod
    def _t(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("title is required")
        return v[:160]

    @field_validator("body")
    @classmethod
    def _b(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("prayer text is required")
        return v[:8000]


def _prayer_public(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "prayer_id": doc["prayer_id"],
        "title": doc.get("title", ""),
        "body": doc.get("body", ""),
        "created_at": _iso(doc.get("created_at")),
    }


# --------------------------------------------------------------------------- #
# Devotionals
# --------------------------------------------------------------------------- #
class DevotionCreate(BaseModel):
    title: str
    saint_name: str
    saint_slug: Optional[str] = None
    intro: Optional[str] = ""
    practices: List[str] = []

    @field_validator("title", "saint_name")
    @classmethod
    def _req(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("required")
        return v[:160]

    @field_validator("practices")
    @classmethod
    def _pr(cls, v: List[str]) -> List[str]:
        out = [p.strip()[:400] for p in (v or []) if p and p.strip()]
        return out[:40]


def _devotion_public(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "devotion_id": doc["devotion_id"],
        "title": doc.get("title", ""),
        "saint_name": doc.get("saint_name", ""),
        "saint_slug": doc.get("saint_slug"),
        "intro": doc.get("intro", ""),
        "practices": doc.get("practices", []),
        "created_at": _iso(doc.get("created_at")),
    }


def build_router(db: AsyncIOMotorDatabase, get_current_user, *_ignore) -> APIRouter:
    router = APIRouter(prefix="/my", tags=["personal"])
    prayers = db["custom_prayers"]
    devotions = db["custom_devotions"]

    # ---- Prayers ----
    @router.post("/prayers")
    async def create_prayer(payload: PrayerCreate, user=Depends(get_current_user)):
        doc = {
            "prayer_id": uuid.uuid4().hex[:12],
            "user_id": user.user_id,
            "title": payload.title,
            "body": payload.body,
            "created_at": datetime.now(timezone.utc),
        }
        await prayers.insert_one(doc)
        return _prayer_public(doc)

    @router.get("/prayers")
    async def list_prayers(user=Depends(get_current_user)):
        cur = prayers.find({"user_id": user.user_id}).sort([("created_at", -1)])
        return {"items": [_prayer_public(d) async for d in cur]}

    @router.get("/prayers/{prayer_id}")
    async def get_prayer(prayer_id: str, user=Depends(get_current_user)):
        doc = await prayers.find_one({"prayer_id": prayer_id, "user_id": user.user_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Prayer not found")
        return _prayer_public(doc)

    @router.delete("/prayers/{prayer_id}")
    async def delete_prayer(prayer_id: str, user=Depends(get_current_user)):
        res = await prayers.delete_one({"prayer_id": prayer_id, "user_id": user.user_id})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Prayer not found")
        return {"ok": True}

    # ---- Devotionals ----
    @router.post("/devotions")
    async def create_devotion(payload: DevotionCreate, user=Depends(get_current_user)):
        doc = {
            "devotion_id": uuid.uuid4().hex[:12],
            "user_id": user.user_id,
            "title": payload.title,
            "saint_name": payload.saint_name,
            "saint_slug": (payload.saint_slug or None),
            "intro": (payload.intro or "").strip()[:4000],
            "practices": payload.practices,
            "created_at": datetime.now(timezone.utc),
        }
        await devotions.insert_one(doc)
        return _devotion_public(doc)

    @router.get("/devotions")
    async def list_devotions(user=Depends(get_current_user)):
        cur = devotions.find({"user_id": user.user_id}).sort([("created_at", -1)])
        return {"items": [_devotion_public(d) async for d in cur]}

    @router.get("/devotions/{devotion_id}")
    async def get_devotion(devotion_id: str, user=Depends(get_current_user)):
        doc = await devotions.find_one({"devotion_id": devotion_id, "user_id": user.user_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Devotional not found")
        return _devotion_public(doc)

    @router.delete("/devotions/{devotion_id}")
    async def delete_devotion(devotion_id: str, user=Depends(get_current_user)):
        res = await devotions.delete_one({"devotion_id": devotion_id, "user_id": user.user_id})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Devotional not found")
        return {"ok": True}

    return router

"""33-Day Consecration to St. Joseph.

A 33-day preparation that ends in an Act of Consecration to St. Joseph.
Traditionally begun on dates that end on a Josephite feast (the "set times").
From a companion's page a user may begin it ANY day; this module is the single
engine behind both entry points.

Each day carries a hand-authored title/theme (drawn from the titles and virtues
of St. Joseph) plus an AI-generated, permanently-cached meditation — mirroring
the Novena reflection pattern. Displayed text is auto-translated client-side.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger("sanctus.consecration")

MODEL = "claude-sonnet-4-5-20250929"
TOTAL_DAYS = 33

DAILY_PRAYER = (
    "To you, O blessed Joseph, do we come in our tribulation, and having implored "
    "the help of your most holy Spouse, we confidently invoke your patronage also. "
    "By that charity wherewith you were united to the Immaculate Virgin Mother of God, "
    "and by the fatherly love with which you embraced the Child Jesus, we beseech you "
    "to graciously regard the inheritance which Jesus Christ purchased by His Blood, "
    "and with your power and strength to aid us in our necessities. Amen."
)

ACT_OF_CONSECRATION = (
    "O dearest St. Joseph, I consecrate myself to you, that you may ever be my father, "
    "my protector, and my guide in the way of salvation. Obtain for me a great purity of "
    "heart and a fervent love of the interior life. After your example, may I do all my "
    "actions for the greater glory of God, in union with the Divine Heart of Jesus and the "
    "Immaculate Heart of Mary. And do you, O blessed Joseph, pray for me, that I may share "
    "in the peace and joy of your holy death. Amen."
)

# Recommended "set time" start windows (start_md, end feast). The 33rd day lands on the feast.
SET_TIMES = [
    {"start": "02-15", "feast": "St. Joseph, Spouse of Mary (March 19)"},
    {"start": "03-30", "feast": "St. Joseph the Worker (May 1)"},
    {"start": "10-20", "feast": "Patronage of St. Joseph (Nov 22)"},
    {"start": "11-06", "feast": "Immaculate Conception (Dec 8)"},
]

# 33 days — title + short theme. Weeks move from knowing Joseph to imitating him.
DAYS: List[Dict[str, str]] = [
    {"title": "St. Joseph, Son of David", "theme": "Joseph's royal lineage and humble heart"},
    {"title": "The Just Man", "theme": "Righteousness that listens and obeys"},
    {"title": "Spouse of the Mother of God", "theme": "His tender, chaste love for Mary"},
    {"title": "Guardian of the Redeemer", "theme": "Entrusted with Jesus Himself"},
    {"title": "Man of Silence", "theme": "Holiness that speaks through deeds, not words"},
    {"title": "Man of Faith", "theme": "Trusting God in darkness and uncertainty"},
    {"title": "Man of Obedience", "theme": "Rising at once to do God's will"},
    {"title": "The Worker of Nazareth", "theme": "Sanctifying ordinary daily labour"},
    {"title": "Provider for the Holy Family", "theme": "Faithful, hidden generosity"},
    {"title": "Protector of Jesus and Mary", "theme": "Guarding what God entrusts to us"},
    {"title": "Joseph the Chaste", "theme": "Purity of body and heart"},
    {"title": "Joseph the Humble", "theme": "Greatness hidden in lowliness"},
    {"title": "Joseph the Patient", "theme": "Bearing trials without complaint"},
    {"title": "Joseph the Courageous", "theme": "Strength to protect and to flee to Egypt"},
    {"title": "Joseph the Obedient Traveller", "theme": "Following God's lead step by step"},
    {"title": "Pillar of Families", "theme": "Holiness lived within the home"},
    {"title": "Model of Workers", "theme": "Offering work as prayer"},
    {"title": "Hope of the Sick", "theme": "Confidence in Joseph's intercession"},
    {"title": "Patron of the Dying", "theme": "Praying for a holy and peaceful death"},
    {"title": "Terror of Demons", "theme": "Spiritual protection through St. Joseph"},
    {"title": "Joseph, Mirror of Patience", "theme": "Quiet endurance in love"},
    {"title": "Lover of Poverty", "theme": "Freedom of heart, detachment from things"},
    {"title": "Joseph the Prayerful", "theme": "A life turned constantly toward God"},
    {"title": "Joseph the Tender Father", "theme": "Fatherly love that forms souls"},
    {"title": "Joseph the Faithful", "theme": "Constancy in duty, day after day"},
    {"title": "Joseph the Wise", "theme": "Discernment that seeks God's will"},
    {"title": "Joseph the Pure of Heart", "theme": "Seeing God in all things"},
    {"title": "Joseph the Devoted Spouse", "theme": "Self-giving love within vocation"},
    {"title": "Joseph the Sanctifier of Work", "theme": "Making the ordinary holy"},
    {"title": "Patron of the Universal Church", "theme": "Joseph's care for all God's people"},
    {"title": "Joseph, Our Intercessor", "theme": "Bringing every need to Jesus through him"},
    {"title": "Joseph, Teacher of Trust", "theme": "Surrendering the future to Providence"},
    {"title": "Act of Consecration to St. Joseph", "theme": "Giving yourself wholly to Jesus through Joseph"},
]


def _parse(d: str) -> date:
    return datetime.strptime(d, "%Y-%m-%d").date()


def _public_enrollment(e: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not e:
        return None
    start = e["start_date"]
    end = (_parse(start) + timedelta(days=TOTAL_DAYS - 1)).isoformat()
    completed = sorted(e.get("completed_days", []))
    current = min(TOTAL_DAYS, len(completed) + 1)
    return {
        "start_date": start, "end_date": end, "completed_days": completed,
        "status": e.get("status", "active"), "current_day": current, "total_days": TOTAL_DAYS,
    }


async def _meditation(db, emergent_llm_key: str, day: int) -> str:
    col = db["consecration_meditations"]
    found = await col.find_one({"day": day}, {"_id": 0, "text": 1})
    if found and found.get("text"):
        return found["text"]
    d = DAYS[day - 1]
    text = (f"Today we contemplate St. Joseph as {d['title']}. {d['theme']}.")
    if emergent_llm_key:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            system = ("You are a Catholic spiritual writer guiding a 33-day Consecration to St. Joseph. "
                      "Write a warm, faithful, doctrinally sound meditation of 90-130 words. No headings.")
            user = (f"Day {day} of 33. Title: '{d['title']}'. Theme: {d['theme']}. "
                    "Write a meditation drawing the reader to imitate St. Joseph and entrust themselves to Jesus "
                    "through him. End with one short sentence of resolution for the day.")
            chat = LlmChat(api_key=emergent_llm_key, session_id=f"consec-{day}", system_message=system).with_model("anthropic", MODEL)
            resp = await chat.send_message(UserMessage(text=user))
            if resp and resp.strip():
                text = resp.strip()
        except Exception as ex:  # noqa: BLE001
            logger.warning("consecration: meditation gen failed day %s: %s", day, repr(ex)[:120])
    await col.update_one({"day": day}, {"$set": {"day": day, "text": text}}, upsert=True)
    return text


class StartModel(BaseModel):
    start_date: str


class DayModel(BaseModel):
    day: int


def build_router(db: AsyncIOMotorDatabase, get_current_user, emergent_llm_key: str = "") -> APIRouter:
    router = APIRouter(prefix="/consecration", tags=["consecration"])
    enroll = db["consecration_enrollments"]

    async def _active(uid: str) -> Optional[Dict[str, Any]]:
        return await enroll.find_one({"user_id": uid, "status": "active"}, {"_id": 0})

    @router.get("")
    async def overview(user=Depends(get_current_user)):
        return {
            "title": "33-Day Consecration to St. Joseph",
            "intro": ("A 33-day journey to entrust yourself to Jesus through the heart of "
                      "St. Joseph. Traditionally begun on a set date ending in a Josephite feast — "
                      "but you may begin today and walk it any time of year."),
            "total_days": TOTAL_DAYS,
            "set_times": SET_TIMES,
            "days": [{"day": i + 1, **d} for i, d in enumerate(DAYS)],
            "daily_prayer": DAILY_PRAYER,
            "act_of_consecration": ACT_OF_CONSECRATION,
            "active": _public_enrollment(await _active(user.user_id)),
        }

    @router.post("/start")
    async def start(payload: StartModel, user=Depends(get_current_user)):
        try:
            _parse(payload.start_date)
        except Exception:
            raise HTTPException(status_code=400, detail="start_date must be YYYY-MM-DD")
        await enroll.update_many({"user_id": user.user_id, "status": "active"}, {"$set": {"status": "abandoned"}})
        await enroll.update_one(
            {"user_id": user.user_id, "start_date": payload.start_date},
            {"$set": {"user_id": user.user_id, "start_date": payload.start_date,
                      "completed_days": [], "status": "active",
                      "created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
        return {"active": _public_enrollment(await _active(user.user_id))}

    @router.post("/stop")
    async def stop(user=Depends(get_current_user)):
        await enroll.update_many({"user_id": user.user_id, "status": "active"}, {"$set": {"status": "abandoned"}})
        return {"ok": True}

    @router.post("/complete-day")
    async def complete_day(payload: DayModel, user=Depends(get_current_user)):
        e = await enroll.find_one({"user_id": user.user_id, "status": "active"})
        if not e:
            raise HTTPException(status_code=404, detail="No active consecration")
        done = set(e.get("completed_days", []))
        done.add(int(payload.day))
        status = "completed" if len(done) >= TOTAL_DAYS else "active"
        await enroll.update_one({"_id": e["_id"]}, {"$set": {"completed_days": sorted(done), "status": status}})
        return {"active": _public_enrollment(await _active(user.user_id)) if status == "active" else None, "status": status}

    @router.get("/day/{day}")
    async def get_day(day: int, user=Depends(get_current_user)):
        if day < 1 or day > TOTAL_DAYS:
            raise HTTPException(status_code=404, detail="Day out of range")
        d = DAYS[day - 1]
        return {
            "day": day, "total_days": TOTAL_DAYS, "title": d["title"], "theme": d["theme"],
            "meditation": await _meditation(db, emergent_llm_key, day),
            "daily_prayer": DAILY_PRAYER,
            "act_of_consecration": ACT_OF_CONSECRATION if day == TOTAL_DAYS else None,
        }

    return router

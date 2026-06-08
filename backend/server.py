"""Sanctus — Catholic-themed meal prep & workout scheduling backend."""
import os
import json
import uuid
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List

import httpx
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

from emergentintegrations.llm.chat import LlmChat, UserMessage

from liturgical import get_liturgical_day
from usccb import fetch_readings, usccb_url_for

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
SESSION_DATA_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

logger = logging.getLogger("sanctus")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

app = FastAPI(title="Sanctus API")
api = APIRouter(prefix="/api")


# ---------- Models ----------
class SessionExchangeRequest(BaseModel):
    session_id: str


class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None


class PreferencesPayload(BaseModel):
    dietary: Optional[str] = "balanced"  # e.g., balanced, vegetarian, low-carb
    allergies: Optional[str] = ""
    fitness_level: Optional[str] = "intermediate"  # beginner / intermediate / advanced
    fitness_goal: Optional[str] = "general fitness"
    devotion_focus: Optional[str] = "daily prayer"


class GenerateMealRequest(BaseModel):
    date: str  # YYYY-MM-DD


class GenerateWorkoutRequest(BaseModel):
    date: str


class MealItem(BaseModel):
    name: str
    description: str = ""
    ingredients: List[str] = []
    prep_minutes: int = 0


class SaveMealRequest(BaseModel):
    date: str
    breakfast: MealItem
    lunch: MealItem
    dinner: MealItem
    reflection: str = ""


class ExerciseItem(BaseModel):
    name: str
    sets: str = ""
    notes: str = ""


class SaveWorkoutRequest(BaseModel):
    date: str
    title: str
    focus: str = ""
    duration_minutes: int = 30
    exercises: List[ExerciseItem]
    opening_prayer: str = ""
    closing_prayer: str = ""
    reflection: str = ""


class SuggestMealSlotRequest(BaseModel):
    date: str
    slot: str  # breakfast | lunch | dinner
    hint: Optional[str] = None


class SuggestExerciseRequest(BaseModel):
    date: str
    focus: Optional[str] = None
    hint: Optional[str] = None


# ---------- Auth helpers ----------
async def ensure_indexes():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.user_sessions.create_index("session_token", unique=True)
    await db.user_sessions.create_index("user_id")
    await db.user_sessions.create_index("expires_at", expireAfterSeconds=0)
    await db.readings.create_index("date", unique=True)
    await db.journal.create_index("entry_id", unique=True)
    await db.journal.create_index([("user_id", 1), ("created_at", -1)])
    await db.journal.create_index([("user_id", 1), ("date", 1)])


async def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    exp = session.get("expires_at")
    if exp is not None:
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Session expired")
    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user)


# ---------- Auth routes ----------
@api.post("/auth/session")
async def auth_session(payload: SessionExchangeRequest):
    """Exchange a session_id from Emergent OAuth redirect for an app session."""
    async with httpx.AsyncClient(timeout=15.0) as cli:
        r = await cli.get(SESSION_DATA_URL, headers={"X-Session-ID": payload.session_id})
    if r.status_code != 200:
        logger.warning("session-data lookup failed: %s %s", r.status_code, r.text)
        raise HTTPException(status_code=401, detail="Invalid session_id")
    data = r.json()
    email = data["email"]
    name = data.get("name", email.split("@")[0])
    picture = data.get("picture")
    session_token = data["session_token"]

    # Upsert user by email
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one(
            {"user_id": user_id, "email": email, "name": name, "picture": picture,
             "created_at": datetime.now(timezone.utc)}
        )

    # Upsert session
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.update_one(
        {"session_token": session_token},
        {"$set": {
            "session_token": session_token,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
        }},
        upsert=True,
    )
    return {"session_token": session_token, "user": {"user_id": user_id, "email": email, "name": name, "picture": picture}}


@api.get("/auth/me")
async def auth_me(user: User = Depends(get_current_user)):
    return user


@api.post("/auth/logout")
async def auth_logout(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        return {"ok": True}
    token = authorization.split(" ", 1)[1].strip()
    await db.user_sessions.delete_one({"session_token": token})
    return {"ok": True}


# ---------- Liturgical routes ----------
@api.get("/liturgical/day")
async def liturgical_day(date: str):
    try:
        d = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    return get_liturgical_day(d)


@api.get("/liturgical/month")
async def liturgical_month(year: int, month: int):
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="month must be 1-12")
    # iterate days in month
    d = date(year, month, 1)
    days = []
    while d.month == month:
        days.append(get_liturgical_day(d))
        d += timedelta(days=1)
    return {"year": year, "month": month, "days": days}


# ---------- Preferences ----------
@api.get("/preferences")
async def get_prefs(user: User = Depends(get_current_user)):
    doc = await db.preferences.find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        return PreferencesPayload().model_dump()
    return {k: v for k, v in doc.items() if k != "user_id"}


@api.put("/preferences")
async def put_prefs(payload: PreferencesPayload, user: User = Depends(get_current_user)):
    data = payload.model_dump()
    await db.preferences.update_one(
        {"user_id": user.user_id},
        {"$set": {**data, "user_id": user.user_id}},
        upsert=True,
    )
    return data


# ---------- AI generation ----------
def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        # remove leading ``` and optional json
        first_nl = t.find("\n")
        if first_nl != -1:
            t = t[first_nl + 1:]
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


async def _chat_json(system: str, user_prompt: str, session_id: str) -> dict:
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    resp = await chat.send_message(UserMessage(text=user_prompt))
    raw = resp if isinstance(resp, str) else str(resp)
    cleaned = _strip_code_fence(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to locate JSON inside
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            return json.loads(cleaned[start:end + 1])
        raise HTTPException(status_code=502, detail="AI returned non-JSON response")


@api.post("/meals/generate")
async def generate_meal(payload: GenerateMealRequest, user: User = Depends(get_current_user)):
    try:
        d = datetime.strptime(payload.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    lit = get_liturgical_day(d)
    prefs = await db.preferences.find_one({"user_id": user.user_id}, {"_id": 0}) or PreferencesPayload().model_dump()

    system = (
        "You are a thoughtful Catholic nutrition coach. You craft a single day's meal plan that "
        "honors the Church's liturgical calendar — observing abstinence (no meat) on Fridays and during Lent, "
        "joyful, festive meals on solemnities and feast days, and simple, contemplative meals on penitential days. "
        "Always return strictly valid JSON. No prose outside JSON."
    )
    abstinence_note = "Today is a day of ABSTINENCE from meat — propose only fish, vegetarian, or seafood meals." if lit["is_abstinence"] else ""
    fast_note = "Today is a day of FAST — propose lighter, smaller meals." if lit["is_fast"] else ""
    feast_note = f"Today is the {lit['feast']} ({lit['rank']}) — propose a festive meal in joyful tradition." if lit.get("feast") and lit["rank"] in ("solemnity", "feast") else ""

    user_prompt = (
        f"Date: {lit['date']} | Season: {lit['season']} | Liturgical color: {lit['color']}.\n"
        f"{abstinence_note}\n{fast_note}\n{feast_note}\n"
        f"User preferences: dietary={prefs.get('dietary')}, allergies={prefs.get('allergies') or 'none'}.\n"
        "Return JSON shaped exactly like:\n"
        "{\n"
        "  \"breakfast\": {\"name\": str, \"description\": str, \"ingredients\": [str], \"prep_minutes\": int},\n"
        "  \"lunch\": {\"name\": str, \"description\": str, \"ingredients\": [str], \"prep_minutes\": int},\n"
        "  \"dinner\": {\"name\": str, \"description\": str, \"ingredients\": [str], \"prep_minutes\": int},\n"
        "  \"reflection\": str  // 1-2 sentence Catholic reflection tying the meal to the day\n"
        "}"
    )
    plan = await _chat_json(system, user_prompt, session_id=f"meals-{user.user_id}-{payload.date}")

    doc = {
        "user_id": user.user_id,
        "date": payload.date,
        "liturgical": lit,
        "plan": plan,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.meals.update_one(
        {"user_id": user.user_id, "date": payload.date},
        {"$set": doc},
        upsert=True,
    )
    return doc


@api.post("/workouts/generate")
async def generate_workout(payload: GenerateWorkoutRequest, user: User = Depends(get_current_user)):
    try:
        d = datetime.strptime(payload.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    lit = get_liturgical_day(d)
    prefs = await db.preferences.find_one({"user_id": user.user_id}, {"_id": 0}) or PreferencesPayload().model_dump()

    system = (
        "You are a Catholic fitness coach who pairs physical training with the liturgical season. "
        "Lent calls for penitential, disciplined workouts; Easter and feast days for joyful, energetic ones; "
        "Advent for steady preparation; Ordinary Time for balanced strength. "
        "Sundays are days of rest — propose only gentle movement (a walk, stretching) and a longer prayer focus. "
        "Always return strictly valid JSON. No prose outside JSON."
    )
    user_prompt = (
        f"Date: {lit['date']} | Day of week: {d.strftime('%A')} | Season: {lit['season']} | "
        f"Feast: {lit.get('feast') or 'none'}.\n"
        f"User: fitness_level={prefs.get('fitness_level')}, goal={prefs.get('fitness_goal')}.\n"
        "Return JSON shaped exactly like:\n"
        "{\n"
        "  \"title\": str,\n"
        "  \"focus\": str,  // e.g. 'Lenten Penitential Strength'\n"
        "  \"duration_minutes\": int,\n"
        "  \"exercises\": [{\"name\": str, \"sets\": str, \"notes\": str}],\n"
        "  \"opening_prayer\": str,  // a short Catholic prayer intention to begin\n"
        "  \"closing_prayer\": str,\n"
        "  \"reflection\": str  // 1-2 sentences tying physical effort to the liturgical season\n"
        "}"
    )
    plan = await _chat_json(system, user_prompt, session_id=f"workout-{user.user_id}-{payload.date}")
    doc = {
        "user_id": user.user_id,
        "date": payload.date,
        "liturgical": lit,
        "plan": plan,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.workouts.update_one(
        {"user_id": user.user_id, "date": payload.date},
        {"$set": doc},
        upsert=True,
    )
    return doc


@api.get("/meals")
async def get_meal(date: str, user: User = Depends(get_current_user)):
    doc = await db.meals.find_one({"user_id": user.user_id, "date": date}, {"_id": 0})
    return doc or {}


@api.get("/workouts")
async def get_workout(date: str, user: User = Depends(get_current_user)):
    doc = await db.workouts.find_one({"user_id": user.user_id, "date": date}, {"_id": 0})
    return doc or {}


@api.get("/meals/week")
async def get_meals_week(start: str, user: User = Depends(get_current_user)):
    try:
        d = datetime.strptime(start, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="start must be YYYY-MM-DD")
    dates = [(d + timedelta(days=i)).isoformat() for i in range(7)]
    docs = await db.meals.find(
        {"user_id": user.user_id, "date": {"$in": dates}}, {"_id": 0}
    ).to_list(20)
    by_date = {doc["date"]: doc for doc in docs}
    return {dt: by_date.get(dt) for dt in dates}


@api.get("/workouts/week")
async def get_workouts_week(start: str, user: User = Depends(get_current_user)):
    try:
        d = datetime.strptime(start, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="start must be YYYY-MM-DD")
    dates = [(d + timedelta(days=i)).isoformat() for i in range(7)]
    docs = await db.workouts.find(
        {"user_id": user.user_id, "date": {"$in": dates}}, {"_id": 0}
    ).to_list(20)
    by_date = {doc["date"]: doc for doc in docs}
    return {dt: by_date.get(dt) for dt in dates}


# ---------- Save custom meal / workout ----------
@api.post("/meals/save")
async def save_meal(payload: SaveMealRequest, user: User = Depends(get_current_user)):
    try:
        d = datetime.strptime(payload.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    lit = get_liturgical_day(d)
    plan = {
        "breakfast": payload.breakfast.model_dump(),
        "lunch": payload.lunch.model_dump(),
        "dinner": payload.dinner.model_dump(),
        "reflection": payload.reflection,
    }
    doc = {
        "user_id": user.user_id,
        "date": payload.date,
        "liturgical": lit,
        "plan": plan,
        "source": "user",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.meals.update_one(
        {"user_id": user.user_id, "date": payload.date},
        {"$set": doc},
        upsert=True,
    )
    return doc


@api.post("/workouts/save")
async def save_workout(payload: SaveWorkoutRequest, user: User = Depends(get_current_user)):
    try:
        d = datetime.strptime(payload.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    lit = get_liturgical_day(d)
    plan = {
        "title": payload.title,
        "focus": payload.focus,
        "duration_minutes": payload.duration_minutes,
        "exercises": [e.model_dump() for e in payload.exercises],
        "opening_prayer": payload.opening_prayer,
        "closing_prayer": payload.closing_prayer,
        "reflection": payload.reflection,
    }
    doc = {
        "user_id": user.user_id,
        "date": payload.date,
        "liturgical": lit,
        "plan": plan,
        "source": "user",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.workouts.update_one(
        {"user_id": user.user_id, "date": payload.date},
        {"$set": doc},
        upsert=True,
    )
    return doc


# ---------- AI suggestions for custom planning ----------
@api.post("/meals/suggest")
async def suggest_meal_slot(payload: SuggestMealSlotRequest, user: User = Depends(get_current_user)):
    if payload.slot not in ("breakfast", "lunch", "dinner"):
        raise HTTPException(status_code=400, detail="slot must be breakfast/lunch/dinner")
    try:
        d = datetime.strptime(payload.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    lit = get_liturgical_day(d)
    prefs = await db.preferences.find_one({"user_id": user.user_id}, {"_id": 0}) or PreferencesPayload().model_dump()
    system = (
        "You suggest a single Catholic-conscious meal honoring the liturgical day. "
        "Strict JSON only, no prose."
    )
    abstinence = "Abstinence from meat — no chicken/beef/pork; fish or vegetarian only." if lit["is_abstinence"] else ""
    fast = "Fast day — keep it light." if lit["is_fast"] else ""
    feast = f"Feast/Solemnity: {lit['feast']}. Make it festive." if lit.get("feast") and lit["rank"] in ("solemnity", "feast") else ""
    user_prompt = (
        f"Date: {lit['date']} | Season: {lit['season']} | Slot: {payload.slot}\n"
        f"{abstinence}\n{fast}\n{feast}\n"
        f"Preferences: dietary={prefs.get('dietary')}, allergies={prefs.get('allergies') or 'none'}.\n"
        f"User hint: {payload.hint or 'none'}\n"
        "Return JSON exactly:\n"
        "{\"name\": str, \"description\": str, \"ingredients\": [str], \"prep_minutes\": int}"
    )
    item = await _chat_json(system, user_prompt, session_id=f"suggest-meal-{user.user_id}-{payload.date}-{payload.slot}")
    return item


@api.post("/workouts/suggest")
async def suggest_workout(payload: SuggestExerciseRequest, user: User = Depends(get_current_user)):
    try:
        d = datetime.strptime(payload.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    lit = get_liturgical_day(d)
    prefs = await db.preferences.find_one({"user_id": user.user_id}, {"_id": 0}) or PreferencesPayload().model_dump()
    system = (
        "You suggest a Catholic-themed workout outline. Strict JSON only."
    )
    user_prompt = (
        f"Date: {lit['date']} | Day: {d.strftime('%A')} | Season: {lit['season']} | "
        f"Feast: {lit.get('feast') or 'none'} | Sunday: {lit['is_sunday']}\n"
        f"User: level={prefs.get('fitness_level')}, goal={prefs.get('fitness_goal')}, focus_hint={payload.focus or payload.hint or 'none'}.\n"
        "Return JSON exactly:\n"
        "{\n"
        "  \"title\": str, \"focus\": str, \"duration_minutes\": int,\n"
        "  \"exercises\": [{\"name\": str, \"sets\": str, \"notes\": str}],\n"
        "  \"opening_prayer\": str, \"closing_prayer\": str\n"
        "}"
    )
    item = await _chat_json(system, user_prompt, session_id=f"suggest-workout-{user.user_id}-{payload.date}")
    return item


# ---------- Grocery list ----------
@api.get("/meals/grocery")
async def grocery_week(start: str, user: User = Depends(get_current_user)):
    try:
        d = datetime.strptime(start, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="start must be YYYY-MM-DD")
    dates = [(d + timedelta(days=i)).isoformat() for i in range(7)]
    docs = await db.meals.find(
        {"user_id": user.user_id, "date": {"$in": dates}}, {"_id": 0}
    ).to_list(50)
    # Aggregate ingredients (case-insensitive dedup, keep count)
    counts: dict[str, int] = {}
    for doc in docs:
        plan = doc.get("plan", {})
        for slot in ("breakfast", "lunch", "dinner"):
            meal = plan.get(slot) or {}
            for ing in meal.get("ingredients", []) or []:
                key = ing.strip().lower()
                if not key:
                    continue
                counts[key] = counts.get(key, 0) + 1
    items = [
        {"name": k.title() if not any(c.isupper() for c in k) else k, "count": v}
        for k, v in sorted(counts.items())
    ]
    return {"start": start, "end": dates[-1], "items": items, "days_with_meals": len(docs)}


# ---------- Daily Mass Readings ----------
async def _ai_reflection(lit: dict, date_str: str) -> str:
    """Short AI-generated reflection — citations come from USCCB, not the model."""
    try:
        system = (
            "You are a Catholic spiritual companion. Write a short, prayerful reflection "
            "(2-3 sentences) inspired by the day's liturgical context — without paraphrasing "
            "scripture itself. Plain text, no markdown."
        )
        prompt = (
            f"Date: {date_str} | Season: {lit.get('season')} | "
            f"Feast: {lit.get('feast') or 'none'} | Sunday: {lit.get('is_sunday')}.\n"
            "Write 2-3 sentences tying today's liturgy to daily life."
        )
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"reflection-{date_str}",
            system_message=system,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        resp = await chat.send_message(UserMessage(text=prompt))
        return (resp if isinstance(resp, str) else str(resp)).strip()
    except Exception as e:  # noqa: BLE001
        logger.warning("reflection AI failed: %s", e)
        return ""


@api.get("/readings")
async def daily_readings(date: str, user: User = Depends(get_current_user)):
    try:
        d = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    cached = await db.readings.find_one({"date": date}, {"_id": 0})
    if cached and cached.get("source") == "usccb":
        return cached
    lit = get_liturgical_day(d)
    scraped = await fetch_readings(d)
    if scraped:
        # Generate short reflection alongside (best-effort).
        reflection = await _ai_reflection(lit, date)
        doc = {
            "date": date,
            "liturgical": lit,
            "source": scraped.get("source", "live"),
            "usccb_url": scraped["url"] or usccb_url_for(d),
            "liturgical_title": scraped["liturgical_title"] or (lit.get("feast") or lit.get("season") or ""),
            "first_reading": scraped["first_reading"],
            "first_reading_excerpt": scraped["first_reading_excerpt"],
            "psalm": scraped["psalm"],
            "psalm_excerpt": scraped["psalm_excerpt"],
            "second_reading": scraped["second_reading"],
            "second_reading_excerpt": scraped["second_reading_excerpt"],
            "gospel_acclamation": scraped["gospel_acclamation"],
            "gospel_acclamation_excerpt": scraped["gospel_acclamation_excerpt"],
            "gospel": scraped["gospel"],
            "gospel_excerpt": scraped["gospel_excerpt"],
            "reflection": reflection,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.readings.update_one({"date": date}, {"$set": doc}, upsert=True)
        return doc

    # Fallback — USCCB unreachable. Try AI for citations.
    logger.info("USCCB scrape failed for %s — falling back to AI citations.", date)
    system = (
        "You are a careful Catholic liturgical assistant. Provide the official Roman Catholic "
        "lectionary citations for a given date (Ordinary Form). Cite only chapter/verse references; "
        "do NOT paraphrase scripture. Use the U.S. lectionary cycle when applicable. "
        "If uncertain about a specific reading, omit it rather than guess. Return strict JSON only."
    )
    user_prompt = (
        f"Date: {lit['date']} ({d.strftime('%A')}) | Liturgical day: {lit.get('feast') or lit['season']}.\n"
        "Provide the Mass readings citations and a short reflection. Return JSON exactly:\n"
        "{\n"
        "  \"liturgical_title\": str,\n"
        "  \"first_reading\": str,\n"
        "  \"psalm\": str,\n"
        "  \"second_reading\": str,\n"
        "  \"gospel\": str,\n"
        "  \"gospel_acclamation\": str,\n"
        "  \"reflection\": str\n"
        "}"
    )
    try:
        data = await _chat_json(system, user_prompt, session_id=f"readings-{date}")
    except Exception as e:  # noqa: BLE001
        logger.warning("readings AI fallback failed: %s", e)
        data = {}
    doc = {
        "date": date,
        "liturgical": lit,
        "source": "ai-fallback",
        "usccb_url": usccb_url_for(d),
        "liturgical_title": data.get("liturgical_title", lit.get("feast") or lit.get("season") or ""),
        "first_reading": data.get("first_reading", ""),
        "first_reading_excerpt": "",
        "psalm": data.get("psalm", ""),
        "psalm_excerpt": "",
        "second_reading": data.get("second_reading", ""),
        "second_reading_excerpt": "",
        "gospel_acclamation": data.get("gospel_acclamation", ""),
        "gospel_acclamation_excerpt": "",
        "gospel": data.get("gospel", ""),
        "gospel_excerpt": "",
        "reflection": data.get("reflection", ""),
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.readings.update_one({"date": date}, {"$set": doc}, upsert=True)
    return doc


# ---------- Journal ----------
class JournalSaveRequest(BaseModel):
    date: str  # YYYY-MM-DD
    title: Optional[str] = ""
    body: str
    mood: Optional[str] = None  # e.g. grateful, sorrowful, joyful, contrite


def _journal_doc(d: dict) -> dict:
    return {
        "entry_id": d["entry_id"],
        "date": d["date"],
        "title": d.get("title", ""),
        "body": d.get("body", ""),
        "mood": d.get("mood"),
        "liturgical": d.get("liturgical"),
        "created_at": d.get("created_at"),
        "updated_at": d.get("updated_at"),
    }


@api.post("/journal")
async def save_journal(payload: JournalSaveRequest, user: User = Depends(get_current_user)):
    try:
        d = datetime.strptime(payload.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="body cannot be empty")
    lit = get_liturgical_day(d)
    now = datetime.now(timezone.utc).isoformat()
    entry_id = f"jrn_{uuid.uuid4().hex[:12]}"
    doc = {
        "entry_id": entry_id,
        "user_id": user.user_id,
        "date": payload.date,
        "title": (payload.title or "").strip(),
        "body": payload.body.strip(),
        "mood": payload.mood,
        "liturgical": lit,
        "created_at": now,
        "updated_at": now,
    }
    await db.journal.insert_one(doc)
    return _journal_doc(doc)


@api.put("/journal/{entry_id}")
async def update_journal(entry_id: str, payload: JournalSaveRequest, user: User = Depends(get_current_user)):
    existing = await db.journal.find_one({"entry_id": entry_id, "user_id": user.user_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="entry not found")
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="body cannot be empty")
    update = {
        "title": (payload.title or "").strip(),
        "body": payload.body.strip(),
        "mood": payload.mood,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.journal.update_one({"entry_id": entry_id, "user_id": user.user_id}, {"$set": update})
    return _journal_doc({**existing, **update})


@api.get("/journal")
async def list_journal(
    user: User = Depends(get_current_user),
    date: Optional[str] = None,
    limit: int = 50,
):
    """List entries for current user. If `date` given, only entries on that day."""
    query: dict = {"user_id": user.user_id}
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
        query["date"] = date
    cursor = db.journal.find(query, {"_id": 0}).sort("created_at", -1).limit(max(1, min(limit, 200)))
    docs = await cursor.to_list(length=limit)
    return {"items": [_journal_doc(d) for d in docs]}


@api.get("/journal/{entry_id}")
async def get_journal(entry_id: str, user: User = Depends(get_current_user)):
    doc = await db.journal.find_one({"entry_id": entry_id, "user_id": user.user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="entry not found")
    return _journal_doc(doc)


@api.delete("/journal/{entry_id}")
async def delete_journal(entry_id: str, user: User = Depends(get_current_user)):
    res = await db.journal.delete_one({"entry_id": entry_id, "user_id": user.user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="entry not found")
    return {"ok": True}


@api.get("/")
async def root():
    return {"app": "Sanctus", "status": "ok"}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await ensure_indexes()
    logger.info("Sanctus API ready")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()

"""Sanctus — Catholic-themed meal prep & workout scheduling backend."""
import os
import json
import uuid
import hashlib
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

from emergentintegrations.llm.chat import LlmChat, UserMessage

from liturgical import get_liturgical_day
from lang_ctx import current_lang, resolve_lang, lang_instruction, get_lang
from usccb import fetch_readings, usccb_url_for
from churches import nearby_churches, enrich_with_masstimes, search_churches
from prayers import EXAMEN_PROMPTS, EXAMINATION_SECTIONS
import bible as bible_svc
import community as community_svc
import self_defense as sd_svc

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
    # Faith bio (all optional — users may keep things private). These power
    # the small chips on the Profile screen and are exposed publicly via
    # /auth/me so the client can render them.
    denomination: Optional[str] = None        # catholic | protestant | orthodox
    tradition_path: Optional[str] = None      # convert | revert | cradle
    age: Optional[int] = None                 # 12..120, optional
    show_attribution: Optional[bool] = None   # default for overlay attributions
    is_admin: Optional[bool] = False          # gates /api/saints/admin/* etc.
    # Premium / Sanctus Premium subscription state. The `premium` subdoc
    # is written by `subscriptions.py` (Stripe webhook + reconcile flow).
    premium: Optional[Dict[str, Any]] = None
    stripe: Optional[Dict[str, Any]] = None


class PreferencesPayload(BaseModel):
    dietary: Optional[str] = "balanced"  # e.g., balanced, vegetarian, low-carb
    allergies: Optional[str] = ""
    fitness_level: Optional[str] = "intermediate"  # beginner / intermediate / advanced
    fitness_goal: Optional[str] = "general fitness"
    devotion_focus: Optional[str] = "daily prayer"


class GenerateMealRequest(BaseModel):
    date: str  # YYYY-MM-DD
    goal_mode: Optional[str] = "liturgical"  # liturgical | goals
    user_note: Optional[str] = None  # free-text suggestion to the AI


class GenerateWorkoutRequest(BaseModel):
    date: str
    goal_mode: Optional[str] = "liturgical"
    user_note: Optional[str] = None  # free-text suggestion to the AI


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
    goal_mode: Optional[str] = "liturgical"


class SuggestExerciseRequest(BaseModel):
    date: str
    focus: Optional[str] = None
    hint: Optional[str] = None
    goal_mode: Optional[str] = "liturgical"


class UpdateMeRequest(BaseModel):
    name: Optional[str] = None
    picture: Optional[str] = None  # base64 data URI or http(s) URL; empty string clears
    denomination: Optional[str] = None       # "catholic" | "protestant" | "orthodox" | "" to clear
    tradition_path: Optional[str] = None     # "convert" | "revert" | "cradle" | "" to clear
    age: Optional[int] = None                # 12..120, or 0/-1 to clear
    show_attribution: Optional[bool] = None  # default for overlay attributions


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
    await db.wellness.create_index("user_id", unique=True)
    await db.weight_log.create_index([("user_id", 1), ("date", -1)])
    await db.user_churches.create_index([("user_id", 1), ("church_id", 1)], unique=True)
    await db.user_churches.create_index([("user_id", 1), ("saved_at", -1)])
    await db.bible_books.create_index([("book_slug", 1), ("chapter", 1)])
    await db.bible_highlights.create_index(
        [("user_id", 1), ("book_slug", 1), ("chapter", 1), ("verse", 1)], unique=True,
    )
    await db.bible_highlights.create_index([("user_id", 1), ("updated_at", -1)])
    # Community indexes
    await db.community_posts.create_index("post_id", unique=True)
    await db.community_posts.create_index([("topic", 1), ("created_at", -1)])
    await db.community_posts.create_index([("created_at", -1)])
    await db.community_posts.create_index([("author_id", 1), ("created_at", -1)])
    await db.community_post_likes.create_index([("post_id", 1), ("user_id", 1)], unique=True)
    await db.community_post_likes.create_index("user_id")
    await db.community_replies.create_index("reply_id", unique=True)
    await db.community_replies.create_index([("post_id", 1), ("created_at", 1)])
    await db.community_dm_threads.create_index("thread_id", unique=True)
    await db.community_dm_threads.create_index("member_ids")
    await db.community_dm_threads.create_index([("member_ids", 1), ("last_message_at", -1)])
    await db.community_dm_messages.create_index("message_id", unique=True)
    await db.community_dm_messages.create_index([("thread_id", 1), ("created_at", 1)])
    await db.community_reports.create_index([("reporter_id", 1), ("created_at", -1)])
    await db.community_blocks.create_index([("user_id", 1), ("blocked_id", 1)], unique=True)
    # Friendships — one document per pair, keyed by `friendship_id` = sorted-user pair.
    await db.community_friendships.create_index("friendship_id", unique=True)
    await db.community_friendships.create_index([("members", 1), ("status", 1)])
    await db.community_friendships.create_index([("members", 1), ("created_at", -1)])
    # Self-defense indexes
    await db.self_defense_sessions.create_index("session_id", unique=True)
    await db.self_defense_sessions.create_index([("user_id", 1), ("discipline_id", 1), ("generated_at", -1)])
    await db.self_defense_sessions.create_index([("user_id", 1), ("generated_at", -1)])
    await db.self_defense_progress.create_index([("user_id", 1), ("discipline_id", 1)], unique=True)
    await db.self_defense_acks.create_index("user_id", unique=True)
    # Daily-practice indexes
    await db.daily_practices.create_index([("user_id", 1), ("date", 1)], unique=True)
    await db.daily_practices.create_index([("user_id", 1), ("date", -1)])
    # Catechism indexes
    await db.catechism_assignments.create_index(
        [("user_id", 1), ("date", 1)], unique=True
    )
    await db.catechism_assignments.create_index([("user_id", 1), ("date", -1)])
    # Parish events indexes
    await db.parish_events.create_index("id", unique=True)
    await db.parish_events.create_index([("loc", "2dsphere")])
    await db.parish_events.create_index([("church_id", 1), ("start_at", 1)])
    await db.parish_events.create_index([("start_at", 1)])
    await db.parish_events.create_index([("organizer_user_id", 1), ("created_at", -1)])
    await db.parish_events.create_index([("removed", 1), ("start_at", 1)])
    # Community-added churches indexes
    await db.community_churches.create_index("church_id", unique=True)
    await db.community_churches.create_index([("loc", "2dsphere")])
    await db.community_churches.create_index([("submitted_by", 1), ("created_at", -1)])
    await db.community_churches.create_index([("removed", 1)])
    # Church overlays — community edits applied on top of any church (OSM or
    # community-submitted). Indexed by church_id so we can batch-merge cheaply.
    await db.church_overlays.create_index("church_id", unique=True)
    await db.church_overlays.create_index([("updated_at", -1)])
    # Saints / Blessed / Venerable of the Day
    await db.saints.create_index("saint_id", unique=True)
    await db.saints.create_index("feast_date")
    await db.saints.create_index("status")
    await db.saints.create_index([("status", 1), ("feast_date", 1)])
    await db.saints.create_index([("status", 1), ("last_shown_at", 1)])
    # Shop (Sanctus shop — products + orders)
    from shop import ensure_indexes as _shop_indexes
    await _shop_indexes(db)
    # Charity hub
    from charity import ensure_indexes as _charity_indexes
    await _charity_indexes(db)
    # Liturgical challenges (Hallowtide / Advent / Lent)
    from challenges import ensure_indexes as _challenges_indexes
    await _challenges_indexes(db)
    # Sanctus Library (books, radio, films)
    from library import ensure_indexes as _library_indexes
    await _library_indexes(db)
    # Support tickets created via /api/legal/support/contact
    await db.support_tickets.create_index("ticket_id", unique=True)
    await db.support_tickets.create_index([("status", 1), ("created_at", -1)])


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
    # Augment with a computed `is_premium` flag for clients (paywall UI).
    from premium import is_premium_user
    payload = user.model_dump()
    payload["is_premium"] = is_premium_user(user)
    return payload


@api.put("/auth/me")
async def update_me(payload: UpdateMeRequest, user: User = Depends(get_current_user)):
    update: dict = {}
    if payload.name is not None:
        name = payload.name.strip()
        if not (1 <= len(name) <= 60):
            raise HTTPException(status_code=400, detail="name must be 1-60 chars")
        update["name"] = name
    if payload.picture is not None:
        pic = payload.picture.strip()
        # Accept empty string (clear), http(s) URL, or data URI under ~2MB.
        if pic and not (pic.startswith("http://") or pic.startswith("https://") or pic.startswith("data:image/")):
            raise HTTPException(status_code=400, detail="picture must be a URL or data URI")
        if pic.startswith("data:image/") and len(pic) > 2_800_000:
            raise HTTPException(status_code=413, detail="picture too large (max ~2MB)")
        update["picture"] = pic or None
    if payload.denomination is not None:
        d = payload.denomination.strip().lower()
        if d and d not in {"catholic", "protestant", "orthodox"}:
            raise HTTPException(status_code=400, detail="denomination must be catholic, protestant, or orthodox")
        update["denomination"] = d or None
    if payload.tradition_path is not None:
        t = payload.tradition_path.strip().lower()
        if t and t not in {"convert", "revert", "cradle"}:
            raise HTTPException(status_code=400, detail="tradition_path must be convert, revert, or cradle")
        update["tradition_path"] = t or None
    if payload.age is not None:
        # 0 (or negative) clears; otherwise must be a sensible adult-or-teen range.
        if payload.age <= 0:
            update["age"] = None
        elif not (12 <= payload.age <= 120):
            raise HTTPException(status_code=400, detail="age must be between 12 and 120")
        else:
            update["age"] = int(payload.age)
    if payload.show_attribution is not None:
        update["show_attribution"] = bool(payload.show_attribution)
    if not update:
        return user
    await db.users.update_one({"user_id": user.user_id}, {"$set": update})
    fresh = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    return User(**fresh)


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
    use_goals = (payload.goal_mode or "liturgical").lower() == "goals"
    wellness_brief = ""
    if use_goals:
        wprofile = await db.wellness.find_one({"user_id": user.user_id}, {"_id": 0})
        wellness_brief = _wellness_brief(wprofile or {})

    system = (
        "You are a thoughtful Catholic nutrition coach. You craft a single day's meal plan that "
        "honors the Church's liturgical calendar — observing abstinence (no meat) on Fridays and during Lent, "
        "joyful, festive meals on solemnities and feast days, and simple, contemplative meals on penitential days. "
        "Always return strictly valid JSON. No prose outside JSON."
    )
    if use_goals:
        system += (
            " The user has shared personal wellness goals: tune portion sizes, macros and ingredient choices "
            "toward their goal (lose / maintain / gain) and activity level. Still honor abstinence and fasts — "
            "those are non-negotiable. Mention the goal subtly in the reflection."
        )
    abstinence_note = "Today is a day of ABSTINENCE from meat — propose only fish, vegetarian, or seafood meals." if lit["is_abstinence"] else ""
    fast_note = "Today is a day of FAST — propose lighter, smaller meals." if lit["is_fast"] else ""
    feast_note = f"Today is the {lit['feast']} ({lit['rank']}) — propose a festive meal in joyful tradition." if lit.get("feast") and lit["rank"] in ("solemnity", "feast") else ""
    goals_note = f"PERSONAL GOALS: {wellness_brief}." if (use_goals and wellness_brief) else ""
    note_clean = (payload.user_note or "").strip()[:600]
    note_block = (
        "\nADDITIONAL USER REQUEST (treat as a strong preference, not an override of "
        "abstinence/fast rules): \"" + note_clean + "\""
    ) if note_clean else ""

    user_prompt = (
        f"Date: {lit['date']} | Season: {lit['season']} | Liturgical color: {lit['color']}.\n"
        f"{abstinence_note}\n{fast_note}\n{feast_note}\n{goals_note}\n"
        f"User preferences: dietary={prefs.get('dietary')}, allergies={prefs.get('allergies') or 'none'}."
        f"{note_block}\n"
        "Return JSON shaped exactly like:\n"
        "{\n"
        "  \"breakfast\": {\"name\": str, \"description\": str, \"ingredients\": [str], \"prep_minutes\": int},\n"
        "  \"lunch\": {\"name\": str, \"description\": str, \"ingredients\": [str], \"prep_minutes\": int},\n"
        "  \"dinner\": {\"name\": str, \"description\": str, \"ingredients\": [str], \"prep_minutes\": int},\n"
        "  \"reflection\": str  // 1-2 sentence Catholic reflection tying the meal to the day\n"
        "}"
    )
    note_hash = hashlib.sha1(note_clean.encode("utf-8")).hexdigest()[:8] if note_clean else "none"
    plan = await _chat_json(system + lang_instruction(), user_prompt, session_id=f"meals-{user.user_id}-{payload.date}-{payload.goal_mode}-{note_hash}")

    doc = {
        "user_id": user.user_id,
        "date": payload.date,
        "liturgical": lit,
        "plan": plan,
        "goal_mode": payload.goal_mode or "liturgical",
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
    use_goals = (payload.goal_mode or "liturgical").lower() == "goals"
    wellness_brief = ""
    if use_goals:
        wprofile = await db.wellness.find_one({"user_id": user.user_id}, {"_id": 0})
        wellness_brief = _wellness_brief(wprofile or {})

    system = (
        "You are a Catholic fitness coach who pairs physical training with the liturgical season. "
        "Lent calls for penitential, disciplined workouts; Easter and feast days for joyful, energetic ones; "
        "Advent for steady preparation; Ordinary Time for balanced strength. "
        "Sundays are days of rest — propose only gentle movement (a walk, stretching) and a longer prayer focus. "
        "Always return strictly valid JSON. No prose outside JSON."
    )
    if use_goals:
        system += (
            " The user has shared personal training goals: tune intensity, volume and duration toward their "
            "goal_type and activity_level. Sundays still get a gentle session. Tie the encouragement to the goal."
        )
    goals_note = f"PERSONAL GOALS: {wellness_brief}." if (use_goals and wellness_brief) else ""
    note_clean = (payload.user_note or "").strip()[:600]
    note_block = (
        "\nADDITIONAL USER REQUEST (treat as a strong preference — but Sunday rest, "
        "fitness safety, and abstinence rules still hold): \"" + note_clean + "\""
    ) if note_clean else ""
    user_prompt = (
        f"Date: {lit['date']} | Day of week: {d.strftime('%A')} | Season: {lit['season']} | "
        f"Feast: {lit.get('feast') or 'none'}.\n"
        f"{goals_note}\n"
        f"User: fitness_level={prefs.get('fitness_level')}, goal={prefs.get('fitness_goal')}."
        f"{note_block}\n"
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
    note_hash = hashlib.sha1(note_clean.encode("utf-8")).hexdigest()[:8] if note_clean else "none"
    plan = await _chat_json(system + lang_instruction(), user_prompt, session_id=f"workout-{user.user_id}-{payload.date}-{payload.goal_mode}-{note_hash}")
    doc = {
        "user_id": user.user_id,
        "date": payload.date,
        "liturgical": lit,
        "plan": plan,
        "goal_mode": "goals" if use_goals else "liturgical",
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


async def _translate_readings_es(base: dict, date: str) -> dict:
    """Produce a Spanish rendering of an English readings doc. Scripture citations
    (e.g. 'Mt 5:1-12') are preserved; titles, excerpts and the reflection are
    faithfully translated to Latin American Spanish."""
    fields = [
        "liturgical_title", "first_reading_excerpt", "psalm_excerpt",
        "second_reading_excerpt", "gospel_acclamation_excerpt",
        "gospel_excerpt", "reflection",
    ]
    es = dict(base)
    es.pop("_id", None)
    es["date"] = date
    es["lang"] = "es"
    es["cached_at"] = datetime.now(timezone.utc).isoformat()
    payload = {k: base.get(k, "") for k in fields if (base.get(k) or "").strip()}
    if payload:
        system = (
            "You are a faithful Catholic translator. Translate the given liturgical "
            "texts from English into reverent, accurate Latin American Spanish. "
            "Return STRICT JSON with the SAME keys, each value translated. Do not add, "
            "remove or rename keys. Preserve the sense of Scripture faithfully; no markdown."
        )
        try:
            data = await _chat_json(system, json.dumps(payload, ensure_ascii=False), session_id=f"readings-es-{date}")
            for k, v in (data or {}).items():
                if k in fields and isinstance(v, str) and v.strip():
                    es[k] = v.strip()
        except Exception as e:  # noqa: BLE001
            logger.warning("readings es translation failed: %s", e)
    return es


@api.get("/readings")
async def daily_readings(date: str, user: User = Depends(get_current_user)):
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    if get_lang() != "es":
        return await _readings_en(date)
    cached_es = await db.readings_es.find_one({"date": date}, {"_id": 0})
    if cached_es:
        return cached_es
    base = await _readings_en(date)
    es = await _translate_readings_es(base, date)
    await db.readings_es.update_one({"date": date}, {"$set": es}, upsert=True)
    return es


async def _readings_en(date: str) -> dict:
    d = datetime.strptime(date, "%Y-%m-%d").date()
    cached = await db.readings.find_one({"date": date}, {"_id": 0})
    if cached and cached.get("source") in {"usccb", "universalis", "ai-fallback"}:
        # Universalis serves today's date — invalidate cache rollover if the cached
        # doc was created on a different calendar day than the requested date and
        # we're now requesting that requested date again.
        if cached.get("source") == "universalis":
            try:
                cached_at = datetime.fromisoformat(str(cached.get("cached_at", "")).replace("Z", "+00:00"))
                if cached_at.date().isoformat() != date:
                    cached = None
            except Exception:  # noqa: BLE001
                pass
        if cached:
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
    mood: Optional[str] = None  # grateful / sorrowful / joyful / contrite / hopeful / weary
    kind: Optional[str] = "free"  # free | examen | examination
    structured: Optional[dict] = None  # mode-specific structured data


def _journal_doc(d: dict) -> dict:
    return {
        "entry_id": d["entry_id"],
        "date": d["date"],
        "title": d.get("title", ""),
        "body": d.get("body", ""),
        "mood": d.get("mood"),
        "kind": d.get("kind", "free"),
        "structured": d.get("structured"),
        "liturgical": d.get("liturgical"),
        "confessed_at": d.get("confessed_at"),
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
    kind = payload.kind if payload.kind in {"free", "examen", "examination", "catechism"} else "free"
    doc = {
        "entry_id": entry_id,
        "user_id": user.user_id,
        "date": payload.date,
        "title": (payload.title or "").strip(),
        "body": payload.body.strip(),
        "mood": payload.mood,
        "kind": kind,
        "structured": payload.structured,
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
    kind = payload.kind if payload.kind in {"free", "examen", "examination", "catechism"} else existing.get("kind", "free")
    update = {
        "title": (payload.title or "").strip(),
        "body": payload.body.strip(),
        "mood": payload.mood,
        "kind": kind,
        "structured": payload.structured,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.journal.update_one({"entry_id": entry_id, "user_id": user.user_id}, {"$set": update})
    return _journal_doc({**existing, **update})


@api.get("/journal")
async def list_journal(
    user: User = Depends(get_current_user),
    date: Optional[str] = None,
    kind: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """List entries for current user. If `date` given, only entries on that day.
    Optionally filter by `kind` (e.g. ``catechism`` for the CCC Reflection folder)."""
    query: dict = {"user_id": user.user_id}
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
        query["date"] = date
    if kind:
        if kind not in {"free", "examen", "examination", "catechism"}:
            raise HTTPException(status_code=400, detail="invalid kind")
        query["kind"] = kind
    cursor = db.journal.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
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


@api.post("/journal/{entry_id}/confess")
async def mark_confessed(entry_id: str, user: User = Depends(get_current_user)):
    """Mark an Examination-of-Conscience entry as confessed today.

    Persists the date of confession on the journal entry. The frontend uses
    this to visually 'archive' examination entries after the sacrament.
    """
    existing = await db.journal.find_one({"entry_id": entry_id, "user_id": user.user_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="entry not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.journal.update_one(
        {"entry_id": entry_id, "user_id": user.user_id},
        {"$set": {"confessed_at": now, "updated_at": now}},
    )
    return _journal_doc({**existing, "confessed_at": now, "updated_at": now})


# ---------- Prayer templates ----------
@api.get("/prayers/examen")
async def get_examen_template(_: User = Depends(get_current_user)):
    return {"prompts": EXAMEN_PROMPTS}


@api.get("/prayers/examination")
async def get_examination_template(_: User = Depends(get_current_user)):
    return {"sections": EXAMINATION_SECTIONS}


# ---------- Wellness (weight + goals) ----------
class WellnessProfilePayload(BaseModel):
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    target_weight_kg: Optional[float] = None
    target_date: Optional[str] = None  # YYYY-MM-DD
    goal_type: Optional[str] = None  # lose | maintain | gain
    activity_level: Optional[str] = None  # sedentary | light | moderate | very_active
    weekly_rate_kg: Optional[float] = None  # desired weekly change (e.g. 0.5)
    units: Optional[str] = "metric"  # metric | imperial
    notes: Optional[str] = None


class WeightLogPayload(BaseModel):
    date: str
    weight_kg: float
    note: Optional[str] = None


def _wellness_doc(d: dict) -> dict:
    return {
        "weight_kg": d.get("weight_kg"),
        "height_cm": d.get("height_cm"),
        "target_weight_kg": d.get("target_weight_kg"),
        "target_date": d.get("target_date"),
        "goal_type": d.get("goal_type"),
        "activity_level": d.get("activity_level"),
        "weekly_rate_kg": d.get("weekly_rate_kg"),
        "units": d.get("units", "metric"),
        "notes": d.get("notes"),
        "updated_at": d.get("updated_at"),
    }


@api.get("/wellness/profile")
async def get_wellness_profile(user: User = Depends(get_current_user)):
    doc = await db.wellness.find_one({"user_id": user.user_id}, {"_id": 0})
    if not doc:
        return _wellness_doc({})
    return _wellness_doc(doc)


@api.put("/wellness/profile")
async def update_wellness_profile(
    payload: WellnessProfilePayload, user: User = Depends(get_current_user)
):
    if payload.target_date:
        try:
            datetime.strptime(payload.target_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="target_date must be YYYY-MM-DD")
    if payload.goal_type and payload.goal_type not in {"lose", "maintain", "gain"}:
        raise HTTPException(status_code=400, detail="goal_type must be lose, maintain, or gain")
    if payload.activity_level and payload.activity_level not in {
        "sedentary", "light", "moderate", "very_active"
    }:
        raise HTTPException(status_code=400, detail="invalid activity_level")
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.wellness.update_one(
        {"user_id": user.user_id}, {"$set": update, "$setOnInsert": {"user_id": user.user_id}}, upsert=True
    )
    doc = await db.wellness.find_one({"user_id": user.user_id}, {"_id": 0})
    return _wellness_doc(doc or {})


@api.post("/wellness/log")
async def log_weight(payload: WeightLogPayload, user: User = Depends(get_current_user)):
    try:
        datetime.strptime(payload.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    if payload.weight_kg <= 0 or payload.weight_kg > 700:
        raise HTTPException(status_code=400, detail="weight_kg out of range")
    log_id = f"wl_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    # Fields that may be overwritten on a same-day re-weigh.
    set_doc = {
        "log_id": log_id,
        "user_id": user.user_id,
        "date": payload.date,
        "weight_kg": payload.weight_kg,
        "note": payload.note,
    }
    # Upsert so two logs on same date overwrite (typical weigh-in habit).
    await db.weight_log.update_one(
        {"user_id": user.user_id, "date": payload.date},
        {"$set": set_doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    # Mirror latest weight into the wellness profile.
    await db.wellness.update_one(
        {"user_id": user.user_id},
        {"$set": {"weight_kg": payload.weight_kg, "updated_at": now}, "$setOnInsert": {"user_id": user.user_id}},
        upsert=True,
    )
    return {"log_id": log_id, "date": payload.date, "weight_kg": payload.weight_kg}


@api.get("/wellness/log")
async def list_weight_log(
    user: User = Depends(get_current_user),
    limit: int = Query(120, ge=1, le=730),
):
    cursor = db.weight_log.find({"user_id": user.user_id}, {"_id": 0}).sort("date", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {"items": docs}


@api.delete("/wellness/log/{log_id}")
async def delete_weight_log(log_id: str, user: User = Depends(get_current_user)):
    res = await db.weight_log.delete_one({"log_id": log_id, "user_id": user.user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="log not found")
    return {"ok": True}


def _wellness_brief(profile: dict) -> str:
    """Compact natural-language string for AI prompts."""
    if not profile:
        return ""
    bits = []
    if profile.get("weight_kg"):
        bits.append(f"current weight {profile['weight_kg']:.1f} kg")
    if profile.get("height_cm"):
        bits.append(f"height {profile['height_cm']:.0f} cm")
    if profile.get("target_weight_kg"):
        bits.append(f"target {profile['target_weight_kg']:.1f} kg")
    if profile.get("goal_type"):
        bits.append(f"goal {profile['goal_type']}")
    if profile.get("activity_level"):
        bits.append(f"activity {profile['activity_level']}")
    if profile.get("weekly_rate_kg"):
        bits.append(f"~{profile['weekly_rate_kg']:.2f} kg/week")
    if profile.get("target_date"):
        bits.append(f"by {profile['target_date']}")
    return "; ".join(bits)


@api.post("/wellness/suggest")
async def wellness_ai_brief(user: User = Depends(get_current_user)):
    """AI-generated coaching brief: meal + workout focus tailored to the user's goal."""
    profile = await db.wellness.find_one({"user_id": user.user_id}, {"_id": 0})
    if not profile or not profile.get("goal_type"):
        raise HTTPException(status_code=400, detail="set a goal first")
    brief = _wellness_brief(profile)
    system = (
        "You are a Catholic wellness coach. Respond with prudence, encouragement, and the conviction that the "
        "body is a temple of the Holy Spirit (1 Cor 6:19). Output STRICT JSON only with these keys: "
        '{"calorie_target": int, "macro_focus": str, "meal_focus": [str, str, str], '
        '"workout_focus": [str, str, str], "weekly_split": str, "encouragement": str}. '
        "calorie_target is a rough daily kcal estimate for the user's stats (use Mifflin-St Jeor + activity multiplier + deficit/surplus). "
        "All strings concise (<= 16 words). Encouragement is a single sentence and may quote a Catholic source."
    )
    prompt = f"User stats: {brief}. Suggest meal and workout focus for next 4 weeks."
    try:
        data = await _chat_json(system, prompt, session_id=f"wellness-{user.user_id}")
    except Exception as e:  # noqa: BLE001
        logger.warning("wellness AI failed: %s", e)
        raise HTTPException(status_code=502, detail="ai unavailable") from e
    return {
        "calorie_target": int(data.get("calorie_target") or 0),
        "macro_focus": str(data.get("macro_focus") or ""),
        "meal_focus": data.get("meal_focus") or [],
        "workout_focus": data.get("workout_focus") or [],
        "weekly_split": str(data.get("weekly_split") or ""),
        "encouragement": str(data.get("encouragement") or ""),
        "based_on": brief,
    }


# ---------- Nearby Catholic churches ----------
class SaveChurchPayload(BaseModel):
    church_id: str
    name: str
    lat: float
    lng: float
    address: Optional[str] = ""
    website: Optional[str] = ""
    phone: Optional[str] = ""
    mass_times: Optional[List[str]] = None
    confession_times: Optional[List[str]] = None
    notes: Optional[str] = ""


@api.get("/churches/nearby")
async def churches_nearby(
    user: User = Depends(get_current_user),
    lat: float = Query(...),
    lng: float = Query(...),
    radius_m: int = Query(8000, ge=500, le=50_000),
    enrich: bool = Query(True),
):
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise HTTPException(status_code=400, detail="invalid lat/lng")
    churches = await nearby_churches(lat, lng, radius_m=radius_m)
    if enrich and churches:
        churches = await enrich_with_masstimes(churches)
    # Merge in community-added churches within the same radius.
    community = await _community_churches_nearby(lat, lng, radius_m)
    churches = _merge_churches(churches, community)
    # Overlay user-contributed details (mass/confession/website/phone/notes)
    # on top of whatever the OSM/community sources provided.
    churches = await _apply_overlays(churches)
    # Annotate which churches the user has starred.
    starred_ids = {
        d["church_id"]
        async for d in db.user_churches.find({"user_id": user.user_id}, {"church_id": 1, "_id": 0})
    }
    for c in churches:
        c["is_starred"] = c["church_id"] in starred_ids
    return {"items": churches, "count": len(churches)}


@api.get("/churches/search")
async def churches_search(
    user: User = Depends(get_current_user),
    q: str = Query(..., min_length=1, max_length=120),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    radius_m: int = Query(60_000, ge=1_000, le=80_000),
    enrich: bool = Query(False),
):
    if lat is not None and not (-90 <= lat <= 90):
        raise HTTPException(status_code=400, detail="invalid lat")
    if lng is not None and not (-180 <= lng <= 180):
        raise HTTPException(status_code=400, detail="invalid lng")
    churches = await search_churches(q, lat=lat, lng=lng, radius_m=radius_m)
    if enrich and churches:
        churches = await enrich_with_masstimes(churches)
    # Include community churches whose name matches the query (and are within
    # the search radius if a center was provided).
    community = await _community_churches_search(q, lat=lat, lng=lng, radius_m=radius_m)
    churches = _merge_churches(churches, community)
    # Overlay user-contributed details on top.
    churches = await _apply_overlays(churches)
    starred_ids = {
        d["church_id"]
        async for d in db.user_churches.find({"user_id": user.user_id}, {"church_id": 1, "_id": 0})
    }
    for c in churches:
        c["is_starred"] = c["church_id"] in starred_ids
        c.setdefault("mass_times", [])
        c.setdefault("confession_times", [])
    return {"items": churches, "count": len(churches), "query": q}


# ---------------------------------------------------------------------------
# Community-added churches (user submissions)
# ---------------------------------------------------------------------------
# Catholic places of worship that didn't surface from OSM. Submitted by
# end-users to grow the database organically. Anyone with the same area
# will see them, tagged with `source: "community"` so the UI can render a
# subtle "Added by a Sanctus user" footnote.

class CommunityChurchSubmission(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    lat: float
    lng: float
    address: Optional[str] = Field(None, max_length=240)
    website: Optional[str] = Field(None, max_length=300)
    phone: Optional[str] = Field(None, max_length=60)
    notes: Optional[str] = Field(None, max_length=600)
    # Free-form schedule strings (e.g. "Sun 9:00 AM", "Wed 6:30 PM"). We keep
    # them as small list of short labels rather than a structured rrule because
    # parish schedules vary wildly and are usually published as plain text.
    mass_times: Optional[List[str]] = Field(default=None, max_length=24)
    confession_times: Optional[List[str]] = Field(default=None, max_length=24)


def _clean_time_list(items: Optional[List[str]]) -> List[str]:
    if not items:
        return []
    cleaned: List[str] = []
    seen: set = set()
    for raw in items:
        if not isinstance(raw, str):
            continue
        s = raw.strip()
        if not s or len(s) > 80:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(s)
        if len(cleaned) >= 24:
            break
    return cleaned


def _community_to_shape(doc: dict, origin: Optional[Tuple[float, float]] = None) -> dict:
    out = {
        "church_id": doc["church_id"],
        "name": doc.get("name", ""),
        "lat": doc.get("lat"),
        "lng": doc.get("lng"),
        "address": doc.get("address", "") or "",
        "denomination": "roman_catholic",
        "website": doc.get("website", "") or "",
        "phone": doc.get("phone", "") or "",
        "mass_times_raw": "",
        "opening_hours": "",
        "mass_times": list(doc.get("mass_times") or []),
        "confession_times": list(doc.get("confession_times") or []),
        "notes": doc.get("notes", "") or "",
        "source": "community",
        "submitted_by_name": doc.get("submitted_by_name") or "a Sanctus user",
    }
    if origin and out.get("lat") is not None and out.get("lng") is not None:
        out["distance_km"] = round(
            _great_circle_km(origin[0], origin[1], float(out["lat"]), float(out["lng"])), 2
        )
    return out


def _great_circle_km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    import math
    R = 6371.0
    p1 = math.radians(a_lat)
    p2 = math.radians(b_lat)
    dp = math.radians(b_lat - a_lat)
    dl = math.radians(b_lng - a_lng)
    s = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(s))


async def _community_churches_nearby(lat: float, lng: float, radius_m: int) -> List[dict]:
    radius_rad = radius_m / 6378137.0
    cursor = db.community_churches.find(
        {
            "removed": {"$ne": True},
            "loc": {"$geoWithin": {"$centerSphere": [[lng, lat], radius_rad]}},
        },
        {"_id": 0},
    ).limit(40)
    docs = await cursor.to_list(length=40)
    return [_community_to_shape(d, origin=(lat, lng)) for d in docs]


async def _community_churches_search(
    q: str, lat: Optional[float], lng: Optional[float], radius_m: int
) -> List[dict]:
    import re
    pattern = re.escape(q.strip())
    if not pattern:
        return []
    filt: Dict[str, Any] = {
        "removed": {"$ne": True},
        "name": {"$regex": pattern, "$options": "i"},
    }
    if lat is not None and lng is not None:
        radius_rad = radius_m / 6378137.0
        filt["loc"] = {"$geoWithin": {"$centerSphere": [[lng, lat], radius_rad]}}
    cursor = db.community_churches.find(filt, {"_id": 0}).limit(20)
    docs = await cursor.to_list(length=20)
    origin = (lat, lng) if (lat is not None and lng is not None) else None
    return [_community_to_shape(d, origin=origin) for d in docs]


def _merge_churches(osm: List[dict], community: List[dict]) -> List[dict]:
    """De-duplicate by (rounded coords + lowercased name), prefer OSM rows."""
    seen: set = set()

    def key(c: dict) -> tuple:
        lat = c.get("lat")
        lng = c.get("lng")
        return (
            (c.get("name") or "").strip().lower(),
            round(float(lat), 3) if lat is not None else None,
            round(float(lng), 3) if lng is not None else None,
        )

    out: List[dict] = []
    for c in osm:
        k = key(c)
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
    for c in community:
        k = key(c)
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
    # Sort by distance_km if present, otherwise leave order.
    out.sort(key=lambda x: x.get("distance_km") if x.get("distance_km") is not None else 1e9)
    return out


@api.post("/churches/manual")
async def submit_community_church(
    payload: CommunityChurchSubmission, user: User = Depends(get_current_user)
):
    """Submit a Catholic church that didn't show up in nearby or search.

    Shared with the community so other nearby users can find the same parish.
    De-duplicates against existing OSM AND community entries by name + coords.
    """
    if not (-90 <= payload.lat <= 90 and -180 <= payload.lng <= 180):
        raise HTTPException(status_code=400, detail="invalid lat/lng")

    name = payload.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="name too short")

    # Dedupe: refuse if a community church with same lowercased-name within ~150m exists.
    radius_rad = 150 / 6378137.0
    existing = await db.community_churches.find_one({
        "removed": {"$ne": True},
        "name_lc": name.lower(),
        "loc": {"$geoWithin": {"$centerSphere": [[payload.lng, payload.lat], radius_rad]}},
    })
    if existing:
        # Same-name + within-150m hit. Don't create a duplicate doc, but if
        # the resubmission carries fresh mass/confession times *not already*
        # in the existing record, merge them in. This makes the manual-entry
        # flow function as a community wiki — successive users can flesh out
        # the schedule for the same parish without us creating multiple rows.
        incoming_mass = _clean_time_list(payload.mass_times)
        incoming_conf = _clean_time_list(payload.confession_times)
        merged_mass = list(existing.get("mass_times") or [])
        merged_conf = list(existing.get("confession_times") or [])
        lower_mass = {x.lower() for x in merged_mass}
        lower_conf = {x.lower() for x in merged_conf}
        added = False
        for t in incoming_mass:
            if t.lower() not in lower_mass and len(merged_mass) < 24:
                merged_mass.append(t)
                lower_mass.add(t.lower())
                added = True
        for t in incoming_conf:
            if t.lower() not in lower_conf and len(merged_conf) < 24:
                merged_conf.append(t)
                lower_conf.add(t.lower())
                added = True
        if added:
            await db.community_churches.update_one(
                {"church_id": existing["church_id"]},
                {"$set": {
                    "mass_times": merged_mass,
                    "confession_times": merged_conf,
                    "updated_at": datetime.now(timezone.utc),
                }},
            )
            existing["mass_times"] = merged_mass
            existing["confession_times"] = merged_conf
        return _community_to_shape(existing, origin=(payload.lat, payload.lng))

    # Rate-limit: max 5 submissions per user per 24h.
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    recent_n = await db.community_churches.count_documents({
        "submitted_by": user.user_id,
        "created_at": {"$gte": one_day_ago},
    })
    if recent_n >= 5:
        raise HTTPException(
            status_code=429,
            detail="Daily submission limit reached. Try again tomorrow.",
        )

    church_id = f"community:{uuid.uuid4().hex[:14]}"
    now = datetime.now(timezone.utc)
    doc = {
        "church_id": church_id,
        "name": name,
        "name_lc": name.lower(),
        "lat": float(payload.lat),
        "lng": float(payload.lng),
        "loc": {"type": "Point", "coordinates": [float(payload.lng), float(payload.lat)]},
        "address": (payload.address or "").strip() or None,
        "website": (payload.website or "").strip() or None,
        "phone": (payload.phone or "").strip() or None,
        "notes": (payload.notes or "").strip() or None,
        "mass_times": _clean_time_list(payload.mass_times),
        "confession_times": _clean_time_list(payload.confession_times),
        "submitted_by": user.user_id,
        "submitted_by_name": getattr(user, "name", None) or "Anonymous",
        "created_at": now,
        "updated_at": now,
        "flag_count": 0,
        "flagged_by": [],
        "removed": False,
    }
    await db.community_churches.insert_one(doc)
    return _community_to_shape(doc, origin=(payload.lat, payload.lng))


# ---------------------------------------------------------------------------
# Church overlays
# ---------------------------------------------------------------------------
# Anyone signed-in can add the Mass / Confession schedule, website, or phone
# number to *any* church — including OSM-sourced ones whose data is sparse.
# Edits land in a single `church_overlays` doc keyed by church_id. We merge
# overlays into both `/churches/nearby` and `/churches/search` so they show
# up immediately for everyone in the area.
#
# Design choices:
#   • Mass / confession times are *unioned* with whatever the underlying
#     source already has (deduped case-insensitively). This makes the field
#     act as a community wiki — successive editors keep adding.
#   • Scalars (website, phone, notes) are *replaced* — last-write-wins. We
#     store a small `editors` audit list (last 20) so we can attribute
#     changes if abuse becomes a problem.
#   • No delete endpoint yet — if it becomes a problem, we'll add a flag
#     mechanism (same as parish events).

class ChurchOverlayPayload(BaseModel):
    mass_times: Optional[List[str]] = Field(default=None, max_length=24)
    confession_times: Optional[List[str]] = Field(default=None, max_length=24)
    website: Optional[str] = Field(default=None, max_length=300)
    phone: Optional[str] = Field(default=None, max_length=60)
    notes: Optional[str] = Field(default=None, max_length=600)
    # Mass/confession behaviour: by default new entries are *added* to the
    # existing list; set replace=True to wipe the existing list and use the
    # incoming one instead (e.g. when the user is fixing a typo).
    replace_mass: bool = False
    replace_confession: bool = False
    # Whether the editor wants their display name credited publicly on this
    # church card. Defaults to False (anonymous community wiki).
    show_name: bool = False


def _merge_time_lists(existing: List[str], incoming: List[str], replace: bool) -> List[str]:
    """Return existing ∪ incoming (case-insensitive dedupe, capped at 24).
    If ``replace`` is True, ignore the existing list and use the incoming one."""
    base = [] if replace else list(existing or [])
    seen = {x.lower() for x in base}
    for it in _clean_time_list(incoming):
        if it.lower() in seen:
            continue
        base.append(it)
        seen.add(it.lower())
        if len(base) >= 24:
            break
    return base


def _scalar_or_existing(incoming: Optional[str], existing: Optional[str]) -> Optional[str]:
    if incoming is None:
        return existing
    s = incoming.strip()
    return s or None  # empty string clears the field


@api.put("/churches/{church_id:path}/overlay")
async def upsert_church_overlay(
    church_id: str,
    payload: ChurchOverlayPayload,
    user: User = Depends(get_current_user),
):
    """Add or update community-supplied details for an existing church."""
    if not church_id or len(church_id) > 200:
        raise HTTPException(status_code=400, detail="invalid church_id")
    # Trust but validate — the church should exist either as a community doc
    # OR be an OSM id (we don't have an OSM lookup table, but the prefix
    # `osm:` and the format are enough to gatekeep). This stops people from
    # spamming arbitrary string keys.
    if not (church_id.startswith("osm:") or church_id.startswith("community:")):
        raise HTTPException(status_code=400, detail="unsupported church_id format")

    now = datetime.now(timezone.utc)
    existing = await db.church_overlays.find_one({"church_id": church_id}, {"_id": 0}) or {}
    merged_mass = _merge_time_lists(
        existing.get("mass_times", []), payload.mass_times or [], payload.replace_mass
    )
    merged_conf = _merge_time_lists(
        existing.get("confession_times", []),
        payload.confession_times or [],
        payload.replace_confession,
    )
    website = _scalar_or_existing(payload.website, existing.get("website"))
    phone = _scalar_or_existing(payload.phone, existing.get("phone"))
    notes = _scalar_or_existing(payload.notes, existing.get("notes"))

    # Audit ring buffer (last 20 editors) — small footprint, useful for moderation.
    fields_touched: List[str] = []
    if payload.mass_times is not None:
        fields_touched.append("mass_times")
    if payload.confession_times is not None:
        fields_touched.append("confession_times")
    if payload.website is not None:
        fields_touched.append("website")
    if payload.phone is not None:
        fields_touched.append("phone")
    if payload.notes is not None:
        fields_touched.append("notes")
    editors = list(existing.get("editors") or [])
    editors.append({
        "user_id": user.user_id,
        "name": getattr(user, "name", None) or "Anonymous",
        "at": now.isoformat(),
        "fields": fields_touched,
        "name_visible": bool(payload.show_name),
    })
    editors = editors[-20:]

    doc = {
        "church_id": church_id,
        "mass_times": merged_mass,
        "confession_times": merged_conf,
        "website": website,
        "phone": phone,
        "notes": notes,
        "editors": editors,
        "updated_at": now,
        "created_at": existing.get("created_at") or now,
    }
    await db.church_overlays.update_one(
        {"church_id": church_id}, {"$set": doc}, upsert=True
    )
    return _overlay_to_shape(doc)


@api.get("/churches/{church_id:path}/overlay")
async def get_church_overlay(
    church_id: str,
    user: User = Depends(get_current_user),
):
    doc = await db.church_overlays.find_one({"church_id": church_id}, {"_id": 0})
    if not doc:
        return _overlay_to_shape({"church_id": church_id})
    return _overlay_to_shape(doc)


def _overlay_to_shape(doc: dict) -> dict:
    editors = list(doc.get("editors") or [])
    # Public attribution list: only editors who explicitly opted in to be
    # credited. We dedupe by user_id and keep the most recent name for each.
    seen: Dict[str, str] = {}
    for e in editors:
        if e.get("name_visible") and e.get("name"):
            seen[e.get("user_id") or e["name"]] = str(e["name"]).strip()
    contributors = [n for n in seen.values() if n]
    last_editor: Optional[Dict[str, Any]] = editors[-1] if editors else None
    return {
        "church_id": doc.get("church_id", ""),
        "mass_times": list(doc.get("mass_times") or []),
        "confession_times": list(doc.get("confession_times") or []),
        "website": doc.get("website") or "",
        "phone": doc.get("phone") or "",
        "notes": doc.get("notes") or "",
        "editor_count": len({e.get("user_id") for e in editors if e.get("user_id")}),
        "contributors": contributors,
        "last_edited_by": (
            last_editor.get("name") if (last_editor and last_editor.get("name_visible")) else None
        ),
        "updated_at": (
            doc["updated_at"].isoformat()
            if isinstance(doc.get("updated_at"), datetime)
            else doc.get("updated_at")
        ),
    }


async def _apply_overlays(churches: List[dict]) -> List[dict]:
    """Merge community overlays onto a list of church dicts in place. Mass /
    confession arrays union with overlay entries (overlay items appended after
    existing ones, deduped). Website / phone / notes — overlay wins when
    non-empty.

    The whole function is one Mongo query keyed by `church_id IN [...]`, so
    it stays cheap even on a full radius dump.
    """
    if not churches:
        return churches
    ids = [c.get("church_id") for c in churches if c.get("church_id")]
    if not ids:
        return churches
    cursor = db.church_overlays.find({"church_id": {"$in": ids}}, {"_id": 0})
    overlays = {o["church_id"]: o async for o in cursor}
    for c in churches:
        ov = overlays.get(c.get("church_id"))
        if not ov:
            c.setdefault("editor_count", 0)
            c.setdefault("contributors", [])
            c.setdefault("last_edited_by", None)
            continue
        # Time arrays: union with existing.
        existing_mass = list(c.get("mass_times") or [])
        existing_conf = list(c.get("confession_times") or [])
        seen_mass = {x.lower() for x in existing_mass}
        for t in (ov.get("mass_times") or []):
            if t.lower() not in seen_mass:
                existing_mass.append(t)
                seen_mass.add(t.lower())
        seen_conf = {x.lower() for x in existing_conf}
        for t in (ov.get("confession_times") or []):
            if t.lower() not in seen_conf:
                existing_conf.append(t)
                seen_conf.add(t.lower())
        c["mass_times"] = existing_mass
        c["confession_times"] = existing_conf
        # Scalars: overlay wins when non-empty.
        if ov.get("website"):
            c["website"] = ov["website"]
        if ov.get("phone"):
            c["phone"] = ov["phone"]
        if ov.get("notes"):
            c["notes"] = ov["notes"]
        editors = list(ov.get("editors") or [])
        c["editor_count"] = len({e.get("user_id") for e in editors if e.get("user_id")})
        # Visible contributors: dedupe by user_id and keep latest opted-in name.
        named: Dict[str, str] = {}
        for e in editors:
            if e.get("name_visible") and e.get("name"):
                named[e.get("user_id") or e["name"]] = str(e["name"]).strip()
        c["contributors"] = [n for n in named.values() if n]
        last = editors[-1] if editors else None
        c["last_edited_by"] = (last.get("name") if (last and last.get("name_visible")) else None)
    return churches


def _user_church_doc(d: dict) -> dict:
    return {
        "church_id": d["church_id"],
        "name": d.get("name", ""),
        "lat": d.get("lat"),
        "lng": d.get("lng"),
        "address": d.get("address", ""),
        "website": d.get("website", ""),
        "phone": d.get("phone", ""),
        "mass_times": d.get("mass_times") or [],
        "confession_times": d.get("confession_times") or [],
        "notes": d.get("notes", ""),
        "is_starred": True,
        "saved_at": d.get("saved_at"),
        "updated_at": d.get("updated_at"),
    }


@api.get("/churches/saved")
async def list_saved_churches(user: User = Depends(get_current_user)):
    cursor = db.user_churches.find({"user_id": user.user_id}, {"_id": 0}).sort("saved_at", -1)
    docs = await cursor.to_list(length=200)
    items = [_user_church_doc(d) for d in docs]
    # Apply community overlays so saved-church cards always show the latest
    # mass/confession/website edits made by anyone in the community.
    items = await _apply_overlays(items)
    return {"items": items}


@api.post("/churches/save")
async def save_church(payload: SaveChurchPayload, user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "user_id": user.user_id,
        "church_id": payload.church_id,
        "name": payload.name,
        "lat": payload.lat,
        "lng": payload.lng,
        "address": payload.address or "",
        "website": payload.website or "",
        "phone": payload.phone or "",
        "mass_times": payload.mass_times or [],
        "confession_times": payload.confession_times or [],
        "notes": payload.notes or "",
        "updated_at": now,
    }
    await db.user_churches.update_one(
        {"user_id": user.user_id, "church_id": payload.church_id},
        {"$set": doc, "$setOnInsert": {"saved_at": now}},
        upsert=True,
    )
    saved = await db.user_churches.find_one(
        {"user_id": user.user_id, "church_id": payload.church_id}, {"_id": 0}
    )
    return _user_church_doc(saved or doc)


@api.delete("/churches/saved/{church_id:path}")
async def unsave_church(church_id: str, user: User = Depends(get_current_user)):
    res = await db.user_churches.delete_one({"user_id": user.user_id, "church_id": church_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="church not in saved list")
    return {"ok": True}


# -------- bible (douay-rheims challoner) --------

class HighlightRequest(BaseModel):
    book: str
    chapter: int
    verse: int
    color: str  # rose | gold | sage | violet


@api.get("/bible/books")
async def bible_books():
    return {"items": bible_svc.all_books()}


@api.get("/bible/chapter/{book_slug}/{chapter}")
async def bible_chapter(book_slug: str, chapter: int, user: User = Depends(get_current_user)):
    data = await bible_svc.get_chapter(db, book_slug, chapter)
    cursor = db.bible_highlights.find(
        {"user_id": user.user_id, "book_slug": book_slug, "chapter": chapter},
        {"_id": 0, "verse": 1, "color": 1},
    )
    hl_list = await cursor.to_list(length=500)
    data["highlights"] = [{"verse": h["verse"], "color": h["color"]} for h in hl_list]
    return data


@api.post("/bible/highlight")
async def bible_set_highlight(payload: HighlightRequest, user: User = Depends(get_current_user)):
    slug, ch, v = bible_svc.parse_verse_ref(payload.book, payload.chapter, payload.verse)
    color = bible_svc.normalize_color(payload.color)
    now = datetime.now(timezone.utc).isoformat()
    await db.bible_highlights.update_one(
        {"user_id": user.user_id, "book_slug": slug, "chapter": ch, "verse": v},
        {"$set": {"color": color, "updated_at": now},
         "$setOnInsert": {"user_id": user.user_id, "book_slug": slug,
                          "chapter": ch, "verse": v, "created_at": now}},
        upsert=True,
    )
    return {"book": slug, "chapter": ch, "verse": v, "color": color}


@api.delete("/bible/highlight/{book_slug}/{chapter}/{verse}")
async def bible_clear_highlight(book_slug: str, chapter: int, verse: int,
                                user: User = Depends(get_current_user)):
    slug, ch, v = bible_svc.parse_verse_ref(book_slug, chapter, verse)
    res = await db.bible_highlights.delete_one(
        {"user_id": user.user_id, "book_slug": slug, "chapter": ch, "verse": v},
    )
    return {"deleted": res.deleted_count}


@api.get("/bible/highlights")
async def bible_my_highlights(user: User = Depends(get_current_user),
                              book: Optional[str] = None,
                              limit: int = 500):
    q: Dict[str, Any] = {"user_id": user.user_id}
    if book:
        q["book_slug"] = book
    cursor = db.bible_highlights.find(q, {"_id": 0, "user_id": 0}).sort("updated_at", -1).limit(min(max(limit, 1), 1000))
    items = await cursor.to_list(length=limit)
    # Enrich with citation for convenience.
    for it in items:
        it["citation"] = bible_svc.citation_for(it["book_slug"], it["chapter"], it["verse"])
    return {"items": items, "count": len(items)}


@api.get("/")
async def root():
    return {"app": "Sanctus", "status": "ok"}


# =====================================================================
# COMMUNITY — Phase 3: global parish feed, topical rooms, 1-on-1 DMs
# =====================================================================

class CommunityChallengeRef(BaseModel):
    slug: str
    name: Optional[str] = None
    day_index: Optional[int] = None
    day_title: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class CommunityPostRequest(BaseModel):
    body: str
    topic: Optional[str] = None  # None => Global parish feed
    image: Optional[str] = None  # base64 data URI (optional)
    challenge: Optional[CommunityChallengeRef] = None  # optional pinned ref to a Liturgical Challenge day


class CommunityReplyRequest(BaseModel):
    body: str


class CommunityDMStartRequest(BaseModel):
    user_id: str


class CommunityDMSendRequest(BaseModel):
    body: str


class CommunityReportRequest(BaseModel):
    target_type: str  # "post" | "reply" | "user" | "message"
    target_id: str
    reason: str
    detail: Optional[str] = None


# --- Friendships & group DMs ------------------------------------------------
class FriendActionRequest(BaseModel):
    user_id: str


class GroupDMCreateRequest(BaseModel):
    # All members the creator wants in the group. The creator is auto-added
    # if not present. Max community.MAX_GROUP_MEMBERS total (incl. creator).
    member_ids: List[str]
    name: Optional[str] = None


class GroupDMNameRequest(BaseModel):
    name: Optional[str] = None  # null => clear and fall back to auto-name


class GroupDMMemberRequest(BaseModel):
    user_id: str


async def _users_by_id(user_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    if not user_ids:
        return {}
    cursor = db.users.find({"user_id": {"$in": list(set(user_ids))}}, {"_id": 0})
    out: Dict[str, Dict[str, Any]] = {}
    async for u in cursor:
        out[u["user_id"]] = u
    return out


def _validate_topic(topic: Optional[str]) -> Optional[str]:
    if topic in (None, "", "all", "parish"):
        return None
    if topic not in community_svc.TOPIC_SLUGS:
        raise HTTPException(status_code=400, detail="Unknown topic")
    return topic


async def _is_blocked(user_a: str, user_b: str) -> bool:
    doc = await db.community_blocks.find_one({
        "$or": [
            {"user_id": user_a, "blocked_id": user_b},
            {"user_id": user_b, "blocked_id": user_a},
        ]
    })
    return doc is not None


# ---- Topics ----
@api.get("/community/topics")
async def community_topics(_: User = Depends(get_current_user)):
    return {"items": community_svc.TOPICS, "report_reasons": community_svc.REPORT_REASONS}


# ---- Feed ----
@api.get("/community/feed")
async def community_feed(
    topic: Optional[str] = None,
    limit: int = 30,
    before: Optional[str] = None,  # ISO datetime cursor
    user: User = Depends(get_current_user),
):
    t = _validate_topic(topic)
    q: Dict[str, Any] = {}
    if t is None:
        # Global feed includes ALL posts regardless of topic.
        pass
    else:
        q["topic"] = t
    if before:
        try:
            q["created_at"] = {"$lt": datetime.fromisoformat(before.replace("Z", "+00:00"))}
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid 'before' cursor")
    q.setdefault("hidden", {"$ne": True})

    limit = max(1, min(limit, 50))
    cursor = db.community_posts.find(q, {"_id": 0}).sort("created_at", -1).limit(limit)
    posts = await cursor.to_list(length=limit)

    author_ids = [p["author_id"] for p in posts]
    authors = await _users_by_id(author_ids)

    post_ids = [p["post_id"] for p in posts]
    liked_set = set()
    if post_ids:
        async for d in db.community_post_likes.find(
            {"post_id": {"$in": post_ids}, "user_id": user.user_id}, {"_id": 0, "post_id": 1}
        ):
            liked_set.add(d["post_id"])

    items = [
        community_svc.post_public(p, authors.get(p["author_id"]),
                                  liked_by_me=(p["post_id"] in liked_set))
        for p in posts
    ]
    next_cursor = community_svc.iso(posts[-1]["created_at"]) if len(posts) == limit else None
    return {"items": items, "next_cursor": next_cursor, "topic": t}


@api.post("/community/posts")
async def community_create_post(payload: CommunityPostRequest,
                                user: User = Depends(get_current_user)):
    body = community_svc.clean_body(payload.body, community_svc.MAX_POST_LEN)
    if not body:
        raise HTTPException(status_code=400, detail="Post body cannot be empty")
    t = _validate_topic(payload.topic)
    # Tag with today's liturgical color for a Catholic-themed badge
    try:
        today_iso = date.today().isoformat()
        lit = get_liturgical_day(today_iso)
        lit_color = lit.get("color")
        lit_season = lit.get("season")
    except Exception:
        lit_color = None
        lit_season = None

    post_id = f"post_{uuid.uuid4().hex[:14]}"
    challenge_ref = None
    if payload.challenge and payload.challenge.slug:
        challenge_ref = {
            "slug": payload.challenge.slug,
            "name": payload.challenge.name,
            "day_index": payload.challenge.day_index,
            "day_title": payload.challenge.day_title,
            "color": payload.challenge.color,
            "icon": payload.challenge.icon,
        }
    doc = {
        "post_id": post_id,
        "author_id": user.user_id,
        "body": body,
        "topic": t,
        "image": (payload.image or None),
        "liturgical_color": lit_color,
        "liturgical_season": lit_season,
        "challenge": challenge_ref,
        "created_at": community_svc.now_utc(),
        "like_count": 0,
        "reply_count": 0,
        "hidden": False,
        "is_pinned": False,
    }
    await db.community_posts.insert_one(doc)
    return community_svc.post_public(doc, {"user_id": user.user_id, "name": user.name, "picture": user.picture})


@api.get("/community/posts/{post_id}")
async def community_get_post(post_id: str, user: User = Depends(get_current_user)):
    p = await db.community_posts.find_one({"post_id": post_id}, {"_id": 0})
    if not p or p.get("hidden"):
        raise HTTPException(status_code=404, detail="Post not found")
    author = await db.users.find_one({"user_id": p["author_id"]}, {"_id": 0})
    liked = await db.community_post_likes.find_one(
        {"post_id": post_id, "user_id": user.user_id}, {"_id": 0}
    )
    return community_svc.post_public(p, author, liked_by_me=bool(liked))


@api.delete("/community/posts/{post_id}")
async def community_delete_post(post_id: str, user: User = Depends(get_current_user)):
    p = await db.community_posts.find_one({"post_id": post_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    if p["author_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Only the author can delete this post")
    await db.community_posts.delete_one({"post_id": post_id})
    await db.community_post_likes.delete_many({"post_id": post_id})
    await db.community_replies.delete_many({"post_id": post_id})
    return {"ok": True}


@api.post("/community/posts/{post_id}/like")
async def community_like(post_id: str, user: User = Depends(get_current_user)):
    p = await db.community_posts.find_one({"post_id": post_id}, {"_id": 0})
    if not p or p.get("hidden"):
        raise HTTPException(status_code=404, detail="Post not found")
    try:
        await db.community_post_likes.insert_one({
            "post_id": post_id,
            "user_id": user.user_id,
            "created_at": community_svc.now_utc(),
        })
        await db.community_posts.update_one({"post_id": post_id}, {"$inc": {"like_count": 1}})
        liked = True
    except Exception:
        await db.community_post_likes.delete_one({"post_id": post_id, "user_id": user.user_id})
        await db.community_posts.update_one({"post_id": post_id}, {"$inc": {"like_count": -1}})
        liked = False
    doc = await db.community_posts.find_one({"post_id": post_id}, {"_id": 0, "like_count": 1})
    return {"liked": liked, "like_count": max(0, int(doc.get("like_count") or 0))}


# ---- Replies ----
@api.get("/community/posts/{post_id}/replies")
async def community_replies(post_id: str, user: User = Depends(get_current_user)):
    p = await db.community_posts.find_one({"post_id": post_id}, {"_id": 0, "post_id": 1, "hidden": 1})
    if not p or p.get("hidden"):
        raise HTTPException(status_code=404, detail="Post not found")
    cursor = db.community_replies.find({"post_id": post_id, "hidden": {"$ne": True}}, {"_id": 0}).sort("created_at", 1)
    replies = await cursor.to_list(length=500)
    authors = await _users_by_id([r["author_id"] for r in replies])
    return {"items": [community_svc.reply_public(r, authors.get(r["author_id"])) for r in replies]}


@api.post("/community/posts/{post_id}/replies")
async def community_create_reply(post_id: str, payload: CommunityReplyRequest,
                                 user: User = Depends(get_current_user)):
    p = await db.community_posts.find_one({"post_id": post_id}, {"_id": 0, "post_id": 1, "hidden": 1})
    if not p or p.get("hidden"):
        raise HTTPException(status_code=404, detail="Post not found")
    body = community_svc.clean_body(payload.body, community_svc.MAX_REPLY_LEN)
    if not body:
        raise HTTPException(status_code=400, detail="Reply cannot be empty")
    reply_id = f"rep_{uuid.uuid4().hex[:14]}"
    doc = {
        "reply_id": reply_id,
        "post_id": post_id,
        "author_id": user.user_id,
        "body": body,
        "created_at": community_svc.now_utc(),
        "hidden": False,
    }
    await db.community_replies.insert_one(doc)
    await db.community_posts.update_one({"post_id": post_id}, {"$inc": {"reply_count": 1}})
    return community_svc.reply_public(doc, {"user_id": user.user_id, "name": user.name, "picture": user.picture})


@api.delete("/community/replies/{reply_id}")
async def community_delete_reply(reply_id: str, user: User = Depends(get_current_user)):
    r = await db.community_replies.find_one({"reply_id": reply_id}, {"_id": 0})
    if not r:
        raise HTTPException(status_code=404, detail="Reply not found")
    if r["author_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Only the author can delete this reply")
    await db.community_replies.delete_one({"reply_id": reply_id})
    await db.community_posts.update_one({"post_id": r["post_id"]}, {"$inc": {"reply_count": -1}})
    return {"ok": True}


# ---- People search & recommendations ----
@api.get("/community/users/search")
async def community_users_search(q: str = "",
                                 limit: int = 20,
                                 user: User = Depends(get_current_user)):
    q = (q or "").strip()
    if len(q) < 1:
        return {"items": []}
    limit = max(1, min(limit, 30))
    # Case-insensitive prefix-ish match on name or email
    import re
    pattern = re.compile(re.escape(q), re.IGNORECASE)
    cursor = db.users.find(
        {"$and": [
            {"user_id": {"$ne": user.user_id}},
            {"$or": [{"name": {"$regex": pattern}}, {"email": {"$regex": pattern}}]},
        ]},
        {"_id": 0},
    ).limit(limit)
    users = await cursor.to_list(length=limit)
    return {"items": [community_svc.public_user(u) for u in users]}


@api.get("/community/users/recommended")
async def community_users_recommended(limit: int = 12,
                                      user: User = Depends(get_current_user)):
    """Recommend recently active community members (excluding self)."""
    limit = max(1, min(limit, 30))
    # 1) Users who recently posted (engaged community)
    pipeline = [
        {"$match": {"author_id": {"$ne": user.user_id}}},
        {"$sort": {"created_at": -1}},
        {"$group": {"_id": "$author_id", "last_active": {"$first": "$created_at"}}},
        {"$sort": {"last_active": -1}},
        {"$limit": limit * 2},
    ]
    rec_ids: List[str] = []
    async for d in db.community_posts.aggregate(pipeline):
        if d.get("_id"):
            rec_ids.append(d["_id"])
    # 2) Fill with newest users overall if not enough recommendations
    if len(rec_ids) < limit:
        cur = db.users.find(
            {"user_id": {"$nin": rec_ids + [user.user_id]}}, {"_id": 0, "user_id": 1}
        ).sort("created_at", -1).limit(limit - len(rec_ids))
        async for d in cur:
            rec_ids.append(d["user_id"])
    rec_ids = rec_ids[:limit]
    users = await _users_by_id(rec_ids)
    items = [community_svc.public_user(users[uid]) for uid in rec_ids if uid in users]
    return {"items": items}


@api.get("/community/users/{user_id}")
async def community_user_profile(user_id: str, user: User = Depends(get_current_user)):
    u = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    # Recent posts by this user
    cur = db.community_posts.find(
        {"author_id": user_id, "hidden": {"$ne": True}}, {"_id": 0}
    ).sort("created_at", -1).limit(20)
    posts = await cur.to_list(length=20)
    post_ids = [p["post_id"] for p in posts]
    liked_set = set()
    if post_ids:
        async for d in db.community_post_likes.find(
            {"post_id": {"$in": post_ids}, "user_id": user.user_id}, {"_id": 0, "post_id": 1}
        ):
            liked_set.add(d["post_id"])
    return {
        "user": community_svc.public_user(u),
        "posts": [community_svc.post_public(p, u, liked_by_me=(p["post_id"] in liked_set)) for p in posts],
        "is_self": user_id == user.user_id,
    }


# ---- Direct Messages (1-on-1) ----
@api.get("/community/dm/unread-count")
async def dm_unread_count(user: User = Depends(get_current_user)):
    """Total number of unread DM messages across all of the user's threads.

    Used by the bottom-tab badge and the Inbox icon badge in the Parish
    header. Cheap to call (one find + one count_documents per thread).
    Returns 0 silently if the user has no threads.
    """
    cur = db.community_dm_threads.find(
        {"member_ids": user.user_id},
        {"_id": 0, "thread_id": 1, "reads": 1},
    )
    threads = await cur.to_list(length=500)
    total = 0
    per_thread: List[Dict[str, Any]] = []
    for t in threads:
        my_reads = (t.get("reads") or {})
        last_read_at = my_reads.get(user.user_id)
        q: Dict[str, Any] = {
            "thread_id": t["thread_id"],
            "sender_id": {"$ne": user.user_id},
        }
        if last_read_at:
            q["created_at"] = {"$gt": last_read_at}
        n = await db.community_dm_messages.count_documents(q)
        if n > 0:
            per_thread.append({"thread_id": t["thread_id"], "unread": n})
            total += n
    return {"total": total, "threads": per_thread}


@api.get("/community/dm/threads")
async def dm_threads(user: User = Depends(get_current_user)):
    cur = db.community_dm_threads.find(
        {"member_ids": user.user_id}, {"_id": 0}
    ).sort("last_message_at", -1)
    threads = await cur.to_list(length=200)
    # Resolve other member
    other_ids: List[str] = []
    for t in threads:
        for m in t.get("member_ids", []):
            if m != user.user_id:
                other_ids.append(m)
    others = await _users_by_id(other_ids)

    items: List[Dict[str, Any]] = []
    for t in threads:
        other_id = next((m for m in t.get("member_ids", []) if m != user.user_id), None)
        # Compute unread count: messages from other after my last_read_at
        my_reads = t.get("reads", {}) or {}
        last_read_at = my_reads.get(user.user_id)
        unread_q: Dict[str, Any] = {"thread_id": t["thread_id"], "sender_id": {"$ne": user.user_id}}
        if last_read_at:
            unread_q["created_at"] = {"$gt": last_read_at}
        unread = await db.community_dm_messages.count_documents(unread_q)
        items.append(community_svc.thread_public(t, others.get(other_id) if other_id else None, unread=unread))
    return {"items": items}


@api.post("/community/dm/threads")
async def dm_start_thread(payload: CommunityDMStartRequest,
                          user: User = Depends(get_current_user)):
    if payload.user_id == user.user_id:
        raise HTTPException(status_code=400, detail="Cannot message yourself")
    other = await db.users.find_one({"user_id": payload.user_id}, {"_id": 0})
    if not other:
        raise HTTPException(status_code=404, detail="User not found")
    tid = community_svc.thread_key(user.user_id, payload.user_id)
    existing = await db.community_dm_threads.find_one({"thread_id": tid}, {"_id": 0})
    if existing:
        return community_svc.thread_public(existing, other)
    doc = {
        "thread_id": tid,
        "member_ids": [user.user_id, payload.user_id],
        "created_at": community_svc.now_utc(),
        "last_message_at": community_svc.now_utc(),
        "last_message": None,
        "reads": {},
    }
    await db.community_dm_threads.insert_one(doc)
    return community_svc.thread_public(doc, other)


@api.get("/community/dm/threads/{thread_id}/messages")
async def dm_messages(thread_id: str, user: User = Depends(get_current_user)):
    t = await db.community_dm_threads.find_one({"thread_id": thread_id}, {"_id": 0})
    if not t or user.user_id not in (t.get("member_ids") or []):
        raise HTTPException(status_code=404, detail="Thread not found")
    cur = db.community_dm_messages.find({"thread_id": thread_id}, {"_id": 0}).sort("created_at", 1)
    msgs = await cur.to_list(length=2000)
    # Mark thread as read by me
    await db.community_dm_threads.update_one(
        {"thread_id": thread_id},
        {"$set": {f"reads.{user.user_id}": community_svc.now_utc()}},
    )
    if t.get("is_group"):
        members_lookup = await _users_by_id(list(t.get("member_ids") or []))
        thread_view = community_svc.thread_public(
            t, None, members_lookup=members_lookup, viewer_id=user.user_id,
        )
    else:
        other_id = next((m for m in t.get("member_ids", []) if m != user.user_id), None)
        other = await db.users.find_one({"user_id": other_id}, {"_id": 0}) if other_id else None
        thread_view = community_svc.thread_public(t, other)
    return {
        "thread": thread_view,
        "messages": [community_svc.message_public(m) for m in msgs],
    }


@api.post("/community/dm/threads/{thread_id}/messages")
async def dm_send_message(thread_id: str, payload: CommunityDMSendRequest,
                          user: User = Depends(get_current_user)):
    t = await db.community_dm_threads.find_one({"thread_id": thread_id}, {"_id": 0})
    if not t or user.user_id not in (t.get("member_ids") or []):
        raise HTTPException(status_code=404, detail="Thread not found")
    body = community_svc.clean_body(payload.body, community_svc.MAX_DM_LEN)
    if not body:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    # In 1-on-1 threads, respect block lists. In groups, individual member
    # blocks shouldn't gag the whole conversation — moderation happens via
    # report + remove-from-group instead.
    if not t.get("is_group"):
        other_id = next((m for m in t.get("member_ids", []) if m != user.user_id), None)
        if other_id and await _is_blocked(user.user_id, other_id):
            raise HTTPException(status_code=403, detail="Messaging is blocked between these users")
    msg_id = f"msg_{uuid.uuid4().hex[:14]}"
    now = community_svc.now_utc()
    doc = {
        "message_id": msg_id,
        "thread_id": thread_id,
        "sender_id": user.user_id,
        "body": body,
        "created_at": now,
    }
    await db.community_dm_messages.insert_one(doc)
    preview = body if len(body) <= 80 else body[:77] + "…"
    await db.community_dm_threads.update_one(
        {"thread_id": thread_id},
        {"$set": {
            "last_message": preview,
            "last_message_at": now,
            f"reads.{user.user_id}": now,
        }},
    )
    return community_svc.message_public(doc)


# ---- Group DM management ------------------------------------------------
@api.post("/community/dm/threads/group")
async def dm_create_group(payload: GroupDMCreateRequest,
                          user: User = Depends(get_current_user)):
    """Create a new group DM. Creator is auto-added. Capped at MAX_GROUP_MEMBERS.

    Group DMs are a Sanctus Premium feature. 1-on-1 DMs remain free for all.
    """
    from premium import require_premium
    require_premium(user, feature="Group DMs")
    requested = list({m for m in (payload.member_ids or []) if m})
    if user.user_id in requested:
        requested.remove(user.user_id)
    if not requested:
        raise HTTPException(status_code=400, detail="Pick at least one other person.")
    if len(requested) + 1 > community_svc.MAX_GROUP_MEMBERS:
        raise HTTPException(
            status_code=400,
            detail=f"Group chats are limited to {community_svc.MAX_GROUP_MEMBERS} people.",
        )
    found = await _users_by_id(requested)
    missing = [m for m in requested if m not in found]
    if missing:
        raise HTTPException(status_code=404, detail=f"Unknown user(s): {', '.join(missing)}")
    name = community_svc.clean_group_name(payload.name)
    member_ids = sorted([user.user_id] + requested)
    tid = f"group:{uuid.uuid4().hex[:14]}"
    now = community_svc.now_utc()
    doc = {
        "thread_id": tid,
        "member_ids": member_ids,
        "is_group": True,
        "name": name,
        "created_by": user.user_id,
        "created_at": now,
        "last_message_at": now,
        "last_message": None,
        "reads": {},
    }
    await db.community_dm_threads.insert_one(doc)
    members_lookup = await _users_by_id(member_ids)
    return community_svc.thread_public(doc, None, members_lookup=members_lookup, viewer_id=user.user_id)


@api.put("/community/dm/threads/{thread_id}/name")
async def dm_rename_group(thread_id: str, payload: GroupDMNameRequest,
                          user: User = Depends(get_current_user)):
    t = await db.community_dm_threads.find_one({"thread_id": thread_id}, {"_id": 0})
    if not t or not t.get("is_group") or user.user_id not in (t.get("member_ids") or []):
        raise HTTPException(status_code=404, detail="Group not found")
    name = community_svc.clean_group_name(payload.name)
    await db.community_dm_threads.update_one(
        {"thread_id": thread_id}, {"$set": {"name": name}}
    )
    fresh = await db.community_dm_threads.find_one({"thread_id": thread_id}, {"_id": 0})
    members_lookup = await _users_by_id(list(fresh.get("member_ids") or []))
    return community_svc.thread_public(fresh, None, members_lookup=members_lookup, viewer_id=user.user_id)


@api.post("/community/dm/threads/{thread_id}/members")
async def dm_add_group_member(thread_id: str, payload: GroupDMMemberRequest,
                              user: User = Depends(get_current_user)):
    t = await db.community_dm_threads.find_one({"thread_id": thread_id}, {"_id": 0})
    if not t or not t.get("is_group") or user.user_id not in (t.get("member_ids") or []):
        raise HTTPException(status_code=404, detail="Group not found")
    new_id = payload.user_id
    if new_id in (t.get("member_ids") or []):
        return community_svc.thread_public(t, None,
                                            members_lookup=await _users_by_id(list(t.get("member_ids") or [])),
                                            viewer_id=user.user_id)
    if len(t.get("member_ids") or []) + 1 > community_svc.MAX_GROUP_MEMBERS:
        raise HTTPException(status_code=400,
                            detail=f"This group is full ({community_svc.MAX_GROUP_MEMBERS} max).")
    new_user = await db.users.find_one({"user_id": new_id}, {"_id": 0})
    if not new_user:
        raise HTTPException(status_code=404, detail="Unknown user")
    await db.community_dm_threads.update_one(
        {"thread_id": thread_id},
        {"$addToSet": {"member_ids": new_id}, "$set": {"last_message_at": community_svc.now_utc()}},
    )
    fresh = await db.community_dm_threads.find_one({"thread_id": thread_id}, {"_id": 0})
    members_lookup = await _users_by_id(list(fresh.get("member_ids") or []))
    return community_svc.thread_public(fresh, None, members_lookup=members_lookup, viewer_id=user.user_id)


@api.delete("/community/dm/threads/{thread_id}/members/{user_id}")
async def dm_remove_group_member(thread_id: str, user_id: str,
                                  user: User = Depends(get_current_user)):
    """Leave a group (when user_id == caller) or remove a member (creator only)."""
    t = await db.community_dm_threads.find_one({"thread_id": thread_id}, {"_id": 0})
    if not t or not t.get("is_group") or user.user_id not in (t.get("member_ids") or []):
        raise HTTPException(status_code=404, detail="Group not found")
    is_self = user_id == user.user_id
    is_creator = t.get("created_by") == user.user_id
    if not is_self and not is_creator:
        raise HTTPException(status_code=403, detail="Only the creator can remove others.")
    if user_id not in (t.get("member_ids") or []):
        raise HTTPException(status_code=404, detail="User is not in this group")
    await db.community_dm_threads.update_one(
        {"thread_id": thread_id},
        {"$pull": {"member_ids": user_id}},
    )
    fresh = await db.community_dm_threads.find_one({"thread_id": thread_id}, {"_id": 0})
    # Last person out deletes the thread + its messages.
    if not (fresh.get("member_ids") or []):
        await db.community_dm_threads.delete_one({"thread_id": thread_id})
        await db.community_dm_messages.delete_many({"thread_id": thread_id})
        return {"ok": True, "deleted": True}
    return {"ok": True, "deleted": False}


# ---- Friendships --------------------------------------------------------
async def _get_friendship(a: str, b: str) -> Optional[Dict[str, Any]]:
    return await db.community_friendships.find_one(
        {"friendship_id": community_svc.friendship_key(a, b)}, {"_id": 0}
    )


@api.get("/community/friends/status/{user_id}")
async def friend_status(user_id: str, user: User = Depends(get_current_user)):
    """Lightweight endpoint so a user-profile screen can render the right
    button (Add friend / Pending / Friends / Accept / Cancel) in one call."""
    if user_id == user.user_id:
        return {"status": "self", "requested_by": None}
    f = await _get_friendship(user.user_id, user_id)
    if not f:
        return {"status": "none", "requested_by": None}
    return {
        "status": f.get("status", "pending"),
        "requested_by": f.get("requested_by"),
    }


@api.post("/community/friends/request")
async def friend_request(payload: FriendActionRequest,
                         user: User = Depends(get_current_user)):
    if payload.user_id == user.user_id:
        raise HTTPException(status_code=400, detail="Cannot friend yourself")
    other = await db.users.find_one({"user_id": payload.user_id}, {"_id": 0})
    if not other:
        raise HTTPException(status_code=404, detail="User not found")
    if await _is_blocked(user.user_id, payload.user_id):
        raise HTTPException(status_code=403, detail="Cannot send a request to this user")
    key = community_svc.friendship_key(user.user_id, payload.user_id)
    existing = await db.community_friendships.find_one({"friendship_id": key}, {"_id": 0})
    if existing:
        if existing.get("status") == "accepted":
            raise HTTPException(status_code=400, detail="Already friends")
        # Pending in either direction — idempotent.
        return community_svc.friendship_public(existing, other)
    now = community_svc.now_utc()
    doc = {
        "friendship_id": key,
        "members": sorted([user.user_id, payload.user_id]),
        "status": "pending",
        "requested_by": user.user_id,
        "created_at": now,
        "accepted_at": None,
    }
    await db.community_friendships.insert_one(doc)
    return community_svc.friendship_public(doc, other)


@api.post("/community/friends/accept")
async def friend_accept(payload: FriendActionRequest,
                        user: User = Depends(get_current_user)):
    f = await _get_friendship(user.user_id, payload.user_id)
    if not f:
        raise HTTPException(status_code=404, detail="No friend request from this user")
    if f.get("status") == "accepted":
        other = await db.users.find_one({"user_id": payload.user_id}, {"_id": 0})
        return community_svc.friendship_public(f, other)
    if f.get("requested_by") == user.user_id:
        raise HTTPException(status_code=400, detail="You sent this request; the other person must accept")
    now = community_svc.now_utc()
    await db.community_friendships.update_one(
        {"friendship_id": f["friendship_id"]},
        {"$set": {"status": "accepted", "accepted_at": now}},
    )
    fresh = await _get_friendship(user.user_id, payload.user_id)
    other = await db.users.find_one({"user_id": payload.user_id}, {"_id": 0})
    return community_svc.friendship_public(fresh, other)


@api.post("/community/friends/decline")
async def friend_decline(payload: FriendActionRequest,
                          user: User = Depends(get_current_user)):
    """Decline an incoming request, OR cancel an outgoing one. Either side
    can erase a pending edge; only the requester can cancel their own
    outgoing request."""
    f = await _get_friendship(user.user_id, payload.user_id)
    if not f:
        return {"ok": True}
    if f.get("status") == "accepted":
        raise HTTPException(status_code=400, detail="Use unfriend instead")
    await db.community_friendships.delete_one({"friendship_id": f["friendship_id"]})
    return {"ok": True}


@api.delete("/community/friends/{user_id}")
async def friend_remove(user_id: str, user: User = Depends(get_current_user)):
    f = await _get_friendship(user.user_id, user_id)
    if not f:
        return {"ok": True}
    await db.community_friendships.delete_one({"friendship_id": f["friendship_id"]})
    return {"ok": True}


@api.get("/community/friends/list")
async def friend_list(status: str = "accepted",
                       user: User = Depends(get_current_user)):
    """status: accepted | incoming | outgoing"""
    if status not in ("accepted", "incoming", "outgoing"):
        raise HTTPException(status_code=400, detail="status must be accepted, incoming, or outgoing")
    q: Dict[str, Any] = {"members": user.user_id}
    if status == "accepted":
        q["status"] = "accepted"
    elif status == "incoming":
        q["status"] = "pending"
        q["requested_by"] = {"$ne": user.user_id}
    elif status == "outgoing":
        q["status"] = "pending"
        q["requested_by"] = user.user_id
    cur = db.community_friendships.find(q, {"_id": 0}).sort("created_at", -1)
    rows = await cur.to_list(length=500)
    other_ids = []
    for r in rows:
        for m in (r.get("members") or []):
            if m != user.user_id:
                other_ids.append(m)
    others = await _users_by_id(other_ids)
    items = []
    for r in rows:
        other_id = next((m for m in (r.get("members") or []) if m != user.user_id), None)
        items.append(community_svc.friendship_public(r, others.get(other_id) if other_id else None))
    return {"items": items, "count": len(items)}


# ---- Reporting & Blocking ----
@api.post("/community/report")
async def community_report(payload: CommunityReportRequest,
                           user: User = Depends(get_current_user)):
    if payload.target_type not in ("post", "reply", "user", "message"):
        raise HTTPException(status_code=400, detail="Invalid target_type")
    if not payload.reason or payload.reason not in community_svc.REPORT_REASONS:
        raise HTTPException(status_code=400, detail="Invalid reason")
    report_id = f"rep_{uuid.uuid4().hex[:12]}"
    await db.community_reports.insert_one({
        "report_id": report_id,
        "reporter_id": user.user_id,
        "target_type": payload.target_type,
        "target_id": payload.target_id,
        "reason": payload.reason,
        "detail": (payload.detail or "").strip()[:500],
        "created_at": community_svc.now_utc(),
        "resolved": False,
    })
    return {"ok": True, "report_id": report_id}


@api.post("/community/block/{user_id}")
async def community_block(user_id: str, user: User = Depends(get_current_user)):
    if user_id == user.user_id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
    try:
        await db.community_blocks.insert_one({
            "user_id": user.user_id,
            "blocked_id": user_id,
            "created_at": community_svc.now_utc(),
        })
    except Exception:
        pass
    return {"ok": True}


@api.delete("/community/block/{user_id}")
async def community_unblock(user_id: str, user: User = Depends(get_current_user)):
    await db.community_blocks.delete_one({"user_id": user.user_id, "blocked_id": user_id})
    return {"ok": True}


# =====================================================================
# SELF-DEFENSE — Phase 4: martial arts subsection inside Workouts
# =====================================================================

class SDGenerateRequest(BaseModel):
    discipline_id: str
    duration_minutes: int = 45
    equipment: List[str] = []
    has_partner: bool = False
    override_level: Optional[str] = None  # "beginner" | "intermediate" | "advanced"
    include_patron_reflection: bool = True


class SDCompleteRequest(BaseModel):
    notes: Optional[str] = None
    intensity_actual: Optional[str] = None  # "low" | "medium" | "high"


def _sd_validate_discipline(discipline_id: str) -> Dict[str, Any]:
    d = sd_svc.get_discipline(discipline_id)
    if not d:
        raise HTTPException(status_code=404, detail="Unknown discipline")
    return d


async def _sd_get_progress(user_id: str, discipline_id: str) -> Dict[str, Any]:
    defaults = {
        "user_id": user_id,
        "discipline_id": discipline_id,
        "current_level": "beginner",
        "sessions_generated": 0,
        "sessions_completed": 0,
        "recent_focus": [],
        "last_session_at": None,
        "last_completed_at": None,
    }
    doc = await db.self_defense_progress.find_one(
        {"user_id": user_id, "discipline_id": discipline_id}, {"_id": 0}
    )
    if doc:
        return {**defaults, **doc}
    return defaults


@api.get("/self-defense/disciplines")
async def sd_list_disciplines(_: User = Depends(get_current_user)):
    items = []
    for d in sd_svc.DISCIPLINES:
        patron = sd_svc.get_patron(d["id"]) or {}
        items.append({**d, "patron": patron})
    return {"items": items, "disclaimer": sd_svc.SAFETY_DISCLAIMER}


@api.get("/self-defense/disciplines/{discipline_id}")
async def sd_discipline_detail(discipline_id: str, user: User = Depends(get_current_user)):
    d = _sd_validate_discipline(discipline_id)
    patron = sd_svc.get_patron(discipline_id) or {}
    progress = await _sd_get_progress(user.user_id, discipline_id)
    progress["current_level"] = sd_svc.determine_level(progress)
    return {"discipline": d, "patron": patron, "progress": progress}


@api.get("/self-defense/disclaimer")
async def sd_disclaimer_status(user: User = Depends(get_current_user)):
    doc = await db.self_defense_acks.find_one({"user_id": user.user_id}, {"_id": 0})
    return {"text": sd_svc.SAFETY_DISCLAIMER, "acknowledged": bool(doc), "acknowledged_at": (doc or {}).get("acknowledged_at")}


@api.post("/self-defense/disclaimer/acknowledge")
async def sd_disclaimer_ack(user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    await db.self_defense_acks.update_one(
        {"user_id": user.user_id},
        {"$set": {"user_id": user.user_id, "acknowledged_at": now}},
        upsert=True,
    )
    return {"ok": True, "acknowledged_at": now}


@api.post("/self-defense/generate")
async def sd_generate(payload: SDGenerateRequest, user: User = Depends(get_current_user)):
    discipline = _sd_validate_discipline(payload.discipline_id)
    patron = sd_svc.get_patron(payload.discipline_id) or {}
    progress = await _sd_get_progress(user.user_id, payload.discipline_id)
    level = (payload.override_level or sd_svc.determine_level(progress)).lower()
    if level not in sd_svc.LEVEL_ORDER:
        level = "beginner"
    duration = max(15, min(int(payload.duration_minutes or 45), 120))

    system = sd_svc.build_session_system_prompt()
    user_prompt = sd_svc.build_session_user_prompt(
        discipline=discipline,
        patron=patron,
        level=level,
        duration_minutes=duration,
        equipment=payload.equipment or [],
        has_partner=bool(payload.has_partner),
        sessions_completed=int(progress.get("sessions_completed") or 0),
        recent_focus=list(progress.get("recent_focus") or []),
        include_patron_reflection=bool(payload.include_patron_reflection),
    )

    sess_id_key = f"sd-{user.user_id}-{payload.discipline_id}-{uuid.uuid4().hex[:8]}"
    plan = await _chat_json(system, user_prompt, session_id=sess_id_key)

    session_id = f"sd_{uuid.uuid4().hex[:14]}"
    now = datetime.now(timezone.utc)
    doc = {
        "session_id": session_id,
        "user_id": user.user_id,
        "discipline_id": payload.discipline_id,
        "discipline_name": discipline["name"],
        "tradition": discipline["tradition"],
        "level": level,
        "duration_minutes": duration,
        "equipment": payload.equipment or [],
        "has_partner": bool(payload.has_partner),
        "include_patron_reflection": bool(payload.include_patron_reflection),
        "patron": patron,
        "plan": plan,
        "generated_at": now,
        "completed_at": None,
        "completion_notes": None,
        "intensity_actual": None,
        "source": "generated",
        "parent_session_id": None,
    }
    await db.self_defense_sessions.insert_one(doc)

    # Bump progress.sessions_generated and recent_focus
    new_focus = (plan or {}).get("technique_focus")
    recent = list(progress.get("recent_focus") or [])
    if new_focus:
        recent.append(new_focus)
        recent = recent[-10:]
    await db.self_defense_progress.update_one(
        {"user_id": user.user_id, "discipline_id": payload.discipline_id},
        {
            "$set": {
                "user_id": user.user_id,
                "discipline_id": payload.discipline_id,
                "current_level": level,
                "recent_focus": recent,
                "last_session_at": now.isoformat(),
            },
            "$inc": {"sessions_generated": 1},
        },
        upsert=True,
    )

    return _sd_session_public(doc)


@api.get("/self-defense/sessions")
async def sd_list_sessions(
    discipline_id: Optional[str] = None,
    completed: Optional[bool] = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
):
    q: Dict[str, Any] = {"user_id": user.user_id}
    if discipline_id:
        _sd_validate_discipline(discipline_id)
        q["discipline_id"] = discipline_id
    if completed is True:
        q["completed_at"] = {"$ne": None}
    elif completed is False:
        q["completed_at"] = None
    limit = max(1, min(limit, 100))
    cursor = db.self_defense_sessions.find(q, {"_id": 0}).sort("generated_at", -1).limit(limit)
    items = [_sd_session_public(d) async for d in cursor]
    return {"items": items}


@api.get("/self-defense/sessions/{session_id}")
async def sd_get_session(session_id: str, user: User = Depends(get_current_user)):
    doc = await db.self_defense_sessions.find_one(
        {"session_id": session_id, "user_id": user.user_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    return _sd_session_public(doc)


@api.delete("/self-defense/sessions/{session_id}")
async def sd_delete_session(session_id: str, user: User = Depends(get_current_user)):
    res = await db.self_defense_sessions.delete_one(
        {"session_id": session_id, "user_id": user.user_id}
    )
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@api.post("/self-defense/sessions/{session_id}/complete")
async def sd_complete_session(session_id: str, payload: SDCompleteRequest,
                              user: User = Depends(get_current_user)):
    doc = await db.self_defense_sessions.find_one(
        {"session_id": session_id, "user_id": user.user_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    now = datetime.now(timezone.utc)
    was_completed = doc.get("completed_at") is not None
    notes = (payload.notes or "").strip()[:1000] or None
    intensity = payload.intensity_actual if payload.intensity_actual in ("low", "medium", "high") else None
    await db.self_defense_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"completed_at": now, "completion_notes": notes, "intensity_actual": intensity}},
    )

    if not was_completed:
        # Bump completion counter and possibly promote level
        progress = await _sd_get_progress(user.user_id, doc["discipline_id"])
        completed_count = int(progress.get("sessions_completed") or 0) + 1
        promoted_level = sd_svc.determine_level({**progress, "sessions_completed": completed_count})
        await db.self_defense_progress.update_one(
            {"user_id": user.user_id, "discipline_id": doc["discipline_id"]},
            {
                "$set": {
                    "current_level": promoted_level,
                    "last_completed_at": now.isoformat(),
                },
                "$inc": {"sessions_completed": 1},
            },
            upsert=True,
        )
    refreshed = await db.self_defense_sessions.find_one(
        {"session_id": session_id}, {"_id": 0}
    )
    return _sd_session_public(refreshed)


@api.post("/self-defense/sessions/{session_id}/uncomplete")
async def sd_uncomplete_session(session_id: str, user: User = Depends(get_current_user)):
    doc = await db.self_defense_sessions.find_one(
        {"session_id": session_id, "user_id": user.user_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    if doc.get("completed_at") is None:
        return _sd_session_public(doc)
    await db.self_defense_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"completed_at": None, "completion_notes": None, "intensity_actual": None}},
    )
    await db.self_defense_progress.update_one(
        {"user_id": user.user_id, "discipline_id": doc["discipline_id"]},
        {"$inc": {"sessions_completed": -1}},
    )
    # Make sure we don't go below zero
    await db.self_defense_progress.update_one(
        {"user_id": user.user_id, "discipline_id": doc["discipline_id"], "sessions_completed": {"$lt": 0}},
        {"$set": {"sessions_completed": 0}},
    )
    refreshed = await db.self_defense_sessions.find_one({"session_id": session_id}, {"_id": 0})
    return _sd_session_public(refreshed)


@api.post("/self-defense/sessions/{session_id}/redo")
async def sd_redo_session(session_id: str, user: User = Depends(get_current_user)):
    """Duplicate an existing session as a new uncompleted session (so the user can rerun it)."""
    src = await db.self_defense_sessions.find_one(
        {"session_id": session_id, "user_id": user.user_id}, {"_id": 0}
    )
    if not src:
        raise HTTPException(status_code=404, detail="Session not found")
    new_id = f"sd_{uuid.uuid4().hex[:14]}"
    now = datetime.now(timezone.utc)
    doc = {
        **src,
        "session_id": new_id,
        "generated_at": now,
        "completed_at": None,
        "completion_notes": None,
        "intensity_actual": None,
        "source": "redo",
        "parent_session_id": session_id,
    }
    await db.self_defense_sessions.insert_one(doc)
    await db.self_defense_progress.update_one(
        {"user_id": user.user_id, "discipline_id": doc["discipline_id"]},
        {"$set": {"last_session_at": now.isoformat()}, "$inc": {"sessions_generated": 1}},
        upsert=True,
    )
    return _sd_session_public(doc)


@api.get("/self-defense/progress")
async def sd_progress_all(user: User = Depends(get_current_user)):
    items: List[Dict[str, Any]] = []
    for d in sd_svc.DISCIPLINES:
        prog = await _sd_get_progress(user.user_id, d["id"])
        prog["current_level"] = sd_svc.determine_level(prog)
        items.append({
            "discipline_id": d["id"],
            "discipline_name": d["name"],
            "icon": d["icon"],
            "progress": prog,
            "patron_name": (sd_svc.get_patron(d["id"]) or {}).get("name"),
        })
    return {"items": items}


def _sd_session_public(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return {}
    return {
        "session_id": doc.get("session_id"),
        "discipline_id": doc.get("discipline_id"),
        "discipline_name": doc.get("discipline_name"),
        "tradition": doc.get("tradition"),
        "level": doc.get("level"),
        "duration_minutes": doc.get("duration_minutes"),
        "equipment": doc.get("equipment") or [],
        "has_partner": bool(doc.get("has_partner")),
        "include_patron_reflection": bool(doc.get("include_patron_reflection")),
        "patron": doc.get("patron") or {},
        "plan": doc.get("plan") or {},
        "generated_at": _iso(doc.get("generated_at")),
        "completed_at": _iso(doc.get("completed_at")),
        "completion_notes": doc.get("completion_notes"),
        "intensity_actual": doc.get("intensity_actual"),
        "source": doc.get("source") or "generated",
        "parent_session_id": doc.get("parent_session_id"),
    }


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return None


from daily_practices import build_router as build_daily_practice_router
from catechism import build_router as build_catechism_router
from parish_events import build_router as build_parish_events_router
from saints import build_router as build_saints_router
from challenges import build_router as build_challenges_router
from shop import build_router as build_shop_router
from charity import build_router as build_charity_router
from library import build_router as build_library_router
from legal import build_legal_router
from subscriptions import build_subscriptions_router
from missals import build_router as build_missals_router
from liturgy_of_hours import build_router as build_liturgy_router
from virtues import build_router as build_virtues_router
from schedule import build_router as build_schedule_router

api.include_router(build_daily_practice_router(db, get_current_user))
api.include_router(build_catechism_router(db, get_current_user, EMERGENT_LLM_KEY))
api.include_router(build_parish_events_router(db, get_current_user))
api.include_router(build_saints_router(db, get_current_user, EMERGENT_LLM_KEY))
api.include_router(build_challenges_router(db, get_current_user, EMERGENT_LLM_KEY))
api.include_router(build_shop_router(db, get_current_user))
api.include_router(build_charity_router(db, get_current_user))
api.include_router(build_library_router(db, get_current_user))
api.include_router(build_subscriptions_router(db, get_current_user))
api.include_router(build_missals_router(db, get_current_user))
api.include_router(build_liturgy_router(db, get_current_user))
api.include_router(build_virtues_router(db, get_current_user, EMERGENT_LLM_KEY))
api.include_router(build_schedule_router(db, get_current_user))


async def _resolve_session_user_optional(authorization: Optional[str]):
    """Used by the public /legal/support/contact endpoint to attach a user
    record when a bearer token is present, without raising 401 for anonymous
    callers."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        return None
    exp = session.get("expires_at")
    if exp is not None:
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            return None
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        return None
    return User(**user_doc)


api.include_router(build_legal_router(db, _resolve_session_user_optional))

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def language_middleware(request: Request, call_next):
    """Resolve the request language from Accept-Language into a ContextVar so
    AI prompt builders can author content in the user's chosen language."""
    token = current_lang.set(resolve_lang(request.headers.get("accept-language")))
    try:
        return await call_next(request)
    finally:
        current_lang.reset(token)


@app.on_event("startup")
async def on_startup():
    await ensure_indexes()
    logger.info("Sanctus API ready")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()

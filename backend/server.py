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


# ---------- Auth helpers ----------
async def ensure_indexes():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.user_sessions.create_index("session_token", unique=True)
    await db.user_sessions.create_index("user_id")
    await db.user_sessions.create_index("expires_at", expireAfterSeconds=0)


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

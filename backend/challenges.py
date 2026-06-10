"""Sanctus Liturgical Challenges.

Three marquee tracks — Hallowtide, Advent, Lent — built as a flexible
"challenge engine":

* **liturgical_challenges**  – metadata for each track (slug, season, dates,
  opening/closing patron-saint prayer, preparation content, status).
* **challenge_days**         – one row per day in each track (patron saint,
  prayer items, reflection, theme).
* **challenge_enrollments**  – per-user opt-in + computed progress.
* **challenge_checkins**     – one row per (user, challenge, date) recording
  the items the user marked done and an optional written reflection.

Daily content is **AI-seeded** (Claude via Emergent LLM key) and then admin-
approved before publish. Once a challenge is published, users can enroll and
check in day-by-day.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from dateutil.easter import easter
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("sanctus.challenges")


# ---------------------------------------------------------------------------
# Constants & seed data
# ---------------------------------------------------------------------------


CHALLENGE_SLUGS = ("hallowtide", "advent", "lent")

ALLOWED_ITEM_KINDS = (
    "rosary",
    "prayer",
    "scripture",
    "reflection",
    "mass_reading",
    "almsgiving",
    "fasting",
    "act_of_charity",
    "examen",
    "spiritual_reading",
    "litany",
    "act_of_mercy",
    "patron_invocation",
    "service",
)


# ---------------------------------------------------------------------------
# Liturgical date helpers
# ---------------------------------------------------------------------------


def _ash_wednesday(year: int) -> date:
    """46 days before Easter Sunday."""
    return easter(year) - timedelta(days=46)


def _holy_saturday(year: int) -> date:
    return easter(year) - timedelta(days=1)


def _first_sunday_of_advent(year: int) -> date:
    """The Sunday closest to Nov 30 (St. Andrew). Concretely, the 4th Sunday
    before Christmas Day. Always falls between Nov 27 and Dec 3."""
    christmas = date(year, 12, 25)
    # Christmas weekday: Mon=0..Sun=6. Sundays before Christmas:
    # christmas - (weekday + 1) gives the Sunday immediately before Christmas
    # IF Christmas is not itself a Sunday; treat Sunday as the prior.
    cw = christmas.weekday()  # Sun=6
    days_back_to_sunday = (cw + 1) % 7 if cw != 6 else 7
    sunday_before_christmas = christmas - timedelta(days=days_back_to_sunday)
    return sunday_before_christmas - timedelta(weeks=3)


def compute_default_window(slug: str, year: int) -> tuple[date, date]:
    """Return (start, end) for the given track in the given liturgical year.
    For Advent the `year` is the calendar year of Christmas. For Lent the
    `year` is the calendar year of Easter. For Hallowtide the `year` is the
    calendar year of All Hallows' Eve."""
    if slug == "hallowtide":
        # Oct 31 (All Hallows' Eve) → Nov 8 (octave-closing of All Souls).
        return date(year, 10, 31), date(year, 11, 8)
    if slug == "advent":
        return _first_sunday_of_advent(year), date(year, 12, 24)
    if slug == "lent":
        return _ash_wednesday(year), _holy_saturday(year)
    raise ValueError(f"unknown challenge slug: {slug}")


def _next_window_for_today(slug: str, today: date) -> tuple[date, date, int]:
    """Returns (start, end, year) for the next occurrence of the track that
    is either active right now or will be active in the future."""
    # Try this year first.
    for year_offset in (0, 1):
        target_year = today.year + year_offset
        start, end = compute_default_window(slug, target_year)
        if today <= end:
            return start, end, target_year
    # Fallback (shouldn't hit).
    return *compute_default_window(slug, today.year + 1), today.year + 1


# ---------------------------------------------------------------------------
# Seeded challenge templates (drafts created at startup if missing)
# ---------------------------------------------------------------------------


SEED_CHALLENGES: list[Dict[str, Any]] = [
    {
        "slug": "hallowtide",
        "name": "Hallowtide",
        "subtitle": "All Hallows' Eve through the Octave of All Souls",
        "season": "hallowtide",
        "color": "#a47148",
        "icon": "flame-outline",
        "patron_saint": "All the Holy Souls in Purgatory",
        "blurb": (
            "Nine days of remembrance and prayer for the souls of the faithful "
            "departed — anchored by All Saints (Nov 1) and All Souls (Nov 2), "
            "rooted in the Catholic conviction that love is stronger than death."
        ),
        "opening_prayer": (
            "Eternal rest grant unto them, O Lord, and let perpetual light shine "
            "upon them. As we begin these days of remembrance, draw our hearts "
            "to the great cloud of witnesses who pray with us, and stir us to "
            "almsgiving and mercy for those who can no longer ask for themselves. "
            "Through Christ our Lord. Amen."
        ),
        "closing_prayer": (
            "Most loving Father, on this final day of Hallowtide we entrust to "
            "your mercy the souls of all the faithful departed, especially "
            "those we have remembered by name. May the prayers, fasts, and acts "
            "of love we have offered hasten their entrance into the joy of your "
            "presence. Through Christ our Lord. Amen."
        ),
        "preparation_content": {
            "title": "Bake Soul Cakes — a Catholic tradition for Hallowtide",
            "intro": (
                "Before Halloween became commercialized, Catholic families in "
                "England, Ireland, and beyond baked small spiced biscuits called "
                "\"soul cakes\" and handed them out on All Hallows' Eve and All "
                "Souls' Day. Every cake given away earned a promise: the receiver "
                "would pray for the soul of a loved one who had died. The "
                "tradition is gentle, generous, and quietly evangelizing — a "
                "perfect way to invite neighbors into the season."
            ),
            "recipe": {
                "yield": "About 18 small cakes",
                "ingredients": [
                    "2¾ cups (340g) all-purpose flour",
                    "½ cup (100g) granulated sugar",
                    "1 tsp ground cinnamon",
                    "½ tsp ground nutmeg",
                    "½ tsp ground allspice",
                    "¼ tsp salt",
                    "¾ cup (170g) cold unsalted butter, cubed",
                    "⅓ cup (50g) currants or raisins",
                    "2 egg yolks",
                    "2 Tbsp milk (or more, as needed)",
                    "1 tsp pure vanilla extract",
                ],
                "steps": [
                    "Preheat oven to 350°F (175°C). Line a baking sheet with parchment.",
                    "Whisk together flour, sugar, cinnamon, nutmeg, allspice, and salt.",
                    "Cut in the cold butter with a pastry cutter or two forks until the mixture looks like coarse crumbs.",
                    "Stir in currants. Add the yolks, milk, and vanilla; mix until a soft dough forms (add milk a teaspoon at a time if needed).",
                    "Turn out, roll to ½ inch thick, and cut 2-inch rounds. Place on the sheet and score a small cross on each cake with the back of a knife — the traditional sign that this cake is offered for the dead.",
                    "Bake 18–22 minutes until pale gold. Cool completely.",
                    "When you give one away, say simply: \"A soul cake for a prayer for [name]'s soul.\" That's the whole tradition.",
                ],
            },
            "encouragement": (
                "Bake a batch in late October. Bring them to neighbors, classmates, "
                "or a parish gathering. Keep a small notebook of the names you've "
                "promised to pray for — and offer them during your Hallowtide "
                "rosary."
            ),
        },
        "expected_day_count_hint": 9,
        "ai_generation_notes": (
            "Days 1–2 anchor on All Saints (Nov 1) and All Souls (Nov 2). The "
            "remaining seven days walk through the Communion of Saints, "
            "purgatory, indulgences for the dead, prayer for ancestors, and "
            "the four last things. Each day should suggest 2–4 small organic "
            "practices — never overwhelming."
        ),
    },
    {
        "slug": "advent",
        "name": "Advent",
        "subtitle": "Watching for the Coming of the King",
        "season": "advent",
        "color": "#5f3fb1",  # liturgical violet
        "icon": "moon-outline",
        "patron_saint": "Our Lady of the Annunciation",
        "blurb": (
            "Four weeks of holy preparation for Christmas — keeping vigil with "
            "Mary, John the Baptist, and the prophets as we await the dawn of "
            "the Word made flesh."
        ),
        "opening_prayer": (
            "Stir up your power, O Lord, and come! As we begin these weeks of "
            "watching, place upon our hearts the longing of Israel, the silence "
            "of Mary, and the boldness of the Baptist. Let every act of prayer, "
            "fasting, and charity become a small lamp held up in the darkness, "
            "ready for the coming of your Son. Amen."
        ),
        "closing_prayer": (
            "On this last night of Advent, O God, we have kept watch — and the "
            "King is near. Receive the desires of these weeks: the prayers "
            "whispered in cold mornings, the meals fasted, the alms quietly "
            "given. Tonight, by the manger, may we kneel with the shepherds "
            "and hear at last the song of the angels. Amen."
        ),
        "preparation_content": None,
        "expected_day_count_hint": None,  # computed from window
        "ai_generation_notes": (
            "Honor the four Advent themes (Hope, Peace, Joy, Love) week by "
            "week. Featured patrons include St. Andrew (Nov 30), St. Nicholas "
            "(Dec 6), the Immaculate Conception (Dec 8), Our Lady of "
            "Guadalupe (Dec 12), St. Lucy (Dec 13), St. John of the Cross "
            "(Dec 14). The O Antiphons run Dec 17–23."
        ),
    },
    {
        "slug": "lent",
        "name": "Lent",
        "subtitle": "Forty days in the desert with Christ",
        "season": "lent",
        "color": "#7a2e2e",  # liturgical violet/oxblood
        "icon": "leaf-outline",
        "patron_saint": "Our Lady of Sorrows",
        "blurb": (
            "From Ash Wednesday to Holy Saturday — the Church's annual journey "
            "of prayer, fasting, and almsgiving, walking with Christ from the "
            "wilderness to the empty tomb."
        ),
        "opening_prayer": (
            "Lord Jesus, who fasted forty days in the desert and conquered the "
            "Tempter not with power but with the Word, lead us into this "
            "wilderness with you. Strip away what is not yours in us. Increase "
            "our hunger for the Bread of Life and our love for the poor in whom "
            "you wait for us. Amen."
        ),
        "closing_prayer": (
            "On this Holy Saturday, O Christ, you lie silent in the tomb — and "
            "yet you descend in glory to free the captives. We have walked these "
            "forty days; tonight we keep vigil. By the prayers, fasts, and alms "
            "of this Lent, prepare our hearts for the Easter alleluia. Amen."
        ),
        "preparation_content": None,
        "expected_day_count_hint": None,
        "ai_generation_notes": (
            "Lent has three pillars: prayer, fasting, almsgiving. Honor the "
            "Sundays as 'little Easters' with a lighter rule. Feature the "
            "Stations of the Cross weekly. Anchor patrons include "
            "St. Joseph (Mar 19), the Annunciation (Mar 25), and the saints "
            "of the Passion (St. Veronica, St. Dismas the Good Thief, etc.). "
            "Holy Week (last 7 days) intensifies daily practices."
        ),
    },
]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class PrayerItemModel(BaseModel):
    item_id: Optional[str] = None
    kind: str = Field(..., min_length=1, max_length=40)
    title: str = Field(..., min_length=2, max_length=120)
    detail: Optional[str] = Field(None, max_length=600)

    @field_validator("kind")
    @classmethod
    def _kind_ok(cls, v: str) -> str:  # noqa: D401
        v = (v or "").strip().lower()
        if v not in ALLOWED_ITEM_KINDS:
            # Don't hard-fail — accept any kind but normalize.
            return v or "prayer"
        return v


class ChallengePatchModel(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    subtitle: Optional[str] = Field(None, max_length=200)
    blurb: Optional[str] = Field(None, max_length=2000)
    patron_saint: Optional[str] = Field(None, max_length=200)
    opening_prayer: Optional[str] = Field(None, max_length=4000)
    closing_prayer: Optional[str] = Field(None, max_length=4000)
    preparation_content: Optional[Dict[str, Any]] = None
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|published|archived)$")


class DayPatchModel(BaseModel):
    title: Optional[str] = Field(None, max_length=160)
    theme: Optional[str] = Field(None, max_length=200)
    patron_saint: Optional[str] = Field(None, max_length=200)
    patron_blurb: Optional[str] = Field(None, max_length=2000)
    reflection: Optional[str] = Field(None, max_length=4000)
    prayer_items: Optional[List[PrayerItemModel]] = None
    status: Optional[str] = Field(None, pattern="^(draft|published)$")


class CheckinModel(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    items_done: List[str] = Field(default_factory=list)
    reflection: Optional[str] = Field(None, max_length=4000)
    completed: bool = True


class GenerateDaysModel(BaseModel):
    overwrite: bool = False
    days: Optional[List[str]] = None  # specific YYYY-MM-DD entries; default = all


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        return dt.replace(tzinfo=dt.tzinfo or timezone.utc).isoformat()
    if isinstance(dt, date):
        return dt.isoformat()
    return None


def _parse_date(v: str) -> date:
    return datetime.strptime(v, "%Y-%m-%d").date()


def _public_challenge(doc: Dict[str, Any], include_prep: bool = True) -> Dict[str, Any]:
    # total_days is the calendar window length (end-start+1) — NOT the number
    # of day_doc rows in the DB. published_days is how many of those have
    # actually been written + marked status=published.
    start = doc.get("start_date")
    end = doc.get("end_date")
    window_days = 0
    if isinstance(start, datetime) and isinstance(end, datetime):
        window_days = (end.date() - start.date()).days + 1
    return {
        "challenge_id": doc.get("challenge_id"),
        "slug": doc.get("slug"),
        "name": doc.get("name"),
        "subtitle": doc.get("subtitle"),
        "season": doc.get("season"),
        "color": doc.get("color"),
        "icon": doc.get("icon"),
        "patron_saint": doc.get("patron_saint"),
        "blurb": doc.get("blurb"),
        "opening_prayer": doc.get("opening_prayer"),
        "closing_prayer": doc.get("closing_prayer"),
        "preparation_content": doc.get("preparation_content") if include_prep else None,
        "start_date": _iso(doc.get("start_date")),
        "end_date": _iso(doc.get("end_date")),
        "status": doc.get("status", "draft"),
        "total_days": window_days or (doc.get("total_days") or 0),
        "published_days": doc.get("published_days") or 0,
    }


def _admin_challenge(doc: Dict[str, Any]) -> Dict[str, Any]:
    base = _public_challenge(doc)
    base.update({
        "ai_generation_notes": doc.get("ai_generation_notes"),
        "created_at": _iso(doc.get("created_at")),
        "updated_at": _iso(doc.get("updated_at")),
    })
    return base


def _public_day(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "day_id": doc["day_id"],
        "challenge_id": doc["challenge_id"],
        "day_index": doc.get("day_index"),
        "date": _iso(doc.get("date")),
        "title": doc.get("title"),
        "theme": doc.get("theme"),
        "patron_saint": doc.get("patron_saint"),
        "patron_blurb": doc.get("patron_blurb"),
        "reflection": doc.get("reflection"),
        "prayer_items": doc.get("prayer_items") or [],
        "status": doc.get("status", "draft"),
    }


async def _ensure_admin(user) -> None:
    if not user or not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admins only")


_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _extract_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    m = _JSON_BLOCK.search(text)
    if m:
        text = m.group(1)
    # Find the first { and last }.
    i = text.find("{")
    j = text.rfind("}")
    if i == -1 or j == -1 or j <= i:
        raise ValueError("no JSON object found")
    raw = text[i : j + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Claude occasionally emits trailing commas or unescaped quotes inside
        # a string. Try a couple of forgiving repairs before bailing.
        cleaned = re.sub(r",\s*([}\]])", r"\1", raw)  # strip trailing commas
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        # Last resort: drop any C-style /* ... */ comments and bare control chars.
        cleaned2 = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.S)
        cleaned2 = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", cleaned2)
        return json.loads(cleaned2)


# ---------------------------------------------------------------------------
# Seed routine
# ---------------------------------------------------------------------------


async def _seed_challenges_if_missing(db: AsyncIOMotorDatabase) -> int:
    col = db["liturgical_challenges"]
    today = datetime.now(timezone.utc).date()
    inserted = 0
    for tpl in SEED_CHALLENGES:
        slug = tpl["slug"]
        if await col.find_one({"slug": slug}):
            continue
        # Pick a sensible next window for the slug.
        if slug == "lent":
            # Use the easter-year that hasn't yet passed.
            target_year = today.year if today < _ash_wednesday(today.year) else today.year + 1
            start, end = compute_default_window(slug, target_year)
        elif slug == "advent":
            target_year = today.year if today < _first_sunday_of_advent(today.year) else today.year + 1
            start, end = compute_default_window(slug, target_year)
        else:  # hallowtide
            target_year = today.year if today <= date(today.year, 11, 8) else today.year + 1
            start, end = compute_default_window(slug, target_year)
        now = datetime.now(timezone.utc)
        await col.insert_one({
            "challenge_id": f"chl_{uuid.uuid4().hex[:10]}",
            **{k: v for k, v in tpl.items() if k != "expected_day_count_hint"},
            "start_date": datetime.combine(start, time.min, tzinfo=timezone.utc),
            "end_date": datetime.combine(end, time.min, tzinfo=timezone.utc),
            "status": "draft",
            "total_days": (end - start).days + 1,
            "published_days": 0,
            "created_at": now,
            "updated_at": now,
        })
        inserted += 1
    return inserted


# ---------------------------------------------------------------------------
# AI day generation (Claude)
# ---------------------------------------------------------------------------


_SYSTEM_PROMPT_BASE = (
    "You are a reverent Catholic spiritual director helping build a daily "
    "liturgical-challenge plan inside the Sanctus app. You write in the voice "
    "of the Church's living tradition — drawing on the Catechism, scripture, "
    "the Doctors, and the lives of the saints. You never invent doctrine, "
    "never speculate beyond Magisterial teaching, and you favor humility over "
    "cleverness.\n\n"
    "For each day requested, output ONE JSON object with these fields exactly:\n"
    "{\n"
    "  \"title\": \"a short reverent line, max 60 chars\",\n"
    "  \"theme\": \"a single phrase describing today's focus\",\n"
    "  \"patron_saint\": \"the Saint/Blessed/Venerable assigned for this day, with honorific\",\n"
    "  \"patron_blurb\": \"2–3 sentences on why this patron, what they witness to today\",\n"
    "  \"reflection\": \"a 90–140 word reflection rooted in scripture or tradition\",\n"
    "  \"prayer_items\": [\n"
    "    { \"kind\": \"rosary|prayer|scripture|reflection|mass_reading|almsgiving|fasting|act_of_charity|examen|spiritual_reading|litany|act_of_mercy|patron_invocation|service\",\n"
    "      \"title\": \"a short call to action, max 70 chars\",\n"
    "      \"detail\": \"one or two sentences with concrete instruction\" }\n"
    "  ]\n"
    "}\n\n"
    "Return between 2 and 4 prayer_items per day — pick what feels organic for "
    "the patron and theme, never a fixed checklist. Do NOT wrap in markdown. "
    "Do NOT add commentary. Output ONLY the JSON object."
)


def _build_day_prompt(
    challenge: Dict[str, Any],
    day_index: int,
    total_days: int,
    day_date: date,
) -> str:
    return (
        f"Challenge: {challenge['name']} — {challenge.get('subtitle') or ''}\n"
        f"Season notes: {challenge.get('ai_generation_notes') or ''}\n"
        f"Challenge patron: {challenge.get('patron_saint')}\n\n"
        f"Day {day_index} of {total_days} — {day_date.isoformat()} "
        f"({day_date.strftime('%A, %B %-d')})\n\n"
        "Build today's content. Honor any saint whose feast day falls on this "
        "date (use the Roman Calendar). If multiple saints are commemorated, "
        "pick the one whose witness best fits the season."
    )


async def _generate_day_with_claude(
    emergent_llm_key: str,
    challenge: Dict[str, Any],
    day_index: int,
    total_days: int,
    day_date: date,
) -> Dict[str, Any]:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    seed = hashlib.sha1(
        f"{challenge['slug']}|{day_date.isoformat()}|{day_index}".encode()
    ).hexdigest()[:12]
    session_id = f"challenges-day-{seed}"
    chat = LlmChat(
        api_key=emergent_llm_key,
        session_id=session_id,
        system_message=_SYSTEM_PROMPT_BASE,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    user_text = _build_day_prompt(challenge, day_index, total_days, day_date)
    response = await chat.send_message(UserMessage(text=user_text))
    data = _extract_json(response or "")
    # Normalize the prayer items.
    items_out = []
    for it in (data.get("prayer_items") or [])[:6]:
        try:
            m = PrayerItemModel.model_validate(it)
            items_out.append(m.model_dump(exclude_none=True))
        except Exception:  # noqa: BLE001
            continue
    return {
        "title": (data.get("title") or "").strip()[:160] or None,
        "theme": (data.get("theme") or "").strip()[:200] or None,
        "patron_saint": (data.get("patron_saint") or "").strip()[:200] or None,
        "patron_blurb": (data.get("patron_blurb") or "").strip()[:2000] or None,
        "reflection": (data.get("reflection") or "").strip()[:4000] or None,
        "prayer_items": items_out,
    }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def build_router(
    db: AsyncIOMotorDatabase,
    get_current_user: Callable,
    emergent_llm_key: str,
) -> APIRouter:
    router = APIRouter(prefix="/challenges", tags=["challenges"])

    challenges = db["liturgical_challenges"]
    days_col = db["challenge_days"]
    enrollments = db["challenge_enrollments"]
    checkins = db["challenge_checkins"]

    async def _get_challenge_or_404(slug: str, *, allow_drafts: bool = False) -> Dict[str, Any]:
        doc = await challenges.find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="challenge not found")
        if not allow_drafts and doc.get("status") != "published":
            raise HTTPException(status_code=404, detail="challenge not yet published")
        return doc

    async def _recount(challenge_id: str) -> tuple[int, int]:
        total = await days_col.count_documents({"challenge_id": challenge_id})
        published = await days_col.count_documents({"challenge_id": challenge_id, "status": "published"})
        await challenges.update_one(
            {"challenge_id": challenge_id},
            {"$set": {"total_days": total, "published_days": published, "updated_at": datetime.now(timezone.utc)}},
        )
        return total, published

    # ----------------------------- Public -----------------------------------

    @router.get("")
    async def list_challenges(user=Depends(get_current_user)):
        """List all PUBLISHED challenges (plus, for admins, drafts) along with
        the caller's enrollment + progress for each."""
        await _seed_challenges_if_missing(db)
        is_admin = bool(getattr(user, "is_admin", False))
        q: Dict[str, Any] = {} if is_admin else {"status": "published"}
        cursor = challenges.find(q).sort([("start_date", 1)])
        out = []
        async for doc in cursor:
            base = _public_challenge(doc)
            base["enrolled"] = False
            base["completed_days"] = 0
            base["streak"] = 0
            enr = await enrollments.find_one({"user_id": user.user_id, "challenge_id": doc["challenge_id"]})
            if enr:
                base["enrolled"] = True
                base["completed_days"] = enr.get("total_days_completed", 0)
                base["streak"] = enr.get("current_streak", 0)
            out.append(base)
        return {"items": out}

    @router.get("/{slug}")
    async def get_challenge(slug: str, user=Depends(get_current_user)):
        is_admin = bool(getattr(user, "is_admin", False))
        doc = await _get_challenge_or_404(slug, allow_drafts=is_admin)
        base = _public_challenge(doc)
        # Attach days (published only, unless admin).
        day_q = {"challenge_id": doc["challenge_id"]}
        if not is_admin:
            day_q["status"] = "published"
        day_docs = [d async for d in days_col.find(day_q).sort([("day_index", 1)])]
        base["days"] = [_public_day(d) for d in day_docs]
        # Attach enrollment state.
        enr = await enrollments.find_one({"user_id": user.user_id, "challenge_id": doc["challenge_id"]})
        base["enrolled"] = bool(enr)
        if enr:
            base["enrollment"] = {
                "joined_at": _iso(enr.get("joined_at")),
                "current_streak": enr.get("current_streak", 0),
                "total_days_completed": enr.get("total_days_completed", 0),
                "last_checkin_date": _iso(enr.get("last_checkin_date")),
            }
        # Today's check-in (if any).
        today = datetime.now(timezone.utc).date()
        chk = await checkins.find_one({
            "user_id": user.user_id,
            "challenge_id": doc["challenge_id"],
            "date_str": today.isoformat(),
        })
        base["today_checkin"] = (
            {
                "items_done": chk.get("items_done", []),
                "reflection": chk.get("reflection"),
                "completed": chk.get("completed", False),
            }
            if chk
            else None
        )
        return base

    @router.post("/{slug}/enroll")
    async def enroll(slug: str, user=Depends(get_current_user)):
        doc = await _get_challenge_or_404(slug)
        existing = await enrollments.find_one({"user_id": user.user_id, "challenge_id": doc["challenge_id"]})
        if existing:
            return {"ok": True, "already": True}
        now = datetime.now(timezone.utc)
        await enrollments.insert_one({
            "enrollment_id": f"enr_{uuid.uuid4().hex[:10]}",
            "user_id": user.user_id,
            "challenge_id": doc["challenge_id"],
            "challenge_slug": slug,
            "joined_at": now,
            "current_streak": 0,
            "longest_streak": 0,
            "total_days_completed": 0,
            "last_checkin_date": None,
        })
        return {"ok": True, "already": False}

    @router.delete("/{slug}/enroll")
    async def unenroll(slug: str, user=Depends(get_current_user)):
        doc = await _get_challenge_or_404(slug, allow_drafts=True)
        r = await enrollments.delete_one({"user_id": user.user_id, "challenge_id": doc["challenge_id"]})
        return {"ok": True, "removed": r.deleted_count}

    @router.post("/{slug}/checkin")
    async def checkin(slug: str, payload: CheckinModel, user=Depends(get_current_user)):
        doc = await _get_challenge_or_404(slug)
        enr = await enrollments.find_one({"user_id": user.user_id, "challenge_id": doc["challenge_id"]})
        if not enr:
            raise HTTPException(status_code=400, detail="enroll first")
        try:
            day = _parse_date(payload.date)
        except Exception:
            raise HTTPException(status_code=400, detail="bad date")
        now = datetime.now(timezone.utc)
        date_str = day.isoformat()
        existing = await checkins.find_one({
            "user_id": user.user_id,
            "challenge_id": doc["challenge_id"],
            "date_str": date_str,
        })
        body = {
            "items_done": [str(x)[:80] for x in (payload.items_done or [])[:30]],
            "reflection": (payload.reflection or "").strip()[:4000] or None,
            "completed": bool(payload.completed),
            "updated_at": now,
        }
        if existing:
            await checkins.update_one({"_id": existing["_id"]}, {"$set": body})
        else:
            await checkins.insert_one({
                "checkin_id": f"chk_{uuid.uuid4().hex[:10]}",
                "user_id": user.user_id,
                "challenge_id": doc["challenge_id"],
                "challenge_slug": slug,
                "date": datetime.combine(day, time.min, tzinfo=timezone.utc),
                "date_str": date_str,
                "created_at": now,
                **body,
            })
        # Recompute streak + totals.
        completed_count = await checkins.count_documents({
            "user_id": user.user_id,
            "challenge_id": doc["challenge_id"],
            "completed": True,
        })
        # Streak: walk back from today across consecutive days with completed=True.
        streak = 0
        cursor_day = day
        while True:
            d_str = cursor_day.isoformat()
            c = await checkins.find_one({
                "user_id": user.user_id,
                "challenge_id": doc["challenge_id"],
                "date_str": d_str,
                "completed": True,
            })
            if not c:
                break
            streak += 1
            cursor_day = cursor_day - timedelta(days=1)
        await enrollments.update_one(
            {"_id": enr["_id"]},
            {"$set": {
                "current_streak": streak,
                "longest_streak": max(streak, enr.get("longest_streak", 0)),
                "total_days_completed": completed_count,
                "last_checkin_date": datetime.combine(day, time.min, tzinfo=timezone.utc),
                "updated_at": now,
            }},
        )
        return {
            "ok": True,
            "current_streak": streak,
            "total_days_completed": completed_count,
        }

    @router.get("/{slug}/my-progress")
    async def my_progress(slug: str, user=Depends(get_current_user)):
        doc = await _get_challenge_or_404(slug, allow_drafts=True)
        enr = await enrollments.find_one({"user_id": user.user_id, "challenge_id": doc["challenge_id"]})
        cks = [c async for c in checkins.find(
            {"user_id": user.user_id, "challenge_id": doc["challenge_id"]},
            {"_id": 0, "date_str": 1, "items_done": 1, "completed": 1, "reflection": 1},
        ).sort([("date_str", 1)])]
        return {
            "enrolled": bool(enr),
            "current_streak": enr.get("current_streak", 0) if enr else 0,
            "longest_streak": enr.get("longest_streak", 0) if enr else 0,
            "total_days_completed": enr.get("total_days_completed", 0) if enr else 0,
            "checkins": cks,
        }

    @router.get("/{slug}/companions")
    async def companions(slug: str, limit: int = 20, user=Depends(get_current_user)):
        """Friends of the current user who are enrolled in this challenge —
        powers the 'walking with you' avatar stack on the detail screen."""
        doc = await _get_challenge_or_404(slug, allow_drafts=True)
        # 1. accepted friendships → friend_ids
        cur = db["community_friendships"].find(
            {"members": user.user_id, "status": "accepted"},
            {"_id": 0, "members": 1},
        )
        friend_ids: list[str] = []
        async for f in cur:
            for m in (f.get("members") or []):
                if m != user.user_id:
                    friend_ids.append(m)
        if not friend_ids:
            return {"items": [], "total": 0}
        # 2. enrolled friends
        cur = enrollments.find(
            {"challenge_id": doc["challenge_id"], "user_id": {"$in": friend_ids}},
            {"_id": 0},
        ).sort([("current_streak", -1), ("joined_at", 1)])
        rows: list[Dict[str, Any]] = await cur.to_list(length=max(1, min(limit, 50)))
        total = await enrollments.count_documents(
            {"challenge_id": doc["challenge_id"], "user_id": {"$in": friend_ids}},
        )
        if not rows:
            return {"items": [], "total": 0}
        # 3. profile lookup via users collection
        user_ids = [r["user_id"] for r in rows]
        u_cur = db["users"].find(
            {"user_id": {"$in": user_ids}},
            {"_id": 0, "user_id": 1, "name": 1, "picture": 1},
        )
        u_by_id: Dict[str, Dict[str, Any]] = {}
        async for u in u_cur:
            u_by_id[u["user_id"]] = u
        items: list[Dict[str, Any]] = []
        for r in rows:
            u = u_by_id.get(r["user_id"]) or {}
            items.append({
                "user_id": r["user_id"],
                "name": u.get("name"),
                "picture": u.get("picture"),
                "current_streak": r.get("current_streak", 0),
                "total_days_completed": r.get("total_days_completed", 0),
            })
        return {"items": items, "total": total}

    # ----------------------------- Admin ------------------------------------

    @router.get("/admin/all")
    async def admin_list(user=Depends(get_current_user)):
        await _ensure_admin(user)
        await _seed_challenges_if_missing(db)
        cursor = challenges.find({}).sort([("start_date", 1)])
        return {"items": [_admin_challenge(d) async for d in cursor]}

    @router.patch("/admin/{slug}")
    async def admin_patch_challenge(slug: str, payload: ChallengePatchModel, user=Depends(get_current_user)):
        await _ensure_admin(user)
        doc = await challenges.find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="not found")
        updates: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        for f in (
            "name", "subtitle", "blurb", "patron_saint",
            "opening_prayer", "closing_prayer", "preparation_content", "status",
        ):
            v = getattr(payload, f)
            if v is not None:
                updates[f] = v
        if payload.start_date:
            updates["start_date"] = datetime.combine(_parse_date(payload.start_date), time.min, tzinfo=timezone.utc)
        if payload.end_date:
            updates["end_date"] = datetime.combine(_parse_date(payload.end_date), time.min, tzinfo=timezone.utc)
        await challenges.update_one({"_id": doc["_id"]}, {"$set": updates})
        await _recount(doc["challenge_id"])
        return _admin_challenge(await challenges.find_one({"_id": doc["_id"]}))  # type: ignore[arg-type]

    @router.get("/admin/{slug}/days")
    async def admin_days(slug: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        doc = await challenges.find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="not found")
        cursor = days_col.find({"challenge_id": doc["challenge_id"]}).sort([("day_index", 1)])
        return {"items": [_public_day(d) async for d in cursor]}

    @router.patch("/admin/days/{day_id}")
    async def admin_patch_day(day_id: str, payload: DayPatchModel, user=Depends(get_current_user)):
        await _ensure_admin(user)
        doc = await days_col.find_one({"day_id": day_id})
        if not doc:
            raise HTTPException(status_code=404, detail="day not found")
        updates: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        for f in ("title", "theme", "patron_saint", "patron_blurb", "reflection", "status"):
            v = getattr(payload, f)
            if v is not None:
                updates[f] = v
        if payload.prayer_items is not None:
            updates["prayer_items"] = [m.model_dump(exclude_none=True) for m in payload.prayer_items]
        await days_col.update_one({"_id": doc["_id"]}, {"$set": updates})
        await _recount(doc["challenge_id"])
        updated = await days_col.find_one({"_id": doc["_id"]})
        return _public_day(updated)  # type: ignore[arg-type]

    @router.post("/admin/{slug}/publish")
    async def admin_publish_challenge(slug: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        doc = await challenges.find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="not found")
        # Publish all days that are still draft along with the challenge itself.
        await days_col.update_many({"challenge_id": doc["challenge_id"], "status": "draft"}, {"$set": {"status": "published"}})
        await challenges.update_one({"_id": doc["_id"]}, {"$set": {"status": "published", "updated_at": datetime.now(timezone.utc)}})
        await _recount(doc["challenge_id"])
        updated = await challenges.find_one({"_id": doc["_id"]})
        return _admin_challenge(updated)  # type: ignore[arg-type]

    @router.post("/admin/{slug}/unpublish")
    async def admin_unpublish_challenge(slug: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        doc = await challenges.find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="not found")
        await challenges.update_one({"_id": doc["_id"]}, {"$set": {"status": "draft", "updated_at": datetime.now(timezone.utc)}})
        await _recount(doc["challenge_id"])
        updated = await challenges.find_one({"_id": doc["_id"]})
        return _admin_challenge(updated)  # type: ignore[arg-type]

    @router.post("/admin/{slug}/generate-days")
    async def admin_generate_days(slug: str, payload: GenerateDaysModel, user=Depends(get_current_user)):
        await _ensure_admin(user)
        if not emergent_llm_key:
            raise HTTPException(status_code=503, detail="LLM unavailable")
        doc = await challenges.find_one({"slug": slug})
        if not doc:
            raise HTTPException(status_code=404, detail="not found")

        start = doc["start_date"]
        end = doc["end_date"]
        if isinstance(start, datetime):
            start = start.date()
        if isinstance(end, datetime):
            end = end.date()
        total = (end - start).days + 1

        # Build the set of target dates.
        if payload.days:
            target_dates = sorted({_parse_date(d) for d in payload.days})
        else:
            target_dates = [start + timedelta(days=i) for i in range(total)]

        results: list[Dict[str, Any]] = []
        failures: list[Dict[str, Any]] = []

        # Process in parallel with a small concurrency cap to keep AI calls
        # snappy while respecting rate limits. Hallowtide (~9 days) finishes
        # in ~15s instead of ~2min serial; Lent stays under ~100s.
        sem = asyncio.Semaphore(5)
        existing_docs = await days_col.find(
            {"challenge_id": doc["challenge_id"]}
        ).to_list(length=None)
        existing_by_idx = {e["day_index"]: e for e in existing_docs}

        async def _gen_one(d):
            day_index = (d - start).days + 1
            if day_index < 1 or day_index > total:
                return None
            existing = existing_by_idx.get(day_index)
            if existing and not payload.overwrite:
                return ("skip", {
                    "day_index": day_index,
                    "date": d.isoformat(),
                    "skipped": True,
                    "day_id": existing["day_id"],
                })
            async with sem:
                ai = None
                last_err: Exception | None = None
                # One automatic retry on AI parse/error to smooth out Claude's
                # occasional malformed JSON — saves the admin from having to
                # hit "Generate missing" twice.
                for attempt in range(2):
                    try:
                        ai = await _generate_day_with_claude(emergent_llm_key, doc, day_index, total, d)
                        break
                    except Exception as e:  # noqa: BLE001
                        last_err = e
                        logger.warning(
                            "challenge day gen failed (%s day %d attempt %d): %s",
                            slug, day_index, attempt + 1, e,
                        )
                        await asyncio.sleep(0.5)
                if ai is None:
                    return ("fail", {
                        "day_index": day_index,
                        "date": d.isoformat(),
                        "error": str(last_err)[:200] if last_err else "unknown",
                    })
            now = datetime.now(timezone.utc)
            day_doc = {
                "day_id": existing["day_id"] if existing else f"chd_{uuid.uuid4().hex[:10]}",
                "challenge_id": doc["challenge_id"],
                "challenge_slug": slug,
                "day_index": day_index,
                "date": datetime.combine(d, time.min, tzinfo=timezone.utc),
                "date_str": d.isoformat(),
                **ai,
                "status": "draft",
                "ai_source": "claude-sonnet-4-5",
                "updated_at": now,
            }
            if existing:
                day_doc["created_at"] = existing.get("created_at", now)
                await days_col.update_one({"_id": existing["_id"]}, {"$set": day_doc})
            else:
                day_doc["created_at"] = now
                await days_col.insert_one(day_doc)
            return ("ok", {
                "day_index": day_index,
                "date": d.isoformat(),
                "day_id": day_doc["day_id"],
                "skipped": False,
            })

        outs = await asyncio.gather(*[_gen_one(d) for d in target_dates], return_exceptions=False)
        for o in outs:
            if not o:
                continue
            kind, payload_ = o
            if kind == "fail":
                failures.append(payload_)
            else:
                results.append(payload_)
        results.sort(key=lambda r: r["day_index"])

        await _recount(doc["challenge_id"])
        return {"ok": True, "results": results, "failures": failures}

    return router


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db["liturgical_challenges"].create_index("challenge_id", unique=True)
    await db["liturgical_challenges"].create_index("slug", unique=True)
    await db["liturgical_challenges"].create_index([("status", 1), ("start_date", 1)])

    await db["challenge_days"].create_index("day_id", unique=True)
    await db["challenge_days"].create_index([("challenge_id", 1), ("day_index", 1)], unique=True)
    await db["challenge_days"].create_index([("challenge_id", 1), ("status", 1)])

    await db["challenge_enrollments"].create_index("enrollment_id", unique=True)
    await db["challenge_enrollments"].create_index([("user_id", 1), ("challenge_id", 1)], unique=True)

    await db["challenge_checkins"].create_index("checkin_id", unique=True)
    await db["challenge_checkins"].create_index(
        [("user_id", 1), ("challenge_id", 1), ("date_str", 1)], unique=True
    )
    await db["challenge_checkins"].create_index([("challenge_id", 1), ("date_str", -1)])

    try:
        n = await _seed_challenges_if_missing(db)
        if n:
            logger.info("challenges: seeded %d default tracks", n)
    except Exception as e:  # noqa: BLE001
        logger.warning("challenges seed skipped: %s", e)

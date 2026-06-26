"""Sanctus — Virtus: a guided study of the Catholic virtues.

Each virtue (and a few allied topics — Spiritual Warfare, Habits & Discipline,
Saints of Virtue) opens to subsections explaining what the virtue is, how it is
lived across the seasons of life (singleness, dating, marriage), how to overcome
the opposing vice, holy patrons of the virtue with a short prayer, and a set of
deeper *Resources* that are gated behind Sanctus Premium.

Content is AI-authored by Claude on first access and cached in MongoDB
(`virtue_content`), so it is fast and consistent. An admin may edit or
regenerate any virtue's content (founder review workflow).

Users may also start a personal *Virtue Plan*: pick one or more virtues and a
timeframe, and the AI proposes concrete goals — things to *do* and things to
*refrain from* — which the user checks off over the period (`virtue_plans`).

All endpoints are prefixed `/api/virtues`. Everything is free EXCEPT the
per-virtue Resources subsection, which requires Premium.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone, date as _date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from premium import is_premium_user, require_premium
from lang_ctx import get_lang, lang_instruction

logger = logging.getLogger("sanctus.virtues")

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)


def _extract_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    m = _JSON_BLOCK.search(text)
    if m:
        text = m.group(1)
    i = text.find("{")
    j = text.rfind("}")
    if i == -1 or j == -1 or j <= i:
        raise ValueError("no JSON object found")
    raw = text[i : j + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = re.sub(r",\s*([}\]])", r"\1", raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            cleaned2 = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.S)
            cleaned2 = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", cleaned2)
            return json.loads(cleaned2)


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------

VIRTUES: List[Dict[str, Any]] = [
    {
        "slug": "chastity", "name": "Chastity", "kind": "virtue",
        "icon": "flower-outline", "accent_color": "#8A4A6C",
        "tagline": "Purity of heart, body, and intention",
        "opposite_vice": "Lust",
    },
    {
        "slug": "charity", "name": "Charity", "kind": "virtue",
        "icon": "heart-outline", "accent_color": "#B23A48",
        "tagline": "Love of God above all and neighbor as self",
        "opposite_vice": "Greed & Indifference",
    },
    {
        "slug": "humility", "name": "Humility", "kind": "virtue",
        "icon": "leaf-outline", "accent_color": "#5B7553",
        "tagline": "Walking in the truth about God and self",
        "opposite_vice": "Pride",
    },
    {
        "slug": "patience", "name": "Patience", "kind": "virtue",
        "icon": "hourglass-outline", "accent_color": "#C99A4A",
        "tagline": "Steadfast endurance under trial",
        "opposite_vice": "Wrath",
    },
    {
        "slug": "temperance", "name": "Temperance", "kind": "virtue",
        "icon": "water-outline", "accent_color": "#3E7C8A",
        "tagline": "Moderation of pleasure and desire",
        "opposite_vice": "Gluttony",
    },
    {
        "slug": "fortitude", "name": "Fortitude", "kind": "virtue",
        "icon": "shield-outline", "accent_color": "#3E5C76",
        "tagline": "Courage to do good in the face of difficulty",
        "opposite_vice": "Cowardice & Sloth",
    },
    {
        "slug": "prudence", "name": "Prudence", "kind": "virtue",
        "icon": "compass-outline", "accent_color": "#5E6BA8",
        "tagline": "Right reason applied to action",
        "opposite_vice": "Rashness & Negligence",
    },
    {
        "slug": "justice", "name": "Justice", "kind": "virtue",
        "icon": "scale-outline", "accent_color": "#7A6A33",
        "tagline": "Giving God and neighbor their due",
        "opposite_vice": "Injustice",
    },
    {
        "slug": "hope", "name": "Hope", "kind": "virtue",
        "icon": "sunny-outline", "accent_color": "#3F8F6E",
        "tagline": "Trusting in God's promise of eternal life",
        "opposite_vice": "Despair & Presumption",
    },
    {
        "slug": "spiritual-warfare", "name": "Spiritual Warfare", "kind": "topic",
        "icon": "flame-outline", "accent_color": "#9C3B2E",
        "tagline": "Standing firm against temptation and the enemy",
        "opposite_vice": "Spiritual Sloth (Acedia)",
    },
    {
        "slug": "habits-discipline", "name": "Habits & Discipline", "kind": "topic",
        "icon": "barbell-outline", "accent_color": "#4A6C8A",
        "tagline": "Building a rule of life that forms the soul",
        "opposite_vice": "Sloth",
    },
    {
        "slug": "saints-of-virtue", "name": "Saints of Virtue", "kind": "saints",
        "icon": "people-outline", "accent_color": "#A8842C",
        "tagline": "Holy patrons and their prayers, virtue by virtue",
        "opposite_vice": None,
    },
]

VIRTUES_BY_SLUG: Dict[str, Dict[str, Any]] = {v["slug"]: v for v in VIRTUES}

# The eight virtues a Virtue Plan can be built from (saints-of-virtue is a
# reference topic, not a goal track).
PLAN_VIRTUE_SLUGS = [v["slug"] for v in VIRTUES if v["kind"] in ("virtue", "topic")]

CLAUDE_MODEL = "claude-sonnet-4-5-20250929"


def _is_admin(user: Any) -> bool:
    return bool(getattr(user, "is_admin", False))


# ---------------------------------------------------------------------------
# AI authoring
# ---------------------------------------------------------------------------

def _virtue_prompt(v: Dict[str, Any]) -> str:
    opp = v.get("opposite_vice") or "the opposing vice"
    return (
        f"Write a faithful Roman Catholic study of the virtue/topic of "
        f"\"{v['name']}\" ({v['tagline']}). Return STRICT JSON only, no prose "
        f"outside the JSON, with exactly these keys:\n"
        "{\n"
        '  "what_is": "180-260 words explaining what this virtue is in Catholic '
        'teaching, rooted in Scripture and the Catechism, warm and pastoral, plain prose",\n'
        '  "life_stages": {\n'
        '     "singleness": "120-180 words on living this virtue well in single life",\n'
        '     "dating": "120-180 words on living it in courtship/dating with chaste, honorable intent",\n'
        '     "marriage": "120-180 words on living it within marriage and family life"\n'
        "  },\n"
        f'  "overcoming_vice": "160-220 words of concrete, encouraging counsel for overcoming {opp}, '
        'the vice opposed to this virtue — practical steps, sacraments, prayer, accountability",\n'
        '  "saints": [ {"name":"St. N.", "years":"c.1500-1560", "why":"one sentence on why a patron of this virtue", '
        '"prayer":"a short 1-3 sentence prayer asking this saint\'s intercession"} ],  // 3 saints\n'
        '  "resources": [ {"title":"...", "kind":"book|prayer|devotion|practice", "author":"optional", '
        '"description":"one sentence on how it helps grow this virtue"} ]  // 4-6 resources\n'
        "}\n"
        "Stay strictly within Catholic doctrine. Do not invent Catechism paragraph "
        "numbers. Keep prose plain (no markdown, no headings, no bullet characters)."
        + lang_instruction()
    )


def _saints_prompt() -> str:
    names = ", ".join(
        v["name"] for v in VIRTUES if v["kind"] in ("virtue", "topic")
    )
    return (
        "Compile a faithful Roman Catholic reference of patron saints for each "
        f"of these virtues: {names}. Return STRICT JSON only with these keys:\n"
        "{\n"
        '  "intro": "60-110 words on how the saints model the virtues and why we ask their intercession",\n'
        '  "saints_by_virtue": [ {"virtue":"Chastity", "saints":[ '
        '{"name":"St. N.", "years":"c.1500-1560", "why":"one sentence why a model of this virtue", '
        '"prayer":"a short 1-3 sentence prayer for their intercession"} ] } ],  // one entry per virtue, 2-3 saints each\n'
        '  "resources": [ {"title":"...", "kind":"book|prayer|devotion|practice", "author":"optional", '
        '"description":"one sentence"} ]  // 4-6 resources on the saints/virtues\n'
        "}\n"
        "Use real, canonized (or beatified) saints appropriate to each virtue. "
        "Stay within Catholic doctrine. Plain prose, no markdown."
        + lang_instruction()
    )


async def _generate_content(emergent_llm_key: str, v: Dict[str, Any]) -> Dict[str, Any]:
    if not emergent_llm_key:
        raise HTTPException(status_code=503, detail="AI authoring unavailable")
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    system = (
        "You are a faithful Catholic catechist and spiritual director. You write "
        "warm, doctrinally sound, pastoral content and ALWAYS return valid JSON "
        "exactly as requested."
    )
    prompt = _saints_prompt() if v["kind"] == "saints" else _virtue_prompt(v)
    try:
        chat = LlmChat(
            api_key=emergent_llm_key,
            session_id=f"virtus-{v['slug']}",
            system_message=system,
        ).with_model("anthropic", CLAUDE_MODEL)
        response = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:  # pragma: no cover - network
        logger.exception("virtue content generation failed: %s", e)
        raise HTTPException(status_code=502, detail="Content generation failed; please retry.")

    try:
        data = _extract_json(response or "")
    except Exception as e:
        logger.exception("virtue JSON parse failed: %s", e)
        raise HTTPException(status_code=502, detail="Could not parse generated content; please retry.")

    now = datetime.now(timezone.utc)
    doc: Dict[str, Any] = {
        "slug": v["slug"],
        "kind": v["kind"],
        "lang": get_lang(),
        "resources": data.get("resources") or [],
        "generated_at": now.isoformat(),
        "edited": False,
        "edited_at": None,
    }
    if v["kind"] == "saints":
        doc["intro"] = (data.get("intro") or "").strip()
        doc["saints_by_virtue"] = data.get("saints_by_virtue") or []
    else:
        doc["what_is"] = (data.get("what_is") or "").strip()
        ls = data.get("life_stages") or {}
        doc["life_stages"] = {
            "singleness": (ls.get("singleness") or "").strip(),
            "dating": (ls.get("dating") or "").strip(),
            "marriage": (ls.get("marriage") or "").strip(),
        }
        doc["overcoming_vice"] = (data.get("overcoming_vice") or "").strip()
        doc["saints"] = data.get("saints") or []
    return doc


def _content_filter(slug: str) -> Dict[str, Any]:
    """Mongo filter for a virtue's cached content in the current language.
    English also matches legacy docs created before per-language caching."""
    lang = get_lang()
    if lang == "en":
        return {"slug": slug, "$or": [{"lang": "en"}, {"lang": {"$exists": False}}]}
    return {"slug": slug, "lang": lang}


async def _get_or_create_content(
    db: AsyncIOMotorDatabase, emergent_llm_key: str, slug: str
) -> Dict[str, Any]:
    v = VIRTUES_BY_SLUG.get(slug)
    if not v:
        raise HTTPException(status_code=404, detail="Virtue not found")
    existing = await db.virtue_content.find_one(_content_filter(slug), {"_id": 0})
    if existing:
        return existing
    doc = await _generate_content(emergent_llm_key, v)
    await db.virtue_content.update_one(
        {"slug": slug, "lang": get_lang()}, {"$set": doc}, upsert=True
    )
    return doc


def _meta(v: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "slug": v["slug"],
        "name": v["name"],
        "kind": v["kind"],
        "icon": v["icon"],
        "accent_color": v["accent_color"],
        "tagline": v["tagline"],
        "opposite_vice": v.get("opposite_vice"),
    }


def _public_content(v: Dict[str, Any], doc: Dict[str, Any], premium: bool) -> Dict[str, Any]:
    """The free payload — everything EXCEPT the resources body."""
    out: Dict[str, Any] = {
        **_meta(v),
        "edited": bool(doc.get("edited")),
        "is_premium_resources": True,        # resources require Premium
        "has_resources": bool(doc.get("resources")),
        "resource_count": len(doc.get("resources") or []),
        "user_is_premium": premium,
    }
    if v["kind"] == "saints":
        out["intro"] = doc.get("intro") or ""
        out["saints_by_virtue"] = doc.get("saints_by_virtue") or []
    else:
        out["what_is"] = doc.get("what_is") or ""
        out["life_stages"] = doc.get("life_stages") or {"singleness": "", "dating": "", "marriage": ""}
        out["overcoming_vice"] = doc.get("overcoming_vice") or ""
        out["saints"] = doc.get("saints") or []
    return out


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

class CreatePlanRequest(BaseModel):
    virtue_slugs: List[str]
    days: int = 14
    note: Optional[str] = None


class CheckinRequest(BaseModel):
    date: str
    goal_id: str


class JournalRequest(BaseModel):
    date: str
    text: str = ""


class EditContentRequest(BaseModel):
    what_is: Optional[str] = None
    life_stages: Optional[Dict[str, str]] = None
    overcoming_vice: Optional[str] = None
    saints: Optional[List[Dict[str, Any]]] = None
    resources: Optional[List[Dict[str, Any]]] = None
    intro: Optional[str] = None
    saints_by_virtue: Optional[List[Dict[str, Any]]] = None


async def _generate_goals(
    emergent_llm_key: str, virtues: List[Dict[str, Any]], days: int, note: Optional[str]
) -> List[Dict[str, Any]]:
    if not emergent_llm_key:
        raise HTTPException(status_code=503, detail="AI planning unavailable")
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    names = ", ".join(v["name"] for v in virtues)
    system = (
        "You are a faithful Catholic spiritual director helping someone grow in "
        "virtue. You ALWAYS return valid JSON exactly as requested."
    )
    extra = f"\nThe person shares this context: {note.strip()}\n" if note else ""
    prompt = (
        f"Create a concrete {days}-day plan to grow in these virtues: {names}.{extra}\n"
        "Return STRICT JSON only:\n"
        '{ "goals": [ {"virtue":"<one of the virtue names>", "type":"do"|"refrain", '
        '"text":"a short, concrete, measurable goal (do something, or refrain from something)"} ] }\n'
        "Give 2 'do' goals and 1 'refrain' goal per virtue (so 3 per virtue). "
        "Goals must be specific and achievable within the timeframe, rooted in "
        "Catholic practice (prayer, sacraments, acts of charity, fasting, "
        "accountability). Plain prose, no markdown."
        + lang_instruction()
    )
    try:
        chat = LlmChat(
            api_key=emergent_llm_key,
            session_id=f"virtus-plan-{uuid.uuid4().hex[:8]}",
            system_message=system,
        ).with_model("anthropic", CLAUDE_MODEL)
        response = await chat.send_message(UserMessage(text=prompt))
        data = _extract_json(response or "")
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover
        logger.exception("goal generation failed: %s", e)
        raise HTTPException(status_code=502, detail="Could not build your plan; please retry.")

    goals: List[Dict[str, Any]] = []
    name_to_slug = {v["name"].lower(): v["slug"] for v in virtues}
    for g in (data.get("goals") or []):
        text = (g.get("text") or "").strip()
        if not text:
            continue
        gtype = "refrain" if (g.get("type") or "").lower().startswith("refr") else "do"
        vname = (g.get("virtue") or "").strip().lower()
        slug = name_to_slug.get(vname) or (virtues[0]["slug"] if virtues else "")
        goals.append({
            "id": f"g_{uuid.uuid4().hex[:10]}",
            "virtue_slug": slug,
            "type": gtype,
            "text": text,
            "done": False,
            "done_at": None,
        })
    if not goals:
        raise HTTPException(status_code=502, detail="No goals were generated; please retry.")
    return goals


def _gold_max_fallen(days: int) -> int:
    """Maximum number of "fallen" (incomplete) days that still earns Gold.

    User-specified anchors: 7d→2, 14d→4, 30d→6, 60d→7. We piecewise-interpolate
    so any custom plan length gets a sensible threshold.
    """
    table = [(7, 2), (14, 4), (30, 6), (60, 7)]
    if days <= table[0][0]:
        return max(0, round(days * table[0][1] / table[0][0]))
    if days >= table[-1][0]:
        return table[-1][1]
    for (d0, g0), (d1, g1) in zip(table, table[1:]):
        if d0 <= days <= d1:
            return round(g0 + (g1 - g0) * (days - d0) / (d1 - d0))
    return table[-1][1]


def _compute_badge(p: Dict[str, Any], goals: List[Dict[str, Any]], checkins: Dict[str, List[str]]) -> Dict[str, Any]:
    """Perseverance badge — counts days *fully* completed vs days fallen across
    the elapsed portion of the plan. Catholic mindset: perseverance over
    perfection. Gold/Silver/Bronze tiers per the user's rules.
    """
    total_goals = len(goals)
    days = int(p.get("days") or 0)
    gold_max = _gold_max_fallen(days)
    silver_max = max(gold_max, days // 2)
    goal_ids = {g.get("id") for g in goals}

    try:
        start = _date.fromisoformat(p.get("start_date"))
    except Exception:
        start = _date.today()
    today = _date.today()
    # Evaluate days strictly before today (today is still in progress), capped at plan length.
    elapsed = max(0, (today - start).days)
    elapsed = min(elapsed, days)

    completed_days = 0
    for i in range(elapsed):
        d = (start + timedelta(days=i)).isoformat()
        done = set(checkins.get(d) or []) & goal_ids
        if total_goals > 0 and len(done) >= total_goals:
            completed_days += 1
    fallen = elapsed - completed_days

    final = today >= (start + timedelta(days=days))
    if elapsed == 0:
        tier = "none"
    elif fallen <= gold_max:
        tier = "gold"
    elif fallen <= silver_max:
        tier = "silver"
    else:
        tier = "bronze"

    return {
        "tier": tier,
        "fallen": fallen,
        "completed_days": completed_days,
        "elapsed": elapsed,
        "gold_max": gold_max,
        "silver_max": silver_max,
        "final": final,
    }


def _shape_plan(p: Dict[str, Any]) -> Dict[str, Any]:
    goals = p.get("goals") or []
    checkins: Dict[str, List[str]] = p.get("checkins") or {}
    journal: Dict[str, str] = p.get("journal") or {}
    today = _date.today().isoformat()
    done_today = len([g for g in (checkins.get(today) or []) if any(x.get("id") == g for x in goals)])
    return {
        "id": p["id"],
        "virtue_slugs": p.get("virtue_slugs") or [],
        "virtues": [
            _meta(VIRTUES_BY_SLUG[s]) for s in (p.get("virtue_slugs") or []) if s in VIRTUES_BY_SLUG
        ],
        "start_date": p.get("start_date"),
        "end_date": p.get("end_date"),
        "days": p.get("days"),
        "note": p.get("note"),
        "goals": goals,
        "total": len(goals),
        "completed": done_today,
        "checkins": checkins,
        "journal": journal,
        "days_logged": len([d for d, ids in checkins.items() if ids]),
        "today": today,
        "badge": _compute_badge(p, goals, checkins),
        "active": (p.get("end_date") or today) >= today,
        "created_at": p.get("created_at"),
    }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def build_router(
    db: AsyncIOMotorDatabase,
    get_current_user,
    emergent_llm_key: str,
) -> APIRouter:
    router = APIRouter(prefix="/virtues", tags=["virtues"])

    # ---- catalogue ----
    @router.get("")
    async def list_virtues(user=Depends(get_current_user)):
        lang = get_lang()
        ready_filter = (
            {"$or": [{"lang": "en"}, {"lang": {"$exists": False}}]}
            if lang == "en"
            else {"lang": lang}
        )
        ready = set(await db.virtue_content.distinct("slug", ready_filter))
        return {
            "items": [
                {**_meta(v), "has_content": v["slug"] in ready}
                for v in VIRTUES
            ],
            "user_is_premium": is_premium_user(user),
            "is_admin": _is_admin(user),
        }

    # ---- plans (must be declared before /{slug} to avoid route capture) ----
    @router.get("/plans")
    async def list_plans(user=Depends(get_current_user)):
        cur = db.virtue_plans.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1)
        items = [_shape_plan(p) async for p in cur]
        # active first
        items.sort(key=lambda x: (not x["active"], x.get("created_at") or ""), reverse=False)
        return {"items": items}

    @router.post("/plans")
    async def create_plan(payload: CreatePlanRequest, user=Depends(get_current_user)):
        slugs = [s for s in (payload.virtue_slugs or []) if s in VIRTUES_BY_SLUG]
        if not slugs:
            raise HTTPException(status_code=400, detail="Pick at least one virtue to work on.")
        days = max(1, min(int(payload.days or 14), 120))
        virtues = [VIRTUES_BY_SLUG[s] for s in slugs]
        goals = await _generate_goals(emergent_llm_key, virtues, days, payload.note)
        now = datetime.now(timezone.utc)
        start = _date.today()
        end = start + timedelta(days=days)
        plan = {
            "id": f"vp_{uuid.uuid4().hex[:12]}",
            "user_id": user.user_id,
            "virtue_slugs": slugs,
            "days": days,
            "note": (payload.note or "").strip() or None,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "goals": goals,
            "checkins": {},
            "journal": {},
            "created_at": now.isoformat(),
        }
        await db.virtue_plans.insert_one(plan)
        return _shape_plan(plan)

    @router.get("/plans/{plan_id}")
    async def get_plan(plan_id: str, user=Depends(get_current_user)):
        p = await db.virtue_plans.find_one({"id": plan_id, "user_id": user.user_id}, {"_id": 0})
        if not p:
            raise HTTPException(status_code=404, detail="Plan not found")
        return _shape_plan(p)

    @router.post("/plans/{plan_id}/goals/{goal_id}/toggle")
    async def toggle_goal(plan_id: str, goal_id: str, user=Depends(get_current_user)):
        p = await db.virtue_plans.find_one({"id": plan_id, "user_id": user.user_id})
        if not p:
            raise HTTPException(status_code=404, detail="Plan not found")
        goals = p.get("goals") or []
        found = False
        for g in goals:
            if g.get("id") == goal_id:
                g["done"] = not bool(g.get("done"))
                g["done_at"] = datetime.now(timezone.utc).isoformat() if g["done"] else None
                found = True
                break
        if not found:
            raise HTTPException(status_code=404, detail="Goal not found")
        await db.virtue_plans.update_one({"id": plan_id}, {"$set": {"goals": goals}})
        p["goals"] = goals
        return _shape_plan(p)

    @router.delete("/plans/{plan_id}")
    async def delete_plan(plan_id: str, user=Depends(get_current_user)):
        res = await db.virtue_plans.delete_one({"id": plan_id, "user_id": user.user_id})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Plan not found")
        return {"ok": True}

    @router.post("/plans/{plan_id}/checkin")
    async def checkin_goal(plan_id: str, payload: CheckinRequest, user=Depends(get_current_user)):
        try:
            datetime.strptime(payload.date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
        p = await db.virtue_plans.find_one({"id": plan_id, "user_id": user.user_id})
        if not p:
            raise HTTPException(status_code=404, detail="Plan not found")
        goal_ids = {g.get("id") for g in (p.get("goals") or [])}
        if payload.goal_id not in goal_ids:
            raise HTTPException(status_code=404, detail="Goal not found")
        checkins: Dict[str, List[str]] = p.get("checkins") or {}
        day = list(checkins.get(payload.date) or [])
        if payload.goal_id in day:
            day = [g for g in day if g != payload.goal_id]
        else:
            day.append(payload.goal_id)
        if day:
            checkins[payload.date] = day
        else:
            checkins.pop(payload.date, None)
        await db.virtue_plans.update_one({"id": plan_id}, {"$set": {"checkins": checkins}})
        p["checkins"] = checkins
        return _shape_plan(p)

    @router.put("/plans/{plan_id}/journal")
    async def set_journal(plan_id: str, payload: JournalRequest, user=Depends(get_current_user)):
        try:
            datetime.strptime(payload.date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
        p = await db.virtue_plans.find_one({"id": plan_id, "user_id": user.user_id})
        if not p:
            raise HTTPException(status_code=404, detail="Plan not found")
        journal: Dict[str, str] = p.get("journal") or {}
        text = (payload.text or "").strip()
        if text:
            journal[payload.date] = text
        else:
            journal.pop(payload.date, None)
        await db.virtue_plans.update_one({"id": plan_id}, {"$set": {"journal": journal}})
        p["journal"] = journal
        return _shape_plan(p)

    # ---- per-virtue content ----
    @router.get("/{slug}")
    async def get_virtue(slug: str, user=Depends(get_current_user)):
        v = VIRTUES_BY_SLUG.get(slug)
        if not v:
            raise HTTPException(status_code=404, detail="Virtue not found")
        doc = await _get_or_create_content(db, emergent_llm_key, slug)
        return _public_content(v, doc, is_premium_user(user))

    @router.get("/{slug}/resources")
    async def get_resources(slug: str, user=Depends(get_current_user)):
        v = VIRTUES_BY_SLUG.get(slug)
        if not v:
            raise HTTPException(status_code=404, detail="Virtue not found")
        require_premium(user, feature="virtue Resources")
        doc = await _get_or_create_content(db, emergent_llm_key, slug)
        return {"slug": slug, "resources": doc.get("resources") or []}

    # ---- admin: edit / regenerate ----
    @router.put("/{slug}")
    async def admin_edit(slug: str, payload: EditContentRequest, user=Depends(get_current_user)):
        if not _is_admin(user):
            raise HTTPException(status_code=403, detail="Admins only")
        v = VIRTUES_BY_SLUG.get(slug)
        if not v:
            raise HTTPException(status_code=404, detail="Virtue not found")
        doc = await _get_or_create_content(db, emergent_llm_key, slug)
        update: Dict[str, Any] = {}
        for field in ("what_is", "overcoming_vice", "intro"):
            val = getattr(payload, field)
            if val is not None:
                update[field] = val
        if payload.life_stages is not None:
            base = doc.get("life_stages") or {}
            base.update({k: v for k, v in payload.life_stages.items() if k in ("singleness", "dating", "marriage")})
            update["life_stages"] = base
        if payload.saints is not None:
            update["saints"] = payload.saints
        if payload.resources is not None:
            update["resources"] = payload.resources
        if payload.saints_by_virtue is not None:
            update["saints_by_virtue"] = payload.saints_by_virtue
        if not update:
            raise HTTPException(status_code=400, detail="Nothing to update")
        update["edited"] = True
        update["edited_at"] = datetime.now(timezone.utc).isoformat()
        await db.virtue_content.update_one(_content_filter(slug), {"$set": update})
        new_doc = await db.virtue_content.find_one(_content_filter(slug), {"_id": 0})
        full = {**_public_content(v, new_doc, True), "resources": new_doc.get("resources") or []}
        return full

    @router.post("/{slug}/regenerate")
    async def admin_regenerate(slug: str, user=Depends(get_current_user)):
        if not _is_admin(user):
            raise HTTPException(status_code=403, detail="Admins only")
        v = VIRTUES_BY_SLUG.get(slug)
        if not v:
            raise HTTPException(status_code=404, detail="Virtue not found")
        doc = await _generate_content(emergent_llm_key, v)
        await db.virtue_content.update_one({"slug": slug, "lang": get_lang()}, {"$set": doc}, upsert=True)
        return {**_public_content(v, doc, True), "resources": doc.get("resources") or []}

    # ---- admin: full content incl. resources (for the edit screen) ----
    @router.get("/{slug}/admin")
    async def admin_full(slug: str, user=Depends(get_current_user)):
        if not _is_admin(user):
            raise HTTPException(status_code=403, detail="Admins only")
        v = VIRTUES_BY_SLUG.get(slug)
        if not v:
            raise HTTPException(status_code=404, detail="Virtue not found")
        doc = await _get_or_create_content(db, emergent_llm_key, slug)
        return {**_public_content(v, doc, True), "resources": doc.get("resources") or []}

    return router

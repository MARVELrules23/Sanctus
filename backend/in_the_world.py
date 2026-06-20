"""'In the World' — politics & public life through a Catholic moral / social
teaching lens.

Issue-based (not a live news feed): a curated set of perennial public issues,
each explained through the Church's Social Teaching and magisterial documents.
Reflections are AI-generated (Claude), cached per (issue, language). The tone is
strictly NON-PARTISAN — it never endorses a party or candidate — yet it is
CLEAR where the Church teaches definitively (e.g. abortion and euthanasia are
always gravely wrong) and distinguishes those from matters of prudential
judgment where faithful Catholics may disagree on application.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from lang_ctx import get_lang, lang_instruction

MODEL = "claude-sonnet-4-5-20250929"

ISSUES: List[Dict[str, Any]] = [
    {"slug": "life-and-dignity", "title": "Life & Human Dignity", "icon": "heart-outline",
     "accent": "#9C3B2E", "blurb": "Abortion, euthanasia, the death penalty and the dignity of every person."},
    {"slug": "common-good", "title": "The Common Good", "icon": "people-outline",
     "accent": "#3E5C76", "blurb": "Politics ordered to the flourishing of all, not private interest."},
    {"slug": "poverty-and-the-poor", "title": "Poverty & the Poor", "icon": "hand-left-outline",
     "accent": "#7A6A33", "blurb": "The preferential option for the poor and a just economy."},
    {"slug": "immigration", "title": "Immigration & the Stranger", "icon": "walk-outline",
     "accent": "#4F8A6B", "blurb": "Welcoming the migrant while respecting the common good and law."},
    {"slug": "religious-liberty", "title": "Religious Liberty", "icon": "book-outline",
     "accent": "#5E6BA8", "blurb": "Freedom to live and witness the faith in public life."},
    {"slug": "family-and-marriage", "title": "Family & Marriage", "icon": "home-outline",
     "accent": "#8A5A44", "blurb": "Marriage, family and the rights of parents in society."},
    {"slug": "work-and-economy", "title": "Work & the Economy", "icon": "briefcase-outline",
     "accent": "#3F6F6E", "blurb": "The dignity of work, just wages, and economic justice."},
    {"slug": "solidarity-and-peace", "title": "Solidarity & Peace", "icon": "git-network-outline",
     "accent": "#6B5B95", "blurb": "War, justice among nations, and our duty to one another."},
    {"slug": "care-for-creation", "title": "Care for Creation", "icon": "leaf-outline",
     "accent": "#5B7553", "blurb": "Stewardship of the earth as our common home."},
    {"slug": "subsidiarity-and-the-state", "title": "Subsidiarity & the State", "icon": "business-outline",
     "accent": "#4A5568", "blurb": "The proper role and limits of government."},
]
ISSUES_BY_SLUG = {i["slug"]: i for i in ISSUES}

SYSTEM_PROMPT = (
    "You are a faithful Catholic teacher of the Church's Social Doctrine, writing "
    "for lay Catholics who want to engage public life well. Ground everything in "
    "the Catechism, Sacred Scripture, and the social encyclicals (e.g. Rerum "
    "Novarum, Quadragesimo Anno, Pacem in Terris, Gaudium et Spes, Centesimus "
    "Annus, Evangelium Vitae, Caritas in Veritate, Laudato Si', and the "
    "Compendium of the Social Doctrine of the Church). "
    "Be STRICTLY NON-PARTISAN: never endorse, name, or attack any political party, "
    "candidate, or movement. Distinguish clearly between (a) matters the Church "
    "teaches definitively and which bind conscience — e.g. the intrinsic evil of "
    "abortion, euthanasia, and the killing of the innocent — and (b) matters of "
    "PRUDENTIAL JUDGMENT (how best to help the poor, immigration policy details, "
    "economic structures) where faithful Catholics may in good conscience differ "
    "on means. State the definitive teachings plainly and charitably; do not "
    "water them down, and do not present prudential policy preferences as dogma. "
    "Cite real Church sources accurately; never invent paragraph numbers."
)


def _extract_json(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if m:
        text = m.group(1).strip()
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        raise ValueError("no json")
    return json.loads(text[s : e + 1])


async def _generate(emergent_llm_key: str, issue: Dict[str, Any]) -> Dict[str, Any]:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    user = (
        f"Write a reflection on the public issue: \"{issue['title']}\" "
        f"({issue['blurb']}) through the lens of Catholic Social Teaching.\n\n"
        "Return STRICT JSON with these keys (all string values plain prose, no "
        "markdown, no bullet characters):\n"
        "{\n"
        '  "summary": "2-3 sentences framing the issue and why it matters to faith.",\n'
        '  "church_teaching": "A clear paragraph of what the Church actually teaches, '
        'citing specific documents/Catechism where apt.",\n'
        '  "principles": ["3-5 short CST principles at play, each one short sentence"],\n'
        '  "where_the_church_is_clear": "What is settled and binds conscience here '
        '(name it plainly, e.g. abortion/euthanasia are always gravely wrong if relevant; '
        'if the issue is mostly prudential, say so).",\n'
        '  "prudential_judgment": "Where faithful Catholics may differ on the best means, '
        'and how to reason charitably.",\n'
        '  "how_to_engage": "Concrete, non-partisan ways a Catholic citizen can act '
        '(prayer, formation, charity, voting with a formed conscience, advocacy).",\n'
        '  "prayer": "A short prayer (3-5 lines) for this intention."\n'
        "}"
        + lang_instruction()
    )
    chat = LlmChat(
        api_key=emergent_llm_key,
        session_id=f"world-{uuid.uuid4().hex[:12]}",
        system_message=SYSTEM_PROMPT,
    ).with_model("anthropic", MODEL)
    resp = await chat.send_message(UserMessage(text=user))
    data = _extract_json(resp or "")
    return {
        "slug": issue["slug"],
        "lang": get_lang(),
        "summary": str(data.get("summary") or "").strip(),
        "church_teaching": str(data.get("church_teaching") or "").strip(),
        "principles": [str(p).strip() for p in (data.get("principles") or []) if str(p).strip()],
        "where_the_church_is_clear": str(data.get("where_the_church_is_clear") or "").strip(),
        "prudential_judgment": str(data.get("prudential_judgment") or "").strip(),
        "how_to_engage": str(data.get("how_to_engage") or "").strip(),
        "prayer": str(data.get("prayer") or "").strip(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _content_filter(slug: str) -> Dict[str, Any]:
    lang = get_lang()
    if lang == "en":
        return {"slug": slug, "$or": [{"lang": "en"}, {"lang": {"$exists": False}}]}
    return {"slug": slug, "lang": lang}


def build_router(db: AsyncIOMotorDatabase, get_current_user, emergent_llm_key: str = "") -> APIRouter:
    router = APIRouter(prefix="/in-the-world", tags=["in-the-world"])

    @router.get("")
    async def list_issues(user=Depends(get_current_user)):
        return {"items": [
            {"slug": i["slug"], "title": i["title"], "icon": i["icon"],
             "accent": i["accent"], "blurb": i["blurb"]}
            for i in ISSUES
        ]}

    @router.get("/{slug}")
    async def get_issue(slug: str, user=Depends(get_current_user)):
        issue = ISSUES_BY_SLUG.get(slug)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        existing = await db.world_content.find_one(_content_filter(slug), {"_id": 0})
        if not existing:
            existing = await _generate(emergent_llm_key, issue)
            await db.world_content.update_one(
                {"slug": slug, "lang": get_lang()}, {"$set": existing}, upsert=True
            )
        return {
            "slug": slug,
            "title": issue["title"],
            "icon": issue["icon"],
            "accent": issue["accent"],
            "blurb": issue["blurb"],
            **existing,
        }

    return router

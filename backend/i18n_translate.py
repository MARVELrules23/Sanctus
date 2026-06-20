"""Generic AI translation with persistent caching.

Used to localize otherwise-static content (daily devotion practices, prayers,
chaplets, rosary) into the user's language on demand. Each unique (text,
target-language) pair is translated once by Claude and cached forever in the
`translations_cache` collection, so repeat views are instant and cheap.

Well-known Catholic prayers are rendered in their TRADITIONAL liturgical
Spanish (e.g. "Padre nuestro…", "Dios te salve, María…"), not a literal
machine translation.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

logger = logging.getLogger("sanctus.translate")

MODEL = "claude-sonnet-4-5-20250929"
SUPPORTED = {"es"}


def _key(text: str, target: str) -> str:
    return hashlib.sha1(f"{target}\x00{text}".encode("utf-8")).hexdigest()


def _extract_json(raw: str) -> Dict:
    text = (raw or "").strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if m:
        text = m.group(1).strip()
    s = text.find("{")
    e = text.rfind("}")
    if s == -1 or e == -1:
        raise ValueError("no json")
    return json.loads(text[s : e + 1])


async def _ai_translate(emergent_llm_key: str, texts: List[str], target: str) -> List[str]:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    lang_name = {"es": "Latin American Spanish (español)"}.get(target, target)
    system = (
        "You are a faithful Catholic translator. Translate each input string into "
        f"{lang_name}. For well-known Catholic prayers, devotions, antiphons and "
        "Scripture (Sign of the Cross, Our Father, Hail Mary, Glory Be, the "
        "Apostles'/Nicene Creed, Hail Holy Queen, Fatima prayer, St Michael prayer, "
        "rosary mysteries, chaplet prayers, etc.) use the TRADITIONAL official "
        "Spanish liturgical text rather than a literal word-for-word translation. "
        "Preserve line breaks and any trailing ellipses. Keep a reverent register. "
        'Return STRICT JSON: {"items": ["...", ...]} with EXACTLY the same number '
        "of items in the same order, each value translated. No commentary."
    )
    payload = json.dumps({"items": texts}, ensure_ascii=False)
    chat = LlmChat(
        api_key=emergent_llm_key,
        session_id=f"translate-{uuid.uuid4().hex[:12]}",
        system_message=system,
    ).with_model("anthropic", MODEL)
    resp = await chat.send_message(UserMessage(text=payload))
    data = _extract_json(resp or "")
    items = data.get("items") or []
    return [items[i] if i < len(items) and isinstance(items[i], str) else texts[i] for i in range(len(texts))]


async def translate_texts(
    db: AsyncIOMotorDatabase,
    emergent_llm_key: str,
    texts: List[str],
    target: str,
) -> List[str]:
    """Return `texts` translated into `target`. English / unsupported langs and
    empty strings pass through unchanged. Results are cached per string."""
    if target not in SUPPORTED or not texts:
        return texts
    keys = [_key(t, target) for t in texts]
    cached: Dict[str, str] = {}
    # Dedup the DB lookup.
    uniq_keys = list({k for k, t in zip(keys, texts) if t.strip()})
    if uniq_keys:
        async for d in db.translations_cache.find({"_id": {"$in": uniq_keys}}):
            cached[d["_id"]] = d.get("text", "")

    # Which unique strings still need translating?
    need: Dict[str, str] = {}  # key -> original text
    for k, t in zip(keys, texts):
        if t.strip() and k not in cached:
            need[k] = t
    if need and emergent_llm_key:
        need_keys = list(need.keys())
        originals = [need[k] for k in need_keys]
        try:
            translated = await _ai_translate(emergent_llm_key, originals, target)
        except Exception as e:  # noqa: BLE001
            logger.warning("translate failed: %s", e)
            translated = originals
        for k, val in zip(need_keys, translated):
            cached[k] = val
            try:
                await db.translations_cache.update_one(
                    {"_id": k},
                    {"$set": {"_id": k, "text": val, "target": target}},
                    upsert=True,
                )
            except Exception:  # noqa: BLE001
                pass

    return [cached.get(keys[i], texts[i]) if texts[i].strip() else texts[i] for i in range(len(texts))]


class TranslateRequest(BaseModel):
    texts: List[str]
    target: str = "es"


def build_router(db: AsyncIOMotorDatabase, get_user, emergent_llm_key: str) -> APIRouter:
    router = APIRouter(prefix="/translate", tags=["translate"])

    @router.post("")
    async def translate(req: TranslateRequest, user=Depends(get_user)):
        if len(req.texts) > 400:
            raise HTTPException(status_code=400, detail="too many texts (max 400)")
        items = await translate_texts(db, emergent_llm_key, req.texts, req.target)
        return {"items": items, "target": req.target}

    return router

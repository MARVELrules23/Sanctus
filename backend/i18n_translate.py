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

import asyncio
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
SUPPORTED = {"es", "it"}

_LANG_NAMES = {
    "es": "Latin American Spanish (español)",
    "it": "Italian (italiano)",
}


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
    """Translate a batch. Raises on any failure or item-count mismatch so the
    caller can retry / fall back WITHOUT caching a bad (English) result."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    lang_name = _LANG_NAMES.get(target, target)
    system = (
        "You are a faithful Catholic translator. Translate each input string into "
        f"{lang_name}. For well-known Catholic prayers, devotions, antiphons and "
        "Scripture (Sign of the Cross, Our Father, Hail Mary, Glory Be, the "
        "Apostles'/Nicene Creed, Hail Holy Queen, Fatima prayer, St Michael prayer, "
        "rosary mysteries, chaplet prayers, psalms, canticles, etc.) use the "
        f"TRADITIONAL official liturgical text of the Catholic Church in {lang_name} "
        "rather than a literal word-for-word translation. "
        "Translate EVERY item; never leave an item in English. "
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
    items = data.get("items")
    if not isinstance(items, list) or len(items) != len(texts):
        raise ValueError(
            f"item count mismatch: got {len(items) if isinstance(items, list) else 'none'} want {len(texts)}"
        )
    out: List[str] = []
    for i, t in enumerate(texts):
        v = items[i]
        out.append(v.strip() if isinstance(v, str) and v.strip() else t)
    return out


async def _translate_segment(emergent_llm_key: str, items: List[str], target: str) -> List[str]:
    """Translate a list of strings. On failure (e.g. a single verse tripping the
    model's content filter) the batch is BISECTED and retried, so one
    problematic item can't block its whole chapter. Items that still cannot be
    translated are returned unchanged (English) rather than poisoning the cache."""
    for attempt in range(2):
        try:
            return await _ai_translate(emergent_llm_key, items, target)
        except Exception as e:  # noqa: BLE001
            logger.warning("translate segment(%d) failed: %s", len(items), str(e)[:140])
            await asyncio.sleep(0.4)
    if len(items) <= 1:
        return list(items)  # give up on this single item; keep English
    mid = len(items) // 2
    left = await _translate_segment(emergent_llm_key, items[:mid], target)
    right = await _translate_segment(emergent_llm_key, items[mid:], target)
    return left + right


async def _translate_chunked(emergent_llm_key: str, originals: List[str], target: str) -> Dict[int, str]:
    """Translate `originals`, returning index -> translated text ONLY for items
    that were genuinely translated (Spanish always differs from English)."""
    result: Dict[int, str] = {}
    CHUNK = 25
    for start in range(0, len(originals), CHUNK):
        part = originals[start : start + CHUNK]
        translated = await _translate_segment(emergent_llm_key, part, target)
        for j, val in enumerate(translated):
            if val and val != part[j]:
                result[start + j] = val
    return result


async def translate_texts(
    db: AsyncIOMotorDatabase,
    emergent_llm_key: str,
    texts: List[str],
    target: str,
) -> List[str]:
    """Return `texts` translated into `target`. English / unsupported langs and
    empty strings pass through unchanged. Only successful translations are
    cached — failures fall back to English for this call and are retried later."""
    if target not in SUPPORTED or not texts:
        return texts
    keys = [_key(t, target) for t in texts]
    cached: Dict[str, str] = {}
    uniq_keys = list({k for k, t in zip(keys, texts) if t.strip()})
    if uniq_keys:
        async for d in db.translations_cache.find({"_id": {"$in": uniq_keys}}):
            if d.get("text"):
                cached[d["_id"]] = d["text"]

    # Unique strings still needing translation (preserve first-seen order).
    need_keys: List[str] = []
    need_texts: List[str] = []
    seen = set()
    for k, t in zip(keys, texts):
        if t.strip() and k not in cached and k not in seen:
            seen.add(k)
            need_keys.append(k)
            need_texts.append(t)

    if need_texts and emergent_llm_key:
        got = await _translate_chunked(emergent_llm_key, need_texts, target)
        for idx, val in got.items():
            k = need_keys[idx]
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

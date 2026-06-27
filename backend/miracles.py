"""Live Feed — reported Catholic miracle claims.

A curated + AI-assisted feed of REPORTED Catholic miracle claims (Eucharistic
miracles, Marian apparitions, healings, incorruptible bodies, etc.) together
with their current ecclesial status: a reported claim, under investigation,
approved by the Church, or declared not supernatural / false.

Content model:
- A set of well-documented seed entries (real, with accurate Church status and
  reputable source links) so the feed is never empty.
- Admins can ask the AI (Claude + live web search via the Emergent key) to draft
  NEW claims pulled from the web; drafts are reviewed, the suggested status is
  confirmed/edited, and then published. Nothing AI-drafted goes live until an
  admin approves it.

Everything is framed as a *reported* claim and links to the original source —
the app never asserts a miracle as fact; it reports the Church's standing.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from lang_ctx import get_lang

MODEL = "claude-sonnet-4-5-20250929"

# Verdict / ecclesial status vocabulary
VERDICTS = {"reported", "investigating", "approved", "not_supernatural"}
TYPES = {"eucharistic", "marian", "healing", "incorruptible", "apparition", "other"}

# --------------------------------------------------------------------------- #
# Seed: well-known, accurately-classified claims with reputable sources.       #
# --------------------------------------------------------------------------- #
SEED_CLAIMS: List[Dict[str, Any]] = [
    {
        "slug": "lanciano",
        "title": "The Eucharistic Miracle of Lanciano",
        "summary": "In the 8th century at Lanciano, Italy, a host and wine reportedly turned into "
        "visible flesh and blood during Mass. 20th-century scientific studies identified the flesh "
        "as cardiac tissue and the blood as type AB. It is among the most studied Eucharistic miracles.",
        "type": "eucharistic", "verdict": "approved",
        "location": "Lanciano, Italy", "reported_year": "c. 750",
        "source_name": "EWTN", "source_url": "https://www.ewtn.com/catholicism/library/eucharistic-miracle-of-lanciano-4983",
    },
    {
        "slug": "guadalupe-tilma",
        "title": "Our Lady of Guadalupe and the Tilma",
        "summary": "In 1531 St. Juan Diego's tilma was imprinted with the image of the Virgin Mary near "
        "Mexico City. The cloth's preservation and the image's properties remain unexplained; the apparition "
        "is approved and Guadalupe is a major Marian shrine.",
        "type": "marian", "verdict": "approved",
        "location": "Tepeyac, Mexico City", "reported_year": "1531",
        "source_name": "Britannica", "source_url": "https://www.britannica.com/topic/Our-Lady-of-Guadalupe",
    },
    {
        "slug": "buenos-aires-1996",
        "title": "The Eucharistic Miracle of Buenos Aires",
        "summary": "In 1996 a discarded host in Buenos Aires reportedly transformed into bloody tissue. "
        "Investigated under then-Archbishop Jorge Bergoglio (later Pope Francis), later analyses described "
        "cardiac muscle tissue. It is widely reported though not formally declared.",
        "type": "eucharistic", "verdict": "investigating",
        "location": "Buenos Aires, Argentina", "reported_year": "1996",
        "source_name": "Wikipedia", "source_url": "https://en.wikipedia.org/wiki/Eucharistic_miracle_of_Buenos_Aires",
    },
    {
        "slug": "carlo-acutis-incorrupt",
        "title": "Bl. Carlo Acutis — Miracles Toward Canonization",
        "summary": "The body of Bl. Carlo Acutis, the teen 'patron of the internet,' lies in Assisi. Two "
        "healing miracles attributed to his intercession were approved by the Vatican, clearing the way for "
        "his canonization.",
        "type": "healing", "verdict": "approved",
        "location": "Assisi, Italy", "reported_year": "2020-2024",
        "source_name": "Vatican News", "source_url": "https://www.vaticannews.va/en/saints.html",
    },
    {
        "slug": "fatima-1917",
        "title": "Our Lady of Fátima and the Miracle of the Sun",
        "summary": "In 1917 three shepherd children at Fátima, Portugal reported Marian apparitions, "
        "culminating in the 'Miracle of the Sun' witnessed by a large crowd on 13 October. The apparitions "
        "were declared worthy of belief by the Church.",
        "type": "marian", "verdict": "approved",
        "location": "Fátima, Portugal", "reported_year": "1917",
        "source_name": "Britannica", "source_url": "https://www.britannica.com/topic/Our-Lady-of-Fatima",
    },
    {
        "slug": "medjugorje",
        "title": "The Reported Apparitions of Medjugorje",
        "summary": "Since 1981, six visionaries in Medjugorje (Bosnia and Herzegovina) have reported ongoing "
        "Marian apparitions. In 2024 the Vatican gave a 'nihil obstat,' permitting devotion while not "
        "pronouncing on the supernatural character of the alleged apparitions themselves.",
        "type": "apparition", "verdict": "investigating",
        "location": "Medjugorje, Bosnia and Herzegovina", "reported_year": "1981-present",
        "source_name": "Vatican News", "source_url": "https://www.vaticannews.va/en.html",
    },
]


def _extract_json_array(raw: str) -> List[Dict[str, Any]]:
    text = (raw or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    if m:
        text = m.group(1).strip()
    s, e = text.find("["), text.rfind("]")
    if s == -1 or e == -1:
        # maybe a single object
        s2, e2 = text.find("{"), text.rfind("}")
        if s2 != -1 and e2 != -1:
            obj = json.loads(text[s2 : e2 + 1])
            return obj.get("items", []) if isinstance(obj, dict) else [obj]
        raise ValueError("no json array")
    return json.loads(text[s : e + 1])


def _slugify(s: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return (base or "claim")[:60] + "-" + uuid.uuid4().hex[:6]


import unicodedata


def _norm(s: Optional[str]) -> str:
    """Lower-case and strip accents for accent-insensitive search."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)
    ).lower()


# --------------------------------------------------------------------------- #
# Process ladders — the typical ecclesial process a claim travels, and where    #
# the claim currently sits. Chosen by claim type; a claim may also store an     #
# explicit process_stage / process_note that overrides the derived defaults.    #
# --------------------------------------------------------------------------- #
PROCESS_LADDERS: Dict[str, Dict[str, Any]] = {
    "apparition": {
        "name": "Discernment of an alleged apparition (2024 DDF Norms)",
        "stages": ["Reported", "Diocesan investigation", "Reviewed by the Holy See (DDF)", "Conclusion (Nihil obstat / Declaration)"],
    },
    "eucharistic": {
        "name": "Investigation of a Eucharistic claim",
        "stages": ["Reported", "Diocesan inquiry", "Scientific examination", "Church judgment"],
    },
    "canonization": {
        "name": "Toward canonization (miracle attributed to intercession)",
        "stages": ["Servant of God", "Venerable", "Blessed (1 miracle)", "Saint (2 miracles)"],
    },
    "generic": {
        "name": "Ecclesial discernment",
        "stages": ["Reported", "Under investigation", "Examined by the Church", "Conclusion"],
    },
}
_CURRENT_INDEX: Dict[str, Dict[str, int]] = {
    "apparition": {"reported": 0, "investigating": 1, "approved": 3, "not_supernatural": 3},
    "eucharistic": {"reported": 0, "investigating": 2, "approved": 3, "not_supernatural": 3},
    "canonization": {"reported": 0, "investigating": 1, "approved": 3, "not_supernatural": 0},
    "generic": {"reported": 0, "investigating": 1, "approved": 3, "not_supernatural": 3},
}
_DEFAULT_NOTE = {
    "reported": "A claim has been reported. The local Church has not yet opened a formal investigation.",
    "investigating": "The claim is being examined — usually by the local diocese, sometimes with scientific or theological review — before any judgment is given.",
    "approved": "The Church has recognised this claim — e.g. approval of the cult, a nihil obstat, or recognition of a miracle for a cause of canonization.",
    "not_supernatural": "After examination, the competent authority has declared this not to be of supernatural origin.",
}


def _ladder_key(t: str) -> str:
    if t in ("marian", "apparition"):
        return "apparition"
    if t == "eucharistic":
        return "eucharistic"
    if t in ("healing", "incorruptible"):
        return "canonization"
    return "generic"


def _process_for(doc: Dict[str, Any]) -> Dict[str, Any]:
    t = doc.get("type") or "other"
    verdict = doc.get("verdict") or "reported"
    lk = _ladder_key(t)
    ladder = PROCESS_LADDERS[lk]
    cur = _CURRENT_INDEX[lk].get(verdict, 0)
    stages = [
        {"label": label, "done": i < cur, "current": i == cur}
        for i, label in enumerate(ladder["stages"])
    ]
    note = (doc.get("process_note") or "").strip() or _DEFAULT_NOTE.get(verdict, "")
    current_label = (doc.get("process_stage") or "").strip() or ladder["stages"][cur]
    if verdict == "not_supernatural" and not (doc.get("process_stage") or "").strip():
        current_label = "Declared not supernatural"
    return {"name": ladder["name"], "stages": stages, "current_label": current_label, "note": note}


def _public(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "claim_id": doc.get("claim_id"),
        "slug": doc.get("slug"),
        "title": doc.get("title"),
        "summary": doc.get("summary"),
        "type": doc.get("type") or "other",
        "verdict": doc.get("verdict") or "reported",
        "location": doc.get("location"),
        "reported_year": doc.get("reported_year"),
        "source_name": doc.get("source_name"),
        "source_url": doc.get("source_url"),
        "process_stage": doc.get("process_stage"),
        "process_note": doc.get("process_note"),
        "process": _process_for(doc),
        "state": doc.get("state") or "published",
        "origin": doc.get("origin") or "seed",
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


async def _localize(db, items: List[Dict[str, Any]], fields: List[str]):
    """Translate the given string fields of feed items into the request language."""
    import os as _os
    lang = get_lang()
    if lang == "en" or not items:
        return items
    texts: List[str] = []
    idx: List[tuple] = []
    for i, it in enumerate(items):
        for f in fields:
            v = it.get(f)
            if isinstance(v, str) and v.strip():
                idx.append((i, f))
                texts.append(v)
    if not texts:
        return items
    try:
        from i18n_translate import translate_texts
        tr = await translate_texts(db, _os.environ.get("EMERGENT_LLM_KEY", ""), texts, lang)
        for (i, f), t in zip(idx, tr):
            if isinstance(t, str) and t.strip():
                items[i][f] = t
    except Exception:  # noqa: BLE001
        pass
    return items


async def _ai_generate(db, emergent_llm_key: str, focus: str = "") -> List[Dict[str, Any]]:
    """Use Claude + live web search to draft recent reported Catholic miracle claims."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    system = (
        "You are a careful Catholic researcher building a 'reported miracle claims' feed. "
        "Use web search to find RECENT, REAL, reported Catholic miracle claims (Eucharistic "
        "miracles, Marian apparitions, healings, incorruptible bodies). Use reputable sources: "
        "Catholic news outlets (Catholic News Agency, EWTN, National Catholic Register, Aleteia, "
        "Vatican News), diocesan statements, or major news. NEVER assert a miracle as fact — use "
        "'reported'/'alleged' language. Classify each claim's current ecclesial status accurately. "
        "Do NOT invent URLs; only use real article URLs you actually found."
    )
    focus_line = f"Focus area: {focus}.\n" if focus else ""
    user = (
        f"{focus_line}Find 4-6 distinct recent reported Catholic miracle claims and return STRICT JSON: "
        "an array of objects, no markdown. Each object:\n"
        "{\n"
        '  "title": "short headline",\n'
        '  "summary": "3-4 sentence neutral summary using reported/alleged language",\n'
        '  "type": one of "eucharistic" | "marian" | "healing" | "incorruptible" | "apparition" | "other",\n'
        '  "verdict": one of "reported" (claimed, no formal action) | "investigating" (diocese/Vatican examining) '
        '| "approved" (Church recognized) | "not_supernatural" (declared not supernatural/false),\n'
        '  "location": "city, country",\n'
        '  "reported_year": "year or range as a string",\n'
        '  "source_name": "publication name",\n'
        '  "source_url": "the real article URL"\n'
        "}\n"
        "Return ONLY the JSON array."
    )
    chat = LlmChat(
        api_key=emergent_llm_key,
        session_id=f"miracles-{uuid.uuid4().hex[:10]}",
        system_message=system,
    ).with_model("anthropic", MODEL)
    chat.with_tools([{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}])
    resp = await chat.send_message_with_tools(UserMessage(text=user))
    rows = _extract_json_array(resp.content or "")
    out: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()
    for r in rows:
        if not isinstance(r, dict):
            continue
        title = str(r.get("title") or "").strip()
        url = str(r.get("source_url") or "").strip()
        if not title or not url.startswith("http"):
            continue
        vtype = str(r.get("type") or "other").strip().lower()
        verdict = str(r.get("verdict") or "reported").strip().lower()
        out.append({
            "claim_id": f"mir_{uuid.uuid4().hex[:12]}",
            "slug": _slugify(title),
            "title": title,
            "summary": str(r.get("summary") or "").strip(),
            "type": vtype if vtype in TYPES else "other",
            "verdict": verdict if verdict in VERDICTS else "reported",
            "location": str(r.get("location") or "").strip(),
            "reported_year": str(r.get("reported_year") or "").strip(),
            "source_name": str(r.get("source_name") or "").strip(),
            "source_url": url,
            "state": "draft",
            "origin": "ai",
            "created_at": now,
            "updated_at": now,
        })
    return out


async def _seed_if_missing(db) -> int:
    col = db["miracle_claims"]
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()
    for s in SEED_CLAIMS:
        exists = await col.find_one({"slug": s["slug"]}, {"_id": 1})
        if exists:
            continue
        doc = {
            "claim_id": f"mir_{uuid.uuid4().hex[:12]}",
            **s,
            "state": "published",
            "origin": "seed",
            "created_at": now,
            "updated_at": now,
        }
        await col.insert_one(doc)
        inserted += 1
    return inserted


class PatchModel(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    type: Optional[str] = None
    verdict: Optional[str] = None
    location: Optional[str] = None
    reported_year: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    process_stage: Optional[str] = None
    process_note: Optional[str] = None


class GenerateModel(BaseModel):
    focus: Optional[str] = None


def build_router(db: AsyncIOMotorDatabase, get_current_user, emergent_llm_key: str = "") -> APIRouter:
    router = APIRouter(prefix="/miracles", tags=["miracles"])
    col = db["miracle_claims"]

    async def _ensure_admin(user) -> None:
        if not user or not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="Admin only")

    # ----------------------------- Public ---------------------------------- #
    @router.get("")
    async def list_published(
        q: Optional[str] = Query(None, description="search text"),
        type: Optional[str] = Query(None),
        verdict: Optional[str] = Query(None),
        user=Depends(get_current_user),
    ):
        await _seed_if_missing(db)
        query: Dict[str, Any] = {"state": "published"}
        if type in TYPES:
            query["type"] = type
        if verdict in VERDICTS:
            query["verdict"] = verdict
        cur = col.find(query, {"_id": 0}).sort([("created_at", -1)])
        items = [_public(d) async for d in cur]
        if q and q.strip():
            nq = _norm(q)
            items = [
                it for it in items
                if nq in _norm(it.get("title")) or nq in _norm(it.get("summary")) or nq in _norm(it.get("location"))
            ]
        await _localize(db, items, ["title", "summary", "location"])
        return {
            "items": items,
            "total": len(items),
            "server_time": datetime.now(timezone.utc).isoformat(),
        }

    @router.get("/admin/all")
    async def list_all(user=Depends(get_current_user)):
        await _ensure_admin(user)
        await _seed_if_missing(db)
        cur = col.find({}, {"_id": 0}).sort([("state", 1), ("created_at", -1)])
        items = [_public(d) async for d in cur]
        return {"items": items, "total": len(items)}

    @router.post("/admin/generate")
    async def generate(payload: GenerateModel, user=Depends(get_current_user)):
        await _ensure_admin(user)
        drafts = await _ai_generate(db, emergent_llm_key, (payload.focus or "").strip())
        created = 0
        for d in drafts:
            # de-dupe by source_url
            if await col.find_one({"source_url": d["source_url"]}, {"_id": 1}):
                continue
            await col.insert_one(dict(d))
            created += 1
        return {"created": created, "drafts": [_public(d) for d in drafts]}

    @router.get("/{claim_id}")
    async def get_one(claim_id: str, user=Depends(get_current_user)):
        is_admin = bool(getattr(user, "is_admin", False))
        q: Dict[str, Any] = {"claim_id": claim_id}
        if not is_admin:
            q["state"] = "published"
        doc = await col.find_one(q, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Claim not found")
        item = _public(doc)
        await _localize(db, [item], ["title", "summary", "location"])
        return item

    @router.patch("/admin/{claim_id}")
    async def patch(claim_id: str, payload: PatchModel, user=Depends(get_current_user)):
        await _ensure_admin(user)
        updates: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
        for f, v in payload.model_dump(exclude_unset=True).items():
            if v is None:
                continue
            if f == "verdict" and v not in VERDICTS:
                raise HTTPException(status_code=400, detail="invalid verdict")
            if f == "type" and v not in TYPES:
                raise HTTPException(status_code=400, detail="invalid type")
            updates[f] = v
        res = await col.update_one({"claim_id": claim_id}, {"$set": updates})
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Claim not found")
        doc = await col.find_one({"claim_id": claim_id}, {"_id": 0})
        return _public(doc)

    @router.post("/admin/{claim_id}/publish")
    async def publish(claim_id: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        res = await col.update_one(
            {"claim_id": claim_id},
            {"$set": {"state": "published", "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Claim not found")
        return {"ok": True, "claim_id": claim_id, "state": "published"}

    @router.post("/admin/{claim_id}/unpublish")
    async def unpublish(claim_id: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        res = await col.update_one(
            {"claim_id": claim_id},
            {"$set": {"state": "draft", "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Claim not found")
        return {"ok": True, "claim_id": claim_id, "state": "draft"}

    @router.delete("/admin/{claim_id}")
    async def delete(claim_id: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        res = await col.delete_one({"claim_id": claim_id})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Claim not found")
        return {"ok": True, "claim_id": claim_id}

    return router

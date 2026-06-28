"""Fill verifiable / attributed quotes for the remaining draft saints.

For each draft missing a quote (or a source), ask Claude for ONE short,
verifiable quotation following strict rules:
  1. Prefer the saint's own well-documented words, with a real citation.
  2. Otherwise, a quote ABOUT the saint from a credible source — a Pope
     (canonization homily / encyclical), a Doctor of the Church, the Sacred
     Scripture of their liturgical feast/Common, or the Roman Martyrology.
  3. Never invent quotes or citations; if nothing verifiable exists, return
     empty and the saint stays in draft.

Idempotent: only touches drafts that still lack quote/quote_source.
"""
from __future__ import annotations

import asyncio
import json
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

KEY = os.environ["EMERGENT_LLM_KEY"]
MODEL = ("anthropic", "claude-sonnet-4-5-20250929")
CONCURRENCY = 4

SYS = (
    "You are a careful Catholic theologian and editor preparing verified "
    "quotations for a devotional app. Accuracy and verifiability are "
    "paramount — you must NEVER fabricate a quotation or a citation."
)

PROMPT = """For the following figure, provide ONE short, VERIFIABLE quotation suitable for a Catholic devotional card.

Figure: {name}
Rank: {rank}
Short biography: {bio}
Existing quote (may be empty): {existing}

STRICT RULES:
1. PREFER the figure's own authentic, well-documented words, with a real citation (work title or context). Use "(attributed)" only if it is a genuinely traditional attribution.
2. If you are NOT confident this figure left a documented quotation, instead give a quotation ABOUT this figure from a credible source: a Pope (canonization/beatification homily or encyclical), a Doctor of the Church, the Sacred Scripture proper to their liturgical feast or Common, or the Roman Martyrology entry.
3. RELIABLE LAST RESORT (applies to virtually every canonized saint): quote or faithfully render the Roman Martyrology's commemoration of this figure, attributed as "Roman Martyrology"; or cite the Scripture appointed for their liturgical Common (e.g., "Common of Martyrs — cf. Revelation 7:14", "Common of Pastors — cf. John 10:11"). You should be able to provide a verifiable quotation in almost every case; return empty ONLY if you genuinely cannot identify the figure with confidence.
4. NEVER fabricate a specific personal quotation or invent a precise citation you are unsure of. A faithful Roman Martyrology commemoration or a liturgical-Common Scripture is always acceptable and verifiable.
4. Keep the quote under ~240 characters. "quote_source" must clearly attribute it, e.g. "St. Teresa of Ávila, The Interior Castle", "Pope St. John Paul II, Canonization Homily (1998)", "Roman Martyrology", or "Cf. Philippians 2:10 (feast of the Holy Name)".
5. If the existing quote is already authentic, you may keep it and simply supply the correct source.

Return ONLY a JSON object, no prose:
{{"quote": "...", "quote_source": "..."}}
If nothing verifiable exists, return {{"quote": "", "quote_source": ""}}."""


def _parse_json(text: str) -> dict:
    s, e = text.find("{"), text.rfind("}")
    if s < 0 or e < 0:
        return {}
    try:
        return json.loads(text[s:e + 1])
    except Exception:
        return {}


async def _ask(name: str, rank: str, bio: str, existing: str) -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=KEY, session_id=f"quote-{name[:30]}", system_message=SYS).with_model(*MODEL)
    msg = PROMPT.format(name=name, rank=rank, bio=(bio or "")[:600], existing=existing or "(none)")
    for attempt in range(3):
        try:
            resp = await chat.send_message(UserMessage(text=msg))
            data = _parse_json(resp)
            if isinstance(data, dict):
                return data
        except Exception as ex:
            await asyncio.sleep(3 * (attempt + 1))
            if attempt == 2:
                print("   LLM err:", repr(ex)[:80])
    return {}


def _empty(v) -> bool:
    return not (v or "").strip()


async def main() -> None:
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    col = db["saints"]
    drafts = await col.find(
        {"status": "draft",
         "$or": [{"quote": {"$in": ["", None]}}, {"quote_source": {"$in": ["", None]}}]},
        {"_id": 0},
    ).to_list(2000)
    print(f"Filling quotes for {len(drafts)} drafts...")

    sem = asyncio.Semaphore(CONCURRENCY)
    stats = {"filled": 0, "kept_empty": 0}

    async def handle(d):
        async with sem:
            data = await _ask(d.get("name", ""), d.get("rank", ""),
                              d.get("biography", ""), d.get("quote", ""))
            q = (data.get("quote") or "").strip()
            src = (data.get("quote_source") or "").strip()
            if q and src:
                await col.update_one({"saint_id": d["saint_id"]},
                                     {"$set": {"quote": q, "quote_source": src}})
                stats["filled"] += 1
                print(f"  [OK ] {d['name'][:38]:38s} | {src[:42]}")
            else:
                stats["kept_empty"] += 1
                print(f"  [-- ] {d['name'][:38]:38s} | no verifiable quote")

    await asyncio.gather(*(handle(d) for d in drafts))
    print("\n=== SUMMARY ===")
    print("  filled:", stats["filled"], "| kept empty:", stats["kept_empty"])
    print("  drafts still missing quote:",
          await col.count_documents({"status": "draft", "quote": {"$in": ["", None]}}))


if __name__ == "__main__":
    asyncio.run(main())

"""Validate & repair saint portrait images, then approve drafts that have
both a verified quote and a WORKING photo.

For each draft saint:
  1. Look up the real portrait via the Wikipedia API (title match, then
     full-text search fallback) — the AI-proposed picture_url hashes were
     mostly broken (404).
  2. Verify the candidate image actually loads (HTTP 200, image/*, > 3 KB).
  3. Persist the working picture_url.
  4. If the saint has a quote + quote_source + biography + recommended_action
     AND a working photo, promote status draft -> approved.

Idempotent: re-running only fills gaps and approves newly-eligible entries.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

UA = "SanctusApp/1.0 (Catholic saints image verification; https://sanctus.app)"
WIKI_API = "https://en.wikipedia.org/w/api.php"
CONCURRENCY = 2


def _now():
    return datetime.now(timezone.utc)


async def _get(cl: httpx.AsyncClient, url: str, params=None, attempts=5):
    """GET with 429/5xx backoff."""
    for i in range(attempts):
        try:
            r = await cl.get(url, params=params)
            if r.status_code == 200:
                return r
            if r.status_code in (429, 502, 503, 504):
                wait = int(r.headers.get("Retry-After", 0)) or (3 * (i + 1))
                await asyncio.sleep(min(wait, 20))
                continue
            return r
        except Exception:
            await asyncio.sleep(2 * (i + 1))
    return None


async def _wiki_image(cl: httpx.AsyncClient, name: str) -> str | None:
    """Return a real Wikimedia image URL for `name`, or None."""
    base = {"action": "query", "format": "json", "redirects": "1",
            "prop": "pageimages", "piprop": "original|thumbnail", "pithumbsize": "800"}
    for params in ({**base, "titles": name},
                   {**base, "generator": "search", "gsrsearch": name, "gsrlimit": "1"}):
        r = await _get(cl, WIKI_API, params=params)
        if not r:
            continue
        try:
            pages = (r.json().get("query") or {}).get("pages") or {}
        except Exception:
            continue
        for _pid, pg in pages.items():
            src = (pg.get("original") or {}).get("source") \
                or (pg.get("thumbnail") or {}).get("source")
            if src:
                return src
    return None


async def _loads(cl: httpx.AsyncClient, url: str) -> bool:
    if not url:
        return False
    r = await _get(cl, url, attempts=3)
    if not r:
        return False
    ct = r.headers.get("content-type", "")
    return r.status_code == 200 and ct.startswith("image/") and len(r.content) > 3000


async def main() -> None:
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    col = db["saints"]
    drafts = await col.find(
        {"status": "draft", "quote": {"$nin": ["", None]}}, {"_id": 0}
    ).to_list(length=2000)
    print(f"Processing {len(drafts)} drafts...")

    sem = asyncio.Semaphore(CONCURRENCY)
    stats = {"approved": 0, "image_fixed": 0, "no_quote": 0, "no_image": 0, "incomplete": 0}

    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": UA},
                                 follow_redirects=True) as cl:
        async def handle(d):
            name = d.get("name", "")
            sid = d.get("saint_id")
            async with sem:
                # find a working photo
                working = None
                cand = await _wiki_image(cl, name)
                if await _loads(cl, cand):
                    working = cand
                elif await _loads(cl, d.get("picture_url")):
                    working = d.get("picture_url")

                update = {}
                if working and working != d.get("picture_url"):
                    update["picture_url"] = working
                    stats["image_fixed"] += 1

                has_quote = bool((d.get("quote") or "").strip())
                complete = all((d.get(f) or "").strip() for f in
                               ("name", "biography", "recommended_action", "quote_source"))

                if working and has_quote and complete:
                    update.update({"status": "approved", "approved_at": _now(),
                                   "approved_by": "admin-bulk-verify"})
                    stats["approved"] += 1
                    tag = "APPROVED"
                else:
                    if not has_quote:
                        stats["no_quote"] += 1
                    elif not working:
                        stats["no_image"] += 1
                    elif not complete:
                        stats["incomplete"] += 1
                    tag = "kept-draft"

                if update:
                    await col.update_one({"saint_id": sid}, {"$set": update})
                print(f"  [{tag:9s}] {name[:40]:40s} img={'ok' if working else 'NONE'}")

        await asyncio.gather(*(handle(d) for d in drafts))

    print("\n=== SUMMARY ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("  approved total now:", await col.count_documents({"status": "approved"}))
    print("  draft remaining:", await col.count_documents({"status": "draft"}))


if __name__ == "__main__":
    asyncio.run(main())

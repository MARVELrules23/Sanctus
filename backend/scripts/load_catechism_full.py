"""
Ingest the FULL Catechism of the Catholic Church into the Sanctus library.

Source: the official Vatican archive (English, 2nd edition) —
https://www.vatican.va/archive/ENG0015/_INDEX.HTM

Each Table-of-Contents leaf page becomes one chapter in the library book,
preserving the Catechism's own pagination (Prologue, Parts, Sections, Chapters,
Articles, numbered paragraphs 1–2865, and the "IN BRIEF" summaries). The book is
stored as a free, embedded reference (tradition="reference", is_premium=False).

Usage:
    cd /app/backend && python -m scripts.load_catechism_full
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

BASE = "https://www.vatican.va/archive/ENG0015/"
INDEX_URL = BASE + "_INDEX.HTM"
SLUG = "catechism-of-the-catholic-church"
UA = {"User-Agent": "Mozilla/5.0 (SanctusApp CCC ingest)"}

LEAF_RE = re.compile(r"^__P[0-9A-Z]+\.HTM$", re.I)


def _clean(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _fetch(client: httpx.Client, url: str) -> str:
    r = client.get(url, headers=UA, timeout=30.0, follow_redirects=True)
    r.raise_for_status()
    # Vatican archive pages are Windows-1252 encoded.
    return r.content.decode("windows-1252", "ignore")


def _parse_toc(html: str) -> List[Tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    leafs: List[Tuple[str, str]] = []
    seen = set()
    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        txt = _clean(a.get_text(" "))
        if LEAF_RE.match(href) and href not in seen:
            seen.add(href)
            leafs.append((href, txt or "Section"))
    return leafs


def _page_paragraphs(html: str, title: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style"]):
        t.decompose()
    paras: List[str] = []
    for p in soup.find_all("p"):
        txt = _clean(p.get_text(" "))
        if not txt:
            continue
        # Skip a leading heading line that merely repeats the chapter title.
        if not paras and txt.strip().lower() == (title or "").strip().lower():
            continue
        paras.append(txt)
    return "\n\n".join(paras)


def _breadcrumb(txt: str, ctx: Dict[str, str]) -> str:
    u = txt.upper()
    if u.startswith("PART"):
        ctx["part"] = txt
        ctx["section"] = ctx["chapter"] = ctx["article"] = ""
    elif u.startswith("SECTION"):
        ctx["section"] = txt
        ctx["chapter"] = ctx["article"] = ""
    elif u.startswith("CHAPTER"):
        ctx["chapter"] = txt
        ctx["article"] = ""
    elif u.startswith("ARTICLE"):
        ctx["article"] = txt
    crumbs = [ctx.get(k, "") for k in ("part", "section", "chapter", "article")]
    # Don't repeat the current title inside its own breadcrumb.
    crumbs = [c for c in crumbs if c and c != txt]
    return " · ".join(crumbs)


def scrape() -> List[Dict[str, str]]:
    chapters: List[Dict[str, str]] = []
    ctx = {"part": "", "section": "", "chapter": "", "article": ""}
    with httpx.Client() as client:
        toc = _parse_toc(_fetch(client, INDEX_URL))
        print(f"TOC leaf pages: {len(toc)}", flush=True)
        for i, (href, txt) in enumerate(toc):
            sub = _breadcrumb(txt, ctx)
            try:
                body = _page_paragraphs(_fetch(client, BASE + href), txt)
            except Exception as e:  # noqa: BLE001
                print(f"  ! {href} failed: {e}", flush=True)
                body = ""
            if not body:
                continue
            chapters.append({"title": txt, "subtitle": sub, "body_md": body})
            if (i + 1) % 25 == 0:
                print(f"  ... {i + 1}/{len(toc)} pages", flush=True)
            time.sleep(0.15)
    print(f"Built {len(chapters)} chapters", flush=True)
    return chapters


async def store(chapters: List[Dict[str, str]]) -> None:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ.get("DB_NAME", "sanctus")]
    now = datetime.now(timezone.utc)
    existing = await db["library_books"].find_one({"slug": SLUG}, {"book_id": 1})
    doc = {
        "book_id": (existing or {}).get("book_id") or str(uuid.uuid4()),
        "slug": SLUG,
        "title": "Catechism of the Catholic Church",
        "author": "Catholic Church",
        "year": 1997,
        "blurb": "The complete Catechism of the Catholic Church — the full, "
        "official summary of Catholic doctrine on the Creed, the Sacraments, "
        "the moral life, and prayer, with all numbered paragraphs (1–2865).",
        "tradition": "reference",
        "cover_color": "#6B0F1A",
        "cover_icon": "library-outline",
        "type": "embedded",
        "status": "published",
        "is_premium": False,
        "source_url": INDEX_URL,
        "chapters": chapters,
        "updated_at": now,
    }
    if not existing:
        doc["created_at"] = now
    await db["library_books"].replace_one({"slug": SLUG}, doc, upsert=True)
    print(f"Stored '{SLUG}' with {len(chapters)} chapters.", flush=True)


def main() -> None:
    chapters = scrape()
    if len(chapters) < 200:
        print(f"ABORT: only {len(chapters)} chapters scraped (expected ~300+).", flush=True)
        sys.exit(1)
    asyncio.run(store(chapters))


if __name__ == "__main__":
    main()

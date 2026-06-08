"""Douay-Rheims (Challoner) Bible service.

Public-domain text sourced from api.getbible.net (translation "douayrheims").
We fetch whole-book JSON on first request and cache each chapter as its own
Mongo document for O(1) reads thereafter.

Mongo collections:
- `bible_books` ........... per-chapter cached verses
    { _id: "{book_slug}-{chapter}", book_slug, book_name, book_order, chapter,
      verses: [{n: int, text: str}], chapters_total: int, fetched_at }
- `bible_highlights` ...... per-user verse highlights
    { user_id, book_slug, chapter, verse, color, created_at, updated_at }
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import HTTPException

GETBIBLE_BASE = "https://api.getbible.net/v2/douayrheims"
USER_AGENT = "SanctusApp/1.0 (+https://sanctus.app)"
ALLOWED_COLORS = {"rose", "gold", "sage", "violet"}


# Canonical 73-book Catholic order with our internal slugs and the upstream
# getbible.net numbering (deuterocanon uses non-sequential book numbers there).
# `name` is the modern English name shown in the UI; `dr_name` is the
# Douay-Rheims Challoner title (shown as a subtitle).
BOOKS: List[Dict[str, Any]] = [
    # Old Testament — Pentateuch
    {"slug": "genesis", "order": 1, "name": "Genesis", "dr_name": "Genesis", "abbr": "Gen", "section": "ot", "getbible_nr": 1, "chapters": 50},
    {"slug": "exodus", "order": 2, "name": "Exodus", "dr_name": "Exodus", "abbr": "Ex", "section": "ot", "getbible_nr": 2, "chapters": 40},
    {"slug": "leviticus", "order": 3, "name": "Leviticus", "dr_name": "Leviticus", "abbr": "Lev", "section": "ot", "getbible_nr": 3, "chapters": 27},
    {"slug": "numbers", "order": 4, "name": "Numbers", "dr_name": "Numbers", "abbr": "Num", "section": "ot", "getbible_nr": 4, "chapters": 36},
    {"slug": "deuteronomy", "order": 5, "name": "Deuteronomy", "dr_name": "Deuteronomy", "abbr": "Deut", "section": "ot", "getbible_nr": 5, "chapters": 34},
    # Historical
    {"slug": "joshua", "order": 6, "name": "Joshua", "dr_name": "Josue", "abbr": "Josh", "section": "ot", "getbible_nr": 6, "chapters": 24},
    {"slug": "judges", "order": 7, "name": "Judges", "dr_name": "Judges", "abbr": "Judg", "section": "ot", "getbible_nr": 7, "chapters": 21},
    {"slug": "ruth", "order": 8, "name": "Ruth", "dr_name": "Ruth", "abbr": "Ruth", "section": "ot", "getbible_nr": 8, "chapters": 4},
    {"slug": "1-samuel", "order": 9, "name": "1 Samuel", "dr_name": "1 Kings (Samuel)", "abbr": "1 Sam", "section": "ot", "getbible_nr": 9, "chapters": 31},
    {"slug": "2-samuel", "order": 10, "name": "2 Samuel", "dr_name": "2 Kings (Samuel)", "abbr": "2 Sam", "section": "ot", "getbible_nr": 10, "chapters": 24},
    {"slug": "1-kings", "order": 11, "name": "1 Kings", "dr_name": "3 Kings", "abbr": "1 Kgs", "section": "ot", "getbible_nr": 11, "chapters": 22},
    {"slug": "2-kings", "order": 12, "name": "2 Kings", "dr_name": "4 Kings", "abbr": "2 Kgs", "section": "ot", "getbible_nr": 12, "chapters": 25},
    {"slug": "1-chronicles", "order": 13, "name": "1 Chronicles", "dr_name": "1 Paralipomenon", "abbr": "1 Chr", "section": "ot", "getbible_nr": 13, "chapters": 29},
    {"slug": "2-chronicles", "order": 14, "name": "2 Chronicles", "dr_name": "2 Paralipomenon", "abbr": "2 Chr", "section": "ot", "getbible_nr": 14, "chapters": 36},
    {"slug": "ezra", "order": 15, "name": "Ezra", "dr_name": "1 Esdras", "abbr": "Ezr", "section": "ot", "getbible_nr": 15, "chapters": 10},
    {"slug": "nehemiah", "order": 16, "name": "Nehemiah", "dr_name": "2 Esdras", "abbr": "Neh", "section": "ot", "getbible_nr": 16, "chapters": 13},
    {"slug": "tobit", "order": 17, "name": "Tobit", "dr_name": "Tobias", "abbr": "Tob", "section": "deutero", "getbible_nr": 69, "chapters": 14},
    {"slug": "judith", "order": 18, "name": "Judith", "dr_name": "Judith", "abbr": "Jdt", "section": "deutero", "getbible_nr": 70, "chapters": 16},
    {"slug": "esther", "order": 19, "name": "Esther", "dr_name": "Esther", "abbr": "Esth", "section": "ot", "getbible_nr": 17, "chapters": 16},
    {"slug": "1-maccabees", "order": 20, "name": "1 Maccabees", "dr_name": "1 Machabees", "abbr": "1 Macc", "section": "deutero", "getbible_nr": 80, "chapters": 16},
    {"slug": "2-maccabees", "order": 21, "name": "2 Maccabees", "dr_name": "2 Machabees", "abbr": "2 Macc", "section": "deutero", "getbible_nr": 81, "chapters": 15},
    # Wisdom
    {"slug": "job", "order": 22, "name": "Job", "dr_name": "Job", "abbr": "Job", "section": "ot", "getbible_nr": 18, "chapters": 42},
    {"slug": "psalms", "order": 23, "name": "Psalms", "dr_name": "Psalms", "abbr": "Ps", "section": "ot", "getbible_nr": 19, "chapters": 150},
    {"slug": "proverbs", "order": 24, "name": "Proverbs", "dr_name": "Proverbs", "abbr": "Prov", "section": "ot", "getbible_nr": 20, "chapters": 31},
    {"slug": "ecclesiastes", "order": 25, "name": "Ecclesiastes", "dr_name": "Ecclesiastes", "abbr": "Eccl", "section": "ot", "getbible_nr": 21, "chapters": 12},
    {"slug": "song-of-songs", "order": 26, "name": "Song of Songs", "dr_name": "Canticle of Canticles", "abbr": "Song", "section": "ot", "getbible_nr": 22, "chapters": 8},
    {"slug": "wisdom", "order": 27, "name": "Wisdom", "dr_name": "Wisdom", "abbr": "Wis", "section": "deutero", "getbible_nr": 73, "chapters": 19},
    {"slug": "sirach", "order": 28, "name": "Sirach", "dr_name": "Ecclesiasticus", "abbr": "Sir", "section": "deutero", "getbible_nr": 74, "chapters": 51},
    # Prophets
    {"slug": "isaiah", "order": 29, "name": "Isaiah", "dr_name": "Isaias", "abbr": "Isa", "section": "ot", "getbible_nr": 23, "chapters": 66},
    {"slug": "jeremiah", "order": 30, "name": "Jeremiah", "dr_name": "Jeremias", "abbr": "Jer", "section": "ot", "getbible_nr": 24, "chapters": 52},
    {"slug": "lamentations", "order": 31, "name": "Lamentations", "dr_name": "Lamentations", "abbr": "Lam", "section": "ot", "getbible_nr": 25, "chapters": 5},
    {"slug": "baruch", "order": 32, "name": "Baruch", "dr_name": "Baruch", "abbr": "Bar", "section": "deutero", "getbible_nr": 75, "chapters": 6},
    {"slug": "ezekiel", "order": 33, "name": "Ezekiel", "dr_name": "Ezechiel", "abbr": "Ezek", "section": "ot", "getbible_nr": 26, "chapters": 48},
    {"slug": "daniel", "order": 34, "name": "Daniel", "dr_name": "Daniel", "abbr": "Dan", "section": "ot", "getbible_nr": 27, "chapters": 14},
    {"slug": "hosea", "order": 35, "name": "Hosea", "dr_name": "Osee", "abbr": "Hos", "section": "ot", "getbible_nr": 28, "chapters": 14},
    {"slug": "joel", "order": 36, "name": "Joel", "dr_name": "Joel", "abbr": "Joel", "section": "ot", "getbible_nr": 29, "chapters": 3},
    {"slug": "amos", "order": 37, "name": "Amos", "dr_name": "Amos", "abbr": "Amos", "section": "ot", "getbible_nr": 30, "chapters": 9},
    {"slug": "obadiah", "order": 38, "name": "Obadiah", "dr_name": "Abdias", "abbr": "Obad", "section": "ot", "getbible_nr": 31, "chapters": 1},
    {"slug": "jonah", "order": 39, "name": "Jonah", "dr_name": "Jonas", "abbr": "Jonah", "section": "ot", "getbible_nr": 32, "chapters": 4},
    {"slug": "micah", "order": 40, "name": "Micah", "dr_name": "Micheas", "abbr": "Mic", "section": "ot", "getbible_nr": 33, "chapters": 7},
    {"slug": "nahum", "order": 41, "name": "Nahum", "dr_name": "Nahum", "abbr": "Nah", "section": "ot", "getbible_nr": 34, "chapters": 3},
    {"slug": "habakkuk", "order": 42, "name": "Habakkuk", "dr_name": "Habacuc", "abbr": "Hab", "section": "ot", "getbible_nr": 35, "chapters": 3},
    {"slug": "zephaniah", "order": 43, "name": "Zephaniah", "dr_name": "Sophonias", "abbr": "Zeph", "section": "ot", "getbible_nr": 36, "chapters": 3},
    {"slug": "haggai", "order": 44, "name": "Haggai", "dr_name": "Aggeus", "abbr": "Hag", "section": "ot", "getbible_nr": 37, "chapters": 2},
    {"slug": "zechariah", "order": 45, "name": "Zechariah", "dr_name": "Zacharias", "abbr": "Zech", "section": "ot", "getbible_nr": 38, "chapters": 14},
    {"slug": "malachi", "order": 46, "name": "Malachi", "dr_name": "Malachias", "abbr": "Mal", "section": "ot", "getbible_nr": 39, "chapters": 4},
    # New Testament — Gospels & Acts
    {"slug": "matthew", "order": 47, "name": "Matthew", "dr_name": "Matthew", "abbr": "Mt", "section": "nt", "getbible_nr": 40, "chapters": 28},
    {"slug": "mark", "order": 48, "name": "Mark", "dr_name": "Mark", "abbr": "Mk", "section": "nt", "getbible_nr": 41, "chapters": 16},
    {"slug": "luke", "order": 49, "name": "Luke", "dr_name": "Luke", "abbr": "Lk", "section": "nt", "getbible_nr": 42, "chapters": 24},
    {"slug": "john", "order": 50, "name": "John", "dr_name": "John", "abbr": "Jn", "section": "nt", "getbible_nr": 43, "chapters": 21},
    {"slug": "acts", "order": 51, "name": "Acts", "dr_name": "Acts of the Apostles", "abbr": "Acts", "section": "nt", "getbible_nr": 44, "chapters": 28},
    # Pauline Epistles
    {"slug": "romans", "order": 52, "name": "Romans", "dr_name": "Romans", "abbr": "Rom", "section": "nt", "getbible_nr": 45, "chapters": 16},
    {"slug": "1-corinthians", "order": 53, "name": "1 Corinthians", "dr_name": "1 Corinthians", "abbr": "1 Cor", "section": "nt", "getbible_nr": 46, "chapters": 16},
    {"slug": "2-corinthians", "order": 54, "name": "2 Corinthians", "dr_name": "2 Corinthians", "abbr": "2 Cor", "section": "nt", "getbible_nr": 47, "chapters": 13},
    {"slug": "galatians", "order": 55, "name": "Galatians", "dr_name": "Galatians", "abbr": "Gal", "section": "nt", "getbible_nr": 48, "chapters": 6},
    {"slug": "ephesians", "order": 56, "name": "Ephesians", "dr_name": "Ephesians", "abbr": "Eph", "section": "nt", "getbible_nr": 49, "chapters": 6},
    {"slug": "philippians", "order": 57, "name": "Philippians", "dr_name": "Philippians", "abbr": "Phil", "section": "nt", "getbible_nr": 50, "chapters": 4},
    {"slug": "colossians", "order": 58, "name": "Colossians", "dr_name": "Colossians", "abbr": "Col", "section": "nt", "getbible_nr": 51, "chapters": 4},
    {"slug": "1-thessalonians", "order": 59, "name": "1 Thessalonians", "dr_name": "1 Thessalonians", "abbr": "1 Thess", "section": "nt", "getbible_nr": 52, "chapters": 5},
    {"slug": "2-thessalonians", "order": 60, "name": "2 Thessalonians", "dr_name": "2 Thessalonians", "abbr": "2 Thess", "section": "nt", "getbible_nr": 53, "chapters": 3},
    {"slug": "1-timothy", "order": 61, "name": "1 Timothy", "dr_name": "1 Timothy", "abbr": "1 Tim", "section": "nt", "getbible_nr": 54, "chapters": 6},
    {"slug": "2-timothy", "order": 62, "name": "2 Timothy", "dr_name": "2 Timothy", "abbr": "2 Tim", "section": "nt", "getbible_nr": 55, "chapters": 4},
    {"slug": "titus", "order": 63, "name": "Titus", "dr_name": "Titus", "abbr": "Titus", "section": "nt", "getbible_nr": 56, "chapters": 3},
    {"slug": "philemon", "order": 64, "name": "Philemon", "dr_name": "Philemon", "abbr": "Phlm", "section": "nt", "getbible_nr": 57, "chapters": 1},
    {"slug": "hebrews", "order": 65, "name": "Hebrews", "dr_name": "Hebrews", "abbr": "Heb", "section": "nt", "getbible_nr": 58, "chapters": 13},
    # Catholic Epistles
    {"slug": "james", "order": 66, "name": "James", "dr_name": "James", "abbr": "Jas", "section": "nt", "getbible_nr": 59, "chapters": 5},
    {"slug": "1-peter", "order": 67, "name": "1 Peter", "dr_name": "1 Peter", "abbr": "1 Pet", "section": "nt", "getbible_nr": 60, "chapters": 5},
    {"slug": "2-peter", "order": 68, "name": "2 Peter", "dr_name": "2 Peter", "abbr": "2 Pet", "section": "nt", "getbible_nr": 61, "chapters": 3},
    {"slug": "1-john", "order": 69, "name": "1 John", "dr_name": "1 John", "abbr": "1 Jn", "section": "nt", "getbible_nr": 62, "chapters": 5},
    {"slug": "2-john", "order": 70, "name": "2 John", "dr_name": "2 John", "abbr": "2 Jn", "section": "nt", "getbible_nr": 63, "chapters": 1},
    {"slug": "3-john", "order": 71, "name": "3 John", "dr_name": "3 John", "abbr": "3 Jn", "section": "nt", "getbible_nr": 64, "chapters": 1},
    {"slug": "jude", "order": 72, "name": "Jude", "dr_name": "Jude", "abbr": "Jude", "section": "nt", "getbible_nr": 65, "chapters": 1},
    {"slug": "revelation", "order": 73, "name": "Revelation", "dr_name": "Apocalypse", "abbr": "Rev", "section": "nt", "getbible_nr": 66, "chapters": 22},
]

_BOOK_BY_SLUG: Dict[str, Dict[str, Any]] = {b["slug"]: b for b in BOOKS}
_BOOK_FETCH_LOCKS: Dict[str, asyncio.Lock] = {}


def book_meta(slug: str) -> Optional[Dict[str, Any]]:
    return _BOOK_BY_SLUG.get(slug)


def all_books() -> List[Dict[str, Any]]:
    # Return a UI-friendly copy without internal upstream IDs.
    return [
        {"slug": b["slug"], "name": b["name"], "dr_name": b["dr_name"], "abbr": b["abbr"],
         "section": b["section"], "order": b["order"], "chapters": b["chapters"]}
        for b in BOOKS
    ]


async def _fetch_book_from_upstream(book: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Download the entire book from getbible.net once and return its chapters."""
    url = f"{GETBIBLE_BASE}/{book['getbible_nr']}.json"
    async with httpx.AsyncClient(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        r = await client.get(url)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"bible upstream error ({r.status_code})")
    payload = r.json()
    chapters = payload.get("chapters") or []
    if not chapters:
        raise HTTPException(status_code=502, detail="bible upstream returned no chapters")
    return chapters


async def _ensure_book_cached(db, book: Dict[str, Any]) -> None:
    """If any chapter for this book is missing in cache, fetch the whole book and
    insert chapter docs that don't yet exist. Concurrent calls coalesce via a lock."""
    # Fast check: if any chapter for this book is already cached we assume the
    # whole book is cached (we always write all chapters together below).
    cached = await db.bible_books.find_one({"book_slug": book["slug"]}, {"_id": 1})
    if cached:
        return
    lock = _BOOK_FETCH_LOCKS.setdefault(book["slug"], asyncio.Lock())
    async with lock:
        # Re-check inside the lock
        cached = await db.bible_books.find_one({"book_slug": book["slug"]}, {"_id": 1})
        if cached:
            return
        chapters = await _fetch_book_from_upstream(book)
        now = datetime.now(timezone.utc).isoformat()
        docs = []
        for idx, chap in enumerate(chapters, start=1):
            verses_raw = chap.get("verses") or []
            verses = [
                {"n": int(v.get("verse") or v.get("v") or 0), "text": (v.get("text") or "").strip()}
                for v in verses_raw
                if (v.get("text") or "").strip()
            ]
            docs.append({
                "_id": f"{book['slug']}-{idx}",
                "book_slug": book["slug"],
                "book_name": book["name"],
                "book_order": book["order"],
                "chapter": idx,
                "verses": verses,
                "chapters_total": len(chapters),
                "fetched_at": now,
            })
        if docs:
            # Use ordered=False so retries don't fail on dup-key after partial writes.
            try:
                await db.bible_books.insert_many(docs, ordered=False)
            except Exception:
                pass


async def get_chapter(db, book_slug: str, chapter: int) -> Dict[str, Any]:
    book = book_meta(book_slug)
    if not book:
        raise HTTPException(status_code=404, detail="unknown book")
    if chapter < 1 or chapter > book["chapters"]:
        raise HTTPException(status_code=400, detail=f"chapter out of range (1-{book['chapters']})")
    await _ensure_book_cached(db, book)
    doc = await db.bible_books.find_one({"_id": f"{book_slug}-{chapter}"}, {"_id": 0, "fetched_at": 0})
    if not doc:
        # Cache write failed silently — fall back to live fetch for this chapter.
        chapters = await _fetch_book_from_upstream(book)
        chap = chapters[chapter - 1] if 0 < chapter <= len(chapters) else None
        if not chap:
            raise HTTPException(status_code=502, detail="chapter unavailable")
        doc = {
            "book_slug": book_slug,
            "book_name": book["name"],
            "book_order": book["order"],
            "chapter": chapter,
            "verses": [
                {"n": int(v.get("verse") or 0), "text": (v.get("text") or "").strip()}
                for v in (chap.get("verses") or []) if (v.get("text") or "").strip()
            ],
            "chapters_total": len(chapters),
        }
    # Enrich with book metadata so the client doesn't need a second lookup.
    doc["book_name"] = book["name"]
    doc["dr_name"] = book["dr_name"]
    doc["chapters_total"] = book["chapters"]
    return doc


def normalize_color(color: str) -> str:
    c = (color or "").strip().lower()
    if c not in ALLOWED_COLORS:
        raise HTTPException(status_code=400, detail=f"color must be one of: {sorted(ALLOWED_COLORS)}")
    return c


def parse_verse_ref(book_slug: str, chapter: int, verse: int) -> Tuple[str, int, int]:
    book = book_meta(book_slug)
    if not book:
        raise HTTPException(status_code=404, detail="unknown book")
    try:
        ch = int(chapter)
        v = int(verse)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="chapter/verse must be integers")
    if ch < 1 or ch > book["chapters"]:
        raise HTTPException(status_code=400, detail="chapter out of range")
    if v < 1 or v > 200:
        raise HTTPException(status_code=400, detail="verse out of range")
    return book_slug, ch, v


def citation_for(book_slug: str, chapter: int, verse: int) -> str:
    book = book_meta(book_slug) or {}
    return f"{book.get('name', book_slug)} {chapter}:{verse}"

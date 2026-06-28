"""Load the COMPLETE Spiritual Exercises of St. Ignatius of Loyola
(Elder Mullan, 1914 — public domain) into MongoDB as a single embedded
library book, split section-by-section into full chapters.

Source: CCEL plain-text cache of the Mullan translation.

Usage:
    cd /app/backend && python -m scripts.load_spiritual_exercises
"""
from __future__ import annotations

import asyncio
import os
import re
import uuid
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

SLUG = "spiritual-exercises-ignatius"
SOURCE = "https://ccel.org/ccel/i/ignatius/exercises/cache/exercises.txt"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119 Safari/537.36"

INTRO_BODY = (
    "The *Spiritual Exercises* is the masterwork of St. Ignatius of Loyola "
    "(1491–1556), forged in the cave of Manresa after his conversion and "
    "refined over a lifetime. It is not a book to be merely read but a "
    "retreat to be *made* — a four-week journey of prayer, meditation, and "
    "the examination of conscience that has formed saints, popes, and "
    "millions of ordinary Christians for nearly five centuries.\n\n"
    "Ignatius arranges the journey in four 'Weeks' (movements, not calendar "
    "weeks):\n\n"
    "- **First Week** — the mercy of God and sorrow for sin; the soul is "
    "purified.\n"
    "- **Second Week** — walking with Christ in His public life; the Call of "
    "the King, the Two Standards, and the great work of *Election* — "
    "discerning God's will for one's life.\n"
    "- **Third Week** — accompanying Christ in His Passion.\n"
    "- **Fourth Week** — the joy of the Resurrection and the Contemplation to "
    "Gain Love.\n\n"
    "Woven through the whole are the famous **Rules for the Discernment of "
    "Spirits**, the **Three Times and Ways for Making a Choice**, and the "
    "**Mysteries of the Life of Christ** for daily contemplation.\n\n"
    "This is the complete text in the classic 1914 translation of Father "
    "Elder Mullan, S.J., made from Ignatius' own Spanish autograph. Read it "
    "slowly, prayerfully, and — if you can — under the guidance of a wise "
    "director. *Ad maiorem Dei gloriam.*"
)

# Ordered (anchor-line-uppercase, clean chapter title). The splitter finds the
# first standalone line equal to each anchor, in order, and slices between them.
ANCHORS = [
    ("ANNOTATIONS", "Annotations"),
    ("PRESUPPOSITION", "Presupposition"),
    ("PRINCIPLE AND FOUNDATION", "First Week — Principle and Foundation; the Examens"),
    ("FIRST EXERCISE", "First Week — The Five Exercises on Sin and Hell"),
    ("ADDITIONS", "First Week — The Ten Additions"),
    ("THE CALL OF THE TEMPORAL KING", "Second Week — The Call of the Temporal King"),
    ("THE INCARNATION", "Second Week — The Incarnation, Nativity and Contemplations"),
    ("TWO STANDARDS", "Second Week — Two Standards and Three Pairs of Men"),
    ("PRELUDE FOR MAKING ELECTION", "The Election — Making a Sound and Good Choice"),
    ("THIRD WEEK", "Third Week — The Passion of Christ"),
    ("FOURTH WEEK", "Fourth Week — The Resurrection"),
    ("CONTEMPLATION TO GAIN LOVE", "Contemplation to Gain Love"),
    ("THREE METHODS OF PRAYER", "Three Methods of Prayer"),
    ("THE MYSTERIES OF THE LIFE OF CHRIST OUR LORD", "The Mysteries of the Life of Christ Our Lord"),
    ("RULES", "Rules for the Discernment of Spirits"),
    ("IN THE MINISTRY OF DISTRIBUTING ALMS", "Rules for Distributing Alms"),
    ("THE FOLLOWING NOTES HELP TO PERCEIVE AND UNDERSTAND SCRUPLES", "Notes on Scruples"),
    ("TO HAVE THE TRUE SENTIMENT", "Rules for Thinking with the Church"),
]

END_MARKER = "GENERAL INDEX"


def _clean_block(block_lines: list[str]) -> str:
    """Join a chapter's lines into readable markdown: collapse blank runs and
    turn standalone ALL-CAPS sub-headings into bold lines."""
    out: list[str] = []
    for ln in block_lines:
        st = ln.strip()
        # Drop CCEL page separators / rule lines (rows of _ - = or *).
        if st and len(set(st)) <= 2 and st[0] in "_-=*~":
            continue
        if st and len(st) <= 60 and st == st.upper() and sum(c.isalpha() for c in st) >= 3 \
                and not st.endswith(",") and st.rstrip(".") == st.rstrip("."):
            # ALL-CAPS sub-heading line → bold, drop a trailing period for neatness
            label = st[:-1] if st.endswith(".") else st
            out.append(f"**{label.title()}**")
        else:
            out.append(st)
    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def split_chapters(raw: str) -> list[dict]:
    lines = raw.split("\n")

    def find(anchor: str, start: int) -> int:
        for i in range(start, len(lines)):
            if lines[i].strip() == anchor:
                return i
        return -1

    # body starts at the real ANNOTATIONS heading (after front-matter ~line 500)
    body_start = find("ANNOTATIONS", 500)
    if body_start < 0:
        body_start = find("ANNOTATIONS", 0)

    # locate each anchor in order, from body_start
    found: list[tuple[int, str]] = []
    cursor = body_start
    for anchor, title in ANCHORS:
        idx = find(anchor, cursor)
        if idx < 0:
            print(f"  ! anchor not found: {anchor}")
            continue
        found.append((idx, title))
        cursor = idx + 1

    # end of content
    end = find(END_MARKER, cursor)
    if end < 0:
        end = len(lines)

    chapters: list[dict] = [{"title": "Why This Matters", "body_md": INTRO_BODY}]
    for k, (idx, title) in enumerate(found):
        nxt = found[k + 1][0] if k + 1 < len(found) else end
        block = lines[idx + 1:nxt]  # drop the main heading line; keep sub-headings
        body = _clean_block(block)
        if body:
            chapters.append({"title": title, "body_md": body})
    return chapters


async def main() -> None:
    print(f"→ fetching {SOURCE}")
    async with httpx.AsyncClient(timeout=60, headers={"User-Agent": UA}) as cl:
        r = await cl.get(SOURCE)
        r.raise_for_status()
        raw = r.text
    chapters = split_chapters(raw)
    total_chars = sum(len(c["body_md"]) for c in chapters)
    print(f"  parsed {len(chapters)} chapters · ~{total_chars:,} chars")
    for c in chapters:
        print(f"    - {c['title']}  ({len(c['body_md']):,})")

    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    existing = await db["library_books"].find_one({"slug": SLUG}, {"book_id": 1})
    now = datetime.now(timezone.utc)
    doc = {
        "book_id": (existing or {}).get("book_id") or f"bk_{uuid.uuid4().hex[:10]}",
        "slug": SLUG,
        "title": "The Spiritual Exercises",
        "author": "St. Ignatius of Loyola",
        "year": 1548,
        "blurb": "The complete spiritual classic of St. Ignatius — a four-week retreat of prayer, meditation, and discernment, including the Rules for the Discernment of Spirits and the method of Election. Full 1914 Elder Mullan translation.",
        "tradition": "catholic-classic",
        "cover_color": "#1E3A5F",
        "cover_icon": "book",
        "type": "embedded",
        "source_url": "https://ccel.org/ccel/ignatius/exercises",
        "chapters": chapters,
        "status": "published",
        "created_at": (existing or {}).get("created_at") or now,
        "updated_at": now,
    }
    await db["library_books"].replace_one({"slug": SLUG}, doc, upsert=True)
    print(f"  ✓ wrote '{SLUG}' with {len(chapters)} chapters")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())

"""
Sanctus Library — Full-text book loader.

Downloads public-domain spiritual classics from Project Gutenberg and
parses them into chapters that are written into the existing
`library_books` documents in MongoDB.

Idempotent: running it multiple times simply overwrites the `chapters`
array for each handled slug.

Run it once after deploying or whenever the catalogue changes:

    python -m scripts.load_full_books              # update all known
    python -m scripts.load_full_books slug-1 slug-2  # selective

Each parser produces a `[{title: str, body_md: str}]` list.  Body is
already markdown-safe — paragraph breaks preserved, leading/trailing
whitespace stripped, and runs of soft line breaks rejoined into a single
paragraph (Gutenberg wraps prose at ~70 cols).
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
from typing import Callable, Dict, List, Optional

import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Allow this script to be executed as a module from /app/backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GUTENBERG = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"


# --------------------------------------------------------------------- #
# Helpers                                                               #
# --------------------------------------------------------------------- #
def _fetch_gutenberg(book_id: int) -> str:
    """Download a Project Gutenberg plain-text book and trim PG boilerplate."""
    r = requests.get(GUTENBERG.format(id=book_id), timeout=30)
    r.raise_for_status()
    text = r.text
    # Normalise line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Drop everything before "*** START OF" and after "*** END OF".
    m = re.search(r"\*\*\* START OF [^*]+\*\*\*\n", text)
    if m:
        text = text[m.end():]
    m = re.search(r"\n\*\*\* END OF [^*]+\*\*\*", text)
    if m:
        text = text[: m.start()]
    return text.strip()


def _paragraphize(raw: str) -> str:
    """Gutenberg wraps lines at ~70 chars.  Re-join wrapped lines into paragraphs.

    Preserves blank-line paragraph breaks. Leaves indented blocks (typically
    poetry / scripture) alone.
    """
    lines = raw.split("\n")
    paragraphs: List[List[str]] = [[]]
    for ln in lines:
        if ln.strip() == "":
            if paragraphs[-1]:
                paragraphs.append([])
            continue
        # Indented lines (4+ spaces) → keep on their own line (poetry/citation).
        if ln.startswith("    "):
            paragraphs.append([ln.strip()])
            paragraphs.append([])
            continue
        paragraphs[-1].append(ln.strip())

    out_parts: List[str] = []
    for p in paragraphs:
        if not p:
            continue
        joined = " ".join(p).strip()
        # Collapse runs of internal whitespace.
        joined = re.sub(r"\s+", " ", joined)
        out_parts.append(joined)
    return "\n\n".join(out_parts).strip()


def _slice(text: str, start: int, end: int) -> str:
    return _paragraphize(text[start:end].strip())


# --------------------------------------------------------------------- #
# Book parsers                                                          #
# --------------------------------------------------------------------- #
def parse_practice_presence(text: str) -> List[Dict[str, str]]:
    """Brother Lawrence — Practice of the Presence of God (Gutenberg 5657)."""
    # Drop everything before "First Conversation:".
    m = re.search(r"^First Conversation:", text, re.MULTILINE)
    if not m:
        raise RuntimeError("structure changed in Practice of Presence")
    body = text[m.start():]

    pattern = re.compile(
        r"^(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|"
        r"Eleventh|Twelfth|Thirteenth|Fourteenth|Fifteenth|Sixteenth) "
        r"(Conversation|Letter):",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(body))
    if not matches:
        raise RuntimeError("no chapter markers found in Practice of Presence")

    chapters: List[Dict[str, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        head = body[m.start(): body.find("\n", m.start())].strip()
        # Use the marker as a clean title (e.g. "First Conversation").
        title = f"{m.group(1)} {m.group(2)}"
        # Body starts AFTER the heading line.
        content_start = body.find("\n", start) + 1
        block = body[content_start: end]
        # Trim the leading heading echo from inside the block if present.
        chapters.append({
            "title": title,
            "subtitle": head[len(title) + 1:].strip(":").strip() if len(head) > len(title) else "",
            "body_md": _paragraphize(block),
        })
    return chapters


def parse_imitation_of_christ(text: str) -> List[Dict[str, str]]:
    """Thomas à Kempis — The Imitation of Christ (Gutenberg 1653)."""
    # The structure is:
    #   THE FIRST BOOK
    #   ADMONITIONS PROFITABLE FOR THE SPIRITUAL LIFE
    #   <blank>
    #   CHAPTER I
    #   <blank>
    #   Of the imitation of Christ ...
    #   <blank>
    #   <body>
    book_re = re.compile(r"^THE (FIRST|SECOND|THIRD|FOURTH) BOOK\b", re.MULTILINE)
    chap_re = re.compile(r"^CHAPTER\s+([IVXLCDM]+)\s*$", re.MULTILINE)

    book_marks = list(book_re.finditer(text))
    if len(book_marks) != 4:
        raise RuntimeError(f"Imitation: expected 4 BOOKs, got {len(book_marks)}")

    BOOK_NAMES = {
        "FIRST": "Book I — Admonitions Profitable for the Spiritual Life",
        "SECOND": "Book II — Admonitions Concerning the Inner Life",
        "THIRD": "Book III — On Inward Consolation",
        "FOURTH": "Book IV — On the Blessed Sacrament",
    }

    chapters: List[Dict[str, str]] = []
    for bi, bm in enumerate(book_marks):
        book_label = BOOK_NAMES[bm.group(1)]
        book_start = bm.start()
        book_end = book_marks[bi + 1].start() if bi + 1 < len(book_marks) else len(text)
        book_text = text[book_start:book_end]

        chap_marks = list(chap_re.finditer(book_text))
        for ci, cm in enumerate(chap_marks):
            ch_start = cm.start()
            ch_end = chap_marks[ci + 1].start() if ci + 1 < len(chap_marks) else len(book_text)
            ch_block = book_text[ch_start:ch_end]
            # Strip the "CHAPTER X" line.
            ch_block = re.sub(r"^CHAPTER\s+[IVXLCDM]+\s*\n+", "", ch_block, count=1)
            # First non-empty line is the chapter heading.
            lines = ch_block.split("\n", 1)
            heading = lines[0].strip()
            body = lines[1] if len(lines) > 1 else ""
            chapters.append({
                "title": f"{book_label.split(' — ')[0]} · Ch. {cm.group(1)}",
                "subtitle": heading,
                "body_md": _paragraphize(body),
            })
    return chapters


def parse_confessions(text: str) -> List[Dict[str, str]]:
    """Augustine — Confessions (Pusey trans., Gutenberg 3296).

    Confessions is divided into 13 BOOKs. Each contains many numbered
    paragraphs but no chapter headings within. We keep each BOOK as a
    single readable chapter to avoid splitting the prose mid-thought.
    """
    book_re = re.compile(r"^BOOK\s+([IVXLCDM]+)\s*\.?\s*$", re.MULTILINE)
    marks = list(book_re.finditer(text))
    if len(marks) < 10:
        raise RuntimeError(f"Confessions: only {len(marks)} BOOK markers found")
    chapters: List[Dict[str, str]] = []
    for i, m in enumerate(marks):
        start = m.start()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        block = re.sub(r"^BOOK\s+[IVXLCDM]+\s*\.?\s*\n+", "", text[start:end], count=1)
        chapters.append({
            "title": f"Book {m.group(1)}",
            "subtitle": "",
            "body_md": _paragraphize(block),
        })
    return chapters


def parse_story_of_a_soul(text: str) -> List[Dict[str, str]]:
    """St. Thérèse of Lisieux — Story of a Soul (Gutenberg 16772)."""
    # Pattern: "CHAPTER I" through "CHAPTER XI" + optional ALL-CAPS subtitle.
    # There's also a PROLOGUE (parentage and birth) and an EPILOGUE.
    chap_re = re.compile(r"^CHAPTER\s+([IVXLCDM]+)\b\s*([A-Z][A-Z' ,\-\.]+)?\s*$",
                         re.MULTILINE)
    # Find the start of the autobiography (after the table of contents).
    autobio = re.search(r"^AUTOBIOGRAPHY\s*$", text, re.MULTILINE)
    body = text[autobio.end():] if autobio else text

    marks = list(chap_re.finditer(body))
    if len(marks) < 8:
        raise RuntimeError(f"Story of a Soul: only {len(marks)} chapters found")

    # Hand-friendly subtitles (Gutenberg version uses different headings per chapter).
    SUBTITLES = {
        "I": "Earliest Memories",
        "II": "A Catholic Household",
        "III": "Pauline Enters the Carmel",
        "IV": "First Communion and Confirmation",
        "V": "Vocation of Thérèse",
        "VI": "A Pilgrimage to Rome",
        "VII": "The Little Flower Enters the Carmel",
        "VIII": "Profession of Sœur Thérèse",
        "IX": "The Night of the Soul",
        "X": "The New Commandment",
        "XI": "A Canticle of Love",
    }

    chapters: List[Dict[str, str]] = []
    for i, m in enumerate(marks):
        roman = m.group(1)
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        block = body[start:end].strip()
        # Skip any leading all-caps subtitle line that already appears at top.
        block = re.sub(r"^[A-Z][A-Z' ,\-\.]+\n+", "", block, count=1)
        # Stop at "EPILOGUE" if it appears in the last chapter block.
        if "EPILOGUE" in block:
            block = block.split("EPILOGUE")[0]
        chapters.append({
            "title": f"Chapter {roman}",
            "subtitle": SUBTITLES.get(roman, ""),
            "body_md": _paragraphize(block),
        })
    return chapters


def parse_abandonment(text: str) -> List[Dict[str, str]]:
    """Jean-Pierre de Caussade — Abandonment to Divine Providence (Gutenberg 52057)."""
    book_re = re.compile(r"^Book\s+(First|Second|Third|Fourth)\s*\.?\s*$", re.MULTILINE)
    marks = list(book_re.finditer(text))
    if len(marks) < 3:
        raise RuntimeError(f"Abandonment: only {len(marks)} Book markers found")
    # Capture any preface before Book First as an Introduction chapter.
    chapters: List[Dict[str, str]] = []
    if marks[0].start() > 200:
        pre = text[:marks[0].start()].strip()
        if pre:
            chapters.append({
                "title": "Foundational Principles",
                "subtitle": "Caussade's opening principles on self-abandonment",
                "body_md": _paragraphize(pre),
            })
    BOOK_TITLES = {
        "First": "On Self-Abandonment",
        "Second": "On the State of Self-Abandonment",
        "Third": "Various Counsels for Souls",
        "Fourth": "Letters of Direction",
    }
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        block = text[start:end].strip()
        chapters.append({
            "title": f"Book {m.group(1)}",
            "subtitle": BOOK_TITLES.get(m.group(1), ""),
            "body_md": _paragraphize(block),
        })
    return chapters


def parse_orthodoxy(text: str) -> List[Dict[str, str]]:
    """G.K. Chesterton — Orthodoxy (Gutenberg 130)."""
    # Drop everything before the PREFACE so the title page / TOC don't pollute.
    m = re.search(r"^PREFACE\s*$", text, re.MULTILINE)
    if not m:
        raise RuntimeError("Orthodoxy: PREFACE not found")
    body = text[m.start():]

    chapters: List[Dict[str, str]] = []

    # First, slice off the PREFACE up to the second ORTHODOXY title block.
    pref_end = re.search(r"^ORTHODOXY\s*$", body, re.MULTILINE)
    pref_block = body[len("PREFACE"):pref_end.start()] if pref_end else ""
    chapters.append({
        "title": "Preface",
        "subtitle": "Chesterton's preface to his apologetic.",
        "body_md": _paragraphize(pref_block),
    })

    # Chapter headings like:
    #   I INTRODUCTION IN DEFENCE OF EVERYTHING ELSE
    chap_re = re.compile(
        r"^(I|II|III|IV|V|VI|VII|VIII|IX)\s+([A-Z][A-Z' ,\-\.]{4,})$",
        re.MULTILINE,
    )
    # Restrict matches to AFTER the title block ("ORTHODOXY" on its own line).
    rest = body[pref_end.end():] if pref_end else body
    marks = list(chap_re.finditer(rest))
    if len(marks) < 8:
        raise RuntimeError(f"Orthodoxy: only {len(marks)} chapter markers found")
    for i, mm in enumerate(marks):
        start = mm.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(rest)
        block = rest[start:end].strip()
        chapters.append({
            "title": f"Chapter {mm.group(1)}",
            "subtitle": mm.group(2).strip().title(),
            "body_md": _paragraphize(block),
        })
    return chapters


# --------------------------------------------------------------------- #
# Registry — slug → (gutenberg id, parser)                              #
# --------------------------------------------------------------------- #
PARSERS: Dict[str, tuple[int, Callable[[str], List[Dict[str, str]]]]] = {
    "practice-presence-of-god": (5657, parse_practice_presence),
    "imitation-of-christ": (1653, parse_imitation_of_christ),
    "confessions-augustine": (3296, parse_confessions),
    "story-of-a-soul": (16772, parse_story_of_a_soul),
    "abandonment-divine-providence": (52057, parse_abandonment),
    "orthodoxy-chesterton": (130, parse_orthodoxy),
}


# --------------------------------------------------------------------- #
# Driver                                                                #
# --------------------------------------------------------------------- #
async def write_book(db, slug: str, chapters: List[Dict[str, str]]) -> None:
    res = await db["library_books"].update_one(
        {"slug": slug},
        {
            "$set": {
                "chapters": [
                    {"title": c["title"], "subtitle": c.get("subtitle", ""), "body_md": c["body_md"]}
                    for c in chapters
                ],
            }
        },
    )
    if res.matched_count == 0:
        print(f"  ! {slug}: no DB document — skipped")
    else:
        total_words = sum(len(c["body_md"].split()) for c in chapters)
        print(f"  ✓ {slug}: wrote {len(chapters)} chapters · ~{total_words:,} words")


async def main(slugs: Optional[List[str]] = None) -> None:
    targets = slugs or list(PARSERS.keys())
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ.get("DB_NAME", "sanctus")]
    for slug in targets:
        if slug not in PARSERS:
            print(f"  ? {slug}: no parser registered — skipped")
            continue
        book_id, parser = PARSERS[slug]
        print(f"→ {slug} (Gutenberg #{book_id})")
        text = _fetch_gutenberg(book_id)
        chapters = parser(text)
        await write_book(db, slug, chapters)


if __name__ == "__main__":
    args = sys.argv[1:]
    asyncio.run(main(args or None))

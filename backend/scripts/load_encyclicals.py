"""
Load 5 Catholic encyclicals (Vatican.va English HTML) into MongoDB as embedded
library books. Each book opens with a short "Why This Matters" summary chapter
written by us, then continues with the full Vatican text split by Roman-numeral
sections (or by ~6K-character chunks if no Roman sections are present).

Usage:
    cd /app/backend && python -m scripts.load_encyclicals [slug ...]

If no slug is given, all five encyclicals are loaded.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Callable, Dict, List

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119 Safari/537.36"

# ---------------------------------------------------------------------------
# 1. Per-book summary chapters (why each encyclical matters)
# ---------------------------------------------------------------------------

SUMMARY_CHAPTERS: Dict[str, Dict[str, str]] = {
    "magnifica-humanitas": {
        "title": "Why This Matters",
        "subtitle": "A reader's introduction",
        "body_md": (
            "Magnifica Humanitas — 'Magnificent Humanity' — is the first "
            "encyclical of Pope Leo XIV, signed on 15 May 2026. Written into "
            "the rising shadow of artificial intelligence, it asks the most "
            "Catholic of questions in a new key: what is the human person, and "
            "what does it cost the world if we forget?\n\n"
            "The Holy Father refuses two extremes. He does not condemn the new "
            "technologies, nor does he baptize them. He instead calls the "
            "Church and the human family to a sober defense of the imago Dei "
            "— the truth that every person is willed by God, irreducible to a "
            "data point, and ordered to eternal life. AI, he writes, is a "
            "powerful instrument that must remain instrument; whenever the "
            "machine begins to set the measure of the human, the measure "
            "itself has been corrupted.\n\n"
            "This document matters because it is the first major Magisterial "
            "act on artificial intelligence written from within the heart of "
            "the Church's anthropology. It draws a direct line from Genesis "
            "1:27 through Gaudium et Spes 22 and Laudato Si' to the moral "
            "questions every Catholic is now facing in school, work, "
            "medicine, war, and prayer. It belongs on the desk of every "
            "engineer, parent, pastor, and pilgrim.\n\n"
            "Read it slowly. Pope Leo writes in the great encyclical tradition "
            "— numbered paragraphs, theological grounding, then a pastoral "
            "summons. He is not afraid of the future. He is asking us to "
            "remember who we are before we build it."
        ),
    },
    "veritatis-splendor": {
        "title": "Why This Matters",
        "subtitle": "A reader's introduction",
        "body_md": (
            "Veritatis Splendor — 'The Splendor of Truth' — was promulgated by "
            "St. John Paul II on 6 August 1993, the Feast of the "
            "Transfiguration. It is widely regarded as one of the most "
            "important moral encyclicals in modern history.\n\n"
            "The encyclical responds to a crisis in Catholic moral theology "
            "after the Second Vatican Council: certain currents had begun to "
            "deny that there are any moral acts intrinsically evil — that is, "
            "wrong always, everywhere, and for everyone, regardless of "
            "circumstance or intention. John Paul II answers with the great "
            "patrimony of the Church: there are absolute moral norms, and the "
            "human conscience is not its own lawgiver but a servant of the "
            "truth.\n\n"
            "Built around the Gospel encounter of the rich young man (Mt 19), "
            "the encyclical re-centers Catholic morality on the call of Christ "
            "and the dignity of the human person. It is essential reading for "
            "any Catholic who wants to understand why the Church teaches what "
            "she teaches on questions of life, sexuality, justice, and "
            "freedom — and why she cannot teach otherwise without ceasing to "
            "be herself.\n\n"
            "Veritatis Splendor is dense but not cold. John Paul II writes as "
            "a pastor convinced that the moral life is not a cage but a road "
            "to joy — and that the splendor of the truth, far from crushing "
            "human freedom, is what finally sets it free."
        ),
    },
    "centesimus-annus": {
        "title": "Why This Matters",
        "subtitle": "A reader's introduction",
        "body_md": (
            "Centesimus Annus — 'The Hundredth Year' — was promulgated by St. "
            "John Paul II on 1 May 1991, on the centenary of Leo XIII's "
            "landmark social encyclical Rerum Novarum. It is the most "
            "important Catholic statement on economics, work, and politics in "
            "the wake of the fall of communism.\n\n"
            "Writing months after the Berlin Wall fell, John Paul II reads "
            "1989 as a moral event before it is an economic one. The collapse "
            "of Marxist atheism is a vindication of the human person against "
            "every system that tries to reduce him to a function of the "
            "state. But the Holy Father refuses any uncritical embrace of "
            "Western capitalism in its place. A free economy, yes — but only "
            "one circumscribed by truth, law, ethics, and the common good.\n\n"
            "Centesimus Annus matters because it gives the Catholic her "
            "framework for thinking about the modern economic order: a "
            "principled defense of private property, free enterprise, and "
            "subsidiarity, alongside an uncompromising critique of "
            "consumerism, exploitation, and the marginalization of the poor. "
            "It is required reading for Catholic voters, workers, employers, "
            "and citizens of a market culture.\n\n"
            "Above all it is a hopeful document. John Paul II believed that "
            "the human person, rightly seen, is a builder — capable, with "
            "grace, of a civilization of love."
        ),
    },
    "humanae-vitae": {
        "title": "Why This Matters",
        "subtitle": "A reader's introduction",
        "body_md": (
            "Humanae Vitae — 'Of Human Life' — was promulgated by Pope Paul "
            "VI on 25 July 1968. Few encyclicals have been so contested in "
            "their own day or so vindicated by time.\n\n"
            "On the cusp of the sexual revolution, the Holy Father reaffirmed "
            "the constant teaching of the Church on the transmission of human "
            "life: the unitive and procreative meanings of the marital act "
            "may not be sundered, and contraception is therefore intrinsically "
            "disordered. He also predicted — with sobering accuracy — what "
            "would happen to marriage, family, women, and society at large if "
            "those meanings were severed at scale.\n\n"
            "Humanae Vitae matters because it is not a private rule for "
            "Catholic couples. It is a defense of the human person — of "
            "the body as sacramental, of sexuality as covenantal, of children "
            "as gift rather than product. It is the seedbed of St. John Paul "
            "II's Theology of the Body and of the modern Catholic vision of "
            "love.\n\n"
            "Read it as a love letter to married couples: short, prophetic, "
            "and deeply pastoral. It calls us not to less love, but to more — "
            "a love willing to receive whom God gives, in the freedom that "
            "comes from chastity, and in the joy of a fruitful covenant."
        ),
    },
    "evangelii-nuntiandi": {
        "title": "Why This Matters",
        "subtitle": "A reader's introduction",
        "body_md": (
            "Evangelii Nuntiandi — 'On Evangelization in the Modern World' — "
            "was issued by Pope Paul VI on 8 December 1975, the tenth "
            "anniversary of the close of the Second Vatican Council. It is "
            "an Apostolic Exhortation rather than an encyclical strictly so "
            "called, but it is so foundational to modern Catholic missionary "
            "life that it belongs in every Catholic library.\n\n"
            "Pope Paul VI declares with apostolic force that the Church "
            "exists in order to evangelize. Evangelization is not a "
            "department of the Church's work; it is her very vocation. He "
            "describes evangelization as the proclamation of Jesus Christ as "
            "Savior, the witness of holy lives, the inculturation of the "
            "Gospel in every culture, and the transformation of the world "
            "from within by the leaven of the Beatitudes.\n\n"
            "This document matters because it shaped the great missionary "
            "vision of St. John Paul II ('the New Evangelization'), Pope "
            "Benedict XVI ('the joy of the truth'), and Pope Francis "
            "('missionary disciples'). It is the Magna Carta of the modern "
            "Catholic call to share Christ with the world.\n\n"
            "Read it especially if you have ever doubted that ordinary "
            "Catholics — by their families, their work, their friendships, "
            "their parishes — are called to be evangelists. Paul VI insists: "
            "modern man listens more willingly to witnesses than to teachers, "
            "and if he listens to teachers it is because they are witnesses."
        ),
    },
    "gaudete-et-exsultate": {
        "title": "Why This Matters",
        "subtitle": "A reader's introduction",
        "body_md": (
            "Gaudete et Exsultate — 'Rejoice and Be Glad' — was issued by "
            "Pope Francis on 19 March 2018. It is the Holy Father's call to "
            "holiness for ordinary people: not heroic monks alone, but "
            "parents, workers, the sick, and the young — 'the saints next "
            "door.'\n\n"
            "For anyone seeking spiritual discernment, the heart of this "
            "document is Chapter Five: 'Spiritual Combat, Vigilance and "
            "Discernment.' There Pope Francis gives one of the clearest "
            "modern guides to discerning the movements of the heart — how to "
            "tell the voice of the Lord from the voice of the world, our own "
            "ego, or the evil one. He insists discernment is not for experts "
            "only; it is 'a gift which we must implore,' a daily habit of "
            "listening that keeps us docile to the Holy Spirit.\n\n"
            "This document matters because it translates the great Ignatian "
            "and mystical tradition of discernment into plain, pastoral "
            "language for lay people. It teaches that God speaks in the "
            "ordinary, that holiness grows in small steps, and that the "
            "Christian must remain awake — neither paralysed by fear nor "
            "naive about the real spiritual battle.\n\n"
            "Read Chapter Five slowly. It is short, practical, and meant to "
            "be returned to whenever you face a decision and ask, 'Lord, what "
            "do you want of me?'"
        ),
    },
    "christus-vivit": {
        "title": "Why This Matters",
        "subtitle": "A reader's introduction",
        "body_md": (
            "Christus Vivit — 'Christ is Alive' — was signed by Pope Francis "
            "on 25 March 2019, the Solemnity of the Annunciation, as the "
            "fruit of the Synod on Young People, Faith and Vocational "
            "Discernment.\n\n"
            "Though addressed to the young, its closing chapters are a gift "
            "to anyone discerning their path in life. Chapter Eight, "
            "'Vocation,' and Chapter Nine, 'Discernment,' lay out how to "
            "recognise God's call: through prayer, the reading of one's own "
            "interior movements, the counsel of a wise guide, and the "
            "patient testing of where true and lasting peace is found. Pope "
            "Francis warns against the noise and haste that smother the "
            "voice of God, and teaches that every state of life — marriage, "
            "priesthood, consecrated or single life, and one's daily work — "
            "is a genuine vocation.\n\n"
            "This document matters because it gives lay people a warm, "
            "practical framework for the biggest decisions of life. It "
            "presents discernment not as anxious self-analysis but as a "
            "loving conversation with the God who already knows and wants "
            "our happiness.\n\n"
            "Read it whenever you stand at a crossroads and want to choose, "
            "not merely what is good, but what God is asking of you in love."
        ),
    },
}


# ---------------------------------------------------------------------------
# 2. Book metadata + Vatican.va URL
# ---------------------------------------------------------------------------

BOOKS: Dict[str, Dict] = {
    "magnifica-humanitas": {
        "title": "Magnifica Humanitas",
        "author": "Pope Leo XIV",
        "year": 2026,
        "blurb": "Pope Leo XIV's first encyclical (2026) on safeguarding the human person in the age of artificial intelligence.",
        "tradition": "papal",
        "cover_color": "#0F172A",
        "cover_icon": "shield-checkmark-outline",
        "url": "https://www.vatican.va/content/leo-xiv/en/encyclicals/documents/20260515-magnifica-humanitas.html",
    },
    "veritatis-splendor": {
        "title": "Veritatis Splendor",
        "author": "Pope St. John Paul II",
        "year": 1993,
        "blurb": "The 1993 encyclical on the foundations of Catholic moral teaching — the splendor of the truth that sets us free.",
        "tradition": "papal",
        "cover_color": "#7C2D12",
        "cover_icon": "sunny-outline",
        "url": "https://www.vatican.va/content/john-paul-ii/en/encyclicals/documents/hf_jp-ii_enc_06081993_veritatis-splendor.html",
    },
    "centesimus-annus": {
        "title": "Centesimus Annus",
        "author": "Pope St. John Paul II",
        "year": 1991,
        "blurb": "The 1991 social encyclical marking the centennial of Rerum Novarum — a moral framework for the post-Cold-War world.",
        "tradition": "papal",
        "cover_color": "#1E3A8A",
        "cover_icon": "people-outline",
        "url": "https://www.vatican.va/content/john-paul-ii/en/encyclicals/documents/hf_jp-ii_enc_01051991_centesimus-annus.html",
    },
    "humanae-vitae": {
        "title": "Humanae Vitae",
        "author": "Pope St. Paul VI",
        "year": 1968,
        "blurb": "The 1968 encyclical defending the transmission of human life and the integrity of married love.",
        "tradition": "papal",
        "cover_color": "#9F1239",
        "cover_icon": "heart-outline",
        "url": "https://www.vatican.va/content/paul-vi/en/encyclicals/documents/hf_p-vi_enc_25071968_humanae-vitae.html",
    },
    "evangelii-nuntiandi": {
        "title": "Evangelii Nuntiandi",
        "author": "Pope St. Paul VI",
        "year": 1975,
        "blurb": "The 1975 apostolic exhortation on evangelization in the modern world — the Magna Carta of the New Evangelization.",
        "tradition": "papal",
        "cover_color": "#365314",
        "cover_icon": "megaphone-outline",
        "url": "https://www.vatican.va/content/paul-vi/en/apost_exhortations/documents/hf_p-vi_exh_19751208_evangelii-nuntiandi.html",
    },
    "gaudete-et-exsultate": {
        "title": "Gaudete et Exsultate",
        "author": "Pope Francis",
        "year": 2018,
        "blurb": "Pope Francis' call to holiness in today's world — including a clear, practical guide to spiritual discernment for everyday Christians (Chapter 5).",
        "tradition": "papal",
        "cover_color": "#15803D",
        "cover_icon": "compass-outline",
        "url": "https://www.vatican.va/content/francesco/en/apost_exhortations/documents/papa-francesco_esortazione-ap_20180319_gaudete-et-exsultate.html",
    },
    "christus-vivit": {
        "title": "Christus Vivit",
        "author": "Pope Francis",
        "year": 2019,
        "blurb": "'Christ is Alive!' — Pope Francis on vocation and discernment, helping lay people recognise God's call and choose their path in life.",
        "tradition": "papal",
        "cover_color": "#B45309",
        "cover_icon": "navigate-outline",
        "url": "https://www.vatican.va/content/francesco/en/apost_exhortations/documents/papa-francesco_esortazione-ap_20190325_christus-vivit.html",
    },
}


# ---------------------------------------------------------------------------
# 3. Parsing helpers
# ---------------------------------------------------------------------------

ROMAN_SECTION_RE = re.compile(
    r"^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV)\.\s+(.{4,})\s*$"
)
CHAPTER_WORD_RE = re.compile(
    r"^CHAPTER\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\b\s*(.*)$",
    re.IGNORECASE,
)
SINGLETON_HEADERS = {
    "INTRODUCTION",
    "CONCLUSION",
    "PREAMBLE",
    "PROLOGUE",
    "EPILOGUE",
    "FOREWORD",
}
NUMERIC_BULLET_RE = re.compile(r"^(\d{1,3})\.\s+")


def _clean(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s


def _detect_header(text: str) -> tuple[str, str] | None:
    """If `text` is a chapter/section header, return (title, subtitle).
    Subtitle may be empty (the caller will look at the next paragraph)."""
    if not text:
        return None

    # Singleton ALL-CAPS section words.
    if text.upper() in SINGLETON_HEADERS:
        return (text.title(), "")

    # CHAPTER ONE [optional inline name]
    m = CHAPTER_WORD_RE.match(text)
    if m:
        num = m.group(1).title()  # one → One, II → Ii (we fix below)
        # If the captured token is a Roman numeral (no vowels with lowercase
        # mix), uppercase it; otherwise keep title-case for English words.
        if re.fullmatch(r"[IVX]+", m.group(1).upper()):
            num = m.group(1).upper()
        rest = (m.group(2) or "").strip(" -—:.")
        return (f"Chapter {num}", rest.title() if rest else "")

    # Roman numeral header  ("I. CHARACTERISTICS OF ...")
    m = ROMAN_SECTION_RE.match(text)
    if m:
        roman = m.group(1)
        name = m.group(2).strip(" -—:.\"")
        # Reject lookalikes that are actually scripture refs like "I. John 1:2".
        if any(ch.isdigit() for ch in name[:30]):
            # Allow numbers later in the title but not as scripture refs.
            pass
        return (f"Part {roman}", name.title())

    return None


def _is_subhead(text: str) -> bool:
    """Short, no numeric bullet, doesn't end with sentence punctuation — likely
    a subheader (e.g. 'Married Love', 'God's Loving Design')."""
    if len(text) > 90 or len(text) < 3:
        return False
    if NUMERIC_BULLET_RE.match(text):
        return False
    if text.endswith((".", "?", "!")):
        return False
    if _detect_header(text):
        return False
    # If most words are capitalized, treat as a heading.
    words = text.split()
    cap = sum(1 for w in words if w[:1].isupper())
    return cap / max(len(words), 1) >= 0.5


def _vatican_paragraphs(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one(".documento") or soup
    paragraphs: List[str] = []
    for p in main.find_all("p"):
        txt = _clean(p.get_text(" "))
        if not txt:
            continue
        # Skip the translation language switcher.
        if txt.startswith("DE - EN") or "ZH_TW" in txt:
            continue
        # Skip footnote-only lines (vatican uses (1), (2) etc).
        if len(txt) < 4:
            continue
        paragraphs.append(txt)
    return paragraphs


def _chunk_into_chapters(paragraphs: List[str], book_title: str) -> List[Dict[str, str]]:
    """Group paragraphs into chapters using detected chapter/section headers
    when present; if absent, fall back to ~6,500-char chunks. If a header
    paragraph has no inline subtitle, the next short heading-looking
    paragraph is consumed as the subtitle."""

    # First pass: find every header position and stitch on a subtitle from the
    # following paragraph(s) when the header itself didn't carry one inline.
    sections: List[tuple[int, str, str]] = []  # (paragraph_index, title, subtitle)
    consumed: set[int] = set()

    for i, p in enumerate(paragraphs):
        if i in consumed:
            continue
        hdr = _detect_header(p)
        if not hdr:
            continue
        title, subtitle = hdr
        consumed.add(i)
        # If subtitle is empty, peek ahead at the next 1-2 paragraphs.
        # ALL-CAPS/title-cased short lines that come immediately after a
        # bare header (e.g. "CHAPTER ONE" → "A DYNAMIC APPROACH ...") are
        # the real chapter name.
        if not subtitle:
            extras: List[str] = []
            j = i + 1
            while j < len(paragraphs) and j - i <= 3:
                nxt = paragraphs[j]
                if _is_subhead(nxt) or (nxt.isupper() and len(nxt) < 120):
                    extras.append(nxt)
                    consumed.add(j)
                    j += 1
                else:
                    break
            subtitle = " ".join(extras).strip(" -—.").title()
        sections.append((i, title, subtitle))

    if not sections:
        # No headers detected — fall back to size-based chunks.
        return _chunk_by_size(paragraphs)

    chapters: List[Dict[str, str]] = []

    # Front matter: everything before the first detected header (greeting,
    # encyclical addressee, etc.) becomes "Introduction" unless the first
    # detected header IS the Introduction.
    first_idx = sections[0][0]
    if first_idx > 0 and sections[0][1].lower() != "introduction":
        front = [p for k, p in enumerate(paragraphs[:first_idx]) if k not in consumed]
        # Drop document-title block if it's the very first ALL-CAPS run.
        while front and front[0].isupper() and len(front[0]) > 80:
            front = front[1:]
        if front:
            chapters.append({
                "title": "Preface",
                "subtitle": "",
                "body_md": _assemble(front),
            })

    for k, (start, title, subtitle) in enumerate(sections):
        end = sections[k + 1][0] if k + 1 < len(sections) else len(paragraphs)
        body_paras = [p for j, p in enumerate(paragraphs[start + 1 : end], start=start + 1) if j not in consumed]
        chapters.append({
            "title": title,
            "subtitle": subtitle,
            "body_md": _assemble(body_paras),
        })

    # Drop any chapter that ended up effectively empty (signature blocks etc).
    return [c for c in chapters if len(c["body_md"]) > 40]


def _chunk_by_size(paragraphs: List[str]) -> List[Dict[str, str]]:
    CHUNK = 6500
    chapters: List[Dict[str, str]] = []
    buf: List[str] = []
    total = 0
    n = 1
    for para in paragraphs:
        buf.append(para)
        total += len(para)
        if total >= CHUNK:
            chapters.append({
                "title": f"Part {n}",
                "subtitle": "",
                "body_md": _assemble(buf),
            })
            n += 1
            buf, total = [], 0
    if buf:
        chapters.append({
            "title": f"Part {n}",
            "subtitle": "",
            "body_md": _assemble(buf),
        })
    return chapters


def _assemble(paragraphs: List[str]) -> str:
    """Render a list of paragraphs into our reader's body_md format. We give
    subheaders an empty line of breathing room and keep numbered paragraphs
    bold-feeling by leaving their numeric prefix intact."""
    lines: List[str] = []
    for p in paragraphs:
        if _is_subhead(p):
            lines.append("")  # extra spacing before subhead
            lines.append(p)
            lines.append("")
        else:
            lines.append(p)
            lines.append("")
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Manual outlines for encyclicals whose HTML lacks chapter markers.
# Keys are paragraph numbers (1-based) where a new chapter begins.
# ---------------------------------------------------------------------------

MANUAL_OUTLINES: Dict[str, List[tuple[int, str, str]]] = {
    # Evangelii Nuntiandi — vatican.va prints the document as flat numbered
    # paragraphs (no section <h*> markers). Outline per the official Latin
    # Editio Typica / printed editions.
    "evangelii-nuntiandi": [
        (1,  "Introduction",        ""),
        (6,  "Part I",   "From Christ the Evangelizer to the Evangelizing Church"),
        (17, "Part II",  "What Is Evangelization?"),
        (25, "Part III", "The Content of Evangelization"),
        (40, "Part IV",  "The Methods of Evangelization"),
        (49, "Part V",   "The Beneficiaries of Evangelization"),
        (59, "Part VI",  "The Workers for Evangelization"),
        (74, "Part VII", "The Spirit of Evangelization"),
        (81, "Conclusion", "A Word of Exhortation"),
    ],
}


def _chunk_by_outline(paragraphs: List[str], outline: List[tuple[int, str, str]]) -> List[Dict[str, str]]:
    """Group flat numbered paragraphs (e.g. '1. The...', '2. ...') into
    chapters at the paragraph indices specified by `outline`. Only honors a
    numeric bullet if it monotonically advances from the previous one — this
    avoids treating scripture references or footnotes like '(6. ...)' or
    incidental '6. ...' as paragraph numbers."""
    bucket_starts = {start: (title, sub) for start, title, sub in outline}
    chapters: List[Dict[str, str]] = []
    current_title: str | None = None
    current_sub = ""
    current_para_list: List[str] = []
    last_num = 0

    def flush():
        if current_title is not None and current_para_list:
            chapters.append({
                "title": current_title,
                "subtitle": current_sub,
                "body_md": _assemble(current_para_list),
            })

    for p in paragraphs:
        m = NUMERIC_BULLET_RE.match(p)
        is_real_bullet = False
        if m:
            n = int(m.group(1))
            # Only accept as a real paragraph marker if it advances strictly
            # forward and stays within a reasonable jump (≤ 5).
            if n == last_num + 1 or (n > last_num and n - last_num <= 5):
                is_real_bullet = True
                last_num = n
                if n in bucket_starts:
                    if current_title is not None:
                        flush()
                    current_title, current_sub = bucket_starts[n]
                    current_para_list = []
        if current_title is None:
            current_title = "Preface"
            current_sub = ""
        current_para_list.append(p)

    flush()
    return [c for c in chapters if len(c["body_md"]) > 40]




async def _fetch(url: str) -> str:
    async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True, timeout=30) as cli:
        r = await cli.get(url)
        r.raise_for_status()
        return r.text


async def _load(slug: str, meta: Dict, db) -> None:
    print(f"→ {slug}  ({meta['url']})")
    html = await _fetch(meta["url"])
    paragraphs = _vatican_paragraphs(html)

    if slug in MANUAL_OUTLINES:
        chapters = _chunk_by_outline(paragraphs, MANUAL_OUTLINES[slug])
    else:
        chapters = _chunk_into_chapters(paragraphs, meta["title"])

    # Collapse TOC ghost chapters: when two chapters share the same title and
    # one is very small (< 1500 chars), drop the small one. This handles
    # Magnifica Humanitas which prints a top-of-document Table of Contents
    # consisting of the same chapter titles as later headers.
    chapters = _dedupe_toc(chapters)

    # Prepend the editorial "Why This Matters" summary chapter.
    summary = SUMMARY_CHAPTERS[slug]
    chapters = [summary] + chapters

    now = datetime.now(timezone.utc)
    doc = {
        "book_id": str(uuid.uuid4()),
        "slug": slug,
        "title": meta["title"],
        "author": meta["author"],
        "year": meta["year"],
        "blurb": meta["blurb"],
        "tradition": meta["tradition"],
        "cover_color": meta["cover_color"],
        "cover_icon": meta["cover_icon"],
        "type": "embedded",
        "status": "published",
        "source_url": meta["url"],
        "chapters": chapters,
        "created_at": now,
        "updated_at": now,
    }

    existing = await db["library_books"].find_one({"slug": slug}, {"book_id": 1})
    if existing and existing.get("book_id"):
        doc["book_id"] = existing["book_id"]
        doc.pop("created_at", None)

    await db["library_books"].replace_one({"slug": slug}, doc, upsert=True)

    total_chars = sum(len(c["body_md"]) for c in chapters)
    print(f"  ✓ wrote {len(chapters)} chapters · ~{total_chars:,} chars")


def _dedupe_toc(chapters: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Drop the first ('TOC-like') occurrence when the same (title, subtitle)
    appears twice and the first instance has < 1500 chars of body."""
    keep: List[Dict[str, str]] = []
    # Group by (title, subtitle).
    from collections import defaultdict
    seen: Dict[tuple, List[int]] = defaultdict(list)
    for i, c in enumerate(chapters):
        seen[(c["title"], c["subtitle"])].append(i)

    drop = set()
    for key, idxs in seen.items():
        if len(idxs) < 2:
            continue
        # Drop the small leading instance(s).
        for j in idxs[:-1]:
            if len(chapters[j]["body_md"]) < 1500:
                drop.add(j)
    return [c for i, c in enumerate(chapters) if i not in drop]


async def main(slugs: List[str] | None = None) -> None:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ.get("DB_NAME", "sanctus")]
    targets = slugs or list(BOOKS.keys())
    for slug in targets:
        if slug not in BOOKS:
            print(f"  ⚠ unknown slug: {slug}")
            continue
        try:
            await _load(slug, BOOKS[slug], db)
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {slug}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    args = sys.argv[1:]
    asyncio.run(main(args or None))

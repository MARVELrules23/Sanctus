"""Daily Mass readings — multi-source fetcher.

USCCB (https://bible.usccb.org) is the official U.S. lectionary publisher but
their Varnish bot protection currently rejects all our automated requests
(403). We use a tiered strategy:

1.  **Universalis** (https://universalis.com) JSONP endpoint — reliable, live
    readings for *today* in the USA lectionary. Free for today only.
2.  **USCCB** scrape via curl_cffi browser impersonation — best-effort for
    historical/future dates. Usually fails but cached if it succeeds.
3.  **AI fallback** (Claude Sonnet 4.5 via Emergent LLM key) — citations only,
    no scripture text. Marked as `ai-suggested` in the response.

Citations + a short excerpt are returned. Full text is never redistributed —
the frontend always links to USCCB for the complete official reading.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import date, datetime, timezone
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup
from curl_cffi import requests as cfreq

logger = logging.getLogger("sanctus.readings")

_BROWSER_PROFILES = ("chrome116", "safari17_0", "chrome", "firefox133")
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15"
)


def usccb_url_for(d: date) -> str:
    return f"https://bible.usccb.org/bible/readings/{d.strftime('%m%d%y')}.cfm"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _strip_html(html: str) -> str:
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return _norm(text)


def _excerpt(s: str, n: int = 280) -> str:
    s = _norm(s)
    if len(s) <= n:
        return s
    cut = s[:n]
    last_space = cut.rfind(" ")
    if last_space > n - 40:
        cut = cut[:last_space]
    return cut + "…"


# ---------- Source 1: Universalis (today only, USA lectionary) ----------
async def _fetch_universalis_today() -> Optional[dict]:
    url = "https://universalis.com//USA/today/jsonpmass.js"
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as c:
            r = await c.get(url, headers={"User-Agent": _USER_AGENT})
        if r.status_code != 200 or len(r.text) < 200:
            return None
    except Exception as e:  # noqa: BLE001
        logger.warning("universalis fetch failed: %s", e)
        return None

    # Strip the JSONP wrapper: universalisCallback({...});
    body = r.text.strip()
    m = re.match(r"\s*\w+\s*\((.*)\)\s*;?\s*$", body, re.DOTALL)
    if not m:
        logger.warning("universalis JSONP unwrap failed")
        return None
    try:
        data: dict[str, Any] = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        logger.warning("universalis JSON parse failed: %s", e)
        return None

    def section(key: str) -> tuple[str, str, str]:
        node = data.get(key) or {}
        if not isinstance(node, dict):
            return "", "", ""
        src = _norm(_strip_html(str(node.get("source", "") or "")))
        body_html = str(node.get("text", "") or "")
        body_txt = _strip_html(body_html)
        return src, _excerpt(body_txt), body_txt

    r1_src, r1_exc, r1_full = section("Mass_R1")
    ps_src, ps_exc, ps_full = section("Mass_Ps")
    r2_src, r2_exc, r2_full = section("Mass_R2")
    acc_src, acc_exc, acc_full = section("Mass_GA")
    gos_src, gos_exc, gos_full = section("Mass_G")

    # 'day' field has HTML for the title (e.g. "Pentecost Sunday")
    day_title = _strip_html(str(data.get("day", "") or ""))

    if not (gos_src or r1_src):
        logger.warning("universalis returned without readings")
        return None

    return {
        "url": "",  # filled by caller with USCCB url for cross-reference
        "liturgical_title": day_title,
        "first_reading": r1_src,
        "first_reading_excerpt": r1_exc,
        "first_reading_full": r1_full,
        "psalm": ps_src,
        "psalm_excerpt": ps_exc,
        "psalm_full": ps_full,
        "second_reading": r2_src,
        "second_reading_excerpt": r2_exc,
        "second_reading_full": r2_full,
        "gospel_acclamation": acc_src or "Alleluia",
        "gospel_acclamation_excerpt": acc_exc,
        "gospel_acclamation_full": acc_full,
        "gospel": gos_src,
        "gospel_excerpt": gos_exc,
        "gospel_full": gos_full,
    }


# ---------- Source 2: USCCB scrape via curl_cffi ----------
def _section_match(header: str, *needles: str) -> bool:
    h = header.lower()
    return any(needle in h for needle in needles)


async def _fetch_usccb_html(url: str) -> Optional[str]:
    for prof in _BROWSER_PROFILES:
        try:
            async with cfreq.AsyncSession(impersonate=prof) as s:
                r = await s.get(url, timeout=15)
            if r.status_code == 200 and len(r.text) > 25000 and "lectionary" in r.text.lower():
                logger.info("usccb fetched %s via %s", url, prof)
                return r.text
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(0.3)
    return None


async def _fetch_usccb(d: date) -> Optional[dict]:
    url = usccb_url_for(d)
    html = await _fetch_usccb_html(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    liturgical_title = ""
    if title_tag:
        liturgical_title = _norm(title_tag.get_text(" ", strip=True)).split("|")[0].strip()

    slots = {
        "first_reading": {"citation": "", "excerpt": ""},
        "psalm": {"citation": "", "excerpt": ""},
        "second_reading": {"citation": "", "excerpt": ""},
        "gospel_acclamation": {"citation": "", "excerpt": ""},
        "gospel": {"citation": "", "excerpt": ""},
    }

    for container in soup.find_all(class_="container"):
        name = container.find(class_="name")
        address = container.find(class_="address")
        body = container.find(class_="content-body")
        if not name or not address:
            continue
        header = _norm(name.get_text(" ", strip=True))
        anchor = address.find("a")
        citation = _norm((anchor or address).get_text(" ", strip=True))
        excerpt = ""
        if body:
            ptexts = []
            for p in body.find_all(["p"], limit=4):
                t = _norm(p.get_text(" ", strip=True))
                if t and not t.lower().startswith(("r.", "—", "©")):
                    ptexts.append(t)
                if len(ptexts) >= 2:
                    break
            if not ptexts:
                ptexts = [_norm(body.get_text(" ", strip=True))]
            excerpt = _excerpt(" ".join(ptexts))

        target = None
        if _section_match(header, "reading 1", "first reading", "reading i"):
            target = "first_reading"
        elif _section_match(header, "psalm", "responsorial"):
            target = "psalm"
        elif _section_match(header, "reading 2", "second reading", "reading ii"):
            target = "second_reading"
        elif _section_match(header, "alleluia", "verse before the gospel", "gospel acclamation"):
            target = "gospel_acclamation"
        elif _section_match(header, "gospel"):
            target = "gospel"
        if target and not slots[target]["citation"]:
            slots[target]["citation"] = citation
            slots[target]["excerpt"] = excerpt

    if not (slots["gospel"]["citation"] or slots["first_reading"]["citation"]):
        return None
    return {
        "url": url,
        "liturgical_title": liturgical_title,
        "first_reading": slots["first_reading"]["citation"],
        "first_reading_excerpt": slots["first_reading"]["excerpt"],
        "psalm": slots["psalm"]["citation"],
        "psalm_excerpt": slots["psalm"]["excerpt"],
        "second_reading": slots["second_reading"]["citation"],
        "second_reading_excerpt": slots["second_reading"]["excerpt"],
        "gospel_acclamation": slots["gospel_acclamation"]["citation"] or "Alleluia",
        "gospel_acclamation_excerpt": slots["gospel_acclamation"]["excerpt"],
        "gospel": slots["gospel"]["citation"],
        "gospel_excerpt": slots["gospel"]["excerpt"],
    }


# ---------- Public API ----------
def _is_today(d: date) -> bool:
    """Universalis serves today's US date — assume server clock matches."""
    return d == datetime.now(timezone.utc).date() or d == datetime.now().date()


async def fetch_readings(d: date) -> Optional[dict]:
    """Try Universalis (today) → USCCB scrape → return None to let caller use AI."""
    if _is_today(d):
        uni = await _fetch_universalis_today()
        if uni:
            uni["url"] = usccb_url_for(d)
            uni["source"] = "universalis"
            return uni

    usccb = await _fetch_usccb(d)
    if usccb:
        usccb["source"] = "usccb"
        return usccb

    return None

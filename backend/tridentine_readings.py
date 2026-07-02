"""Traditional Latin Mass (1962 Missal) readings — Epistle & Gospel.

We key each Mass to the 1962 temporal cycle (Sundays computed from Easter /
Advent) plus the major feasts, and resolve the FULL text from the app's
Douay-Rheims Bible (the traditional Catholic English translation).

Ferias (weekdays with no proper of their own) repeat the preceding Sunday's
Mass, exactly as the 1962 rubrics prescribe — so every day yields readings.

Citations are stored as (book_slug, chapter, verse_start, verse_end).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from tridentine_calendar import (
    easter_date,
    first_advent_sunday,
    last_sunday_of_october,
    nth_sunday_of_month,
)
import bible

Ref = Tuple[str, int, int, int]  # book_slug, chapter, v_start, v_end


def _r(epistle_cite: str, epistle: Ref, gospel_cite: str, gospel: Ref) -> Dict[str, Any]:
    return {
        "epistle": {"citation": epistle_cite, "ref": epistle},
        "gospel": {"citation": gospel_cite, "ref": gospel},
    }


# Propers keyed by a stable identifier. Citations follow the 1962 Missal.
PROPERS: Dict[str, Dict[str, Any]] = {
    # ---- Advent ----
    "advent-1": _r("Romans 13:11-14", ("romans", 13, 11, 14), "Luke 21:25-33", ("luke", 21, 25, 33)),
    "advent-2": _r("Romans 15:4-13", ("romans", 15, 4, 13), "Matthew 11:2-10", ("matthew", 11, 2, 10)),
    "advent-3": _r("Philippians 4:4-7", ("philippians", 4, 4, 7), "John 1:19-28", ("john", 1, 19, 28)),
    "advent-4": _r("1 Corinthians 4:1-5", ("1-corinthians", 4, 1, 5), "Luke 3:1-6", ("luke", 3, 1, 6)),
    # ---- Christmas season ----
    "christmas": _r("Titus 2:11-15", ("titus", 2, 11, 15), "Luke 2:1-14", ("luke", 2, 1, 14)),
    "holy-name": _r("Acts 4:8-12", ("acts", 4, 8, 12), "Luke 2:21", ("luke", 2, 21, 21)),
    "epiphany": _r("Isaiah 60:1-6", ("isaiah", 60, 1, 6), "Matthew 2:1-12", ("matthew", 2, 1, 12)),
    "holy-family": _r("Colossians 3:12-17", ("colossians", 3, 12, 17), "Luke 2:42-52", ("luke", 2, 42, 52)),
    "epiphany-1": _r("Romans 12:1-5", ("romans", 12, 1, 5), "Luke 2:42-52", ("luke", 2, 42, 52)),
    "epiphany-2": _r("Romans 12:6-16", ("romans", 12, 6, 16), "John 2:1-11", ("john", 2, 1, 11)),
    "epiphany-3": _r("Romans 12:16-21", ("romans", 12, 16, 21), "Matthew 8:1-13", ("matthew", 8, 1, 13)),
    "epiphany-4": _r("Romans 13:8-10", ("romans", 13, 8, 10), "Matthew 8:23-27", ("matthew", 8, 23, 27)),
    "epiphany-5": _r("Colossians 3:12-17", ("colossians", 3, 12, 17), "Matthew 13:24-30", ("matthew", 13, 24, 30)),
    "epiphany-6": _r("1 Thessalonians 1:2-10", ("1-thessalonians", 1, 2, 10), "Matthew 13:31-35", ("matthew", 13, 31, 35)),
    # ---- Pre-Lent ----
    "septuagesima": _r("1 Corinthians 9:24-27; 10:1-5", ("1-corinthians", 9, 24, 27), "Matthew 20:1-16", ("matthew", 20, 1, 16)),
    "sexagesima": _r("2 Corinthians 11:19-33; 12:1-9", ("2-corinthians", 11, 19, 33), "Luke 8:4-15", ("luke", 8, 4, 15)),
    "quinquagesima": _r("1 Corinthians 13:1-13", ("1-corinthians", 13, 1, 13), "Luke 18:31-43", ("luke", 18, 31, 43)),
    # ---- Lent ----
    "ash-wednesday": _r("Joel 2:12-19", ("joel", 2, 12, 19), "Matthew 6:16-21", ("matthew", 6, 16, 21)),
    "lent-1": _r("2 Corinthians 6:1-10", ("2-corinthians", 6, 1, 10), "Matthew 4:1-11", ("matthew", 4, 1, 11)),
    "lent-2": _r("1 Thessalonians 4:1-7", ("1-thessalonians", 4, 1, 7), "Matthew 17:1-9", ("matthew", 17, 1, 9)),
    "lent-3": _r("Ephesians 5:1-9", ("ephesians", 5, 1, 9), "Luke 11:14-28", ("luke", 11, 14, 28)),
    "lent-4": _r("Galatians 4:22-31", ("galatians", 4, 22, 31), "John 6:1-15", ("john", 6, 1, 15)),
    "passion": _r("Hebrews 9:11-15", ("hebrews", 9, 11, 15), "John 8:46-59", ("john", 8, 46, 59)),
    "palm-sunday": _r("Philippians 2:5-11", ("philippians", 2, 5, 11), "Matthew 26:1-75; 27:1-66", ("matthew", 27, 1, 66)),
    "good-friday": _r("Hebrews 9:11-15", ("hebrews", 9, 11, 15), "John 18:1-40; 19:1-42", ("john", 19, 1, 42)),
    # ---- Eastertide ----
    "easter": _r("1 Corinthians 5:7-8", ("1-corinthians", 5, 7, 8), "Mark 16:1-7", ("mark", 16, 1, 7)),
    "easter-1": _r("1 John 5:4-10", ("1-john", 5, 4, 10), "John 20:19-31", ("john", 20, 19, 31)),  # Low Sunday
    "easter-2": _r("1 Peter 2:21-25", ("1-peter", 2, 21, 25), "John 10:11-16", ("john", 10, 11, 16)),
    "easter-3": _r("1 Peter 2:11-19", ("1-peter", 2, 11, 19), "John 16:16-22", ("john", 16, 16, 22)),
    "easter-4": _r("James 1:17-21", ("james", 1, 17, 21), "John 16:5-14", ("john", 16, 5, 14)),
    "easter-5": _r("James 1:22-27", ("james", 1, 22, 27), "John 16:23-30", ("john", 16, 23, 30)),
    "ascension": _r("Acts 1:1-11", ("acts", 1, 1, 11), "Mark 16:14-20", ("mark", 16, 14, 20)),
    "after-ascension": _r("1 Peter 4:7-11", ("1-peter", 4, 7, 11), "John 15:26-27; 16:1-4", ("john", 15, 26, 27)),
    "pentecost": _r("Acts 2:1-11", ("acts", 2, 1, 11), "John 14:23-31", ("john", 14, 23, 31)),
    # ---- After Pentecost / feasts of the Lord ----
    "trinity": _r("Romans 11:33-36", ("romans", 11, 33, 36), "Matthew 28:18-20", ("matthew", 28, 18, 20)),
    "corpus-christi": _r("1 Corinthians 11:23-29", ("1-corinthians", 11, 23, 29), "John 6:56-59", ("john", 6, 56, 59)),
    "sacred-heart": _r("Ephesians 3:8-19", ("ephesians", 3, 8, 19), "John 19:31-37", ("john", 19, 31, 37)),
    "christ-king": _r("Colossians 1:12-20", ("colossians", 1, 12, 20), "John 18:33-37", ("john", 18, 33, 37)),
    "pentecost-1": _r("1 John 4:8-21", ("1-john", 4, 8, 21), "Luke 6:36-42", ("luke", 6, 36, 42)),
    "pentecost-2": _r("1 John 3:13-18", ("1-john", 3, 13, 18), "Luke 14:16-24", ("luke", 14, 16, 24)),
    "pentecost-3": _r("1 Peter 5:6-11", ("1-peter", 5, 6, 11), "Luke 15:1-10", ("luke", 15, 1, 10)),
    "pentecost-4": _r("Romans 8:18-23", ("romans", 8, 18, 23), "Luke 5:1-11", ("luke", 5, 1, 11)),
    "pentecost-5": _r("1 Peter 3:8-15", ("1-peter", 3, 8, 15), "Matthew 5:20-24", ("matthew", 5, 20, 24)),
    "pentecost-6": _r("Romans 6:3-11", ("romans", 6, 3, 11), "Mark 8:1-9", ("mark", 8, 1, 9)),
    "pentecost-7": _r("Romans 6:19-23", ("romans", 6, 19, 23), "Matthew 7:15-21", ("matthew", 7, 15, 21)),
    "pentecost-8": _r("Romans 8:12-17", ("romans", 8, 12, 17), "Luke 16:1-9", ("luke", 16, 1, 9)),
    "pentecost-9": _r("1 Corinthians 10:6-13", ("1-corinthians", 10, 6, 13), "Luke 19:41-47", ("luke", 19, 41, 47)),
    "pentecost-10": _r("1 Corinthians 12:2-11", ("1-corinthians", 12, 2, 11), "Luke 18:9-14", ("luke", 18, 9, 14)),
    "pentecost-11": _r("1 Corinthians 15:1-10", ("1-corinthians", 15, 1, 10), "Mark 7:31-37", ("mark", 7, 31, 37)),
    "pentecost-12": _r("2 Corinthians 3:4-9", ("2-corinthians", 3, 4, 9), "Luke 10:23-37", ("luke", 10, 23, 37)),
    "pentecost-13": _r("Galatians 3:16-22", ("galatians", 3, 16, 22), "Luke 17:11-19", ("luke", 17, 11, 19)),
    "pentecost-14": _r("Galatians 5:16-24", ("galatians", 5, 16, 24), "Matthew 6:24-33", ("matthew", 6, 24, 33)),
    "pentecost-15": _r("Galatians 5:25-26; 6:1-10", ("galatians", 5, 25, 26), "Luke 7:11-16", ("luke", 7, 11, 16)),
    "pentecost-16": _r("Ephesians 3:13-21", ("ephesians", 3, 13, 21), "Luke 14:1-11", ("luke", 14, 1, 11)),
    "pentecost-17": _r("Ephesians 4:1-6", ("ephesians", 4, 1, 6), "Matthew 22:34-46", ("matthew", 22, 34, 46)),
    "pentecost-18": _r("1 Corinthians 1:4-8", ("1-corinthians", 1, 4, 8), "Matthew 9:1-8", ("matthew", 9, 1, 8)),
    "pentecost-19": _r("Ephesians 4:23-28", ("ephesians", 4, 23, 28), "Matthew 22:1-14", ("matthew", 22, 1, 14)),
    "pentecost-20": _r("Ephesians 5:15-21", ("ephesians", 5, 15, 21), "John 4:46-53", ("john", 4, 46, 53)),
    "pentecost-21": _r("Ephesians 6:10-17", ("ephesians", 6, 10, 17), "Matthew 18:23-35", ("matthew", 18, 23, 35)),
    "pentecost-22": _r("Philippians 1:6-11", ("philippians", 1, 6, 11), "Matthew 22:15-21", ("matthew", 22, 15, 21)),
    "pentecost-23": _r("Philippians 3:17-21; 4:1-3", ("philippians", 3, 17, 21), "Matthew 9:18-26", ("matthew", 9, 18, 26)),
    "pentecost-24": _r("Colossians 1:9-14", ("colossians", 1, 9, 14), "Matthew 24:15-35", ("matthew", 24, 15, 35)),
    # ---- Major fixed feasts (override the temporal) ----
    "immaculate-conception": _r("Proverbs 8:22-35", ("proverbs", 8, 22, 35), "Luke 1:26-28", ("luke", 1, 26, 28)),
    "assumption": _r("Judith 13:22-25; 15:10", ("judith", 13, 22, 25), "Luke 1:41-50", ("luke", 1, 41, 50)),
    "all-saints": _r("Revelation 7:2-12", ("revelation", 7, 2, 12), "Matthew 5:1-12", ("matthew", 5, 1, 12)),
    "peter-paul": _r("Acts 12:1-11", ("acts", 12, 1, 11), "Matthew 16:13-19", ("matthew", 16, 13, 19)),
    "st-joseph": _r("Sirach 45:1-6", ("sirach", 45, 1, 6), "Matthew 1:18-21", ("matthew", 1, 18, 21)),
    "john-baptist": _r("Isaiah 49:1-7", ("isaiah", 49, 1, 7), "Luke 1:57-68", ("luke", 1, 57, 68)),
    "purification": _r("Malachi 3:1-4", ("malachi", 3, 1, 4), "Luke 2:22-32", ("luke", 2, 22, 32)),
    "annunciation": _r("Isaiah 7:10-15", ("isaiah", 7, 10, 15), "Luke 1:26-38", ("luke", 1, 26, 38)),
    "nativity-bvm": _r("Proverbs 8:22-35", ("proverbs", 8, 22, 35), "Matthew 1:1-16", ("matthew", 1, 1, 16)),
    "holy-cross": _r("Philippians 2:5-11", ("philippians", 2, 5, 11), "John 12:31-36", ("john", 12, 31, 36)),
    "michaelmas": _r("Revelation 1:1-5", ("revelation", 1, 1, 5), "Matthew 18:1-10", ("matthew", 18, 1, 10)),
}

# Fixed-date feasts → proper key (month, day).
FIXED_FEAST_KEYS = {
    (12, 8): "immaculate-conception",
    (12, 25): "christmas",
    (1, 6): "epiphany",
    (2, 2): "purification",
    (3, 19): "st-joseph",
    (3, 25): "annunciation",
    (6, 24): "john-baptist",
    (6, 29): "peter-paul",
    (8, 15): "assumption",
    (9, 8): "nativity-bvm",
    (9, 14): "holy-cross",
    (9, 29): "michaelmas",
    (11, 1): "all-saints",
}


def _sunday_key(d: date) -> Optional[str]:
    """Return the temporal proper key for the SUNDAY on or before d's week,
    i.e. the Mass currently being repeated on ferias."""
    year = d.year
    easter = easter_date(year)
    advent = first_advent_sunday(year)
    christmas = date(year, 12, 25)

    # Advent (may belong to the previous liturgical year for Jan dates handled below)
    if advent <= d <= date(year, 12, 24):
        n = ((d - advent).days // 7) + 1
        return f"advent-{min(n, 4)}"

    # Christmas → Epiphany
    if christmas <= d <= date(year, 12, 31) or d == date(year, 1, 1):
        return "christmas"
    if date(year, 1, 2) <= d <= date(year, 1, 5):
        return "holy-name"
    if date(year, 1, 6) <= d <= date(year, 1, 13):
        return "epiphany"

    septuagesima = easter - timedelta(days=63)
    ash = easter - timedelta(days=46)
    passion = easter - timedelta(days=14)
    palm = easter - timedelta(days=7)
    pentecost = easter + timedelta(days=49)

    # Time after Epiphany (Sundays 1..6 until Septuagesima)
    if date(year, 1, 14) <= d < septuagesima:
        # first Sunday after Jan 13
        first = date(year, 1, 14)
        while first.weekday() != 6:
            first += timedelta(days=1)
        n = ((d - first).days // 7) + 1
        if n < 1:
            return "epiphany-1"
        return f"epiphany-{min(n, 6)}"

    if septuagesima <= d < septuagesima + timedelta(days=7):
        return "septuagesima"
    if septuagesima + timedelta(days=7) <= d < septuagesima + timedelta(days=14):
        return "sexagesima"
    if septuagesima + timedelta(days=14) <= d < ash:
        return "quinquagesima"

    # Lent
    if ash <= d < ash + timedelta(days=4):
        return "ash-wednesday"
    if ash + timedelta(days=4) <= d < passion:
        n = ((d - (ash + timedelta(days=4))).days // 7) + 1
        return f"lent-{min(n, 4)}"
    if passion <= d < palm:
        return "passion"
    if palm <= d < easter:
        return "palm-sunday"

    # Eastertide
    if d == easter or (easter < d < easter + timedelta(days=7)):
        return "easter"
    ascension = easter + timedelta(days=39)
    if easter + timedelta(days=7) <= d < pentecost:
        n = ((d - easter).days // 7)  # Low Sunday = week 1
        if d >= ascension and d < pentecost and n >= 6:
            return "after-ascension"
        return f"easter-{min(n, 5)}"

    # Pentecost week
    if pentecost <= d < pentecost + timedelta(days=7):
        return "pentecost"
    trinity = pentecost + timedelta(days=7)
    if trinity <= d < trinity + timedelta(days=7):
        return "trinity"

    # Time after Pentecost (1..24), until Advent
    if trinity + timedelta(days=7) <= d < advent:
        n = ((d - trinity).days // 7)  # Trinity=0 -> first Sunday after Pentecost proper = n
        key = f"pentecost-{min(max(n, 1), 24)}"
        return key
    return None


async def get_tridentine_readings(db, d: date) -> Dict[str, Any]:
    """Full TLM readings for a date (Epistle + Gospel, Douay-Rheims text)."""
    year = d.year
    easter = easter_date(year)

    # 1) Movable feasts of Our Lord take precedence.
    movable = {
        easter: "easter",
        easter + timedelta(days=39): "ascension",
        easter + timedelta(days=49): "pentecost",
        easter + timedelta(days=60): "corpus-christi",
        easter + timedelta(days=68): "sacred-heart",
        easter - timedelta(days=2): "good-friday",
        last_sunday_of_october(year): "christ-king",
    }
    key = movable.get(d)

    # 2) Major fixed feasts.
    if not key:
        key = FIXED_FEAST_KEYS.get((d.month, d.day))

    # 3) Holy Family = Sunday within the octave of Epiphany (first Sunday after Jan 6).
    if not key and date(year, 1, 7) <= d <= date(year, 1, 13) and d.weekday() == 6:
        key = "holy-family"

    # 4) Otherwise the temporal proper for this day (Sunday, or the preceding
    #    Sunday repeated on ferias).
    is_feria_fallback = False
    if not key:
        key = _sunday_key(d)
        if d.weekday() != 6 and key:
            is_feria_fallback = True

    proper = PROPERS.get(key or "")
    if not proper:
        return {"date": d.isoformat(), "available": False}

    async def _text(ref: Ref) -> List[Dict[str, Any]]:
        slug, ch, v1, v2 = ref
        try:
            chap = await bible.get_chapter(db, slug, ch)
        except Exception:
            return []
        verses = chap.get("verses") or []
        return [{"n": v["n"], "text": v["text"]} for v in verses if v1 <= int(v["n"]) <= v2]

    epistle_text = await _text(proper["epistle"]["ref"])
    gospel_text = await _text(proper["gospel"]["ref"])
    return {
        "date": d.isoformat(),
        "available": True,
        "proper_key": key,
        "feria_fallback": is_feria_fallback,
        "epistle": {"citation": proper["epistle"]["citation"], "verses": epistle_text},
        "gospel": {"citation": proper["gospel"]["citation"], "verses": gospel_text},
    }

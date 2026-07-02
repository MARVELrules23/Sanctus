"""Byzantine (Eastern Catholic) Divine Liturgy readings — Epistle & Gospel.

Keyed to the Paschal cycle (movable Sundays from Pascha through the Sundays
after Pentecost) plus the Great Feasts of the Menaion. The full text is
resolved from the app's embedded Douay-Rheims Bible, matching the Traditional
Latin Mass readings for a consistent reverent English register.

Ordinary weekdays with no proper of their own repeat the most recent Sunday's
readings (a "feria fallback"), so every day yields readings — matching the
coverage promised for the TLM screen.

References are stored as a list of contiguous segments so a reading that spans a
chapter boundary (e.g. Heb 11:33-12:2) resolves cleanly. A segment is
(book_slug, chapter, verse_start, verse_end); verse_end may be 999 to mean
"to the end of the chapter".
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from eastern_calendar import pascha_for
import bible

Seg = Tuple[str, int, int, int]  # book_slug, chapter, v_start, v_end


def _r(epistle_cite: str, epistle: List[Seg], gospel_cite: str, gospel: List[Seg]) -> Dict[str, Any]:
    return {
        "epistle": {"citation": epistle_cite, "segs": epistle},
        "gospel": {"citation": gospel_cite, "segs": gospel},
    }


# --- Propers keyed by a stable identifier. Citations follow the Byzantine (Ruthenian/
#     Melkite) recension of the Divine Liturgy lectionary. ---
PROPERS: Dict[str, Dict[str, Any]] = {
    # ---- Paschal season ----
    "pascha": _r("Acts 1:1-8", [("acts", 1, 1, 8)], "John 1:1-17", [("john", 1, 1, 17)]),
    "thomas": _r("Acts 5:12-20", [("acts", 5, 12, 20)], "John 20:19-31", [("john", 20, 19, 31)]),
    "myrrhbearers": _r("Acts 6:1-7", [("acts", 6, 1, 7)], "Mark 15:43-16:8", [("mark", 15, 43, 999), ("mark", 16, 1, 8)]),
    "paralytic": _r("Acts 9:32-42", [("acts", 9, 32, 42)], "John 5:1-15", [("john", 5, 1, 15)]),
    "samaritan": _r("Acts 11:19-30", [("acts", 11, 19, 30)], "John 4:5-42", [("john", 4, 5, 42)]),
    "blind-man": _r("Acts 16:16-34", [("acts", 16, 16, 34)], "John 9:1-38", [("john", 9, 1, 38)]),
    "nicaea-fathers": _r("Acts 20:16-36", [("acts", 20, 16, 18), ("acts", 20, 28, 36)], "John 17:1-13", [("john", 17, 1, 13)]),
    "pentecost": _r("Acts 2:1-11", [("acts", 2, 1, 11)], "John 7:37-52; 8:12", [("john", 7, 37, 52), ("john", 8, 12, 12)]),
    # ---- Sundays after Pentecost ----
    "after-pentecost-1": _r("Hebrews 11:33-12:2", [("hebrews", 11, 33, 999), ("hebrews", 12, 1, 2)], "Matthew 10:32-33, 37-38; 19:27-30", [("matthew", 10, 32, 33), ("matthew", 10, 37, 38), ("matthew", 19, 27, 30)]),
    "after-pentecost-2": _r("Romans 2:10-16", [("romans", 2, 10, 16)], "Matthew 4:18-23", [("matthew", 4, 18, 23)]),
    "after-pentecost-3": _r("Romans 5:1-10", [("romans", 5, 1, 10)], "Matthew 6:22-33", [("matthew", 6, 22, 33)]),
    "after-pentecost-4": _r("Romans 6:18-23", [("romans", 6, 18, 23)], "Matthew 8:5-13", [("matthew", 8, 5, 13)]),
    "after-pentecost-5": _r("Romans 10:1-10", [("romans", 10, 1, 10)], "Matthew 8:28-9:1", [("matthew", 8, 28, 999), ("matthew", 9, 1, 1)]),
    "after-pentecost-6": _r("Romans 12:6-14", [("romans", 12, 6, 14)], "Matthew 9:1-8", [("matthew", 9, 1, 8)]),
    "after-pentecost-7": _r("Romans 15:1-7", [("romans", 15, 1, 7)], "Matthew 9:27-35", [("matthew", 9, 27, 35)]),
    "after-pentecost-8": _r("1 Corinthians 1:10-18", [("1-corinthians", 1, 10, 18)], "Matthew 14:14-22", [("matthew", 14, 14, 22)]),
    "after-pentecost-9": _r("1 Corinthians 3:9-17", [("1-corinthians", 3, 9, 17)], "Matthew 14:22-34", [("matthew", 14, 22, 34)]),
    "after-pentecost-10": _r("1 Corinthians 4:9-16", [("1-corinthians", 4, 9, 16)], "Matthew 17:14-23", [("matthew", 17, 14, 23)]),
    "after-pentecost-11": _r("1 Corinthians 9:2-12", [("1-corinthians", 9, 2, 12)], "Matthew 18:23-35", [("matthew", 18, 23, 35)]),
    "after-pentecost-12": _r("1 Corinthians 15:1-11", [("1-corinthians", 15, 1, 11)], "Matthew 19:16-26", [("matthew", 19, 16, 26)]),
    "after-pentecost-13": _r("1 Corinthians 16:13-24", [("1-corinthians", 16, 13, 24)], "Matthew 21:33-42", [("matthew", 21, 33, 42)]),
    "after-pentecost-14": _r("2 Corinthians 1:21-2:4", [("2-corinthians", 1, 21, 24), ("2-corinthians", 2, 1, 4)], "Matthew 22:2-14", [("matthew", 22, 2, 14)]),
    "after-pentecost-15": _r("2 Corinthians 4:6-15", [("2-corinthians", 4, 6, 15)], "Matthew 22:35-46", [("matthew", 22, 35, 46)]),
    "after-pentecost-16": _r("2 Corinthians 6:1-10", [("2-corinthians", 6, 1, 10)], "Matthew 25:14-30", [("matthew", 25, 14, 30)]),
    "after-pentecost-17": _r("2 Corinthians 6:16-7:1", [("2-corinthians", 6, 16, 999), ("2-corinthians", 7, 1, 1)], "Matthew 15:21-28", [("matthew", 15, 21, 28)]),
    "after-pentecost-18": _r("2 Corinthians 9:6-11", [("2-corinthians", 9, 6, 11)], "Luke 5:1-11", [("luke", 5, 1, 11)]),
    "after-pentecost-19": _r("2 Corinthians 11:31-12:9", [("2-corinthians", 11, 31, 999), ("2-corinthians", 12, 1, 9)], "Luke 6:31-36", [("luke", 6, 31, 36)]),
    "after-pentecost-20": _r("Galatians 1:11-19", [("galatians", 1, 11, 19)], "Luke 7:11-16", [("luke", 7, 11, 16)]),
    "after-pentecost-21": _r("Galatians 2:16-20", [("galatians", 2, 16, 20)], "Luke 8:5-15", [("luke", 8, 5, 15)]),
    "after-pentecost-22": _r("Galatians 6:11-18", [("galatians", 6, 11, 18)], "Luke 16:19-31", [("luke", 16, 19, 31)]),
    "after-pentecost-23": _r("Ephesians 2:4-10", [("ephesians", 2, 4, 10)], "Luke 8:26-39", [("luke", 8, 26, 39)]),
    "after-pentecost-24": _r("Ephesians 2:14-22", [("ephesians", 2, 14, 22)], "Luke 8:41-56", [("luke", 8, 41, 56)]),
    "after-pentecost-25": _r("Ephesians 4:1-6", [("ephesians", 4, 1, 6)], "Luke 10:25-37", [("luke", 10, 25, 37)]),
    "after-pentecost-26": _r("Ephesians 5:9-19", [("ephesians", 5, 9, 19)], "Luke 12:16-21", [("luke", 12, 16, 21)]),
    "after-pentecost-27": _r("Ephesians 6:10-17", [("ephesians", 6, 10, 17)], "Luke 13:10-17", [("luke", 13, 10, 17)]),
    "after-pentecost-28": _r("Colossians 1:12-18", [("colossians", 1, 12, 18)], "Luke 14:16-24", [("luke", 14, 16, 24)]),
    "after-pentecost-29": _r("Colossians 3:4-11", [("colossians", 3, 4, 11)], "Luke 17:12-19", [("luke", 17, 12, 19)]),
    "after-pentecost-30": _r("Colossians 3:12-16", [("colossians", 3, 12, 16)], "Luke 18:18-27", [("luke", 18, 18, 27)]),
    "after-pentecost-31": _r("1 Timothy 1:15-17", [("1-timothy", 1, 15, 17)], "Luke 18:35-43", [("luke", 18, 35, 43)]),
    "after-pentecost-32": _r("1 Timothy 4:9-15", [("1-timothy", 4, 9, 15)], "Luke 19:1-10", [("luke", 19, 1, 10)]),
    # ---- Pre-Lenten & Great Lent Sundays ----
    "publican-pharisee": _r("2 Timothy 3:10-15", [("2-timothy", 3, 10, 15)], "Luke 18:10-14", [("luke", 18, 10, 14)]),
    "prodigal-son": _r("1 Corinthians 6:12-20", [("1-corinthians", 6, 12, 20)], "Luke 15:11-32", [("luke", 15, 11, 32)]),
    "meatfare": _r("1 Corinthians 8:8-9:2", [("1-corinthians", 8, 8, 999), ("1-corinthians", 9, 1, 2)], "Matthew 25:31-46", [("matthew", 25, 31, 46)]),
    "cheesefare": _r("Romans 13:11-14:4", [("romans", 13, 11, 999), ("romans", 14, 1, 4)], "Matthew 6:14-21", [("matthew", 6, 14, 21)]),
    "lent-1-orthodoxy": _r("Hebrews 11:24-40; 12:1-2", [("hebrews", 11, 24, 26), ("hebrews", 11, 32, 999), ("hebrews", 12, 1, 2)], "John 1:43-51", [("john", 1, 43, 51)]),
    "lent-2-palamas": _r("Hebrews 1:10-2:3", [("hebrews", 1, 10, 999), ("hebrews", 2, 1, 3)], "Mark 2:1-12", [("mark", 2, 1, 12)]),
    "lent-3-cross": _r("Hebrews 4:14-5:6", [("hebrews", 4, 14, 999), ("hebrews", 5, 1, 6)], "Mark 8:34-9:1", [("mark", 8, 34, 999), ("mark", 9, 1, 1)]),
    "lent-4-climacus": _r("Hebrews 6:13-20", [("hebrews", 6, 13, 20)], "Mark 9:17-31", [("mark", 9, 17, 31)]),
    "lent-5-mary-egypt": _r("Hebrews 9:11-14", [("hebrews", 9, 11, 14)], "Mark 10:32-45", [("mark", 10, 32, 45)]),
    "palm-sunday": _r("Philippians 4:4-9", [("philippians", 4, 4, 9)], "John 12:1-18", [("john", 12, 1, 18)]),
    # ---- Great Feasts of the Menaion (fixed) ----
    "nativity-theotokos": _r("Philippians 2:5-11", [("philippians", 2, 5, 11)], "Luke 10:38-42; 11:27-28", [("luke", 10, 38, 42), ("luke", 11, 27, 28)]),
    "exaltation-cross": _r("1 Corinthians 1:18-24", [("1-corinthians", 1, 18, 24)], "John 19:6-35", [("john", 19, 6, 11), ("john", 19, 13, 20), ("john", 19, 25, 28), ("john", 19, 30, 35)]),
    "protection-theotokos": _r("Hebrews 9:1-7", [("hebrews", 9, 1, 7)], "Luke 10:38-42; 11:27-28", [("luke", 10, 38, 42), ("luke", 11, 27, 28)]),
    "entrance-theotokos": _r("Hebrews 9:1-7", [("hebrews", 9, 1, 7)], "Luke 10:38-42; 11:27-28", [("luke", 10, 38, 42), ("luke", 11, 27, 28)]),
    "st-nicholas": _r("Hebrews 13:17-21", [("hebrews", 13, 17, 21)], "Luke 6:17-23", [("luke", 6, 17, 23)]),
    "nativity-christ": _r("Galatians 4:4-7", [("galatians", 4, 4, 7)], "Matthew 2:1-12", [("matthew", 2, 1, 12)]),
    "theophany": _r("Titus 2:11-14; 3:4-7", [("titus", 2, 11, 14), ("titus", 3, 4, 7)], "Matthew 3:13-17", [("matthew", 3, 13, 17)]),
    "three-hierarchs": _r("Hebrews 13:7-16", [("hebrews", 13, 7, 16)], "Matthew 5:14-19", [("matthew", 5, 14, 19)]),
    "meeting-lord": _r("Hebrews 7:7-17", [("hebrews", 7, 7, 17)], "Luke 2:22-40", [("luke", 2, 22, 40)]),
    "annunciation": _r("Hebrews 2:11-18", [("hebrews", 2, 11, 18)], "Luke 1:24-38", [("luke", 1, 24, 38)]),
    "st-george": _r("Acts 12:1-11", [("acts", 12, 1, 11)], "John 15:17-16:2", [("john", 15, 17, 999), ("john", 16, 1, 2)]),
    "nativity-forerunner": _r("Romans 13:11-14:4", [("romans", 13, 11, 999), ("romans", 14, 1, 4)], "Luke 1:1-25, 57-68, 76-80", [("luke", 1, 1, 25), ("luke", 1, 57, 68), ("luke", 1, 76, 80)]),
    "peter-paul": _r("2 Corinthians 11:21-12:9", [("2-corinthians", 11, 21, 999), ("2-corinthians", 12, 1, 9)], "Matthew 16:13-19", [("matthew", 16, 13, 19)]),
    "transfiguration": _r("2 Peter 1:10-19", [("2-peter", 1, 10, 19)], "Matthew 17:1-9", [("matthew", 17, 1, 9)]),
    "dormition": _r("Philippians 2:5-11", [("philippians", 2, 5, 11)], "Luke 10:38-42; 11:27-28", [("luke", 10, 38, 42), ("luke", 11, 27, 28)]),
    "beheading-forerunner": _r("Acts 13:25-33", [("acts", 13, 25, 33)], "Mark 6:14-30", [("mark", 6, 14, 30)]),
}

# Fixed great-feast dates (Gregorian/"new" reckoning) → proper key.
FIXED_FEAST_KEYS = {
    (9, 8): "nativity-theotokos",
    (9, 14): "exaltation-cross",
    (10, 1): "protection-theotokos",
    (11, 21): "entrance-theotokos",
    (12, 6): "st-nicholas",
    (12, 25): "nativity-christ",
    (1, 6): "theophany",
    (1, 30): "three-hierarchs",
    (2, 2): "meeting-lord",
    (3, 25): "annunciation",
    (4, 23): "st-george",
    (6, 24): "nativity-forerunner",
    (6, 29): "peter-paul",
    (8, 6): "transfiguration",
    (8, 15): "dormition",
    (8, 29): "beheading-forerunner",
}

# Named Sundays of the Paschal season, offset in weeks from Pascha.
PASCHAL_SUNDAYS = {
    0: "pascha",
    1: "thomas",
    2: "myrrhbearers",
    3: "paralytic",
    4: "samaritan",
    5: "blind-man",
    6: "nicaea-fathers",  # Sunday after Ascension
    7: "pentecost",
}

# Pre-Lenten & Lenten Sundays, offset in weeks BEFORE Pascha.
PRE_PASCHA_SUNDAYS = {
    10: "publican-pharisee",
    9: "prodigal-son",
    8: "meatfare",
    7: "cheesefare",
    6: "lent-1-orthodoxy",
    5: "lent-2-palamas",
    4: "lent-3-cross",
    3: "lent-4-climacus",
    2: "lent-5-mary-egypt",
    1: "palm-sunday",
}


def _governing_sunday(d: date) -> date:
    """The Sunday on or before ``d`` (Sunday == weekday() 6)."""
    return d - timedelta(days=(d.weekday() + 1) % 7)


def _sunday_key(sunday: date, calendar: str) -> Optional[str]:
    """Resolve the temporal proper key for a given Sunday date."""
    year = sunday.year
    # Consider this year's and last year's Pascha so early-year dates map to the
    # previous cycle's Sundays-after-Pentecost.
    for p in (pascha_for(year, calendar), pascha_for(year - 1, calendar), pascha_for(year + 1, calendar)):
        weeks = (sunday - p).days // 7
        # Paschal season (Pascha .. Pentecost)
        if 0 <= weeks <= 7 and sunday >= p:
            return PASCHAL_SUNDAYS.get(weeks)
        # After Pentecost (weeks 8.. -> "1st after Pentecost" = week 8)
        if 8 <= weeks:
            n = weeks - 7  # week 8 -> 1
            if 1 <= n <= 32:
                return f"after-pentecost-{n}"
        # Pre-Lent / Great Lent (weeks before Pascha)
        before = (p - sunday).days // 7
        if before in PRE_PASCHA_SUNDAYS:
            return PRE_PASCHA_SUNDAYS[before]
    return None


async def get_byzantine_readings(db, d: date, calendar: str = "new") -> Dict[str, Any]:
    """Full Byzantine Divine Liturgy readings for a date (Epistle + Gospel)."""
    # 1) Fixed Great Feasts take precedence on their own day.
    key = None
    offset = 0 if calendar == "new" else 13
    civil = d - timedelta(days=offset)  # menaion date in its own calendar
    key = FIXED_FEAST_KEYS.get((civil.month, civil.day))

    # 2) Otherwise the temporal proper of the governing Sunday.
    is_feria_fallback = False
    if not key:
        gov = _governing_sunday(d)
        key = _sunday_key(gov, calendar)
        if d.weekday() != 6 and key:
            is_feria_fallback = True

    proper = PROPERS.get(key or "")
    if not proper:
        return {"date": d.isoformat(), "available": False}

    async def _text(segs: List[Seg]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for slug, ch, v1, v2 in segs:
            try:
                chap = await bible.get_chapter(db, slug, ch)
            except Exception:
                continue
            for v in (chap.get("verses") or []):
                n = int(v["n"])
                if v1 <= n <= v2:
                    out.append({"n": n, "text": v["text"], "ch": ch})
        return out

    epistle_text = await _text(proper["epistle"]["segs"])
    gospel_text = await _text(proper["gospel"]["segs"])
    return {
        "date": d.isoformat(),
        "available": True,
        "proper_key": key,
        "feria_fallback": is_feria_fallback,
        "calendar": "old" if calendar == "old" else "new",
        "epistle": {"citation": proper["epistle"]["citation"], "verses": epistle_text},
        "gospel": {"citation": proper["gospel"]["citation"], "verses": gospel_text},
    }

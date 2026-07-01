"""Byzantine (Eastern Catholic) liturgical calendar.

Supports the two reckonings used across the Eastern Catholic Churches:

* ``"new"`` — the Revised-Julian / Gregorian reckoning: fixed feasts fall on the
  same civil dates you'd read off a wall calendar, and Pascha is aligned with the
  Gregorian (Roman) computus.
* ``"old"`` — the traditional Julian ("Old Calendar") reckoning: fixed feasts are
  shifted +13 days on the civil calendar (so the Nativity falls on Jan 7), and
  Pascha follows the Julian (Orthodox) computus.

Not exhaustive — it covers Pascha, the Twelve Great Feasts, the four great fasts
and a curated set of major commemorations so users always see meaningful context.
"""
from datetime import date, timedelta
from typing import Optional

from liturgical import easter_date  # Gregorian (Roman) Pascha

# Julian → Gregorian civil-date offset for the years 1900–2099.
JULIAN_OFFSET_DAYS = 13


def julian_pascha(year: int) -> date:
    """Orthodox (Julian-computus) Pascha as a Gregorian civil date."""
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = ((d + e + 114) % 31) + 1
    julian = date(year, month, day)  # date in the Julian calendar
    return julian + timedelta(days=JULIAN_OFFSET_DAYS)


def pascha_for(year: int, calendar: str) -> date:
    return easter_date(year) if calendar == "new" else julian_pascha(year)


# Fixed (Menaion) feasts, keyed by the feast's own (month, day) in its calendar.
# rank: greatfeast | feast | commemoration
FIXED_EASTERN = {
    (9, 8): {"name": "Nativity of the Theotokos", "rank": "greatfeast", "color": "white"},
    (9, 14): {"name": "Exaltation of the Holy Cross", "rank": "greatfeast", "color": "red"},
    (10, 1): {"name": "Protection of the Theotokos", "rank": "feast", "color": "white"},
    (11, 8): {"name": "Synaxis of the Archangel Michael", "rank": "feast", "color": "white"},
    (11, 21): {"name": "Entrance of the Theotokos into the Temple", "rank": "greatfeast", "color": "white"},
    (12, 6): {"name": "St Nicholas the Wonderworker", "rank": "feast", "color": "white"},
    (12, 25): {"name": "Nativity of Christ", "rank": "greatfeast", "color": "white"},
    (1, 1): {"name": "Circumcision of Christ · St Basil the Great", "rank": "feast", "color": "white"},
    (1, 6): {"name": "Theophany (Baptism) of the Lord", "rank": "greatfeast", "color": "white"},
    (1, 30): {"name": "Three Holy Hierarchs", "rank": "feast", "color": "white"},
    (2, 2): {"name": "Meeting of the Lord in the Temple", "rank": "greatfeast", "color": "white"},
    (3, 25): {"name": "Annunciation to the Theotokos", "rank": "greatfeast", "color": "white"},
    (4, 23): {"name": "St George the Great Martyr", "rank": "feast", "color": "red"},
    (6, 24): {"name": "Nativity of St John the Forerunner", "rank": "feast", "color": "white"},
    (6, 29): {"name": "Holy Apostles Peter and Paul", "rank": "greatfeast", "color": "red"},
    (8, 6): {"name": "Transfiguration of the Lord", "rank": "greatfeast", "color": "white"},
    (8, 15): {"name": "Dormition of the Theotokos", "rank": "greatfeast", "color": "white"},
    (8, 29): {"name": "Beheading of St John the Forerunner", "rank": "feast", "color": "red"},
}


def _fixed_lookup(d: date, calendar: str) -> Optional[dict]:
    """Fixed feast on civil date ``d`` for the chosen calendar."""
    key_date = d if calendar == "new" else (d - timedelta(days=JULIAN_OFFSET_DAYS))
    return FIXED_EASTERN.get((key_date.month, key_date.day))


def get_eastern_day(d: date, calendar: str = "new") -> dict:
    """Byzantine liturgical info for a civil date under the chosen reckoning."""
    calendar = "old" if calendar == "old" else "new"
    year = d.year

    # Moveable (Paschal) cycle — anchor to the Pascha of this civil year and,
    # for dates early in the year, the previous year's Pentecostarion tail.
    pascha = pascha_for(year, calendar)
    lent_start = pascha - timedelta(days=48)          # Clean Monday
    palm_sunday = pascha - timedelta(days=7)
    lazarus_saturday = pascha - timedelta(days=8)
    ascension = pascha + timedelta(days=39)           # Thursday
    pentecost = pascha + timedelta(days=49)
    all_saints = pascha + timedelta(days=56)          # 1st Sun after Pentecost

    moveable = {
        lazarus_saturday: ("Lazarus Saturday", "feast", "white"),
        palm_sunday: ("Entry of the Lord into Jerusalem (Palm Sunday)", "greatfeast", "white"),
        pascha: ("Pascha — Resurrection of the Lord", "greatfeast", "white"),
        ascension: ("Ascension of the Lord", "greatfeast", "white"),
        pentecost: ("Pentecost", "greatfeast", "red"),
        all_saints: ("All Saints", "feast", "green"),
    }
    great_friday = pascha - timedelta(days=2)
    great_thursday = pascha - timedelta(days=3)
    moveable[great_thursday] = ("Great and Holy Thursday", "greatfeast", "purple")
    moveable[great_friday] = ("Great and Holy Friday", "greatfeast", "red")

    is_sunday = d.weekday() == 6

    # Season + base color.
    season = "Ordinary Time (After Pentecost)"
    color = "green"
    if lent_start <= d < palm_sunday:
        season, color = "Great Lent", "purple"
    elif palm_sunday <= d < pascha:
        season, color = "Great and Holy Week", "purple"
    elif pascha <= d <= pentecost:
        season, color = "Pentecostarion (Paschal Season)", "white"

    # ---- Byzantine fasting seasons (abstinence from meat) ----
    def _win(m1, d1, m2, d2):
        """Civil-date membership in a shifted fixed window [start, end).

        Wrap-safe across the civil new year — essential on the Old (Julian)
        calendar, where e.g. the Nativity Fast runs civil Nov 28 → Jan 7.
        """
        for yy in (d.year, d.year - 1):
            start = _shift(date(yy, m1, d1), calendar)
            end = _shift(date(yy, m2, d2), calendar)
            if end <= start:
                end = _shift(date(yy + 1, m2, d2), calendar)
            if start <= d < end:
                return True
        return False

    in_nativity_fast = _win(11, 15, 12, 25)      # Philip's Fast → Nativity
    in_dormition_fast = _win(8, 1, 8, 15)         # Dormition Fast
    apostles_start = pentecost + timedelta(days=8)     # Monday after All Saints Sunday
    apostles_end = _shift(date(year, 6, 29), calendar)  # eve of Sts Peter & Paul
    in_apostles_fast = apostles_start <= d < apostles_end
    # Meat is set aside from the day after Meatfare Sunday (Cheesefare week)
    # right through Great Lent and Holy Week to Pascha.
    in_lenten_meat_fast = (pascha - timedelta(days=55)) <= d < pascha

    if in_nativity_fast:
        season = "Nativity Fast (Philip's Fast)"
    elif in_dormition_fast:
        season = "Dormition Fast"
    elif (pascha - timedelta(days=55)) <= d < lent_start:
        season = "Pre-Lent (Cheesefare Week)"

    feast_name: Optional[str] = None
    rank = "feria"

    mv = moveable.get(d)
    if mv:
        feast_name, rank, mv_color = mv
        color = mv_color
    else:
        fx = _fixed_lookup(d, calendar)
        if fx:
            feast_name, rank = fx["name"], fx["rank"]
            if rank in ("greatfeast", "feast"):
                color = fx.get("color", color)

    # Fasting discipline (abstinence from meat).
    is_greatfeast = rank == "greatfeast"

    # Fast-free periods when the weekly Wednesday/Friday abstinence is lifted
    # (meat is permitted even on Wed/Fri). Dates below are civil dates, so they
    # already reflect the +13-day shift on the Old (Julian) calendar.
    fast_free = (
        (pascha <= d <= pascha + timedelta(days=6))                              # Bright Week
        or (pentecost + timedelta(days=1) <= d <= pentecost + timedelta(days=6))  # week after Pentecost
        or (pascha - timedelta(days=69) <= d <= pascha - timedelta(days=63))      # Publican & Pharisee week
        or _win(12, 25, 1, 5)                                                     # Nativity → Theophany eve
    )
    # The Exaltation of the Cross (Sep 14), the Beheading of the Forerunner
    # (Aug 29) and Theophany Eve (Jan 5) are strict fast days on which meat is
    # abstained even though they fall outside the fasting seasons.
    key = d if calendar == "new" else d - timedelta(days=JULIAN_OFFSET_DAYS)
    strict_fixed = (key.month, key.day) in {(9, 14), (8, 29), (1, 5)}

    # Seasonal fasts abstain from meat every day (a great feast permits fish/wine
    # but not meat). The weekly Wed/Fri rule is lifted by a great feast or a
    # fast-free week.
    seasonal_meat = (
        in_lenten_meat_fast or in_nativity_fast or in_dormition_fast or in_apostles_fast
    )
    weekly_meat = (d.weekday() in (2, 4)) and not fast_free and not is_greatfeast
    is_abstinence = bool(seasonal_meat or weekly_meat or strict_fixed)
    # Strict-fast days (in addition to daily Great-Lent discipline).
    is_fast = bool(d in (lent_start, great_friday) or strict_fixed)

    return {
        "date": d.isoformat(),
        "season": season,
        "color": color,
        "feast": feast_name,
        "rank": rank,
        "is_abstinence": is_abstinence,
        "is_fast": is_fast,
        "is_sunday": is_sunday,
        "calendar": calendar,
    }


def _shift(d: date, calendar: str) -> date:
    """Civil date of a fixed feast under the chosen calendar."""
    return d if calendar == "new" else (d + timedelta(days=JULIAN_OFFSET_DAYS))


def get_eastern_month(year: int, month: int, calendar: str = "new") -> list:
    first = date(year, month, 1)
    if month == 12:
        nxt = date(year + 1, 1, 1)
    else:
        nxt = date(year, month + 1, 1)
    out = []
    d = first
    while d < nxt:
        out.append(get_eastern_day(d, calendar))
        d += timedelta(days=1)
    return out

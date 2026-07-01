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

    # Fixed-date fasts (feast day itself relaxes the fast).
    nativity_fast_start = _shift(date(year, 11, 15), calendar)
    nativity = _shift(date(year, 12, 25), calendar)
    dormition_fast_start = _shift(date(year, 8, 1), calendar)
    dormition = _shift(date(year, 8, 15), calendar)
    if nativity_fast_start <= d < nativity:
        season = "Nativity Fast (Philip's Fast)"
    elif dormition_fast_start <= d < dormition:
        season = "Dormition Fast"
    apostles_start = pentecost + timedelta(days=8)   # Monday after All Saints
    apostles_end = _shift(date(year, 6, 29), calendar)
    in_apostles_fast = apostles_start <= d < apostles_end

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

    # Fasting discipline: Great Lent + Holy Week; the great fasts; and the
    # weekly Wednesday/Friday fast (relaxed on great feasts).
    is_greatfeast = rank == "greatfeast"
    in_lent = lent_start <= d < pascha
    weekly_fast_day = d.weekday() in (2, 4)  # Wed / Fri
    in_fixed_fast = season in ("Nativity Fast (Philip's Fast)", "Dormition Fast")
    is_abstinence = (in_lent or in_fixed_fast or in_apostles_fast or weekly_fast_day) and not is_greatfeast
    # Strict fast days.
    is_fast = d in (great_friday, lent_start) and not is_greatfeast

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

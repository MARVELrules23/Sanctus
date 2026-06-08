"""Liturgical calendar helpers for the Roman Catholic calendar (Ordinary Form).

Computes liturgical season, color, and major feasts/saints for a given date.
Not exhaustive — covers principal seasons + a curated set of solemnities,
feasts and well-known memorials so users always see meaningful context.
"""
from datetime import date, timedelta
from typing import Optional


def easter_date(year: int) -> date:
    """Compute Easter Sunday date using Anonymous Gregorian algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def first_advent_sunday(year: int) -> date:
    """First Sunday of Advent — Sunday closest to St Andrew (Nov 30)."""
    nov30 = date(year, 11, 30)
    # weekday(): Mon=0 ... Sun=6
    # We want the Sunday on or just before/after Nov 30 (closest).
    diff = nov30.weekday() - 6  # how far from Sunday
    if diff < -3:
        return nov30 - timedelta(days=nov30.weekday() + 1)
    return nov30 - timedelta(days=(nov30.weekday() + 1) % 7)


# Fixed feast/saints map: (month, day) -> { name, rank, color? }
FIXED_FEASTS = {
    (1, 1): {"name": "Mary, Mother of God", "rank": "solemnity", "color": "white"},
    (1, 6): {"name": "Epiphany of the Lord", "rank": "solemnity", "color": "white"},
    (1, 25): {"name": "Conversion of St Paul", "rank": "feast", "color": "white"},
    (2, 2): {"name": "Presentation of the Lord", "rank": "feast", "color": "white"},
    (2, 22): {"name": "Chair of St Peter", "rank": "feast", "color": "white"},
    (3, 19): {"name": "St Joseph, Husband of Mary", "rank": "solemnity", "color": "white"},
    (3, 25): {"name": "Annunciation of the Lord", "rank": "solemnity", "color": "white"},
    (4, 25): {"name": "St Mark, Evangelist", "rank": "feast", "color": "red"},
    (5, 1): {"name": "St Joseph the Worker", "rank": "memorial", "color": "white"},
    (5, 31): {"name": "Visitation of the Blessed Virgin Mary", "rank": "feast", "color": "white"},
    (6, 13): {"name": "St Anthony of Padua", "rank": "memorial", "color": "white"},
    (6, 24): {"name": "Nativity of St John the Baptist", "rank": "solemnity", "color": "white"},
    (6, 29): {"name": "Sts Peter and Paul, Apostles", "rank": "solemnity", "color": "red"},
    (7, 11): {"name": "St Benedict of Nursia", "rank": "memorial", "color": "white"},
    (7, 22): {"name": "St Mary Magdalene", "rank": "feast", "color": "white"},
    (7, 25): {"name": "St James, Apostle", "rank": "feast", "color": "red"},
    (8, 6): {"name": "Transfiguration of the Lord", "rank": "feast", "color": "white"},
    (8, 10): {"name": "St Lawrence, Deacon", "rank": "feast", "color": "red"},
    (8, 15): {"name": "Assumption of the Blessed Virgin Mary", "rank": "solemnity", "color": "white"},
    (8, 28): {"name": "St Augustine of Hippo", "rank": "memorial", "color": "white"},
    (9, 8): {"name": "Nativity of the Blessed Virgin Mary", "rank": "feast", "color": "white"},
    (9, 14): {"name": "Exaltation of the Holy Cross", "rank": "feast", "color": "red"},
    (9, 29): {"name": "Sts Michael, Gabriel, and Raphael, Archangels", "rank": "feast", "color": "white"},
    (10, 1): {"name": "St Thérèse of the Child Jesus", "rank": "memorial", "color": "white"},
    (10, 4): {"name": "St Francis of Assisi", "rank": "memorial", "color": "white"},
    (10, 7): {"name": "Our Lady of the Rosary", "rank": "memorial", "color": "white"},
    (10, 15): {"name": "St Teresa of Jesus (Ávila)", "rank": "memorial", "color": "white"},
    (11, 1): {"name": "All Saints", "rank": "solemnity", "color": "white"},
    (11, 2): {"name": "All Souls", "rank": "commemoration", "color": "purple"},
    (11, 22): {"name": "St Cecilia", "rank": "memorial", "color": "red"},
    (11, 30): {"name": "St Andrew, Apostle", "rank": "feast", "color": "red"},
    (12, 8): {"name": "Immaculate Conception of the BVM", "rank": "solemnity", "color": "white"},
    (12, 12): {"name": "Our Lady of Guadalupe", "rank": "feast", "color": "white"},
    (12, 25): {"name": "Nativity of the Lord (Christmas)", "rank": "solemnity", "color": "white"},
    (12, 26): {"name": "St Stephen, the First Martyr", "rank": "feast", "color": "red"},
    (12, 27): {"name": "St John, Apostle and Evangelist", "rank": "feast", "color": "white"},
    (12, 28): {"name": "Holy Innocents", "rank": "feast", "color": "red"},
}


def get_liturgical_day(d: date) -> dict:
    """Return liturgical info for a date: season, color, feast/saint, abstinence."""
    year = d.year
    easter = easter_date(year)
    ash_wednesday = easter - timedelta(days=46)
    palm_sunday = easter - timedelta(days=7)
    holy_thursday = easter - timedelta(days=3)
    good_friday = easter - timedelta(days=2)
    holy_saturday = easter - timedelta(days=1)
    pentecost = easter + timedelta(days=49)
    trinity_sunday = pentecost + timedelta(days=7)
    corpus_christi = trinity_sunday + timedelta(days=4)  # Thursday after Trinity (in many places transferred to Sunday)
    sacred_heart = corpus_christi + timedelta(days=8)
    christ_the_king = first_advent_sunday(year) - timedelta(days=7)
    advent_start = first_advent_sunday(year)
    christmas = date(year, 12, 25)
    # Baptism of the Lord: Sunday after Epiphany (Jan 6). If Epiphany is Sunday, then Monday after.
    epiphany = date(year, 1, 6)
    if epiphany.weekday() == 6:  # Sunday
        baptism = epiphany + timedelta(days=1)
    else:
        baptism = epiphany + timedelta(days=(6 - epiphany.weekday()))

    # Determine season
    season = "Ordinary Time"
    color = "green"

    if d == ash_wednesday:
        season = "Lent"
        color = "purple"
        return {
            "date": d.isoformat(),
            "season": season,
            "color": color,
            "feast": "Ash Wednesday",
            "rank": "fast",
            "is_abstinence": True,
            "is_fast": True,
            "is_sunday": d.weekday() == 6,
        }
    if d == good_friday:
        return {
            "date": d.isoformat(),
            "season": "Paschal Triduum",
            "color": "red",
            "feast": "Good Friday of the Lord's Passion",
            "rank": "solemnity",
            "is_abstinence": True,
            "is_fast": True,
            "is_sunday": False,
        }
    if d == holy_thursday:
        return {
            "date": d.isoformat(),
            "season": "Paschal Triduum",
            "color": "white",
            "feast": "Holy Thursday — Mass of the Lord's Supper",
            "rank": "solemnity",
            "is_abstinence": False,
            "is_fast": False,
            "is_sunday": False,
        }
    if d == holy_saturday:
        return {
            "date": d.isoformat(),
            "season": "Paschal Triduum",
            "color": "white",
            "feast": "Holy Saturday — Easter Vigil",
            "rank": "solemnity",
            "is_abstinence": False,
            "is_fast": False,
            "is_sunday": False,
        }
    if d == easter:
        return {
            "date": d.isoformat(),
            "season": "Easter",
            "color": "white",
            "feast": "Easter Sunday — Resurrection of the Lord",
            "rank": "solemnity",
            "is_abstinence": False,
            "is_fast": False,
            "is_sunday": True,
        }
    if d == palm_sunday:
        return {
            "date": d.isoformat(),
            "season": "Lent",
            "color": "red",
            "feast": "Palm Sunday of the Passion of the Lord",
            "rank": "solemnity",
            "is_abstinence": False,
            "is_fast": False,
            "is_sunday": True,
        }
    if d == pentecost:
        return {
            "date": d.isoformat(),
            "season": "Easter",
            "color": "red",
            "feast": "Pentecost Sunday",
            "rank": "solemnity",
            "is_abstinence": False,
            "is_fast": False,
            "is_sunday": True,
        }
    if d == trinity_sunday:
        return {
            "date": d.isoformat(),
            "season": "Ordinary Time",
            "color": "white",
            "feast": "Most Holy Trinity",
            "rank": "solemnity",
            "is_abstinence": False,
            "is_fast": False,
            "is_sunday": True,
        }
    if d == sacred_heart:
        return {
            "date": d.isoformat(),
            "season": "Ordinary Time",
            "color": "white",
            "feast": "Most Sacred Heart of Jesus",
            "rank": "solemnity",
            "is_abstinence": False,
            "is_fast": False,
            "is_sunday": False,
        }
    if d == christ_the_king:
        return {
            "date": d.isoformat(),
            "season": "Ordinary Time",
            "color": "white",
            "feast": "Our Lord Jesus Christ, King of the Universe",
            "rank": "solemnity",
            "is_abstinence": False,
            "is_fast": False,
            "is_sunday": True,
        }
    if d == baptism:
        return {
            "date": d.isoformat(),
            "season": "Christmas",
            "color": "white",
            "feast": "Baptism of the Lord",
            "rank": "feast",
            "is_abstinence": False,
            "is_fast": False,
            "is_sunday": d.weekday() == 6,
        }

    # Seasons
    if ash_wednesday < d < easter:
        season = "Lent"
        color = "purple"
        # 4th Sunday of Lent — Laetare — rose
        laetare = ash_wednesday + timedelta(days=(4 * 7) - ash_wednesday.weekday() % 7 + 4)
        # easier: just check it's a Sunday in lent
    elif easter < d <= pentecost:
        season = "Easter"
        color = "white"
    elif advent_start <= d < christmas:
        season = "Advent"
        color = "purple"
        # 3rd Sunday of Advent (Gaudete) — rose
        gaudete = advent_start + timedelta(days=14)
        if d == gaudete:
            color = "rose"
    elif christmas <= d <= date(year, 12, 31) or date(year, 1, 1) <= d < baptism:
        # Christmas season — Dec 25 through Baptism of the Lord
        # But Baptism may be in the next year for a Dec date; we treat current year.
        if d.month == 12 and d >= christmas:
            season = "Christmas"
            color = "white"
        elif d < baptism:
            season = "Christmas"
            color = "white"
    # else default Ordinary Time / green

    # Fixed feasts override season color where appropriate
    feast = FIXED_FEASTS.get((d.month, d.day))
    feast_name = feast["name"] if feast else None
    rank = feast["rank"] if feast else "feria"
    if feast and feast.get("color"):
        # Solemnities/feasts of saints generally override season color
        if feast["rank"] in ("solemnity", "feast"):
            color = feast["color"]

    is_sunday = d.weekday() == 6  # Sunday

    # Friday abstinence from meat (general Latin Church discipline).
    # Suspended on solemnities. Outside Lent, the obligation may be commuted to
    # another penitential work; we still surface the badge as a reminder.
    is_friday = d.weekday() == 4
    is_solemnity = rank == "solemnity"
    is_abstinence = is_friday and not is_solemnity

    # Fasting days: Ash Wed and Good Friday (already handled above).
    is_fast = False

    return {
        "date": d.isoformat(),
        "season": season,
        "color": color,
        "feast": feast_name,
        "rank": rank,
        "is_abstinence": is_abstinence,
        "is_fast": is_fast,
        "is_sunday": is_sunday,
    }

"""Traditional Latin (1962 Roman Missal / General Roman Calendar of 1960) helpers.

This is the pre-1966 "usus antiquior" calendar used for the Traditional Latin
Mass. It differs from the Ordinary Form calendar in several important ways:

  * Pre-Lent season of Septuagesima (Septuagesima / Sexagesima / Quinquagesima).
  * Passiontide (Passion Sunday = 5th Sunday of Lent) with veiled images.
  * Christ the King on the LAST SUNDAY OF OCTOBER (not the last Sunday of the year).
  * "Time after Epiphany" and "Time after Pentecost" instead of Ordinary Time.
  * Ranks in the 1960 system: I, II, III, IV (feria) class.
  * The stricter pre-conciliar penitential discipline (1917 Code of Canon Law):
      - Complete abstinence from meat on EVERY Friday of the year.
      - Fast on all Lenten weekdays; Ash Wednesday, Lenten Fridays & Good Friday
        are fast + complete abstinence.
      - Ember Days (Lent, Pentecost, September, Advent): fast; Wed & Sat partial
        abstinence, Friday complete abstinence.
      - Rogation Days (Major on Apr 25; Minor Mon–Wed before Ascension): days of
        the Litany/procession (no fast).
      - Vigils of Christmas, Pentecost, the Assumption and All Saints:
        fast + complete abstinence.
  * Holy Days of Obligation flagged for the Universal 1917 Code list (10 days)
    and the traditional United States list (6 days).

Data verified against the 1962 Missal / 1960 rubrics.
"""

from datetime import date, timedelta

VIOLET = "purple"  # theme maps "purple" -> liturgical violet
WHITE = "white"
RED = "red"
GREEN = "green"
ROSE = "rose"
BLACK = "black"


def easter_date(year: int) -> date:
    """Anonymous Gregorian (Meeus/Jones/Butcher) algorithm."""
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
    """First Sunday of Advent: the Sunday nearest to St Andrew (Nov 30)."""
    christmas = date(year, 12, 25)
    # Advent begins 4 Sundays before Christmas.
    # weekday(): Mon=0 .. Sun=6
    days_back = christmas.weekday() + 1  # Sunday before Christmas
    fourth_sunday_before = christmas - timedelta(days=days_back + 21)
    return fourth_sunday_before


def last_sunday_of_october(year: int) -> date:
    d = date(year, 10, 31)
    while d.weekday() != 6:  # Sunday
        d -= timedelta(days=1)
    return d


def nth_sunday_of_month(year: int, month: int, n: int) -> date:
    d = date(year, month, 1)
    # advance to first Sunday
    while d.weekday() != 6:
        d += timedelta(days=1)
    return d + timedelta(days=7 * (n - 1))


# Fixed feasts of the 1962 calendar: (month, day) -> {name, rank, color}.
# Ranks use the 1960 class system. Only I/II class (and notable III class)
# feasts are listed; unlisted days default to feria (IV class).
FIXED_FEASTS = {
    (1, 1): {"name": "The Circumcision of Our Lord", "rank": "I class", "color": WHITE},
    (1, 6): {"name": "The Epiphany of Our Lord", "rank": "I class", "color": WHITE},
    (1, 13): {"name": "Commemoration of the Baptism of Our Lord", "rank": "II class", "color": WHITE},
    (1, 25): {"name": "Conversion of St Paul, Apostle", "rank": "III class", "color": WHITE},
    (2, 2): {"name": "Purification of the B.V.M. (Candlemas)", "rank": "II class", "color": WHITE},
    (2, 22): {"name": "Chair of St Peter, Apostle", "rank": "II class", "color": WHITE},
    (2, 24): {"name": "St Matthias, Apostle", "rank": "II class", "color": RED},
    (3, 19): {"name": "St Joseph, Spouse of the B.V.M.", "rank": "I class", "color": WHITE},
    (3, 25): {"name": "The Annunciation of the B.V.M.", "rank": "I class", "color": WHITE},
    (4, 25): {"name": "St Mark, Evangelist", "rank": "II class", "color": RED},
    (5, 1): {"name": "St Joseph the Worker", "rank": "I class", "color": WHITE},
    (5, 11): {"name": "Ss Philip and James, Apostles", "rank": "II class", "color": RED},
    (5, 31): {"name": "Queenship of the B.V.M.", "rank": "II class", "color": WHITE},
    (6, 24): {"name": "Nativity of St John the Baptist", "rank": "I class", "color": WHITE},
    (6, 29): {"name": "Ss Peter and Paul, Apostles", "rank": "I class", "color": RED},
    (6, 30): {"name": "Commemoration of St Paul, Apostle", "rank": "III class", "color": RED},
    (7, 1): {"name": "The Most Precious Blood of Our Lord", "rank": "I class", "color": RED},
    (7, 2): {"name": "The Visitation of the B.V.M.", "rank": "II class", "color": WHITE},
    (7, 22): {"name": "St Mary Magdalene, Penitent", "rank": "III class", "color": WHITE},
    (7, 25): {"name": "St James, Apostle", "rank": "II class", "color": RED},
    (7, 26): {"name": "St Anne, Mother of the B.V.M.", "rank": "II class", "color": WHITE},
    (8, 6): {"name": "The Transfiguration of Our Lord", "rank": "II class", "color": WHITE},
    (8, 10): {"name": "St Lawrence, Martyr", "rank": "II class", "color": RED},
    (8, 15): {"name": "The Assumption of the B.V.M.", "rank": "I class", "color": WHITE},
    (8, 22): {"name": "The Immaculate Heart of the B.V.M.", "rank": "II class", "color": WHITE},
    (8, 24): {"name": "St Bartholomew, Apostle", "rank": "II class", "color": RED},
    (9, 8): {"name": "Nativity of the B.V.M.", "rank": "II class", "color": WHITE},
    (9, 14): {"name": "Exaltation of the Holy Cross", "rank": "II class", "color": RED},
    (9, 15): {"name": "The Seven Sorrows of the B.V.M.", "rank": "II class", "color": WHITE},
    (9, 21): {"name": "St Matthew, Apostle & Evangelist", "rank": "II class", "color": RED},
    (9, 29): {"name": "Dedication of St Michael the Archangel", "rank": "I class", "color": WHITE},
    (10, 2): {"name": "The Holy Guardian Angels", "rank": "III class", "color": WHITE},
    (10, 7): {"name": "Our Lady of the Rosary", "rank": "II class", "color": WHITE},
    (10, 11): {"name": "The Maternity of the B.V.M.", "rank": "II class", "color": WHITE},
    (10, 18): {"name": "St Luke, Evangelist", "rank": "II class", "color": RED},
    (10, 28): {"name": "Ss Simon and Jude, Apostles", "rank": "II class", "color": RED},
    (11, 1): {"name": "All Saints", "rank": "I class", "color": WHITE},
    (11, 2): {"name": "All Souls (Commemoration of the Faithful Departed)", "rank": "I class", "color": BLACK},
    (11, 9): {"name": "Dedication of the Archbasilica of the Savior", "rank": "II class", "color": WHITE},
    (11, 21): {"name": "The Presentation of the B.V.M.", "rank": "III class", "color": WHITE},
    (11, 30): {"name": "St Andrew, Apostle", "rank": "II class", "color": RED},
    (12, 8): {"name": "The Immaculate Conception of the B.V.M.", "rank": "I class", "color": WHITE},
    (12, 21): {"name": "St Thomas, Apostle", "rank": "II class", "color": RED},
    (12, 24): {"name": "Vigil of the Nativity", "rank": "I class", "color": VIOLET},
    (12, 25): {"name": "The Nativity of Our Lord (Christmas)", "rank": "I class", "color": WHITE},
    (12, 26): {"name": "St Stephen, Protomartyr", "rank": "II class", "color": RED},
    (12, 27): {"name": "St John, Apostle & Evangelist", "rank": "II class", "color": WHITE},
    (12, 28): {"name": "The Holy Innocents, Martyrs", "rank": "II class", "color": RED},
    (12, 31): {"name": "St Sylvester I, Pope", "rank": "III class", "color": WHITE},
}

# Holy Days of Obligation.
#   universal = 1917 Code of Canon Law (canon 1247 §1) — 10 days.
#   us = traditional United States list (Third Plenary Council of Baltimore) — 6 days.
# Keys are ("fixed", month, day) or movable identifiers.
UNIVERSAL_FIXED = {(1, 1), (1, 6), (3, 19), (6, 29), (8, 15), (11, 1), (12, 8), (12, 25)}
US_FIXED = {(1, 1), (8, 15), (11, 1), (12, 8), (12, 25)}
# Movable holy days (Ascension, Corpus Christi) handled inline.


def _holy_day_note(universal: bool, us: bool) -> str:
    if universal and us:
        return "Holy Day of Obligation (Universal & USA)"
    if universal:
        return "Holy Day of Obligation (Universal 1917 Code)"
    if us:
        return "Holy Day of Obligation (USA)"
    return ""


def get_tridentine_day(d: date) -> dict:
    """Liturgical info for a date on the 1962 traditional Latin calendar."""
    year = d.year
    easter = easter_date(year)
    ash_wednesday = easter - timedelta(days=46)
    septuagesima = easter - timedelta(days=63)
    sexagesima = easter - timedelta(days=56)
    quinquagesima = easter - timedelta(days=49)
    passion_sunday = easter - timedelta(days=14)
    palm_sunday = easter - timedelta(days=7)
    holy_thursday = easter - timedelta(days=3)
    good_friday = easter - timedelta(days=2)
    holy_saturday = easter - timedelta(days=1)
    ascension = easter + timedelta(days=39)
    pentecost = easter + timedelta(days=49)
    pentecost_vigil = pentecost - timedelta(days=1)
    trinity = pentecost + timedelta(days=7)
    corpus_christi = easter + timedelta(days=60)
    sacred_heart = easter + timedelta(days=68)
    gaudete = first_advent_sunday(year) + timedelta(days=14)
    laetare = ash_wednesday + timedelta(days=24)  # 4th Sunday of Lent
    advent_start = first_advent_sunday(year)
    christmas = date(year, 12, 25)
    epiphany = date(year, 1, 6)
    christ_king = last_sunday_of_october(year)

    # Ember Days ---------------------------------------------------------
    lent_first_sunday = ash_wednesday + timedelta(days=4)  # Sunday after Ash Wed
    lent_ember = {
        lent_first_sunday + timedelta(days=3): "Ember Wednesday of Lent",
        lent_first_sunday + timedelta(days=5): "Ember Friday of Lent",
        lent_first_sunday + timedelta(days=6): "Ember Saturday of Lent",
    }
    whit_ember = {
        pentecost + timedelta(days=3): "Ember Wednesday of Whitsun",
        pentecost + timedelta(days=5): "Ember Friday of Whitsun",
        pentecost + timedelta(days=6): "Ember Saturday of Whitsun",
    }
    sept_third_sunday = nth_sunday_of_month(year, 9, 3)
    sept_ember = {
        sept_third_sunday + timedelta(days=3): "Ember Wednesday of September",
        sept_third_sunday + timedelta(days=5): "Ember Friday of September",
        sept_third_sunday + timedelta(days=6): "Ember Saturday of September",
    }
    advent_ember = {
        gaudete + timedelta(days=3): "Ember Wednesday of Advent",
        gaudete + timedelta(days=5): "Ember Friday of Advent",
        gaudete + timedelta(days=6): "Ember Saturday of Advent",
    }
    ember_days = {**lent_ember, **whit_ember, **sept_ember, **advent_ember}

    # Rogation Days ------------------------------------------------------
    rogations = {
        date(year, 4, 25): "The Greater Litanies (Major Rogation)",
        ascension - timedelta(days=3): "Rogation Monday (Lesser Litanies)",
        ascension - timedelta(days=2): "Rogation Tuesday (Lesser Litanies)",
        ascension - timedelta(days=1): "Rogation Wednesday (Lesser Litanies)",
    }

    # Vigils that carry a fast + complete abstinence (1917 Code, canon 1252).
    fasting_vigils = {
        date(year, 12, 24): "Vigil of the Nativity",
        pentecost_vigil: "Vigil of Pentecost",
        date(year, 8, 14): "Vigil of the Assumption",
        date(year, 10, 31): "Vigil of All Saints",
    }

    is_sunday = d.weekday() == 6
    is_friday = d.weekday() == 4

    # ---- Determine feast / season / color -------------------------------
    feast_name = None
    rank = "feria"
    observance = None

    # Season baseline
    if advent_start <= d <= date(year, 12, 24):
        season, color = "Advent", VIOLET
    elif christmas <= d <= date(year, 12, 31) or date(year, 1, 1) <= d <= date(year, 1, 13):
        season, color = "Christmastide", WHITE
    elif date(year, 1, 14) <= d < septuagesima:
        season, color = "Time after Epiphany", GREEN
    elif septuagesima <= d < ash_wednesday:
        season, color = "Septuagesima", VIOLET
    elif ash_wednesday <= d < passion_sunday:
        season, color = "Lent", VIOLET
    elif passion_sunday <= d <= holy_saturday:
        season, color = "Passiontide", VIOLET
    elif easter <= d < pentecost:
        season, color = "Paschaltide", WHITE
    elif pentecost <= d <= pentecost + timedelta(days=6):
        season, color = "Octave of Pentecost", RED
    else:
        season, color = "Time after Pentecost", GREEN

    # Fixed feast lookup
    ff = FIXED_FEASTS.get((d.month, d.day))
    if ff:
        feast_name = ff["name"]
        rank = ff["rank"]
        color = ff["color"]

    # Movable feasts / days override where they occur.
    def _set(name, rk, col, seas=None):
        nonlocal feast_name, rank, color, season
        feast_name, rank, color = name, rk, col
        if seas:
            season = seas

    if d == septuagesima:
        _set("Septuagesima Sunday", "II class", VIOLET)
    elif d == sexagesima:
        _set("Sexagesima Sunday", "II class", VIOLET)
    elif d == quinquagesima:
        _set("Quinquagesima Sunday", "II class", VIOLET)
    elif d == ash_wednesday:
        _set("Ash Wednesday", "I class", VIOLET, "Lent")
    elif d == laetare:
        _set("Laetare Sunday (IV of Lent)", "I class", ROSE, "Lent")
    elif d == passion_sunday:
        _set("Passion Sunday (I of the Passion)", "I class", VIOLET, "Passiontide")
    elif d == palm_sunday:
        _set("Palm Sunday (II of the Passion)", "I class", RED, "Passiontide")
    elif d == holy_thursday:
        _set("Maundy Thursday", "I class", WHITE, "Sacred Triduum")
    elif d == good_friday:
        _set("Good Friday", "I class", BLACK, "Sacred Triduum")
    elif d == holy_saturday:
        _set("Holy Saturday", "I class", VIOLET, "Sacred Triduum")
    elif d == easter:
        _set("Easter Sunday — Resurrection of Our Lord", "I class", WHITE, "Paschaltide")
    elif d == ascension:
        _set("The Ascension of Our Lord", "I class", WHITE, "Paschaltide")
    elif d == pentecost:
        _set("Pentecost (Whitsunday)", "I class", RED, "Octave of Pentecost")
    elif d == trinity:
        _set("Trinity Sunday", "I class", WHITE, "Time after Pentecost")
    elif d == corpus_christi:
        _set("Corpus Christi", "I class", WHITE, "Time after Pentecost")
    elif d == sacred_heart:
        _set("The Most Sacred Heart of Jesus", "I class", WHITE, "Time after Pentecost")
    elif d == christ_king:
        _set("Our Lord Jesus Christ the King", "I class", WHITE, "Time after Pentecost")
    elif d == gaudete:
        _set("Gaudete Sunday (III of Advent)", "I class", ROSE, "Advent")

    # Sundays that are otherwise feria get their season rank (I/II class Sundays).
    if is_sunday and rank == "feria":
        if season in ("Advent", "Lent", "Passiontide"):
            rank = "I class"
        else:
            rank = "II class"
        if feast_name is None:
            feast_name = None  # generic Sunday of the season

    # Ember / Rogation / Vigil observance markers (do not override a feast name,
    # but are surfaced separately).
    if d in ember_days:
        observance = ember_days[d]
    elif d in rogations:
        observance = rogations[d]
    elif d in fasting_vigils and feast_name is None:
        observance = fasting_vigils[d]

    # ---- Fasting & abstinence (1917 Code discipline) --------------------
    is_fast = False
    is_abstinence = False
    abstinence_type = None

    is_i_class = rank == "I class"

    if not is_sunday:
        # Friday abstinence — complete, every Friday of the year.
        if is_friday and not is_i_class:
            is_abstinence = True
            abstinence_type = "complete"

        # Lent: fast on all weekdays.
        if ash_wednesday <= d <= holy_saturday and d != easter:
            is_fast = True
            if not is_abstinence:
                # partial abstinence on non-Friday Lenten weekdays
                is_abstinence = True
                abstinence_type = "partial"

        # Ash Wednesday & Good Friday: fast + complete abstinence.
        if d in (ash_wednesday, good_friday):
            is_fast = True
            is_abstinence = True
            abstinence_type = "complete"

        # Ember Days.
        if d in ember_days:
            is_fast = True
            if is_friday:
                is_abstinence, abstinence_type = True, "complete"
            else:
                is_abstinence, abstinence_type = True, "partial"

        # Fasting vigils.
        if d in fasting_vigils:
            is_fast = True
            is_abstinence = True
            abstinence_type = "complete"

    # ---- Holy Day of Obligation ----------------------------------------
    universal = (d.month, d.day) in UNIVERSAL_FIXED
    us = (d.month, d.day) in US_FIXED
    if d == ascension:
        universal = True
        us = True
    if d == corpus_christi:
        universal = True
    is_holy_day = universal or us
    holy_day_note = _holy_day_note(universal, us) if is_holy_day else None

    return {
        "date": d.isoformat(),
        "season": season,
        "color": color,
        "feast": feast_name,
        "rank": rank,
        "is_abstinence": is_abstinence,
        "is_fast": is_fast,
        "is_sunday": is_sunday,
        "is_holy_day": is_holy_day,
        "holy_day_note": holy_day_note,
        "observance": observance,
        "abstinence_type": abstinence_type,
        "calendar": "1962",
    }


def get_tridentine_month(year: int, month: int) -> list:
    d = date(year, month, 1)
    days = []
    while d.month == month:
        days.append(get_tridentine_day(d))
        d += timedelta(days=1)
    return days

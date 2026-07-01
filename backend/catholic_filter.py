"""Shared filter: only churches in full communion with Rome.

Covers the Latin (Roman) Church, all 23 Eastern Catholic Churches (Byzantine,
Alexandrian, Antiochene/West-Syriac, Chaldean/East-Syriac, Armenian) and the
Personal Ordinariates. Explicitly EXCLUDES bodies that use "Catholic" in their
name but are NOT in communion with Rome (Old Catholic, Polish National Catholic,
Liberal Catholic, Chinese Patriotic, independent/apostolic "catholic" groups),
as well as any Orthodox / Protestant / Anglican community.
"""

# Denomination substrings that indicate a Church in communion with Rome.
ALLOW_SUBSTR = (
    "catholic",          # roman_catholic, greek_catholic, chaldean_catholic, coptic_catholic, ...
    "maronite",
    "melkite",
    "chaldean",
    "ruthenian",
    "syro_malabar",
    "syro_malankara",
    "syro-malabar",
    "syro-malankara",
    "ordinariate",
)

# Substrings that DISQUALIFY a place even if it also contains "catholic".
BLOCK_SUBSTR = (
    "old_catholic",
    "old-catholic",
    "old catholic",
    "altkatholisch",          # German "Old Catholic"
    "polish_national",
    "polish national",
    "national_catholic",
    "liberal_catholic",
    "liberal catholic",
    "chinese_patriotic",
    "patriotic",
    "independent_catholic",
    "independent catholic",
    "apostolic_catholic",
    "reformed_catholic",
    "orthodox",
    "anglican",
    "protestant",
    "lutheran",
    "evangelical",
)

# --- Overpass (OSM) tag filters -------------------------------------------
_POS = (
    "catholic|maronite|melkite|chaldean|ruthenian|"
    "syro_malabar|syro_malankara|syro-malabar|syro-malankara|ordinariate"
)
_NEG = (
    "old_catholic|old-catholic|altkatholisch|polish_national|national_catholic|"
    "liberal_catholic|chinese_patriotic|patriotic|independent_catholic|"
    "apostolic_catholic|reformed_catholic|orthodox|anglican|protestant|lutheran|evangelical"
)


def overpass_denomination_filter() -> str:
    """Overpass tag-filter fragment: keep Catholic-in-communion, drop the rest."""
    return f'["denomination"~"{_POS}",i]["denomination"!~"{_NEG}",i]'


def is_catholic_denomination(denomination: str) -> bool:
    """True only for a denomination string in communion with Rome."""
    d = (denomination or "").lower().strip()
    if not d:
        return False
    if any(b in d for b in BLOCK_SUBSTR):
        return False
    return any(a in d for a in ALLOW_SUBSTR)


def is_catholic_place(tags: dict) -> bool:
    """Classify an OSM place-of-worship as Catholic (in communion with Rome).

    Uses the denomination tag first; falls back to religion/name only with
    strict Catholic/Eastern-rite keywords (never generic 'St.'/'Cathedral').
    """
    denom = (tags.get("denomination") or "").lower().strip()
    if denom:
        return is_catholic_denomination(denom)
    religion = (tags.get("religion") or "").lower().strip()
    if religion == "catholic":
        return True
    if religion in ("christian", ""):
        name = (tags.get("name") or "").lower()
        if any(b in name for b in BLOCK_SUBSTR):
            return False
        if any(k in name for k in ("catholic", "maronite", "melkite", "ordinariate",
                                    "syro-malabar", "syro malabar", "syro-malankara")):
            return True
    return False


# --- Rite classification (for badges & profile) ---------------------------
RITE_LABELS = {
    "latin": "Latin (Roman)",
    "byzantine": "Byzantine",
    "maronite": "Maronite",
    "chaldean": "Chaldean",
    "syro_malabar": "Syro-Malabar",
    "syro_malankara": "Syro-Malankara",
    "coptic": "Coptic",
    "armenian": "Armenian",
    "syriac": "Syriac",
    "ordinariate": "Ordinariate",
}
RITE_KEYS = set(RITE_LABELS)


def rite_label(key: str) -> str:
    return RITE_LABELS.get((key or "").lower().strip(), "")


def rite_from_denomination(denomination: str) -> str:
    """Best-effort rite key from an OSM denomination (or ''). '' if unknown."""
    if not is_catholic_denomination(denomination):
        return ""
    d = denomination.lower()
    if "maronite" in d:
        return "maronite"
    if "syro_malabar" in d or "syro-malabar" in d:
        return "syro_malabar"
    if "syro_malankara" in d or "syro-malankara" in d:
        return "syro_malankara"
    if "chaldean" in d:
        return "chaldean"
    if "coptic" in d:
        return "coptic"
    if "armenian" in d:
        return "armenian"
    if "syriac" in d or "syrian" in d:
        return "syriac"
    if "ordinariate" in d:
        return "ordinariate"
    if any(k in d for k in ("melkite", "greek_catholic", "ukrainian", "ruthenian",
                            "romanian", "byzantine", "russian_catholic", "slovak",
                            "hungarian", "croatian", "macedonian", "belarusian")):
        return "byzantine"
    # roman_catholic / catholic and everything else in communion → Latin.
    return "latin"


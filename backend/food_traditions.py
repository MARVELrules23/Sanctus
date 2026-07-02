"""Catholic feast-day & seasonal food traditions people can make at home.

A small curated catalogue keyed to feasts (matched against the liturgical day's
`feast` string) and seasons (`season`). Each entry carries a simple home recipe.
Display text is localized (EN/ES/IT) through the shared cached translator; the
ingredient/step *lists* are localized too so the whole card reads in-language.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from lang_ctx import get_lang
from i18n_translate import translate_texts

_LLM_KEY = ""


def set_llm_key(key: str) -> None:
    global _LLM_KEY
    _LLM_KEY = key or ""


# `feasts` are lowercase substrings matched against the day's feast name.
# `seasons` match the liturgical season exactly (Advent, Christmas, Lent, Easter,
# Ordinary Time). A tradition with neither is browse-only.
TRADITIONS: List[Dict[str, Any]] = [
    {
        "slug": "kings-cake-epiphany", "title": "Three Kings' Cake (Rosca de Reyes)",
        "origin": "Spain & Latin America", "occasion": "Epiphany",
        "icon": "star-outline", "color": "#8A6A2E",
        "feasts": ["epiphany", "three kings"], "seasons": [],
        "description": "A ring-shaped sweet bread crowned with candied fruit, baked for Epiphany. A small figure of the Christ Child is hidden inside; whoever finds it hosts the Candlemas celebration.",
        "ingredients": ["3 cups flour", "1/2 cup sugar", "2 eggs", "1 packet yeast", "1/2 cup warm milk", "1/3 cup butter", "Orange-blossom water", "Candied fruit & a dried bean or small figure"],
        "steps": ["Bloom the yeast in warm milk with a spoon of sugar.", "Mix flour, sugar, eggs, butter and yeast into a soft dough; knead until smooth.", "Let rise until doubled, then shape into a ring on a tray.", "Tuck a small figure of the Christ Child inside; decorate with candied fruit.", "Let rise again, then bake at 180°C (350°F) for 25–30 minutes until golden."],
    },
    {
        "slug": "st-lucia-buns", "title": "St. Lucy's Saffron Buns (Lussekatter)",
        "origin": "Sweden", "occasion": "St. Lucy (Dec 13)",
        "icon": "flame-outline", "color": "#C8961E",
        "feasts": ["lucy", "lucia"], "seasons": [],
        "description": "Golden saffron buns eaten on St. Lucy's day, when the eldest daughter serves them wearing a crown of candles — a sign of Christ the Light coming in Advent.",
        "ingredients": ["4 cups flour", "1 pinch saffron", "3/4 cup sugar", "1 packet yeast", "1 cup warm milk", "1/3 cup butter", "1 egg", "Raisins"],
        "steps": ["Steep saffron in a little warm milk.", "Bloom yeast in the rest of the warm milk.", "Knead all into a soft dough; rise until doubled.", "Roll into S-shapes and press a raisin into each coil.", "Rise again, brush with egg, and bake at 200°C (400°F) for 10–12 minutes."],
    },
    {
        "slug": "st-joseph-zeppole", "title": "St. Joseph's Zeppole",
        "origin": "Italy", "occasion": "St. Joseph (Mar 19)",
        "icon": "cafe-outline", "color": "#7A5C2E",
        "feasts": ["joseph"], "seasons": [],
        "description": "Cream-filled pastries traditionally eaten on the Solemnity of St. Joseph, patron of fathers and workers — a joyful table even in Lent.",
        "ingredients": ["1 cup water", "1/2 cup butter", "1 cup flour", "4 eggs", "Pastry cream", "Powdered sugar", "Amarena cherries"],
        "steps": ["Boil water and butter; stir in flour until a ball forms.", "Off heat, beat in eggs one at a time to a smooth choux paste.", "Pipe rings onto a tray; bake at 200°C (400°F) for 20–25 minutes until puffed.", "Cool, then fill with pastry cream.", "Dust with powdered sugar and top with a cherry."],
    },
    {
        "slug": "hot-cross-buns", "title": "Hot Cross Buns",
        "origin": "England", "occasion": "Good Friday / Lent",
        "icon": "add-outline", "color": "#8A4B2E",
        "feasts": ["good friday"], "seasons": ["Lent"],
        "description": "Spiced buns marked with a cross, eaten in Lent and especially on Good Friday — the cross recalling the Passion and the spices the burial of the Lord.",
        "ingredients": ["4 cups flour", "1/4 cup sugar", "1 packet yeast", "1 cup warm milk", "1/4 cup butter", "1 egg", "2 tsp mixed spice", "Currants", "Flour paste for crosses"],
        "steps": ["Bloom yeast in warm milk.", "Mix in flour, sugar, spice, butter, egg and currants; knead and rise.", "Shape into buns; pipe a flour-water cross on each.", "Rise again, then bake at 200°C (400°F) for 18–20 minutes.", "Glaze with warm apricot jam while hot."],
    },
    {
        "slug": "easter-lamb-cake", "title": "Easter Lamb Cake (Agnus Dei)",
        "origin": "Poland & Central Europe", "occasion": "Easter Sunday",
        "icon": "happy-outline", "color": "#C9A84C",
        "feasts": ["resurrection", "easter"], "seasons": ["Easter"],
        "description": "A butter cake baked in a lamb-shaped mould for Easter dinner, honouring Christ the Paschal Lamb who rose from the dead.",
        "ingredients": ["1 cup butter", "1 cup sugar", "4 eggs", "2 cups flour", "2 tsp baking powder", "1 tsp vanilla", "Powdered sugar", "A red ribbon & small banner"],
        "steps": ["Cream butter and sugar; beat in eggs and vanilla.", "Fold in flour and baking powder to a thick batter.", "Grease a lamb mould well and fill; bake at 175°C (350°F) for 45–55 minutes.", "Cool fully before unmoulding.", "Dust with powdered sugar and set with a little red-cross banner."],
    },
    {
        "slug": "pentecost-dove-bread", "title": "Pentecost Dove Bread (Colomba)",
        "origin": "Italy", "occasion": "Pentecost",
        "icon": "cloud-outline", "color": "#A0821E",
        "feasts": ["pentecost"], "seasons": [],
        "description": "A dove-shaped sweet bread for Pentecost, recalling the Holy Spirit descending like a dove and the tongues of fire upon the Apostles.",
        "ingredients": ["3 cups flour", "1/2 cup sugar", "1 packet yeast", "1/2 cup warm milk", "3 eggs", "1/3 cup butter", "Orange zest", "Pearl sugar & almonds"],
        "steps": ["Bloom yeast in warm milk.", "Knead flour, sugar, eggs, butter and orange zest into a rich dough; rise.", "Shape into a dove (or a simple round) on a tray.", "Top with almonds and pearl sugar.", "Rise again and bake at 180°C (350°F) for 30–35 minutes."],
    },
    {
        "slug": "all-souls-bread", "title": "Bread of the Dead (Pan de Muerto)",
        "origin": "Mexico", "occasion": "All Souls (Nov 2)",
        "icon": "flower-outline", "color": "#7A3E5B",
        "feasts": ["all souls", "all saints"], "seasons": [],
        "description": "A soft orange-scented bread shaped with 'bones' on top, shared while praying for the faithful departed on All Souls' Day.",
        "ingredients": ["4 cups flour", "1/2 cup sugar", "1 packet yeast", "1/2 cup warm milk", "4 eggs", "1/2 cup butter", "Orange-blossom water & zest", "Sugar for dusting"],
        "steps": ["Bloom yeast in warm milk.", "Knead flour, sugar, eggs, butter and orange into a soft dough; rise.", "Shape into a round; roll 'bone' strips and cross them on top.", "Rise again, then bake at 180°C (350°F) for 30 minutes.", "Brush with butter and roll in sugar while warm."],
    },
    {
        "slug": "advent-wreath-cookies", "title": "Advent Spice Cookies (Lebkuchen)",
        "origin": "Germany", "occasion": "Advent",
        "icon": "leaf-outline", "color": "#5B4B7A",
        "feasts": [], "seasons": ["Advent"],
        "description": "Soft, honey-spiced cookies baked through Advent as the family keeps vigil for the coming of the Lord around the Advent wreath.",
        "ingredients": ["1/2 cup honey", "1/3 cup sugar", "1 egg", "2 cups flour", "1 tbsp mixed spice (cinnamon, clove, nutmeg)", "1 tsp cocoa", "Zest of 1 lemon", "1/2 tsp baking soda"],
        "steps": ["Warm honey and sugar until dissolved; cool slightly.", "Stir in egg, then flour, spices, cocoa, zest and soda to a soft dough.", "Rest the dough in the fridge for an hour.", "Roll and cut into rounds; bake at 175°C (350°F) for 12–15 minutes.", "Glaze with a thin lemon icing when cool."],
    },
    {
        "slug": "christmas-panettone", "title": "Christmas Panettone",
        "origin": "Italy", "occasion": "Christmas",
        "icon": "gift-outline", "color": "#8A2E2E",
        "feasts": ["nativity", "christmas"], "seasons": ["Christmas"],
        "description": "The tall, fragrant Christmas bread of Milan, studded with candied fruit and raisins — shared through the twelve days of Christmas.",
        "ingredients": ["3 cups flour", "1/2 cup sugar", "1 packet yeast", "1/2 cup warm milk", "3 eggs", "1/2 cup butter", "Raisins & candied orange", "Vanilla & zest"],
        "steps": ["Bloom yeast in warm milk.", "Knead flour, sugar, eggs, butter, vanilla and zest into a soft, elastic dough.", "Fold in raisins and candied fruit; rise until doubled.", "Place in a tall paper mould and rise again.", "Bake at 180°C (350°F) for 40–45 minutes; cool hanging upside-down."],
    },
    {
        "slug": "assumption-blessed-herbs", "title": "Blessed Herb & Honey Cakes",
        "origin": "Central Europe", "occasion": "Assumption (Aug 15)",
        "icon": "flower-outline", "color": "#3E6B8A",
        "feasts": ["assumption"], "seasons": [],
        "description": "On the Assumption, bundles of herbs and first fruits are blessed; these simple honey cakes with garden herbs celebrate Our Lady's harvest feast.",
        "ingredients": ["2 cups flour", "1/2 cup honey", "1 egg", "1/3 cup butter", "1 tsp baking powder", "Chopped fresh herbs (lavender or rosemary)", "Lemon zest"],
        "steps": ["Cream butter and honey; beat in the egg.", "Fold in flour, baking powder, zest and finely chopped herbs.", "Spoon into a small tin or muffin cups.", "Bake at 175°C (350°F) for 20–25 minutes.", "Bring to be blessed, then share in Our Lady's honour."],
    },
    {
        "slug": "ordinary-time-bread", "title": "Daily Communion Bread (Simple Loaf)",
        "origin": "Universal", "occasion": "Ordinary Time",
        "icon": "restaurant-outline", "color": "#4B6B3E",
        "feasts": [], "seasons": ["Ordinary Time"],
        "description": "A plain, wholesome loaf for ordinary days — a reminder to give thanks for daily bread and to keep the family table a small altar of gratitude.",
        "ingredients": ["3 cups flour", "1 packet yeast", "1 cup warm water", "1 tbsp honey", "1 tbsp olive oil", "1 tsp salt"],
        "steps": ["Bloom yeast in warm water with honey.", "Mix in flour, oil and salt; knead until smooth.", "Rise until doubled, then shape into a loaf.", "Rise again in a tin; slash a cross on top.", "Bake at 220°C (425°F) for 25–30 minutes until it sounds hollow."],
    },
    {
        "slug": "sacred-heart-cherry", "title": "Sacred Heart Cherry Tart",
        "origin": "France", "occasion": "Sacred Heart of Jesus",
        "icon": "heart-outline", "color": "#9E1B1B",
        "feasts": ["sacred heart"], "seasons": [],
        "description": "A red cherry tart for the Solemnity of the Sacred Heart, its deep red fruit recalling the Heart of Jesus pierced with love for us.",
        "ingredients": ["1 shortcrust pastry", "3 cups pitted cherries", "1/2 cup sugar", "1 tbsp cornstarch", "1 tsp vanilla", "A little lemon juice"],
        "steps": ["Line a tart tin with the pastry and prick the base.", "Toss cherries with sugar, cornstarch, vanilla and lemon.", "Fill the shell and arrange a lattice or heart on top.", "Bake at 190°C (375°F) for 35–40 minutes until bubbling.", "Cool before serving in honour of the Sacred Heart."],
    },
]

_BY_SLUG = {t["slug"]: t for t in TRADITIONS}


def all_traditions() -> List[Dict[str, Any]]:
    return [dict(t) for t in TRADITIONS]


def get_tradition(slug: str) -> Optional[Dict[str, Any]]:
    t = _BY_SLUG.get(slug)
    return dict(t) if t else None


def traditions_for_day(lit: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return traditions matching the day's feast first, then its season."""
    feast = (lit.get("feast") or "").lower()
    season = (lit.get("season") or "")
    feast_matches = [dict(t) for t in TRADITIONS if feast and any(k in feast for k in t["feasts"])]
    if feast_matches:
        return feast_matches
    season_matches = [dict(t) for t in TRADITIONS if season and season in t["seasons"]]
    return season_matches


async def localize(db, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Translate display fields + ingredient/step lists into the request language."""
    lang = get_lang()
    if lang == "en" or not items:
        return items
    # Gather every string to translate in one batch, tracking where to write it back.
    strings: List[str] = []
    setters: List[Any] = []

    def add(get, setv):
        v = get()
        if v:
            strings.append(v)
            setters.append(setv)

    for it in items:
        add(lambda i=it: i.get("title"), lambda t, i=it: i.__setitem__("title", t))
        add(lambda i=it: i.get("origin"), lambda t, i=it: i.__setitem__("origin", t))
        add(lambda i=it: i.get("occasion"), lambda t, i=it: i.__setitem__("occasion", t))
        add(lambda i=it: i.get("description"), lambda t, i=it: i.__setitem__("description", t))
        for idx in range(len(it.get("ingredients") or [])):
            add(lambda i=it, k=idx: i["ingredients"][k], lambda t, i=it, k=idx: i["ingredients"].__setitem__(k, t))
        for idx in range(len(it.get("steps") or [])):
            add(lambda i=it, k=idx: i["steps"][k], lambda t, i=it, k=idx: i["steps"].__setitem__(k, t))
    if not strings:
        return items
    out: List[str] = []
    for i in range(0, len(strings), 60):
        out += await translate_texts(db, _LLM_KEY, strings[i : i + 60], lang)
    for setv, tr in zip(setters, out):
        if tr:
            setv(tr)
    return items

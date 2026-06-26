"""Vocation companion — a tailored Home-screen guide for one's state of life.

Based on the user's chosen path in their "Walk with Christ" (singleness /
religious life / marriage) and whether they are *discerning* or *living* it,
this module serves hand-curated, accurate Catholic content:

  - a morning prayer to begin the day in that vocation
  - a set of saint companions the user may choose to walk with
  - ideas to draw closer to the vocation (e.g. Eucharistic adoration, reading)
  - traditions to build as one grows into the vocation (state-tailored:
    discerners get discernment practices; those living get family / religious
    traditions to bring into their home or community)

Content is fixed/curated for accuracy; strings are localized on demand via the
shared translation cache (EN / ES / IT), exactly like the rest of the app.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from lang_ctx import get_lang

VOCATIONS = {"singleness", "religious life", "marriage"}
STATES = {"discerning", "living"}

# --------------------------------------------------------------------------- #
# Curated content per vocation.                                               #
# --------------------------------------------------------------------------- #
CONTENT: Dict[str, Dict[str, Any]] = {
    "singleness": {
        "label": "Holy Singleness",
        "intro": "Your single years are not a waiting room but a gift — a time of undivided "
        "love and freedom to give yourself to God and neighbour.",
        "morning_prayer": {
            "title": "Morning Offering for the Single Heart",
            "body": "Lord Jesus, I give you this day — my freedom, my time, my heart. "
            "While I am yours alone, let me love generously and serve gladly. Keep me pure "
            "and joyful, and use these years to make me wholly yours. Through Mary, my "
            "Mother, I offer all that I am. Amen.",
        },
        "companions": [
            {"slug": "catherine-siena", "name": "St. Catherine of Siena",
             "why": "A consecrated virgin in the world who changed the Church through prayer and love.",
             "prayer": "St. Catherine, teach me to love Christ with an undivided heart."},
            {"slug": "pier-giorgio", "name": "Bl. Pier Giorgio Frassati",
             "why": "A joyful young layman who found holiness in friendship, the poor, and the mountains.",
             "prayer": "Bl. Pier Giorgio, help me to live my youth 'verso l'alto' — toward the heights."},
            {"slug": "john-paul-ii", "name": "St. John Paul II",
             "why": "He lived his single years in deep prayer and gave the Church the Theology of the Body.",
             "prayer": "St. John Paul II, help me discover the meaning of self-gift."},
            {"slug": "agnes", "name": "St. Agnes",
             "why": "A young virgin martyr who gave her whole heart to Christ alone.",
             "prayer": "St. Agnes, guard my heart and keep it for the Lord."},
        ],
        "ideas": [
            {"title": "Pray before the Eucharist", "body": "Spend a weekly holy hour before the "
             "Blessed Sacrament. Let Jesus love you in the silence — this is where the heart learns self-gift."},
            {"title": "Take up spiritual reading", "body": "Begin with 'Introduction to the Devout "
             "Life' by St. Francis de Sales — a gentle guide to holiness for those living in the world."},
            {"title": "Make a daily Examen", "body": "Each evening, review your day with God: where "
             "you loved well, where you fell short, and give thanks. Five minutes changes a life."},
            {"title": "Serve with your freedom", "body": "Your time is your treasure now. Volunteer, "
             "visit the lonely, give to the poor — let your singleness overflow in works of mercy."},
        ],
        "traditions": {
            "discerning": [
                {"title": "Keep a discernment journal", "body": "Write what stirs your heart in prayer "
                 "— the desires, fears, and consolations. God often speaks through the deep desires he plants."},
                {"title": "Seek a spiritual director", "body": "Meet regularly with a wise guide who "
                 "can help you read the movements of your heart and listen for God's call."},
                {"title": "Pray a novena to St. Joseph", "body": "Entrust your future to the guardian "
                 "of the Holy Family; ask him to lead you to the path where you will become a saint."},
            ],
            "living": [
                {"title": "Adopt a simple Rule of Life", "body": "Set fixed times for prayer, work, "
                 "rest, and charity — a gentle structure that keeps God at the centre of an independent life."},
                {"title": "Build deep friendships in faith", "body": "Gather friends for a meal, the "
                 "Rosary, or Sunday Mass. Holy friendship is a foretaste of heaven and a guard against loneliness."},
                {"title": "Tithe your time to the parish", "body": "Let your community know you. Lectoring, "
                 "hospitality, or catechesis turns free time into a self-gift that bears lasting fruit."},
            ],
        },
    },
    "religious life": {
        "label": "Religious Life",
        "intro": "To follow Christ closely in poverty, chastity, and obedience is to give him "
        "everything — a life hidden in God for the sake of the world.",
        "morning_prayer": {
            "title": "The Suscipe of St. Ignatius",
            "body": "Take, Lord, and receive all my liberty, my memory, my understanding, and "
            "my entire will — all that I have and call my own. You have given it all to me; to "
            "you, Lord, I return it. Do with it what you will. Give me only your love and your "
            "grace; that is enough for me. Amen.",
        },
        "companions": [
            {"slug": "therese-lisieux", "name": "St. Thérèse of Lisieux",
             "why": "The 'Little Flower' who found holiness in small things done with great love.",
             "prayer": "St. Thérèse, teach me your little way of trust and surrender."},
            {"slug": "benedict", "name": "St. Benedict",
             "why": "Father of Western monasticism, who ordered life around prayer and work — 'ora et labora'.",
             "prayer": "St. Benedict, help me to prefer nothing whatever to Christ."},
            {"slug": "francis-assisi", "name": "St. Francis of Assisi",
             "why": "He embraced Lady Poverty and rebuilt the Church through humble love.",
             "prayer": "St. Francis, make me an instrument of God's peace."},
            {"slug": "teresa-avila", "name": "St. Teresa of Ávila",
             "why": "Reformer and mystic who taught that prayer is friendship with the God who loves us.",
             "prayer": "St. Teresa, let nothing disturb me, for God alone suffices."},
        ],
        "ideas": [
            {"title": "Pray before the Eucharist", "body": "Make daily adoration the heart of your "
             "day. Religious life is born and sustained in long, loving gazes upon the Lord present in the Host."},
            {"title": "Pray the Liturgy of the Hours", "body": "Begin with Lauds (Morning Prayer) and "
             "Compline (Night Prayer) — joining your voice to the Church's unceasing prayer."},
            {"title": "Practise Lectio Divina", "body": "Read the Scriptures slowly and prayerfully: "
             "read, meditate, pray, contemplate. Let the Word dwell in you richly."},
            {"title": "Read a spiritual classic", "body": "Try 'Story of a Soul' by St. Thérèse, or "
             "'The Rule of St. Benedict' — and learn how the saints gave their lives to God."},
        ],
        "traditions": {
            "discerning": [
                {"title": "Make a 'Come and See' visit", "body": "Spend time with a religious community "
                 "— pray their hours, share their meals. You discern a way of life best by tasting it."},
                {"title": "Embrace silence", "body": "Carve out times of quiet each day. God's call is "
                 "often a whisper, heard only when we still the noise around and within us."},
                {"title": "Pray for the grace to know God's will", "body": "Ask daily, with St. Ignatius, "
                 "for the freedom to want only what God wants — and trust he will make the way clear."},
            ],
            "living": [
                {"title": "Keep the rhythm of the Hours", "body": "Let the bells of prayer order your "
                 "whole day, sanctifying every hour and binding the community together in praise."},
                {"title": "Honour the Great Silence", "body": "Guard the quiet of the evening and night "
                 "as a sacred space where the soul rests in God alone."},
                {"title": "Celebrate your community's feasts", "body": "Keep the feast of your founder "
                 "and patrons with joy — these traditions are the family memory that forms each generation."},
            ],
        },
    },
    "marriage": {
        "label": "Holy Marriage",
        "intro": "Marriage is a path to heaven walked two-by-two — a covenant where spouses help "
        "each other, and their children, become saints.",
        "morning_prayer": {
            "title": "Morning Prayer for the Family",
            "body": "Heavenly Father, bless my spouse (or future spouse) and our family this day. "
            "Make our home a domestic church, where love is patient and forgiveness quick. Holy "
            "Family of Nazareth — Jesus, Mary, and Joseph — pray for us, that we may love as you "
            "loved. Amen.",
        },
        "companions": [
            {"slug": "st-joseph", "name": "St. Joseph",
             "why": "Guardian of the Holy Family — model of the faithful, hardworking, protecting spouse.",
             "prayer": "St. Joseph, guardian of families, watch over my home."},
            {"slug": "louis-zelie", "name": "Sts. Louis & Zélie Martin",
             "why": "A married couple, parents of St. Thérèse, canonized together for their holy family life.",
             "prayer": "Sts. Louis and Zélie, teach us to make our home a school of holiness."},
            {"slug": "gianna-molla", "name": "St. Gianna Beretta Molla",
             "why": "A wife, mother, and doctor who loved her family and gave her life for her child.",
             "prayer": "St. Gianna, help me to love my family with sacrificial love."},
            {"slug": "monica", "name": "St. Monica",
             "why": "Her tears and unceasing prayer won the conversion of her son, St. Augustine.",
             "prayer": "St. Monica, teach me to pray with perseverance for those I love."},
        ],
        "ideas": [
            {"title": "Pray before the Eucharist", "body": "Visit the Blessed Sacrament — together when "
             "you can. A marriage rooted in adoration draws its strength from the source of all love."},
            {"title": "Pray together as a couple", "body": "End each day with a short prayer hand in "
             "hand. Couples who pray together build their home upon the rock that does not fall."},
            {"title": "Read together", "body": "Try 'Three to Get Married' by Ven. Fulton Sheen, or "
             "St. John Paul II's Theology of the Body — and discover the beauty of married love."},
            {"title": "Frequent the sacraments together", "body": "Go to Confession and Sunday Mass as "
             "a family. Grace, received together, knits hearts together."},
        ],
        "traditions": {
            "discerning": [
                {"title": "Court with chastity and prayer", "body": "Invite God into your relationship "
                 "from the start — pray together, keep purity, and let your love be ordered to the altar."},
                {"title": "Learn each other's faith", "body": "Share how you pray, attend Mass together, "
                 "and speak openly of your hopes for a future domestic church."},
                {"title": "Pray a novena to St. Joseph for a holy spouse", "body": "Ask the guardian of "
                 "the Holy Family to lead you to — or strengthen you for — a holy marriage."},
            ],
            "living": [
                {"title": "Enthrone the Sacred Heart in your home", "body": "Install an image of the "
                 "Sacred Heart and consecrate your family to him — a beautiful tradition that makes Christ "
                 "the King of your household."},
                {"title": "Pray the family Rosary & grace at meals", "body": "Gather the family for a "
                 "decade of the Rosary and never eat without giving thanks. Small daily rites form holy children."},
                {"title": "Live the liturgical year at home", "body": "Keep an Advent wreath and Jesse "
                 "tree, leave shoes out for St. Nicholas, and celebrate baptismal anniversaries — let the "
                 "Church's seasons fill your home with wonder."},
                {"title": "Bless your children", "body": "Trace a cross on each child's forehead at "
                 "bedtime. A parent's blessing is an ancient and powerful tradition of the domestic church."},
            ],
        },
    },
}


async def _localize(db, payload: Dict[str, Any]) -> Dict[str, Any]:
    lang = get_lang()
    if lang == "en":
        return payload

    texts: List[str] = []
    setters: List[Any] = []

    def collect(get, set_):
        v = get()
        if isinstance(v, str) and v.strip():
            texts.append(v)
            setters.append(set_)

    collect(lambda: payload.get("intro"), lambda t: payload.__setitem__("intro", t))
    collect(lambda: payload.get("label"), lambda t: payload.__setitem__("label", t))
    mp = payload.get("morning_prayer") or {}
    collect(lambda: mp.get("title"), lambda t: mp.__setitem__("title", t))
    collect(lambda: mp.get("body"), lambda t: mp.__setitem__("body", t))
    for c in payload.get("companions") or []:
        collect(lambda c=c: c.get("why"), lambda t, c=c: c.__setitem__("why", t))
        collect(lambda c=c: c.get("prayer"), lambda t, c=c: c.__setitem__("prayer", t))
    for sec in ("ideas", "traditions"):
        for item in payload.get(sec) or []:
            collect(lambda i=item: i.get("title"), lambda t, i=item: i.__setitem__("title", t))
            collect(lambda i=item: i.get("body"), lambda t, i=item: i.__setitem__("body", t))

    if not texts:
        return payload
    try:
        from i18n_translate import translate_texts
        tr = await translate_texts(db, os.environ.get("EMERGENT_LLM_KEY", ""), texts, lang)
        for setter, t in zip(setters, tr):
            if isinstance(t, str) and t.strip():
                setter(t)
    except Exception:  # noqa: BLE001
        pass
    return payload


def _build_guide(vocation: str, state: str) -> Dict[str, Any]:
    base = CONTENT[vocation]
    traditions = base["traditions"].get(state) or base["traditions"]["living"]
    # Deep-ish copy so localization does not mutate the module constants.
    import copy
    return {
        "vocation": vocation,
        "state": state,
        "label": base["label"],
        "intro": base["intro"],
        "morning_prayer": copy.deepcopy(base["morning_prayer"]),
        "companions": copy.deepcopy(base["companions"]),
        "ideas": copy.deepcopy(base["ideas"]),
        "traditions": copy.deepcopy(traditions),
    }


def build_router(db: AsyncIOMotorDatabase, get_current_user, emergent_llm_key: str = "") -> APIRouter:
    router = APIRouter(prefix="/vocation", tags=["vocation"])

    @router.get("/guide")
    async def get_guide(user=Depends(get_current_user)):
        prefs = await db.preferences.find_one({"user_id": user.user_id}, {"_id": 0}) or {}
        vocation = (prefs.get("vocation") or "").strip().lower()
        state = (prefs.get("vocation_state") or "living").strip().lower()
        if vocation not in VOCATIONS:
            return {"has_vocation": False}
        if state not in STATES:
            state = "living"
        guide = _build_guide(vocation, state)
        guide = await _localize(db, guide)
        guide["has_vocation"] = True
        guide["companion_saint"] = prefs.get("companion_saint") or ""
        return guide

    return router

"""
Catechism in 90 seconds.

A curated rotation of paragraphs drawn from the Catechism of the Catholic
Church (CCC). The CCC itself is in the public domain (Libreria Editrice
Vaticana grants free use of the text for catechetical purposes), so the
`quote` field uses brief verbatim excerpts identified by their canonical
paragraph numbers. Each entry layers a short explanation in our own voice
and a personal reflection prompt suitable for journaling.

Selection mirrors the daily-practice module: pool of N teachings, one
deterministic pick per (user_id, date), persisted so refreshing keeps
today's teaching stable. A user's most-recent 60 days are excluded so the
same teaching doesn't recur for two months.

The AI reflect endpoint takes the user's optional context note and the
teaching of the day, then uses Claude Sonnet 4.5 (via the Emergent LLM key)
to return a single, gentle, 80-120 word reflection that the user can save
to their journal. We deliberately constrain the model to Catholic doctrine
and to a pastoral tone with a guardrail system prompt.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import date as _date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from liturgical import get_liturgical_day

logger = logging.getLogger("sanctus.catechism")

# Catholic seasons we'll tag each teaching against. "Ordinary Time" acts as a
# universal fallback: anything tagged with it can surface in any green-vestment
# day, but season-specific teachings (Advent/Lent/etc.) are preferred when
# the day is in that season — so the catechetical flow follows the Church year.
ALL_SEASONS = {
    "Advent",
    "Christmas",
    "Lent",
    "Paschal Triduum",
    "Easter",
    "Ordinary Time",
}


# ---------------------------------------------------------------------------
# Curated CCC teaching pool
# ---------------------------------------------------------------------------
# Each entry is anchored to a real CCC paragraph number. The `quote` is a
# faithful excerpt. The `expansion` is original devotional commentary in
# Sanctus' voice and is NOT a paraphrase of the CCC text — it's our gloss
# meant to land the teaching for a modern reader in ~3 sentences.

Teaching = Dict[str, Any]


TEACHINGS: List[Teaching] = [
    # ---------------------- PRAYER -----------------------------
    {
        "id": "ccc_2559",
        "ccc_ref": "CCC 2559",
        "theme": "Prayer",
        "title": "Prayer is the raising of the heart",
        "quote": "Prayer is the raising of one's mind and heart to God or the requesting of good things from God.",
        "expansion": (
            "Prayer is not a performance. It is a quiet, deliberate turning of "
            "the heart toward the One who already knows you. Begin in honesty — "
            "even three sincere words count more than an hour of distracted "
            "recitation."
        ),
        "reflection_prompt": "What words would you actually use if you stopped reciting and just spoke?",
    },
    {
        "id": "ccc_2725",
        "ccc_ref": "CCC 2725",
        "theme": "Prayer",
        "title": "Prayer is a battle",
        "quote": "Prayer is both a gift of grace and a determined response on our part. It always presupposes effort.",
        "expansion": (
            "Resistance to prayer is not a sign that prayer is failing — it is a "
            "sign that prayer is working. The distractions, the dryness, the "
            "checking of the clock: all are evidence that something deeper than "
            "comfort is being trained in you."
        ),
        "reflection_prompt": "Where do you feel most resistance to prayer this week, and what might that be guarding?",
    },
    {
        "id": "ccc_2710",
        "ccc_ref": "CCC 2710",
        "theme": "Prayer",
        "title": "Silence before God",
        "quote": "One does not always have the time to retire... One can always set aside some time to be alone with God.",
        "expansion": (
            "Silence is not the absence of noise — it is the presence of "
            "attention. Five minutes of silent attention given to God is more "
            "powerful than an hour of background prayer. Schedule it before "
            "your phone schedules it for you."
        ),
        "reflection_prompt": "When today can you guard five minutes of silence — and what will you give up to protect it?",
    },

    # ---------------------- LOVE / CHARITY -----------------------------
    {
        "id": "ccc_1822",
        "ccc_ref": "CCC 1822",
        "theme": "Love",
        "title": "Charity loves God above all",
        "quote": "Charity is the theological virtue by which we love God above all things for his own sake, and our neighbor as ourselves for the love of God.",
        "expansion": (
            "Charity is not warm feeling. It is a chosen direction — God first, "
            "then everyone else through Him. The order matters: when neighbor "
            "comes first, love eventually exhausts itself. When God comes first, "
            "love widens to include even those who don't deserve it."
        ),
        "reflection_prompt": "Who in your life are you trying to love without first loving God?",
    },
    {
        "id": "ccc_1827",
        "ccc_ref": "CCC 1827",
        "theme": "Love",
        "title": "Charity binds everything together",
        "quote": "The practice of all the virtues is animated and inspired by charity, which 'binds everything together in perfect harmony.'",
        "expansion": (
            "Without charity, even courage hardens into harshness, prudence "
            "into calculation, justice into vengeance. Charity is what makes "
            "the virtues recognizable as Christian. Ask not 'was I right?' but "
            "'was I loving?'"
        ),
        "reflection_prompt": "Where this week did you choose to be right at the cost of being loving?",
    },
    {
        "id": "ccc_2447",
        "ccc_ref": "CCC 2447",
        "theme": "Mercy",
        "title": "The works of mercy",
        "quote": "The works of mercy are charitable actions by which we come to the aid of our neighbor in his spiritual and bodily necessities.",
        "expansion": (
            "Mercy is theology with hands. Feed someone, visit someone, "
            "forgive someone, listen to someone. The Church names seven "
            "corporal and seven spiritual works — concrete, unglamorous, "
            "transformative. Pick one and do it today."
        ),
        "reflection_prompt": "Which one act of mercy could you complete before sunset today?",
    },

    # ---------------------- THE MASS / EUCHARIST -----------------------------
    {
        "id": "ccc_1324",
        "ccc_ref": "CCC 1324",
        "theme": "Eucharist",
        "title": "Source and summit",
        "quote": "The Eucharist is 'the source and summit of the Christian life.' The other sacraments... are bound up with the Eucharist and are oriented toward it.",
        "expansion": (
            "Everything in the Christian life either flows from the altar or "
            "flows toward it. If your week feels off, ask whether you have "
            "actually been to the source. The Mass is not one obligation "
            "among many — it is the center of gravity."
        ),
        "reflection_prompt": "When was the last time you walked into Mass expecting to receive something real?",
    },
    {
        "id": "ccc_1374",
        "ccc_ref": "CCC 1374",
        "theme": "Eucharist",
        "title": "Truly, really, substantially present",
        "quote": "In the most blessed sacrament of the Eucharist 'the body and blood, together with the soul and divinity, of our Lord Jesus Christ... is truly, really, and substantially contained.'",
        "expansion": (
            "Not a symbol. Not a memory. Not a metaphor. Christ Himself. If "
            "you believed this with the full weight of the Church's teaching, "
            "you would never receive Him distracted, and you would never miss "
            "a chance to kneel in adoration."
        ),
        "reflection_prompt": "How would the next Mass look different if you arrived knowing the King would actually be there?",
    },

    # ---------------------- CONFESSION / RECONCILIATION -----------------------------
    {
        "id": "ccc_1422",
        "ccc_ref": "CCC 1422",
        "theme": "Confession",
        "title": "Reconciled to God and to the Church",
        "quote": "Those who approach the sacrament of Penance obtain pardon from God's mercy for the offense committed against him, and are, at the same time, reconciled with the Church.",
        "expansion": (
            "Sin is never a strictly private affair. It wounds you, your "
            "neighbor, and the body of the Church. Confession heals all three "
            "in a single absolution. Don't postpone it because you 'feel "
            "fine.' The point isn't feelings — it's reality."
        ),
        "reflection_prompt": "What sin are you minimizing because it 'doesn't seem that bad' anymore?",
    },
    {
        "id": "ccc_1458",
        "ccc_ref": "CCC 1458",
        "theme": "Confession",
        "title": "Confession of venial sins",
        "quote": "Without being strictly necessary, confession of everyday faults (venial sins) is nevertheless strongly recommended by the Church.",
        "expansion": (
            "You don't need a mortal sin to enter the confessional. Regular "
            "confession of small faults is preventive medicine. It builds "
            "self-knowledge, deepens humility, and refines the conscience so "
            "that mortal sin never finds a foothold."
        ),
        "reflection_prompt": "What recurring small fault would benefit from being spoken aloud to a priest this month?",
    },

    # ---------------------- VIRTUE -----------------------------
    {
        "id": "ccc_1804",
        "ccc_ref": "CCC 1804",
        "theme": "Virtue",
        "title": "A habitual and firm disposition to do the good",
        "quote": "Human virtues are firm attitudes, stable dispositions, habitual perfections of intellect and will that govern our actions, order our passions, and guide our conduct according to reason and faith.",
        "expansion": (
            "Virtue is not how you feel — it's what you reliably do. Built one "
            "small choice at a time. Don't wait for inspiration. Today's "
            "small fidelity is tomorrow's stable disposition."
        ),
        "reflection_prompt": "What single small act, repeated daily for 30 days, would most reshape your character?",
    },
    {
        "id": "ccc_1808",
        "ccc_ref": "CCC 1808",
        "theme": "Virtue",
        "title": "Fortitude",
        "quote": "Fortitude is the moral virtue that ensures firmness in difficulties and constancy in the pursuit of the good. It strengthens the resolve to resist temptations and to overcome obstacles in the moral life.",
        "expansion": (
            "Courage is not the absence of fear. It is the decision to do the "
            "right thing while afraid. Fortitude is the muscle the saints "
            "trained — most often in unseen choices, long before any "
            "spotlight ever arrived."
        ),
        "reflection_prompt": "Where is fear making the moral decision for you, and what would courage choose instead?",
    },
    {
        "id": "ccc_1809",
        "ccc_ref": "CCC 1809",
        "theme": "Virtue",
        "title": "Temperance",
        "quote": "Temperance is the moral virtue that moderates the attraction of pleasures and provides balance in the use of created goods.",
        "expansion": (
            "Pleasure is not the enemy. Disordered pleasure is. Temperance "
            "doesn't kill desire — it teaches desire to obey the soul. The "
            "person who can say 'enough' is freer than the person who cannot "
            "say 'no.'"
        ),
        "reflection_prompt": "Which legitimate good in your life has quietly stopped serving you?",
    },

    # ---------------------- SIN -----------------------------
    {
        "id": "ccc_1849",
        "ccc_ref": "CCC 1849",
        "theme": "Sin",
        "title": "Sin is an offense against reason and against God",
        "quote": "Sin is an offense against reason, truth, and right conscience; it is failure in genuine love for God and neighbor caused by a perverse attachment to certain goods.",
        "expansion": (
            "Sin almost always begins as the love of something good held in "
            "the wrong place or the wrong measure. Examining your life means "
            "noticing not just what you've done, but what you've over-loved. "
            "Disordered loves are the architecture of every fall."
        ),
        "reflection_prompt": "Which good thing in your life are you currently loving in a disordered way?",
    },
    {
        "id": "ccc_1855",
        "ccc_ref": "CCC 1855",
        "theme": "Sin",
        "title": "Mortal and venial",
        "quote": "Mortal sin destroys charity in the heart of man by a grave violation of God's law... Venial sin allows charity to subsist, even though it offends and wounds it.",
        "expansion": (
            "Take the distinction seriously. Mortal sin is not a synonym for "
            "'big embarrassment.' It is a chosen rupture. Venial sin is not a "
            "synonym for 'no big deal.' It is a wound that compounds. Both "
            "deserve confession; only one demands it before Communion."
        ),
        "reflection_prompt": "Are there areas where you have stopped distinguishing — and quietly normalized what you should be repenting?",
    },

    # ---------------------- HOPE / LAST THINGS -----------------------------
    {
        "id": "ccc_1817",
        "ccc_ref": "CCC 1817",
        "theme": "Hope",
        "title": "The virtue of hope",
        "quote": "Hope is the theological virtue by which we desire the kingdom of heaven and eternal life as our happiness, placing our trust in Christ's promises.",
        "expansion": (
            "Hope is not optimism. Optimism is a guess about outcomes. Hope "
            "is a confidence in a Person. Christ does not promise an easy "
            "life; He promises a faithful presence. Hope is what lets you "
            "endure when optimism would have already quit."
        ),
        "reflection_prompt": "Where in your life are you running on optimism that will eventually fail, instead of hope?",
    },
    {
        "id": "ccc_1023",
        "ccc_ref": "CCC 1023",
        "theme": "Last Things",
        "title": "The Beatific Vision",
        "quote": "Those who die in God's grace and friendship and are perfectly purified live for ever with Christ... They see him as he is, face to face.",
        "expansion": (
            "Heaven is not endless harp music. It is the unmediated sight of "
            "God Himself. Every joy you have ever known is a thin shadow of "
            "the thing that waits. Live now in a way that makes that "
            "encounter not a shock, but a homecoming."
        ),
        "reflection_prompt": "If today were your last day, what would you most regret not having begun?",
    },
    {
        "id": "ccc_1033",
        "ccc_ref": "CCC 1033",
        "theme": "Last Things",
        "title": "Hell, soberly named",
        "quote": "To die in mortal sin without repenting and accepting God's merciful love means remaining separated from him for ever by our own free choice.",
        "expansion": (
            "Hell is not God's vengeance — it is the perfectly respected "
            "outcome of a freedom that finally refuses Him. The Church names "
            "it not to terrify but to love you enough to tell you the truth. "
            "Mercy is always available; refusing it forever is also a "
            "possibility."
        ),
        "reflection_prompt": "Is there any door in your soul currently closed to God's mercy? What would it take to open it?",
    },

    # ---------------------- TRINITY / CHRIST -----------------------------
    {
        "id": "ccc_234",
        "ccc_ref": "CCC 234",
        "theme": "Trinity",
        "title": "The central mystery",
        "quote": "The mystery of the Most Holy Trinity is the central mystery of Christian faith and life. It is the mystery of God in himself.",
        "expansion": (
            "The Trinity is not a puzzle to solve. It is a Person to love. "
            "Three in one means God is, in His very being, relationship. To "
            "be made in His image is to be made for communion — first with "
            "Him, then with others. Nothing about you is meant to be alone."
        ),
        "reflection_prompt": "Where in your life are you trying to be self-sufficient in a way that contradicts the God who is communion?",
    },
    {
        "id": "ccc_460",
        "ccc_ref": "CCC 460",
        "theme": "Christ",
        "title": "Why the Word became flesh",
        "quote": "The Word became flesh to make us 'partakers of the divine nature.' For this is why the Word became man, and the Son of God became the Son of man: so that man, by entering into communion with the Word and thus receiving divine sonship, might become a son of God.",
        "expansion": (
            "Christ did not come merely to fix you. He came to divinize you. "
            "Salvation is not a status change in a heavenly ledger — it is "
            "actual participation in God's own life. Live as someone being "
            "made new, not merely as someone being forgiven."
        ),
        "reflection_prompt": "Do you live as if Christ is making you into a new kind of being — or just patching the old one?",
    },

    # ---------------------- MARY -----------------------------
    {
        "id": "ccc_494",
        "ccc_ref": "CCC 494",
        "theme": "Mary",
        "title": "Mary's 'yes'",
        "quote": "Mary, by uniting herself to Christ's sacrifice and his consent, opened the way to the salvation of all.",
        "expansion": (
            "Salvation hung on a young woman's free yes. God will not save "
            "you without your consent either. Today's grace is waiting on "
            "your fiat — small, often unglamorous, almost always inconvenient."
        ),
        "reflection_prompt": "What is God currently asking your 'yes' to, that you have been politely deferring?",
    },

    # ---------------------- SUFFERING -----------------------------
    {
        "id": "ccc_1505",
        "ccc_ref": "CCC 1505",
        "theme": "Suffering",
        "title": "Christ takes our infirmities",
        "quote": "By his passion and death on the cross Christ has given a new meaning to suffering: it can henceforth configure us to him and unite us with his redemptive Passion.",
        "expansion": (
            "Suffering remains evil. But after the Cross it is no longer "
            "meaningless. United to Christ's passion, even small daily pains "
            "become participatory — not earning salvation, but applying it. "
            "Offer the pain you cannot avoid."
        ),
        "reflection_prompt": "What pain in your life right now could become an offering instead of just an interruption?",
    },

    # ---------------------- SCRIPTURE -----------------------------
    {
        "id": "ccc_133",
        "ccc_ref": "CCC 133",
        "theme": "Scripture",
        "title": "Reading the Scriptures",
        "quote": "Ignorance of the Scriptures is ignorance of Christ.",
        "expansion": (
            "St. Jerome's blunt warning still lands. You cannot love a "
            "Person you do not know, and you will not know Christ if you "
            "rarely read His Word. Even ten minutes a day, faithfully, will "
            "change a year of your life."
        ),
        "reflection_prompt": "What single book of the Bible could you commit to reading slowly over the next 30 days?",
    },

    # ---------------------- VOCATION / WORK -----------------------------
    {
        "id": "ccc_2427",
        "ccc_ref": "CCC 2427",
        "theme": "Work",
        "title": "Work as participation",
        "quote": "Human work proceeds directly from persons created in the image of God and called to prolong the work of creation by subduing the earth, both with and for one another.",
        "expansion": (
            "Your job is not separate from your discipleship. Whether you "
            "code, clean, build, teach, or care — done in charity, with "
            "competence, for the love of God — it is liturgical. The "
            "spreadsheet can sanctify if it's offered."
        ),
        "reflection_prompt": "How would the next hour of your work change if you began it with the words, 'For You, Lord'?",
    },

    # ---------------------- FAMILY -----------------------------
    {
        "id": "ccc_2204",
        "ccc_ref": "CCC 2204",
        "theme": "Family",
        "title": "The domestic church",
        "quote": "The Christian family constitutes a specific revelation and realization of ecclesial communion, and for this reason it can and should be called a domestic church.",
        "expansion": (
            "Your home is meant to be the first church anyone in it ever "
            "knows. Not perfect — sanctifying. Pray together. Forgive often. "
            "Eat slowly. The little disciplines of family life are the most "
            "consequential evangelization most of us will ever do."
        ),
        "reflection_prompt": "What single rhythm in your household would shape your family most if you protected it for a year?",
    },

    # ---------------------- HUMILITY -----------------------------
    {
        "id": "ccc_2559_humility",
        "ccc_ref": "CCC 2559",
        "theme": "Humility",
        "title": "Humility is the foundation of prayer",
        "quote": "'Man is a beggar before God.' Humility is the foundation of prayer.",
        "expansion": (
            "If prayer feels heavy, check your posture. Standing tall in "
            "self-sufficiency, prayer becomes a memo. Kneeling in poverty of "
            "spirit, prayer becomes communion. Beg, gladly. The saints did."
        ),
        "reflection_prompt": "Where in prayer are you still negotiating instead of asking?",
    },

    # ---------------------- GRACE -----------------------------
    {
        "id": "ccc_2003",
        "ccc_ref": "CCC 2003",
        "theme": "Grace",
        "title": "Sanctifying grace",
        "quote": "Grace is first and foremost the gift of the Spirit who justifies and sanctifies us.",
        "expansion": (
            "You will not white-knuckle your way to holiness. Grace is the "
            "engine; your cooperation is the steering. Stop trying so hard "
            "to be good and start asking, more often, for the only Power "
            "that can actually make you so."
        ),
        "reflection_prompt": "Where have you been working harder than praying? What would change if those were reversed?",
    },

    # ---------------------- FORGIVENESS -----------------------------
    {
        "id": "ccc_2843",
        "ccc_ref": "CCC 2843",
        "theme": "Forgiveness",
        "title": "Forgiving from the heart",
        "quote": "It is there, in fact, 'in the depths of the heart,' that everything is bound and loosed. It is not in our power not to feel or to forget an offense; but the heart that offers itself to the Holy Spirit turns injury into compassion.",
        "expansion": (
            "Forgiveness is not pretending the wound didn't happen. It is "
            "handing the wound to the Holy Spirit and refusing to feed it. "
            "You may not feel it yet — feeling follows decision. Make the "
            "decision; let the feeling catch up."
        ),
        "reflection_prompt": "Whose name comes to mind right now — and what would it cost you to begin loosing them?",
    },
]


# ---------------------------------------------------------------------------
# Liturgical-season affinity per theme
# ---------------------------------------------------------------------------
# Each theme is tagged with the seasons it most naturally fits. "Ordinary Time"
# is universal — anything tagged with it can also appear in green vestment days.
# A teaching whose theme matches the current liturgical season is preferred.
THEME_SEASONS: Dict[str, set] = {
    # Advent leans hope/incarnation/Marian — waiting for the Lord.
    "Hope":        {"Advent", "Easter", "Ordinary Time"},
    "Last Things": {"Advent", "Ordinary Time"},
    "Mary":        {"Advent", "Christmas", "Easter", "Ordinary Time"},
    # Christmas: Christ-incarnate, Trinity, family/domestic church.
    "Christ":      {"Christmas", "Easter", "Ordinary Time"},
    "Trinity":     {"Christmas", "Ordinary Time"},
    "Family":      {"Christmas", "Ordinary Time"},
    # Lent: sin, confession, suffering, virtue, humility.
    "Sin":         {"Lent", "Ordinary Time"},
    "Confession":  {"Lent", "Ordinary Time"},
    "Suffering":   {"Lent", "Paschal Triduum", "Ordinary Time"},
    "Humility":    {"Lent", "Ordinary Time"},
    "Virtue":      {"Lent", "Ordinary Time"},
    "Forgiveness": {"Lent", "Easter", "Ordinary Time"},
    # Easter: Eucharist, grace, Christ.
    "Eucharist":   {"Easter", "Ordinary Time"},
    "Grace":       {"Easter", "Ordinary Time"},
    # Universal
    "Prayer":      {"Advent", "Christmas", "Lent", "Easter", "Ordinary Time"},
    "Love":        {"Christmas", "Easter", "Ordinary Time"},
    "Mercy":       {"Lent", "Easter", "Ordinary Time"},
    "Scripture":   {"Advent", "Christmas", "Lent", "Easter", "Ordinary Time"},
    "Work":        {"Ordinary Time"},
}


def _theme_matches_season(theme: str, season: str) -> bool:
    seasons = THEME_SEASONS.get(theme)
    if not seasons:
        return True  # untagged theme — treat as universal
    return season in seasons


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def _user_offset(user_id: str) -> int:
    """Small deterministic per-user offset so two users on the same date in the
    same season get *similar* — but not identical — teachings."""
    h = hashlib.sha256(f"{user_id}|catechism".encode()).hexdigest()
    return int(h[:6], 16)


def _day_of_year(date_str: str) -> int:
    try:
        d = _date.fromisoformat(date_str)
    except Exception:
        return 0
    return d.timetuple().tm_yday


def _season_for(date_str: str) -> str:
    try:
        d = _date.fromisoformat(date_str)
    except Exception:
        return "Ordinary Time"
    lit = get_liturgical_day(d)
    return str(lit.get("season") or "Ordinary Time")


async def select_or_assign_teaching(
    db: AsyncIOMotorDatabase,
    user_id: str,
    date_str: str,
    recent_window_days: int = 60,
) -> Teaching:
    # 1. Already-assigned for today?
    existing = await db.catechism_assignments.find_one(
        {"user_id": user_id, "date": date_str}, {"_id": 0}
    )
    if existing:
        pid = existing.get("teaching_id")
        teaching = next((t for t in TEACHINGS if t["id"] == pid), None)
        if teaching:
            return {**teaching, "_assignment": _strip(existing)}

    # 2. Exclude recent
    cursor = db.catechism_assignments.find(
        {"user_id": user_id}, {"teaching_id": 1, "date": 1, "_id": 0}
    ).sort("date", -1).limit(recent_window_days)
    recent_rows = await cursor.to_list(length=recent_window_days)
    recent_ids = {r["teaching_id"] for r in recent_rows}

    season = _season_for(date_str)

    # 3. Build candidate list, preferring season-matched teachings.
    season_pool = [
        t for t in TEACHINGS
        if t["id"] not in recent_ids and _theme_matches_season(t["theme"], season)
    ]
    if season_pool:
        candidates = season_pool
    else:
        # Fall back to anything not recent.
        any_pool = [t for t in TEACHINGS if t["id"] not in recent_ids]
        if any_pool:
            candidates = any_pool
        else:
            # Full pool exhausted recently — drop only the half-most-recent.
            half = max(1, len(TEACHINGS) // 2)
            very_recent = {r["teaching_id"] for r in recent_rows[:half]}
            candidates = [t for t in TEACHINGS if t["id"] not in very_recent] or list(TEACHINGS)

    # 4. Pick deterministically by day-of-year + per-user offset so that
    #    each day of the year shows a different teaching for a given user.
    idx = (_day_of_year(date_str) + _user_offset(user_id)) % len(candidates)
    pick = candidates[idx]

    assignment = {
        "user_id": user_id,
        "date": date_str,
        "teaching_id": pick["id"],
        "assigned_at": datetime.now(timezone.utc),
        "saved_to_journal": False,
        "reflection": None,
    }
    try:
        await db.catechism_assignments.insert_one(assignment)
    except Exception as e:
        logger.info("catechism insert race: %s", e)
        # Re-read after race
        existing = await db.catechism_assignments.find_one(
            {"user_id": user_id, "date": date_str}, {"_id": 0}
        )
        if existing:
            pid = existing.get("teaching_id")
            teaching = next((t for t in TEACHINGS if t["id"] == pid), pick)
            return {**teaching, "_assignment": _strip(existing)}

    return {**pick, "_assignment": _strip(assignment)}


def _strip(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in doc.items() if k != "_id"}
    v = out.get("assigned_at")
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        out["assigned_at"] = v.isoformat()
    return out


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class ReflectRequest(BaseModel):
    teaching_id: str
    note: Optional[str] = Field(None, max_length=600)


class SaveToJournalRequest(BaseModel):
    date: str
    teaching_id: str
    reflection: Optional[str] = None
    user_note: Optional[str] = None


def _shape(teaching: Teaching) -> Dict[str, Any]:
    a = teaching.get("_assignment") or {}
    return {
        "id": teaching["id"],
        "ccc_ref": teaching["ccc_ref"],
        "theme": teaching["theme"],
        "title": teaching["title"],
        "quote": teaching["quote"],
        "expansion": teaching["expansion"],
        "reflection_prompt": teaching["reflection_prompt"],
        "date": a.get("date"),
        "saved_to_journal": bool(a.get("saved_to_journal")),
        "reflection": a.get("reflection"),
    }


def build_router(
    db: AsyncIOMotorDatabase,
    get_user,
    emergent_llm_key: str,
) -> APIRouter:
    from emergentintegrations.llm.chat import LlmChat, UserMessage  # local import; same pattern as server.py

    router = APIRouter(prefix="/catechism", tags=["catechism"])

    @router.get("/today")
    async def today(date: str, user=Depends(get_user)):
        t = await select_or_assign_teaching(db, user.user_id, date)
        return _shape(t)

    @router.get("/teaching/{teaching_id}")
    async def get_one(teaching_id: str, user=Depends(get_user)):
        teaching = next((t for t in TEACHINGS if t["id"] == teaching_id), None)
        if not teaching:
            raise HTTPException(status_code=404, detail="teaching not found")
        # If user has it assigned, include the assignment
        existing = await db.catechism_assignments.find_one(
            {"user_id": user.user_id, "teaching_id": teaching_id},
            sort=[("date", -1)],
        )
        if existing:
            return _shape({**teaching, "_assignment": _strip(existing)})
        return _shape(teaching)

    @router.post("/reflect")
    async def reflect(payload: ReflectRequest, user=Depends(get_user)):
        teaching = next((t for t in TEACHINGS if t["id"] == payload.teaching_id), None)
        if not teaching:
            raise HTTPException(status_code=404, detail="teaching not found")
        if not emergent_llm_key:
            raise HTTPException(status_code=503, detail="AI reflection unavailable")

        system = (
            "You are a gentle Catholic spiritual director. Respond in 80-120 words. "
            "Tone: pastoral, warm, never preachy. Stay strictly within Catholic doctrine. "
            "Do not invent CCC paragraphs. Do not quote the Bible unless directly relevant. "
            "Focus on the user's actual situation if they share one. End with one single "
            "concrete invitation for today — not a list. No bullet points, no headings. "
            "Plain prose only."
        )
        user_block = (
            f"Today's teaching is from {teaching['ccc_ref']} on the theme of "
            f"{teaching['theme'].lower()}:\n\n\"{teaching['quote']}\"\n\n"
            f"Title: {teaching['title']}\n"
            f"Reflection prompt: {teaching['reflection_prompt']}\n\n"
        )
        if payload.note:
            user_block += f"The user shares this context:\n{payload.note.strip()}\n\n"
        user_block += "Write a single short reflection (no greeting, no sign-off)."

        try:
            session_id = f"catechism-{user.user_id}-{payload.teaching_id}"
            chat = LlmChat(
                api_key=emergent_llm_key,
                session_id=session_id,
                system_message=system,
            ).with_model("anthropic", "claude-sonnet-4-5-20250929")
            response = await chat.send_message(UserMessage(text=user_block))
        except Exception as e:
            logger.exception("catechism reflect failed: %s", e)
            raise HTTPException(status_code=502, detail="Reflection failed; please retry.")

        reflection_text = (response or "").strip()
        if not reflection_text:
            raise HTTPException(status_code=502, detail="Empty reflection")

        return {"reflection": reflection_text, "teaching_id": teaching["id"]}

    class SaveToJournalRequest(BaseModel):
        date: str
        teaching_id: str
        reflection: Optional[str] = None
        user_note: Optional[str] = None

    @router.post("/save-to-journal")
    async def save_to_journal(payload: SaveToJournalRequest, user=Depends(get_user)):
        teaching = next((t for t in TEACHINGS if t["id"] == payload.teaching_id), None)
        if not teaching:
            raise HTTPException(status_code=404, detail="teaching not found")

        # Build journal entry body
        parts = [
            f"\u201c{teaching['quote']}\u201d",
            f"— {teaching['ccc_ref']}",
            "",
        ]
        if payload.reflection:
            parts.append(payload.reflection.strip())
            parts.append("")
        if payload.user_note:
            parts.append("My note: " + payload.user_note.strip())

        body = "\n".join(parts).strip()
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        # Compute liturgical day for the entry — same shape the main /journal
        # endpoint stores — so the Journal screen renders this entry uniformly.
        try:
            lit = get_liturgical_day(_date.fromisoformat(payload.date))
        except Exception:
            lit = None
        entry_id = f"jrn_{uuid.uuid4().hex[:12]}"
        journal_doc = {
            "entry_id": entry_id,
            "user_id": user.user_id,
            "date": payload.date,
            "title": f"CCC Reflection — {teaching['title']}",
            "body": body,
            "mood": None,
            "kind": "catechism",
            "structured": {
                "teaching_id": teaching["id"],
                "ccc_ref": teaching["ccc_ref"],
                "theme": teaching["theme"],
                "title": teaching["title"],
                "quote": teaching["quote"],
                "reflection": payload.reflection or None,
                "user_note": payload.user_note or None,
            },
            "liturgical": lit,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        # Write to the main `journal` collection used by /api/journal endpoints
        # so the Home tab + Journal list both pick this up out of the box.
        await db.journal.insert_one(journal_doc)

        # Mark assignment as saved
        await db.catechism_assignments.update_one(
            {"user_id": user.user_id, "date": payload.date},
            {"$set": {
                "saved_to_journal": True,
                "reflection": payload.reflection or None,
                "journal_entry_id": entry_id,
            }},
            upsert=True,
        )
        return {"ok": True, "entry_id": entry_id}

    @router.get("/history")
    async def history(limit: int = 30, user=Depends(get_user)):
        if limit < 1 or limit > 365:
            raise HTTPException(status_code=400, detail="limit must be 1..365")
        cursor = db.catechism_assignments.find(
            {"user_id": user.user_id}, {"_id": 0}
        ).sort("date", -1).limit(limit)
        rows = await cursor.to_list(length=limit)
        items = []
        for r in rows:
            t = next((t for t in TEACHINGS if t["id"] == r.get("teaching_id")), None)
            if not t:
                continue
            items.append(_shape({**t, "_assignment": _strip(r)}))
        return {"items": items, "total_pool": len(TEACHINGS)}

    return router

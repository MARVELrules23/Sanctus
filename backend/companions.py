"""Companion Saints — a dedicated devotional space for the saint a user walks with.

Each companion has:
  - why they matter for one's walk / vocation
  - virtues to imitate (practised in the Virtus section)
  - a linked novena (in the Prayer section)
  - a rotating "daily act" pool (a different small act each day to grow closer)
  - a lazily-generated, permanently-cached lo-fi illustration (Gemini Nano Banana)

The St. Joseph companion additionally surfaces the 33-day Consecration.
Displayed text is auto-translated client-side (AutoText) into EN/ES/IT.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger("sanctus.companions")

IMAGE_MODEL = "gemini-3.1-flash-image-preview"

_IMG_STYLE = (
    "lo-fi dreamy illustration, soft muted pastel colours, gentle film grain, "
    "soft glowing golden halo, warm calm contemplative atmosphere, lofi anime aesthetic, "
    "standing serenely, full figure, simple background of soft light, clouds and faint stained-glass glow, "
    "reverent and peaceful, no text, no words"
)

# --------------------------------------------------------------------------- #
# Companion catalogue                                                          #
# --------------------------------------------------------------------------- #
COMPANIONS: Dict[str, Dict[str, Any]] = {
    "catherine-siena": {
        "name": "St. Catherine of Siena",
        "feast": "April 29",
        "novena_slug": "st-catherine-siena",
        "image_prompt": "Saint Catherine of Siena, young Dominican woman in white habit and black cappa, holding a lily and a book, " + _IMG_STYLE,
        "importance": "Catherine shows that a hidden life of prayer can set the whole Church on fire. A consecrated virgin who never left her 'interior cell,' she counselled popes and loved Christ crucified with an undivided heart — proof that whatever your state, holiness begins within.",
        "virtues": [
            {"name": "Interior recollection", "how": "Carry the 'inner cell' of self-knowledge and God's love through a busy day."},
            {"name": "Courageous truth", "how": "Speak the truth in love, even to those in authority, as she did."},
            {"name": "Love of the Church", "how": "Pray daily for the Pope and the unity of the Church."},
            {"name": "Spiritual zeal", "how": "Let love of Christ crucified move you to serve others tirelessly."},
        ],
        "daily_acts": [
            "Withdraw for five silent minutes into your 'interior cell' and rest in God's love.",
            "Offer one prayer today for the Holy Father and the unity of the Church.",
            "Speak a hard truth gently to someone who needs to hear it.",
            "Read one short paragraph of St. Catherine's 'Dialogue' or 'Letters'.",
            "Make a small sacrifice in reparation for sins against the Church.",
            "Visit the Blessed Sacrament and tell Jesus you love Him crucified.",
            "Write an encouraging note to a priest or religious.",
            "Fast from one comfort today and offer it for a wandering soul.",
            "Practise self-knowledge: name one fault and one gift before God tonight.",
            "Serve someone sick or suffering, as Catherine served the plague-stricken.",
            "Pray, 'O eternal God, accept the sacrifice of my life for the Church.'",
            "Choose love over winning in one disagreement today.",
            "Spend your commute in silent conversation with Christ.",
            "Give away something you were saving for yourself.",
            "Ask the Holy Spirit for boldness to do one good thing you've been avoiding.",
            "End the day repeating, 'You are He who is; I am she who is not.'",
        ],
    },
    "pier-giorgio": {
        "name": "Bl. Pier Giorgio Frassati",
        "feast": "July 4",
        "novena_slug": "bl-pier-giorgio",
        "image_prompt": "Blessed Pier Giorgio Frassati, joyful young man in 1920s climbing clothes with a pipe and rope on a mountain, " + _IMG_STYLE,
        "importance": "Pier Giorgio is the saint of joyful, ordinary holiness — a young layman who climbed mountains, loved his friends, and secretly served the poor. He proves that sanctity is not gloomy: it is 'verso l'alto,' a life lived to the heights for love of Christ.",
        "virtues": [
            {"name": "Joy", "how": "Choose cheerfulness and bring lightness to those around you."},
            {"name": "Hidden charity", "how": "Do a good deed for the poor that no one will ever know about."},
            {"name": "Eucharistic devotion", "how": "Make Holy Communion and visits to Jesus the fuel of your day."},
            {"name": "Friendship", "how": "Lead your friends gently upward toward holiness."},
        ],
        "daily_acts": [
            "Greet everyone you meet today with genuine, contagious joy.",
            "Give money or food to a poor person — and tell no one.",
            "Make a short visit to the Blessed Sacrament before your day's main task.",
            "Invite a friend to do something good or holy with you.",
            "Spend time outdoors and thank God 'verso l'alto' — toward the heights.",
            "Offer a small hardship cheerfully instead of complaining.",
            "Pray for the poor by name as you pass them.",
            "Do a chore for your family without being asked.",
            "Receive Holy Communion, or make a spiritual communion, with great love.",
            "Encourage a friend who is discouraged today.",
            "Give away your 'bus fare' — sacrifice a small convenience for charity.",
            "Smile through a tiring moment for love of Christ.",
            "Pray a decade of the Rosary while walking.",
            "Reach 'higher' in one virtue today — pick one and push upward.",
            "Thank a friend for the good they bring to your life.",
            "Climb one small spiritual mountain: do the thing you fear most for God.",
        ],
    },
    "john-paul-ii": {
        "name": "St. John Paul II",
        "feast": "October 22",
        "novena_slug": "st-john-paul-ii",
        "image_prompt": "Saint John Paul II as Pope in white cassock holding a crosier, kind smiling face, " + _IMG_STYLE,
        "importance": "John Paul II lived his single and priestly years in deep prayer and gave the world the Theology of the Body. 'Be not afraid!' was his cry — a witness that the human heart is made for total self-gift, and that Christ alone reveals man to himself.",
        "virtues": [
            {"name": "Fearless trust", "how": "Face one fear today with the words, 'Be not afraid.'"},
            {"name": "Marian devotion", "how": "Entrust everything to Our Lady — 'Totus Tuus.'"},
            {"name": "Self-gift", "how": "Give yourself generously in one concrete act of service."},
            {"name": "Prayerfulness", "how": "Begin and end the day on your knees, as he did."},
        ],
        "daily_acts": [
            "Say 'Totus Tuus' and entrust your whole day to Mary.",
            "Face one fear today with the words, 'Be not afraid.'",
            "Pray the Luminous Mysteries of the Rosary.",
            "Read one paragraph on the Theology of the Body or the dignity of the person.",
            "Treat one person today as a gift, never as a means to an end.",
            "Spend ten minutes in silent adoration before the Lord.",
            "Reconcile with someone, or pray for an enemy.",
            "Offer your work today as a gift of self to God.",
            "Defend the dignity of the unborn, the poor, or the elderly in some small way.",
            "Renew your Marian consecration with a short prayer.",
            "Make a sacrifice for the young people of the world.",
            "Write down what 'self-gift' looks like for you today, and do it.",
            "Pray for vocations to the priesthood and religious life.",
            "Begin and end the day on your knees.",
            "Forgive a past hurt and let it go before God.",
            "Tell God, 'I am totally yours,' and mean it in one decision today.",
        ],
    },
    "agnes": {
        "name": "St. Agnes",
        "feast": "January 21",
        "novena_slug": "st-agnes",
        "image_prompt": "Saint Agnes, young girl in white robe with a lamb in her arms and a palm branch, " + _IMG_STYLE,
        "importance": "Agnes was a girl of about twelve who chose Christ as her only Spouse and died rather than betray that love. She is the patron of purity and youth — a fierce, tender reminder that a heart given wholly to Christ fears nothing.",
        "virtues": [
            {"name": "Purity of heart", "how": "Guard your eyes, words, and thoughts for love of Christ."},
            {"name": "Courage", "how": "Stand for what is right even when it costs you."},
            {"name": "Single-hearted love", "how": "Renew your desire to belong to Christ alone."},
            {"name": "Innocence", "how": "Choose simplicity and trust over cynicism today."},
        ],
        "daily_acts": [
            "Each morning, place your heart in Agnes' care and ask for purity.",
            "Guard your eyes today from one thing that pulls you from God.",
            "Stand up for someone being mistreated.",
            "Renew your desire to belong to Christ alone in a short prayer.",
            "Fast from a screen or media for an hour and give the time to Jesus.",
            "Speak only kind and pure words today.",
            "Offer your chastity, in your state of life, as a gift to God.",
            "Pray for young people tempted against purity.",
            "Choose courage over comfort in one moment today.",
            "Honour someone weaker or younger than you.",
            "Make a small act of penance for the gift of innocence.",
            "Pray, 'Jesus, You alone are the Spouse of my soul.'",
            "Resist a temptation immediately, the moment it comes.",
            "Trust God with childlike simplicity in one worry today.",
            "Light a candle (real or in your heart) for the persecuted.",
            "Thank God tonight for the gift of a heart that can love.",
        ],
    },
    "therese-lisieux": {
        "name": "St. Thérèse of Lisieux",
        "feast": "October 1",
        "novena_slug": "st-therese-little-flower",
        "image_prompt": "Saint Therese of Lisieux, young Carmelite nun in brown habit holding roses and a crucifix, " + _IMG_STYLE,
        "importance": "Thérèse discovered the 'Little Way' — that we reach Heaven not by great deeds but by small things done with great love and total trust, like a child in the arms of God. Her way makes holiness possible for everyone, every day.",
        "virtues": [
            {"name": "Trust (confidence)", "how": "Hand God one worry today as a little child would."},
            {"name": "Little love", "how": "Do an ordinary task with extraordinary love."},
            {"name": "Hidden sacrifice", "how": "Offer small, unseen sacrifices through the day."},
            {"name": "Gratitude", "how": "Thank God for one small 'rose' He sends you."},
        ],
        "daily_acts": [
            "Do one ordinary task today with extraordinary love.",
            "Offer a small, hidden sacrifice and tell no one.",
            "Smile at someone you find difficult to love.",
            "Hand God one worry as a little child hands a burden to a parent.",
            "Pick a 'flower' for Jesus: a tiny act of love every hour.",
            "Accept a small annoyance without complaint, as a gift.",
            "Thank God for one 'shower of roses' He sent you today.",
            "Pray for a missionary or a priest.",
            "Let someone else have their way in a small thing.",
            "Do a kindness for the person no one notices.",
            "Whisper, 'My God, I trust You,' whenever fear rises.",
            "Offer your weariness as a love-gift to Jesus.",
            "Make your next chore an act of love, not duty.",
            "Refuse to dwell on a fault you committed — trust His mercy instead.",
            "Give your full, patient attention to someone today.",
            "End the day placing all you did, well or poorly, into God's hands.",
        ],
    },
    "benedict": {
        "name": "St. Benedict",
        "feast": "July 11",
        "novena_slug": "st-benedict",
        "image_prompt": "Saint Benedict of Nursia, abbot in black Benedictine habit holding a book and a crozier with a raven nearby, " + _IMG_STYLE,
        "importance": "Benedict gave the West a Rule of life — 'pray and work,' ora et labora — and taught that ordinary days, well-ordered, become a ladder to God. He is the father of a stable, balanced, prayerful life rooted in humility.",
        "virtues": [
            {"name": "Stability", "how": "Stay faithful to your duties and people instead of fleeing."},
            {"name": "Order (ora et labora)", "how": "Balance prayer and work with set times for each."},
            {"name": "Humility", "how": "Take the lower place; obey gladly in small things."},
            {"name": "Listening", "how": "'Listen with the ear of your heart' to God and others."},
        ],
        "daily_acts": [
            "Set a fixed time for prayer today and keep it like a monk keeps the hours.",
            "Begin your work with a short prayer and offer it to God.",
            "Take the lower place in one situation today.",
            "Listen fully to one person 'with the ear of your heart.'",
            "Keep your living space in order as a sign of an ordered soul.",
            "Stay faithful to a duty you were tempted to abandon.",
            "Read a few lines of the Rule of St. Benedict or a Psalm.",
            "Eat and rest with moderation today.",
            "Make the sign of the cross before each meal with attention.",
            "Obey a reasonable request promptly and gladly.",
            "Pray a Psalm slowly at midday.",
            "Welcome someone as if welcoming Christ Himself.",
            "Do a humble, hidden chore for your community or family.",
            "Pause at three set moments to lift your heart to God.",
            "Resist murmuring or complaining about your work.",
            "End the day examining whether prayer and work were in balance.",
        ],
    },
    "francis-assisi": {
        "name": "St. Francis of Assisi",
        "feast": "October 4",
        "novena_slug": "st-francis-assisi",
        "image_prompt": "Saint Francis of Assisi, gentle friar in grey-brown habit with a rope cincture surrounded by birds, stigmata on hands, " + _IMG_STYLE,
        "importance": "Francis fell in love with 'Lady Poverty' and with Christ crucified, and the whole of creation became his family. He shows that joy, simplicity, and peace flow from letting go — from owning nothing and loving everything for God.",
        "virtues": [
            {"name": "Poverty / detachment", "how": "Let go of one possession or comfort today."},
            {"name": "Peace", "how": "Be an instrument of peace in one tense moment."},
            {"name": "Joyful simplicity", "how": "Delight in something small and free today."},
            {"name": "Love of creation", "how": "Praise God through the beauty of the world."},
        ],
        "daily_acts": [
            "Give away one thing you own to someone who needs it.",
            "Pray the prayer, 'Lord, make me an instrument of Your peace.'",
            "Make peace in one strained relationship today.",
            "Spend time in nature and praise God for 'Brother Sun, Sister Moon.'",
            "Eat more simply today and offer the difference to the poor.",
            "Speak gently to someone who is harsh with you.",
            "Care for an animal or tend a plant for love of the Creator.",
            "Do without one comfort and embrace 'Lady Poverty' for a day.",
            "Greet a stranger or outcast with warmth.",
            "Kiss the crucifix and thank Christ for His wounds.",
            "Pick up litter or repair something broken — 'rebuild my Church.'",
            "Sing or hum praise to God as you work.",
            "Forgive a debt or let go of something owed to you.",
            "Sit with someone lonely as Francis sat with lepers.",
            "Give thanks before sleep for the gift of simply being alive.",
            "Choose to own less and love more in one decision today.",
        ],
    },
    "teresa-avila": {
        "name": "St. Teresa of Ávila",
        "feast": "October 15",
        "novena_slug": "st-teresa-avila",
        "image_prompt": "Saint Teresa of Avila, Carmelite nun in brown and white habit, pen and book, a dove near her, mystical light, " + _IMG_STYLE,
        "importance": "Teresa is the great teacher of prayer — the 'Interior Castle' of the soul where God dwells. Practical, witty, and utterly given to God, she reformed Carmel and shows that friendship with Christ in prayer transforms everything.",
        "virtues": [
            {"name": "Mental prayer", "how": "Spend time simply being with the God who loves you."},
            {"name": "Determination", "how": "Make a 'determined determination' to never give up prayer."},
            {"name": "Humility", "how": "Walk in truth about yourself before God."},
            {"name": "Holy joy", "how": "Serve God cheerfully — 'let nothing disturb you.'"},
        ],
        "daily_acts": [
            "Spend fifteen minutes in mental prayer, simply being with Christ.",
            "Repeat through the day, 'Let nothing disturb you; God alone suffices.'",
            "Make a 'determined determination' to keep one prayer commitment.",
            "Enter the first room of your 'interior castle' — examine your conscience.",
            "Serve God cheerfully in a tedious task today.",
            "Read a page of 'The Way of Perfection' or 'Interior Castle.'",
            "Speak to Jesus today as your closest Friend.",
            "Walk in humble truth: admit one thing you got wrong.",
            "Offer a frustration to God with a smile.",
            "Pray slowly the Our Father, dwelling on each phrase.",
            "Befriend someone overlooked, for love of Christ.",
            "Resist hurry; do one thing today with full attention to God.",
            "Thank God for a difficulty as a path deeper into the castle.",
            "Encourage someone to begin or return to prayer.",
            "Keep a cheerful face through a trial today.",
            "End the day resting in the truth that God dwells within you.",
        ],
    },
    "st-joseph": {
        "name": "St. Joseph",
        "feast": "March 19",
        "novena_slug": "st-joseph",
        "image_prompt": "Saint Joseph, strong gentle man in brown and ochre robes holding a blossoming lily and carpenter's tools, the Christ Child beside him, " + _IMG_STYLE,
        "importance": "Joseph, the silent guardian of Jesus and Mary, teaches holiness through faithful, hidden work and total trust. Patron of the universal Church, of fathers, workers, and a happy death — he leads souls quietly and surely to Jesus.",
        "virtues": [
            {"name": "Silent obedience", "how": "Do God's will promptly and without complaint."},
            {"name": "Diligent work", "how": "Offer your daily work as a prayer, as Joseph did."},
            {"name": "Protective love", "how": "Guard and provide for those entrusted to you."},
            {"name": "Trust in Providence", "how": "Surrender your worries about the future to God."},
        ],
        "daily_acts": [
            "Offer your work today, hour by hour, to God through St. Joseph.",
            "Do God's will in one thing promptly and without complaint.",
            "Pray the prayer, 'To you, O blessed Joseph...'",
            "Guard and provide for someone entrusted to your care.",
            "Work in silence at one task, lifting your heart to God.",
            "Entrust a worry about the future entirely to St. Joseph.",
            "Pray for the dying and for the grace of a happy death.",
            "Do a hidden act of service for your household.",
            "Honour fathers — pray for your own father, living or dead.",
            "Pray for the universal Church, of which Joseph is patron.",
            "Keep custody of your tongue; speak only what is needful and kind.",
            "Place a difficult decision in Joseph's hands and trust.",
            "Offer your fatigue from work as a prayer.",
            "Defend the Holy Family of your home from one disorder today.",
            "Ask St. Joseph to lead you closer to Jesus.",
            "End the day entrusting your sleep and your death to St. Joseph.",
        ],
    },
    "louis-zelie": {
        "name": "Sts. Louis & Zélie Martin",
        "feast": "July 12",
        "novena_slug": "sts-louis-zelie",
        "image_prompt": "Saints Louis and Zelie Martin, a devout 19th-century married couple in modest dress standing together with quiet affection, " + _IMG_STYLE,
        "importance": "Louis and Zélie are the first spouses canonized together — parents of St. Thérèse. They sanctified marriage, work, and family life amid grief and hardship, showing that an ordinary home, full of faith and love, is a true road to sainthood.",
        "virtues": [
            {"name": "Faithful love", "how": "Choose your spouse or loved ones over yourself today."},
            {"name": "Sanctified work", "how": "Offer your daily labour for your family's good."},
            {"name": "Acceptance of God's will", "how": "Receive joys and sorrows from God's hand."},
            {"name": "Family prayer", "how": "Pray together with those you love."},
        ],
        "daily_acts": [
            "Do one selfless act of love for your spouse or family.",
            "Pray together with someone you love today.",
            "Offer your work for the good of your household.",
            "Accept a sorrow or setback from God's hand with peace.",
            "Speak words of affirmation to a family member.",
            "Attend Mass, or make a spiritual communion, for your family.",
            "Care for the poor as the Martins did from their home.",
            "Forgive a small fault in your spouse or loved one.",
            "Teach a child, or someone younger, one thing about God.",
            "Make your home a place of peace today by your patience.",
            "Pray for married couples who are struggling.",
            "Give thanks for your family, even amid its difficulties.",
            "Do a hidden chore that serves everyone at home.",
            "Trust God with a worry about a child or loved one.",
            "Keep Sunday holy — rest and worship with those you love.",
            "End the day blessing each member of your family by name.",
        ],
    },
    "gianna-molla": {
        "name": "St. Gianna Beretta Molla",
        "feast": "April 28",
        "novena_slug": "st-gianna",
        "image_prompt": "Saint Gianna Beretta Molla, mid-20th-century woman doctor in a simple dress with a warm smile, holding a child, " + _IMG_STYLE,
        "importance": "Gianna was a wife, mother, and physician who gave her life for her unborn child. A modern saint of professional and family life, she shows that everyday love — of patients, husband, and children — lived heroically, is the stuff of holiness.",
        "virtues": [
            {"name": "Sacrificial love", "how": "Put another's good before your own comfort."},
            {"name": "Reverence for life", "how": "Protect and cherish life, born and unborn."},
            {"name": "Joyful duty", "how": "Do your daily work and vocation with a glad heart."},
            {"name": "Wholehearted faith", "how": "Begin the day with God and offer Him your plans."},
        ],
        "daily_acts": [
            "Put someone else's good before your own comfort today.",
            "Pray for mothers and for the protection of unborn children.",
            "Do your work today as a service of love, as Gianna served patients.",
            "Offer a sacrifice for a pregnant woman in difficulty.",
            "Begin the day by giving God your plans and your hands.",
            "Care attentively for someone who is sick.",
            "Smile and bring joy into your duties, not just diligence.",
            "Support a family or charity that protects life.",
            "Cherish your own life as a gift — care for your body and soul.",
            "Encourage a young mother or father today.",
            "Make a generous decision that costs you something.",
            "Pray for doctors, nurses, and the suffering.",
            "Offer a tiredness or pain for someone who needs grace.",
            "Defend the dignity of a vulnerable person in some small way.",
            "Do your vocation today 'with a glad heart,' as she did.",
            "End the day entrusting your loved ones to God's providence.",
        ],
    },
    "monica": {
        "name": "St. Monica",
        "feast": "August 27",
        "novena_slug": "st-monica",
        "image_prompt": "Saint Monica, mature woman in modest dark veil and robe with tears and a gentle hopeful face, hands clasped in prayer, " + _IMG_STYLE,
        "importance": "Monica wept and prayed for years for the conversion of her wayward son Augustine — and never gave up. She is the patron of mothers and of patience in prayer: a witness that persevering, tearful intercession is never wasted.",
        "virtues": [
            {"name": "Perseverance in prayer", "how": "Keep praying for the one intention you most desire."},
            {"name": "Patience", "how": "Wait on God's timing without losing hope."},
            {"name": "Trustful tears", "how": "Bring your sorrows honestly to God."},
            {"name": "Gentle witness", "how": "Lead others to God by love, not nagging."},
        ],
        "daily_acts": [
            "Pray persistently today for one person's conversion or return.",
            "Wait on God's timing in one situation without losing hope.",
            "Bring a sorrow honestly to God in prayer.",
            "Lead someone toward God by love and example, not nagging.",
            "Offer a small fast for a loved one far from the faith.",
            "Pray for mothers carrying heavy burdens for their children.",
            "Forgive someone who has wounded or worried you.",
            "Keep hope alive: thank God in advance for a prayer not yet answered.",
            "Speak a gentle, encouraging word to a struggling family member.",
            "Renew a prayer intention you were tempted to give up on.",
            "Attend Mass, or make a spiritual communion, for a lost soul.",
            "Shed your worry into God's hands and trust like Monica.",
            "Pray for the grace of patience in one daily trial.",
            "Write down the conversion you long for and place it on your prayer space.",
            "Be present to someone without trying to fix them today.",
            "End the day repeating, 'Lord, I trust You with the ones I love.'",
        ],
    },
}


def _today_act(acts: List[str]) -> Dict[str, Any]:
    idx = (date.today().toordinal()) % max(1, len(acts))
    return {"text": acts[idx], "index": idx, "total": len(acts)}


_IMG_LOCKS: Dict[str, "asyncio.Lock"] = {}


async def _get_or_make_image(db, slug: str, prompt: str, emergent_llm_key: str) -> Optional[str]:
    """Return a cached data-URL for the saint, generating it once if absent.

    A per-slug lock prevents concurrent first-hit requests from generating the
    image more than once (the detail endpoint warms it while the image endpoint
    may also ask for it)."""
    col = db["companion_images"]
    cached = await col.find_one({"slug": slug}, {"_id": 0, "data_url": 1})
    if cached and cached.get("data_url"):
        return cached["data_url"]
    if not emergent_llm_key:
        return None
    lock = _IMG_LOCKS.setdefault(slug, asyncio.Lock())
    async with lock:
        # Re-check inside the lock: another waiter may have just generated it.
        cached = await col.find_one({"slug": slug}, {"_id": 0, "data_url": 1})
        if cached and cached.get("data_url"):
            return cached["data_url"]
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            chat = LlmChat(api_key=emergent_llm_key, session_id=f"companion-img-{slug}",
                           system_message="You are an illustrator of reverent, peaceful Catholic devotional art.")
            chat.with_model("gemini", IMAGE_MODEL).with_params(modalities=["image", "text"])
            _text, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
            if images:
                img = images[0]
                data_url = f"data:{img.get('mime_type', 'image/png')};base64,{img['data']}"
                await col.update_one(
                    {"slug": slug},
                    {"$set": {"slug": slug, "data_url": data_url, "created_at": datetime.now(timezone.utc).isoformat()}},
                    upsert=True,
                )
                logger.info("companions: generated image for %s (%s)", slug, img.get("mime_type"))
                return data_url
        except Exception as ex:  # noqa: BLE001
            logger.warning("companions: image generation failed for %s: %s", slug, repr(ex)[:120])
    return None


def _public(slug: str, c: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "slug": slug,
        "name": c["name"],
        "feast": c.get("feast"),
        "importance": c["importance"],
        "virtues": c["virtues"],
        "novena_slug": c.get("novena_slug"),
        "daily_act": _today_act(c["daily_acts"]),
        "has_consecration": True,  # the St. Joseph consecration is open to all companions
        "is_joseph": slug == "st-joseph",
    }


def build_router(db: AsyncIOMotorDatabase, get_current_user, emergent_llm_key: str = "") -> APIRouter:
    router = APIRouter(prefix="/companions", tags=["companions"])

    @router.get("/{slug}")
    async def get_companion(slug: str, user=Depends(get_current_user)):
        c = COMPANIONS.get(slug)
        if not c:
            raise HTTPException(status_code=404, detail="Companion not found")
        # Warm the illustration in the background so the image endpoint is fast.
        asyncio.create_task(_get_or_make_image(db, slug, c["image_prompt"], emergent_llm_key))
        return _public(slug, c)

    @router.get("/{slug}/image")
    async def get_companion_image(slug: str, user=Depends(get_current_user)):
        c = COMPANIONS.get(slug)
        if not c:
            raise HTTPException(status_code=404, detail="Companion not found")
        data_url = await _get_or_make_image(db, slug, c["image_prompt"], emergent_llm_key)
        return {"image": data_url}

    return router

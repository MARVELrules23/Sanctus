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
    "guardian-angel": {
        "name": "Your Guardian Angel",
        "feast": "October 2",
        "novena_slug": "guardian-angel",
        "linked": "padre-pio",
        "do_not_name": True,
        "note": ("Unlike every other companion on this list, this one has known you since before you were "
                 "born — and will be with you until the moment you stand before God. The Catechism (336) "
                 "teaches that 'from its beginning until death, human life is surrounded by their watchful "
                 "care and intercession.'\n\nA gentle reminder: we do not name our guardian angel. The "
                 "Church asks us not to give angels names of our own choosing — it is not our place to do so. "
                 "Simply call on 'my Guardian Angel.'"),
        "image_prompt": "a radiant guardian angel with large gentle feathered wings standing protectively, soft golden light, hands resting in blessing, " + _IMG_STYLE,
        "importance": "Your guardian angel was given to you by God to guard, guide, and light your way home to Heaven. Devotion to your angel — like St. Padre Pio's — keeps you aware that you are never alone, and that an unseen friend constantly carries your prayers before the throne of God.",
        "virtues": [
            {"name": "Awareness of God's presence", "how": "Remember through the day that you are never alone — your angel is at your side."},
            {"name": "Docility", "how": "Listen for the gentle promptings of grace and follow them."},
            {"name": "Trust", "how": "Entrust your travels, decisions, and dangers to your angel's care."},
            {"name": "Gratitude", "how": "Thank God for the unseen friend who has guarded you since birth."},
        ],
        "daily_acts": [
            "Pray the 'Angel of God' prayer the moment you wake.",
            "Ask your guardian angel to guide one decision today.",
            "Before travelling, entrust your journey to your angel.",
            "Pause and remember: 'I am never alone — my angel is here.'",
            "Send your guardian angel to someone who needs help today (as Padre Pio did).",
            "Thank your angel tonight for guarding you through the day.",
            "Ask your angel to wake your soul to one temptation before it comes.",
            "Pray for the conversion of someone, asking your angel to assist them.",
            "Follow a gentle good prompting you would normally ignore.",
            "Greet the guardian angels of the people you meet today.",
            "Ask your angel to keep watch over your sleep tonight.",
            "Offer a quiet 'thank you' each time you are kept from harm.",
            "Call on your angel before a hard conversation.",
            "Entrust a worry to your angel and let it go.",
            "Be a 'guardian' to someone weaker today, imitating your angel.",
            "End the day asking your angel to present your deeds to God.",
        ],
    },
    "padre-pio": {
        "name": "St. Padre Pio",
        "feast": "September 23",
        "novena_slug": "st-padre-pio",
        "linked": "guardian-angel",
        "image_prompt": "Saint Padre Pio, elderly Capuchin friar in brown habit with a white beard, fingerless gloves over his stigmata, kind serious face, " + _IMG_STYLE,
        "importance": "Padre Pio bore the wounds of Christ for fifty years, spent endless hours hearing confessions, and was so close to his guardian angel that he sent it on errands of prayer. His motto — 'Pray, hope, and don't worry' — anchors a life of total trust in God.",
        "virtues": [
            {"name": "Trust ('don't worry')", "how": "Hand your anxieties to God and refuse to be ruled by worry."},
            {"name": "Love of Confession", "how": "Go to Confession often and examine your conscience daily."},
            {"name": "Perseverance in prayer", "how": "Pray the Rosary faithfully — his 'weapon.'"},
            {"name": "Patient suffering", "how": "Offer your pains and trials in union with the Cross."},
        ],
        "daily_acts": [
            "Repeat his motto today: 'Pray, hope, and don't worry.'",
            "Pray the Rosary — Padre Pio called it his 'weapon.'",
            "Ask your guardian angel to carry a prayer to someone, as Padre Pio did.",
            "Examine your conscience tonight and resolve to go to Confession soon.",
            "Offer a pain or annoyance in union with the wounds of Christ.",
            "Spend a few minutes in thanksgiving after Communion, as he urged.",
            "Refuse one worry today and entrust it entirely to God.",
            "Pray for someone who has hurt you.",
            "Do a hidden penance and tell no one.",
            "Make a spiritual communion if you cannot receive today.",
            "Pray, 'Stay with me, Lord,' as in his famous prayer.",
            "Be patient with an interruption, offering it to God.",
            "Encourage someone to return to the sacraments.",
            "Ask the Holy Spirit for sorrow for your sins.",
            "Send your guardian angel ahead to a difficult meeting.",
            "End the day in trust: 'Jesus, I place everything in Your hands.'",
        ],
    },
    "st-lucy": {
        "name": "St. Lucy",
        "feast": "December 13",
        "novena_slug": "st-lucy",
        "image_prompt": "Saint Lucy, young woman in a white and red robe holding a small dish with a palm branch, crown of light, " + _IMG_STYLE,
        "importance": "Lucy ('light') is the virgin-martyr who kept her faith and her purity even unto death, and whose name means light. Patroness of eyes and of those in darkness, she helps us see by the light of faith and to give Christ first place in our hearts.",
        "virtues": [
            {"name": "Light of faith", "how": "Let the light of Christ guide your choices today."},
            {"name": "Purity", "how": "Guard your heart, eyes, and mind for love of God."},
            {"name": "Courage", "how": "Hold to the truth even when it is costly."},
            {"name": "Generosity to the poor", "how": "Give from what you have, as Lucy gave her dowry."},
        ],
        "daily_acts": [
            "Ask St. Lucy for the light to see what God asks of you today.",
            "Guard your eyes from one thing that dims your soul.",
            "Pray for those suffering with eye or sight troubles.",
            "Give something of yours to the poor, as Lucy gave her dowry.",
            "Bring the 'light' of a kind word into someone's dark day.",
            "Hold to the truth in one situation, even if it costs you.",
            "Light a candle and pray for someone walking in darkness.",
            "Offer a small sacrifice for the gift of faith.",
            "Choose purity in your words and screens today.",
            "Thank God for the gift of sight and of the light of faith.",
            "Pray for the persecuted who keep the faith in darkness.",
            "Do one good deed quietly, letting your light shine unseen.",
            "Ask for courage to witness to Christ today.",
            "Spend a moment before the Light of the world in the Eucharist.",
            "Encourage someone who feels they are in the dark.",
            "End the day asking Christ, the true Light, to guard your night.",
        ],
    },
    "st-faustina": {
        "name": "St. Faustina",
        "feast": "October 5",
        "novena_slug": "st-faustina",
        "image_prompt": "Saint Faustina Kowalska, young Polish nun in a black and white habit, gentle face, rays of red and white light nearby, " + _IMG_STYLE,
        "importance": "Faustina was the humble sister chosen by Jesus to be the 'secretary' of His Mercy. Through her the Lord gave the world the Divine Mercy image, chaplet, and feast. She teaches childlike trust: 'Jesus, I trust in You,' and to be merciful in deed, word, and prayer.",
        "virtues": [
            {"name": "Trust in Divine Mercy", "how": "Say with all your heart, 'Jesus, I trust in You.'"},
            {"name": "Mercy in action", "how": "Show mercy by a deed, a word, and a prayer each day."},
            {"name": "Humility", "how": "Embrace the hidden, ordinary path as she did."},
            {"name": "Confidence in prayer", "how": "Approach God as a trusting child, sure of His love."},
        ],
        "daily_acts": [
            "Pray, 'Jesus, I trust in You,' especially when you are afraid.",
            "Show mercy today by a deed, a word, AND a prayer.",
            "Pray the Chaplet of Divine Mercy, especially at 3 o'clock.",
            "Forgive someone, as the Father is merciful.",
            "Do a hidden act of kindness for a difficult person.",
            "Read a short passage of her 'Diary' (Divine Mercy in My Soul).",
            "Pray for a sinner who needs God's mercy today.",
            "Offer your weakness to Jesus with childlike trust.",
            "Speak a merciful word instead of a critical one.",
            "Pause at 3:00 PM to honour the Hour of Mercy.",
            "Give an act of mercy to the poor or suffering.",
            "Trust God with a fear you usually carry alone.",
            "Pray for the dying, that they meet the Mercy of God.",
            "Thank Jesus for His Mercy toward you, by name.",
            "Be patient and gentle, mirroring the Mercy you've received.",
            "End the day entrusting everyone you met to Divine Mercy.",
        ],
    },
    "blessed-virgin-mary": {
        "name": "The Blessed Virgin Mary",
        "feast": "January 1 (Mary, Mother of God)",
        "novena_slug": "our-lady-perpetual-help",
        "image_prompt": "The Blessed Virgin Mary as a tender nurturing mother in blue and white veil, holding the Christ Child close with a gentle loving gaze, soft halo of twelve stars, " + _IMG_STYLE,
        "importance": "Mary is the Mother God gave to us from the Cross — 'Behold your mother.' Her nurturing heart shelters, feeds, and forms us, leading us gently to Jesus. To walk with her is to be mothered: held in tenderness, taught to ponder, and carried close to her Son.",
        "virtues": [
            {"name": "Maternal tenderness", "how": "Care for others gently, as a mother cares for her child."},
            {"name": "Pondering heart", "how": "Treasure and ponder God's word and works in quiet."},
            {"name": "Fiat — loving 'yes'", "how": "Say yes to God's will today, as Mary did."},
            {"name": "Humble service", "how": "Hasten to help others in need, as she went to Elizabeth."},
        ],
        "daily_acts": [
            "Pray a decade of the Rosary, resting in your Mother's care.",
            "Entrust your day to Mary with a morning 'Hail Mary.'",
            "Do one tender, nurturing act for someone in your life.",
            "Ponder a word of Scripture in your heart through the day.",
            "Say your 'fiat': accept one part of God's will with love.",
            "Hasten to help someone in need, as Mary visited Elizabeth.",
            "Pray the Memorare in a moment of worry.",
            "Wear or hold the Brown Scapular and renew your trust in her.",
            "Bring a hidden burden to your Mother and leave it with her.",
            "Speak gently to someone who is hurting today.",
            "Offer your work to Jesus through the hands of Mary.",
            "Pray the Angelus at noon, recalling the Word made flesh.",
            "Comfort someone who feels alone, as a mother would.",
            "Thank God for the gift of Mary as your Mother.",
            "Keep a small image of Our Lady near you and glance to her often.",
            "End the day in her mantle: 'Holy Mary, Mother of God, pray for me.'",
        ],
    },
    "sacred-heart": {
        "name": "The Sacred Heart of Jesus",
        "feast": "Most Sacred Heart of Jesus (June)",
        "novena_slug": "sacred-heart-jesus",
        "image_prompt": "The Sacred Heart of Jesus, Jesus with a gentle compassionate face pointing to His radiant heart crowned with thorns and flames, soft golden light, " + _IMG_STYLE,
        "importance": "The Sacred Heart is the furnace of God's love — a Heart that loved us to the end and was pierced for our sake. To walk with the Sacred Heart is to live in His love, to make reparation for indifference, and to learn from a Heart 'meek and humble.'",
        "virtues": [
            {"name": "Love in return", "how": "Return love for Love — offer your heart to His each morning."},
            {"name": "Meekness & humility", "how": "Learn from His Heart, meek and humble, in your dealings today."},
            {"name": "Reparation", "how": "Make a small act of love to console His Heart for the world's coldness."},
            {"name": "Trust & confidence", "how": "Rest in His love, especially when you feel unworthy."},
        ],
        "daily_acts": [
            "Pray, 'Sacred Heart of Jesus, I place my trust in You.'",
            "Offer your heart to His Heart at the start of the day.",
            "Make a Morning Offering of all you do today for love of Him.",
            "Console His Heart with one act of love for a neglected person.",
            "Learn meekness: respond gently where you'd usually react.",
            "Spend a few minutes before the Blessed Sacrament, heart to Heart.",
            "Make a small reparation for the indifference of the world.",
            "Practice the First Friday devotion this month, or resolve to begin it.",
            "Forgive from the heart someone who wronged you.",
            "Pray the Litany of the Sacred Heart, or one of its invocations.",
            "Carry your day's burden to His Heart and rest there.",
            "Show His love through one concrete act of charity.",
            "Thank Jesus for loving you 'to the end.'",
            "Offer a sacrifice to console the Heart that was pierced for you.",
            "Pause at midday: 'Jesus, meek and humble of Heart, make my heart like Yours.'",
            "End the day enthroned in His love: place everything in His Heart.",
        ],
    },
    "sts-peter-paul": {
        "name": "Sts. Peter & Paul",
        "feast": "June 29",
        "novena_slug": "sts-peter-paul",
        "image_prompt": "Saints Peter and Paul standing together, Peter holding golden keys and Paul holding a sword and book, dignified apostles in robes, soft light, " + _IMG_STYLE,
        "importance": "Peter, the rock on whom Christ built His Church, and Paul, the tireless Apostle to the nations, are the twin pillars of the faith. One fell and was raised by mercy; the other was seized by grace on the road. Together they teach steadfast faith and fearless zeal for souls.",
        "virtues": [
            {"name": "Rock-solid faith", "how": "Confess Jesus as Lord boldly, as Peter did."},
            {"name": "Apostolic zeal", "how": "Share the faith with someone, in word or example, as Paul did."},
            {"name": "Repentance & mercy", "how": "Rise quickly after a fall, trusting Christ's mercy like Peter."},
            {"name": "Perseverance", "how": "Run the race to the end; finish your duties faithfully."},
        ],
        "daily_acts": [
            "Make a bold act of faith today: 'You are the Christ, the Son of the living God.'",
            "Pray for the Pope, the successor of Peter.",
            "Share one word about Christ, or witness by example, as Paul did.",
            "Rise quickly from a fault today, trusting in mercy as Peter did.",
            "Read a short passage from one of St. Paul's letters.",
            "Pray for the unity and strength of the Church.",
            "Do your duty faithfully, 'finishing the race' as St. Paul wrote.",
            "Forgive yourself a past failure and let Christ raise you up.",
            "Encourage someone in their faith today.",
            "Pray for missionaries carrying the Gospel to the nations.",
            "Offer a hardship for love of Christ, as the apostles suffered for Him.",
            "Defend the truth gently in one conversation.",
            "Pray for the bishops and priests who shepherd the Church.",
            "Step out in faith on something you've been afraid to do for God.",
            "Pray for the conversion of one person far from Christ.",
            "End the day: 'Lord, You know everything; You know that I love You.'",
        ],
    },
    "carlo-acutis": {
        "name": "St. Carlo Acutis",
        "feast": "October 12",
        "novena_slug": None,
        "image_prompt": "Saint Carlo Acutis, smiling teenage boy with dark hair in a red polo shirt and backpack, holding a rosary, modern and youthful, gentle light, " + _IMG_STYLE,
        "importance": "Carlo Acutis was an ordinary teenager who loved computers, programming, and football — yet he called the Eucharist 'my highway to heaven.' He used the internet to spread word of Eucharistic miracles and shows young people that holiness is possible now, with the very tools of modern life.",
        "virtues": [
            {"name": "Eucharistic love", "how": "Make the Eucharist your 'highway to heaven' — Mass and Communion at the centre of the day."},
            {"name": "Purity in a digital age", "how": "Use your phone and the internet for good; guard your eyes and heart online."},
            {"name": "Joyful ordinariness", "how": "Be yourself and be a saint — holiness in homework, friends, and hobbies."},
            {"name": "Love of Our Lady", "how": "Pray the Rosary every day, as Carlo never missed his."},
        ],
        "daily_acts": [
            "Make the Eucharist the centre of your day — attend Mass or make a spiritual Communion.",
            "Pray a decade (or the whole) Rosary, as Carlo did every single day.",
            "Use your phone or the internet today for one genuinely good purpose.",
            "Guard your eyes online — turn away from one thing you shouldn't look at.",
            "Make a short visit to the Blessed Sacrament: your 'highway to heaven.'",
            "Do an ordinary duty (homework, chores, work) with great love.",
            "Tell a friend about something beautiful in the faith.",
            "Offer a small sacrifice for the souls in Purgatory.",
            "Be kind to someone left out or bullied, as Carlo defended the weak.",
            "Examine your conscience tonight and plan to go to Confession soon.",
            "Give some pocket money or time to someone poor.",
            "Choose to 'be original, not a photocopy' — resist one peer pressure today.",
            "Thank God for the gift of the Eucharist in your own words.",
            "Spend less time scrolling; give that time to prayer or family.",
            "Pray, 'To always be close to Jesus, that's my life plan.'",
            "End the day asking Our Lady to lead you to her Son.",
        ],
    },
    "fulton-sheen": {
        "name": "Ven. Fulton Sheen",
        "feast": "December 9",
        "novena_slug": None,
        "image_prompt": "Venerable Fulton Sheen, dignified American bishop in black cassock with red zucchetto and pectoral cross, warm expressive face and piercing eyes, " + _IMG_STYLE,
        "importance": "Venerable Fulton Sheen brought Christ to millions through radio and television, winning Emmy awards while preaching the Gospel. Yet the secret of his fruitfulness was the daily Holy Hour before the Blessed Sacrament, which he never missed for over sixty years.",
        "virtues": [
            {"name": "The daily Holy Hour", "how": "Spend time before the Blessed Sacrament each day, as he did for sixty years."},
            {"name": "Bold evangelisation", "how": "Witness to Christ confidently and winsomely in your own world."},
            {"name": "Wit and joy", "how": "Use humour and culture to draw others gently toward the truth."},
            {"name": "Reparation", "how": "Offer small sacrifices and your work for the conversion of souls."},
        ],
        "daily_acts": [
            "Make a Holy Hour — or at least a few minutes — before the Blessed Sacrament.",
            "Begin your day by giving God the first thoughts of the morning.",
            "Speak one confident, kind word about Christ to someone today.",
            "Offer your work today for the conversion of a particular soul.",
            "Read a few lines of Scripture or a Sheen reflection and ponder them.",
            "Bring a touch of holy humour to lighten someone's burden.",
            "Make a small sacrifice and unite it to the Mass for sinners.",
            "Pray for priests, that they may be holy and bold.",
            "Examine where the world has shaped you more than the Gospel — and adjust one thing.",
            "Turn off the noise for a while and sit in silence with the Lord.",
            "Encourage someone to take their faith seriously, without preaching at them.",
            "Pray for those who have no one to pray for them.",
            "Offer your suffering today; 'unless there is a Good Friday, there is no Easter Sunday.'",
            "Give generously and quietly to someone in need.",
            "Renew your love before the Eucharist: 'the Hour that makes my day.'",
            "End the day thanking God for one way He used you to reach another.",
        ],
    },
    "augustine": {
        "name": "St. Augustine of Hippo",
        "feast": "August 28",
        "image_prompt": "Saint Augustine of Hippo, bishop in ornate cope and mitre holding a flaming heart and a book, thoughtful and prayerful, " + _IMG_STYLE,
        "importance": "Augustine turned from a restless, sinful youth to become one of the Church's greatest bishops and Doctors. His 'Confessions' show that no past is too dark for grace: 'You have made us for Yourself, O Lord, and our heart is restless until it rests in You.' He is the patron of converts and of the restless heart seeking truth.",
        "virtues": [
            {"name": "Restless seeking of truth", "how": "Keep searching for God honestly, refusing to settle for lesser goods."},
            {"name": "Humble confession", "how": "Name your sins plainly before God, trusting His mercy more than your failures."},
            {"name": "Love as the measure", "how": "'Love, and do what you will' — let charity order every choice."},
            {"name": "Interior conversion", "how": "Turn inward daily; God is 'more inward to me than my innermost self.'"},
        ],
        "daily_acts": [
            "Pray, 'Our heart is restless until it rests in You,' and offer your restlessness to God.",
            "Make an honest confession of one fault, trusting His mercy.",
            "Read a short passage of the 'Confessions' as lectio divina.",
            "Spend five minutes in interior silence, seeking God within.",
            "Turn away from one lesser good today for the sake of the greatest Good.",
            "Pray for someone who has drifted from the faith, as St. Monica prayed for you.",
            "Do one act purely for love, then 'do what you will.'",
            "Thank God for a grace that drew you back to Him.",
            "Order your day around one fixed time of prayer.",
            "End the day praising 'Beauty ever ancient, ever new.'",
        ],
        "novena_slug": "st-augustine",
    },
    "john-the-baptist": {
        "name": "St. John the Baptist",
        "feast": "June 24 (Nativity)",
        "image_prompt": "Saint John the Baptist, rugged prophet in camel-hair garment holding a slender reed cross, pointing upward by the Jordan, " + _IMG_STYLE,
        "importance": "John was the forerunner of Christ, the voice crying in the wilderness who prepared the way of the Lord. Filled with the Spirit from the womb, he lived in penance and pointed always away from himself: 'He must increase, but I must decrease.' He is the model of humility, courage, and repentance.",
        "virtues": [
            {"name": "Humility", "how": "Point to Christ, not yourself: 'He must increase, but I must decrease.'"},
            {"name": "Courageous truth", "how": "Speak the truth even to the powerful, whatever the cost."},
            {"name": "Penance", "how": "Embrace simplicity and self-denial to make room for God."},
            {"name": "Preparing the way", "how": "Make straight in your own heart a highway for the Lord."},
        ],
        "daily_acts": [
            "Pray, 'He must increase, but I must decrease,' and step back so Christ is seen.",
            "Make one small act of penance in the spirit of the desert.",
            "Speak a needed truth today with courage and charity.",
            "Simplify one thing you own or consume.",
            "Point someone toward Christ by a quiet word or example.",
            "Examine your conscience and repent of one sin.",
            "Spend time in silence, listening as John listened in the wilderness.",
            "Fast from one comfort and offer it in reparation.",
            "Pray for the grace of true humility.",
            "Behold the Lamb of God at Mass or in adoration, and adore.",
        ],
        "novena_slug": "st-john-baptist",
    },
    "james-the-less": {
        "name": "St. James the Less",
        "feast": "May 3 (with St. Philip)",
        "image_prompt": "Saint James the Less, apostle in simple robe holding a fuller's club and a scroll, steady and prayerful, " + _IMG_STYLE,
        "importance": "James the Less, an Apostle and first bishop of Jerusalem, was called 'the Just' for his holiness and constant prayer. His letter urges a living faith: 'Faith without works is dead.' A man whose knees were worn from prayer, he shows that leadership in the Church is built on justice, prayer, and works of mercy.",
        "virtues": [
            {"name": "Living faith", "how": "Let your faith show in concrete works of mercy — 'faith without works is dead.'"},
            {"name": "Constancy in prayer", "how": "Be a person of persevering prayer, like James 'the Just.'"},
            {"name": "Care for the poor", "how": "Show no partiality; honor the lowly as much as the great."},
            {"name": "Steadfast leadership", "how": "Serve quietly and justly wherever you are entrusted."},
        ],
        "daily_acts": [
            "Put your faith into action with one concrete work of mercy today.",
            "Spend extra time on your knees in prayer.",
            "Show kindness to someone the world overlooks.",
            "Read a short passage of the Letter of St. James.",
            "Guard your tongue, which James calls a small member that sets great fires.",
            "Be 'quick to hear, slow to speak, slow to anger' in one conversation.",
            "Ask a priest or the sick if they need prayers, and offer them.",
            "Give patiently in a trial, counting it 'all joy.'",
            "Pray for the unity and holiness of the Church's shepherds.",
            "End the day examining whether your faith was living today.",
        ],
        "novena_slug": "st-james-less",
    },
    "thomas-aquinas": {
        "name": "St. Thomas Aquinas",
        "feast": "January 28",
        "image_prompt": "Saint Thomas Aquinas, Dominican friar in white and black habit holding a book and a radiant sun on his chest, serene and brilliant, " + _IMG_STYLE,
        "importance": "Thomas Aquinas, the 'Angelic Doctor,' united faith and reason as no other, giving the Church the 'Summa Theologiae' and the great Eucharistic hymns. Yet this towering genius was a man of deep prayer who called all his writing 'straw' before the vision of God. He is the patron of students and of all who seek truth on their knees.",
        "virtues": [
            {"name": "Faith seeking understanding", "how": "Study the faith prayerfully; let reason serve belief."},
            {"name": "Eucharistic love", "how": "Adore the Blessed Sacrament, the theme of his greatest hymns."},
            {"name": "Humility of the mind", "how": "Hold your knowledge lightly; before God all is 'straw.'"},
            {"name": "Diligent study", "how": "Offer your learning and work to God as a form of prayer."},
        ],
        "daily_acts": [
            "Begin study or work with his prayer, 'Creator of all things, true source of light and wisdom.'",
            "Learn one truth of the faith today and thank God for it.",
            "Adore the Blessed Sacrament; pray a verse of 'Adoro te devote' or 'Tantum Ergo.'",
            "Hold an opinion humbly; seek the truth rather than winning.",
            "Offer your studies or labor to God as prayer.",
            "Read a short article of the Summa or Catechism slowly.",
            "Practise recollection: withdraw the mind to God amid busy work.",
            "Give a clear, charitable answer to someone's honest question about the faith.",
            "Pray for students and teachers.",
            "End the day acknowledging that all you know is a gift and 'straw' before God.",
        ],
        "novena_slug": "st-thomas-aquinas",
    },

}


# --------------------------------------------------------------------------- #
# Traditions the Church holds for each saint (hand-curated, saint-specific).   #
# --------------------------------------------------------------------------- #
CHURCH_TRADITIONS: Dict[str, List[Dict[str, str]]] = {
    "carlo-acutis": [
        {"title": "Pilgrimage to Assisi", "body": "His tomb in Assisi, where he is seen in jeans and trainers, has become a place of pilgrimage for the young."},
        {"title": "The Eucharistic Miracles exhibition", "body": "His online catalogue of approved Eucharistic miracles travels the world in parishes and schools."},
        {"title": "Patron of the internet & youth", "body": "Increasingly invoked by young people and for the right use of technology."},
    ],
    "fulton-sheen": [
        {"title": "The daily Holy Hour", "body": "Sheen popularised the daily Holy Hour before the Blessed Sacrament, which he kept for over sixty years."},
        {"title": "Catholic radio & television", "body": "His broadcasts ('The Catholic Hour,' 'Life Is Worth Living') are a model for evangelising through the media."},
        {"title": "Prayer for his cause", "body": "The faithful pray for miracles through his intercession toward beatification."},
    ],
    "catherine-siena": [
        {"title": "Pray for the Pope & the Church", "body": "As a Doctor and co-patroness of Europe who counselled popes, the faithful invoke her for the Holy Father and Church unity."},
        {"title": "Read the 'Dialogue'", "body": "Her mystical 'Dialogue of Divine Providence' is treasured spiritual reading on her feast (April 29)."},
        {"title": "Dominican devotion", "body": "A Third Order Dominican, she is honoured with the Dominican Rosary and a pilgrimage to her shrine in Siena."},
    ],
    "pier-giorgio": [
        {"title": "'Verso l'alto' outing", "body": "Pilgrims climb a mountain or hike on his feast (July 4), offering the heights to God as he did."},
        {"title": "Secret almsgiving", "body": "In his memory the faithful serve the poor quietly, the way he gave away his money and even his bus fare."},
        {"title": "Eucharistic adoration", "body": "He drew his joy from daily Communion and adoration — a devotion encouraged in his honour."},
    ],
    "john-paul-ii": [
        {"title": "Divine Mercy", "body": "He canonized St. Faustina and gave the Church Divine Mercy Sunday; the Chaplet of Divine Mercy is prayed in his memory."},
        {"title": "Luminous Mysteries", "body": "He added the Mysteries of Light to the Rosary — pray them especially on his feast (Oct 22)."},
        {"title": "Totus Tuus consecration", "body": "Renew Marian consecration ('Totus Tuus') as he did, entrusting everything to Our Lady."},
    ],
    "agnes": [
        {"title": "Blessing of the lambs", "body": "On her feast (Jan 21) lambs are blessed in Rome; their wool weaves the pallia given to archbishops."},
        {"title": "Patroness of purity", "body": "Young people consecrate their chastity to God under her protection."},
        {"title": "Pilgrimage to her basilica", "body": "The faithful venerate her at Sant'Agnese fuori le mura in Rome."},
    ],
    "therese-lisieux": [
        {"title": "The Little Way", "body": "Offer small acts of love and 'sacrifice beads' through the day, her path to holiness."},
        {"title": "Shower of roses novena", "body": "Her famous novena trusts she will send a rose as a sign of intercession."},
        {"title": "Relic veneration", "body": "Her relics travel the world; pilgrims honour the Doctor of the Little Way at Lisieux."},
    ],
    "benedict": [
        {"title": "The St. Benedict medal", "body": "Worn and placed in homes for protection; often blessed with the special Jubilee blessing."},
        {"title": "Liturgy of the Hours", "body": "Pray the Hours and practise 'ora et labora' after his Rule."},
        {"title": "Blessing of the home", "body": "Homes and doorways are blessed under his patronage against evil."},
    ],
    "francis-assisi": [
        {"title": "The Christmas crèche", "body": "St. Francis created the first Nativity scene at Greccio — set one up in your home at Christmas."},
        {"title": "Blessing of animals", "body": "On his feast (Oct 4) pets and animals are brought to be blessed."},
        {"title": "The Transitus & Franciscan Crown", "body": "Keep the vigil of his death (Oct 3) and pray the Seraphic Rosary (Franciscan Crown)."},
        {"title": "Portiuncula indulgence", "body": "Visit a church on Aug 2 for the indulgence he obtained at the Portiuncula."},
    ],
    "teresa-avila": [
        {"title": "Mental prayer", "body": "Keep a daily time of quiet prayer, the heart of her Carmelite teaching."},
        {"title": "St. Teresa's bookmark", "body": "Pray her words: 'Let nothing disturb you… God alone suffices.'"},
        {"title": "The Brown Scapular", "body": "Wear the Carmelite scapular and honour the Doctor of Prayer on her feast (Oct 15)."},
    ],
    "st-joseph": [
        {"title": "St. Joseph's Table", "body": "On March 19 families set a St. Joseph altar of food and share it with the poor."},
        {"title": "Wednesdays for St. Joseph", "body": "Dedicate Wednesdays to him and pray the Litany of St. Joseph."},
        {"title": "'Go to Joseph'", "body": "Bring your needs to the Patron of the Universal Church and of a happy death."},
        {"title": "33-day Consecration", "body": "Entrust yourself to Jesus through St. Joseph with the 33-day consecration."},
    ],
    "louis-zelie": [
        {"title": "The family Rosary", "body": "Pray the Rosary together as a household, as the Martins did each evening."},
        {"title": "Consecrate your family", "body": "Entrust your home to the Holy Family on their feast (July 12)."},
        {"title": "Pilgrimage to Alençon/Lisieux", "body": "Families honour the first canonized spouses at their shrines."},
    ],
    "gianna-molla": [
        {"title": "Prayer for mothers & the unborn", "body": "She is invoked for expectant mothers, difficult pregnancies, and the protection of life."},
        {"title": "Patroness of physicians", "body": "Doctors and the sick seek her intercession on her feast (April 28)."},
        {"title": "A glad heart in duty", "body": "Offer professional and family work joyfully, as she sanctified hers."},
    ],
    "monica": [
        {"title": "Novena for conversions", "body": "Pray persistently for loved ones far from God, trusting her decades of tears for Augustine."},
        {"title": "Feast before St. Augustine", "body": "Her feast (Aug 27) precedes her son's (Aug 28) — honour them together."},
        {"title": "Patroness of mothers & wives", "body": "Mothers, wives, and those bearing family burdens entrust themselves to her."},
    ],
    "guardian-angel": [
        {"title": "The 'Angel of God' prayer", "body": "Pray it morning and night: 'Angel of God, my guardian dear…' — a treasured Catholic devotion."},
        {"title": "Feast of the Guardian Angels", "body": "Honour your angel especially on October 2."},
        {"title": "Send your angel on errands", "body": "Like St. Padre Pio, ask your angel to carry prayers and help others."},
    ],
    "padre-pio": [
        {"title": "Pray the Rosary daily", "body": "His 'weapon' against evil — keep it always in hand."},
        {"title": "Frequent Confession", "body": "Imitate the saint who spent his life in the confessional; examine your conscience daily."},
        {"title": "Devotion to the guardian angel", "body": "Honour your angel as Padre Pio did, sending it to those in need."},
        {"title": "'Stay with me, Lord' prayer", "body": "Pray his beloved prayer after Communion."},
    ],
    "st-lucy": [
        {"title": "Festival of light", "body": "On her feast (Dec 13) candles and crowns of light honour Lucy, whose name means 'light.'"},
        {"title": "Patroness of the eyes", "body": "Invoke her for eye troubles and for the light of faith."},
        {"title": "Almsgiving", "body": "Give to the poor in her memory, as she gave away her dowry."},
    ],
    "st-faustina": [
        {"title": "Chaplet of Divine Mercy", "body": "Pray it daily, especially at the 3 o'clock Hour of Mercy."},
        {"title": "Divine Mercy image", "body": "Venerate the image inscribed 'Jesus, I trust in You.'"},
        {"title": "Divine Mercy Sunday", "body": "Keep the feast on the Sunday after Easter, with its great graces."},
    ],
    "blessed-virgin-mary": [
        {"title": "The Holy Rosary", "body": "Pray the Rosary daily — the Church's great Marian devotion, meditating on Christ with His Mother."},
        {"title": "The Angelus", "body": "Pray it at 6am, noon, and 6pm, recalling the Incarnation."},
        {"title": "The Brown Scapular", "body": "Wear the scapular of Our Lady of Mount Carmel as a sign of her motherly protection."},
        {"title": "Marian consecration & feasts", "body": "Entrust yourself to her ('Totus Tuus') and honour her many feasts through the year."},
    ],
    "sacred-heart": [
        {"title": "First Friday devotion", "body": "Receive Communion on nine consecutive First Fridays, as the Lord asked St. Margaret Mary."},
        {"title": "Enthronement of the home", "body": "Enthrone an image of the Sacred Heart and consecrate your household to His love."},
        {"title": "Morning Offering & Litany", "body": "Begin the day offering all to His Heart; pray the Litany of the Sacred Heart."},
    ],
    "sts-peter-paul": [
        {"title": "Solemnity on June 29", "body": "Honour the two pillars of the Church together on their great feast."},
        {"title": "Pray for the Pope", "body": "Pray for Peter's successor and the unity of the Church."},
        {"title": "Read St. Paul's letters", "body": "Take up the Epistles as daily spiritual reading and apostolic encouragement."},
    ],
}

# --------------------------------------------------------------------------- #
# Daily traditions — small, repeatable practices (rooted in the Church's       #
# devotional tradition for each saint) one can do EACH DAY to grow closer.     #
# Distinct from CHURCH_TRADITIONS above (which lean to feasts & customs).       #
# --------------------------------------------------------------------------- #
DAILY_TRADITIONS: Dict[str, List[Dict[str, str]]] = {
    "carlo-acutis": [
        {"title": "Daily Mass & Communion", "body": "Make the Eucharist your 'highway to heaven' — receive or visit Jesus each day."},
        {"title": "The daily Rosary", "body": "Carlo never missed his Rosary; pray at least a decade for Our Lady's protection."},
        {"title": "Use technology for good", "body": "Spend a few minutes using your phone or the web to learn or share something of the faith."},
    ],
    "fulton-sheen": [
        {"title": "Keep a Holy Hour", "body": "Spend time before the Blessed Sacrament daily — 'the Hour that makes my day.'"},
        {"title": "Offer your work for souls", "body": "Dedicate today's tasks for the conversion of one person."},
        {"title": "Witness with joy", "body": "Share the truth with confidence and good humour, as he did on the air."},
    ],
    "catherine-siena": [
        {"title": "Enter the 'inner cell'", "body": "Pause once today in self-knowledge before God, the cell she said we carry within us."},
        {"title": "Pray for the Pope & the Church", "body": "Offer a short daily prayer for the Holy Father and the Church's unity, as she did."},
        {"title": "Speak to Jesus as a friend", "body": "Make a spiritual Communion and tell Christ crucified one thing on your heart."},
    ],
    "pier-giorgio": [
        {"title": "Daily Eucharist", "body": "Receive Communion or make a spiritual Communion — the secret of his joy."},
        {"title": "One hidden act of charity", "body": "Help someone quietly today, the way he gave away even his bus fare."},
        {"title": "Aim 'verso l'alto'", "body": "Pray a decade of the Rosary and offer one effort 'toward the heights.'"},
    ],
    "john-paul-ii": [
        {"title": "Renew 'Totus Tuus'", "body": "Each morning entrust your whole day to Jesus through Mary."},
        {"title": "Chaplet at 3 o'clock", "body": "Pray the Chaplet of Divine Mercy at the Hour of Mercy."},
        {"title": "'Be not afraid'", "body": "Make one courageous act of faith you've been putting off."},
    ],
    "agnes": [
        {"title": "Guard your heart", "body": "Offer a small act of purity today — custody of the eyes and thoughts."},
        {"title": "Pray for the young & the chaste", "body": "Remember those striving for purity in a short daily prayer."},
        {"title": "A quiet courage", "body": "Stand gently for Christ in one ordinary moment today."},
    ],
    "therese-lisieux": [
        {"title": "Sacrifice beads", "body": "Offer small hidden sacrifices through the day, counting them as love."},
        {"title": "Small things, great love", "body": "Do one ordinary task today with extraordinary love."},
        {"title": "Childlike trust", "body": "End the day with a short act of abandonment into the Father's hands."},
    ],
    "benedict": [
        {"title": "Pray the Hours", "body": "Pray at least one hour of the Divine Office (Morning or Evening Prayer)."},
        {"title": "Ora et labora", "body": "Offer your work today as a prayer, doing it for God's glory."},
        {"title": "Listen in silence", "body": "Keep a moment of quiet, listening 'with the ear of your heart.'"},
    ],
    "francis-assisi": [
        {"title": "Be an instrument of peace", "body": "Make peace with one person, or pray his Peace Prayer."},
        {"title": "Praise God in creation", "body": "Thank God for one created thing — Brother Sun, Sister Water."},
        {"title": "A small poverty", "body": "Give something away or do without one comfort for love of Christ."},
    ],
    "teresa-avila": [
        {"title": "Mental prayer", "body": "Keep a set time of quiet conversation with the God who dwells within you."},
        {"title": "Teresa's bookmark", "body": "Pray slowly: 'Let nothing disturb you… God alone suffices.'"},
        {"title": "Recollection", "body": "Recall God's presence within once during the busy day."},
    ],
    "st-joseph": [
        {"title": "'Go to Joseph'", "body": "Bring one need to him today with a short prayer of confidence."},
        {"title": "Work in silence", "body": "Offer your labour quietly and faithfully, as the carpenter of Nazareth did."},
        {"title": "Honour Wednesdays", "body": "Pray the Litany of St. Joseph, especially on Wednesdays."},
    ],
    "louis-zelie": [
        {"title": "The family decade", "body": "Pray at least a decade of the Rosary with (or for) your family."},
        {"title": "Sanctify your duty", "body": "Offer today's work and chores to God as they did."},
        {"title": "Patient love at home", "body": "Make one small act of patient, faithful love for your household."},
    ],
    "gianna-molla": [
        {"title": "Duty with a glad heart", "body": "Do your daily work cheerfully, offering it as love."},
        {"title": "Pray for mothers & the unborn", "body": "Remember expectant mothers and the unborn in a short prayer."},
        {"title": "One sacrifice of love", "body": "Offer a small sacrifice today for someone you love."},
    ],
    "monica": [
        {"title": "Persevere for a loved one", "body": "Pray daily, without losing heart, for someone far from God."},
        {"title": "Offer your worry", "body": "Hand your anxieties to God with trust, as she gave Him her tears."},
        {"title": "An act of hope", "body": "Renew hope that God is at work, even when you see no fruit yet."},
    ],
    "guardian-angel": [
        {"title": "'Angel of God'", "body": "Pray the prayer morning and night, asking to be lit, guarded, ruled, and guided."},
        {"title": "Ask before deciding", "body": "Pause and ask your angel's help before a choice today."},
        {"title": "Send your angel", "body": "Ask your angel to carry a prayer to someone in need."},
    ],
    "padre-pio": [
        {"title": "The Rosary — his weapon", "body": "Keep the Rosary in hand and pray it daily."},
        {"title": "Examine & confess", "body": "Examine your conscience tonight; seek Confession often."},
        {"title": "'Pray, hope, don't worry'", "body": "Make one deliberate act of trust in God's Providence today."},
    ],
    "st-lucy": [
        {"title": "Ask for the light of faith", "body": "Pray to see clearly what God asks of you today."},
        {"title": "Use your eyes for good", "body": "Guard what you look at; turn your gaze to what is true and pure."},
        {"title": "A small almsgiving", "body": "Give to someone in need in her memory, as she gave her dowry."},
    ],
    "st-faustina": [
        {"title": "Chaplet at 3 o'clock", "body": "Pray the Chaplet of Divine Mercy at the Hour of Great Mercy."},
        {"title": "'Jesus, I trust in You'", "body": "Repeat this aspiration often through the day."},
        {"title": "A work of mercy", "body": "Show mercy once today in deed, word, or prayer."},
    ],
    "blessed-virgin-mary": [
        {"title": "Pray the Rosary", "body": "Pray a decade or the full Rosary, meditating on Christ with His Mother."},
        {"title": "The Angelus at noon", "body": "Pause to recall the Incarnation in the Angelus."},
        {"title": "A Hail Mary for the difficult", "body": "Pray a Hail Mary for anyone you find hard to love today."},
    ],
    "sacred-heart": [
        {"title": "Morning Offering", "body": "Offer the day — prayers, works, joys, sufferings — to His Sacred Heart."},
        {"title": "An act of reparation", "body": "Make a spiritual Communion or short act of love to console His Heart."},
        {"title": "'Heart of Jesus, I trust in You'", "body": "Return to His Heart with this aspiration when you grow anxious."},
    ],
    "sts-peter-paul": [
        {"title": "Read St. Paul", "body": "Take up a few verses of the Epistles as daily spiritual reading."},
        {"title": "Confess Christ", "body": "Make an act of faith with Peter: 'You are the Christ, the Son of the living God.'"},
        {"title": "Pray for the Church's mission", "body": "Pray for the Pope and for the spread of the Gospel."},
    ],
}


# Day-focused prayer shown at the top of each companion's daily space.
DAILY_PRAYERS: Dict[str, str] = {
    "catherine-siena": "St. Catherine of Siena, set my heart on fire this day with love for Christ and His Church; let me dwell in the cell of self-knowledge and love. Pray for me today.",
    "pier-giorgio": "Bl. Pier Giorgio, lift my heart 'verso l'alto' today; give me your joy, and let me serve Christ in the poor I meet this day. Pray for me.",
    "john-paul-ii": "St. John Paul II, this day I say 'Totus Tuus' — I am totally yours, Mary. Help me be not afraid and to make a gift of myself today. Pray for me.",
    "agnes": "St. Agnes, guard my heart this day in purity and courage, that I may belong wholly to Christ. Pray for me today.",
    "therese-lisieux": "St. Thérèse, teach me your Little Way today: to do small things with great love and to trust like a child. Send me a rose. Pray for me.",
    "benedict": "St. Benedict, order my day in prayer and work; let me listen for God with the ear of my heart and stay faithful in all things. Pray for me today.",
    "francis-assisi": "St. Francis, make me an instrument of God's peace this day; give me your joyful simplicity and love for all God's creation. Pray for me.",
    "teresa-avila": "St. Teresa, let nothing disturb me today, for God alone suffices. Draw me into prayer and friendship with Christ this day. Pray for me.",
    "st-joseph": "St. Joseph, guardian of the Redeemer, watch over my work and my household this day; lead me, in silence and trust, closer to Jesus. Pray for me.",
    "louis-zelie": "Sts. Louis and Zélie, bless my family this day; help me to love faithfully and to make our home a school of holiness. Pray for us.",
    "gianna-molla": "St. Gianna, help me to love sacrificially today and to do my daily duties with a glad heart, reverencing every life. Pray for me.",
    "monica": "St. Monica, give me perseverance this day to pray without losing heart for those I love, trusting God's timing. Pray for me.",
    "guardian-angel": "Angel of God, my guardian dear, to whom God's love commits me here: ever this day be at my side, to light and guard, to rule and guide. Amen.",
    "padre-pio": "St. Padre Pio, help me this day to 'pray, hope, and don't worry.' Carry my prayers to God and obtain for me trust in His Providence. Pray for me.",
    "st-lucy": "St. Lucy, obtain for me the light of faith this day, that I may see clearly what God asks and walk in His light. Pray for me.",
    "st-faustina": "St. Faustina, help me to say with my whole heart this day, 'Jesus, I trust in You,' and to be merciful in deed, word, and prayer. Pray for me.",
    "blessed-virgin-mary": "Holy Mary, my Mother, take my hand this day; teach me to ponder, to say 'yes' to God, and to bring your gentle love to everyone I meet. Pray for me.",
    "sacred-heart": "Most Sacred Heart of Jesus, I give You my heart this day. Make it meek and humble like Yours, and let everything I do be an act of love for You. I trust in You.",
    "sts-peter-paul": "Sts. Peter and Paul, obtain for me this day a faith as firm as rock and a zeal as bold as fire, that I may follow Christ without fear. Pray for me.",
    "carlo-acutis": "St. Carlo Acutis, help me today to make the Eucharist my 'highway to heaven,' to use all I have for Jesus, and to be original — not a photocopy. Pray for me.",
    "fulton-sheen": "Ven. Fulton Sheen, help me to give God my daily Holy Hour and to witness to Christ with courage and joy in my own world this day. Pray for me.",
    "augustine": "St. Augustine, you made our hearts for God and know their restlessness; win for me true conversion of heart, that I may rest at last in Him. Pray for me.",
    "john-the-baptist": "St. John the Baptist, forerunner of the Lord, teach me humility and courage, that Christ may increase in me and I may decrease. Pray for me.",
    "james-the-less": "St. James the Less, apostle and man of prayer, obtain for me a living faith that shows itself in works of mercy. Pray for me.",
    "thomas-aquinas": "St. Thomas Aquinas, Angelic Doctor, enlighten my mind and enkindle my love, that I may seek the truth and adore it in the Blessed Sacrament. Pray for me.",
}

# The Guardian Angel is a permanent companion for everyone — always present,
# never counted against the 3 daily companions the user chooses.
PERMANENT_COMPANION = "guardian-angel"

# Display order for the daily-companions hub.
COMPANION_ORDER: List[str] = [ "blessed-virgin-mary", "sacred-heart", "guardian-angel", "sts-peter-paul",
    "carlo-acutis", "padre-pio", "st-faustina", "fulton-sheen", "st-lucy",
    "therese-lisieux", "francis-assisi", "st-joseph", "teresa-avila",
    "catherine-siena", "benedict", "john-paul-ii", "pier-giorgio",
    "agnes", "gianna-molla", "louis-zelie", "monica",
    "augustine", "thomas-aquinas", "john-the-baptist", "james-the-less",
]


def _tagline(c: Dict[str, Any]) -> str:
    imp = c.get("importance", "")
    first = imp.split(".")[0].strip()
    return (first[:110] + "…") if len(first) > 110 else first

# --------------------------------------------------------------------------- #
# Vocation-tailored traditions to add to daily life (by vocation + state).     #
# --------------------------------------------------------------------------- #
VOCATION_TRADITIONS: Dict[str, Dict[str, Any]] = {
    "marriage|discerning": {
        "label": "Preparing for marriage",
        "items": [
            {"title": "Pray for your future spouse", "body": "Offer a daily decade of the Rosary for the person God may be preparing for you."},
            {"title": "Grow in chaste self-mastery", "body": "Practise purity and self-gift now — the habits you build today will form a faithful marriage."},
            {"title": "Study self-giving love", "body": "Read 'Introduction to the Devout Life' or the Theology of the Body, and seek good marriage prep (Pre-Cana)."},
            {"title": "Entrust it to the Holy Family", "body": "Bring your discernment to Jesus, Mary and Joseph in adoration, asking clarity and peace."},
        ],
    },
    "marriage|living": {
        "label": "Growing a holier family",
        "items": [
            {"title": "Enthrone the home", "body": "Enthrone the Sacred Heart or an image of the Holy Family and consecrate your household to them."},
            {"title": "The family Rosary", "body": "Gather to pray a decade or the full Rosary together each night."},
            {"title": "Keep Sunday holy", "body": "Worship at Mass together, then share a family meal and true rest."},
            {"title": "Live the liturgical year at home", "body": "Mark Advent (wreath), feast days and seasons; bless your children each night."},
            {"title": "Frequent the sacraments", "body": "Go to Mass weekly and Confession regularly as a family."},
        ],
    },
    "religious life|discerning": {
        "label": "Preparing for religious life",
        "items": [
            {"title": "Pray the Liturgy of the Hours", "body": "Begin praying (part of) the Divine Office daily — the prayer of the Church and of religious."},
            {"title": "Make a 'Come and See' visit", "body": "Spend time with a community and find a spiritual director to walk with you."},
            {"title": "Practise the counsels in seed", "body": "Live small acts of poverty and obedience; simplify what you own."},
            {"title": "Daily Holy Hour & silence", "body": "Keep a time of Eucharistic adoration and interior silence each day."},
        ],
    },
    "religious life|living": {
        "label": "Deepening religious life",
        "items": [
            {"title": "Faithful to the Hours & lectio", "body": "Guard fidelity to the Divine Office and daily lectio divina."},
            {"title": "Examen & direction", "body": "Make the daily Examen and keep regular spiritual direction; renew your vows interiorly."},
            {"title": "Live your charism", "body": "Embrace community life and the hidden acts of service your charism asks."},
            {"title": "Adoration & Marian devotion", "body": "Anchor each day in adoration and the Rosary."},
        ],
    },
    "singleness|discerning": {
        "label": "Discerning in the single life",
        "items": [
            {"title": "Keep a discernment journal", "body": "Write what stirs your heart in prayer and review it with a spiritual director."},
            {"title": "A daily prayer rule", "body": "Anchor your day with Mass or adoration when possible, and a fixed time of prayer."},
            {"title": "Works of mercy", "body": "Let your freedom overflow in service to the poor, the lonely, and your parish."},
            {"title": "Live simply and chastely", "body": "Practise the evangelical counsels in spirit while God reveals your path."},
        ],
    },
    "singleness|living": {
        "label": "Holiness in the single life",
        "items": [
            {"title": "Consecrate your singleness", "body": "Offer your single life to God as a gift, with a steady daily prayer rule."},
            {"title": "Be generously available", "body": "Use your freedom to serve the Church, the poor, and those in need."},
            {"title": "Spiritual friendship", "body": "Build holy friendships and accountability; frequent the sacraments often."},
            {"title": "A rule of life", "body": "Balance prayer, work and rest so your days are ordered toward God."},
        ],
    },
}


# --------------------------------------------------------------------------- #
# Recommended devotionals — classic Catholic devotions to take up, tailored to #
# each companion saint. Rendered as a checklist of suggestions on the          #
# companion page.                                                              #
# --------------------------------------------------------------------------- #
SAINT_DEVOTIONS: Dict[str, List[Dict[str, str]]] = {
    "catherine-siena": [
        {"title": "The Holy Rosary", "body": "Pray a daily Rosary, meditating on Christ crucified whom Catherine loved above all."},
        {"title": "Eucharistic adoration", "body": "Visit the Blessed Sacrament — Catherine lived on the Eucharist."},
        {"title": "The Precious Blood of Jesus", "body": "Honor His Precious Blood: pray, 'Blood of Christ, inebriate me.'"},
        {"title": "Lectio on the 'Dialogue'", "body": "Read a short passage of her Dialogue prayerfully each day."},
    ],
    "pier-giorgio": [
        {"title": "Daily Mass & Communion", "body": "Make the Eucharist the fuel of your day, as Frassati did."},
        {"title": "The daily Rosary", "body": "Pray it faithfully — Frassati never missed it, even on the mountains."},
        {"title": "Eucharistic (nocturnal) adoration", "body": "Keep holy hours before the Blessed Sacrament."},
        {"title": "Works of mercy", "body": "Serve the poor quietly, as he did through the St. Vincent de Paul Society."},
    ],
    "john-paul-ii": [
        {"title": "Totus Tuus — Marian consecration", "body": "Consecrate yourself totally to Jesus through Mary (St. Louis de Montfort)."},
        {"title": "The Luminous Mysteries", "body": "Pray the Mysteries of Light he gave the Church."},
        {"title": "Divine Mercy Chaplet", "body": "Pray the Chaplet at 3pm; he gave us Divine Mercy Sunday."},
        {"title": "A daily Holy Hour", "body": "Keep a daily hour of adoration, the heartbeat of his priesthood."},
    ],
    "agnes": [
        {"title": "Renew your consecration of purity", "body": "Offer your heart to Christ your Spouse each morning."},
        {"title": "The Rosary (Joyful Mysteries)", "body": "Meditate on Christ's hidden life with childlike love."},
        {"title": "Litany of the virgin-martyrs", "body": "Ask the prayers of the holy virgins who kept the faith."},
        {"title": "Guardian Angel devotion", "body": "Entrust your purity to your angel each day."},
    ],
    "therese-lisieux": [
        {"title": "The Little Way", "body": "Do small things with great love; offer tiny sacrifices all day."},
        {"title": "Sacrifice beads", "body": "Count acts of love and self-denial on a set of sacrifice beads."},
        {"title": "Devotion to the Holy Face", "body": "Honor the Holy Face of Jesus, Thérèse's beloved devotion."},
        {"title": "Novena of the 'Shower of Roses'", "body": "Ask her intercession, trusting her promise of roses."},
    ],
    "benedict": [
        {"title": "Liturgy of the Hours", "body": "Pray part of the Divine Office at fixed times — ora et labora."},
        {"title": "The Medal & Cross of St. Benedict", "body": "Wear the Jubilee Medal for protection against evil."},
        {"title": "Lectio divina", "body": "Read Scripture slowly and prayerfully each day."},
        {"title": "Compline before sleep", "body": "End the day with Night Prayer and a brief examen."},
    ],
    "francis-assisi": [
        {"title": "The Franciscan Crown", "body": "Pray the seven-decade rosary of Our Lady's Joys."},
        {"title": "Stations of the Cross", "body": "Meditate on the Passion; Francis bore the stigmata for love of the Cross."},
        {"title": "The Peace Prayer", "body": "Pray daily, 'Lord, make me an instrument of Your peace.'"},
        {"title": "The Christmas crèche", "body": "Pray before a Nativity scene, a devotion Francis gave the Church."},
    ],
    "teresa-avila": [
        {"title": "Mental prayer", "body": "Spend 15 minutes daily simply being with the God who loves you."},
        {"title": "Read the 'Interior Castle'", "body": "Take a passage of her writings as a guide to deeper prayer."},
        {"title": "Devotion to St. Joseph", "body": "Entrust your needs to St. Joseph, Teresa's great patron."},
        {"title": "The Bookmark of St. Teresa", "body": "Pray, 'Let nothing disturb you… God alone suffices.'"},
    ],
    "st-joseph": [
        {"title": "Consecration to St. Joseph", "body": "Make and renew the 33-day consecration to the foster-father of Jesus."},
        {"title": "'To you, O blessed Joseph'", "body": "Pray this Leonine prayer daily for the Church and your family."},
        {"title": "Wednesday devotion & Seven Sorrows and Joys", "body": "Honor Joseph on Wednesdays; pray his Seven Sorrows and Joys."},
        {"title": "The Chaplet of St. Joseph", "body": "Pray the chaplet, entrusting your work and a holy death to him."},
    ],
    "louis-zelie": [
        {"title": "The family Rosary", "body": "Pray the Rosary together as a household each evening."},
        {"title": "Enthronement of the Sacred Heart", "body": "Consecrate your home to the Sacred Heart of Jesus."},
        {"title": "Sunday Mass & rest together", "body": "Keep the Lord's Day holy as a family."},
        {"title": "A morning offering as a couple", "body": "Offer the day, your work and children, to God each morning."},
    ],
    "gianna-molla": [
        {"title": "Morning offering of your work", "body": "Offer your profession and duties to God with a glad heart."},
        {"title": "Daily Mass when possible", "body": "Draw strength from the Eucharist as Gianna did."},
        {"title": "A daily decade for your family", "body": "Pray the Rosary for your spouse and children."},
        {"title": "Prayer for the unborn", "body": "Intercede for expectant mothers and the protection of life."},
    ],
    "monica": [
        {"title": "Persevering intercession", "body": "Keep praying daily for one soul's conversion, never giving up."},
        {"title": "The Rosary (Sorrowful Mysteries)", "body": "Unite your tears to Our Lady's for the one you love."},
        {"title": "Novena to St. Monica", "body": "Pray her novena for wayward loved ones."},
        {"title": "A Mass offered for them", "body": "Have Mass offered for the intention closest to your heart."},
    ],
    "guardian-angel": [
        {"title": "The 'Angel of God' prayer", "body": "Pray it morning and night to your guardian angel."},
        {"title": "Chaplet of the Guardian Angel", "body": "Pray the chaplet honoring the nine choirs of angels."},
        {"title": "The St. Michael Prayer", "body": "Ask St. Michael's protection against the enemy."},
        {"title": "Send your angel on errands", "body": "Ask your angel to carry prayers and help others, as Padre Pio taught."},
    ],
    "padre-pio": [
        {"title": "'Pray, hope, and don't worry'", "body": "Make his motto a daily act of trust in Providence."},
        {"title": "The Rosary — his 'weapon'", "body": "Pray it daily; Pio called the Rosary the weapon against evil."},
        {"title": "Frequent Confession", "body": "Go to Confession regularly, as Padre Pio urged all souls."},
        {"title": "Devotion to your Guardian Angel", "body": "Send your angel to those who need prayers."},
    ],
    "st-lucy": [
        {"title": "Pray for the light of faith", "body": "Ask St. Lucy (whose name means 'light') for clear vision of soul."},
        {"title": "The Rosary in Advent", "body": "Pray for Christ the Light around her December feast."},
        {"title": "Litany of the virgin-martyrs", "body": "Honor the holy martyrs who kept the faith unto death."},
        {"title": "Quiet almsgiving", "body": "Give secretly to the poor, as Lucy gave her dowry."},
    ],
    "st-faustina": [
        {"title": "The Chaplet of Divine Mercy", "body": "Pray the Chaplet daily, especially at the 3 o'clock hour."},
        {"title": "The Hour of Great Mercy (3pm)", "body": "Pause at 3pm to honor the hour of Jesus' death."},
        {"title": "The Divine Mercy Image", "body": "Keep the 'Jesus, I trust in You' image and pray before it."},
        {"title": "The Divine Mercy Novena", "body": "Pray the novena from Good Friday to Divine Mercy Sunday."},
    ],
    "blessed-virgin-mary": [
        {"title": "The Holy Rosary", "body": "Pray the daily Rosary, meditating on the life of Christ with Mary."},
        {"title": "Marian consecration (Totus Tuus)", "body": "Consecrate yourself to Jesus through Mary."},
        {"title": "The Angelus", "body": "Pray the Angelus at 6am, noon, and 6pm."},
        {"title": "The Brown Scapular or Miraculous Medal", "body": "Wear a Marian sacramental as a sign of her protection."},
    ],
    "sacred-heart": [
        {"title": "The Nine First Fridays", "body": "Receive Communion on the first Friday of nine consecutive months."},
        {"title": "Morning Offering", "body": "Offer your day to the Sacred Heart each morning."},
        {"title": "Enthronement of the Sacred Heart", "body": "Consecrate your home and family to His Heart."},
        {"title": "Holy Hour of reparation", "body": "Keep a Thursday or Friday holy hour of adoration."},
    ],
    "sts-peter-paul": [
        {"title": "Pray for the Pope", "body": "Offer a daily prayer for Peter's successor and the unity of the Church."},
        {"title": "Lectio on the Epistles", "body": "Read a passage of St. Paul's letters prayerfully."},
        {"title": "Profess the Creed", "body": "Say the Creed daily — the faith for which they gave their lives."},
        {"title": "Devotion to the Chair of St. Peter", "body": "Pray for fidelity to the Church's teaching."},
    ],
    "carlo-acutis": [
        {"title": "Eucharistic adoration", "body": "Visit Jesus in the Blessed Sacrament — Carlo's 'highway to Heaven.'"},
        {"title": "Frequent Communion & Confession", "body": "Receive the Eucharist often and confess regularly."},
        {"title": "The daily Rosary", "body": "Pray the Rosary each day, as Carlo did."},
        {"title": "Offer your screen time to God", "body": "Use technology for good; offer your online life to Christ."},
    ],
    "fulton-sheen": [
        {"title": "The daily Holy Hour", "body": "Keep a daily hour of Eucharistic adoration, as Sheen did for decades."},
        {"title": "The Rosary", "body": "Pray the daily Rosary; Sheen carried it everywhere."},
        {"title": "Frequent Confession", "body": "Confess regularly to keep the soul bright."},
        {"title": "Daily spiritual reading", "body": "Read a few pages of solid Catholic doctrine each day."},
    ],
    "augustine": [
        {"title": "Frequent Confession", "body": "Confess regularly, trusting the mercy that raised Augustine from sin."},
        {"title": "Lectio on the 'Confessions'", "body": "Read a short passage of his Confessions prayerfully."},
        {"title": "Daily interior prayer", "body": "Withdraw inward each day to the God who is nearer than your own heart."},
        {"title": "Novena to St. Augustine", "body": "Ask his intercession for a wandering soul or your own conversion."},
    ],
    "john-the-baptist": [
        {"title": "Daily examination & repentance", "body": "Prepare the way of the Lord by repenting of one sin each day."},
        {"title": "A spirit of penance", "body": "Take up a small fast or self-denial in John's desert spirit."},
        {"title": "The Benedictus (Canticle of Zechariah)", "body": "Pray the canticle sung at his birth, part of Morning Prayer."},
        {"title": "Novena to St. John the Baptist", "body": "Ask the forerunner for humility and courage."},
    ],
    "james-the-less": [
        {"title": "Read the Letter of St. James", "body": "Take a short passage daily and put one verse into practice."},
        {"title": "A daily work of mercy", "body": "Show your faith by works — visit, feed, clothe, or console someone."},
        {"title": "Persevering prayer", "body": "Spend extra time on your knees, like James 'the Just.'"},
        {"title": "Novena to St. James the Less", "body": "Ask the apostle for a living, active faith."},
    ],
    "thomas-aquinas": [
        {"title": "The prayer before study", "body": "Pray his 'Creator of all things' before work or study."},
        {"title": "Eucharistic adoration & 'Adoro te devote'", "body": "Adore the Blessed Sacrament with his own hymn."},
        {"title": "'Tantum Ergo' at Benediction", "body": "Sing or pray his hymn before the exposed Eucharist."},
        {"title": "Read an article of the Summa or Catechism", "body": "Study one point of the faith slowly and prayerfully."},
        {"title": "Novena to St. Thomas Aquinas", "body": "Ask the Angelic Doctor for wisdom, purity, and love of the Eucharist."},
    ],
}


# Recommended devotionals tailored to the user's vocation + state.
VOCATION_DEVOTIONS: Dict[str, Dict[str, Any]] = {
    "marriage|discerning": {
        "label": "Devotions for those preparing for marriage",
        "items": [
            {"title": "A daily decade for your future spouse", "body": "Offer one decade of the Rosary for the person God may be preparing for you."},
            {"title": "Novena to Sts. Louis & Zélie Martin", "body": "Ask the patrons of spouses to guide your discernment."},
            {"title": "Consecration to the Holy Family", "body": "Entrust your vocation to Jesus, Mary, and Joseph in adoration."},
            {"title": "Study self-giving love", "body": "Pray with the Theology of the Body or the 'Introduction to the Devout Life.'"},
        ],
    },
    "marriage|living": {
        "label": "Devotions for a holier marriage & family",
        "items": [
            {"title": "The family Rosary", "body": "Gather to pray a decade or the full Rosary together each night."},
            {"title": "Enthronement of the Sacred Heart", "body": "Consecrate your home to the Sacred Heart of Jesus."},
            {"title": "Regular Confession as a couple", "body": "Go to Confession together each month."},
            {"title": "Novena to St. Joseph", "body": "Ask the guardian of the Holy Family to protect your home."},
        ],
    },
    "religious life|discerning": {
        "label": "Devotions for those discerning religious life",
        "items": [
            {"title": "Liturgy of the Hours", "body": "Begin praying (part of) the Divine Office daily."},
            {"title": "A daily Holy Hour", "body": "Keep Eucharistic adoration and interior silence each day."},
            {"title": "Novena to the Holy Spirit for vocations", "body": "Ask for light to know God's call."},
            {"title": "Lectio divina", "body": "Pray slowly with the day's Scriptures."},
        ],
    },
    "religious life|living": {
        "label": "Devotions for deepening religious life",
        "items": [
            {"title": "Faithful Divine Office & lectio", "body": "Guard fidelity to the Hours and daily lectio divina."},
            {"title": "The daily Examen", "body": "Review your day with God and renew your vows interiorly."},
            {"title": "Marian consecration & Rosary", "body": "Anchor each day in the Rosary and total consecration."},
            {"title": "Eucharistic adoration", "body": "Keep a daily time before the Blessed Sacrament."},
        ],
    },
    "singleness|discerning": {
        "label": "Devotions for discerning the single life",
        "items": [
            {"title": "A fixed daily prayer rule", "body": "Anchor your day with Mass or adoration and a set time of prayer."},
            {"title": "Novena to the Holy Spirit", "body": "Pray for guidance to know your path."},
            {"title": "Eucharistic adoration", "body": "Bring your discernment to Jesus in the Blessed Sacrament."},
            {"title": "A discernment journal", "body": "Write what stirs your heart in prayer; review it with a director."},
        ],
    },
    "singleness|living": {
        "label": "Devotions for holiness in the single life",
        "items": [
            {"title": "Consecrate your singleness", "body": "Offer your single life to God with a steady daily prayer rule."},
            {"title": "The daily Rosary", "body": "Keep company with Our Lady each day."},
            {"title": "Works of mercy", "body": "Let your freedom overflow in service to the poor and your parish."},
            {"title": "Frequent the sacraments", "body": "Go to Mass and Confession often."},
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


def _devotion_route(title: str, novena_slug: Optional[str]) -> Optional[str]:
    """Map a devotional's title to an in-app prayer/novena route when one exists."""
    t = (title or "").lower()
    if "novena" in t:
        return f"/novenas/{novena_slug}" if novena_slug else "/novenas"
    if "rosary" in t:
        return "/prayer/rosary"
    if "chaplet" in t or "divine mercy" in t:
        return "/prayer/category/chaplets"
    if "consecrat" in t or "enthron" in t or "totus tuus" in t:
        return "/consecration"
    if "liturgy of the hours" in t or "divine office" in t:
        return "/liturgy"
    if "stations of the cross" in t:
        return "/prayer/category/stations"
    if "litany" in t or "litanies" in t:
        return "/prayer/category/litany"
    if "angelus" in t or "memorare" in t or "salve regina" in t or "magnificat" in t:
        return "/prayer/category/marian"
    if "st. michael" in t or "st michael" in t:
        return "/prayer/category/devotional"
    if "before mass" in t or "after mass" in t or "communion" in t:
        return "/prayer/category/mass"
    return None


def _with_routes(items: List[Dict[str, str]], novena_slug: Optional[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for it in items:
        d = dict(it)
        r = _devotion_route(it.get("title", ""), novena_slug)
        if r:
            d["route"] = r
        out.append(d)
    return out


def _public(slug: str, c: Dict[str, Any], vocation: str = "", state: str = "") -> Dict[str, Any]:
    voc_key = f"{vocation}|{state}"
    voc_trad = VOCATION_TRADITIONS.get(voc_key)
    linked_slug = c.get("linked")
    linked = None
    if linked_slug and linked_slug in COMPANIONS:
        linked = {"slug": linked_slug, "name": COMPANIONS[linked_slug]["name"]}
    return {
        "slug": slug,
        "name": c["name"],
        "feast": c.get("feast"),
        "importance": c["importance"],
        "daily_prayer": DAILY_PRAYERS.get(slug),
        "virtues": c["virtues"],
        "novena_slug": c.get("novena_slug"),
        "daily_act": _today_act(c["daily_acts"]),
        "church_traditions": CHURCH_TRADITIONS.get(slug, []),
        "daily_traditions": DAILY_TRADITIONS.get(slug, []),
        "vocation_traditions": voc_trad,
        "saint_devotions": _with_routes(SAINT_DEVOTIONS.get(slug, []), c.get("novena_slug")),
        "vocation_devotions": (
            {"label": VOCATION_DEVOTIONS[voc_key]["label"],
             "items": _with_routes(VOCATION_DEVOTIONS[voc_key]["items"], c.get("novena_slug"))}
            if voc_key in VOCATION_DEVOTIONS else None
        ),
        "has_consecration": True,  # the St. Joseph consecration is open to all companions
        "is_joseph": slug == "st-joseph",
        "note": c.get("note"),
        "do_not_name": bool(c.get("do_not_name", False)),
        "linked": linked,
    }


def build_router(db: AsyncIOMotorDatabase, get_current_user, emergent_llm_key: str = "") -> APIRouter:
    router = APIRouter(prefix="/companions", tags=["companions"])

    @router.get("")
    async def list_companions(user=Depends(get_current_user)):
        prefs = await db.preferences.find_one({"user_id": user.user_id}, {"_id": 0}) or {}
        selected = [s for s in (prefs.get("daily_companions") or []) if s != PERMANENT_COMPANION]
        vocation_companion = (prefs.get("companion_saint") or "").strip()
        items = []
        for slug in COMPANION_ORDER:
            c = COMPANIONS[slug]
            items.append({
                "slug": slug, "name": c["name"], "feast": c.get("feast"),
                "tagline": _tagline(c),
                "selected": slug in selected,
                "is_vocation_companion": slug == vocation_companion,
                "is_permanent": slug == PERMANENT_COMPANION,
                "linked": c.get("linked"),
            })
        return {"companions": items, "selected": selected, "max": 3,
                "vocation_companion": vocation_companion,
                "permanent": PERMANENT_COMPANION}

    @router.get("/daily-acts")
    async def daily_acts(user=Depends(get_current_user)):
        """Today's small act for each of the user's chosen daily companions
        (plus the permanent Guardian Angel), for the Home screen."""
        prefs = await db.preferences.find_one({"user_id": user.user_id}, {"_id": 0}) or {}
        selected = [s for s in (prefs.get("daily_companions") or []) if s != PERMANENT_COMPANION]
        order = [PERMANENT_COMPANION] + selected
        items = []
        for slug in order:
            c = COMPANIONS.get(slug)
            if not c:
                continue
            act = _today_act(c["daily_acts"])
            items.append({"slug": slug, "name": c["name"], "act": act["text"]})
        return {"items": items}

    @router.post("/select")
    async def select_companion(payload: Dict[str, Any], user=Depends(get_current_user)):
        slug = (payload.get("slug") or "").strip()
        action = (payload.get("action") or "toggle").strip()
        if slug not in COMPANIONS:
            raise HTTPException(status_code=404, detail="Companion not found")
        if slug == PERMANENT_COMPANION:
            raise HTTPException(status_code=400, detail="Your Guardian Angel is always with you and cannot be removed.")
        prefs = await db.preferences.find_one({"user_id": user.user_id}, {"_id": 0}) or {}
        selected: List[str] = [s for s in (prefs.get("daily_companions") or []) if s != PERMANENT_COMPANION]
        if action == "remove" or (action == "toggle" and slug in selected):
            selected = [s for s in selected if s != slug]
        else:
            if slug in selected:
                pass
            elif len(selected) >= 3:
                raise HTTPException(status_code=400, detail="You can choose up to 3 daily companions")
            else:
                selected.append(slug)
        await db.preferences.update_one(
            {"user_id": user.user_id},
            {"$set": {"user_id": user.user_id, "daily_companions": selected}},
            upsert=True,
        )
        return {"selected": selected, "max": 3}

    @router.get("/{slug}")
    async def get_companion(slug: str, user=Depends(get_current_user)):
        c = COMPANIONS.get(slug)
        if not c:
            raise HTTPException(status_code=404, detail="Companion not found")
        prefs = await db.preferences.find_one({"user_id": user.user_id}, {"_id": 0}) or {}
        vocation = (prefs.get("vocation") or "").strip().lower()
        state = (prefs.get("vocation_state") or "").strip().lower()
        # Warm the illustration in the background so the image endpoint is fast.
        asyncio.create_task(_get_or_make_image(db, slug, c["image_prompt"], emergent_llm_key))
        return _public(slug, c, vocation, state)

    @router.get("/{slug}/image")
    async def get_companion_image(slug: str, user=Depends(get_current_user)):
        c = COMPANIONS.get(slug)
        if not c:
            raise HTTPException(status_code=404, detail="Companion not found")
        data_url = await _get_or_make_image(db, slug, c["image_prompt"], emergent_llm_key)
        return {"image": data_url}

    return router

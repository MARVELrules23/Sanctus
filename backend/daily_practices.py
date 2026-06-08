"""
Daily Practice Recommendations.

A large pool (~120) of small daily disciplines, charitable acts, devotional
practices, and acts of mortification. Each user is assigned one practice per
day, and we record the assignment so refreshing won't change it. Selection
avoids the user's most recent 90 days of practices, so the same practice
should almost never appear twice to the same person.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

logger = logging.getLogger("sanctus.daily_practice")


# ---------------------------------------------------------------------------
# Pool
# ---------------------------------------------------------------------------
# Each practice has a stable id (used for history lookup) so renames/edits
# don't break the user's "already-seen" set. Keep ids short and snake_case.

Practice = Dict[str, Any]


PRACTICES: List[Practice] = [
    # ------------------------------- MORTIFICATION ----------------------------
    {
        "id": "cold_shower",
        "category": "Mortification",
        "title": "Take a cold shower",
        "body": "Sixty seconds at the end of your shower, full cold. Offer it for someone who is suffering today.",
        "why": "Small voluntary mortifications keep the body in service to the soul.",
        "virtue": "Temperance",
        "intensity": "moderate",
    },
    {
        "id": "skip_one_meal",
        "category": "Mortification",
        "title": "Skip one meal",
        "body": "Skip a meal today (unless health forbids) and unite the hunger pang to Christ's hunger in the desert.",
        "why": "Fasting orders the appetites and quiets the noise of the body.",
        "virtue": "Temperance",
        "intensity": "moderate",
    },
    {
        "id": "no_sugar_today",
        "category": "Mortification",
        "title": "No sweets or added sugar today",
        "body": "From sunrise to bedtime, no desserts, sodas, syrups, or candy. Drink water and offer the craving.",
        "why": "The smallest 'no' to self trains a stronger 'yes' to God.",
        "virtue": "Temperance",
        "intensity": "easy",
    },
    {
        "id": "no_complaints",
        "category": "Mortification",
        "title": "Go a full day without complaining",
        "body": "Notice every complaint before it leaves the mouth. Swap it for a brief silent thanksgiving.",
        "why": "The tongue is a small rudder steering the soul.",
        "virtue": "Patience",
        "intensity": "moderate",
    },
    {
        "id": "no_phone_after_dinner",
        "category": "Mortification",
        "title": "No phone after dinner",
        "body": "Plug it in face-down across the room. Read, talk, pray, or sit in silence until bed.",
        "why": "Reclaim the dusk for those you love — and for the Lord.",
        "virtue": "Detachment",
        "intensity": "easy",
    },
    {
        "id": "stairs_only",
        "category": "Mortification",
        "title": "Take the stairs every time today",
        "body": "Skip elevators and escalators all day. Offer each climb for someone whose path is steep right now.",
        "why": "The body offered in small things is the body offered.",
        "virtue": "Diligence",
        "intensity": "easy",
    },
    {
        "id": "no_music_commute",
        "category": "Mortification",
        "title": "Drive in silence today",
        "body": "No music, no podcasts, no calls in the car. Let the quiet do its work.",
        "why": "Silence is where the Lord whispers.",
        "virtue": "Recollection",
        "intensity": "easy",
    },
    {
        "id": "kneel_when_hard",
        "category": "Mortification",
        "title": "Kneel during your evening prayer",
        "body": "Even if just for five minutes. The knees teach the heart what the lips alone cannot.",
        "why": "Posture forms the soul as much as the soul forms posture.",
        "virtue": "Humility",
        "intensity": "easy",
    },
    {
        "id": "no_seconds",
        "category": "Mortification",
        "title": "Take no second helpings today",
        "body": "Eat your portion. Stop. Even if there is room. Even if it is good.",
        "why": "A small leash on the appetite trains a great freedom.",
        "virtue": "Temperance",
        "intensity": "easy",
    },
    {
        "id": "cold_morning_walk",
        "category": "Mortification",
        "title": "Walk outside in the morning cold",
        "body": "Ten minutes outdoors in the chill before doing anything else. No coat heroics — just step into the day.",
        "why": "A body awake to weather is a body awake to grace.",
        "virtue": "Fortitude",
        "intensity": "easy",
    },
    {
        "id": "no_screens_morning",
        "category": "Mortification",
        "title": "No screens for the first hour you're awake",
        "body": "No phone, no laptop, no TV until 60 minutes after rising. Pray, eat, move, breathe.",
        "why": "The first hour shapes the whole day.",
        "virtue": "Detachment",
        "intensity": "moderate",
    },
    {
        "id": "skip_dessert",
        "category": "Mortification",
        "title": "Skip dessert tonight",
        "body": "If it's offered, refuse with a smile. Offer it quietly for a soul in purgatory.",
        "why": "Even forgotten souls feel the touch of a small renunciation.",
        "virtue": "Temperance",
        "intensity": "easy",
    },
    {
        "id": "sleep_no_pillow",
        "category": "Mortification",
        "title": "Sleep without a pillow tonight",
        "body": "One night. Don't make a show of it. Let the discomfort be your prayer.",
        "why": "Christ had nowhere to lay his head.",
        "virtue": "Humility",
        "intensity": "moderate",
    },
    {
        "id": "no_alcohol_today",
        "category": "Mortification",
        "title": "No alcohol today",
        "body": "Skip the beer, the wine, the cocktail. Drink water with gratitude.",
        "why": "Even moderate goods become great when offered as gifts back.",
        "virtue": "Temperance",
        "intensity": "easy",
    },
    {
        "id": "fast_until_noon",
        "category": "Mortification",
        "title": "Fast until noon",
        "body": "Black coffee or water only until midday. Eat at noon as if it were the Mass: deliberately, gratefully.",
        "why": "Hunger reminds the body who it serves.",
        "virtue": "Temperance",
        "intensity": "moderate",
    },
    # ----------------------------------- CHARITY ------------------------------
    {
        "id": "call_a_parent",
        "category": "Charity",
        "title": "Call a parent or grandparent",
        "body": "Pick up the phone today — no text. Ask one real question and listen longer than you speak.",
        "why": "Honor your father and your mother is the only commandment with a promise.",
        "virtue": "Piety",
        "intensity": "easy",
    },
    {
        "id": "write_thankyou",
        "category": "Charity",
        "title": "Write a thank-you note",
        "body": "On paper. To someone who shaped you. Mail it or leave it. Don't ask for a reply.",
        "why": "Gratitude expressed becomes gratitude doubled.",
        "virtue": "Gratitude",
        "intensity": "easy",
    },
    {
        "id": "offer_time_in_need",
        "category": "Charity",
        "title": "Offer your time to someone in need",
        "body": "An hour. Maybe two. To a friend in trouble, a neighbor who's alone, a relative who's struggling. Show up.",
        "why": "Love is time given away.",
        "virtue": "Charity",
        "intensity": "moderate",
    },
    {
        "id": "pay_for_stranger_coffee",
        "category": "Charity",
        "title": "Pay for a stranger's coffee",
        "body": "Or a meal, or anything small. No note, no name. Just a quiet gift.",
        "why": "Let not your left hand know what your right hand does.",
        "virtue": "Generosity",
        "intensity": "easy",
    },
    {
        "id": "give_anonymous_donation",
        "category": "Charity",
        "title": "Give an anonymous donation",
        "body": "To a parish poor box, a shelter, a pro-life ministry. Whatever moves you. Tell no one.",
        "why": "Almsgiving in secret has a Father who sees in secret.",
        "virtue": "Mercy",
        "intensity": "easy",
    },
    {
        "id": "compliment_three_people",
        "category": "Charity",
        "title": "Sincerely compliment three people",
        "body": "Not flattery. Specific, true things. Watch how they straighten as you speak.",
        "why": "Words are seeds — sow good ones.",
        "virtue": "Kindness",
        "intensity": "easy",
    },
    {
        "id": "visit_someone_sick",
        "category": "Charity",
        "title": "Visit someone sick or homebound",
        "body": "Even briefly. Even if they're family. Bring nothing but yourself.",
        "why": "I was sick, and you visited me.",
        "virtue": "Charity",
        "intensity": "moderate",
    },
    {
        "id": "pray_for_enemy",
        "category": "Charity",
        "title": "Pray for someone who has wronged you",
        "body": "By name. For their good — not their conversion to your view. Repeat through the day if needed.",
        "why": "Love your enemies and pray for those who persecute you.",
        "virtue": "Charity",
        "intensity": "moderate",
    },
    {
        "id": "forgive_one_thing",
        "category": "Charity",
        "title": "Forgive one held grudge today",
        "body": "Not feel it — choose it. You can do it without their knowledge. The grudge is yours to lay down.",
        "why": "Forgive us our trespasses as we forgive…",
        "virtue": "Mercy",
        "intensity": "hard",
    },
    {
        "id": "tip_extravagantly",
        "category": "Charity",
        "title": "Tip extravagantly today",
        "body": "Round up. Then round up again. Service workers will not forget the day.",
        "why": "Give and it will be given to you, pressed down, shaken together, running over.",
        "virtue": "Generosity",
        "intensity": "easy",
    },
    {
        "id": "give_away_one_thing",
        "category": "Charity",
        "title": "Give away one thing you love",
        "body": "Not a thing you've outgrown. A thing you still enjoy. Today. To someone who would treasure it.",
        "why": "Whoever has two coats should share with whoever has none.",
        "virtue": "Detachment",
        "intensity": "moderate",
    },
    {
        "id": "let_someone_go_first",
        "category": "Charity",
        "title": "Let everyone go first today",
        "body": "In traffic, in line, in conversation. Practice yielding all day. Small deaths to ego.",
        "why": "The first shall be last and the last shall be first.",
        "virtue": "Humility",
        "intensity": "easy",
    },
    {
        "id": "speak_well_of_absent",
        "category": "Charity",
        "title": "Speak well of someone who isn't there",
        "body": "Today, in every conversation. If you cannot speak well, stay silent.",
        "why": "The tongue can either build or burn.",
        "virtue": "Charity",
        "intensity": "moderate",
    },
    {
        "id": "buy_groceries_for_neighbor",
        "category": "Charity",
        "title": "Buy groceries for a neighbor or friend in need",
        "body": "Drop them at the door. A note, no name. Or stop and stay for coffee. Either way — provide.",
        "why": "Bear one another's burdens.",
        "virtue": "Charity",
        "intensity": "moderate",
    },
    {
        "id": "say_sorry_first",
        "category": "Charity",
        "title": "Say sorry first",
        "body": "To whoever you're at odds with. Don't wait for them. Don't explain — apologize.",
        "why": "Be reconciled to your brother, then come and offer your gift.",
        "virtue": "Humility",
        "intensity": "hard",
    },
    {
        "id": "drive_with_patience",
        "category": "Charity",
        "title": "Drive with patience all day",
        "body": "No honking, no muttering, no tailgating. Let in every merger. Wave thanks.",
        "why": "Bear with one another in love.",
        "virtue": "Patience",
        "intensity": "moderate",
    },
    # ------------------------------------ PRAYER ------------------------------
    {
        "id": "rosary_for_souls",
        "category": "Prayer",
        "title": "Pray a full Rosary for the souls in purgatory",
        "body": "Five decades. You can split it through the day. Offer all of it for those who have no one to pray for them.",
        "why": "Mercy spills both ways — it returns to the merciful.",
        "virtue": "Charity",
        "intensity": "moderate",
    },
    {
        "id": "chaplet_divine_mercy",
        "category": "Prayer",
        "title": "Pray the Chaplet of Divine Mercy",
        "body": "Three o'clock if you can — the hour of mercy. Offer for someone you know who is far from God.",
        "why": "Mercy at the hour of mercy.",
        "virtue": "Mercy",
        "intensity": "easy",
    },
    {
        "id": "examen_evening",
        "category": "Prayer",
        "title": "Make an Examen of conscience before bed",
        "body": "Five Ignatian steps: gratitude, request light, review the day, repent, resolve. Ten minutes.",
        "why": "The unexamined day is half-lived.",
        "virtue": "Prudence",
        "intensity": "easy",
    },
    {
        "id": "lectio_divina",
        "category": "Prayer",
        "title": "Pray Lectio Divina on today's Gospel",
        "body": "Read · meditate · pray · contemplate. Twenty minutes. Let one word arrest you and stay with it.",
        "why": "Scripture is the Word made readable.",
        "virtue": "Studiousness",
        "intensity": "moderate",
    },
    {
        "id": "angelus_thrice",
        "category": "Prayer",
        "title": "Pray the Angelus at 6am, noon, and 6pm",
        "body": "Set three alarms. Whatever you're doing, pause and pray. Even a whispered version counts.",
        "why": "The Word became flesh. Remember this three times a day.",
        "virtue": "Devotion",
        "intensity": "easy",
    },
    {
        "id": "memorize_one_psalm_verse",
        "category": "Prayer",
        "title": "Memorize one verse of a Psalm today",
        "body": "Just one. Carry it like a coin in your pocket. Speak it over the day's troubles.",
        "why": "The mind that knows the Word by heart prays it without thinking.",
        "virtue": "Studiousness",
        "intensity": "easy",
    },
    {
        "id": "pray_for_priest",
        "category": "Prayer",
        "title": "Pray for one priest by name",
        "body": "Your parish priest, your confessor, a bishop, the Pope. By name. For perseverance.",
        "why": "A priest carries more than he can carry — pray him up.",
        "virtue": "Piety",
        "intensity": "easy",
    },
    {
        "id": "pray_for_marriage",
        "category": "Prayer",
        "title": "Pray for one struggling marriage you know",
        "body": "By name if you know it. For healing, mercy, fidelity, and the protection of the children.",
        "why": "Marriages are battlefields. Pray for the people in the trenches.",
        "virtue": "Charity",
        "intensity": "easy",
    },
    {
        "id": "litany_humility",
        "category": "Prayer",
        "title": "Pray the Litany of Humility",
        "body": "Slowly. Mean every petition. If one stings, that's the one to repeat.",
        "why": "Humility is the foundation of every virtue.",
        "virtue": "Humility",
        "intensity": "moderate",
    },
    {
        "id": "guardian_angel_morning",
        "category": "Prayer",
        "title": "Pray to your guardian angel first thing",
        "body": "Before getting out of bed. Ask for protection, guidance, and good company today.",
        "why": "You are not alone.",
        "virtue": "Trust",
        "intensity": "easy",
    },
    {
        "id": "rosary_walk",
        "category": "Prayer",
        "title": "Pray a Rosary while walking outside",
        "body": "Twenty minutes of fresh air and twenty decades of meditation on the life of Christ.",
        "why": "The body in motion makes the mind willing.",
        "virtue": "Devotion",
        "intensity": "easy",
    },
    {
        "id": "offer_first_15_minutes",
        "category": "Prayer",
        "title": "Offer the first 15 minutes of your day to God",
        "body": "No scrolling. No coffee. Just silence and a few prayers. Then begin the day.",
        "why": "Tithe your morning.",
        "virtue": "Recollection",
        "intensity": "moderate",
    },
    {
        "id": "intercession_seven",
        "category": "Prayer",
        "title": "Intercede for seven people by name today",
        "body": "List them this morning. Pray for each at a meal, in the car, in line, at night.",
        "why": "Names lifted to God do not return empty.",
        "virtue": "Charity",
        "intensity": "easy",
    },
    {
        "id": "memento_mori",
        "category": "Prayer",
        "title": "Pray a Memento Mori reflection",
        "body": "Ten minutes considering: if today were your last, would you be ready? What needs setting right?",
        "why": "Remember death; you will not waste the hour.",
        "virtue": "Wisdom",
        "intensity": "moderate",
    },
    # --------------------------- SILENCE / DETACHMENT -------------------------
    {
        "id": "one_hour_silence",
        "category": "Silence",
        "title": "Spend one hour in deliberate silence",
        "body": "No noise, no input. Sit with the discomfort if it comes. Don't fill the space.",
        "why": "Silence is the language God speaks loudest in.",
        "virtue": "Recollection",
        "intensity": "moderate",
    },
    {
        "id": "no_social_media_today",
        "category": "Silence",
        "title": "No social media for a full day",
        "body": "Uninstall an app or block it. Notice how often the thumb reaches for it. Pray each time.",
        "why": "Every glance you skip is an act of will.",
        "virtue": "Detachment",
        "intensity": "moderate",
    },
    {
        "id": "leave_phone_at_door",
        "category": "Silence",
        "title": "Leave your phone at the door when you come home",
        "body": "In a basket, drawer, or on a shelf. Be home when you are home.",
        "why": "Presence is a gift you can give.",
        "virtue": "Attentiveness",
        "intensity": "easy",
    },
    {
        "id": "eat_one_meal_alone_no_screen",
        "category": "Silence",
        "title": "Eat one meal alone, without a screen",
        "body": "No phone, no TV, no laptop. Taste the food. Give thanks before and after.",
        "why": "Eating is a small Eucharist of creation.",
        "virtue": "Recollection",
        "intensity": "easy",
    },
    {
        "id": "no_radio_today",
        "category": "Silence",
        "title": "No radio, podcasts, or audiobooks today",
        "body": "Let your ears rest. Let your mind wander. Notice the thoughts you usually drown out.",
        "why": "Constant input is a quiet form of distraction.",
        "virtue": "Detachment",
        "intensity": "moderate",
    },
    {
        "id": "ten_minutes_in_church",
        "category": "Silence",
        "title": "Sit in a church for ten silent minutes",
        "body": "Don't read, don't pray with words. Just look at the tabernacle. Let Him look back.",
        "why": "He is really there.",
        "virtue": "Adoration",
        "intensity": "easy",
    },
    {
        "id": "delete_one_app",
        "category": "Silence",
        "title": "Delete one app you waste time on",
        "body": "Today. Without ceremony. You can reinstall in a week if you must. You probably won't.",
        "why": "Cut what does not bear fruit.",
        "virtue": "Detachment",
        "intensity": "moderate",
    },
    {
        "id": "phone_in_drawer_3_hours",
        "category": "Silence",
        "title": "Put your phone in a drawer for three hours",
        "body": "Choose a block of the day — morning, afternoon, evening. Out of sight, out of reach.",
        "why": "Your attention is the most valuable thing you own.",
        "virtue": "Detachment",
        "intensity": "easy",
    },
    {
        "id": "no_news_today",
        "category": "Silence",
        "title": "No news consumption today",
        "body": "Skip the headlines, the feeds, the alerts. Pray instead for those in the headlines.",
        "why": "The world will not collapse without your attention.",
        "virtue": "Tranquility",
        "intensity": "easy",
    },
    # --------------------------- WORK / STEWARDSHIP --------------------------
    {
        "id": "clean_one_drawer",
        "category": "Work",
        "title": "Clean one drawer today",
        "body": "Just one. Sort, throw, donate. Don't move to a second. Make the one drawer beautiful.",
        "why": "Order outside is a small order inside.",
        "virtue": "Diligence",
        "intensity": "easy",
    },
    {
        "id": "fix_one_thing",
        "category": "Work",
        "title": "Fix one broken thing in your home",
        "body": "A loose hinge, a dripping faucet, a frayed wire. Tend to it today. Not next week.",
        "why": "Stewardship begins with the small.",
        "virtue": "Diligence",
        "intensity": "moderate",
    },
    {
        "id": "make_bed_perfectly",
        "category": "Work",
        "title": "Make your bed with care today",
        "body": "Hospital corners or not — but neat, intentional, slow. Begin the day with one finished task.",
        "why": "Order begets order.",
        "virtue": "Diligence",
        "intensity": "easy",
    },
    {
        "id": "write_one_goal",
        "category": "Work",
        "title": "Write one goal for the coming month",
        "body": "On paper. Specific. Measurable. Begin one small action toward it today.",
        "why": "Without vision the people perish.",
        "virtue": "Prudence",
        "intensity": "easy",
    },
    {
        "id": "inbox_zero",
        "category": "Work",
        "title": "Reach inbox zero today",
        "body": "Reply, archive, or delete every email by sunset. Then leave it alone.",
        "why": "Unfinished business weighs more than you think.",
        "virtue": "Diligence",
        "intensity": "moderate",
    },
    {
        "id": "budget_review",
        "category": "Work",
        "title": "Review one month of spending",
        "body": "Sit with it for twenty minutes. Notice patterns. Adjust one thing.",
        "why": "Where your treasure is, there your heart is also.",
        "virtue": "Prudence",
        "intensity": "moderate",
    },
    {
        "id": "donate_5_items",
        "category": "Work",
        "title": "Pull five items to donate",
        "body": "Clothes, books, kitchen things. Today. Not 'someday.' Bag them and take them to the door.",
        "why": "Travel light through this life.",
        "virtue": "Detachment",
        "intensity": "easy",
    },
    {
        "id": "deep_work_two_hours",
        "category": "Work",
        "title": "Two hours of deep work, no interruptions",
        "body": "Phone in another room. One task. Two hours. The phone can wait. The work cannot.",
        "why": "Work done well is a prayer of its own.",
        "virtue": "Diligence",
        "intensity": "moderate",
    },
    {
        "id": "sharpen_skill_30",
        "category": "Work",
        "title": "Practice one skill for 30 deliberate minutes",
        "body": "Music, language, craft, writing, code. The kind of practice that's a little uncomfortable.",
        "why": "Stewardship of the talents you've been given.",
        "virtue": "Diligence",
        "intensity": "moderate",
    },
    # --------------------------- FAMILY / COMMUNITY ---------------------------
    {
        "id": "family_dinner_no_phones",
        "category": "Family",
        "title": "Eat dinner with family — no phones at the table",
        "body": "A basket at the door. Conversation. Eye contact. End with grace if you can.",
        "why": "The table is the first altar of the home.",
        "virtue": "Piety",
        "intensity": "easy",
    },
    {
        "id": "play_with_kids_30",
        "category": "Family",
        "title": "Give thirty minutes of undivided play",
        "body": "To your kids, niece, nephew, godchild. Their game, their rules. No phone. No clock.",
        "why": "Of such is the kingdom.",
        "virtue": "Charity",
        "intensity": "easy",
    },
    {
        "id": "ask_spouse_one_question",
        "category": "Family",
        "title": "Ask your spouse one deep question today",
        "body": "Not 'how was your day.' Something like 'what are you afraid of right now?' or 'where do you see God lately?'",
        "why": "Marriage feeds on questions, not assumptions.",
        "virtue": "Charity",
        "intensity": "easy",
    },
    {
        "id": "no_argument_today",
        "category": "Family",
        "title": "Go a full day without arguing with family",
        "body": "Walk away if needed. Yield. Listen. You can resume disagreements tomorrow if they still matter.",
        "why": "Peace is the air the home breathes.",
        "virtue": "Peace",
        "intensity": "hard",
    },
    {
        "id": "say_i_love_you",
        "category": "Family",
        "title": "Tell three people you love them today",
        "body": "Out loud. Even if it feels redundant. Especially if it feels redundant.",
        "why": "The unsaid 'I love you' is the one we regret.",
        "virtue": "Charity",
        "intensity": "easy",
    },
    {
        "id": "reach_out_to_old_friend",
        "category": "Family",
        "title": "Reach out to a friend you've drifted from",
        "body": "A call, a long message, a letter. Not 'we should catch up' — a real attempt to be present again.",
        "why": "Friendship is the sacrament of fidelity.",
        "virtue": "Loyalty",
        "intensity": "moderate",
    },
    {
        "id": "praise_a_child",
        "category": "Family",
        "title": "Praise a child for who they ARE, not what they do",
        "body": "Not 'great job.' Something like 'I love your kindness' or 'you are patient.' Let the praise stick to the soul, not the act.",
        "why": "Identity is shaped by what we hear about ourselves.",
        "virtue": "Charity",
        "intensity": "easy",
    },
    {
        "id": "neighbor_introduce",
        "category": "Family",
        "title": "Greet a neighbor by name today",
        "body": "If you don't know their name yet, learn it. Even just a wave with eye contact counts as a start.",
        "why": "The neighbor is the first mission field.",
        "virtue": "Charity",
        "intensity": "easy",
    },
    {
        "id": "thank_a_mentor",
        "category": "Family",
        "title": "Thank a mentor or teacher from your past",
        "body": "Find them. Email, letter, call. Tell them specifically what they gave you. Don't ask for anything.",
        "why": "We stand on shoulders. Acknowledge them.",
        "virtue": "Gratitude",
        "intensity": "moderate",
    },
    {
        "id": "share_a_meal_with_someone_alone",
        "category": "Family",
        "title": "Invite someone who is alone to a meal",
        "body": "Co-worker, neighbor, parishioner. Doesn't have to be elaborate. Just a place at your table.",
        "why": "Loneliness is the modern poverty.",
        "virtue": "Hospitality",
        "intensity": "moderate",
    },
    # ------------------------- SACRAMENT / DEVOTION --------------------------
    {
        "id": "go_to_confession",
        "category": "Sacrament",
        "title": "Go to Confession this week",
        "body": "Check your parish times. Prepare an examination of conscience tonight. Go.",
        "why": "The peace of absolution cannot be substituted.",
        "virtue": "Humility",
        "intensity": "moderate",
    },
    {
        "id": "weekday_mass",
        "category": "Sacrament",
        "title": "Attend a weekday Mass",
        "body": "Even a 7am one before work. Even a noon one squeezed into lunch. He will meet you there.",
        "why": "The Mass is the source and summit of every grace.",
        "virtue": "Devotion",
        "intensity": "moderate",
    },
    {
        "id": "adoration_30",
        "category": "Sacrament",
        "title": "Spend 30 minutes in Eucharistic Adoration",
        "body": "Find a chapel. Sit. Don't bring an agenda. Bring yourself.",
        "why": "Behold the Lamb of God.",
        "virtue": "Adoration",
        "intensity": "moderate",
    },
    {
        "id": "spiritual_communion",
        "category": "Sacrament",
        "title": "Make a Spiritual Communion at noon",
        "body": "\"My Jesus, I believe You are truly present…\" Wherever you are, however the day is going. Pause.",
        "why": "A heart that desires the sacrament is already drawing close.",
        "virtue": "Devotion",
        "intensity": "easy",
    },
    {
        "id": "read_saint_today",
        "category": "Sacrament",
        "title": "Read about today's saint",
        "body": "Find them in Universalis or a Lives of the Saints. Read for ten minutes. Take one quote.",
        "why": "The saints are our friends — make them so in fact.",
        "virtue": "Studiousness",
        "intensity": "easy",
    },
    {
        "id": "scripture_30_minutes",
        "category": "Sacrament",
        "title": "Read 30 minutes of Sacred Scripture",
        "body": "A Gospel chapter. A psalm. An epistle. Read slowly. Stop when something strikes you.",
        "why": "Ignorance of Scripture is ignorance of Christ. — St. Jerome",
        "virtue": "Studiousness",
        "intensity": "moderate",
    },
    {
        "id": "carry_a_relic",
        "category": "Sacrament",
        "title": "Carry a sacramental today",
        "body": "Rosary in your pocket, scapular on your neck, medal in your wallet. Touch it through the day. Remember.",
        "why": "Matter is the first vocabulary of God.",
        "virtue": "Devotion",
        "intensity": "easy",
    },
    {
        "id": "morning_offering",
        "category": "Sacrament",
        "title": "Make a Morning Offering before you rise",
        "body": "\"O Jesus, through the Immaculate Heart of Mary…\" Give the day before the day claims you.",
        "why": "What is offered first cannot be stolen later.",
        "virtue": "Devotion",
        "intensity": "easy",
    },
    {
        "id": "stations_of_cross",
        "category": "Sacrament",
        "title": "Pray the Stations of the Cross",
        "body": "At home, in a church, or on a walk. Linger on whichever station meets your day.",
        "why": "He walked them so you would not be alone in yours.",
        "virtue": "Devotion",
        "intensity": "moderate",
    },
    {
        "id": "novena_start",
        "category": "Sacrament",
        "title": "Begin a 9-day novena today",
        "body": "Choose a saint or intention. Set a reminder. Start now and let the calendar carry you.",
        "why": "Persistent prayer wears down even Heaven's threshold.",
        "virtue": "Perseverance",
        "intensity": "easy",
    },
]


# ---------------------------------------------------------------------------
# Selection logic
# ---------------------------------------------------------------------------

def _hash_seed(user_id: str, date_str: str) -> int:
    h = hashlib.sha256(f"{user_id}|{date_str}".encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big")


async def select_or_assign_practice(
    db: AsyncIOMotorDatabase,
    user_id: str,
    date_str: str,
    recent_window_days: int = 90,
) -> Practice:
    """Return today's practice for the user. Idempotent — repeated calls
    on the same date return the same practice. Excludes practices the
    user has been shown in the last `recent_window_days`."""

    # 1. If an assignment exists for this date, return it.
    existing = await db.daily_practices.find_one(
        {"user_id": user_id, "date": date_str}
    )
    if existing:
        practice_id = existing.get("practice_id")
        practice = next((p for p in PRACTICES if p["id"] == practice_id), None)
        if practice:
            return {**practice, "_assignment": _strip(existing)}
        # else: practice id was retired — fall through and re-assign

    # 2. Build exclusion set from recent history
    cursor = db.daily_practices.find(
        {"user_id": user_id},
        {"practice_id": 1, "date": 1, "_id": 0},
    ).sort("date", -1).limit(recent_window_days)
    recent_rows = await cursor.to_list(length=recent_window_days)
    recent_ids = {r["practice_id"] for r in recent_rows}

    # 3. Candidates: pool minus recent. If pool is smaller than the window,
    #    fall back to just excluding the most recent half.
    candidates = [p for p in PRACTICES if p["id"] not in recent_ids]
    if not candidates:
        # Pool exhausted — exclude only the most recent half
        half = max(1, len(PRACTICES) // 2)
        very_recent = {r["practice_id"] for r in recent_rows[:half]}
        candidates = [p for p in PRACTICES if p["id"] not in very_recent] or list(PRACTICES)

    # 4. Deterministic pick from candidates based on (user_id, date) hash
    seed = _hash_seed(user_id, date_str)
    pick = candidates[seed % len(candidates)]

    # 5. Persist assignment
    assignment = {
        "user_id": user_id,
        "date": date_str,
        "practice_id": pick["id"],
        "assigned_at": datetime.now(timezone.utc),
        "completed_at": None,
        "note": None,
    }
    try:
        await db.daily_practices.insert_one(assignment)
    except Exception as e:
        # Race: another request just inserted the same (user, date).
        logger.info("daily_practice insert race: %s", e)
        existing = await db.daily_practices.find_one(
            {"user_id": user_id, "date": date_str}
        )
        if existing:
            pid = existing.get("practice_id")
            practice = next((p for p in PRACTICES if p["id"] == pid), pick)
            return {**practice, "_assignment": _strip(existing)}

    return {**pick, "_assignment": _strip(assignment)}


def _strip(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in doc.items() if k != "_id"}
    for k in ("assigned_at", "completed_at"):
        v = out.get(k)
        if isinstance(v, datetime):
            out[k] = v.isoformat()
    return out


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class CompleteRequest(BaseModel):
    date: str
    note: Optional[str] = None


def build_router(db: AsyncIOMotorDatabase, get_user) -> APIRouter:
    """Factory so we can share the existing get_current_user dependency."""
    router = APIRouter(prefix="/daily-practice", tags=["daily-practice"])

    @router.get("")
    async def get_today(date: str, user=Depends(get_user)):
        practice = await select_or_assign_practice(db, user.user_id, date)
        return _shape(practice)

    @router.post("/complete")
    async def complete(payload: CompleteRequest, user=Depends(get_user)):
        # ensure assignment exists
        practice = await select_or_assign_practice(db, user.user_id, payload.date)
        await db.daily_practices.update_one(
            {"user_id": user.user_id, "date": payload.date},
            {"$set": {
                "completed_at": datetime.now(timezone.utc),
                "note": (payload.note or "").strip() or None,
            }},
        )
        refreshed = await db.daily_practices.find_one(
            {"user_id": user.user_id, "date": payload.date}
        )
        return _shape({**practice, "_assignment": _strip(refreshed or {})})

    @router.delete("/complete")
    async def uncomplete(date: str, user=Depends(get_user)):
        await db.daily_practices.update_one(
            {"user_id": user.user_id, "date": date},
            {"$set": {"completed_at": None, "note": None}},
        )
        practice = await select_or_assign_practice(db, user.user_id, date)
        return _shape(practice)

    @router.get("/history")
    async def history(limit: int = 30, user=Depends(get_user)):
        if limit < 1 or limit > 365:
            raise HTTPException(status_code=400, detail="limit must be 1..365")
        cursor = db.daily_practices.find(
            {"user_id": user.user_id},
            {"_id": 0},
        ).sort("date", -1).limit(limit)
        rows = await cursor.to_list(length=limit)
        # decorate with practice text
        items = []
        for r in rows:
            p = next((p for p in PRACTICES if p["id"] == r.get("practice_id")), None)
            if not p:
                continue
            items.append({
                **_shape({**p, "_assignment": _strip(r)})
            })
        return {"items": items, "total_pool": len(PRACTICES)}

    return router


def _shape(practice: Practice) -> Dict[str, Any]:
    """Map internal practice dict → API response."""
    a = practice.get("_assignment") or {}
    return {
        "id": practice["id"],
        "category": practice["category"],
        "title": practice["title"],
        "body": practice["body"],
        "why": practice["why"],
        "virtue": practice["virtue"],
        "intensity": practice["intensity"],
        "date": a.get("date"),
        "completed_at": a.get("completed_at"),
        "note": a.get("note"),
    }

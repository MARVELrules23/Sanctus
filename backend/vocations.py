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
from datetime import date
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
        "afternoon_prayer": {
            "title": "Midday Prayer for the Single Heart",
            "body": "Lord, in the middle of this day I pause and lift my heart to you. "
            "Thank you for the freedom of this hour. Let my work and my rest, my words and "
            "my silences, be a gift of love. Guard my heart in purity and fill my solitude "
            "with your presence, that I may never be alone. Amen.",
        },
        "night_prayer": {
            "title": "Night Prayer for the Single Heart",
            "body": "Lord Jesus, as this day closes I return it to you. For the good I did, "
            "I give you thanks; for what I failed to do, I ask your mercy. Keep watch over "
            "me this night, and let me rest in the peace of one who is wholly yours. Mary, "
            "my Mother, keep me under your mantle until morning. Amen.",
        },
        "companions": [
            {"slug": "catherine-siena", "name": "St. Catherine of Siena",
             "why": "A consecrated virgin in the world who changed the Church through prayer and love.",
             "prayer": "St. Catherine, teach me to love Christ with an undivided heart.",
             "devotions": [
                {"title": "Build your 'interior cell'", "body": "As she taught, withdraw daily into the inner cell of self-knowledge and the love of God, carrying it with you everywhere."},
                {"title": "Pray for the Church and the Pope", "body": "Make her great love your own — offer a daily prayer for the Holy Father and the unity of the Church."},
                {"title": "Read her Dialogue & Letters", "body": "Let her bold, tender counsel form your soul; keep her feast on 29 April."},
             ]},
            {"slug": "pier-giorgio", "name": "Bl. Pier Giorgio Frassati",
             "why": "A joyful young layman who found holiness in friendship, the poor, and the mountains.",
             "prayer": "Bl. Pier Giorgio, help me to live my youth 'verso l'alto' — toward the heights.",
             "devotions": [
                {"title": "Make the Eucharist your 'fuel'", "body": "Receive Communion often and visit the Blessed Sacrament — as he did before climbing mountains or serving the poor."},
                {"title": "Take up the works of mercy", "body": "Visit the sick and the poor in secret, as he did, giving even your bus fare away."},
                {"title": "Aim 'Verso l'alto'", "body": "Make his motto your own — reach higher each day in holiness, friendship and joy."},
             ]},
            {"slug": "john-paul-ii", "name": "St. John Paul II",
             "why": "He lived his single years in deep prayer and gave the Church the Theology of the Body.",
             "prayer": "St. John Paul II, help me discover the meaning of self-gift.",
             "devotions": [
                {"title": "Consecrate yourself: 'Totus Tuus'", "body": "Entrust everything to Our Lady, as he did — make a Marian consecration and renew it often."},
                {"title": "Pray the Luminous Mysteries", "body": "Pray the mysteries of light he gave the Church, meditating on the public life of Christ."},
                {"title": "Study the Theology of the Body", "body": "Read or listen to his teaching on love, the body and the gift of self."},
             ]},
            {"slug": "agnes", "name": "St. Agnes",
             "why": "A young virgin martyr who gave her whole heart to Christ alone.",
             "prayer": "St. Agnes, guard my heart and keep it for the Lord.",
             "devotions": [
                {"title": "Ask daily for the gift of purity", "body": "Each morning, place your heart in her care and ask her help to love chastely and wholly."},
                {"title": "Keep her feast (21 January)", "body": "Honour the young virgin-martyr who chose Christ above all, even unto death."},
             ]},
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
                {"title": "Make a monthly day of recollection", "body": "Step away for a morning of "
                 "silence, Mass and confession to listen for where the Lord is gently leading you."},
                {"title": "Examine your deepest desires", "body": "In prayer, notice what gives lasting "
                 "peace rather than passing excitement — God often calls through the desires he has planted."},
                {"title": "Serve in several ministries", "body": "Try teaching, caring for the poor or the "
                 "sick — a vocation is frequently discovered in the joy of self-giving service."},
            ],
            "living": [
                {"title": "Adopt a simple Rule of Life", "body": "Set fixed times for prayer, work, "
                 "rest, and charity — a gentle structure that keeps God at the centre of an independent life."},
                {"title": "Build deep friendships in faith", "body": "Gather friends for a meal, the "
                 "Rosary, or Sunday Mass. Holy friendship is a foretaste of heaven and a guard against loneliness."},
                {"title": "Tithe your time to the parish", "body": "Let your community know you. Lectoring, "
                 "hospitality, or catechesis turns free time into a self-gift that bears lasting fruit."},
                {"title": "Begin with a Morning Offering", "body": "Consecrate every act, joy and trial of "
                 "the day to the Sacred Heart of Jesus the moment you wake."},
                {"title": "Keep First Fridays and First Saturdays", "body": "Honour the Sacred Heart and the "
                 "Immaculate Heart with these traditional devotions of reparation and love."},
                {"title": "Make a yearly pilgrimage", "body": "Visit a shrine each year to rekindle your "
                 "zeal, give thanks, and place your life again in God's hands."},
                {"title": "Practise spiritual parenthood", "body": "Pray for and quietly mentor the young, "
                 "the poor, priests and religious — your love bears fruit far beyond what you see."},
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
        "afternoon_prayer": {
            "title": "Midday Prayer of Consecrated Love",
            "body": "Lord, at the turning of the day I renew my gift of self to you. In poverty, "
            "let me be rich only in you; in chastity, let my heart be undivided; in obedience, "
            "let me seek only your will. Sanctify this afternoon's labor and prayer, that my "
            "hidden life may bear fruit for the world you love. Amen.",
        },
        "night_prayer": {
            "title": "Compline for the Consecrated Heart",
            "body": "Into your hands, O Lord, I commend my spirit. As the Church keeps vigil, "
            "let my rest be prayer and my sleep be trust. Forgive whatever was unfaithful this "
            "day, and keep me close to your Heart through the night, that I may rise again to "
            "seek you before all else. Amen.",
        },
        "companions": [
            {"slug": "therese-lisieux", "name": "St. Thérèse of Lisieux",
             "why": "The 'Little Flower' who found holiness in small things done with great love.",
             "prayer": "St. Thérèse, teach me your little way of trust and surrender.",
             "devotions": [
                {"title": "Walk the 'Little Way'", "body": "Do the smallest duties with the greatest love, offering each one to Jesus as a child to a Father."},
                {"title": "Pray the Novena of Roses", "body": "Make her famous 24-glory novena and watch for the 'shower of roses' she promised to send."},
                {"title": "Offer little sacrifices", "body": "Keep 'sacrifice beads' or simply count hidden acts of love through the day."},
             ]},
            {"slug": "benedict", "name": "St. Benedict",
             "why": "Father of Western monasticism, who ordered life around prayer and work — 'ora et labora'.",
             "prayer": "St. Benedict, help me to prefer nothing whatever to Christ.",
             "devotions": [
                {"title": "Live 'Ora et Labora'", "body": "Balance fixed times of prayer with honest work, sanctifying the whole day."},
                {"title": "Venerate the St. Benedict Medal", "body": "Wear or keep the medal of protection, praying for deliverance from all evil."},
                {"title": "Read the Rule and seek peace", "body": "Read a little of his Rule daily and practise stability, humility and obedience."},
             ]},
            {"slug": "francis-assisi", "name": "St. Francis of Assisi",
             "why": "He embraced Lady Poverty and rebuilt the Church through humble love.",
             "prayer": "St. Francis, make me an instrument of God's peace.",
             "devotions": [
                {"title": "Pray the Peace Prayer", "body": "Make 'Lord, make me an instrument of your peace' your daily prayer."},
                {"title": "Embrace simplicity and the poor", "body": "Give to those in need and let go of excess, loving Lady Poverty as he did."},
                {"title": "Venerate the San Damiano Crucifix", "body": "Pray before the cross that spoke to him: 'Rebuild my Church.'"},
             ]},
            {"slug": "teresa-avila", "name": "St. Teresa of Ávila",
             "why": "Reformer and mystic who taught that prayer is friendship with the God who loves us.",
             "prayer": "St. Teresa, let nothing disturb me, for God alone suffices.",
             "devotions": [
                {"title": "Pray her bookmark: 'Nada te turbe'", "body": "'Let nothing disturb you… God alone suffices.' Pray it whenever your heart is troubled."},
                {"title": "Practise mental prayer daily", "body": "Spend time alone with the God who loves you — her definition of prayer is simply friendship with him."},
                {"title": "Read 'The Interior Castle'", "body": "Let her map of the soul's journey toward union with God guide your own prayer."},
             ]},
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
                {"title": "Keep a daily holy hour", "body": "Grow accustomed now to long, quiet prayer "
                 "before the Lord — it is the heartbeat of every consecrated life."},
                {"title": "Practise obedience in small things", "body": "Learn to surrender your own "
                 "preferences in ordinary daily life; this is the soil in which a religious vocation grows."},
                {"title": "Live simply and give to the poor", "body": "Taste evangelical poverty before "
                 "you would profess it — let go of what you do not need and share with those in want."},
                {"title": "Read the lives of the founders", "body": "Let the charisms of Benedict, Francis, "
                 "Dominic, Clare and Ignatius speak to your heart — God may call you through one of them."},
            ],
            "living": [
                {"title": "Keep the rhythm of the Hours", "body": "Let the bells of prayer order your "
                 "whole day, sanctifying every hour and binding the community together in praise."},
                {"title": "Honour the Great Silence", "body": "Guard the quiet of the evening and night "
                 "as a sacred space where the soul rests in God alone."},
                {"title": "Celebrate your community's feasts", "body": "Keep the feast of your founder "
                 "and patrons with joy — these traditions are the family memory that forms each generation."},
                {"title": "Practise lectio and the Jesus Prayer", "body": "Let the Word of God and the "
                 "holy Name of Jesus echo within you through the day, until prayer becomes as natural as breathing."},
                {"title": "Offer your work as prayer", "body": "Live 'ora et labora' — sanctify manual "
                 "labour and ordinary tasks by offering them to God with love."},
                {"title": "Welcome the guest as Christ", "body": "Keep the ancient tradition of "
                 "hospitality: see the face of the Lord in every visitor and stranger who comes."},
                {"title": "Guard silence and custody of the eyes", "body": "Cherish exterior and interior "
                 "silence, and guard your senses, so the soul remains recollected and at peace in God."},
                {"title": "Make a daily examen of conscience", "body": "Each night review the day with "
                 "gratitude and humility — a tender conscience is the safeguard of perseverance."},
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
        "afternoon_prayer": {
            "title": "Midday Prayer for the Home",
            "body": "Lord, in the busyness of this day I lift up my spouse and family to you. "
            "Where there is tiredness, give strength; where there is tension, give patience; "
            "where there is distance, draw us near. Holy Family of Nazareth, keep our home in "
            "your peace until we are gathered again this evening. Amen.",
        },
        "night_prayer": {
            "title": "Night Prayer for the Family",
            "body": "Father, we thank you for this day shared in love. Forgive the harsh word "
            "and the missed kindness, and let us not sleep on our anger. Bless my spouse and "
            "each one under this roof; send your holy angels to guard our rest. Jesus, Mary, "
            "and Joseph, watch over our home this night. Amen.",
        },
        "companions": [
            {"slug": "st-joseph", "name": "St. Joseph",
             "why": "Guardian of the Holy Family — model of the faithful, hardworking, protecting spouse.",
             "prayer": "St. Joseph, guardian of families, watch over my home.",
             "devotions": [
                {"title": "Keep Wednesdays for St. Joseph", "body": "Dedicate Wednesdays to him with a prayer or small sacrifice for your family and work."},
                {"title": "Pray the Litany or Chaplet of St. Joseph", "body": "Entrust your home, your livelihood and a holy death to his fatherly care."},
                {"title": "'Go to Joseph'", "body": "Begin the day asking his protection over your spouse, children and household."},
             ]},
            {"slug": "louis-zelie", "name": "Sts. Louis & Zélie Martin",
             "why": "A married couple, parents of St. Thérèse, canonized together for their holy family life.",
             "prayer": "Sts. Louis and Zélie, teach us to make our home a school of holiness.",
             "devotions": [
                {"title": "Pray together each night as they did", "body": "End the day with shared prayer, entrusting your marriage and children to God."},
                {"title": "Sanctify work and family meals", "body": "Offer the ordinary tasks and the family table to God, as they sanctified daily life."},
                {"title": "Attend daily Mass when you can", "body": "They began each day at early Mass — let the Eucharist be the foundation of your family."},
             ]},
            {"slug": "gianna-molla", "name": "St. Gianna Beretta Molla",
             "why": "A wife, mother, and doctor who loved her family and gave her life for her child.",
             "prayer": "St. Gianna, help me to love my family with sacrificial love.",
             "devotions": [
                {"title": "Offer your daily duties with love", "body": "Like her, sanctify work, marriage and motherhood by doing each ordinary duty for love of God."},
                {"title": "Pray for expectant mothers", "body": "Honour the dignity of every life — pray daily for mothers and the unborn."},
                {"title": "Pray her prayer for families", "body": "Ask her intercession for your spouse, children and the health of your family."},
             ]},
            {"slug": "monica", "name": "St. Monica",
             "why": "Her tears and unceasing prayer won the conversion of her son, St. Augustine.",
             "prayer": "St. Monica, teach me to pray with perseverance for those I love.",
             "devotions": [
                {"title": "Pray with perseverance for loved ones", "body": "Never give up praying for the conversion of those you love — she prayed 17 years for St. Augustine."},
                {"title": "Offer your tears and patience", "body": "Unite your sufferings and longings to hers, trusting that no prayer of a faithful heart is wasted."},
                {"title": "Pray her novena for conversions", "body": "Make a novena to St. Monica for a wandering family member or friend."},
             ]},
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
                {"title": "Let courtship be a school of patience", "body": "Practise forgiving quickly "
                 "and putting the other first — the habits you build now will carry into marriage."},
                {"title": "Pray a daily decade for your future family", "body": "Entrust your future "
                 "spouse and children — even now — to the care of Our Lady."},
                {"title": "Find a mentor couple", "body": "Seek out a holy married couple, and make a "
                 "good marriage preparation (Pre-Cana), to learn what self-giving love really asks."},
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
                {"title": "Keep a home altar or prayer corner", "body": "Set apart a sacred space with a "
                 "crucifix, an icon of Our Lady, holy water and a candle — a place the family gathers to pray."},
                {"title": "Chalk your door at Epiphany", "body": "Write 20 + C + M + B + 26 above the door "
                 "and ask God's blessing on all who enter — and have a priest bless your home."},
                {"title": "Pray the Angelus at noon", "body": "Pause at midday to remember the Incarnation; "
                 "a small bell or phone reminder can call the household to prayer."},
                {"title": "Keep holy water at the door", "body": "Bless yourselves on leaving and entering, "
                 "a simple reminder of baptism that sanctifies the comings and goings of the home."},
                {"title": "Feast and rest on Sundays", "body": "Make the Lord's Day different — Mass "
                 "together, a special meal, and true rest from work — so children taste the joy of the faith."},
                {"title": "Read the lives of the saints at bedtime", "body": "Let your children fall asleep "
                 "with heroes of holiness, and grow up wanting to imitate them."},
                {"title": "Renew your vows each anniversary", "body": "Before the Lord, consecrate your "
                 "marriage anew to the Holy Family, asking the grace to love as Christ loves the Church."},
            ],
        },
    },
}


# --------------------------------------------------------------------------- #
# Recommended reading (books + papal encyclicals) per vocation.               #
# `slug` (when present) deep-links into the in-app Library at                 #
# /library/books/<slug>, where encyclicals & classics are free to read.       #
# `kind` is "book" | "encyclical" (drives the badge on the client).           #
# --------------------------------------------------------------------------- #
READINGS: Dict[str, List[Dict[str, Any]]] = {
    "singleness": [
        {"title": "Introduction to the Devout Life", "author": "St. Francis de Sales", "kind": "book", "slug": "devout-life",
         "note": "A gentle, practical guide to holiness for those living in the world."},
        {"title": "Rules for the Discernment of Spirits", "author": "St. Ignatius of Loyola", "kind": "book", "slug": "discernment-of-spirits-ignatius",
         "note": "Learn to read the movements of your heart as you seek God's will."},
        {"title": "The Practice of the Presence of God", "author": "Brother Lawrence", "kind": "book", "slug": "practice-presence-of-god",
         "note": "Turn ordinary solitude into constant, loving companionship with God."},
        {"title": "Gaudete et Exsultate", "author": "Pope Francis", "kind": "encyclical", "slug": "gaudete-et-exsultate",
         "note": "The universal call to holiness in the modern world — yours to answer now."},
        {"title": "Christus Vivit", "author": "Pope Francis", "kind": "encyclical", "slug": "christus-vivit",
         "note": "Christ is alive and calls you to live your youth fully for him."},
    ],
    "religious life": [
        {"title": "The Story of a Soul", "author": "St. Thérèse of Lisieux", "kind": "book", "slug": "story-of-a-soul",
         "note": "The 'Little Way' of trust and love — the heart of a consecrated life."},
        {"title": "The Interior Castle", "author": "St. Teresa of Ávila", "kind": "book", "slug": "interior-castle",
         "note": "A map of the soul's journey through prayer to union with God."},
        {"title": "The Imitation of Christ", "author": "Thomas à Kempis", "kind": "book", "slug": "imitation-of-christ",
         "note": "The classic school of interior life and humble following of Christ."},
        {"title": "The Spiritual Exercises", "author": "St. Ignatius of Loyola", "kind": "book", "slug": "spiritual-exercises-ignatius",
         "note": "A retreat in a book — order your whole life to the greater glory of God."},
        {"title": "Vita Consecrata / Veritatis Splendor", "author": "Pope St. John Paul II", "kind": "encyclical", "slug": "veritatis-splendor",
         "note": "The splendour of truth that grounds every consecrated gift of self."},
        {"title": "Gaudete et Exsultate", "author": "Pope Francis", "kind": "encyclical", "slug": "gaudete-et-exsultate",
         "note": "Holiness is for you — a call renewed for every state of life."},
    ],
    "marriage": [
        {"title": "True Devotion to Mary", "author": "St. Louis de Montfort", "kind": "book", "slug": "true-devotion-mary",
         "note": "Entrust your marriage and children totally to Jesus through Mary."},
        {"title": "The Life and Glories of St. Joseph", "author": "Edward Healy Thompson", "kind": "book", "slug": "life-and-glories-of-st-joseph",
         "note": "Learn from the model husband, father and guardian of the Holy Family."},
        {"title": "Humanae Vitae", "author": "Pope St. Paul VI", "kind": "encyclical", "slug": "humanae-vitae",
         "note": "The Church's beautiful teaching on married love and the gift of life."},
        {"title": "Patris Corde", "author": "Pope Francis", "kind": "encyclical", "slug": "patris-corde",
         "note": "'With a father's heart' — St. Joseph for husbands and fathers today."},
        {"title": "Rosarium Virginis Mariae", "author": "Pope St. John Paul II", "kind": "encyclical", "slug": "rosarium-virginis-mariae",
         "note": "On the family Rosary — the prayer that builds a home upon the rock."},
        {"title": "Redemptoris Custos", "author": "Pope St. John Paul II", "kind": "encyclical", "slug": "redemptoris-custos",
         "note": "On St. Joseph, guardian of the Redeemer and of every Christian home."},
    ],
}

# --------------------------------------------------------------------------- #
# Prayer / novena / devotion recommendations per vocation.                    #
# `route` deep-links to an existing in-app screen.                            #
# --------------------------------------------------------------------------- #
DEVOTIONAL_RECS: Dict[str, List[Dict[str, Any]]] = {
    "singleness": [
        {"title": "Daily Rosary", "body": "Pray a decade or the full Rosary for a pure, generous and undivided heart.", "route": "/prayer/rosary"},
        {"title": "Novena to St. Joseph", "body": "Entrust your future and vocation to the guardian of the Holy Family.", "route": "/novenas/st-joseph"},
        {"title": "Marian Consecration (33 Days)", "body": "Give yourself totally to Jesus through Mary — a beautiful path for the single heart.", "route": "/consecration"},
        {"title": "Liturgy of the Hours", "body": "Sanctify your day with the Church's prayer, morning and night.", "route": "/liturgy"},
    ],
    "religious life": [
        {"title": "Liturgy of the Hours", "body": "Pray Lauds and Compline daily, joining the Church's unceasing praise.", "route": "/liturgy"},
        {"title": "Novena to St. Thérèse of Lisieux", "body": "Ask the Little Flower to guide you in her 'little way' of love.", "route": "/novenas/st-therese-little-flower"},
        {"title": "Chaplets", "body": "Pray the Divine Mercy Chaplet and others as a school of trust and intercession.", "route": "/prayer/category/chaplets"},
        {"title": "Marian Consecration", "body": "Consecrate your whole life to Jesus through the hands of Our Lady.", "route": "/consecration"},
    ],
    "marriage": [
        {"title": "Family Rosary", "body": "Gather the family for a daily decade — the prayer that keeps a home together.", "route": "/prayer/rosary"},
        {"title": "Novena to Sts. Louis & Zélie Martin", "body": "Ask the patrons of holy marriage to bless your family life.", "route": "/novenas/sts-louis-zelie"},
        {"title": "Novena to St. Joseph", "body": "Place your spouse, children and livelihood under his fatherly care.", "route": "/novenas/st-joseph"},
        {"title": "Marian Prayers", "body": "Entrust your spouse and children to Our Lady with the Church's Marian prayers.", "route": "/prayer/category/marian"},
    ],
}


# --------------------------------------------------------------------------- #
# Daily Scripture aligned to the vocation. One verse is surfaced each day,     #
# chosen deterministically from the pool by the ordinal date so it is stable   #
# for everyone on a given day and rotates through the week.                    #
# --------------------------------------------------------------------------- #
VOCATION_VERSES: Dict[str, List[Dict[str, str]]] = {
    "singleness": [
        {"reference": "1 Corinthians 7:34", "text": "The unmarried woman and the virgin thinketh on the things of the Lord, that she may be holy both in body and in spirit."},
        {"reference": "Psalm 27:4", "text": "One thing I have asked of the Lord, this will I seek after: that I may dwell in the house of the Lord all the days of my life."},
        {"reference": "Matthew 6:33", "text": "Seek ye therefore first the kingdom of God, and his justice, and all these things shall be added unto you."},
        {"reference": "Psalm 73:25-26", "text": "For what have I in heaven? and besides thee what do I desire upon earth? God is the God of my heart, and the God that is my portion for ever."},
        {"reference": "1 Corinthians 7:35", "text": "This I speak for your profit… that which may give you power to attend upon the Lord, without impediment."},
        {"reference": "Isaiah 26:3", "text": "The old error is passed away: thou wilt keep peace: peace, because we have hoped in thee."},
        {"reference": "Philippians 4:6-7", "text": "Be nothing solicitous; but in every thing, by prayer and supplication, let your petitions be made known to God. And the peace of God… keep your hearts and minds in Christ Jesus."},
    ],
    "religious life": [
        {"reference": "Matthew 19:21", "text": "If thou wilt be perfect, go sell what thou hast, and give to the poor, and thou shalt have treasure in heaven: and come, follow me."},
        {"reference": "Psalm 16:5-6", "text": "The Lord is the portion of my inheritance and of my cup: it is thou that wilt restore my inheritance to me. The lines are fallen unto me in goodly places."},
        {"reference": "Luke 10:42", "text": "But one thing is necessary. Mary hath chosen the best part, which shall not be taken away from her."},
        {"reference": "Matthew 16:24", "text": "If any man will come after me, let him deny himself, and take up his cross, and follow me."},
        {"reference": "Galatians 2:20", "text": "And I live, now not I; but Christ liveth in me. And that I live now in the flesh: I live in the faith of the Son of God."},
        {"reference": "Song of Songs 1:3", "text": "Draw me: we will run after thee to the odour of thy ointments."},
        {"reference": "Psalm 42:1-2", "text": "As the hart panteth after the fountains of water; so my soul panteth after thee, O God. My soul hath thirsted after the strong living God."},
    ],
    "marriage": [
        {"reference": "Genesis 2:24", "text": "Wherefore a man shall leave father and mother, and shall cleave to his wife: and they shall be two in one flesh."},
        {"reference": "Ephesians 5:25", "text": "Husbands, love your wives, as Christ also loved the church, and delivered himself up for it."},
        {"reference": "1 Corinthians 13:4-5", "text": "Charity is patient, is kind: charity envieth not, dealeth not perversely; is not puffed up; is not ambitious, seeketh not her own."},
        {"reference": "Tobit 8:7", "text": "And now, Lord, thou knowest, that not for fleshly lust do I take my sister to wife, but only for the love of posterity… have mercy on us, and grant that we may grow old together."},
        {"reference": "Ecclesiastes 4:9-10", "text": "It is better therefore that two should be together, than one: for they have the advantage of their society. If one fall he shall be supported by the other."},
        {"reference": "Colossians 3:14", "text": "But above all these things have charity, which is the bond of perfection."},
        {"reference": "Mark 10:9", "text": "What therefore God hath joined together, let no man put asunder."},
    ],
}


def _daily_verse(vocation: str) -> Dict[str, str]:
    pool = VOCATION_VERSES.get(vocation) or []
    if not pool:
        return {}
    idx = date.today().toordinal() % len(pool)
    return dict(pool[idx])


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
    for key in ("afternoon_prayer", "night_prayer"):
        pr = payload.get(key) or {}
        collect(lambda pr=pr: pr.get("title"), lambda t, pr=pr: pr.__setitem__("title", t))
        collect(lambda pr=pr: pr.get("body"), lambda t, pr=pr: pr.__setitem__("body", t))
    for c in payload.get("companions") or []:
        collect(lambda c=c: c.get("why"), lambda t, c=c: c.__setitem__("why", t))
        collect(lambda c=c: c.get("prayer"), lambda t, c=c: c.__setitem__("prayer", t))
        for dv in c.get("devotions") or []:
            collect(lambda d=dv: d.get("title"), lambda t, d=dv: d.__setitem__("title", t))
            collect(lambda d=dv: d.get("body"), lambda t, d=dv: d.__setitem__("body", t))
    for sec in ("ideas", "traditions"):
        for item in payload.get(sec) or []:
            collect(lambda i=item: i.get("title"), lambda t, i=item: i.__setitem__("title", t))
            collect(lambda i=item: i.get("body"), lambda t, i=item: i.__setitem__("body", t))
    # Recommended reading — translate the one-line note only (keep book titles/authors as-is).
    for item in payload.get("readings") or []:
        collect(lambda i=item: i.get("note"), lambda t, i=item: i.__setitem__("note", t))
    # Prayer/novena/devotion recommendations — translate title + body.
    for item in payload.get("devotional_recs") or []:
        collect(lambda i=item: i.get("title"), lambda t, i=item: i.__setitem__("title", t))
        collect(lambda i=item: i.get("body"), lambda t, i=item: i.__setitem__("body", t))
    # Daily Scripture — translate the verse text (keep the reference untouched).
    dv = payload.get("daily_verse")
    if dv:
        collect(lambda: dv.get("text"), lambda t: dv.__setitem__("text", t))

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
        "afternoon_prayer": copy.deepcopy(base.get("afternoon_prayer") or base["morning_prayer"]),
        "night_prayer": copy.deepcopy(base.get("night_prayer") or base["morning_prayer"]),
        "companions": copy.deepcopy(base["companions"]),
        "ideas": copy.deepcopy(base["ideas"]),
        "traditions": copy.deepcopy(traditions),
        "readings": copy.deepcopy(READINGS.get(vocation, [])),
        "devotional_recs": copy.deepcopy(DEVOTIONAL_RECS.get(vocation, [])),
        "daily_verse": _daily_verse(vocation),
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

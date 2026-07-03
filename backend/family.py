"""Family tab — daily prayers, devotional suggestion, question of the day and a
rotating Saint Spotlight for parents and children to pray and talk together.

Everything is deterministic per calendar day (rotates by ordinal date) so a
whole family sees the same content, and it is localized (EN/ES/IT) through the
shared cached translator.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from lang_ctx import get_lang
from i18n_translate import translate_texts

_LLM_KEY = ""


def set_llm_key(key: str) -> None:
    global _LLM_KEY
    _LLM_KEY = key or ""


MORNING_PRAYER = {
    "title": "Morning Prayer Together",
    "lines": [
        {"who": "Leader", "text": "In the name of the Father, and of the Son, and of the Holy Spirit. Amen."},
        {"who": "All", "text": "Thank You, God, for this new day. We offer You all we think, say and do."},
        {"who": "Parent", "text": "Guardian angels, watch over our children today."},
        {"who": "Child", "text": "Jesus, help me to be kind, honest and joyful today."},
        {"who": "All", "text": "Hail Mary, full of grace… (pray one Hail Mary together). Amen."},
    ],
}

NIGHT_PRAYER = {
    "title": "Night Prayer Together",
    "lines": [
        {"who": "Leader", "text": "In the name of the Father, and of the Son, and of the Holy Spirit. Amen."},
        {"who": "All", "text": "Thank You, God, for the gifts of today. We are sorry for the times we were unkind."},
        {"who": "Parent", "text": "Bless our family and keep us safe through the night."},
        {"who": "Child", "text": "Jesus, Mary and Joseph, watch over me while I sleep."},
        {"who": "All", "text": "Angel of God, my guardian dear… Amen. Goodnight, God — we love You."},
    ],
}

# Rotating daily devotional suggestions. `route` deep-links into the app.
DEVOTIONALS: List[Dict[str, str]] = [
    {"title": "Pray one decade of the Rosary", "body": "Ten Hail Marys as a family, offered for one another.", "route": "/prayer/rosary"},
    {"title": "Begin a novena to St. Joseph", "body": "Nine days of prayer to the guardian of the Holy Family.", "route": "/novenas/st-joseph"},
    {"title": "Pray the Angelus at noon", "body": "Pause together to remember the Word made flesh.", "route": "/prayer/category/marian"},
    {"title": "A novena to St. Thérèse", "body": "Ask the Little Flower to teach your family the little way of love.", "route": "/novenas/st-therese-little-flower"},
    {"title": "Make a Morning Offering", "body": "Give the whole day to Jesus through the heart of Mary.", "route": "/prayer/category/marian"},
    {"title": "Pray the Divine Mercy Chaplet", "body": "A short, powerful prayer for God's mercy on the world.", "route": "/prayer/category/chaplets"},
    {"title": "Read the day's Gospel together", "body": "Listen to a few lines of Jesus' words at the dinner table.", "route": "/mass"},
    {"title": "Litany of the saints (short)", "body": "Call on your family's patron saints by name.", "route": "/prayer/category/litany"},
    {"title": "Consecrate the day to the Sacred Heart", "body": "Place your family in the Heart of Jesus.", "route": "/prayer/category/marian"},
    {"title": "A novena to Sts. Louis & Zélie Martin", "body": "Patrons of holy marriage and family life.", "route": "/novenas/sts-louis-zelie"},
    {"title": "Pray for the holy souls", "body": "One Our Father for those who have gone before us.", "route": "/prayer/rosary"},
    {"title": "Practice the Jesus Prayer", "body": "Repeat gently: 'Lord Jesus Christ, have mercy on me.'", "route": "/prayer/rosary"},
    {"title": "Novena to Our Lady of Perpetual Help", "body": "Bring every family need to our Mother.", "route": "/novenas/our-lady-perpetual-help"},
    {"title": "Bless your children before bed", "body": "Trace a small cross on each child's forehead.", "route": None},
]

# One question a day for parents to ask their children.
QUESTIONS: List[str] = [
    "If you could ask Jesus one question, what would it be?",
    "When did you feel most loved today?",
    "Who is someone you can be kind to tomorrow?",
    "What is one thing you are thankful to God for right now?",
    "If your guardian angel had a name, what would it be?",
    "What is the hardest part about being kind sometimes?",
    "Which Bible story is your favourite, and why?",
    "When did you say sorry today, or need to?",
    "What do you think heaven looks like?",
    "Who in our family needs a little extra love this week?",
    "What is something good you did today that no one saw?",
    "If you could help one person tomorrow, who would it be?",
    "What makes you feel close to God?",
    "What is a rule that is actually there to keep us safe?",
    "Which saint would you most like to meet, and what would you say?",
    "What is one worry you can give to Jesus tonight?",
    "How did someone show you kindness today?",
    "What is your favourite thing about our family?",
    "When is it hardest to tell the truth?",
    "What is one way we could pray better together?",
    "If Jesus came to dinner, what would you want to show Him?",
    "What made you laugh today? Thank God for it.",
    "Who is someone you should forgive?",
    "What is something beautiful God made that you saw today?",
    "How can you be a peacemaker with your brothers or sisters?",
    "What are you looking forward to, and can we pray about it?",
    "What does it mean to be brave for what is good?",
    "Which of God's commandments is easiest for you? Which is hardest?",
    "What is one small sacrifice you could make for love tomorrow?",
    "How do you know that God loves you?",
]

# Rotating Saint Spotlight — a saint a day, tappable to learn more.
SAINTS: List[Dict[str, str]] = [
    {"name": "St. Francis of Assisi", "feast": "October 4", "patronage": "Animals & ecology", "icon": "paw-outline", "color": "#5B7A3E",
     "bio": "St. Francis gave up wealth to follow Jesus in total poverty and joy. He loved all of God's creation, calling the sun his brother and the moon his sister, and even preached to the birds. He received the wounds of Christ (the stigmata) and founded the Franciscan order. He shows us to live simply and to see God in everything."},
    {"name": "St. Thérèse of Lisieux", "feast": "October 1", "patronage": "Missions", "icon": "flower-outline", "color": "#8A6A2E",
     "bio": "A young nun in France, Thérèse found her 'Little Way' — doing small, ordinary things with great love for God. She trusted Jesus like a little child trusts a loving father. Though she never left her convent, she is the patroness of missionaries, and promised to spend her heaven sending a shower of roses of grace to earth."},
    {"name": "St. Joseph", "feast": "March 19", "patronage": "Fathers & workers", "icon": "hammer-outline", "color": "#7A5C2E",
     "bio": "St. Joseph was the husband of Mary and the earthly father of Jesus. A humble carpenter, he protected the Holy Family and taught Jesus to work and pray. He speaks no words in the Gospels, yet his quiet obedience makes him the model of fathers and the patron of a holy death and of the whole Church."},
    {"name": "St. Nicholas", "feast": "December 6", "patronage": "Children & gift-givers", "icon": "gift-outline", "color": "#8A2E2E",
     "bio": "A kind bishop who loved to give in secret, St. Nicholas once tossed bags of gold through a poor family's window at night. His generosity inspired the tradition of Christmas gift-giving. He is a great patron of children and reminds us of the joy of giving without expecting thanks."},
    {"name": "St. Patrick", "feast": "March 17", "patronage": "Ireland", "icon": "leaf-outline", "color": "#3E7A4E",
     "bio": "Taken from home as a boy, Patrick grew close to God through prayer. He returned to Ireland as a missionary and used the three-leaf shamrock to explain the Holy Trinity — three Persons in one God. He brought countless people to Christ and is the beloved patron of Ireland."},
    {"name": "St. Bernadette", "feast": "April 16", "patronage": "The sick", "icon": "water-outline", "color": "#3E6B8A",
     "bio": "A poor, humble girl of Lourdes, Bernadette saw the Blessed Virgin Mary eighteen times. Mary asked for prayer and penance, and a healing spring appeared where Bernadette dug. Millions still visit Lourdes. Bernadette teaches us that God chooses the small and humble to do great things."},
    {"name": "St. Kateri Tekakwitha", "feast": "July 14", "patronage": "Ecology & the environment", "icon": "sparkles-outline", "color": "#5B6B3E",
     "bio": "A young Mohawk woman in North America, Kateri fell in love with Jesus and was baptized despite opposition. Known as the 'Lily of the Mohawks' for her purity and kindness, she prayed constantly before the cross. She is the first Native American saint."},
    {"name": "St. John Bosco", "feast": "January 31", "patronage": "Young people", "icon": "happy-outline", "color": "#7A4E2E",
     "bio": "Don Bosco loved poor boys who had no one to care for them. He gathered them with games and juggling tricks, then taught them about Jesus. He gave them homes, schools and trades. His secret to holiness was simple: joy, hard work, and love of God."},
    {"name": "St. Anthony of Padua", "feast": "June 13", "patronage": "Lost things", "icon": "search-outline", "color": "#6B4E2E",
     "bio": "A brilliant preacher and Doctor of the Church, St. Anthony could explain the faith so clearly that even fish were said to listen. He is famous as the finder of lost things — many pray, 'St. Anthony, help me find what is lost,' whether keys or a wandering heart."},
    {"name": "St. Cecilia", "feast": "November 22", "patronage": "Musicians", "icon": "musical-notes-outline", "color": "#8A2E5B",
     "bio": "A young Roman woman who loved God with all her heart, Cecilia is said to have sung to the Lord in her heart even at her wedding. She remained faithful to Christ unto death. She is the patroness of music and church musicians."},
    {"name": "St. George", "feast": "April 23", "patronage": "Courage & soldiers", "icon": "shield-outline", "color": "#8A2E2E",
     "bio": "A brave Roman soldier who refused to deny Christ, St. George is remembered in the legend of the dragon — a picture of courage overcoming evil. He is a patron of many lands and reminds us to be brave in defending what is good and true."},
    {"name": "St. Clare of Assisi", "feast": "August 11", "patronage": "Television & eyes", "icon": "flower-outline", "color": "#7A6A3E",
     "bio": "Inspired by St. Francis, Clare left everything to follow Jesus in poverty and prayer, founding the Poor Clares. Once, when her convent was in danger, she trusted so deeply in the Blessed Sacrament that the enemy fled. She shows us the power of quiet, hidden holiness."},
    {"name": "St. Michael the Archangel", "feast": "September 29", "patronage": "Protection", "icon": "shield-checkmark-outline", "color": "#3E4E7A",
     "bio": "St. Michael is a mighty angel and defender of God's people. His name means 'Who is like God?' He leads the angels against evil. Families often pray to St. Michael for protection: 'St. Michael the Archangel, defend us in battle.'"},
    {"name": "St. Rita of Cascia", "feast": "May 22", "patronage": "Impossible cases", "icon": "rose-outline", "color": "#7A2E4E",
     "bio": "Through great trials as a wife, mother and later a nun, St. Rita never lost her trust in God. She is the patroness of impossible and desperate causes, reminding worried hearts that nothing is impossible for God."},
    {"name": "St. Padre Pio", "feast": "September 23", "patronage": "Confessors", "icon": "medal-outline", "color": "#6B5A2E",
     "bio": "A humble Italian friar who bore the wounds of Christ for fifty years, Padre Pio spent long hours hearing confessions and praying. His famous advice was: 'Pray, hope, and don't worry.' He reminds us to bring everything to God in trust."},
    {"name": "St. Elizabeth of Hungary", "feast": "November 17", "patronage": "The poor", "icon": "heart-outline", "color": "#8A5C2E",
     "bio": "A princess who used her riches to feed and care for the poor and sick, St. Elizabeth once carried bread to the hungry that turned to roses. She teaches children that true greatness is found in serving those in need."},
]


def _pick(pool: List[Any]) -> Any:
    return pool[date.today().toordinal() % len(pool)]


async def get_today(db) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "morning_prayer": {k: (v if k != "lines" else [dict(x) for x in v]) for k, v in MORNING_PRAYER.items()},
        "night_prayer": {k: (v if k != "lines" else [dict(x) for x in v]) for k, v in NIGHT_PRAYER.items()},
        "devotional": dict(_pick(DEVOTIONALS)),
        "question": _pick(QUESTIONS),
        "saint": dict(_pick(SAINTS)),
    }
    return await _localize(db, payload)


async def _localize(db, payload: Dict[str, Any]) -> Dict[str, Any]:
    lang = get_lang()
    if lang == "en":
        return payload
    strings: List[str] = []
    setters: List[Any] = []

    def add(get, setv):
        v = get()
        if v:
            strings.append(v)
            setters.append(setv)

    for pr in (payload["morning_prayer"], payload["night_prayer"]):
        add(lambda p=pr: p.get("title"), lambda t, p=pr: p.__setitem__("title", t))
        for ln in pr["lines"]:
            add(lambda l=ln: l.get("text"), lambda t, l=ln: l.__setitem__("text", t))
    dv = payload["devotional"]
    add(lambda: dv.get("title"), lambda t: dv.__setitem__("title", t))
    add(lambda: dv.get("body"), lambda t: dv.__setitem__("body", t))
    add(lambda: payload.get("question"), lambda t: payload.__setitem__("question", t))
    sa = payload["saint"]
    add(lambda: sa.get("patronage"), lambda t: sa.__setitem__("patronage", t))
    add(lambda: sa.get("bio"), lambda t: sa.__setitem__("bio", t))
    if not strings:
        return payload
    out: List[str] = []
    for i in range(0, len(strings), 60):
        out += await translate_texts(db, _LLM_KEY, strings[i : i + 60], lang)
    for setv, tr in zip(setters, out):
        if tr:
            setv(tr)
    return payload

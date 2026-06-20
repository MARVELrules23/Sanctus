"""Sanctus — Christian Prayer: The Liturgy of the Hours.

A public-domain, in-app reader for the traditional Roman Breviary
(Liturgia Horarum) in pre-1962 form. Latin (Vulgata Clementina) + English
(Douay-Rheims 1899 + pre-1929 English translations of the canticles).

Scope (v1): the three principal Hours every Catholic ought to be able to
pray — Lauds (Ad Laudes), Vespers (Ad Vesperas), and Compline (Ad
Completorium) — with a full weekday ferial rotation (Sunday through
Saturday). The sections are arranged in the **exact order printed in
the physical breviary**:

    Lauds & Vespers
      1. Deus in adjutórium (opening versicle)
      2. Antiphons & Psalms (5 psalms, varies by weekday)
      3. Capitulum (Little Chapter — short reading)
      4. Hymnus (Hymn)
      5. Versus (Versicle & Response)
      6. Canticum Evangelicum (Benedictus at Lauds; Magnificat at Vespers)
      7. Pater Noster · Preces · Oratio (Collect)
      8. Benedicámus Dómino (Dismissal)

    Compline
      1. Jube, domne, benedícere (Preparation)
      2. Lectio brevis · Adjutórium nostrum · Confíteor
      3. Deus in adjutórium
      4. Psalms (fixed pre-1911 scheme: Ps 4, 30:1–6, 90, 133)
      5. Hymnus — Te lucis ante términum
      6. Capitulum · Responsorium · Versus
      7. Nunc dimíttis (Canticle of Simeon)
      8. Oratio · Benedictio · Marian Antiphon (varies by season)

Hybrid implementation note:
    This module ships the public-domain TEXT natively. Modern (post-Vatican II)
    Liturgy of the Hours texts are copyrighted (ICEL / Catholic Book Publishing
    Corp.) and are NOT included here. The frontend offers an explicit deep-link
    button out to iBreviary / Universalis for users who want the modern form.

All endpoints require auth and are NOT premium-gated. Founder direction:
the divine office should be free for every member of the Body of Christ.

Endpoints (all prefixed `/api`):

  GET  /api/liturgy
       → { hours: [...], days: [{key, name, latin_name, weekday_index}] }

  GET  /api/liturgy/{hour_slug}
       → { slug, name, latin_name, intro, days: [...], section_count_per_day }

  GET  /api/liturgy/{hour_slug}/{day_key}
       → { hour: {...}, day: {...},
           sections: [{index, title, latin_title?, latin?, english,
                       rubric?, note?}] }
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from lang_ctx import get_lang
from i18n_translate import translate_texts

logger = logging.getLogger("sanctus.liturgy")


# ---------------------------------------------------------------------------
# Section helper (mirrors missals._section for consistency)
# ---------------------------------------------------------------------------


def _section(
    title: str,
    english: str,
    latin: Optional[str] = None,
    latin_title: Optional[str] = None,
    rubric: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "title": title,
        "latin_title": latin_title.strip() if latin_title else None,
        "english": english.strip(),
        "latin": latin.strip() if latin else None,
        "rubric": rubric.strip() if rubric else None,
        "note": note.strip() if note else None,
    }


# ===========================================================================
# COMMON / ORDINARY PIECES — used across days
# ===========================================================================

# --- Opening versicle (every hour except Matins / Compline preparation) ---
DEUS_IN_ADJUTORIUM = _section(
    title="Opening Versicle",
    latin_title="Deus in adjutórium",
    rubric=(
        "All make the Sign of the Cross at \"Deus in adjutórium meum inténde\""
        " and bow at the Glória Patri."
    ),
    english=(
        "V. O God, come to my assistance.\n"
        "R. O Lord, make haste to help me.\n\n"
        "Glory be to the Father, and to the Son, and to the Holy Ghost.\n"
        "As it was in the beginning, is now, and ever shall be, "
        "world without end. Amen. Alleluia.\n\n"
        "(From Septuagesima to Holy Saturday, in place of Alleluia is said: "
        "Laus tibi, Dómine, Rex ætérnæ glóriæ. — Praise be to thee, O Lord, "
        "King of eternal glory.)"
    ),
    latin=(
        "V. Deus, in adjutórium meum inténde.\n"
        "R. Dómine, ad adjuvándum me festína.\n\n"
        "Glória Patri, et Fílio, et Spirítui Sancto.\n"
        "Sicut erat in princípio, et nunc, et semper, "
        "et in sǽcula sæculórum. Amen. Allelúja."
    ),
)

PATER_NOSTER = _section(
    title="Our Father",
    latin_title="Pater Noster",
    rubric="Said silently as far as \"and lead us not into temptation.\"",
    english=(
        "Our Father, who art in heaven, hallowed be thy name; thy kingdom come; "
        "thy will be done on earth as it is in heaven. Give us this day our "
        "daily bread; and forgive us our trespasses, as we forgive those who "
        "trespass against us;\n\n"
        "V. And lead us not into temptation.\n"
        "R. But deliver us from evil."
    ),
    latin=(
        "Pater noster, qui es in cælis, sanctificétur nomen tuum. Advéniat "
        "regnum tuum. Fiat volúntas tua, sicut in cælo et in terra. Panem "
        "nostrum quotidiánum da nobis hódie, et dimítte nobis débita nostra, "
        "sicut et nos dimíttimus debitóribus nostris.\n\n"
        "V. Et ne nos indúcas in tentatiónem.\n"
        "R. Sed líbera nos a malo."
    ),
)

DISMISSAL_BENEDICAMUS = _section(
    title="Dismissal",
    latin_title="Benedicámus Dómino",
    english=(
        "V. Let us bless the Lord.\n"
        "R. Thanks be to God.\n\n"
        "V. May the souls of the faithful departed, through the mercy of God, "
        "rest in peace.\n"
        "R. Amen."
    ),
    latin=(
        "V. Benedicámus Dómino.\n"
        "R. Deo grátias.\n\n"
        "V. Fidélium ánimæ per misericórdiam Dei requiéscant in pace.\n"
        "R. Amen."
    ),
)


# ===========================================================================
# LAUDS — Ad Laudes (Morning Prayer)
# ===========================================================================
#
# Each weekday has its proper psalmody. The pre-1962 Roman Breviary, after
# the Pian (1911) reform, distributes the psalter through the week. We give
# the Sunday Lauds I scheme on Sunday and the ferial schemes Mon–Sat.
# Psalm texts are excerpted from the Douay-Rheims (1899) for English and
# the Clementine Vulgate for Latin — typically the opening verses to keep
# the office prayable in 10–15 minutes; the full psalter is encouraged.

LAUDS_SUNDAY_PSALMS = _section(
    title="Antiphons & Psalms",
    latin_title="Antiphonæ et Psalmi",
    rubric=(
        "Sunday Lauds: Psalms 92, 99, 62 (with 66 as one psalm), the canticle "
        "Benedícite (Daniel 3:57–88, 56), and Psalms 148–149–150 (as one psalm)."
    ),
    english=(
        "Ant. 1. The Lord hath reigned, He is clothed with beauty.\n\n"
        "Psalm 92.\n"
        "The Lord hath reigned, he is clothed with beauty: the Lord is clothed "
        "with strength, and hath girded himself. For he hath established the "
        "world which shall not be moved. Thy throne is prepared from of old: "
        "thou art from everlasting. Glory be to the Father…\n\n"
        "Ant. 2. Sing joyfully to God, all the earth: serve ye the Lord with "
        "gladness.\n\n"
        "Psalm 99.\n"
        "Sing joyfully to God, all the earth: serve ye the Lord with gladness. "
        "Come in before his presence with exceeding great joy. Know ye that the "
        "Lord he is God: he made us, and not we ourselves. We are his people "
        "and the sheep of his pasture. Glory be to the Father…\n\n"
        "Ant. 3. O God, my God, to thee do I watch at break of day.\n\n"
        "Psalm 62.\n"
        "O God, my God, to thee do I watch at break of day. For thee my soul "
        "hath thirsted; for thee my flesh, O how many ways! In a desert land, "
        "and where there is no way, and no water: so in the sanctuary have I "
        "come before thee, to see thy power and thy glory. Glory be…\n\n"
        "Ant. 4. The three children, as out of one mouth, sang praise in the "
        "furnace, saying: Blessed be God.\n\n"
        "Canticle of the Three Young Men. (Daniel 3:57–88,56)\n"
        "All ye works of the Lord, bless the Lord: praise and exalt him above "
        "all for ever. O ye Angels of the Lord, bless the Lord. O ye sun and "
        "moon, bless the Lord. O ye stars of heaven, bless the Lord… "
        "Let us bless the Father, and the Son, with the Holy Ghost: let us "
        "praise and exalt him above all for ever.\n\n"
        "Ant. 5. Praise the Lord from the heavens, alleluia.\n\n"
        "Psalm 148.\n"
        "Praise ye the Lord from the heavens: praise ye him in the high places. "
        "Praise ye him, all his angels: praise him, all his hosts. Praise ye "
        "him, O sun and moon: praise him all ye stars and light. "
        "Praise ye the name of the Lord. Glory be to the Father…"
    ),
    latin=(
        "Ant. 1. Dóminus regnávit, decórem índuit.\n\n"
        "Psalmus 92.\n"
        "Dóminus regnávit, decórem indútus est: indútus est Dóminus "
        "fortitúdinem, et præcínxit se. Étenim firmávit orbem terræ, qui non "
        "commovébitur. Paráta sedes tua ex tunc: a sǽculo tu es. Glória Patri…\n\n"
        "Ant. 2. Jubiláte Deo, omnis terra: servíte Dómino in lætítia.\n\n"
        "Psalmus 99.\n"
        "Jubiláte Deo, omnis terra: servíte Dómino in lætítia. Introíte in "
        "conspéctu ejus in exsultatióne. Scitóte quóniam Dóminus ipse est Deus: "
        "ipse fecit nos, et non ipsi nos. Pópulus ejus, et oves páscuæ ejus. "
        "Glória Patri…\n\n"
        "Ant. 3. Deus, Deus meus, ad te de luce vígilo.\n\n"
        "Psalmus 62.\n"
        "Deus, Deus meus, ad te de luce vígilo. Sitívit in te ánima mea, quam "
        "multiplíciter tibi caro mea. In terra desérta, et ínvia, et inaquósa: "
        "sic in sancto appárui tibi, ut vidérem virtútem tuam, et glóriam "
        "tuam. Glória Patri…\n\n"
        "Ant. 4. Tres púeri quasi ex uno ore laudábant in camíno fornácis, "
        "dicéntes: Benedíctus Deus.\n\n"
        "Canticum Trium Puerorum. (Daniel 3:57–88,56)\n"
        "Benedícite, ómnia ópera Dómini, Dómino: laudáte et superexaltáte eum "
        "in sǽcula. Benedícite, ángeli Dómini, Dómino. Benedícite, sol et luna, "
        "Dómino. Benedícite, stellæ cæli, Dómino… Benedicámus Patrem, et "
        "Fílium, cum Sancto Spíritu: laudémus et superexaltémus eum in sǽcula.\n\n"
        "Ant. 5. Laudáte Dóminum de cælis, allelúja.\n\n"
        "Psalmus 148.\n"
        "Laudáte Dóminum de cælis: laudáte eum in excélsis. Laudáte eum, omnes "
        "ángeli ejus: laudáte eum, omnes virtútes ejus. Laudáte eum, sol et "
        "luna: laudáte eum, omnes stellæ et lumen. Laudáte nomen Dómini. "
        "Glória Patri…"
    ),
)

LAUDS_MONDAY_PSALMS = _section(
    title="Antiphons & Psalms",
    latin_title="Antiphonæ et Psalmi",
    rubric="Monday Lauds: Psalms 46, 5, 28, the Canticle of Isaias, Ps 116.",
    english=(
        "Ant. 1. O clap your hands, all ye nations.\n\n"
        "Psalm 46.\n"
        "O clap your hands, all ye nations: shout unto God with the voice of "
        "joy. For the Lord is high, terrible: a great king over all the earth. "
        "He hath subdued the people under us; and the nations under our feet. "
        "Glory be to the Father…\n\n"
        "Ant. 2. Give ear, O Lord, to my words.\n\n"
        "Psalm 5.\n"
        "Give ear, O Lord, to my words, understand my cry. Hearken to the voice "
        "of my prayer, O my King and my God. For to thee will I pray: O Lord, "
        "in the morning thou shalt hear my voice. In the morning I will stand "
        "before thee, and will see. Glory be…\n\n"
        "Ant. 3. Unto thee, O Lord, will I cry.\n\n"
        "Psalm 28.\n"
        "Bring to the Lord, O ye children of God: bring to the Lord the "
        "offspring of rams. Bring to the Lord glory and honour: bring to the "
        "Lord glory to his name; adore ye the Lord in his holy court. The "
        "voice of the Lord is upon the waters; the God of majesty hath "
        "thundered. Glory be…\n\n"
        "Ant. 4. We shall rejoice in thy salvation.\n\n"
        "Canticle of Isaias. (Isaias 12)\n"
        "I will give thanks to thee, O Lord, for thou wast angry with me: thy "
        "wrath is turned away, and thou hast comforted me. Behold, God is my "
        "saviour, I will deal confidently, and will not fear; because the Lord "
        "is my strength, and my praise, and he is become my salvation. Glory "
        "be…\n\n"
        "Ant. 5. I will praise the Lord all my life.\n\n"
        "Psalm 116.\n"
        "O praise the Lord, all ye nations: praise him, all ye people. For his "
        "mercy is confirmed upon us: and the truth of the Lord remaineth for "
        "ever. Glory be to the Father…"
    ),
    latin=(
        "Ant. 1. Omnes gentes, pláudite mánibus.\n\n"
        "Psalmus 46.\n"
        "Omnes gentes, pláudite mánibus: jubiláte Deo in voce exsultatiónis. "
        "Quóniam Dóminus excélsus, terríbilis: Rex magnus super omnem terram. "
        "Subjécit pópulos nobis: et gentes sub pédibus nostris. Glória Patri…\n\n"
        "Ant. 2. Verba mea áuribus pércipe, Dómine.\n\n"
        "Psalmus 5.\n"
        "Verba mea áuribus pércipe, Dómine, intéllige clamórem meum. Inténde "
        "voci oratiónis meæ, Rex meus et Deus meus. Quóniam ad te orábo: "
        "Dómine, mane exáudies vocem meam. Mane astábo tibi et vidébo. Glória "
        "Patri…\n\n"
        "Ant. 3. Ad te, Dómine, clamábo.\n\n"
        "Psalmus 28.\n"
        "Afférte Dómino, fílii Dei: afférte Dómino fílios aríetum. Afférte "
        "Dómino glóriam et honórem, afférte Dómino glóriam nómini ejus: "
        "adoráte Dóminum in átrio sancto ejus. Vox Dómini super aquas, Deus "
        "majestátis intónuit. Glória Patri…\n\n"
        "Ant. 4. Exsultábimus in salutári tuo.\n\n"
        "Canticum Isaiæ. (Isaias 12)\n"
        "Confitébor tibi, Dómine, quóniam irátus es mihi: convérsus est furor "
        "tuus, et consolátus es me. Ecce Deus salvátor meus, fiduciáliter "
        "agam, et non timébo: quia fortitúdo mea, et laus mea Dóminus, et "
        "factus est mihi in salútem. Glória Patri…\n\n"
        "Ant. 5. Laudábo Dóminum in vita mea.\n\n"
        "Psalmus 116.\n"
        "Laudáte Dóminum, omnes gentes: laudáte eum, omnes pópuli. Quóniam "
        "confirmáta est super nos misericórdia ejus: et véritas Dómini manet "
        "in ætérnum. Glória Patri…"
    ),
)

LAUDS_TUESDAY_PSALMS = _section(
    title="Antiphons & Psalms",
    latin_title="Antiphonæ et Psalmi",
    rubric="Tuesday Lauds: Psalms 95, 42, 66, the Canticle of Ezechias, Ps 134.",
    english=(
        "Ant. 1. Sing ye to the Lord, and bless his name.\n\n"
        "Psalm 95.\n"
        "Sing ye to the Lord a new canticle: sing to the Lord, all the earth. "
        "Sing ye to the Lord and bless his name: shew forth his salvation from "
        "day to day. Declare his glory among the Gentiles: his wonders among "
        "all people. Glory be…\n\n"
        "Ant. 2. Send forth thy light and thy truth.\n\n"
        "Psalm 42.\n"
        "Judge me, O God, and distinguish my cause from the nation that is "
        "not holy: deliver me from the unjust and deceitful man. For thou art "
        "God my strength: why hast thou cast me off? and why do I go sorrowful "
        "whilst the enemy afflicteth me? Send forth thy light and thy truth: "
        "they have conducted me, and brought me unto thy holy hill. Glory be…\n\n"
        "Ant. 3. May God have mercy on us, and bless us.\n\n"
        "Psalm 66.\n"
        "May God have mercy on us, and bless us: may he cause the light of "
        "his countenance to shine upon us, and may he have mercy on us. That "
        "we may know thy way upon earth: thy salvation in all nations. Let "
        "people confess to thee, O God: let all people give praise to thee. "
        "Glory be…\n\n"
        "Ant. 4. I said: In the midst of my days I shall go.\n\n"
        "Canticle of Ezechias. (Isaias 38:10–20)\n"
        "I said: In the midst of my days I shall go to the gates of hell: I "
        "sought for the residue of my years. I said: I shall not see the Lord "
        "God in the land of the living. I shall behold man no more, nor the "
        "inhabitant of rest. The Lord is my saviour; we shall sing our psalms "
        "all the days of our life in the house of the Lord. Glory be…\n\n"
        "Ant. 5. Behold now bless ye the Lord.\n\n"
        "Psalm 134.\n"
        "Praise ye the name of the Lord: O you his servants, praise the Lord: "
        "You that stand in the house of the Lord, in the courts of the house "
        "of our God. Praise ye the Lord, for the Lord is good: sing ye to his "
        "name, for it is sweet. Glory be…"
    ),
    latin=(
        "Ant. 1. Cantáte Dómino et benedícite nómini ejus.\n\n"
        "Psalmus 95.\n"
        "Cantáte Dómino cánticum novum: cantáte Dómino, omnis terra. Cantáte "
        "Dómino, et benedícite nómini ejus: annuntiáte de die in diem "
        "salutáre ejus. Annuntiáte inter gentes glóriam ejus, in ómnibus "
        "pópulis mirabília ejus. Glória Patri…\n\n"
        "Ant. 2. Emítte lucem tuam et veritátem tuam.\n\n"
        "Psalmus 42.\n"
        "Júdica me, Deus, et discérne causam meam de gente non sancta: ab "
        "hómine iníquo et dolóso érue me. Quia tu es, Deus, fortitúdo mea: "
        "quare me repulísti? et quare tristis incédo, dum afflígit me "
        "inimícus? Emítte lucem tuam, et veritátem tuam: ipsa me deduxérunt, "
        "et adduxérunt in montem sanctum tuum. Glória Patri…\n\n"
        "Ant. 3. Deus misereátur nostri, et benedícat nobis.\n\n"
        "Psalmus 66.\n"
        "Deus misereátur nostri, et benedícat nobis: illúminet vultum suum "
        "super nos, et misereátur nostri. Ut cognoscámus in terra viam tuam, "
        "in ómnibus géntibus salutáre tuum. Confiteántur tibi pópuli, Deus: "
        "confiteántur tibi pópuli omnes. Glória Patri…\n\n"
        "Ant. 4. Ego dixi: In dimídio diérum meórum vadam.\n\n"
        "Canticum Ezechiæ. (Isaias 38:10–20)\n"
        "Ego dixi: In dimídio diérum meórum vadam ad portas ínferi: quæsívi "
        "resíduum annórum meórum. Dixi: Non vidébo Dóminum Deum in terra "
        "vivéntium. Non aspíciam hóminem ultra, et habitatórem quiétis. "
        "Dómine, salvum me fac: et psalmos nostros cantábimus cunctis diébus "
        "vitæ nostræ in domo Dómini. Glória Patri…\n\n"
        "Ant. 5. Ecce nunc benedícite Dóminum.\n\n"
        "Psalmus 134.\n"
        "Laudáte nomen Dómini, laudáte, servi, Dóminum: qui statis in domo "
        "Dómini, in átriis domus Dei nostri. Laudáte Dóminum, quia bonus "
        "Dóminus: psállite nómini ejus, quóniam suáve. Glória Patri…"
    ),
)

LAUDS_WEDNESDAY_PSALMS = _section(
    title="Antiphons & Psalms",
    latin_title="Antiphonæ et Psalmi",
    rubric="Wednesday Lauds: Psalms 96, 64, 100, the Canticle of Anna, Ps 145.",
    english=(
        "Ant. 1. The Lord hath reigned, let the earth rejoice.\n\n"
        "Psalm 96.\n"
        "The Lord hath reigned, let the earth rejoice: let many islands be "
        "glad. Clouds and darkness are round about him: justice and judgment "
        "are the establishment of his throne. A fire shall go before him, and "
        "shall burn his enemies round about. Glory be…\n\n"
        "Ant. 2. A hymn, O God, becometh thee in Sion.\n\n"
        "Psalm 64.\n"
        "A hymn, O God, becometh thee in Sion: and a vow shall be paid to thee "
        "in Jerusalem. O hear my prayer: all flesh shall come to thee. The "
        "words of the wicked have prevailed over us: and thou wilt pardon our "
        "transgressions. Glory be…\n\n"
        "Ant. 3. I will sing of mercy and judgment to thee, O Lord.\n\n"
        "Psalm 100.\n"
        "Mercy and judgment I will sing to thee, O Lord: I will sing, and I "
        "will understand in the unspotted way, when thou shalt come to me. I "
        "walked in the innocence of my heart, in the midst of my house. Glory "
        "be…\n\n"
        "Ant. 4. My heart hath rejoiced in the Lord.\n\n"
        "Canticle of Anna. (1 Kings 2:1–10)\n"
        "My heart hath rejoiced in the Lord, and my horn is exalted in my God: "
        "my mouth is enlarged over my enemies: because I have joyed in thy "
        "salvation. There is none holy as the Lord is: for there is no other "
        "beside thee, and there is none strong like our God. Glory be…\n\n"
        "Ant. 5. I will extol thee, O God my king.\n\n"
        "Psalm 145.\n"
        "Praise the Lord, O my soul, in my life I will praise the Lord: I will "
        "sing to my God as long as I shall be. Put not your trust in princes: "
        "in the children of men, in whom there is no salvation. Glory be…"
    ),
    latin=(
        "Ant. 1. Dóminus regnávit, exsúltet terra.\n\n"
        "Psalmus 96.\n"
        "Dóminus regnávit, exsúltet terra: læténtur ínsulæ multæ. Nubes et "
        "calígo in circúitu ejus: justítia et judícium corréctio sedis ejus. "
        "Ignis ante ipsum præcédet, et inflammábit in circúitu inimícos ejus. "
        "Glória Patri…\n\n"
        "Ant. 2. Te decet hymnus, Deus, in Sion.\n\n"
        "Psalmus 64.\n"
        "Te decet hymnus, Deus, in Sion: et tibi reddétur votum in Jerúsalem. "
        "Exáudi oratiónem meam: ad te omnis caro véniet. Verba iniquórum "
        "prævaluérunt super nos: et impietátibus nostris tu propitiáberis. "
        "Glória Patri…\n\n"
        "Ant. 3. Misericórdiam et judícium cantábo tibi, Dómine.\n\n"
        "Psalmus 100.\n"
        "Misericórdiam et judícium cantábo tibi, Dómine: psallam, et "
        "intélligam in via immaculáta, quando vénies ad me. Perambulábam in "
        "innocéntia cordis mei, in médio domus meæ. Glória Patri…\n\n"
        "Ant. 4. Exsultávit cor meum in Dómino.\n\n"
        "Canticum Annæ. (1 Reg 2:1–10)\n"
        "Exsultávit cor meum in Dómino, et exaltátum est cornu meum in Deo "
        "meo: dilatátum est os meum super inimícos meos: quia lætáta sum in "
        "salutári tuo. Non est sanctus, ut est Dóminus: neque enim est álius "
        "extra te, et non est fortis sicut Deus noster. Glória Patri…\n\n"
        "Ant. 5. Exaltábo te, Deus meus Rex.\n\n"
        "Psalmus 145.\n"
        "Lauda, ánima mea, Dóminum, laudábo Dóminum in vita mea: psallam Deo "
        "meo quámdiu fúero. Nolíte confídere in princípibus: in fíliis "
        "hóminum, in quibus non est salus. Glória Patri…"
    ),
)

LAUDS_THURSDAY_PSALMS = _section(
    title="Antiphons & Psalms",
    latin_title="Antiphonæ et Psalmi",
    rubric="Thursday Lauds: Psalms 97, 89, 35, the Canticle of Moses, Ps 146.",
    english=(
        "Ant. 1. Sing ye to the Lord a new canticle.\n\n"
        "Psalm 97.\n"
        "Sing ye to the Lord a new canticle: because he hath done wonderful "
        "things. His right hand hath wrought for him salvation, and his arm is "
        "holy. The Lord hath made known his salvation: he hath revealed his "
        "justice in the sight of the Gentiles. Glory be…\n\n"
        "Ant. 2. Lord, thou hast been our refuge.\n\n"
        "Psalm 89.\n"
        "Lord, thou hast been our refuge from generation to generation. Before "
        "the mountains were made, or the earth and the world was formed; from "
        "eternity and to eternity thou art God. Turn not man away to be brought "
        "low: and thou hast said: Be converted, O ye sons of men. Glory be…\n\n"
        "Ant. 3. With thee, O Lord, is the fountain of life.\n\n"
        "Psalm 35.\n"
        "The unjust hath said within himself, that he would sin: there is no "
        "fear of God before his eyes. For in his sight he hath done "
        "deceitfully, that his iniquity may be found unto hatred. O Lord, thy "
        "mercy is in heaven, and thy truth reacheth even to the clouds. Glory "
        "be…\n\n"
        "Ant. 4. Let us sing to the Lord, for he is gloriously magnified.\n\n"
        "Canticle of Moses. (Exodus 15:1–19)\n"
        "Let us sing to the Lord: for he is gloriously magnified, the horse "
        "and the rider he hath thrown into the sea. The Lord is my strength "
        "and my praise, and he is become salvation to me: he is my God and I "
        "will glorify him: the God of my father, and I will exalt him. Glory "
        "be…\n\n"
        "Ant. 5. Praise the Lord, O my soul.\n\n"
        "Psalm 146.\n"
        "Praise ye the Lord, because psalm is good: to our God be joyful and "
        "comely praise. The Lord buildeth up Jerusalem: he will gather "
        "together the dispersed of Israel. Who healeth the broken of heart, "
        "and bindeth up their bruises. Glory be…"
    ),
    latin=(
        "Ant. 1. Cantáte Dómino cánticum novum.\n\n"
        "Psalmus 97.\n"
        "Cantáte Dómino cánticum novum: quia mirabília fecit. Salvávit sibi "
        "déxtera ejus: et bráchium sanctum ejus. Notum fecit Dóminus salutáre "
        "suum: in conspéctu géntium revelávit justítiam suam. Glória Patri…\n\n"
        "Ant. 2. Dómine, refúgium factus es nobis.\n\n"
        "Psalmus 89.\n"
        "Dómine, refúgium factus es nobis: a generatióne in generatiónem. "
        "Priúsquam montes fíerent, aut formarétur terra et orbis: a sǽculo et "
        "usque in sǽculum tu es, Deus. Ne avértas hóminem in humilitátem: et "
        "dixísti: Convertímini, fílii hóminum. Glória Patri…\n\n"
        "Ant. 3. Apud te, Dómine, est fons vitæ.\n\n"
        "Psalmus 35.\n"
        "Dixit injústus ut delínquat in semetípso: non est timor Dei ante "
        "óculos ejus. Quóniam dolóse egit in conspéctu ejus: ut inveniátur "
        "iníquitas ejus ad ódium. Dómine, in cælo misericórdia tua: et véritas "
        "tua usque ad nubes. Glória Patri…\n\n"
        "Ant. 4. Cantémus Dómino: glorióse enim magnificátus est.\n\n"
        "Canticum Moysi. (Ex 15:1–19)\n"
        "Cantémus Dómino: glorióse enim magnificátus est, equum et "
        "ascensórem dejécit in mare. Fortitúdo mea, et laus mea Dóminus, et "
        "factus est mihi in salútem: iste Deus meus, et glorificábo eum: Deus "
        "patris mei, et exaltábo eum. Glória Patri…\n\n"
        "Ant. 5. Lauda, ánima mea, Dóminum.\n\n"
        "Psalmus 146.\n"
        "Laudáte Dóminum, quóniam bonus est psalmus: Deo nostro sit jucúnda, "
        "decóraque laudátio. Ædíficans Jerúsalem Dóminus: dispersiónes "
        "Israélis congregábit. Qui sanat contrítos corde: et álligat "
        "contritiónes eórum. Glória Patri…"
    ),
)

LAUDS_FRIDAY_PSALMS = _section(
    title="Antiphons & Psalms",
    latin_title="Antiphonæ et Psalmi",
    rubric=(
        "Friday Lauds: Psalm 50 (Miserere), Ps 142, Ps 84, the Canticle of "
        "Habacuc, Psalm 147."
    ),
    english=(
        "Ant. 1. Have mercy on me, O God, according to thy great mercy.\n\n"
        "Psalm 50 — Miserere.\n"
        "Have mercy on me, O God, according to thy great mercy. And according "
        "to the multitude of thy tender mercies blot out my iniquity. Wash me "
        "yet more from my iniquity, and cleanse me from my sin. For I know my "
        "iniquity, and my sin is always before me. To thee only have I sinned, "
        "and have done evil before thee: that thou mayest be justified in thy "
        "words. Create a clean heart in me, O God: and renew a right spirit "
        "within my bowels. Cast me not away from thy face; and take not thy "
        "holy spirit from me. Glory be to the Father…\n\n"
        "Ant. 2. Hear my prayer, O Lord, in thy truth.\n\n"
        "Psalm 142.\n"
        "Hear, O Lord, my prayer: give ear to my supplication in thy truth: "
        "hear me in thy justice. And enter not into judgment with thy servant: "
        "for in thy sight no man living shall be justified. For the enemy hath "
        "persecuted my soul: he hath brought down my life to the earth. Glory "
        "be…\n\n"
        "Ant. 3. How lovely are thy tabernacles, O Lord of hosts.\n\n"
        "Psalm 84.\n"
        "Lord, thou hast blessed thy land: thou hast turned away the "
        "captivity of Jacob. Thou hast forgiven the iniquity of thy people: "
        "thou hast covered all their sins. Thou hast mitigated all thy anger: "
        "thou hast turned away from the wrath of thy indignation. Glory be…\n\n"
        "Ant. 4. O Lord, I have heard thy hearing, and was afraid.\n\n"
        "Canticle of Habacuc. (Hab 3:2–19)\n"
        "O Lord, I have heard thy hearing, and was afraid. O Lord, thy work, "
        "in the midst of the years bring it to life: in the midst of the "
        "years thou shalt make it known: when thou art angry, thou wilt "
        "remember mercy. God will come from the south, and the holy one from "
        "mount Pharan. His glory covered the heavens. Glory be…\n\n"
        "Ant. 5. Praise the Lord, because psalm is good.\n\n"
        "Psalm 147.\n"
        "Praise the Lord, O Jerusalem: praise thy God, O Sion. Because he "
        "hath strengthened the bolts of thy gates, he hath blessed thy "
        "children within thee. Who hath placed peace in thy borders: and "
        "filleth thee with the fat of corn. Glory be to the Father…"
    ),
    latin=(
        "Ant. 1. Miserére mei, Deus, secúndum magnam misericórdiam tuam.\n\n"
        "Psalmus 50 — Miserére.\n"
        "Miserére mei, Deus, secúndum magnam misericórdiam tuam. Et secúndum "
        "multitúdinem miseratiónum tuárum, dele iniquitátem meam. Ámplius lava "
        "me ab iniquitáte mea: et a peccáto meo munda me. Quóniam iniquitátem "
        "meam ego cognósco: et peccátum meum contra me est semper. Tibi soli "
        "peccávi, et malum coram te feci: ut justificéris in sermónibus tuis. "
        "Cor mundum crea in me, Deus: et spíritum rectum ínnova in viscéribus "
        "meis. Ne projícias me a fácie tua: et spíritum sanctum tuum ne áuferas "
        "a me. Glória Patri…\n\n"
        "Ant. 2. Exáudi oratiónem meam, Dómine, in veritáte tua.\n\n"
        "Psalmus 142.\n"
        "Dómine, exáudi oratiónem meam: áuribus pércipe obsecratiónem meam in "
        "veritáte tua: exáudi me in tua justítia. Et non intres in judícium "
        "cum servo tuo: quia non justificábitur in conspéctu tuo omnis vivens. "
        "Quia persecútus est inimícus ánimam meam: humiliávit in terra vitam "
        "meam. Glória Patri…\n\n"
        "Ant. 3. Quam dilécta tabernácula tua, Dómine virtútum.\n\n"
        "Psalmus 84.\n"
        "Benedixísti, Dómine, terram tuam: avertísti captivitátem Jacob. "
        "Remisísti iniquitátem plebis tuæ: operuísti ómnia peccáta eórum. "
        "Mitigásti omnem iram tuam: avertísti ab ira indignatiónis tuæ. "
        "Glória Patri…\n\n"
        "Ant. 4. Dómine, audívi audítum tuum, et tímui.\n\n"
        "Canticum Habacuc. (Hab 3:2–19)\n"
        "Dómine, audívi audítum tuum, et tímui. Dómine, opus tuum, in médio "
        "annórum vivífica illud: in médio annórum notum fácies: cum irátus "
        "fúeris, misericórdiæ recordáberis. Deus ab Austro véniet, et sanctus "
        "de monte Pharan. Opéruit cælos glória ejus. Glória Patri…\n\n"
        "Ant. 5. Laudáte Dóminum, quóniam bonus est psalmus.\n\n"
        "Psalmus 147.\n"
        "Lauda, Jerúsalem, Dóminum: lauda Deum tuum, Sion. Quóniam confortávit "
        "seras portárum tuárum: benedíxit fíliis tuis in te. Qui pósuit fines "
        "tuos pacem: et ádipe fruménti sátiat te. Glória Patri…"
    ),
)

LAUDS_SATURDAY_PSALMS = _section(
    title="Antiphons & Psalms",
    latin_title="Antiphonæ et Psalmi",
    rubric=(
        "Saturday Lauds: Psalm 91, Ps 8, Ps 75, the Canticle of Moses "
        "(Deut 32), Psalm 148."
    ),
    english=(
        "Ant. 1. It is good to give praise to the Lord.\n\n"
        "Psalm 91.\n"
        "It is good to give praise to the Lord: and to sing to thy name, O "
        "most High. To shew forth thy mercy in the morning, and thy truth in "
        "the night: upon an instrument of ten strings, upon the psaltery: "
        "with a canticle upon the harp. For thou hast given me, O Lord, a "
        "delight in thy doings. Glory be…\n\n"
        "Ant. 2. O Lord, our Lord, how admirable is thy name.\n\n"
        "Psalm 8.\n"
        "O Lord, our Lord, how admirable is thy name in the whole earth! For "
        "thy magnificence is elevated above the heavens. Out of the mouth of "
        "infants and of sucklings thou hast perfected praise, because of thy "
        "enemies, that thou mayst destroy the enemy and the avenger. Glory "
        "be…\n\n"
        "Ant. 3. In Judea God is known: his name is great in Israel.\n\n"
        "Psalm 75.\n"
        "In Judea God is known: his name is great in Israel. And his place is "
        "in peace: and his abode in Sion. There hath he broken the powers of "
        "bows, the shield, the sword, and the battle. Thou enlightenest "
        "wonderfully from the everlasting hills. Glory be…\n\n"
        "Ant. 4. Give ye glory to our God.\n\n"
        "Canticle of Moses. (Deut 32:1–43)\n"
        "Hear, O ye heavens, the things I speak, let the earth give ear to the "
        "words of my mouth. Let my doctrine gather as the rain, let my speech "
        "distil as the dew. Because I will invoke the name of the Lord: give "
        "ye magnificence to our God. The works of God are perfect, and all "
        "his ways are judgments: God is faithful and without any iniquity, "
        "he is just and right. Glory be…\n\n"
        "Ant. 5. Praise ye the Lord from the heavens.\n\n"
        "Psalm 148.\n"
        "Praise ye the Lord from the heavens: praise ye him in the high "
        "places. Praise ye him, all his angels: praise him, all his hosts. "
        "Praise ye him, O sun and moon: praise him, all ye stars and light. "
        "Praise ye him, ye heavens of heavens: and let all the waters that "
        "are above the heavens praise the name of the Lord. Glory be to the "
        "Father…"
    ),
    latin=(
        "Ant. 1. Bonum est confitéri Dómino.\n\n"
        "Psalmus 91.\n"
        "Bonum est confitéri Dómino: et psállere nómini tuo, Altíssime. Ad "
        "annuntiándum mane misericórdiam tuam: et veritátem tuam per noctem. "
        "In decachórdo, psaltério: cum cántico, in cíthara. Quia delectásti "
        "me, Dómine, in factúra tua. Glória Patri…\n\n"
        "Ant. 2. Dómine Dóminus noster, quam admirábile est nomen tuum.\n\n"
        "Psalmus 8.\n"
        "Dómine, Dóminus noster, quam admirábile est nomen tuum in univérsa "
        "terra! Quóniam eleváta est magnificéntia tua, super cælos. Ex ore "
        "infántium et lacténtium perfecísti laudem propter inimícos tuos, ut "
        "déstruas inimícum et ultórem. Glória Patri…\n\n"
        "Ant. 3. Notus in Judǽa Deus: in Israël magnum nomen ejus.\n\n"
        "Psalmus 75.\n"
        "Notus in Judǽa Deus: in Israël magnum nomen ejus. Et factus est in "
        "pace locus ejus: et habitátio ejus in Sion. Ibi confrégit poténtias "
        "árcuum, scutum, gládium, et bellum. Illúminans tu mirabíliter a "
        "móntibus ætérnis. Glória Patri…\n\n"
        "Ant. 4. Date magnificéntiam Deo nostro.\n\n"
        "Canticum Moysi. (Deut 32:1–43)\n"
        "Audíte, cæli, quæ loquor: áudiat terra verba oris mei. Concréscat ut "
        "plúvia doctrína mea, fluat ut ros elóquium meum. Quia nomen Dómini "
        "invocábo: date magnificéntiam Deo nostro. Dei perfécta sunt ópera, "
        "et omnes viæ ejus judícia: Deus fidélis, et absque ulla iniquitáte, "
        "justus et rectus. Glória Patri…\n\n"
        "Ant. 5. Laudáte Dóminum de cælis.\n\n"
        "Psalmus 148.\n"
        "Laudáte Dóminum de cælis: laudáte eum in excélsis. Laudáte eum, omnes "
        "ángeli ejus: laudáte eum, omnes virtútes ejus. Laudáte eum, sol et "
        "luna: laudáte eum, omnes stellæ et lumen. Laudáte eum, cæli "
        "cælórum: et aquæ omnes, quæ super cælos sunt, laudent nomen Dómini. "
        "Glória Patri…"
    ),
)


# --- Lauds: Capitulum, Hymn, Versicle (largely fixed in ferial use) ---

LAUDS_CAPITULUM = _section(
    title="Little Chapter",
    latin_title="Capítulum",
    rubric="Read by the officiant. The response is sung by all.",
    english=(
        "Brethren: From the rising of the sun even to the going down, the "
        "name of the Lord is worthy of praise. The Lord is high above all "
        "nations, and his glory above the heavens. (Romans 13:12)\n\n"
        "R. Thanks be to God."
    ),
    latin=(
        "Fratres: A solis ortu usque ad occásum, laudábile nomen Dómini. "
        "Excélsus super omnes gentes Dóminus, et super cælos glória ejus. "
        "(Rom 13:12)\n\n"
        "R. Deo grátias."
    ),
)

LAUDS_HYMN = _section(
    title="Hymn — Æterne rerum Conditor",
    latin_title="Hymnus",
    rubric="The ancient Ambrosian morning hymn, attributed to St. Ambrose.",
    english=(
        "Eternal Maker of the world,\n"
        "Who rul'st both day and night,\n"
        "Granting to time its varied course\n"
        "That weariness may find respite:\n\n"
        "Now sounds the herald of the day,\n"
        "Watchful through hours of deepest night,\n"
        "A wayfarer's nocturnal light\n"
        "That parts the watches of the night.\n\n"
        "Roused by his call the day-star rises,\n"
        "And bids the gloom of darkness flee:\n"
        "Now every wandering spirit ceases\n"
        "To work its mischief secretly.\n\n"
        "The sailor heartens at the sound,\n"
        "The tempests of the sea grow calm;\n"
        "The Rock of holy Church arose\n"
        "And, at the cock-crow, washed his shame.\n\n"
        "To Christ, our King most merciful,\n"
        "And to the Father, glory be,\n"
        "With Holy Ghost, the Paraclete,\n"
        "Now and through all eternity. Amen."
    ),
    latin=(
        "Ætérne rerum Cónditor,\n"
        "Noctem diémque qui regis,\n"
        "Et témporum das témpora,\n"
        "Ut álleves fastídium.\n\n"
        "Præco diéi jam sonat,\n"
        "Noctis profúndæ pérvigil,\n"
        "Noctúrna lux viántibus,\n"
        "A nocte noctem ségregans.\n\n"
        "Hoc excitátus Lúcifer\n"
        "Solvit polum calígine:\n"
        "Hoc omnis errórum chorus\n"
        "Vias nocéndi déserit.\n\n"
        "Hoc nauta vires cólligit,\n"
        "Pontíque mitéscunt freta:\n"
        "Hoc, ipsa petra Ecclésiæ,\n"
        "Canénte, culpam díluit.\n\n"
        "Jesu, labántes réspice,\n"
        "Et nos vidéndo córrige:\n"
        "Si réspicis, lapsi stabunt,\n"
        "Fletúque culpa sólvitur. Amen."
    ),
)

LAUDS_VERSICLE = _section(
    title="Versicle",
    latin_title="Versus",
    english=(
        "V. The Lord shall fill thy mouth with laughter.\n"
        "R. And thy lips with rejoicing."
    ),
    latin=(
        "V. Replébit os tuum rísu.\n"
        "R. Et lábia tua jubílo."
    ),
)

LAUDS_BENEDICTUS = _section(
    title="Canticle of Zachary — Benedictus",
    latin_title="Canticum Zachariæ",
    rubric=(
        "All stand and make the Sign of the Cross at the beginning. The "
        "antiphon (varies by season; below is a ferial example) is said "
        "before and after the canticle."
    ),
    english=(
        "Ant. Blessed be the Lord God of Israel: for he hath visited and "
        "wrought the redemption of his people.\n\n"
        "Blessed be the Lord God of Israel; * because he hath visited and "
        "wrought the redemption of his people:\n"
        "And hath raised up an horn of salvation to us, * in the house of "
        "David his servant:\n"
        "As he spoke by the mouth of his holy prophets, * who are from the "
        "beginning:\n"
        "Salvation from our enemies, * and from the hand of all that hate us:\n"
        "To perform mercy to our fathers, * and to remember his holy testament,\n"
        "The oath, which he swore to Abraham our father, * that he would "
        "grant to us,\n"
        "That being delivered from the hand of our enemies, * we may serve "
        "him without fear,\n"
        "In holiness and justice before him, * all our days.\n"
        "And thou, child, shalt be called the prophet of the Highest: * for "
        "thou shalt go before the face of the Lord to prepare his ways:\n"
        "To give knowledge of salvation to his people, * unto the remission "
        "of their sins:\n"
        "Through the bowels of the mercy of our God, * in which the Orient "
        "from on high hath visited us:\n"
        "To enlighten them that sit in darkness, and in the shadow of death: "
        "* to direct our feet into the way of peace.\n\n"
        "Glory be to the Father, and to the Son, * and to the Holy Ghost.\n"
        "As it was in the beginning, is now, and ever shall be, * world "
        "without end. Amen.\n\n"
        "Ant. Blessed be the Lord God of Israel: for he hath visited and "
        "wrought the redemption of his people."
    ),
    latin=(
        "Ant. Benedíctus Dóminus Deus Israël: quia visitávit et fecit "
        "redemptiónem plebis suæ.\n\n"
        "Benedíctus Dóminus Deus Israël: * quia visitávit, et fecit "
        "redemptiónem plebis suæ:\n"
        "Et eréxit cornu salútis nobis: * in domo David, púeri sui.\n"
        "Sicut locútus est per os sanctórum, * qui a sǽculo sunt, "
        "prophetárum ejus:\n"
        "Salútem ex inimícis nostris, * et de manu ómnium, qui odérunt nos:\n"
        "Ad faciéndam misericórdiam cum pátribus nostris: * et memorári "
        "testaménti sui sancti.\n"
        "Jusjurándum, quod jurávit ad Ábraham patrem nostrum, * datúrum se "
        "nobis:\n"
        "Ut sine timóre, de manu inimicórum nostrórum liberáti, * "
        "serviámus illi.\n"
        "In sanctitáte, et justítia coram ipso, * ómnibus diébus nostris.\n"
        "Et tu, puer, Prophéta Altíssimi vocáberis: * præíbis enim ante "
        "fáciem Dómini, paráre vias ejus:\n"
        "Ad dandam sciéntiam salútis plebi ejus: * in remissiónem peccatórum "
        "eórum:\n"
        "Per víscera misericórdiæ Dei nostri: * in quibus visitávit nos, "
        "óriens ex alto:\n"
        "Illumináre his, qui in ténebris, et in umbra mortis sedent: * ad "
        "dirigéndos pedes nostros in viam pacis.\n\n"
        "Glória Patri, et Fílio, * et Spirítui Sancto.\n"
        "Sicut erat in princípio, et nunc, et semper, * et in sǽcula "
        "sæculórum. Amen.\n\n"
        "Ant. Benedíctus Dóminus Deus Israël: quia visitávit et fecit "
        "redemptiónem plebis suæ."
    ),
)

LAUDS_COLLECT = _section(
    title="Preces & Collect",
    latin_title="Preces et Orátio",
    rubric=(
        "After the Pater Noster (above), the officiant prays the Collect of "
        "the day. On ferial days outside privileged seasons, the following "
        "general Collect is used."
    ),
    english=(
        "V. The Lord be with you.\n"
        "R. And with thy spirit.\n\n"
        "Let us pray. — O Lord, our God, by whose appointment the silence "
        "of night and the labour of day succeed each other: we humbly beseech "
        "thy boundless mercy that, what we are mindful to sing in this "
        "morning's praise, we may carry out in this day's work. Through our "
        "Lord Jesus Christ thy Son, who liveth and reigneth with thee in the "
        "unity of the Holy Ghost, God, world without end. R. Amen."
    ),
    latin=(
        "V. Dóminus vobíscum.\n"
        "R. Et cum spíritu tuo.\n\n"
        "Orémus. — Dómine, Deus noster, cujus dispositióne noctis siléntium "
        "et diéi succédit labor: tuam súpplices deprecámur cleméntiam, ut "
        "quod hujus matutínæ laudis prosequímur cánticis, totíus diéi sequátur "
        "in ópere. Per Dóminum nostrum Jesum Christum Fílium tuum, qui tecum "
        "vivit et regnat in unitáte Spíritus Sancti Deus, per ómnia sǽcula "
        "sæculórum. R. Amen."
    ),
)


def _lauds_day(psalms_section: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Assemble a complete Lauds office in canonical breviary order."""
    return [
        DEUS_IN_ADJUTORIUM,
        psalms_section,
        LAUDS_CAPITULUM,
        LAUDS_HYMN,
        LAUDS_VERSICLE,
        LAUDS_BENEDICTUS,
        PATER_NOSTER,
        LAUDS_COLLECT,
        DISMISSAL_BENEDICAMUS,
    ]


# ===========================================================================
# VESPERS — Ad Vesperas (Evening Prayer)
# ===========================================================================

VESPERS_SUNDAY_PSALMS = _section(
    title="Antiphons & Psalms",
    latin_title="Antiphonæ et Psalmi",
    rubric="Sunday Vespers: Psalms 109, 110, 111, 112, 113.",
    english=(
        "Ant. 1. The Lord said to my Lord: Sit thou at my right hand.\n\n"
        "Psalm 109 — Dixit Dominus.\n"
        "The Lord said to my Lord: Sit thou at my right hand: until I make "
        "thy enemies thy footstool. The Lord will send forth the sceptre of "
        "thy power out of Sion: rule thou in the midst of thy enemies. With "
        "thee is the principality in the day of thy strength: in the "
        "brightness of the saints, from the womb before the day star I begot "
        "thee. Glory be…\n\n"
        "Ant. 2. Great are the works of the Lord.\n\n"
        "Psalm 110.\n"
        "I will praise thee, O Lord, with my whole heart; in the council of "
        "the just, and in the congregation. Great are the works of the Lord: "
        "sought out according to all his wills. His work is praise and "
        "magnificence: and his justice continueth for ever and ever. He hath "
        "made a remembrance of his wonderful works, being a merciful and "
        "gracious Lord. Glory be…\n\n"
        "Ant. 3. Blessed is the man that feareth the Lord.\n\n"
        "Psalm 111.\n"
        "Blessed is the man that feareth the Lord: he shall delight "
        "exceedingly in his commandments. His seed shall be mighty upon "
        "earth: the generation of the righteous shall be blessed. Glory and "
        "wealth shall be in his house: and his justice remaineth for ever "
        "and ever. To the righteous a light is risen up in darkness. Glory "
        "be…\n\n"
        "Ant. 4. Praise the Lord, ye children.\n\n"
        "Psalm 112.\n"
        "Praise the Lord, ye children: praise ye the name of the Lord. "
        "Blessed be the name of the Lord, from henceforth now and for ever. "
        "From the rising of the sun unto the going down of the same, the "
        "name of the Lord is worthy of praise. The Lord is high above all "
        "nations: and his glory above the heavens. Glory be…\n\n"
        "Ant. 5. Out of Egypt did Israel come forth, alleluia.\n\n"
        "Psalm 113.\n"
        "When Israel went out of Egypt, the house of Jacob from a barbarous "
        "people: Judea was made his sanctuary, Israel his dominion. The sea "
        "saw and fled: Jordan was turned back. The mountains skipped like "
        "rams: and the hills like the lambs of the flock. Glory be to the "
        "Father…"
    ),
    latin=(
        "Ant. 1. Dixit Dóminus Dómino meo: Sede a dextris meis.\n\n"
        "Psalmus 109 — Dixit Dóminus.\n"
        "Dixit Dóminus Dómino meo: Sede a dextris meis: donec ponam inimícos "
        "tuos, scabéllum pedum tuórum. Virgam virtútis tuæ emíttet Dóminus "
        "ex Sion: domináre in médio inimicórum tuórum. Tecum princípium in "
        "die virtútis tuæ in splendóribus sanctórum: ex útero ante lucíferum "
        "génui te. Glória Patri…\n\n"
        "Ant. 2. Magna ópera Dómini.\n\n"
        "Psalmus 110.\n"
        "Confitébor tibi, Dómine, in toto corde meo: in consílio justórum, "
        "et congregatióne. Magna ópera Dómini: exquisíta in omnes "
        "voluntátes ejus. Conféssio et magnificéntia opus ejus: et justítia "
        "ejus manet in sǽculum sǽculi. Memóriam fecit mirabílium suórum, "
        "miséricors et miserátor Dóminus. Glória Patri…\n\n"
        "Ant. 3. Beátus vir, qui timet Dóminum.\n\n"
        "Psalmus 111.\n"
        "Beátus vir, qui timet Dóminum: in mandátis ejus volet nimis. Potens "
        "in terra erit semen ejus: generátio rectórum benedicétur. Glória "
        "et divítiæ in domo ejus: et justítia ejus manet in sǽculum sǽculi. "
        "Exórtum est in ténebris lumen rectis. Glória Patri…\n\n"
        "Ant. 4. Laudáte, púeri, Dóminum.\n\n"
        "Psalmus 112.\n"
        "Laudáte, púeri, Dóminum: laudáte nomen Dómini. Sit nomen Dómini "
        "benedíctum, ex hoc nunc, et usque in sǽculum. A solis ortu usque "
        "ad occásum, laudábile nomen Dómini. Excélsus super omnes gentes "
        "Dóminus, et super cælos glória ejus. Glória Patri…\n\n"
        "Ant. 5. In éxitu Israël ex Ægýpto, allelúja.\n\n"
        "Psalmus 113.\n"
        "In éxitu Israël de Ægýpto, domus Jacob de pópulo bárbaro: facta est "
        "Judǽa sanctificátio ejus, Israël potéstas ejus. Mare vidit, et "
        "fugit: Jordánis convérsus est retrórsum. Montes exsultavérunt ut "
        "aríetes: et colles sicut agni óvium. Glória Patri…"
    ),
)

VESPERS_MONDAY_PSALMS = _section(
    title="Antiphons & Psalms",
    latin_title="Antiphonæ et Psalmi",
    rubric="Monday Vespers: Psalms 114, 115, 119, 120, 121.",
    english=(
        "Ant. 1. I have loved, because the Lord will hear the voice of my "
        "prayer.\n\n"
        "Psalm 114.\n"
        "I have loved, because the Lord will hear the voice of my prayer. "
        "Because he hath inclined his ear unto me: and in my days I will call "
        "upon him. The sorrows of death have compassed me: and the perils of "
        "hell have found me. I met with trouble and sorrow: and I called upon "
        "the name of the Lord. O Lord, deliver my soul. Glory be…\n\n"
        "Ant. 2. I will walk before the Lord in the land of the living.\n\n"
        "Psalm 115.\n"
        "I have believed, therefore have I spoken; but I have been humbled "
        "exceedingly. I said in my excess: Every man is a liar. What shall I "
        "render to the Lord, for all the things that he hath rendered to me? "
        "I will take the chalice of salvation; and I will call upon the name "
        "of the Lord. Glory be…\n\n"
        "Ant. 3. To thee have I lifted up my eyes.\n\n"
        "Psalm 119.\n"
        "In my trouble I cried to the Lord: and he heard me. O Lord, deliver "
        "my soul from wicked lips, and a deceitful tongue. What shall be given "
        "to thee, or what shall be added to thee, to a deceitful tongue? The "
        "sharp arrows of the mighty, with coals that lay waste. Glory be…\n\n"
        "Ant. 4. The Lord is thy keeper.\n\n"
        "Psalm 120.\n"
        "I have lifted up my eyes to the mountains, from whence help shall "
        "come to me. My help is from the Lord, who made heaven and earth. May "
        "he not suffer thy foot to be moved: neither let him slumber that "
        "keepeth thee. Behold he shall neither slumber nor sleep, that "
        "keepeth Israel. Glory be…\n\n"
        "Ant. 5. We will go up with joy into the house of the Lord.\n\n"
        "Psalm 121.\n"
        "I rejoiced at the things that were said to me: We shall go into the "
        "house of the Lord. Our feet were standing in thy courts, O "
        "Jerusalem. Jerusalem, which is built as a city, which is compact "
        "together. For thither did the tribes go up, the tribes of the Lord: "
        "the testimony of Israel, to praise the name of the Lord. Glory be…"
    ),
    latin=(
        "Ant. 1. Diléxi, quóniam exáudiet Dóminus vocem oratiónis meæ.\n\n"
        "Psalmus 114.\n"
        "Diléxi, quóniam exáudiet Dóminus vocem oratiónis meæ. Quia inclinávit "
        "aurem suam mihi: et in diébus meis invocábo. Circumdedérunt me "
        "dolóres mortis: et perícula inférni invenérunt me. Tribulatiónem et "
        "dolórem invéni: et nomen Dómini invocávi. O Dómine, líbera ánimam "
        "meam. Glória Patri…\n\n"
        "Ant. 2. Placébo Dómino in regióne vivórum.\n\n"
        "Psalmus 115.\n"
        "Crédidi, propter quod locútus sum: ego autem humiliátus sum nimis. "
        "Ego dixi in excéssu meo: Omnis homo mendax. Quid retríbuam Dómino, "
        "pro ómnibus quæ retríbuit mihi? Cálicem salutáris accípiam: et "
        "nomen Dómini invocábo. Glória Patri…\n\n"
        "Ant. 3. Ad te levávi óculos meos.\n\n"
        "Psalmus 119.\n"
        "Ad Dóminum, cum tribulárer, clamávi: et exaudívit me. Dómine, líbera "
        "ánimam meam a lábiis iníquis, et a lingua dolósa. Quid detur tibi, "
        "aut quid apponátur tibi, ad linguam dolósam? Sagíttæ poténtis "
        "acútæ, cum carbónibus desolatóriis. Glória Patri…\n\n"
        "Ant. 4. Dóminus custódit te.\n\n"
        "Psalmus 120.\n"
        "Levávi óculos meos in montes, unde véniet auxílium mihi. Auxílium "
        "meum a Dómino, qui fecit cælum et terram. Non det in commotiónem "
        "pedem tuum: neque dormítet qui custódit te. Ecce non dormitábit "
        "neque dórmiet, qui custódit Israël. Glória Patri…\n\n"
        "Ant. 5. In domum Dómini lætántes íbimus.\n\n"
        "Psalmus 121.\n"
        "Lætátus sum in his quæ dicta sunt mihi: In domum Dómini íbimus. "
        "Stantes erant pedes nostri, in átriis tuis, Jerúsalem. Jerúsalem, "
        "quæ ædificátur ut cívitas: cujus participátio ejus in idípsum. Illuc "
        "enim ascendérunt tribus, tribus Dómini: testimónium Israël, ad "
        "confiténdum nómini Dómini. Glória Patri…"
    ),
)

VESPERS_TUESDAY_PSALMS = _section(
    title="Antiphons & Psalms",
    latin_title="Antiphonæ et Psalmi",
    rubric="Tuesday Vespers: Psalms 122, 123, 124, 125, 126.",
    english=(
        "Ant. 1. To thee have I lifted up my eyes, who dwellest in heaven.\n\n"
        "Psalm 122.\n"
        "To thee have I lifted up my eyes, who dwellest in heaven. Behold "
        "as the eyes of servants are on the hands of their masters. As the "
        "eyes of the handmaid are on the hands of her mistress: so are our "
        "eyes unto the Lord our God, until he have mercy on us. Glory be…\n\n"
        "Ant. 2. Our help is in the name of the Lord.\n\n"
        "Psalm 123.\n"
        "If it had not been that the Lord was with us, let Israel now say: "
        "If it had not been that the Lord was with us, when men rose up "
        "against us, perhaps they had swallowed us up alive. When their fury "
        "was enkindled against us, perhaps the waters had swallowed us up. "
        "Blessed be the Lord, who hath not given us to be a prey to their "
        "teeth. Glory be…\n\n"
        "Ant. 3. The Lord is round about his people.\n\n"
        "Psalm 124.\n"
        "They that trust in the Lord shall be as mount Sion: he shall not "
        "be moved for ever that dwelleth in Jerusalem. Mountains are round "
        "about it: so the Lord is round about his people, from henceforth "
        "now and for ever. Glory be…\n\n"
        "Ant. 4. The Lord hath done great things for us.\n\n"
        "Psalm 125.\n"
        "When the Lord brought back the captivity of Sion, we became like "
        "men comforted. Then was our mouth filled with gladness; and our "
        "tongue with joy. Then shall they say among the Gentiles: The Lord "
        "hath done great things for them. The Lord hath done great things "
        "for us: we are become joyful. Glory be…\n\n"
        "Ant. 5. Unless the Lord build the house.\n\n"
        "Psalm 126.\n"
        "Unless the Lord build the house, they labour in vain that build it. "
        "Unless the Lord keep the city, he watcheth in vain that keepeth it. "
        "It is vain for you to rise before light, rise ye after you have "
        "sitten: you that eat the bread of sorrow. Glory be…"
    ),
    latin=(
        "Ant. 1. Ad te levávi óculos meos, qui hábitas in cælis.\n\n"
        "Psalmus 122.\n"
        "Ad te levávi óculos meos, qui hábitas in cælis. Ecce sicut óculi "
        "servórum, in mánibus dominórum suórum: Sicut óculi ancíllæ in "
        "mánibus dóminæ suæ: ita óculi nostri ad Dóminum Deum nostrum, donec "
        "misereátur nostri. Glória Patri…\n\n"
        "Ant. 2. Adjutórium nostrum in nómine Dómini.\n\n"
        "Psalmus 123.\n"
        "Nisi quia Dóminus erat in nobis, dicat nunc Israël: nisi quia "
        "Dóminus erat in nobis, cum exsúrgerent hómines in nos, forte vivos "
        "deglutíssent nos. Cum irascerétur furor eórum in nos, fórsitan aqua "
        "absorbuísset nos. Benedíctus Dóminus, qui non dedit nos in "
        "captiónem déntibus eórum. Glória Patri…\n\n"
        "Ant. 3. Dóminus in circúitu pópuli sui.\n\n"
        "Psalmus 124.\n"
        "Qui confídunt in Dómino, sicut mons Sion: non commovébitur in "
        "ætérnum, qui hábitat in Jerúsalem. Montes in circúitu ejus: et "
        "Dóminus in circúitu pópuli sui, ex hoc nunc et usque in sǽculum. "
        "Glória Patri…\n\n"
        "Ant. 4. Magnificávit Dóminus fácere nobíscum.\n\n"
        "Psalmus 125.\n"
        "In converténdo Dóminus captivitátem Sion, facti sumus sicut "
        "consoláti. Tunc replétum est gáudio os nostrum: et lingua nostra "
        "exsultatióne. Tunc dicent inter gentes: Magnificávit Dóminus fácere "
        "cum eis. Magnificávit Dóminus fácere nobíscum: facti sumus "
        "lætántes. Glória Patri…\n\n"
        "Ant. 5. Nisi Dóminus ædificáverit domum.\n\n"
        "Psalmus 126.\n"
        "Nisi Dóminus ædificáverit domum, in vanum laboravérunt qui "
        "ædíficant eam. Nisi Dóminus custodíerit civitátem, frustra vígilat "
        "qui custódit eam. Vanum est vobis ante lucem súrgere: súrgite "
        "postquam sedéritis, qui manducátis panem dolóris. Glória Patri…"
    ),
)

VESPERS_WEDNESDAY_PSALMS = _section(
    title="Antiphons & Psalms",
    latin_title="Antiphonæ et Psalmi",
    rubric="Wednesday Vespers: Psalms 127, 128, 129, 130, 131.",
    english=(
        "Ant. 1. Blessed are all they that fear the Lord.\n\n"
        "Psalm 127.\n"
        "Blessed are all they that fear the Lord: that walk in his ways. For "
        "thou shalt eat the labours of thy hands: blessed art thou, and it "
        "shall be well with thee. Thy wife as a fruitful vine, on the sides "
        "of thy house. Thy children as olive plants, round about thy table. "
        "Behold, thus shall the man be blessed that feareth the Lord. Glory "
        "be…\n\n"
        "Ant. 2. Many times have they fought against me from my youth.\n\n"
        "Psalm 128.\n"
        "Often have they fought against me from my youth, let Israel now "
        "say. Often have they fought against me from my youth: but they "
        "could not prevail over me. The wicked have wrought upon my back: "
        "they have lengthened their iniquity. The Lord who is just will cut "
        "the necks of sinners. Glory be…\n\n"
        "Ant. 3. Out of the depths I have cried to thee, O Lord.\n\n"
        "Psalm 129 — De profundis.\n"
        "Out of the depths I have cried to thee, O Lord: Lord, hear my voice. "
        "Let thy ears be attentive to the voice of my supplication. If thou, "
        "O Lord, wilt mark iniquities: Lord, who shall stand it? For with "
        "thee there is merciful forgiveness: and by reason of thy law, I "
        "have waited for thee, O Lord. Glory be…\n\n"
        "Ant. 4. Hope in the Lord from henceforth now and for ever.\n\n"
        "Psalm 130.\n"
        "Lord, my heart is not exalted: nor are my eyes lofty. Neither have "
        "I walked in great matters, nor in wonderful things above me. If I "
        "was not humbly minded, but exalted my soul: as a child that is "
        "weaned is towards his mother, so reward in my soul. Glory be…\n\n"
        "Ant. 5. Remember, O Lord, David.\n\n"
        "Psalm 131.\n"
        "O Lord, remember David, and all his meekness. How he swore to the "
        "Lord, he vowed a vow to the God of Jacob: If I shall enter into the "
        "tabernacle of my house: if I shall go up into the bed wherein I lie. "
        "If I shall give sleep to my eyes, or slumber to my eyelids, until I "
        "find out a place for the Lord. Glory be…"
    ),
    latin=(
        "Ant. 1. Beáti omnes qui timent Dóminum.\n\n"
        "Psalmus 127.\n"
        "Beáti omnes qui timent Dóminum: qui ámbulant in viis ejus. Labóres "
        "mánuum tuárum quia manducábis: beátus es, et bene tibi erit. Uxor "
        "tua sicut vitis abúndans, in latéribus domus tuæ. Fílii tui sicut "
        "novéllæ olivárum, in circúitu mensæ tuæ. Ecce sic benedicétur homo "
        "qui timet Dóminum. Glória Patri…\n\n"
        "Ant. 2. Sæpe expugnavérunt me a juventúte mea.\n\n"
        "Psalmus 128.\n"
        "Sæpe expugnavérunt me a juventúte mea, dicat nunc Israël. Sæpe "
        "expugnavérunt me a juventúte mea: étenim non potuérunt mihi. Supra "
        "dorsum meum fabricavérunt peccatóres: prolongavérunt iniquitátem "
        "suam. Dóminus justus concídit cervíces peccatórum. Glória Patri…\n\n"
        "Ant. 3. De profúndis clamávi ad te, Dómine.\n\n"
        "Psalmus 129 — De profúndis.\n"
        "De profúndis clamávi ad te, Dómine: Dómine, exáudi vocem meam. Fiant "
        "aures tuæ intendéntes, in vocem deprecatiónis meæ. Si iniquitátes "
        "observáveris, Dómine: Dómine, quis sustinébit? Quia apud te "
        "propitiátio est: et propter legem tuam sustínui te, Dómine. Glória "
        "Patri…\n\n"
        "Ant. 4. Speret Israël in Dómino, ex hoc nunc et usque in sǽculum.\n\n"
        "Psalmus 130.\n"
        "Dómine, non est exaltátum cor meum: neque eláti sunt óculi mei. "
        "Neque ambulávi in magnis: neque in mirabílibus super me. Si non "
        "humíliter sentiébam: sed exaltávi ánimam meam: sicut ablactátus est "
        "super matre sua, ita retribútio in ánima mea. Glória Patri…\n\n"
        "Ant. 5. Meménto, Dómine, David.\n\n"
        "Psalmus 131.\n"
        "Meménto, Dómine, David, et omnis mansuetúdinis ejus. Sicut jurávit "
        "Dómino, votum vovit Deo Jacob: Si introíero in tabernáculum domus "
        "meæ, si ascéndero in lectum strati mei. Si dédero somnum óculis "
        "meis, et pálpebris meis dormitatiónem, donec invéniam locum "
        "Dómino. Glória Patri…"
    ),
)

VESPERS_THURSDAY_PSALMS = _section(
    title="Antiphons & Psalms",
    latin_title="Antiphonæ et Psalmi",
    rubric="Thursday Vespers: Psalms 132, 135, 136, 138, 139.",
    english=(
        "Ant. 1. Behold how good and how pleasant it is for brethren to dwell "
        "together in unity.\n\n"
        "Psalm 132.\n"
        "Behold how good and how pleasant it is for brethren to dwell "
        "together in unity: Like the precious ointment on the head, that ran "
        "down upon the beard, the beard of Aaron, which ran down to the skirt "
        "of his garment: As the dew of Hermon, which descendeth upon mount "
        "Sion. For there the Lord hath commanded blessing, and life for "
        "evermore. Glory be…\n\n"
        "Ant. 2. Praise the Lord, for he is good.\n\n"
        "Psalm 135.\n"
        "Praise the Lord, for he is good: for his mercy endureth for ever. "
        "Praise ye the God of gods: for his mercy endureth for ever. Praise "
        "ye the Lord of lords: for his mercy endureth for ever. Who alone "
        "doth great wonders: for his mercy endureth for ever. Who made the "
        "heavens in understanding: for his mercy endureth for ever. Glory "
        "be…\n\n"
        "Ant. 3. Upon the rivers of Babylon, there we sat and wept.\n\n"
        "Psalm 136.\n"
        "Upon the rivers of Babylon, there we sat and wept: when we "
        "remembered Sion: On the willows in the midst thereof we hung up "
        "our instruments. For there they that led us into captivity required "
        "of us the words of songs. And they that carried us away, said: Sing "
        "ye to us a hymn of the songs of Sion. How shall we sing the song of "
        "the Lord in a strange land? Glory be…\n\n"
        "Ant. 4. I will praise thee, O Lord, with my whole heart.\n\n"
        "Psalm 138.\n"
        "Lord, thou hast proved me, and known me: Thou hast known my sitting "
        "down, and my rising up. Thou hast understood my thoughts afar off: "
        "my path and my line thou hast searched out. And thou hast foreseen "
        "all my ways: for there is no speech in my tongue. Behold, O Lord, "
        "thou hast known all things, the last and those of old. Glory be…\n\n"
        "Ant. 5. Deliver me, O Lord, from the evil man.\n\n"
        "Psalm 139.\n"
        "Deliver me, O Lord, from the evil man: rescue me from the unjust "
        "man. Who have devised iniquities in their hearts: all the day long "
        "they designed battles. They have sharpened their tongues like a "
        "serpent: the venom of asps is under their lips. Glory be…"
    ),
    latin=(
        "Ant. 1. Ecce quam bonum et quam jucúndum, habitáre fratres in "
        "unum.\n\n"
        "Psalmus 132.\n"
        "Ecce quam bonum, et quam jucúndum habitáre fratres in unum: Sicut "
        "unguéntum in cápite, quod descéndit in barbam, barbam Aaron, quod "
        "descéndit in oram vestiménti ejus: Sicut ros Hermon, qui descéndit "
        "in montem Sion. Quóniam illic mandávit Dóminus benedictiónem, et "
        "vitam usque in sǽculum. Glória Patri…\n\n"
        "Ant. 2. Confitémini Dómino, quóniam bonus.\n\n"
        "Psalmus 135.\n"
        "Confitémini Dómino, quóniam bonus: quóniam in ætérnum misericórdia "
        "ejus. Confitémini Deo deórum: quóniam in ætérnum misericórdia ejus. "
        "Confitémini Dómino dominórum: quóniam in ætérnum misericórdia ejus. "
        "Qui facit mirabília magna solus: quóniam in ætérnum misericórdia "
        "ejus. Qui fecit cælos in intelléctu: quóniam in ætérnum misericórdia "
        "ejus. Glória Patri…\n\n"
        "Ant. 3. Super flúmina Babylónis, illic sédimus et flévimus.\n\n"
        "Psalmus 136.\n"
        "Super flúmina Babylónis, illic sédimus et flévimus: cum recordarémur "
        "Sion: In salícibus in médio ejus, suspéndimus órgana nostra. Quia "
        "illic interrogavérunt nos, qui captívos duxérunt nos, verba "
        "cantiónum. Et qui abduxérunt nos: Hymnum cantáte nobis de cánticis "
        "Sion. Quómodo cantábimus cánticum Dómini in terra aliéna? Glória "
        "Patri…\n\n"
        "Ant. 4. Confitébor tibi, Dómine, in toto corde meo.\n\n"
        "Psalmus 138.\n"
        "Dómine, probásti me, et cognovísti me: tu cognovísti sessiónem "
        "meam, et resurrectiónem meam. Intellexísti cogitatiónes meas de "
        "longe: sémitam meam, et funículum meum investigásti. Et omnes vias "
        "meas prævidísti: quia non est sermo in lingua mea. Ecce, Dómine, "
        "tu cognovísti ómnia, novíssima, et antíqua. Glória Patri…\n\n"
        "Ant. 5. Éripe me, Dómine, ab hómine malo.\n\n"
        "Psalmus 139.\n"
        "Éripe me, Dómine, ab hómine malo: a viro iníquo éripe me. Qui "
        "cogitavérunt iniquitátes in corde: tota die constituébant prǽlia. "
        "Acuérunt linguas suas sicut serpéntis: venénum áspidum sub lábiis "
        "eórum. Glória Patri…"
    ),
)

VESPERS_FRIDAY_PSALMS = _section(
    title="Antiphons & Psalms",
    latin_title="Antiphonæ et Psalmi",
    rubric="Friday Vespers: Psalms 140, 141, 143, 144 (split into two parts).",
    english=(
        "Ant. 1. Let my prayer be directed, O Lord, as incense in thy "
        "sight.\n\n"
        "Psalm 140.\n"
        "I have cried to thee, O Lord, hear me: hearken to my voice, when I "
        "cry to thee. Let my prayer be directed as incense in thy sight: "
        "the lifting up of my hands, as evening sacrifice. Set a watch, O "
        "Lord, before my mouth: and a door round about my lips. Incline not "
        "my heart to evil words. Glory be…\n\n"
        "Ant. 2. With my voice I cried to the Lord.\n\n"
        "Psalm 141.\n"
        "I cried to the Lord with my voice: with my voice I made supplication "
        "to the Lord. In his sight I pour out my prayer: and before him I "
        "declare my trouble: When my spirit failed me, then thou knewest my "
        "paths. In this way wherein I walked, they have hidden a snare for "
        "me. Glory be…\n\n"
        "Ant. 3. Hear me, O Lord, in thy justice.\n\n"
        "Psalm 143.\n"
        "Blessed be the Lord my God, who teacheth my hands to fight, and my "
        "fingers to war. My mercy, and my refuge: my support, and my "
        "deliverer: My protector, and I have hoped in him: who subdueth my "
        "people under me. Lord, what is man, that thou art made known to him? "
        "or the son of man, that thou makest account of him? Glory be…\n\n"
        "Ant. 4. Every day I will bless thee, O Lord.\n\n"
        "Psalm 144 (i).\n"
        "I will extol thee, O God my king: and I will bless thy name for ever; "
        "yea, for ever and ever. Every day will I bless thee: and I will "
        "praise thy name for ever; yea, for ever and ever. Great is the "
        "Lord, and greatly to be praised: and of his greatness there is no "
        "end. Generation and generation shall praise thy works. Glory be…\n\n"
        "Ant. 5. The Lord is faithful in all his words.\n\n"
        "Psalm 144 (ii).\n"
        "The Lord is faithful in all his words: and holy in all his works. "
        "The Lord lifteth up all that fall: and setteth up all that are cast "
        "down. The eyes of all hope in thee, O Lord: and thou givest them "
        "meat in due season. Thou openest thy hand, and fillest with blessing "
        "every living creature. Glory be…"
    ),
    latin=(
        "Ant. 1. Dirigátur orátio mea sicut incénsum in conspéctu tuo, "
        "Dómine.\n\n"
        "Psalmus 140.\n"
        "Dómine, clamávi ad te, exáudi me: inténde voci meæ, cum clamávero "
        "ad te. Dirigátur orátio mea sicut incénsum in conspéctu tuo: "
        "elevátio mánuum meárum sacrifícium vespertínum. Pone, Dómine, "
        "custódiam ori meo, et óstium circumstántiæ lábiis meis. Non declínes "
        "cor meum in verba malítiæ. Glória Patri…\n\n"
        "Ant. 2. Voce mea ad Dóminum clamávi.\n\n"
        "Psalmus 141.\n"
        "Voce mea ad Dóminum clamávi: voce mea ad Dóminum deprecátus sum. "
        "Effúndo in conspéctu ejus oratiónem meam: et tribulatiónem meam "
        "ante ipsum pronúntio. In deficiéndo ex me spíritum meum, et tu "
        "cognovísti sémitas meas. In via hac, qua ambulábam, abscondérunt "
        "láqueum mihi. Glória Patri…\n\n"
        "Ant. 3. Exáudi me, Dómine, in justítia tua.\n\n"
        "Psalmus 143.\n"
        "Benedíctus Dóminus Deus meus, qui docet manus meas ad prǽlium, et "
        "dígitos meos ad bellum. Misericórdia mea, et refúgium meum: "
        "suscéptor meus, et liberátor meus: Protéctor meus, et in ipso "
        "sperávi: qui subdit pópulum meum sub me. Dómine, quid est homo, "
        "quia innotuísti ei? aut fílius hóminis, quia réputas eum? Glória "
        "Patri…\n\n"
        "Ant. 4. Per síngulos dies benedícam te, Dómine.\n\n"
        "Psalmus 144 (i).\n"
        "Exaltábo te, Deus meus rex: et benedícam nómini tuo in sǽculum, et "
        "in sǽculum sǽculi. Per síngulos dies benedícam tibi: et laudábo "
        "nomen tuum in sǽculum, et in sǽculum sǽculi. Magnus Dóminus, et "
        "laudábilis nimis: et magnitúdinis ejus non est finis. Generátio et "
        "generátio laudábit ópera tua. Glória Patri…\n\n"
        "Ant. 5. Fidélis Dóminus in ómnibus verbis suis.\n\n"
        "Psalmus 144 (ii).\n"
        "Fidélis Dóminus in ómnibus verbis suis: et sanctus in ómnibus "
        "opéribus suis. Állevat Dóminus omnes qui córruunt: et érigit omnes "
        "elísos. Óculi ómnium in te sperant, Dómine: et tu das escam illórum "
        "in témpore opportúno. Áperis tu manum tuam: et imples omne ánimal "
        "benedictióne. Glória Patri…"
    ),
)

VESPERS_SATURDAY_PSALMS = _section(
    title="Antiphons & Psalms",
    latin_title="Antiphonæ et Psalmi",
    rubric=(
        "Saturday Vespers: Psalms 144 (final part), 145, 146, 147 — "
        "anticipating the Sunday."
    ),
    english=(
        "Ant. 1. I will praise the Lord all my life.\n\n"
        "Psalm 144 (final).\n"
        "The Lord is nigh unto all them that call upon him: to all that call "
        "upon him in truth. He will do the will of them that fear him: and "
        "he will hear their prayer, and save them. The Lord keepeth all them "
        "that love him: but all the wicked he will destroy. My mouth shall "
        "speak the praise of the Lord. Glory be…\n\n"
        "Ant. 2. I will praise the Lord as long as I live.\n\n"
        "Psalm 145.\n"
        "Praise the Lord, O my soul, in my life I will praise the Lord: I "
        "will sing to my God as long as I shall be. Put not your trust in "
        "princes: in the children of men, in whom there is no salvation. "
        "His spirit shall go forth, and he shall return into his earth: in "
        "that day all their thoughts shall perish. Glory be…\n\n"
        "Ant. 3. Praise the Lord, for psalm is good.\n\n"
        "Psalm 146.\n"
        "Praise ye the Lord, because psalm is good: to our God be joyful and "
        "comely praise. The Lord buildeth up Jerusalem: he will gather "
        "together the dispersed of Israel. Who healeth the broken of heart, "
        "and bindeth up their bruises. Who telleth the number of the stars: "
        "and calleth them all by their names. Glory be…\n\n"
        "Ant. 4. Praise the Lord, O Jerusalem.\n\n"
        "Psalm 147.\n"
        "Praise the Lord, O Jerusalem: praise thy God, O Sion. Because he "
        "hath strengthened the bolts of thy gates: he hath blessed thy "
        "children within thee. Who hath placed peace in thy borders: and "
        "filleth thee with the fat of corn. Who sendeth forth his speech to "
        "the earth: his word runneth swiftly. Who giveth snow like wool: "
        "scattereth mists like ashes. Glory be…\n\n"
        "Ant. 5. O Mary, conceived without sin, pray for us who have recourse "
        "to thee.\n\n"
        "Marian Commemoration (Saturday is traditionally dedicated to Our "
        "Lady).\n"
        "V. Hail Mary, full of grace, the Lord is with thee.\n"
        "R. Blessed art thou amongst women, and blessed is the fruit of thy "
        "womb, Jesus.\n"
        "Holy Mary, Mother of God, pray for us sinners, now and at the hour "
        "of our death. Amen."
    ),
    latin=(
        "Ant. 1. Laudábo Dóminum in vita mea.\n\n"
        "Psalmus 144 (finis).\n"
        "Prope est Dóminus ómnibus invocántibus eum: ómnibus invocántibus "
        "eum in veritáte. Voluntátem timéntium se fáciet: et deprecatiónem "
        "eórum exáudiet, et salvos fáciet eos. Custódit Dóminus omnes "
        "diligéntes se: et omnes peccatóres dispérdet. Laudatiónem Dómini "
        "loquétur os meum. Glória Patri…\n\n"
        "Ant. 2. Laudábo Deum meum, quámdiu fúero.\n\n"
        "Psalmus 145.\n"
        "Lauda, ánima mea, Dóminum, laudábo Dóminum in vita mea: psallam "
        "Deo meo quámdiu fúero. Nolíte confídere in princípibus: in fíliis "
        "hóminum, in quibus non est salus. Exíbit spíritus ejus, et "
        "revertétur in terram suam: in illa die períbunt omnes cogitatiónes "
        "eórum. Glória Patri…\n\n"
        "Ant. 3. Laudáte Dóminum, quóniam bonus est psalmus.\n\n"
        "Psalmus 146.\n"
        "Laudáte Dóminum, quóniam bonus est psalmus: Deo nostro sit jucúnda, "
        "decóraque laudátio. Ædíficans Jerúsalem Dóminus: dispersiónes "
        "Israélis congregábit. Qui sanat contrítos corde: et álligat "
        "contritiónes eórum. Qui númerat multitúdinem stellárum: et "
        "ómnibus eis nómina vocat. Glória Patri…\n\n"
        "Ant. 4. Lauda, Jerúsalem, Dóminum.\n\n"
        "Psalmus 147.\n"
        "Lauda, Jerúsalem, Dóminum: lauda Deum tuum, Sion. Quóniam confortávit "
        "seras portárum tuárum: benedíxit fíliis tuis in te. Qui pósuit fines "
        "tuos pacem: et ádipe fruménti sátiat te. Qui emíttit elóquium suum "
        "terræ: velóciter currit sermo ejus. Qui dat nivem sicut lanam: "
        "nébulam sicut cínerem spargit. Glória Patri…\n\n"
        "Ant. 5. O María, sine labe concépta, ora pro nobis qui ad te "
        "confúgimus.\n\n"
        "Commemorátio B.M.V. (in Sábbato).\n"
        "V. Ave María, grátia plena, Dóminus tecum.\n"
        "R. Benedícta tu in muliéribus, et benedíctus fructus ventris tui, "
        "Jesus.\n"
        "Sancta María, Mater Dei, ora pro nobis peccatóribus, nunc et in "
        "hora mortis nostræ. Amen."
    ),
)

# --- Vespers: Capitulum, Hymn, Versicle, Magnificat, Collect ---

VESPERS_CAPITULUM = _section(
    title="Little Chapter",
    latin_title="Capítulum",
    english=(
        "Brethren: Blessed be the God and Father of our Lord Jesus Christ, "
        "the Father of mercies, and the God of all comfort. Who comforteth "
        "us in all our tribulation. (2 Corinthians 1:3–4)\n\n"
        "R. Thanks be to God."
    ),
    latin=(
        "Fratres: Benedíctus Deus et Pater Dómini nostri Jesu Christi, Pater "
        "misericordiárum, et Deus totíus consolatiónis. Qui consolátur nos "
        "in omni tribulatióne nostra. (2 Cor 1:3–4)\n\n"
        "R. Deo grátias."
    ),
)

VESPERS_HYMN = _section(
    title="Hymn — Lucis Creator óptime",
    latin_title="Hymnus",
    rubric=(
        "The ancient Sunday Vespers hymn, attributed to St. Gregory the "
        "Great. (On ferial days the proper hymn of the day is used; this "
        "stands as the principal exemplar.)"
    ),
    english=(
        "O blest Creator of the light,\n"
        "Who mak'st the day with radiance bright,\n"
        "And o'er the forming world didst call\n"
        "The light from chaos first of all:\n\n"
        "Whose wisdom joined in meet array\n"
        "The morn and eve, and named them Day:\n"
        "Night comes with all its darkling fears;\n"
        "Regard thy people's prayers and tears.\n\n"
        "Lest, sunk in sin, and whelmed with strife,\n"
        "They lose the gift of endless life;\n"
        "While thinking but the thoughts of time,\n"
        "They weave new chains of woe and crime.\n\n"
        "But grant them grace that they may strain\n"
        "The heavenly gate and prize to gain:\n"
        "Each harmful lure aside to cast,\n"
        "And purge away each error past.\n\n"
        "O Father, that we ask be done,\n"
        "Through Jesus Christ thine only Son,\n"
        "Who, with the Holy Ghost and thee,\n"
        "Doth live and reign eternally. Amen."
    ),
    latin=(
        "Lucis Creátor óptime,\n"
        "Lucem diérum próferens,\n"
        "Primórdiis lucis novæ\n"
        "Mundi parans oríginem:\n\n"
        "Qui mane junctum vésperi\n"
        "Diem vocári prǽcipis:\n"
        "Illábitur tetrum chaos,\n"
        "Audi preces cum flétibus.\n\n"
        "Ne mens graváta crímine,\n"
        "Vitæ sit exsul múnere,\n"
        "Dum nil perénne cógitat,\n"
        "Seséque culpis ílligat.\n\n"
        "Cæléste pulset óstium:\n"
        "Vitále tollat prǽmium:\n"
        "Vitémus omne nóxium:\n"
        "Purgémus omne péssimum.\n\n"
        "Præsta, Pater piíssime,\n"
        "Patríque compar Únice,\n"
        "Cum Spíritu Paráclito\n"
        "Regnans per omne sǽculum. Amen."
    ),
)

VESPERS_VERSICLE = _section(
    title="Versicle",
    latin_title="Versus",
    english=(
        "V. Let my prayer be directed, O Lord.\n"
        "R. As incense in thy sight."
    ),
    latin=(
        "V. Dirigátur, Dómine, orátio mea.\n"
        "R. Sicut incénsum in conspéctu tuo."
    ),
)

VESPERS_MAGNIFICAT = _section(
    title="Canticle of the Blessed Virgin — Magnificat",
    latin_title="Canticum B. Maríæ Vírginis",
    rubric=(
        "All stand and make the Sign of the Cross at the beginning. The "
        "altar is incensed during this canticle. The antiphon is said before "
        "and after."
    ),
    english=(
        "Ant. My soul doth magnify the Lord.\n\n"
        "My soul doth magnify the Lord. * And my spirit hath rejoiced in "
        "God my Saviour.\n"
        "Because he hath regarded the humility of his handmaid; * for "
        "behold from henceforth all generations shall call me blessed.\n"
        "Because he that is mighty hath done great things to me; * and holy "
        "is his name.\n"
        "And his mercy is from generation unto generations, * to them that "
        "fear him.\n"
        "He hath shewed might in his arm: * he hath scattered the proud in "
        "the conceit of their heart.\n"
        "He hath put down the mighty from their seat, * and hath exalted "
        "the humble.\n"
        "He hath filled the hungry with good things; * and the rich he hath "
        "sent empty away.\n"
        "He hath received Israel his servant, * being mindful of his mercy:\n"
        "As he spoke to our fathers, * to Abraham and to his seed for ever.\n\n"
        "Glory be to the Father, and to the Son, * and to the Holy Ghost.\n"
        "As it was in the beginning, is now, and ever shall be, * world "
        "without end. Amen.\n\n"
        "Ant. My soul doth magnify the Lord."
    ),
    latin=(
        "Ant. Magníficat ánima mea Dóminum.\n\n"
        "Magníficat * ánima mea Dóminum.\n"
        "Et exsultávit spíritus meus: * in Deo, salutári meo.\n"
        "Quia respéxit humilitátem ancíllæ suæ: * ecce enim ex hoc beátam "
        "me dicent omnes generatiónes.\n"
        "Quia fecit mihi magna qui potens est: * et sanctum nomen ejus.\n"
        "Et misericórdia ejus a progénie in progénies: * timéntibus eum.\n"
        "Fecit poténtiam in bráchio suo: * dispérsit supérbos mente cordis "
        "sui.\n"
        "Depósuit poténtes de sede: * et exaltávit húmiles.\n"
        "Esuriéntes implévit bonis: * et dívites dimísit inánes.\n"
        "Suscépit Israël púerum suum: * recordátus misericórdiæ suæ.\n"
        "Sicut locútus est ad patres nostros: * Ábraham et sémini ejus in "
        "sǽcula.\n\n"
        "Glória Patri, et Fílio, * et Spirítui Sancto.\n"
        "Sicut erat in princípio, et nunc, et semper, * et in sǽcula "
        "sæculórum. Amen.\n\n"
        "Ant. Magníficat ánima mea Dóminum."
    ),
)

VESPERS_COLLECT = _section(
    title="Preces & Collect",
    latin_title="Preces et Orátio",
    rubric=(
        "After the Pater Noster (above), the officiant prays the Collect of "
        "the day. The following is the general evening Collect for ferial use."
    ),
    english=(
        "V. The Lord be with you.\n"
        "R. And with thy spirit.\n\n"
        "Let us pray. — Visit, we beseech thee, O Lord, this dwelling, and "
        "drive far from it all snares of the enemy; let thy holy angels "
        "dwell herein to preserve us in peace; and let thy blessing be upon "
        "us always. Through our Lord Jesus Christ thy Son, who liveth and "
        "reigneth with thee in the unity of the Holy Ghost, God, world "
        "without end. R. Amen."
    ),
    latin=(
        "V. Dóminus vobíscum.\n"
        "R. Et cum spíritu tuo.\n\n"
        "Orémus. — Vísita, quǽsumus, Dómine, habitatiónem istam, et omnes "
        "insídias inimíci ab ea longe repélle: Ángeli tui sancti hábitent "
        "in ea, qui nos in pace custódiant; et benedíctio tua sit super nos "
        "semper. Per Dóminum nostrum Jesum Christum Fílium tuum, qui tecum "
        "vivit et regnat in unitáte Spíritus Sancti Deus, per ómnia sǽcula "
        "sæculórum. R. Amen."
    ),
)


def _vespers_day(psalms_section: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        DEUS_IN_ADJUTORIUM,
        psalms_section,
        VESPERS_CAPITULUM,
        VESPERS_HYMN,
        VESPERS_VERSICLE,
        VESPERS_MAGNIFICAT,
        PATER_NOSTER,
        VESPERS_COLLECT,
        DISMISSAL_BENEDICAMUS,
    ]


# ===========================================================================
# COMPLINE — Ad Completorium (Night Prayer)
# ===========================================================================
#
# Compline in the traditional Roman Breviary (pre-1911 form, retained in
# popular devotion and many monastic uses) has a FIXED psalter every day:
# Psalms 4, 30:1–6, 90, and 133. This makes Compline easy to memorise and
# pray daily; it is the same office your grandparents prayed.

COMPLINE_OPENING = _section(
    title="Preparation",
    latin_title="Jube, domne, benedícere",
    rubric="The lector asks the officiant's blessing before the reading.",
    english=(
        "V. Sir, pray a blessing.\n"
        "R. May the Lord almighty grant us a quiet night and a perfect end.\n"
        "R. Amen."
    ),
    latin=(
        "V. Jube, domne, benedícere.\n"
        "R. Noctem quiétam et finem perféctum concédat nobis Dóminus "
        "omnípotens.\n"
        "R. Amen."
    ),
)

COMPLINE_LECTIO_BREVIS = _section(
    title="Short Reading & Confiteor",
    latin_title="Léctio brevis & Confíteor",
    english=(
        "Brethren, be sober, be watchful: for your adversary the devil, as a "
        "roaring lion, goeth about, seeking whom he may devour: whom resist "
        "ye, strong in faith. But thou, O Lord, have mercy upon us.\n"
        "R. Thanks be to God.\n\n"
        "V. Our help is in the name of the Lord.\n"
        "R. Who made heaven and earth.\n\n"
        "Pater Noster (silently).\n\n"
        "I confess to almighty God, to blessed Mary ever Virgin, to blessed "
        "Michael the Archangel, to blessed John the Baptist, to the holy "
        "Apostles Peter and Paul, to all the Saints, and to you, brethren, "
        "that I have sinned exceedingly in thought, word, and deed: through "
        "my fault, through my fault, through my most grievous fault. "
        "Therefore I beseech blessed Mary ever Virgin, blessed Michael the "
        "Archangel, blessed John the Baptist, the holy Apostles Peter and "
        "Paul, all the Saints, and you, brethren, to pray for me to the "
        "Lord our God.\n\n"
        "V. May almighty God have mercy upon you, forgive you your sins, "
        "and bring you to everlasting life.\n"
        "R. Amen.\n\n"
        "V. May the almighty and merciful Lord grant us pardon, absolution, "
        "and remission of our sins.\n"
        "R. Amen."
    ),
    latin=(
        "Fratres: Sóbrii estóte, et vigiláte: quia adversárius vester "
        "diábolus tamquam leo rúgiens círcuit, quærens quem dévoret: cui "
        "resístite fortes in fide. Tu autem, Dómine, miserére nobis.\n"
        "R. Deo grátias.\n\n"
        "V. Adjutórium nostrum in nómine Dómini.\n"
        "R. Qui fecit cælum et terram.\n\n"
        "Pater noster (secréto).\n\n"
        "Confíteor Deo omnipoténti, beátæ Maríæ semper Vírgini, beáto "
        "Michaéli Archángelo, beáto Joánni Baptístæ, sanctis Apóstolis "
        "Petro et Paulo, ómnibus Sanctis, et vobis, fratres: quia peccávi "
        "nimis cogitatióne, verbo, et ópere: mea culpa, mea culpa, mea "
        "máxima culpa. Ideo precor beátam Maríam semper Vírginem, beátum "
        "Michaélem Archángelum, beátum Joánnem Baptístam, sanctos Apóstolos "
        "Petrum et Paulum, omnes Sanctos, et vos, fratres, oráre pro me ad "
        "Dóminum Deum nostrum.\n\n"
        "V. Misereátur vestri omnípotens Deus, et dimíssis peccátis vestris, "
        "perdúcat vos ad vitam ætérnam.\n"
        "R. Amen.\n\n"
        "V. Indulgéntiam, absolutiónem et remissiónem peccatórum nostrórum, "
        "tríbuat nobis omnípotens et miséricors Dóminus.\n"
        "R. Amen."
    ),
)

COMPLINE_PSALMS = _section(
    title="Psalms 4, 30, 90, 133",
    latin_title="Psalmi",
    rubric=(
        "Sung under one antiphon: \"Have mercy on me, O Lord, and hear my "
        "prayer.\" (Miserére mihi, Dómine, et exáudi oratiónem meam.)"
    ),
    english=(
        "Ant. Have mercy on me, O Lord, and hear my prayer.\n\n"
        "Psalm 4.\n"
        "When I called upon him, the God of my justice heard me: when I was "
        "in distress, thou hast enlarged me. Have mercy on me: and hear my "
        "prayer. O ye sons of men, how long will you be dull of heart? why "
        "do you love vanity, and seek after lying? Know ye also that the "
        "Lord hath made his holy one wonderful: the Lord will hear me when "
        "I shall cry unto him. Be ye angry, and sin not: the things you say "
        "in your hearts, be sorry for them upon your beds. In peace in the "
        "self-same I will sleep, and I will rest: for thou, O Lord, "
        "singularly hast settled me in hope. Glory be…\n\n"
        "Psalm 30:1–6.\n"
        "In thee, O Lord, I have hoped, let me never be confounded: deliver "
        "me in thy justice. Bow down thy ear to me: make haste to deliver "
        "me. Be thou unto me a God, a protector, and a house of refuge, to "
        "save me. For thou art my strength and my refuge; and for thy "
        "name's sake thou wilt lead me, and nourish me. Thou wilt bring me "
        "out of this snare, which they have hidden for me: for thou art my "
        "protector. Into thy hands I commend my spirit: thou hast redeemed "
        "me, O Lord, the God of truth. Glory be…\n\n"
        "Psalm 90 — Qui hábitat.\n"
        "He that dwelleth in the aid of the most High, shall abide under the "
        "protection of the God of Jacob. He shall say to the Lord: Thou art "
        "my protector, and my refuge: my God, in him will I trust. For he "
        "hath delivered me from the snare of the hunters: and from the "
        "sharp word. He will overshadow thee with his shoulders: and under "
        "his wings thou shalt trust. His truth shall compass thee with a "
        "shield: thou shalt not be afraid of the terror of the night. A "
        "thousand shall fall at thy side, and ten thousand at thy right "
        "hand: but it shall not come nigh thee. For he hath given his angels "
        "charge over thee; to keep thee in all thy ways. In their hands "
        "they shall bear thee up: lest thou dash thy foot against a stone. "
        "He shall cry to me, and I will hear him: I am with him in "
        "tribulation, I will deliver him, and I will glorify him. I will "
        "fill him with length of days; and I will shew him my salvation. "
        "Glory be…\n\n"
        "Psalm 133.\n"
        "Behold now bless ye the Lord, all ye servants of the Lord: Who "
        "stand in the house of the Lord, in the courts of the house of our "
        "God. In the nights lift up your hands to the holy places, and bless "
        "ye the Lord. May the Lord out of Sion bless thee, he that made "
        "heaven and earth. Glory be to the Father…\n\n"
        "Ant. Have mercy on me, O Lord, and hear my prayer."
    ),
    latin=(
        "Ant. Miserére mihi, Dómine, et exáudi oratiónem meam.\n\n"
        "Psalmus 4.\n"
        "Cum invocárem exaudívit me Deus justítiæ meæ: in tribulatióne "
        "dilatásti mihi. Miserére mei: et exáudi oratiónem meam. Fílii "
        "hóminum, úsquequo gravi corde? ut quid dilígitis vanitátem, et "
        "quǽritis mendácium? Et scitóte quóniam mirificávit Dóminus "
        "sanctum suum: Dóminus exáudiet me cum clamávero ad eum. Iráscimini, "
        "et nolíte peccáre: quæ dícitis in córdibus vestris, in cubílibus "
        "vestris compungímini. In pace in idípsum dórmiam, et requiéscam: "
        "quóniam tu, Dómine, singuláriter in spe constituísti me. Glória "
        "Patri…\n\n"
        "Psalmus 30:1–6.\n"
        "In te, Dómine, sperávi, non confúndar in ætérnum: in justítia tua "
        "líbera me. Inclína ad me aurem tuam: accélera ut éruas me. Esto "
        "mihi in Deum protectórem, et in domum refúgii, ut salvum me fácias. "
        "Quóniam fortitúdo mea, et refúgium meum es tu: et propter nomen "
        "tuum dedúces me, et enútries me. Edúces me de láqueo hoc, quem "
        "abscondérunt mihi: quóniam tu es protéctor meus. In manus tuas "
        "comméndo spíritum meum: redemísti me, Dómine, Deus veritátis. "
        "Glória Patri…\n\n"
        "Psalmus 90 — Qui hábitat.\n"
        "Qui hábitat in adjutório Altíssimi, in protectióne Dei cæli "
        "commorábitur. Dicet Dómino: Suscéptor meus es tu, et refúgium "
        "meum: Deus meus, sperábo in eum. Quóniam ipse liberávit me de "
        "láqueo venántium, et a verbo áspero. Scápulis suis obumbrábit "
        "tibi: et sub pennis ejus sperábis. Scuto circúmdabit te véritas "
        "ejus: non timébis a timóre noctúrno. Cadent a látere tuo mille, et "
        "decem míllia a dextris tuis: ad te autem non appropinquábit. "
        "Quóniam Ángelis suis mandávit de te: ut custódiant te in ómnibus "
        "viis tuis. In mánibus portábunt te: ne forte offéndas ad lápidem "
        "pedem tuum. Clamábit ad me, et ego exáudiam eum: cum ipso sum in "
        "tribulatióne: erípiam eum, et glorificábo eum. Longitúdine diérum "
        "replébo eum: et osténdam illi salutáre meum. Glória Patri…\n\n"
        "Psalmus 133.\n"
        "Ecce nunc benedícite Dóminum, omnes servi Dómini: Qui statis in "
        "domo Dómini, in átriis domus Dei nostri. In nóctibus extóllite "
        "manus vestras in sancta, et benedícite Dóminum. Benedícat te "
        "Dóminus ex Sion, qui fecit cælum et terram. Glória Patri…\n\n"
        "Ant. Miserére mihi, Dómine, et exáudi oratiónem meam."
    ),
)

COMPLINE_HYMN = _section(
    title="Hymn — Te lucis ante términum",
    latin_title="Hymnus",
    rubric=(
        "The night hymn of the universal Church, sung at Compline since "
        "the 7th century."
    ),
    english=(
        "Before the ending of the day,\n"
        "Creator of the world, we pray\n"
        "That with thy wonted favour thou\n"
        "Wouldst be our guard and keeper now.\n\n"
        "From all ill dreams defend our eyes,\n"
        "From nightly fears and fantasies;\n"
        "Tread under foot our ghostly foe,\n"
        "That no pollution we may know.\n\n"
        "O Father, that we ask be done,\n"
        "Through Jesus Christ thine only Son;\n"
        "Who, with the Holy Ghost and thee,\n"
        "Doth live and reign eternally. Amen."
    ),
    latin=(
        "Te lucis ante términum,\n"
        "Rerum Creátor, póscimus,\n"
        "Ut pro tua cleméntia\n"
        "Sis præsul et custódia.\n\n"
        "Procul recédant sómnia,\n"
        "Et nóctium phantásmata;\n"
        "Hostémque nostrum cómprime,\n"
        "Ne pollúantur córpora.\n\n"
        "Præsta, Pater piíssime,\n"
        "Patríque compar Únice,\n"
        "Cum Spíritu Paráclito\n"
        "Regnans per omne sǽculum. Amen."
    ),
)

COMPLINE_CAPITULUM = _section(
    title="Little Chapter & Versicle",
    latin_title="Capítulum & Responsórium",
    english=(
        "But thou, O Lord, art among us, and thy name is called upon by us: "
        "forsake us not, O Lord our God. (Jeremias 14:9)\n"
        "R. Thanks be to God.\n\n"
        "V. Keep us, O Lord, as the apple of thine eye.\n"
        "R. Protect us under the shadow of thy wings."
    ),
    latin=(
        "Tu autem in nobis es, Dómine, et nomen sanctum tuum invocátum "
        "est super nos: ne derelínquas nos, Dómine Deus noster. "
        "(Jer 14:9)\n"
        "R. Deo grátias.\n\n"
        "V. Custódi nos, Dómine, ut pupíllam óculi.\n"
        "R. Sub umbra alárum tuárum prótege nos."
    ),
)

COMPLINE_NUNC_DIMITTIS = _section(
    title="Canticle of Simeon — Nunc dimittis",
    latin_title="Canticum Simeónis",
    rubric=(
        "All stand and make the Sign of the Cross at the beginning. The "
        "antiphon is said before and after."
    ),
    english=(
        "Ant. Save us, O Lord, while waking, and guard us while sleeping; "
        "that we may watch with Christ and rest in peace.\n\n"
        "Now thou dost dismiss thy servant, O Lord, * according to thy word "
        "in peace;\n"
        "Because my eyes have seen * thy salvation,\n"
        "Which thou hast prepared * before the face of all peoples:\n"
        "A light to the revelation of the Gentiles, * and the glory of thy "
        "people Israel.\n\n"
        "Glory be to the Father, and to the Son, * and to the Holy Ghost.\n"
        "As it was in the beginning, is now, and ever shall be, * world "
        "without end. Amen.\n\n"
        "Ant. Save us, O Lord, while waking, and guard us while sleeping; "
        "that we may watch with Christ and rest in peace."
    ),
    latin=(
        "Ant. Salva nos, Dómine, vigilántes, custódi nos dormiéntes: ut "
        "vigilémus cum Christo, et requiescámus in pace.\n\n"
        "Nunc dimíttis servum tuum, Dómine, * secúndum verbum tuum in pace:\n"
        "Quia vidérunt óculi mei * salutáre tuum,\n"
        "Quod parásti * ante fáciem ómnium populórum:\n"
        "Lumen ad revelatiónem géntium, * et glóriam plebis tuæ Israël.\n\n"
        "Glória Patri, et Fílio, * et Spirítui Sancto.\n"
        "Sicut erat in princípio, et nunc, et semper, * et in sǽcula "
        "sæculórum. Amen.\n\n"
        "Ant. Salva nos, Dómine, vigilántes, custódi nos dormiéntes: ut "
        "vigilémus cum Christo, et requiescámus in pace."
    ),
)

COMPLINE_COLLECT = _section(
    title="Collect & Blessing",
    latin_title="Orátio et Benedíctio",
    english=(
        "V. The Lord be with you.\n"
        "R. And with thy spirit.\n\n"
        "Let us pray. — Visit, we beseech thee, O Lord, this dwelling, and "
        "drive far from it all the snares of the enemy: let thy holy angels "
        "dwell herein, who may keep us in peace, and may thy blessing be "
        "always upon us. Through our Lord Jesus Christ thy Son, who liveth "
        "and reigneth with thee, in the unity of the Holy Ghost, God, world "
        "without end. R. Amen.\n\n"
        "V. The Lord be with you.\n"
        "R. And with thy spirit.\n\n"
        "V. Let us bless the Lord.\n"
        "R. Thanks be to God.\n\n"
        "The almighty and merciful Lord, the Father, the Son, and the Holy "
        "Ghost, bless and preserve us.\n"
        "R. Amen."
    ),
    latin=(
        "V. Dóminus vobíscum.\n"
        "R. Et cum spíritu tuo.\n\n"
        "Orémus. — Vísita, quǽsumus, Dómine, habitatiónem istam, et omnes "
        "insídias inimíci ab ea longe repélle: Ángeli tui sancti hábitent "
        "in ea, qui nos in pace custódiant; et benedíctio tua sit super nos "
        "semper. Per Dóminum nostrum Jesum Christum Fílium tuum, qui tecum "
        "vivit et regnat in unitáte Spíritus Sancti Deus, per ómnia sǽcula "
        "sæculórum. R. Amen.\n\n"
        "V. Dóminus vobíscum.\n"
        "R. Et cum spíritu tuo.\n\n"
        "V. Benedicámus Dómino.\n"
        "R. Deo grátias.\n\n"
        "Benedícat et custódiat nos omnípotens et miséricors Dóminus, "
        "Pater, et Fílius, et Spíritus Sanctus.\n"
        "R. Amen."
    ),
)

COMPLINE_MARIAN_ANTIPHON = _section(
    title="Final Marian Antiphon — Salve Regina",
    latin_title="Antíphona Mariána Finalis",
    rubric=(
        "Compline closes with the seasonal Marian antiphon. The Salve "
        "Regina (sung from Trinity Sunday to Advent) is given here. From "
        "Advent to the Purification: Alma Redemptóris Mater. From the "
        "Purification to Holy Thursday: Ave Regína cælórum. From Easter to "
        "the eve of Trinity: Regína cæli."
    ),
    english=(
        "Hail, holy Queen, Mother of mercy: hail, our life, our sweetness, "
        "and our hope. To thee do we cry, poor banished children of Eve. To "
        "thee do we send up our sighs, mourning and weeping in this valley "
        "of tears. Turn then, most gracious Advocate, thine eyes of mercy "
        "toward us; and after this our exile, shew unto us the blessed fruit "
        "of thy womb, Jesus. O clement, O loving, O sweet Virgin Mary.\n\n"
        "V. Pray for us, O holy Mother of God.\n"
        "R. That we may be made worthy of the promises of Christ."
    ),
    latin=(
        "Salve, Regína, mater misericórdiæ;\n"
        "vita, dulcédo et spes nostra, salve.\n"
        "Ad te clamámus, éxsules fílii Hevæ.\n"
        "Ad te suspirámus, geméntes et flentes\n"
        "in hac lacrimárum valle.\n"
        "Eja ergo, advocáta nostra,\n"
        "illos tuos misericórdes óculos ad nos convérte.\n"
        "Et Jesum, benedíctum fructum ventris tui,\n"
        "nobis post hoc exsílium osténde.\n"
        "O clemens: O pia: O dulcis Virgo María.\n\n"
        "V. Ora pro nobis, sancta Dei Génitrix.\n"
        "R. Ut digni efficiámur promissiónibus Christi."
    ),
)


COMPLINE_SECTIONS: List[Dict[str, Any]] = [
    COMPLINE_OPENING,
    COMPLINE_LECTIO_BREVIS,
    DEUS_IN_ADJUTORIUM,
    COMPLINE_PSALMS,
    COMPLINE_HYMN,
    COMPLINE_CAPITULUM,
    COMPLINE_NUNC_DIMITTIS,
    COMPLINE_COLLECT,
    COMPLINE_MARIAN_ANTIPHON,
]


# ===========================================================================
# DAYTIME PRAYER — The Little Hours (Terce · Sext · None)
# ===========================================================================
#
# The "Little Hours" sanctify the working day at the third, sixth, and ninth
# hours (≈ 9 a.m., noon, 3 p.m.). In the traditional Roman Breviary each has
# the same shape — a proper hymn, a portion of Psalm 118 (the longest psalm,
# spread across the week), a little chapter, a versicle, and the day's
# collect. The psalmody and collect follow the day's proper; what is printed
# here is the ferial *per annum* form, with a representative portion of
# Psalm 118. Pray whichever Hour matches the time of day.

DAYTIME_INTRO = _section(
    title="About the Little Hours",
    latin_title="De Horis Minóribus",
    note=(
        "Pray Terce in mid-morning (the third hour), Sext at midday (the "
        "sixth hour), and None in mid-afternoon (the ninth hour). Each Hour "
        "is short — a hymn, a portion of Psalm 118, a little chapter, a "
        "versicle, and a collect. The chapter and collect change with the "
        "day and season; for the exact proper of today, open iBreviary from "
        "the previous screen."
    ),
    english=(
        "The Apostles kept the ancient Jewish hours of prayer: \u201cPeter "
        "and John went up into the temple at the ninth hour of prayer\u201d "
        "(Acts 3:1); the Spirit descended at the third hour (Acts 2:15); "
        "Peter prayed on the housetop about the sixth hour (Acts 10:9). The "
        "Church keeps watch with them, hallowing the whole course of the day."
    ),
)

# --- TERCE (Ad Tértiam) -----------------------------------------------------

TERCE_HYMN = _section(
    title="Terce — Hymn",
    latin_title="Nunc, Sancte, nobis, Spíritus",
    rubric="The hymn of Terce, invoking the Holy Ghost who came at the third hour.",
    english=(
        "Come, Holy Ghost, who ever One\n"
        "Art with the Father and the Son,\n"
        "It is the hour, our souls possess\n"
        "With thy full flood of holiness.\n\n"
        "Let flesh and heart and lips and mind\n"
        "Sound forth our witness to mankind;\n"
        "And love light up our mortal frame,\n"
        "Till others catch the living flame.\n\n"
        "Almighty Father, hear our cry\n"
        "Through Jesus Christ our Lord most high,\n"
        "Who with the Holy Ghost and thee\n"
        "Doth live and reign eternally. Amen."
    ),
    latin=(
        "Nunc, Sancte, nobis, Spíritus,\n"
        "Unum Patri cum Fílio,\n"
        "Dignáre promptus íngeri\n"
        "Nostro refúsus péctori.\n\n"
        "Os, lingua, mens, sensus, vigor\n"
        "Confessiónem pérsonent,\n"
        "Flamméscat igne cáritas,\n"
        "Accéndat ardor próximos.\n\n"
        "Præsta, Pater piíssime,\n"
        "Patríque compar Únice,\n"
        "Cum Spíritu Paráclito\n"
        "Regnans per omne sǽculum. Amen."
    ),
)

TERCE_PSALMODY = _section(
    title="Terce — Psalmody",
    latin_title="Psalmus 118 (Legem pone)",
    rubric=(
        "A portion of Psalm 118 is said under one antiphon. The opening of the "
        "\u201cLegem pone\u201d section is given here."
    ),
    english=(
        "Ant. Blessed are the undefiled in the way, who walk in the law of the Lord.\n\n"
        "Psalm 118 (He).\n"
        "Set before me for a law the way of thy justifications, O Lord: and I "
        "will always seek after it. Give me understanding, and I will search "
        "thy law; and I will keep it with my whole heart. Lead me into the "
        "path of thy commandments; for this same I have desired. Incline my "
        "heart into thy testimonies and not to covetousness. Turn away my eyes "
        "that they may not behold vanity: quicken me in thy way. Glory be to "
        "the Father…"
    ),
    latin=(
        "Ant. Beáti immaculáti in via, qui ámbulant in lege Dómini.\n\n"
        "Psalmus 118 (He).\n"
        "Legem pone mihi, Dómine, viam justificatiónum tuárum, et exquíram eam "
        "semper. Da mihi intelléctum, et scrutábor legem tuam, et custódiam "
        "illam in toto corde meo. Deduc me in sémitam mandatórum tuórum, quia "
        "ipsam vólui. Inclína cor meum in testimónia tua, et non in avarítiam. "
        "Avérte óculos meos ne vídeant vanitátem: in via tua vivífica me. "
        "Glória Patri…"
    ),
)

TERCE_CHAPTER = _section(
    title="Terce — Chapter, Versicle & Collect",
    latin_title="Capítulum, Versus et Orátio",
    rubric=(
        "The little chapter and the collect are proper to the day; the ferial "
        "per annum form is given."
    ),
    english=(
        "Chapter (Jeremiah 17:14).\n"
        "Heal me, O Lord, and I shall be healed: save me, and I shall be "
        "saved, for thou art my praise.\n"
        "R. Thanks be to God.\n\n"
        "V. I have run the way of thy commandments.\n"
        "R. When thou didst enlarge my heart.\n\n"
        "Let us pray.\n"
        "O Lord, our God, by whose providence the labour of the day is "
        "ordered: pour out upon us thy grace, that we may begin and end this "
        "day in thy service; through Christ our Lord. R. Amen."
    ),
    latin=(
        "Capítulum (Jeremías 17:14).\n"
        "Sana me, Dómine, et sanábor: salvum me fac, et salvus ero: quóniam "
        "laus mea tu es.\n"
        "R. Deo grátias.\n\n"
        "V. Viam mandatórum tuórum cucúrri.\n"
        "R. Cum dilatásti cor meum.\n\n"
        "Orémus.\n"
        "Dómine Deus noster, cujus providéntia labor diéi ordinátur: effúnde "
        "super nos grátiam tuam, ut hunc diem in servítio tuo incipiámus et "
        "perficiámus; per Christum Dóminum nostrum. R. Amen."
    ),
)

# --- SEXT (Ad Sextam) -------------------------------------------------------

SEXT_HYMN = _section(
    title="Sext — Hymn",
    latin_title="Rector potens, verax Deus",
    rubric="The hymn of Sext, prayed at midday when the sun is at its height.",
    english=(
        "O God of truth, O Lord of might,\n"
        "Who orderest time and change aright,\n"
        "And send'st the early morning ray,\n"
        "And light'st the glow of perfect day:\n\n"
        "Extinguish thou each sinful fire,\n"
        "And banish every ill desire;\n"
        "And while thou keep'st the body whole,\n"
        "Shed forth thy peace upon the soul.\n\n"
        "Almighty Father, hear our cry\n"
        "Through Jesus Christ our Lord most high,\n"
        "Who with the Holy Ghost and thee\n"
        "Doth live and reign eternally. Amen."
    ),
    latin=(
        "Rector potens, verax Deus,\n"
        "Qui témperas rerum vices,\n"
        "Splendóre mane illúminas,\n"
        "Et ígnibus merídiem:\n\n"
        "Exstíngue flammas lítium,\n"
        "Aufer calórem nóxium,\n"
        "Confer salútem córporum,\n"
        "Verámque pacem córdium.\n\n"
        "Præsta, Pater piíssime,\n"
        "Patríque compar Únice,\n"
        "Cum Spíritu Paráclito\n"
        "Regnans per omne sǽculum. Amen."
    ),
)

SEXT_PSALMODY = _section(
    title="Sext — Psalmody",
    latin_title="Psalmus 118 (Defécit)",
    rubric="A further portion of Psalm 118 is said under one antiphon.",
    english=(
        "Ant. Let thy mercies come unto me, O Lord, and I shall live.\n\n"
        "Psalm 118 (Caph).\n"
        "My soul hath fainted after thy salvation: and in thy word I have very "
        "much hoped. My eyes have failed for thy word, saying: When wilt thou "
        "comfort me? For I am become like a bottle in the frost: yet have I "
        "not forgotten thy justifications. How many are the days of thy "
        "servant: when wilt thou execute judgment on them that persecute me? "
        "Glory be to the Father…"
    ),
    latin=(
        "Ant. Véniant mihi miseratiónes tuæ, Dómine, et vivam.\n\n"
        "Psalmus 118 (Caph).\n"
        "Defécit in salutáre tuum ánima mea: et in verbum tuum supersperávi. "
        "Defecérunt óculi mei in elóquium tuum, dicéntes: Quando consoláberis "
        "me? Quia factus sum sicut uter in pruína: justificatiónes tuas non "
        "sum oblítus. Quot sunt dies servi tui: quando fácies de persequéntibus "
        "me judícium? Glória Patri…"
    ),
)

SEXT_CHAPTER = _section(
    title="Sext — Chapter, Versicle & Collect",
    latin_title="Capítulum, Versus et Orátio",
    rubric=(
        "The little chapter and collect are proper to the day; the ferial per "
        "annum form is given."
    ),
    english=(
        "Chapter (Romans 13:12).\n"
        "The night is passed, and the day is at hand. Let us therefore cast off "
        "the works of darkness, and put on the armour of light.\n"
        "R. Thanks be to God.\n\n"
        "V. Direct my steps according to thy word.\n"
        "R. And let no iniquity have dominion over me.\n\n"
        "Let us pray.\n"
        "O God, who at the sixth hour didst stretch out thine arms upon the "
        "Cross for the salvation of the world: keep us this day from every "
        "evil, and bring us to the peace of thy kingdom; through Christ our "
        "Lord. R. Amen."
    ),
    latin=(
        "Capítulum (Románi 13:12).\n"
        "Nox præcéssit, dies autem appropinquávit. Abjiciámus ergo ópera "
        "tenebrárum, et induámur arma lucis.\n"
        "R. Deo grátias.\n\n"
        "V. Gressus meos dírige secúndum elóquium tuum.\n"
        "R. Et non dominétur mei omnis injustítia.\n\n"
        "Orémus.\n"
        "Deus, qui hora sexta pro mundi redemptióne in Cruce manus extendísti: "
        "custódi nos hódie ab omni malo, et ad regni tui pacem perdúc nos; per "
        "Christum Dóminum nostrum. R. Amen."
    ),
)

# --- NONE (Ad Nonam) --------------------------------------------------------

NONE_HYMN = _section(
    title="None — Hymn",
    latin_title="Rerum, Deus, tenax vigor",
    rubric="The hymn of None, prayed in mid-afternoon as the day declines.",
    english=(
        "O God, unchangeable and true,\n"
        "Of all the Life and Power,\n"
        "Dispensing light in silence through\n"
        "Each successive hour:\n\n"
        "Lord, brighten our declining day,\n"
        "That it may never wane,\n"
        "Till death, when all things round decay,\n"
        "Brings back the morn again.\n\n"
        "Almighty Father, hear our cry\n"
        "Through Jesus Christ our Lord most high,\n"
        "Who with the Holy Ghost and thee\n"
        "Doth live and reign eternally. Amen."
    ),
    latin=(
        "Rerum, Deus, tenax vigor,\n"
        "Immótus in te pérmanens,\n"
        "Lucis diúrnæ témpora\n"
        "Succéssibus detérminans:\n\n"
        "Largíre lumen véspere,\n"
        "Quo vita nusquam décidat,\n"
        "Sed prǽmium mortis sacræ\n"
        "Perénnis instet glória.\n\n"
        "Præsta, Pater piíssime,\n"
        "Patríque compar Únice,\n"
        "Cum Spíritu Paráclito\n"
        "Regnans per omne sǽculum. Amen."
    ),
)

NONE_PSALMODY = _section(
    title="None — Psalmody",
    latin_title="Psalmus 118 (Mirabília)",
    rubric="The closing portion of Psalm 118 is said under one antiphon.",
    english=(
        "Ant. Let my cry come near in thy sight, O Lord: give me understanding "
        "according to thy word.\n\n"
        "Psalm 118 (Pe).\n"
        "Thy testimonies are wonderful: therefore my soul hath sought them. "
        "The declaration of thy words giveth light: and giveth understanding "
        "to little ones. I opened my mouth, and panted: because I longed for "
        "thy commandments. Look thou upon me, and have mercy on me, according "
        "to the judgment of them that love thy name. Glory be to the Father…"
    ),
    latin=(
        "Ant. Appropínquet deprecátio mea in conspéctu tuo, Dómine: juxta "
        "elóquium tuum da mihi intelléctum.\n\n"
        "Psalmus 118 (Pe).\n"
        "Mirabília testimónia tua: ídeo scrutáta est ea ánima mea. Declarátio "
        "sermónum tuórum illúminat: et intelléctum dat párvulis. Os meum "
        "apérui, et attráxi spíritum: quia mandáta tua desiderábam. Aspice in "
        "me, et miserére mei, secúndum judícium diligéntium nomen tuum. Glória "
        "Patri…"
    ),
)

NONE_CHAPTER = _section(
    title="None — Chapter, Versicle & Collect",
    latin_title="Capítulum, Versus et Orátio",
    rubric=(
        "The little chapter and collect are proper to the day; the ferial per "
        "annum form is given. None concludes with the dismissal below."
    ),
    english=(
        "Chapter (Daniel 9:19).\n"
        "Hear, O Lord; be appeased, O Lord: hearken and do: delay not, for thy "
        "own sake, O my God.\n"
        "R. Thanks be to God.\n\n"
        "V. From the rising of the sun unto the going down of the same.\n"
        "R. The name of the Lord is worthy of praise.\n\n"
        "Let us pray.\n"
        "O God, who at the ninth hour didst will thy Son to taste death upon "
        "the Cross for us sinners: grant that, dying daily to sin, we may live "
        "to thee alone; through the same Christ our Lord. R. Amen.\n\n"
        "V. Let us bless the Lord. R. Thanks be to God."
    ),
    latin=(
        "Capítulum (Dániel 9:19).\n"
        "Exáudi, Dómine; placáre, Dómine: atténde et fac: ne moréris propter "
        "temetípsum, Deus meus.\n"
        "R. Deo grátias.\n\n"
        "V. A solis ortu usque ad occásum.\n"
        "R. Laudábile nomen Dómini.\n\n"
        "Orémus.\n"
        "Deus, qui hora nona pro nobis peccatóribus Fílium tuum mortem in Cruce "
        "gustáre voluísti: præsta; ut, peccáto quotídie moriéntes, tibi soli "
        "vivámus; per eúndem Christum Dóminum nostrum. R. Amen.\n\n"
        "V. Benedicámus Dómino. R. Deo grátias."
    ),
)

DAYTIME_SECTIONS: List[Dict[str, Any]] = [
    DAYTIME_INTRO,
    TERCE_HYMN,
    TERCE_PSALMODY,
    TERCE_CHAPTER,
    SEXT_HYMN,
    SEXT_PSALMODY,
    SEXT_CHAPTER,
    NONE_HYMN,
    NONE_PSALMODY,
    NONE_CHAPTER,
]



# ===========================================================================
# Days catalogue (weekday rotation)
# ===========================================================================

DAYS: List[Dict[str, Any]] = [
    {"key": "sunday",    "name": "Sunday",    "latin_name": "Domínica",     "weekday_index": 6},
    {"key": "monday",    "name": "Monday",    "latin_name": "Féria II",     "weekday_index": 0},
    {"key": "tuesday",   "name": "Tuesday",   "latin_name": "Féria III",    "weekday_index": 1},
    {"key": "wednesday", "name": "Wednesday", "latin_name": "Féria IV",     "weekday_index": 2},
    {"key": "thursday",  "name": "Thursday",  "latin_name": "Féria V",      "weekday_index": 3},
    {"key": "friday",    "name": "Friday",    "latin_name": "Féria VI",     "weekday_index": 4},
    {"key": "saturday",  "name": "Saturday",  "latin_name": "Sábbato",      "weekday_index": 5},
]


LAUDS_BY_DAY: Dict[str, List[Dict[str, Any]]] = {
    "sunday":    _lauds_day(LAUDS_SUNDAY_PSALMS),
    "monday":    _lauds_day(LAUDS_MONDAY_PSALMS),
    "tuesday":   _lauds_day(LAUDS_TUESDAY_PSALMS),
    "wednesday": _lauds_day(LAUDS_WEDNESDAY_PSALMS),
    "thursday":  _lauds_day(LAUDS_THURSDAY_PSALMS),
    "friday":    _lauds_day(LAUDS_FRIDAY_PSALMS),
    "saturday":  _lauds_day(LAUDS_SATURDAY_PSALMS),
}

VESPERS_BY_DAY: Dict[str, List[Dict[str, Any]]] = {
    "sunday":    _vespers_day(VESPERS_SUNDAY_PSALMS),
    "monday":    _vespers_day(VESPERS_MONDAY_PSALMS),
    "tuesday":   _vespers_day(VESPERS_TUESDAY_PSALMS),
    "wednesday": _vespers_day(VESPERS_WEDNESDAY_PSALMS),
    "thursday":  _vespers_day(VESPERS_THURSDAY_PSALMS),
    "friday":    _vespers_day(VESPERS_FRIDAY_PSALMS),
    "saturday":  _vespers_day(VESPERS_SATURDAY_PSALMS),
}

# Compline psalter is fixed across all days in the pre-1911 Roman use.
COMPLINE_BY_DAY: Dict[str, List[Dict[str, Any]]] = {
    d["key"]: COMPLINE_SECTIONS for d in DAYS
}

# Daytime Prayer (the Little Hours) is fixed in structure across the week;
# the psalmody/collect propers vary but we present the ferial per annum form.
DAYTIME_BY_DAY: Dict[str, List[Dict[str, Any]]] = {
    d["key"]: DAYTIME_SECTIONS for d in DAYS
}


HOURS: List[Dict[str, Any]] = [
    {
        "slug": "lauds",
        "name": "Lauds",
        "subtitle": "Morning Prayer",
        "latin_name": "Ad Laudes",
        "icon": "sunny-outline",
        "accent_color": "#C99A4A",  # dawn gold
        "time_of_day": "Daybreak — between dawn and sunrise",
        "duration": "~12 min",
        "intro": (
            "Lauds (\"praises\") is the morning Hour of the Divine Office, "
            "prayed at daybreak. It is the sacrifice of praise the Church "
            "offers as the sun rises, in fulfilment of the psalmist's "
            "promise: \"In the morning, O Lord, thou shalt hear my voice.\" "
            "Each weekday rotates a different set of psalms; the Benedictus "
            "(Canticle of Zachary) is sung every day."
        ),
        "psalms_vary_by_day": True,
        "sections_by_day": LAUDS_BY_DAY,
    },
    {
        "slug": "daytime",
        "name": "Daytime Prayer",
        "subtitle": "The Little Hours · Terce, Sext, None",
        "latin_name": "Ad Horas Minóres",
        "icon": "sunny",
        "accent_color": "#B8842C",  # midday amber
        "time_of_day": "Mid-morning, midday & mid-afternoon",
        "duration": "~6 min each",
        "intro": (
            "Daytime Prayer sanctifies the working day at the third, sixth, "
            "and ninth hours — Terce (\u2248 9 a.m.), Sext (noon), and None "
            "(\u2248 3 p.m.). Each \u201cLittle Hour\u201d is brief: a proper "
            "hymn invoking God for that moment of the day, a portion of Psalm "
            "118, a little chapter, a versicle, and a collect. The Apostles "
            "kept these same hours of prayer in the Temple. Pray whichever "
            "Hour matches the time of day."
        ),
        "psalms_vary_by_day": False,
        "sections_by_day": DAYTIME_BY_DAY,
    },
    {
        "slug": "vespers",
        "name": "Vespers",
        "subtitle": "Evening Prayer",
        "latin_name": "Ad Vésperas",
        "icon": "partly-sunny-outline",
        "accent_color": "#8A4A6C",  # dusk plum
        "time_of_day": "Sunset — the hour of lamp-lighting",
        "duration": "~12 min",
        "intro": (
            "Vespers (from \"vesper,\" evening star) is the Church's twilight "
            "thanksgiving for the day. With incense and the Magnificat, the "
            "Bride of Christ joins her voice to that of His Mother: \"My "
            "soul doth magnify the Lord.\" Each weekday rotates a different "
            "set of five psalms."
        ),
        "psalms_vary_by_day": True,
        "sections_by_day": VESPERS_BY_DAY,
    },
    {
        "slug": "compline",
        "name": "Compline",
        "subtitle": "Night Prayer",
        "latin_name": "Ad Completórium",
        "icon": "moon-outline",
        "accent_color": "#2E3A5F",  # midnight blue
        "time_of_day": "Before retiring — the close of the day",
        "duration": "~8 min",
        "intro": (
            "Compline (\"completion\") is the last Hour of the day, prayed "
            "before sleep. The Church's bedtime prayer commends the soul to "
            "God under His angels' wings. In the traditional Roman use the "
            "psalter is fixed (Ps 4, 30:1–6, 90, 133) — easy to memorise, "
            "the same every night. Compline closes with a Marian antiphon "
            "that changes with the liturgical season."
        ),
        "psalms_vary_by_day": False,
        "sections_by_day": COMPLINE_BY_DAY,
    },
]

HOURS_BY_SLUG: Dict[str, Dict[str, Any]] = {h["slug"]: h for h in HOURS}
DAYS_BY_KEY: Dict[str, Dict[str, Any]] = {d["key"]: d for d in DAYS}


# ---------------------------------------------------------------------------
# Helpers for the router
# ---------------------------------------------------------------------------


def _hour_summary(h: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "slug": h["slug"],
        "name": h["name"],
        "subtitle": h["subtitle"],
        "latin_name": h["latin_name"],
        "icon": h["icon"],
        "accent_color": h["accent_color"],
        "time_of_day": h["time_of_day"],
        "duration": h["duration"],
        "psalms_vary_by_day": h["psalms_vary_by_day"],
    }


def _hour_detail(h: Dict[str, Any]) -> Dict[str, Any]:
    sample = next(iter(h["sections_by_day"].values()))
    return {
        **_hour_summary(h),
        "intro": h["intro"],
        "section_count_per_day": len(sample),
        "days": DAYS,
    }


def _today_key() -> str:
    """Return the current weekday key in server time (UTC). The frontend
    sends its own preferred day, but we use this as a default if no day
    is given."""
    # weekday(): Monday is 0 ... Sunday is 6
    idx = datetime.now(timezone.utc).weekday()
    for d in DAYS:
        if d["weekday_index"] == idx:
            return d["key"]
    return "sunday"


def _section_payload(
    hour: Dict[str, Any],
    day_key: str,
) -> Dict[str, Any]:
    day = DAYS_BY_KEY.get(day_key)
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")
    sections = hour["sections_by_day"].get(day_key)
    if not sections:
        # For hours whose psalter doesn't vary, all days return the same list.
        sections = hour["sections_by_day"].get("sunday")
        if not sections:
            raise HTTPException(status_code=404, detail="No sections for day")
    return {
        "hour": _hour_summary(hour),
        "day": day,
        "today": _today_key(),
        "sections": [
            {
                "index": i,
                "title": s["title"],
                "latin_title": s.get("latin_title"),
                "english": s.get("english") or "",
                "latin": s.get("latin"),
                "rubric": s.get("rubric"),
                "note": s.get("note"),
            }
            for i, s in enumerate(sections)
        ],
    }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def build_router(
    db: AsyncIOMotorDatabase,
    get_current_user: Callable,
    emergent_llm_key: str = "",
) -> APIRouter:
    router = APIRouter(prefix="/liturgy", tags=["liturgy"])

    async def _tr_fields(containers_fields):
        """Translate (dict, key) value pairs in place into the request language.
        Latin text is never passed in, so it is preserved untouched."""
        lang = get_lang()
        if lang == "en" or not containers_fields:
            return
        originals = [str(c.get(k) or "") for c, k in containers_fields]
        translated = await translate_texts(db, emergent_llm_key, originals, lang)
        for (c, k), val in zip(containers_fields, translated):
            if val:
                c[k] = val

    @router.get("")
    async def list_hours(user=Depends(get_current_user)):
        hours = [_hour_summary(h) for h in HOURS]
        external = {
            "url": "https://www.ibreviary.com/m2/breviario.php",
            "label": "iBreviary (modern Liturgy of the Hours)",
            "description": (
                "For the modern post-Vatican II text in your own "
                "language, open the official iBreviary website. Texts "
                "there are kept up to date with the day's proper."
            ),
        }
        cf = []
        for h in hours:
            cf += [(h, "name"), (h, "subtitle")]
        cf.append((external, "description"))
        await _tr_fields(cf)
        return {
            "hours": hours,
            "days": DAYS,
            "today": _today_key(),
            "external_link": external,
        }

    @router.get("/{hour_slug}")
    async def get_hour(hour_slug: str, user=Depends(get_current_user)):
        h = HOURS_BY_SLUG.get(hour_slug)
        if not h:
            raise HTTPException(status_code=404, detail="Hour not found")
        detail = _hour_detail(h)
        await _tr_fields([(detail, "name"), (detail, "subtitle"), (detail, "intro")])
        return detail

    @router.get("/{hour_slug}/{day_key}")
    async def get_hour_for_day(
        hour_slug: str,
        day_key: str,
        user=Depends(get_current_user),
    ):
        h = HOURS_BY_SLUG.get(hour_slug)
        if not h:
            raise HTTPException(status_code=404, detail="Hour not found")
        payload = _section_payload(h, day_key)
        cf = [(payload["hour"], "name"), (payload["hour"], "subtitle")]
        for s in payload["sections"]:
            cf += [(s, "title"), (s, "english"), (s, "rubric"), (s, "note")]
        await _tr_fields(cf)
        return payload

    return router

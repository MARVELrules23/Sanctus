"""Sanctus — Mass Missals Hub.

Read-only, in-app rendering of the Order of Mass for the three Roman-rite
missals supported by the Catholic Church today:

  * `novus-ordo`  — The Order of Mass of the 1970 Roman Missal
                    (Ordinary Form), English (ICEL 2010) + Latin.
  * `tlm`         — The Traditional Latin Mass / Tridentine Mass
                    (1962 Missale Romanum, Extraordinary Form), Latin
                    + a faithful English translation.
  * `ordinariate` — Divine Worship: The Missal (2015), the missal of
                    the Personal Ordinariates for former Anglicans now
                    in full communion with Rome. Cranmer-style English.

Scope (v1): "Order of Mass" only — the unchanging parts (Introductory
Rites → Concluding Rites). Sunday/daily Propers are deliberately NOT
included; they change every day and would require liturgical-calendar
sourcing. This is purely an in-app reader; no audio, no progress tracking.

All endpoints require auth (so we can analytics-track who's reading what
later) but the content itself is free for every authenticated user —
NOT premium-gated, by founder direction.

Endpoints (all prefixed `/api`):

  GET  /api/missals
       → { items: [{slug, name, subtitle, tradition, language_note,
                    accent_color, icon, section_count}] }

  GET  /api/missals/{slug}
       → { slug, name, subtitle, tradition, intro,
           sections: [{index, title, latin_title?}] }

  GET  /api/missals/{slug}/sections/{index}
       → { slug, index, title, latin_title?, latin?, english,
           rubric?, note?, prev?, next? }

`latin` and `english` are MARKDOWN-ish — each is just plain text split
into paragraphs by blank lines. The frontend renders them side-by-side
when both are present, stacked otherwise.

All text in this module is public-domain (1962 Missale Romanum) or, for
post-1970 missals, the English translation as approved by the USCCB /
ICEL is reproduced in commonly-cited liturgical excerpts. We intentionally
DO NOT scrape or include copyrighted prefaces, propers, or commentary;
only the unchanging Order of Mass.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger("sanctus.missals")


# ---------------------------------------------------------------------------
# Section helper
# ---------------------------------------------------------------------------


def _section(
    title: str,
    english: str,
    latin: Optional[str] = None,
    latin_title: Optional[str] = None,
    rubric: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a section dict. `english` and `latin` are stripped to remove
    accidental leading/trailing whitespace from triple-quoted strings."""
    return {
        "title": title,
        "latin_title": latin_title.strip() if latin_title else None,
        "english": english.strip(),
        "latin": latin.strip() if latin else None,
        "rubric": rubric.strip() if rubric else None,
        "note": note.strip() if note else None,
    }


# ===========================================================================
# 1) NOVUS ORDO — Ordinary Form of the Roman Rite (1970, English/Latin)
# ===========================================================================

NOVUS_ORDO_SECTIONS: List[Dict[str, Any]] = [
    _section(
        title="Introductory Rites · Sign of the Cross & Greeting",
        latin_title="Ritus Initiales",
        rubric="The Priest, after making the Sign of the Cross with the people, greets the assembly.",
        english=(
            "In the name of the Father, and of the Son, and of the Holy Spirit.\n"
            "R. Amen.\n\n"
            "The grace of our Lord Jesus Christ, and the love of God, and the communion of "
            "the Holy Spirit be with you all.\n"
            "R. And with your spirit."
        ),
        latin=(
            "In nómine Patris, et Fílii, et Spíritus Sancti.\n"
            "R. Amen.\n\n"
            "Grátia Dómini nostri Iesu Christi, et cáritas Dei, et communicátio Sancti "
            "Spíritus sit cum ómnibus vobis.\n"
            "R. Et cum spíritu tuo."
        ),
    ),
    _section(
        title="Penitential Act",
        latin_title="Actus Pænitentialis",
        rubric=(
            "The Priest invites the faithful to acknowledge their sins. A brief pause for "
            "silence follows. One of three forms may be used; the Confiteor is given here."
        ),
        english=(
            "I confess to almighty God\n"
            "and to you, my brothers and sisters,\n"
            "that I have greatly sinned,\n"
            "in my thoughts and in my words,\n"
            "in what I have done and in what I have failed to do,\n"
            "through my fault, through my fault,\n"
            "through my most grievous fault;\n"
            "therefore I ask blessed Mary ever-Virgin,\n"
            "all the Angels and Saints,\n"
            "and you, my brothers and sisters,\n"
            "to pray for me to the Lord our God.\n\n"
            "May almighty God have mercy on us,\n"
            "forgive us our sins,\n"
            "and bring us to everlasting life.\n"
            "R. Amen."
        ),
        latin=(
            "Confíteor Deo omnipoténti\n"
            "et vobis, fratres,\n"
            "quia peccávi nimis\n"
            "cogitatióne, verbo, ópere et omissióne:\n"
            "mea culpa, mea culpa, mea máxima culpa.\n"
            "Ídeo precor beátam Maríam semper Vírginem,\n"
            "omnes Ángelos et Sanctos,\n"
            "et vos, fratres, oráre pro me\n"
            "ad Dóminum Deum nostrum.\n\n"
            "Misereátur nostri omnípotens Deus\n"
            "et, dimíssis peccátis nostris,\n"
            "perdúcat nos ad vitam ætérnam.\n"
            "R. Amen."
        ),
    ),
    _section(
        title="Kyrie",
        latin_title="Kýrie",
        english=(
            "Lord, have mercy.\n"
            "R. Lord, have mercy.\n"
            "Christ, have mercy.\n"
            "R. Christ, have mercy.\n"
            "Lord, have mercy.\n"
            "R. Lord, have mercy."
        ),
        latin=(
            "Kýrie, eléison.\n"
            "R. Kýrie, eléison.\n"
            "Christe, eléison.\n"
            "R. Christe, eléison.\n"
            "Kýrie, eléison.\n"
            "R. Kýrie, eléison."
        ),
    ),
    _section(
        title="Gloria",
        latin_title="Glória",
        rubric="Sung or said on Sundays outside Advent and Lent, on solemnities and feasts.",
        english=(
            "Glory to God in the highest,\n"
            "and on earth peace to people of good will.\n"
            "We praise you, we bless you, we adore you, we glorify you,\n"
            "we give you thanks for your great glory,\n"
            "Lord God, heavenly King, O God, almighty Father.\n\n"
            "Lord Jesus Christ, Only Begotten Son,\n"
            "Lord God, Lamb of God, Son of the Father,\n"
            "you take away the sins of the world, have mercy on us;\n"
            "you take away the sins of the world, receive our prayer;\n"
            "you are seated at the right hand of the Father, have mercy on us.\n\n"
            "For you alone are the Holy One, you alone are the Lord,\n"
            "you alone are the Most High, Jesus Christ,\n"
            "with the Holy Spirit, in the glory of God the Father. Amen."
        ),
        latin=(
            "Glória in excélsis Deo\n"
            "et in terra pax homínibus bonæ voluntátis.\n"
            "Laudámus te, benedícimus te, adorámus te, glorificámus te,\n"
            "grátias ágimus tibi propter magnam glóriam tuam,\n"
            "Dómine Deus, Rex cæléstis, Deus Pater omnípotens.\n\n"
            "Dómine Fili unigénite, Iesu Christe,\n"
            "Dómine Deus, Agnus Dei, Fílius Patris,\n"
            "qui tollis peccáta mundi, miserére nobis;\n"
            "qui tollis peccáta mundi, súscipe deprecatiónem nostram;\n"
            "qui sedes ad déxteram Patris, miserére nobis.\n\n"
            "Quóniam tu solus Sanctus, tu solus Dóminus,\n"
            "tu solus Altíssimus, Iesu Christe,\n"
            "cum Sancto Spíritu, in glória Dei Patris. Amen."
        ),
    ),
    _section(
        title="Collect",
        latin_title="Collécta",
        rubric=(
            "The Priest invites the people to pray. After a brief silence, he proclaims the "
            "Collect — the prayer that gathers (\"col-ligit\") the intentions of the day. "
            "The text changes daily; only the dialogue is fixed."
        ),
        english=(
            "Let us pray.\n\n"
            "[The Priest proclaims the Collect of the day.]\n\n"
            "Through our Lord Jesus Christ, your Son,\n"
            "who lives and reigns with you in the unity of the Holy Spirit,\n"
            "one God, for ever and ever.\n"
            "R. Amen."
        ),
        latin=(
            "Orémus.\n\n"
            "[Collécta diei.]\n\n"
            "Per Dóminum nostrum Iesum Christum Fílium tuum,\n"
            "qui tecum vivit et regnat in unitáte Spíritus Sancti, Deus,\n"
            "per ómnia sæcula sæculórum.\n"
            "R. Amen."
        ),
    ),
    _section(
        title="Liturgy of the Word",
        latin_title="Liturgía Verbi",
        rubric=(
            "The First Reading is proclaimed (Old Testament, or Acts during Easter), "
            "followed by the Responsorial Psalm. On Sundays and Solemnities a Second "
            "Reading (Epistle) follows. The Gospel Acclamation prepares the assembly to "
            "stand for the Gospel."
        ),
        english=(
            "After the First Reading:\n"
            "The word of the Lord.\n"
            "R. Thanks be to God.\n\n"
            "Before the Gospel:\n"
            "The Lord be with you.\n"
            "R. And with your spirit.\n"
            "A reading from the holy Gospel according to N.\n"
            "R. Glory to you, O Lord.\n\n"
            "After the Gospel:\n"
            "The Gospel of the Lord.\n"
            "R. Praise to you, Lord Jesus Christ.\n\n"
            "[The Homily follows.]"
        ),
        latin=(
            "Post lectiónem:\n"
            "Verbum Dómini.\n"
            "R. Deo grátias.\n\n"
            "Ante Evangélium:\n"
            "Dóminus vobíscum.\n"
            "R. Et cum spíritu tuo.\n"
            "Léctio sancti Evangélii secúndum N.\n"
            "R. Glória tibi, Dómine.\n\n"
            "Post Evangélium:\n"
            "Verbum Dómini.\n"
            "R. Laus tibi, Christe."
        ),
    ),
    _section(
        title="Profession of Faith · The Nicene Creed",
        latin_title="Symbolum Nicænum",
        rubric="Said or sung on Sundays and Solemnities. All bow at \"and by the Holy Spirit … and became man.\"",
        english=(
            "I believe in one God,\n"
            "the Father almighty,\n"
            "maker of heaven and earth,\n"
            "of all things visible and invisible.\n\n"
            "I believe in one Lord Jesus Christ,\n"
            "the Only Begotten Son of God,\n"
            "born of the Father before all ages.\n"
            "God from God, Light from Light,\n"
            "true God from true God,\n"
            "begotten, not made, consubstantial with the Father;\n"
            "through him all things were made.\n"
            "For us men and for our salvation\n"
            "he came down from heaven,\n"
            "and by the Holy Spirit was incarnate of the Virgin Mary,\n"
            "and became man.\n"
            "For our sake he was crucified under Pontius Pilate,\n"
            "he suffered death and was buried,\n"
            "and rose again on the third day\n"
            "in accordance with the Scriptures.\n"
            "He ascended into heaven\n"
            "and is seated at the right hand of the Father.\n"
            "He will come again in glory to judge the living and the dead\n"
            "and his kingdom will have no end.\n\n"
            "I believe in the Holy Spirit, the Lord, the giver of life,\n"
            "who proceeds from the Father and the Son,\n"
            "who with the Father and the Son is adored and glorified,\n"
            "who has spoken through the prophets.\n\n"
            "I believe in one, holy, catholic and apostolic Church.\n"
            "I confess one Baptism for the forgiveness of sins\n"
            "and I look forward to the resurrection of the dead\n"
            "and the life of the world to come. Amen."
        ),
        latin=(
            "Credo in unum Deum,\n"
            "Patrem omnipoténtem,\n"
            "factórem cæli et terræ,\n"
            "visibílium ómnium et invisibílium.\n\n"
            "Et in unum Dóminum Iesum Christum,\n"
            "Fílium Dei Unigénitum,\n"
            "et ex Patre natum ante ómnia sǽcula.\n"
            "Deum de Deo, Lumen de Lúmine,\n"
            "Deum verum de Deo vero,\n"
            "génitum, non factum, consubstantiálem Patri:\n"
            "per quem ómnia facta sunt.\n"
            "Qui propter nos hómines et propter nostram salútem\n"
            "descéndit de cælis.\n"
            "Et incarnátus est de Spíritu Sancto\n"
            "ex María Vírgine, et homo factus est.\n"
            "Crucifíxus étiam pro nobis sub Póntio Piláto;\n"
            "passus et sepúltus est,\n"
            "et resurréxit tértia die, secúndum Scriptúras,\n"
            "et ascéndit in cælum, sedet ad déxteram Patris.\n"
            "Et íterum ventúrus est cum glória,\n"
            "iudicáre vivos et mórtuos,\n"
            "cuius regni non erit finis.\n\n"
            "Et in Spíritum Sanctum, Dóminum et vivificántem,\n"
            "qui ex Patre Filióque procédit.\n"
            "Qui cum Patre et Fílio simul adorátur et conglorificátur:\n"
            "qui locútus est per prophétas.\n\n"
            "Et unam, sanctam, cathólicam et apostólicam Ecclésiam.\n"
            "Confíteor unum baptísma in remissiónem peccatórum.\n"
            "Et exspécto resurrectiónem mortuórum,\n"
            "et vitam ventúri sǽculi. Amen."
        ),
    ),
    _section(
        title="Universal Prayer · Prayer of the Faithful",
        latin_title="Oratio Universalis",
        rubric=(
            "The faithful intercede for the Church, civil authorities, those weighed down by "
            "various needs, all humanity, and the salvation of the entire world."
        ),
        english=(
            "Let us pray to the Lord.\n"
            "R. Lord, hear our prayer.\n\n"
            "[Petitions are offered.]\n\n"
            "Hear the prayers of your people, O Lord,\n"
            "and grant what we ask of you.\n"
            "Through Christ our Lord.\n"
            "R. Amen."
        ),
    ),
    _section(
        title="Liturgy of the Eucharist · Preparation of the Gifts",
        latin_title="Liturgía Eucharística",
        rubric="The bread and wine are brought forward and placed on the altar.",
        english=(
            "Blessed are you, Lord God of all creation,\n"
            "for through your goodness we have received\n"
            "the bread we offer you:\n"
            "fruit of the earth and work of human hands,\n"
            "it will become for us the bread of life.\n"
            "R. Blessed be God for ever.\n\n"
            "Blessed are you, Lord God of all creation,\n"
            "for through your goodness we have received\n"
            "the wine we offer you:\n"
            "fruit of the vine and work of human hands,\n"
            "it will become our spiritual drink.\n"
            "R. Blessed be God for ever.\n\n"
            "Pray, brethren (brothers and sisters),\n"
            "that my sacrifice and yours may be acceptable to God,\n"
            "the almighty Father.\n"
            "R. May the Lord accept the sacrifice at your hands\n"
            "for the praise and glory of his name,\n"
            "for our good and the good of all his holy Church."
        ),
        latin=(
            "Benedíctus es, Dómine, Deus univérsi,\n"
            "quia de tua largitáte accépimus panem,\n"
            "quem tibi offérimus,\n"
            "fructum terræ et óperis mánuum hóminum,\n"
            "ex quo nobis fiet panis vitæ.\n"
            "R. Benedíctus Deus in sǽcula.\n\n"
            "Benedíctus es, Dómine, Deus univérsi,\n"
            "quia de tua largitáte accépimus vinum,\n"
            "quod tibi offérimus,\n"
            "fructum vitis et óperis mánuum hóminum,\n"
            "ex quo nobis fiet potus spiritális.\n"
            "R. Benedíctus Deus in sǽcula.\n\n"
            "Oráte, fratres, ut meum ac vestrum sacrifícium\n"
            "acceptábile fiat apud Deum Patrem omnipoténtem.\n"
            "R. Suscípiat Dóminus sacrifícium de mánibus tuis\n"
            "ad laudem et glóriam nóminis sui,\n"
            "ad utilitátem quoque nostram totiúsque Ecclésiæ suæ sanctæ."
        ),
    ),
    _section(
        title="Preface & Sanctus",
        latin_title="Præfátio · Sanctus",
        english=(
            "The Lord be with you.\n"
            "R. And with your spirit.\n"
            "Lift up your hearts.\n"
            "R. We lift them up to the Lord.\n"
            "Let us give thanks to the Lord our God.\n"
            "R. It is right and just.\n\n"
            "[The Priest proclaims the Preface of the day.]\n\n"
            "Holy, Holy, Holy Lord God of hosts.\n"
            "Heaven and earth are full of your glory.\n"
            "Hosanna in the highest.\n"
            "Blessed is he who comes in the name of the Lord.\n"
            "Hosanna in the highest."
        ),
        latin=(
            "Dóminus vobíscum.\n"
            "R. Et cum spíritu tuo.\n"
            "Sursum corda.\n"
            "R. Habémus ad Dóminum.\n"
            "Grátias agámus Dómino Deo nostro.\n"
            "R. Dignum et iustum est.\n\n"
            "[Præfátio diei.]\n\n"
            "Sanctus, Sanctus, Sanctus Dóminus Deus Sábaoth.\n"
            "Pleni sunt cæli et terra glória tua.\n"
            "Hosánna in excélsis.\n"
            "Benedíctus qui venit in nómine Dómini.\n"
            "Hosánna in excélsis."
        ),
    ),
    _section(
        title="Eucharistic Prayer II",
        latin_title="Prex Eucharística II",
        rubric=(
            "Of the four principal Eucharistic Prayers, the second is the shortest and is "
            "based on an ancient text attributed to Hippolytus (c. 215 A.D.). The Words of "
            "Institution and the Memorial Acclamation are reproduced here."
        ),
        english=(
            "You are indeed Holy, O Lord, the fount of all holiness.\n\n"
            "Make holy, therefore, these gifts, we pray,\n"
            "by sending down your Spirit upon them like the dewfall,\n"
            "so that they may become for us\n"
            "the Body and Blood of our Lord Jesus Christ.\n\n"
            "At the time he was betrayed and entered willingly into his Passion,\n"
            "he took bread and, giving thanks, broke it,\n"
            "and gave it to his disciples, saying:\n"
            "TAKE THIS, ALL OF YOU, AND EAT OF IT,\n"
            "FOR THIS IS MY BODY,\n"
            "WHICH WILL BE GIVEN UP FOR YOU.\n\n"
            "In a similar way, when supper was ended,\n"
            "he took the chalice and, once more giving thanks,\n"
            "he gave it to his disciples, saying:\n"
            "TAKE THIS, ALL OF YOU, AND DRINK FROM IT,\n"
            "FOR THIS IS THE CHALICE OF MY BLOOD,\n"
            "THE BLOOD OF THE NEW AND ETERNAL COVENANT,\n"
            "WHICH WILL BE POURED OUT FOR YOU AND FOR MANY\n"
            "FOR THE FORGIVENESS OF SINS.\n"
            "DO THIS IN MEMORY OF ME.\n\n"
            "The mystery of faith.\n"
            "R. We proclaim your Death, O Lord,\n"
            "and profess your Resurrection\n"
            "until you come again."
        ),
        latin=(
            "Vere Sanctus es, Dómine, fons omnis sanctitátis.\n\n"
            "Hæc ergo dona, quǽsumus, Spíritus tui rore sanctífica,\n"
            "ut nobis Corpus et Sanguis fiant\n"
            "Dómini nostri Iesu Christi.\n\n"
            "Qui cum Passióni voluntárie traderétur,\n"
            "accépit panem et grátias agens fregit,\n"
            "dedítque discípulis suis, dicens:\n"
            "ACCÍPITE ET MANDUCÁTE EX HOC OMNES:\n"
            "HOC EST ENIM CORPUS MEUM,\n"
            "QUOD PRO VOBIS TRADÉTUR.\n\n"
            "Símili modo, postquam cenátum est,\n"
            "accípiens et cálicem, íterum tibi grátias agens dedit discípulis suis, dicens:\n"
            "ACCÍPITE ET BÍBITE EX EO OMNES:\n"
            "HIC EST ENIM CALIX SÁNGUINIS MEI\n"
            "NOVI ET ÆTÉRNI TESTAMÉNTI,\n"
            "QUI PRO VOBIS ET PRO MULTIS EFFUNDÉTUR\n"
            "IN REMISSIÓNEM PECCATÓRUM.\n"
            "HOC FÁCITE IN MEAM COMMEMORATIÓNEM.\n\n"
            "Mystérium fídei.\n"
            "R. Mortem tuam annuntiámus, Dómine,\n"
            "et tuam resurrectiónem confitémur, donec vénias."
        ),
    ),
    _section(
        title="Final Doxology",
        latin_title="Doxología finalis",
        english=(
            "Through him, and with him, and in him,\n"
            "O God, almighty Father,\n"
            "in the unity of the Holy Spirit,\n"
            "all glory and honor is yours,\n"
            "for ever and ever.\n"
            "R. Amen."
        ),
        latin=(
            "Per ipsum, et cum ipso, et in ipso,\n"
            "est tibi Deo Patri omnipoténti,\n"
            "in unitáte Spíritus Sancti,\n"
            "omnis honor et glória\n"
            "per ómnia sǽcula sæculórum.\n"
            "R. Amen."
        ),
    ),
    _section(
        title="Communion Rite · The Lord's Prayer",
        latin_title="Ritus Communiónis",
        english=(
            "At the Savior's command and formed by divine teaching, we dare to say:\n\n"
            "Our Father, who art in heaven,\n"
            "hallowed be thy name;\n"
            "thy kingdom come,\n"
            "thy will be done on earth as it is in heaven.\n"
            "Give us this day our daily bread,\n"
            "and forgive us our trespasses,\n"
            "as we forgive those who trespass against us;\n"
            "and lead us not into temptation,\n"
            "but deliver us from evil.\n\n"
            "Deliver us, Lord, we pray, from every evil,\n"
            "graciously grant peace in our days,\n"
            "that, by the help of your mercy,\n"
            "we may be always free from sin\n"
            "and safe from all distress,\n"
            "as we await the blessed hope\n"
            "and the coming of our Savior, Jesus Christ.\n"
            "R. For the kingdom, the power and the glory are yours\n"
            "now and for ever."
        ),
        latin=(
            "Præcéptis salutáribus móniti, et divína institutióne formáti, audémus dícere:\n\n"
            "Pater noster, qui es in cælis:\n"
            "sanctificétur nomen tuum;\n"
            "advéniat regnum tuum;\n"
            "fiat volúntas tua, sicut in cælo, et in terra.\n"
            "Panem nostrum cotidiánum da nobis hódie;\n"
            "et dimítte nobis débita nostra,\n"
            "sicut et nos dimíttimus debitóribus nostris;\n"
            "et ne nos indúcas in tentatiónem;\n"
            "sed líbera nos a malo.\n\n"
            "Líbera nos, quǽsumus, Dómine, ab ómnibus malis,\n"
            "da propítius pacem in diébus nostris,\n"
            "ut, ope misericórdiæ tuæ adiúti,\n"
            "et a peccáto simus semper líberi\n"
            "et ab omni perturbatióne secúri:\n"
            "exspectántes beátam spem\n"
            "et advéntum Salvatóris nostri Iesu Christi.\n"
            "R. Quia tuum est regnum, et potéstas, et glória in sǽcula."
        ),
    ),
    _section(
        title="Sign of Peace · Agnus Dei",
        latin_title="Signum Pacis · Agnus Dei",
        english=(
            "Lord Jesus Christ, who said to your Apostles:\n"
            "Peace I leave you, my peace I give you,\n"
            "look not on our sins, but on the faith of your Church,\n"
            "and graciously grant her peace and unity\n"
            "in accordance with your will.\n"
            "Who live and reign for ever and ever.\n"
            "R. Amen.\n\n"
            "The peace of the Lord be with you always.\n"
            "R. And with your spirit.\n\n"
            "Let us offer each other the sign of peace.\n\n"
            "Lamb of God, you take away the sins of the world, have mercy on us.\n"
            "Lamb of God, you take away the sins of the world, have mercy on us.\n"
            "Lamb of God, you take away the sins of the world, grant us peace."
        ),
        latin=(
            "Agnus Dei, qui tollis peccáta mundi, miserére nobis.\n"
            "Agnus Dei, qui tollis peccáta mundi, miserére nobis.\n"
            "Agnus Dei, qui tollis peccáta mundi, dona nobis pacem."
        ),
    ),
    _section(
        title="Communion",
        latin_title="Communio",
        rubric=(
            "The Priest holds the Host slightly raised above the paten or chalice, showing it "
            "to the people."
        ),
        english=(
            "Behold the Lamb of God,\n"
            "behold him who takes away the sins of the world.\n"
            "Blessed are those called to the supper of the Lamb.\n\n"
            "R. Lord, I am not worthy that you should enter under my roof,\n"
            "but only say the word and my soul shall be healed.\n\n"
            "[At the moment of receiving:]\n"
            "The Body of Christ. R. Amen.\n"
            "The Blood of Christ. R. Amen."
        ),
        latin=(
            "Ecce Agnus Dei, ecce qui tollit peccáta mundi.\n"
            "Beáti qui ad cenam Agni vocáti sunt.\n\n"
            "R. Dómine, non sum dignus, ut intres sub tectum meum,\n"
            "sed tantum dic verbo, et sanábitur ánima mea.\n\n"
            "[Tempore Communiónis:]\n"
            "Corpus Christi. R. Amen.\n"
            "Sanguis Christi. R. Amen."
        ),
    ),
    _section(
        title="Concluding Rites · Blessing & Dismissal",
        latin_title="Ritus Conclusiónis",
        english=(
            "The Lord be with you.\n"
            "R. And with your spirit.\n\n"
            "May almighty God bless you,\n"
            "the Father, and the Son, and the Holy Spirit.\n"
            "R. Amen.\n\n"
            "Go forth, the Mass is ended. [or: Go in peace, glorifying the Lord by your life.]\n"
            "R. Thanks be to God."
        ),
        latin=(
            "Dóminus vobíscum.\n"
            "R. Et cum spíritu tuo.\n\n"
            "Benedícat vos omnípotens Deus,\n"
            "Pater, et Fílius, et Spíritus Sanctus.\n"
            "R. Amen.\n\n"
            "Ite, missa est.\n"
            "R. Deo grátias."
        ),
    ),
]


# ===========================================================================
# 2) TRADITIONAL LATIN MASS — 1962 Missale Romanum
# ===========================================================================

TLM_SECTIONS: List[Dict[str, Any]] = [
    _section(
        title="Prayers at the Foot of the Altar",
        latin_title="Orationes ante Gradus Altáris",
        rubric=(
            "After the Asperges (when present), the Priest, vested for Mass, ascends with "
            "his ministers to the foot of the altar, where he makes the Sign of the Cross "
            "and begins Psalm 42 — \"I will go in unto the altar of God…\""
        ),
        english=(
            "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.\n\n"
            "I will go in unto the altar of God.\n"
            "R. Unto God who giveth joy to my youth.\n\n"
            "Judge me, O God, and distinguish my cause from the nation that is not holy:\n"
            "deliver me from the unjust and deceitful man.\n"
            "R. For Thou, O God, art my strength: why hast Thou cast me off?\n"
            "and why do I go sorrowful whilst the enemy afflicteth me?\n\n"
            "Send forth Thy light and Thy truth: they have conducted me,\n"
            "and brought me unto Thy holy hill, and into Thy tabernacles.\n"
            "R. And I will go in unto the altar of God:\n"
            "to God who giveth joy to my youth.\n\n"
            "Our help is in the name of the Lord.\n"
            "R. Who made heaven and earth."
        ),
        latin=(
            "In nómine Patris, et Fílii, et Spíritus Sancti. Amen.\n\n"
            "Introíbo ad altáre Dei.\n"
            "R. Ad Deum qui lætíficat iuventútem meam.\n\n"
            "Iúdica me, Deus, et discérne causam meam de gente non sancta:\n"
            "ab hómine iníquo et dolóso érue me.\n"
            "R. Quia tu es, Deus, fortitúdo mea: quare me reppulísti?\n"
            "et quare tristis incédo, dum afflígit me inimícus?\n\n"
            "Emítte lucem tuam et veritátem tuam: ipsa me deduxérunt,\n"
            "et adduxérunt in montem sanctum tuum et in tabernácula tua.\n"
            "R. Et introíbo ad altáre Dei:\n"
            "ad Deum qui lætíficat iuventútem meam.\n\n"
            "Adiutórium nostrum in nómine Dómini.\n"
            "R. Qui fecit cælum et terram."
        ),
    ),
    _section(
        title="The Confiteor",
        latin_title="Confíteor",
        rubric=(
            "The Priest bows profoundly and confesses his sins; the servers respond. The "
            "servers then confess in turn while the Priest stands erect."
        ),
        english=(
            "I confess to almighty God, to blessed Mary ever Virgin,\n"
            "to blessed Michael the Archangel, to blessed John the Baptist,\n"
            "to the holy Apostles Peter and Paul, to all the Saints,\n"
            "and to you, brethren,\n"
            "that I have sinned exceedingly in thought, word, and deed,\n"
            "through my fault, through my fault, through my most grievous fault.\n"
            "Therefore I beseech blessed Mary ever Virgin,\n"
            "blessed Michael the Archangel, blessed John the Baptist,\n"
            "the holy Apostles Peter and Paul, all the Saints,\n"
            "and you, brethren, to pray for me to the Lord our God.\n\n"
            "R. May almighty God have mercy on thee,\n"
            "forgive thee thy sins, and bring thee to life everlasting.\n"
            "Amen."
        ),
        latin=(
            "Confíteor Deo omnipoténti, beátæ Maríæ semper Vírgini,\n"
            "beáto Michaéli Archángelo, beáto Ioánni Baptístæ,\n"
            "sanctis Apóstolis Petro et Paulo, ómnibus Sanctis,\n"
            "et vobis, fratres:\n"
            "quia peccávi nimis cogitatióne, verbo et ópere:\n"
            "mea culpa, mea culpa, mea máxima culpa.\n"
            "Ideo precor beátam Maríam semper Vírginem,\n"
            "beátum Michaélem Archángelum, beátum Ioánnem Baptístam,\n"
            "sanctos Apóstolos Petrum et Paulum, omnes Sanctos,\n"
            "et vos, fratres, oráre pro me ad Dóminum Deum nostrum.\n\n"
            "R. Misereátur tui omnípotens Deus,\n"
            "et, dimíssis peccátis tuis, perdúcat te ad vitam ætérnam.\n"
            "Amen."
        ),
    ),
    _section(
        title="Introit · Kyrie · Gloria",
        latin_title="Introitus · Kýrie · Glória",
        rubric=(
            "The Priest ascends the altar, kisses it, and proceeds to the Epistle side to "
            "read the Introit (the proper antiphon for the Mass of the day). The Kyrie, "
            "ninefold, follows. The Gloria is intoned by the Priest when prescribed."
        ),
        english=(
            "Lord, have mercy. R. Lord, have mercy.\n"
            "Lord, have mercy. R. Lord, have mercy.\n"
            "Lord, have mercy. R. Lord, have mercy.\n"
            "Christ, have mercy. R. Christ, have mercy.\n"
            "Christ, have mercy. R. Christ, have mercy.\n"
            "Christ, have mercy. R. Christ, have mercy.\n"
            "Lord, have mercy. R. Lord, have mercy.\n"
            "Lord, have mercy. R. Lord, have mercy.\n"
            "Lord, have mercy. R. Lord, have mercy.\n\n"
            "Glory be to God on high, and on earth peace to men of good will.\n"
            "We praise Thee, we bless Thee, we adore Thee, we glorify Thee.\n"
            "We give Thee thanks for Thy great glory,\n"
            "O Lord God, heavenly King, God the Father Almighty.\n"
            "O Lord Jesus Christ, the only-begotten Son.\n"
            "O Lord God, Lamb of God, Son of the Father.\n"
            "Who takest away the sins of the world, have mercy on us.\n"
            "Who takest away the sins of the world, receive our prayer.\n"
            "Who sittest at the right hand of the Father, have mercy on us.\n"
            "For Thou alone art holy. Thou alone art the Lord.\n"
            "Thou alone, O Jesus Christ, art most high.\n"
            "With the Holy Ghost, in the glory of God the Father. Amen."
        ),
        latin=(
            "Kýrie, eléison. (ter)\n"
            "Christe, eléison. (ter)\n"
            "Kýrie, eléison. (ter)\n\n"
            "Glória in excélsis Deo, et in terra pax homínibus bonæ voluntátis.\n"
            "Laudámus te. Benedícimus te. Adorámus te. Glorificámus te.\n"
            "Grátias ágimus tibi propter magnam glóriam tuam.\n"
            "Dómine Deus, Rex cæléstis, Deus Pater omnípotens.\n"
            "Dómine Fili unigénite, Iesu Christe.\n"
            "Dómine Deus, Agnus Dei, Fílius Patris.\n"
            "Qui tollis peccáta mundi, miserére nobis.\n"
            "Qui tollis peccáta mundi, súscipe deprecatiónem nostram.\n"
            "Qui sedes ad déxteram Patris, miserére nobis.\n"
            "Quóniam tu solus Sanctus. Tu solus Dóminus.\n"
            "Tu solus Altíssimus, Iesu Christe.\n"
            "Cum Sancto Spíritu, in glória Dei Patris. Amen."
        ),
    ),
    _section(
        title="Collect · Epistle · Gradual · Gospel",
        latin_title="Collécta · Epístola · Graduále · Evangélium",
        rubric=(
            "The Priest sings or says \"Dóminus vobíscum,\" then \"Orémus,\" and reads the "
            "Collect(s) of the day. The Epistle and Gradual follow. Before the Gospel the "
            "Priest bows at the middle of the altar and prays the Munda cor meum (\"Cleanse "
            "my heart\"). At the end of the Gospel he kisses the book and says, \"Per "
            "evangélica dicta deleántur nostra delícta.\""
        ),
        english=(
            "The Lord be with you. R. And with thy spirit.\n"
            "Let us pray.\n"
            "[The Collect, Epistle, and Gradual of the day are read.]\n\n"
            "Before the Gospel:\n"
            "The Lord be with you. R. And with thy spirit.\n"
            "The continuation of the holy Gospel according to N.\n"
            "R. Glory be to Thee, O Lord.\n\n"
            "After the Gospel:\n"
            "R. Praise be to Thee, O Christ.\n"
            "By the words of the Gospel may our sins be blotted out."
        ),
        latin=(
            "Dóminus vobíscum. R. Et cum spíritu tuo.\n"
            "Orémus.\n"
            "[Collécta, Epístola, Graduále diéi.]\n\n"
            "Ante Evangélium:\n"
            "Dóminus vobíscum. R. Et cum spíritu tuo.\n"
            "Sequéntia sancti Evangélii secúndum N.\n"
            "R. Glória tibi, Dómine.\n\n"
            "Post Evangélium:\n"
            "R. Laus tibi, Christe.\n"
            "Per evangélica dicta deleántur nostra delícta."
        ),
    ),
    _section(
        title="Credo",
        latin_title="Credo",
        rubric="When prescribed, the Priest intones the Creed. All kneel at \"Et incarnátus est… et homo factus est.\"",
        english=(
            "I believe in one God, the Father Almighty,\n"
            "Maker of heaven and earth, and of all things visible and invisible.\n"
            "And in one Lord Jesus Christ, the only-begotten Son of God,\n"
            "born of the Father before all ages.\n"
            "God of God; Light of Light; true God of true God;\n"
            "begotten, not made; of one substance with the Father,\n"
            "by whom all things were made.\n"
            "Who for us men, and for our salvation, came down from heaven,\n"
            "AND WAS INCARNATE BY THE HOLY GHOST OF THE VIRGIN MARY:\n"
            "AND WAS MADE MAN.\n"
            "He was crucified also for us, suffered under Pontius Pilate, and was buried.\n"
            "And the third day He rose again according to the Scriptures,\n"
            "and ascended into heaven, and sitteth at the right hand of the Father.\n"
            "And He shall come again with glory, to judge the living and the dead;\n"
            "of whose kingdom there shall be no end.\n"
            "And in the Holy Ghost, the Lord and Giver of life,\n"
            "who proceedeth from the Father and the Son,\n"
            "who together with the Father and the Son is adored and glorified;\n"
            "who spoke by the Prophets.\n"
            "And in one, holy, catholic, and apostolic Church.\n"
            "I confess one baptism for the remission of sins.\n"
            "And I look for the resurrection of the dead.\n"
            "And the life of the world to come. Amen."
        ),
        latin=(
            "Credo in unum Deum, Patrem omnipoténtem,\n"
            "factórem cæli et terræ, visibílium ómnium et invisibílium.\n"
            "Et in unum Dóminum Iesum Christum, Fílium Dei unigénitum.\n"
            "Et ex Patre natum ante ómnia sǽcula.\n"
            "Deum de Deo, lumen de lúmine, Deum verum de Deo vero.\n"
            "Génitum, non factum, consubstantiálem Patri:\n"
            "per quem ómnia facta sunt.\n"
            "Qui propter nos hómines et propter nostram salútem descéndit de cælis.\n"
            "ET INCARNÁTUS EST DE SPÍRITU SANCTO EX MARÍA VÍRGINE:\n"
            "ET HOMO FACTUS EST.\n"
            "Crucifíxus étiam pro nobis: sub Póntio Piláto passus, et sepúltus est.\n"
            "Et resurréxit tértia die, secúndum Scriptúras.\n"
            "Et ascéndit in cælum: sedet ad déxteram Patris.\n"
            "Et íterum ventúrus est cum glória iudicáre vivos et mórtuos:\n"
            "cuius regni non erit finis.\n"
            "Et in Spíritum Sanctum, Dóminum et vivificántem:\n"
            "qui ex Patre Filióque procédit.\n"
            "Qui cum Patre et Fílio simul adorátur et conglorificátur:\n"
            "qui locútus est per Prophétas.\n"
            "Et unam, sanctam, cathólicam et apostólicam Ecclésiam.\n"
            "Confíteor unum baptísma in remissiónem peccatórum.\n"
            "Et exspécto resurrectiónem mortuórum.\n"
            "Et vitam ventúri sǽculi. Amen."
        ),
    ),
    _section(
        title="Offertory & Lavabo",
        latin_title="Offertorium · Lavábo",
        rubric=(
            "The Priest uncovers the chalice, offers the host on the paten, mingles water "
            "with the wine in the chalice (a sign of Christ's two natures), and offers the "
            "chalice. He then washes his fingers at the side of the altar (the Lavabo)."
        ),
        english=(
            "Receive, O Holy Father, almighty and eternal God,\n"
            "this unspotted host, which I, Thine unworthy servant,\n"
            "offer unto Thee, my living and true God,\n"
            "for mine innumerable sins, offenses, and negligences,\n"
            "and for all here present;\n"
            "as also for all faithful Christians both living and dead,\n"
            "that it may avail both me and them to salvation, unto life everlasting. Amen.\n\n"
            "O God, who in creating man didst exalt his nature very wonderfully,\n"
            "and yet more wonderfully didst establish it anew:\n"
            "by the mystery signified in the mingling of this water and wine,\n"
            "grant us to have part in the Godhead of Him,\n"
            "who hath vouchsafed to become partaker of our humanity,\n"
            "Jesus Christ, Thy Son, our Lord. Amen.\n\n"
            "I will wash my hands among the innocent,\n"
            "and will compass Thine altar, O Lord."
        ),
        latin=(
            "Súscipe, sancte Pater, omnípotens ætérne Deus,\n"
            "hanc immaculátam hóstiam,\n"
            "quam ego indígnus fámulus tuus óffero tibi, Deo meo vivo et vero,\n"
            "pro innumerabílibus peccátis, et offensiónibus, et negligéntiis meis,\n"
            "et pro ómnibus circumstántibus,\n"
            "sed et pro ómnibus fidélibus christiánis vivis atque defúnctis:\n"
            "ut mihi et illis profíciat ad salútem in vitam ætérnam. Amen.\n\n"
            "Deus, qui humánæ substántiæ dignitátem mirabíliter condidísti,\n"
            "et mirabílius reformásti:\n"
            "da nobis per huius aquæ et vini mystérium,\n"
            "eius divinitátis esse consórtes,\n"
            "qui humanitátis nostræ fíeri dignátus est párticeps,\n"
            "Iesus Christus, Fílius tuus, Dóminus noster. Amen.\n\n"
            "Lavábo inter innocéntes manus meas,\n"
            "et circúmdabo altáre tuum, Dómine."
        ),
    ),
    _section(
        title="Orate Fratres · Secret · Preface · Sanctus",
        latin_title="Oráte Fratres · Secréta · Præfátio · Sanctus",
        rubric=(
            "The Priest turns to the people: \"Pray, brethren…\" and the servers respond. The "
            "Secret (a silent prayer over the offerings) follows. He then chants the Preface "
            "dialogue and the Preface of the day, ending with the Sanctus, which the people "
            "or schola sing."
        ),
        english=(
            "Pray, brethren, that my Sacrifice and yours may be acceptable\n"
            "to God, the Father almighty.\n"
            "R. May the Lord receive the Sacrifice from thy hands,\n"
            "to the praise and glory of His name,\n"
            "for our benefit, and that of all His holy Church.\n\n"
            "The Lord be with you. R. And with thy spirit.\n"
            "Lift up your hearts. R. We have lifted them up to the Lord.\n"
            "Let us give thanks to the Lord our God.\n"
            "R. It is meet and just.\n\n"
            "[The Preface of the day is chanted.]\n\n"
            "Holy, Holy, Holy, Lord God of Hosts.\n"
            "Heaven and earth are full of Thy glory. Hosanna in the highest.\n"
            "Blessed is He that cometh in the name of the Lord. Hosanna in the highest."
        ),
        latin=(
            "Oráte, fratres: ut meum ac vestrum sacrifícium acceptábile fiat\n"
            "apud Deum Patrem omnipoténtem.\n"
            "R. Suscípiat Dóminus sacrifícium de mánibus tuis,\n"
            "ad laudem et glóriam nóminis sui,\n"
            "ad utilitátem quoque nostram totiúsque Ecclésiæ suæ sanctæ.\n\n"
            "Dóminus vobíscum. R. Et cum spíritu tuo.\n"
            "Sursum corda. R. Habémus ad Dóminum.\n"
            "Grátias agámus Dómino Deo nostro. R. Dignum et iustum est.\n\n"
            "[Præfátio diéi.]\n\n"
            "Sanctus, Sanctus, Sanctus Dóminus, Deus Sábaoth.\n"
            "Pleni sunt cæli et terra glória tua. Hosánna in excélsis.\n"
            "Benedíctus qui venit in nómine Dómini. Hosánna in excélsis."
        ),
    ),
    _section(
        title="The Roman Canon · Te Igitur",
        latin_title="Canon Romanus · Te ígitur",
        rubric=(
            "The Canon of the Mass is prayed in silence, the heart of the Roman liturgy. "
            "The Priest, with hands extended, begins: \"Te ígitur…\" praying for the Pope, "
            "the bishop, all the faithful, and the saints. The Memento prayer commemorates "
            "the living."
        ),
        english=(
            "Most merciful Father, we humbly pray and beseech Thee,\n"
            "through Jesus Christ Thy Son, our Lord, to accept and to bless\n"
            "these gifts, these presents, these holy unspotted Sacrifices,\n"
            "which we offer up to Thee, in the first place, for Thy holy Catholic Church,\n"
            "that it may please Thee to grant her peace,\n"
            "to preserve, unite, and govern her throughout the world;\n"
            "as also for Thy servant N., our Pope, and N., our Bishop,\n"
            "and for all who, holding to the truth, hand on the catholic and apostolic faith.\n\n"
            "Be mindful, O Lord, of Thy servants and handmaids, N. and N.,\n"
            "and of all here present, whose faith and devotion are known unto Thee,\n"
            "for whom we offer, or who offer up to Thee, this Sacrifice of praise…"
        ),
        latin=(
            "Te ígitur, clementíssime Pater,\n"
            "per Iesum Christum Fílium tuum, Dóminum nostrum,\n"
            "súpplices rogámus, ac pétimus,\n"
            "uti accépta hábeas, et benedícas\n"
            "hæc dona, hæc múnera, hæc sancta sacrifícia illibáta;\n"
            "in primis, quæ tibi offérimus pro Ecclésia tua sancta cathólica:\n"
            "quam pacificáre, custodíre, adunáre, et régere dignéris toto orbe terrárum:\n"
            "una cum fámulo tuo Papa nostro N., et Antístite nostro N.,\n"
            "et ómnibus orthodóxis atque cathólicæ et apostólicæ fídei cultóribus.\n\n"
            "Meménto, Dómine, famulórum famularúmque tuárum N. et N.,\n"
            "et ómnium circumstántium, quorum tibi fides cógnita est et nota devótio,\n"
            "pro quibus tibi offérimus, vel qui tibi ófferunt hoc sacrifícium laudis…"
        ),
    ),
    _section(
        title="The Consecration",
        latin_title="Consecrátio",
        rubric=(
            "At the heart of the Canon, the Priest pronounces the words of Christ over the "
            "bread, genuflects, elevates the Host for the adoration of the faithful, and "
            "genuflects again. The same is then done over the chalice."
        ),
        english=(
            "WHO, THE DAY BEFORE HE SUFFERED, TOOK BREAD\n"
            "INTO HIS HOLY AND VENERABLE HANDS,\n"
            "AND WITH EYES LIFTED UP TOWARDS HEAVEN, UNTO THEE,\n"
            "GOD, HIS ALMIGHTY FATHER,\n"
            "GIVING THANKS TO THEE, HE BLESSED, BROKE, AND GAVE IT\n"
            "TO HIS DISCIPLES, SAYING: TAKE AND EAT YE ALL OF THIS,\n\n"
            "FOR THIS IS MY BODY.\n\n"
            "IN LIKE MANNER, AFTER HE HAD SUPPED,\n"
            "TAKING ALSO THIS GOODLY CHALICE INTO HIS HOLY AND VENERABLE HANDS,\n"
            "ALSO GIVING THEE THANKS, HE BLESSED, AND GAVE IT TO HIS DISCIPLES, SAYING:\n"
            "TAKE AND DRINK YE ALL OF IT,\n\n"
            "FOR THIS IS THE CHALICE OF MY BLOOD,\n"
            "OF THE NEW AND ETERNAL TESTAMENT:\n"
            "THE MYSTERY OF FAITH:\n"
            "WHICH SHALL BE SHED FOR YOU AND FOR MANY,\n"
            "UNTO THE REMISSION OF SINS.\n\n"
            "AS OFTEN AS YE DO THESE THINGS,\n"
            "YE SHALL DO THEM IN REMEMBRANCE OF ME."
        ),
        latin=(
            "QUI, PRÍDIE QUAM PATERÉTUR, ACCÉPIT PANEM\n"
            "IN SANCTAS AC VENERÁBILES MANUS SUAS,\n"
            "ET ELEVÁTIS ÓCULIS IN CÆLUM\n"
            "AD TE DEUM, PATREM SUUM OMNIPOTÉNTEM,\n"
            "TIBI GRÁTIAS AGENS, BENEDÍXIT, FREGIT,\n"
            "DEDÍTQUE DISCÍPULIS SUIS, DICENS:\n"
            "ACCÍPITE, ET MANDUCÁTE EX HOC OMNES:\n\n"
            "HOC EST ENIM CORPUS MEUM.\n\n"
            "SÍMILI MODO POSTQUAM CENÁTUM EST,\n"
            "ACCÍPIENS ET HUNC PRÆCLÁRUM CÁLICEM\n"
            "IN SANCTAS AC VENERÁBILES MANUS SUAS:\n"
            "ITEM TIBI GRÁTIAS AGENS, BENEDÍXIT, DEDÍTQUE DISCÍPULIS SUIS, DICENS:\n"
            "ACCÍPITE, ET BÍBITE EX EO OMNES:\n\n"
            "HIC EST ENIM CALIX SÁNGUINIS MEI,\n"
            "NOVI ET ÆTÉRNI TESTAMÉNTI:\n"
            "MYSTÉRIUM FÍDEI:\n"
            "QUI PRO VOBIS ET PRO MULTIS EFFUNDÉTUR\n"
            "IN REMISSIÓNEM PECCATÓRUM.\n\n"
            "HÆC QUOTIESCÚMQUE FECÉRITIS,\n"
            "IN MEI MEMÓRIAM FACIÉTIS."
        ),
    ),
    _section(
        title="Pater Noster",
        latin_title="Pater Noster",
        english=(
            "Let us pray. Taught by Thy saving precepts and following Thy divine instruction,\n"
            "we make bold to say:\n\n"
            "Our Father, who art in heaven, hallowed be Thy name; Thy kingdom come;\n"
            "Thy will be done on earth as it is in heaven.\n"
            "Give us this day our daily bread,\n"
            "and forgive us our trespasses, as we forgive those who trespass against us;\n"
            "and lead us not into temptation.\n"
            "R. But deliver us from evil.\n"
            "Amen."
        ),
        latin=(
            "Orémus. Præcéptis salutáribus móniti, et divína institutióne formáti,\n"
            "audémus dícere:\n\n"
            "Pater noster, qui es in cælis: sanctificétur nomen tuum;\n"
            "advéniat regnum tuum; fiat volúntas tua, sicut in cælo, et in terra.\n"
            "Panem nostrum cotidiánum da nobis hódie;\n"
            "et dimítte nobis débita nostra, sicut et nos dimíttimus debitóribus nostris.\n"
            "Et ne nos indúcas in tentatiónem.\n"
            "R. Sed líbera nos a malo.\n"
            "Amen."
        ),
    ),
    _section(
        title="Agnus Dei · Communion",
        latin_title="Agnus Dei · Commúnio",
        rubric=(
            "After the Pax (kiss of peace, at Solemn Mass), the Priest strikes his breast at "
            "the Agnus Dei and prays the three preparation prayers before Communion: Dómine "
            "Iesu Christe; Percéptio Córporis tui; and Pánem cæléstem accípiam. He then takes "
            "the Host, saying, \"Dómine, non sum dignus…\" thrice, striking his breast each "
            "time. The faithful do likewise."
        ),
        english=(
            "Lamb of God, who takest away the sins of the world, have mercy on us.\n"
            "Lamb of God, who takest away the sins of the world, have mercy on us.\n"
            "Lamb of God, who takest away the sins of the world, grant us peace.\n\n"
            "Lord, I am not worthy that Thou shouldst enter under my roof;\n"
            "say but the word, and my soul shall be healed. (×3)\n\n"
            "[At Communion:]\n"
            "May the Body of our Lord Jesus Christ keep my soul unto life everlasting. Amen."
        ),
        latin=(
            "Agnus Dei, qui tollis peccáta mundi, miserére nobis.\n"
            "Agnus Dei, qui tollis peccáta mundi, miserére nobis.\n"
            "Agnus Dei, qui tollis peccáta mundi, dona nobis pacem.\n\n"
            "Dómine, non sum dignus, ut intres sub tectum meum:\n"
            "sed tantum dic verbo, et sanábitur ánima mea. (ter)\n\n"
            "[In Communióne:]\n"
            "Corpus Dómini nostri Iesu Christi custódiat ánimam meam in vitam ætérnam. Amen."
        ),
    ),
    _section(
        title="Communion · Postcommunion · Ite Missa Est",
        latin_title="Commúnio · Postcommúnio · Ite, missa est",
        rubric=(
            "After purifying the chalice, the Priest reads the Communion Antiphon and then "
            "the Postcommunion prayer. He then turns to the people: \"Dóminus vobíscum,\" "
            "and the Deacon (or Priest) chants the dismissal."
        ),
        english=(
            "The Lord be with you. R. And with thy spirit.\n\n"
            "Let us pray.\n"
            "[The Postcommunion prayer is read.]\n"
            "Through our Lord Jesus Christ, Thy Son,\n"
            "who liveth and reigneth with Thee in the unity of the Holy Ghost,\n"
            "God, world without end. R. Amen.\n\n"
            "The Lord be with you. R. And with thy spirit.\n"
            "Go, the Mass is ended.\n"
            "R. Thanks be to God.\n\n"
            "May the homage of my service be pleasing unto Thee, O most Holy Trinity:\n"
            "and grant that the Sacrifice which I, though unworthy, have offered up\n"
            "in the sight of Thy majesty, may be acceptable unto Thee,\n"
            "and through Thy mercy be a propitiation for me\n"
            "and for those for whom I have offered it. Through Christ our Lord. Amen."
        ),
        latin=(
            "Dóminus vobíscum. R. Et cum spíritu tuo.\n\n"
            "Orémus.\n"
            "[Postcommúnio.]\n"
            "Per Dóminum nostrum Iesum Christum Fílium tuum,\n"
            "qui tecum vivit et regnat in unitáte Spíritus Sancti, Deus,\n"
            "per ómnia sǽcula sæculórum. R. Amen.\n\n"
            "Dóminus vobíscum. R. Et cum spíritu tuo.\n"
            "Ite, missa est.\n"
            "R. Deo grátias.\n\n"
            "Pláceat tibi, sancta Trínitas, obséquium servitútis meæ:\n"
            "et præsta, ut sacrifícium, quod óculis tuæ maiestátis indígnus óbtuli,\n"
            "tibi sit acceptábile, mihíque, et ómnibus pro quibus illud óbtuli,\n"
            "sit, te miseránte, propitiábile. Per Christum, Dóminum nostrum. Amen."
        ),
    ),
    _section(
        title="The Last Gospel · John 1:1–14",
        latin_title="Últimum Evangélium · Ioán. 1:1–14",
        rubric=(
            "After the final blessing, the Priest moves to the Gospel side of the altar and "
            "reads the Prologue of St. John. At the words, \"And the Word was made flesh,\" "
            "all genuflect. This Gospel proclaims the great mystery of the Incarnation as "
            "the consummation of the Mass."
        ),
        english=(
            "The Lord be with you. R. And with thy spirit.\n"
            "The beginning of the holy Gospel according to John.\n"
            "R. Glory be to Thee, O Lord.\n\n"
            "In the beginning was the Word, and the Word was with God,\n"
            "and the Word was God. The same was in the beginning with God.\n"
            "All things were made by Him, and without Him was made nothing that was made.\n"
            "In Him was life, and the life was the light of men:\n"
            "and the light shineth in darkness, and the darkness did not comprehend it.\n"
            "There was a man sent from God, whose name was John.\n"
            "This man came for a witness, to give testimony of the light,\n"
            "that all men might believe through him. He was not the light,\n"
            "but was to give testimony of the light.\n"
            "That was the true light, which enlighteneth every man that cometh into this world.\n"
            "He was in the world, and the world was made by Him,\n"
            "and the world knew Him not.\n"
            "He came unto His own, and His own received Him not.\n"
            "But as many as received Him, He gave them power\n"
            "to be made the sons of God, to them that believe in His name:\n"
            "who are born, not of blood, nor of the will of the flesh,\n"
            "nor of the will of man, but of God.\n\n"
            "AND THE WORD WAS MADE FLESH, [all genuflect] AND DWELT AMONG US:\n"
            "and we saw His glory, the glory as it were of the only-begotten of the Father,\n"
            "full of grace and truth.\n\n"
            "R. Thanks be to God."
        ),
        latin=(
            "Dóminus vobíscum. R. Et cum spíritu tuo.\n"
            "Inítium sancti Evangélii secúndum Ioánnem.\n"
            "R. Glória tibi, Dómine.\n\n"
            "In princípio erat Verbum, et Verbum erat apud Deum,\n"
            "et Deus erat Verbum. Hoc erat in princípio apud Deum.\n"
            "Ómnia per ipsum facta sunt: et sine ipso factum est nihil, quod factum est.\n"
            "In ipso vita erat, et vita erat lux hóminum:\n"
            "et lux in ténebris lucet, et ténebræ eam non comprehendérunt.\n"
            "Fuit homo missus a Deo, cui nomen erat Ioánnes.\n"
            "Hic venit in testimónium, ut testimónium perhibéret de lúmine,\n"
            "ut omnes créderent per illum. Non erat ille lux,\n"
            "sed ut testimónium perhibéret de lúmine.\n"
            "Erat lux vera, quæ illúminat omnem hóminem veniéntem in hunc mundum.\n"
            "In mundo erat, et mundus per ipsum factus est, et mundus eum non cognóvit.\n"
            "In própria venit, et sui eum non recepérunt.\n"
            "Quotquot autem recepérunt eum, dedit eis potestátem fílios Dei fíeri,\n"
            "his qui credunt in nómine eius:\n"
            "qui non ex sanguínibus, neque ex voluntáte carnis,\n"
            "neque ex voluntáte viri, sed ex Deo nati sunt.\n\n"
            "ET VERBUM CARO FACTUM EST, [omnes genuflectunt] ET HABITÁVIT IN NOBIS:\n"
            "et vídimus glóriam eius, glóriam quasi Unigéniti a Patre,\n"
            "plenum grátiæ et veritátis.\n\n"
            "R. Deo grátias."
        ),
    ),
]


# ===========================================================================
# 3) DIVINE WORSHIP: THE MISSAL — The Ordinariate Use (2015)
# ===========================================================================

ORDINARIATE_SECTIONS: List[Dict[str, Any]] = [
    _section(
        title="The Collect for Purity",
        rubric=(
            "Divine Worship preserves the venerable Anglican patrimony reconciled to Rome. "
            "The Mass begins with a sign of the Cross, then the Collect for Purity — a "
            "private prayer of the Priest now spoken aloud, a hallmark of the English "
            "liturgical tradition since Sarum."
        ),
        english=(
            "In the name of the Father, and of the Son, and of the Holy Ghost. Amen.\n\n"
            "The grace of our Lord Jesus Christ, and the love of God,\n"
            "and the fellowship of the Holy Ghost, be with you all.\n"
            "R. And with thy spirit.\n\n"
            "Almighty God,\n"
            "unto whom all hearts be open, all desires known,\n"
            "and from whom no secrets are hid:\n"
            "Cleanse the thoughts of our hearts\n"
            "by the inspiration of thy Holy Spirit,\n"
            "that we may perfectly love thee,\n"
            "and worthily magnify thy holy Name;\n"
            "through Christ our Lord. Amen."
        ),
    ),
    _section(
        title="Summary of the Law · Kyrie · Gloria",
        rubric=(
            "In place of the Penitential Act, Divine Worship may use the Summary of the "
            "Law, recited by the Priest with all kneeling. The ninefold Kyrie follows; on "
            "Sundays outside Advent and Lent the Gloria is sung in Tudor English."
        ),
        english=(
            "Hear what our Lord Jesus Christ saith:\n"
            "Thou shalt love the Lord thy God with all thy heart,\n"
            "and with all thy soul, and with all thy mind.\n"
            "This is the first and great commandment.\n"
            "And the second is like unto it:\n"
            "Thou shalt love thy neighbour as thyself.\n"
            "On these two commandments hang all the Law and the Prophets.\n\n"
            "Lord, have mercy upon us. R. Lord, have mercy upon us.\n"
            "Christ, have mercy upon us. R. Christ, have mercy upon us.\n"
            "Lord, have mercy upon us. R. Lord, have mercy upon us.\n\n"
            "Glory be to God on high,\n"
            "and on earth peace, good will towards men.\n"
            "We praise thee, we bless thee, we worship thee,\n"
            "we glorify thee, we give thanks to thee for thy great glory,\n"
            "O Lord God, heavenly King, God the Father Almighty.\n"
            "O Lord, the only-begotten Son, Jesu Christ;\n"
            "O Lord God, Lamb of God, Son of the Father,\n"
            "that takest away the sins of the world, have mercy upon us.\n"
            "Thou that takest away the sins of the world, have mercy upon us.\n"
            "Thou that takest away the sins of the world, receive our prayer.\n"
            "Thou that sittest at the right hand of God the Father, have mercy upon us.\n"
            "For thou only art holy; thou only art the Lord;\n"
            "thou only, O Christ, with the Holy Ghost,\n"
            "art most high in the glory of God the Father. Amen."
        ),
    ),
    _section(
        title="The Collect of the Day",
        rubric=(
            "The Priest sings or says, \"The Lord be with you,\" and \"Let us pray.\" The "
            "Collect of the day, often drawn from the patrimony of Thomas Cranmer's "
            "translations of the Sarum and Roman collects, follows. The dialogue is fixed; "
            "the prayer itself changes each Sunday and feast."
        ),
        english=(
            "The Lord be with you.\n"
            "R. And with thy spirit.\n"
            "Let us pray.\n\n"
            "[The Collect of the Day is sung or said.]\n\n"
            "…Through Jesus Christ our Lord,\n"
            "who liveth and reigneth with thee\n"
            "in the unity of the Holy Ghost, ever one God,\n"
            "world without end. R. Amen."
        ),
    ),
    _section(
        title="The Liturgy of the Word",
        rubric=(
            "The Lessons of the day are read; the Responsorial Psalm or Gradual follows. "
            "Before the Gospel: \"The Lord be with you. R. And with thy spirit. The "
            "continuation of the Holy Gospel according to N. R. Glory be to thee, O "
            "Lord.\" After the Gospel: \"R. Praise be to thee, O Christ.\" The Homily "
            "follows."
        ),
        english=(
            "After each Reading:\n"
            "The word of the Lord.\n"
            "R. Thanks be to God.\n\n"
            "Before the Gospel:\n"
            "The Lord be with you.\n"
            "R. And with thy spirit.\n"
            "The continuation of the Holy Gospel according to N.\n"
            "R. Glory be to thee, O Lord.\n\n"
            "After the Gospel:\n"
            "The Gospel of the Lord.\n"
            "R. Praise be to thee, O Christ."
        ),
    ),
    _section(
        title="The Nicene Creed",
        rubric="Recited on Sundays and Solemnities. All bow at the Incarnation.",
        english=(
            "I believe in one God,\n"
            "the Father Almighty, Maker of heaven and earth,\n"
            "and of all things visible and invisible:\n"
            "And in one Lord Jesus Christ,\n"
            "the only-begotten Son of God,\n"
            "begotten of his Father before all worlds,\n"
            "God of God, Light of Light, very God of very God,\n"
            "begotten, not made, being of one substance with the Father,\n"
            "by whom all things were made:\n"
            "Who for us men and for our salvation\n"
            "came down from heaven,\n"
            "and was incarnate by the Holy Ghost of the Virgin Mary,\n"
            "and was made man:\n"
            "and was crucified also for us under Pontius Pilate;\n"
            "he suffered and was buried:\n"
            "and the third day he rose again according to the Scriptures,\n"
            "and ascended into heaven,\n"
            "and sitteth on the right hand of the Father:\n"
            "and he shall come again, with glory,\n"
            "to judge both the quick and the dead;\n"
            "whose kingdom shall have no end.\n"
            "And I believe in the Holy Ghost,\n"
            "the Lord, and Giver of life,\n"
            "who proceedeth from the Father and the Son;\n"
            "who with the Father and the Son together is worshipped and glorified;\n"
            "who spake by the Prophets.\n"
            "And I believe one holy Catholic and Apostolic Church.\n"
            "I acknowledge one Baptism for the remission of sins.\n"
            "And I look for the Resurrection of the dead,\n"
            "and the life of the world to come. Amen."
        ),
    ),
    _section(
        title="The Prayers of the People",
        rubric=(
            "The faithful intercede in solemn form. Petitions are offered for the Church, the "
            "civil authorities, those in need, and the departed; each ends with: \"R. Hear us, "
            "good Lord.\""
        ),
        english=(
            "Let us pray for the whole state of Christ's Church.\n\n"
            "[Petitions are offered.]\n\n"
            "Lord, in thy mercy,\n"
            "R. Hear our prayer.\n\n"
            "Hear our prayers, O merciful Father,\n"
            "and what we have asked faithfully, grant us effectually,\n"
            "through Jesus Christ our Lord.\n"
            "R. Amen."
        ),
    ),
    _section(
        title="The Penitential Rite · Comfortable Words",
        rubric=(
            "Where the Penitential Rite is observed at this point (the Anglican usage), the "
            "Priest invites all to make a humble confession. The Comfortable Words from the "
            "Scriptures are then proclaimed — a unique treasure of the Ordinariate Missal."
        ),
        english=(
            "Ye that do truly and earnestly repent you of your sins,\n"
            "and are in love and charity with your neighbours,\n"
            "and intend to lead a new life,\n"
            "following the commandments of God,\n"
            "and walking from henceforth in his holy ways:\n"
            "draw near with faith…\n\n"
            "[The general Confession is made.]\n\n"
            "Almighty God, our heavenly Father, who of his great mercy\n"
            "hath promised forgiveness of sins to all them\n"
            "that with hearty repentance and true faith turn unto him:\n"
            "have mercy upon you, pardon and deliver you from all your sins,\n"
            "confirm and strengthen you in all goodness,\n"
            "and bring you to everlasting life;\n"
            "through Jesus Christ our Lord. R. Amen.\n\n"
            "Hear what comfortable words our Saviour Christ saith\n"
            "unto all that truly turn to him:\n"
            "Come unto me, all that travail and are heavy laden, and I will refresh you."
        ),
    ),
    _section(
        title="The Offertory & Sursum Corda",
        rubric=(
            "The bread and wine are offered with the same formulas as the Roman Rite, in "
            "sacral English. The Priest washes his hands and invites the people: \"Pray, "
            "brethren…\""
        ),
        english=(
            "Pray, brethren, that this my sacrifice and yours\n"
            "may be acceptable unto God, the Father Almighty.\n"
            "R. May the Lord accept the sacrifice at thy hands,\n"
            "to the praise and glory of his Name,\n"
            "both to our benefit, and that of all his holy Church.\n\n"
            "The Lord be with you. R. And with thy spirit.\n"
            "Lift up your hearts. R. We lift them up unto the Lord.\n"
            "Let us give thanks unto our Lord God.\n"
            "R. It is meet and right so to do.\n\n"
            "[Preface and Sanctus follow.]\n\n"
            "Holy, Holy, Holy, Lord God of Hosts,\n"
            "Heaven and earth are full of thy glory.\n"
            "Glory be to thee, O Lord most High.\n"
            "Blessed is he that cometh in the Name of the Lord.\n"
            "Hosanna in the highest."
        ),
    ),
    _section(
        title="The Roman Canon (Eucharistic Prayer I) · Consecration",
        rubric=(
            "Divine Worship retains the Roman Canon, but in the sacral English style. The "
            "Words of Institution are pronounced over the bread, then over the chalice."
        ),
        english=(
            "Most merciful Father, we humbly pray thee,\n"
            "through Jesus Christ thy Son our Lord,\n"
            "and we ask, that thou wouldest accept and bless\n"
            "these gifts, these presents, these holy and unblemished sacrifices…\n\n"
            "Who, the day before he suffered, took bread into his holy and venerable hands,\n"
            "and with eyes lifted up to heaven, unto thee, O God, his Father Almighty,\n"
            "giving thanks to thee, did bless, break,\n"
            "and give it to his disciples, saying:\n"
            "TAKE, AND EAT YE ALL OF THIS,\n"
            "FOR THIS IS MY BODY, WHICH SHALL BE GIVEN UP FOR YOU.\n\n"
            "Likewise, after supper, taking also this excellent chalice\n"
            "into his holy and venerable hands,\n"
            "again giving thanks to thee, he blessed it, and gave it to his disciples, saying:\n"
            "TAKE, AND DRINK YE ALL OF THIS,\n"
            "FOR THIS IS THE CHALICE OF MY BLOOD,\n"
            "OF THE NEW AND ETERNAL COVENANT:\n"
            "THE MYSTERY OF FAITH:\n"
            "WHICH SHALL BE SHED FOR YOU AND FOR MANY\n"
            "UNTO THE REMISSION OF SINS.\n"
            "DO THIS, AS OFT AS YE SHALL DO IT, IN REMEMBRANCE OF ME.\n\n"
            "The mystery of faith:\n"
            "R. We proclaim thy Death, O Lord, and confess thy Resurrection,\n"
            "until thou come again."
        ),
    ),
    _section(
        title="The Lord's Prayer · Embolism",
        rubric="In Cranmer's incomparable Tudor English, beloved across the English-speaking world for nearly five centuries.",
        english=(
            "And now, as our Saviour Christ hath taught us, we are bold to say:\n\n"
            "Our Father, who art in heaven,\n"
            "hallowed be thy Name;\n"
            "thy kingdom come;\n"
            "thy will be done, on earth as it is in heaven.\n"
            "Give us this day our daily bread;\n"
            "and forgive us our trespasses,\n"
            "as we forgive those who trespass against us;\n"
            "and lead us not into temptation,\n"
            "but deliver us from evil.\n\n"
            "Deliver us, O Lord, we beseech thee, from all evils,\n"
            "past, present, and to come;\n"
            "and by the intercession of the Blessed and glorious ever-Virgin Mary,\n"
            "of thy holy Apostles Peter and Paul, of Andrew, and of all the Saints,\n"
            "favourably grant peace in our days,\n"
            "that by the help of thine availing mercy\n"
            "we may be ever free from sin, and safe from all distress.\n"
            "Through the same Lord Jesus Christ thy Son,\n"
            "who liveth and reigneth with thee in the unity of the Holy Ghost, God,\n"
            "world without end. R. Amen.\n\n"
            "R. For thine is the kingdom, the power, and the glory,\n"
            "for ever and ever. Amen."
        ),
    ),
    _section(
        title="The Prayer of Humble Access",
        rubric=(
            "Unique to the Ordinariate (and to historic Anglican usage), the Prayer of "
            "Humble Access — composed by Thomas Cranmer in 1548 — is prayed by the people "
            "kneeling, just before Communion. One of the great jewels of English-language "
            "eucharistic devotion."
        ),
        english=(
            "We do not presume to come to this thy Table, O merciful Lord,\n"
            "trusting in our own righteousness,\n"
            "but in thy manifold and great mercies.\n"
            "We are not worthy so much as to gather up the crumbs under thy Table.\n"
            "But thou art the same Lord, whose property is always to have mercy:\n"
            "Grant us therefore, gracious Lord,\n"
            "so to eat the Flesh of thy dear Son Jesus Christ,\n"
            "and to drink his Blood,\n"
            "that we may evermore dwell in him, and he in us. Amen."
        ),
    ),
    _section(
        title="Agnus Dei · Ecce Agnus Dei · Communion",
        rubric=(
            "After the Pax (\"The peace of the Lord be alway with you\") the Agnus Dei is "
            "sung. The Priest then elevates the Sacrament and proclaims, \"Behold the Lamb "
            "of God…\""
        ),
        english=(
            "The peace of the Lord be alway with you.\n"
            "R. And with thy spirit.\n\n"
            "O Lamb of God, that takest away the sins of the world,\n"
            "have mercy upon us.\n"
            "O Lamb of God, that takest away the sins of the world,\n"
            "have mercy upon us.\n"
            "O Lamb of God, that takest away the sins of the world,\n"
            "grant us thy peace.\n\n"
            "Behold the Lamb of God, behold him that taketh away the sins of the world.\n"
            "Blessed are they which are called unto the marriage supper of the Lamb.\n"
            "R. Lord, I am not worthy that thou shouldest come under my roof:\n"
            "but speak the word only, and my soul shall be healed.\n\n"
            "[At Communion:]\n"
            "The Body of our Lord Jesus Christ, which was given for thee,\n"
            "preserve thy body and soul unto everlasting life. Amen.\n"
            "The Blood of our Lord Jesus Christ, which was shed for thee,\n"
            "preserve thy body and soul unto everlasting life. Amen."
        ),
    ),
    _section(
        title="Post-Communion · Blessing · Dismissal",
        rubric=(
            "After the Communion antiphon, the Priest prays the Post-Communion of the day, "
            "then turns to bless the people. The dismissal may be in either form."
        ),
        english=(
            "The Lord be with you. R. And with thy spirit.\n\n"
            "Let us pray.\n"
            "[Post-Communion Prayer.]\n"
            "…through Jesus Christ our Lord. R. Amen.\n\n"
            "Almighty God, the Father, the Son, and the Holy Ghost,\n"
            "bless you, and keep you, this day and evermore.\n"
            "R. Amen.\n\n"
            "Go forth, the Mass is ended; alleluia, alleluia.\n"
            "R. Thanks be to God, alleluia, alleluia."
        ),
    ),
]


# ===========================================================================
# 4) ROMAN MISSAL — Spanish (Misal Romano) — Ordinary Form, Spanish + Latin
# 5) ROMAN MISSAL — Italian (Messale Romano) — Ordinary Form, Italian + Latin
# ---------------------------------------------------------------------------
# The Order of Mass (Ordinary) of the 1970 Roman Missal as it is celebrated
# in Spanish and Italian. The vernacular text is the official approved
# translation; the Latin editio typica is provided alongside for reference.
# We reuse the Latin and Latin-titles already defined in NOVUS_ORDO_SECTIONS
# (same Ordinary, same order) so the two columns stay perfectly aligned.
# ===========================================================================


def _vern_section(
    no_idx: int,
    title: str,
    vernacular: str,
    rubric: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a vernacular (Spanish/Italian) Order-of-Mass section that reuses
    the Latin original + Latin title from the matching Novus Ordo section."""
    base = NOVUS_ORDO_SECTIONS[no_idx]
    return _section(
        title=title,
        english=vernacular,  # primary column = vernacular
        latin=base.get("latin"),
        latin_title=base.get("latin_title"),
        rubric=rubric,
    )


SPANISH_NOVUS_ORDO_SECTIONS: List[Dict[str, Any]] = [
    _vern_section(
        0,
        "Ritos Iniciales · Señal de la Cruz y Saludo",
        "En el nombre del Padre, y del Hijo, y del Espíritu Santo.\n"
        "R. Amén.\n\n"
        "La gracia de nuestro Señor Jesucristo, el amor del Padre y la comunión "
        "del Espíritu Santo estén con todos vosotros.\n"
        "R. Y con tu espíritu.",
        rubric="El sacerdote, junto con el pueblo, se signa con la señal de la cruz y saluda a la asamblea.",
    ),
    _vern_section(
        1,
        "Acto Penitencial",
        "Yo confieso ante Dios todopoderoso\n"
        "y ante vosotros, hermanos,\n"
        "que he pecado mucho\n"
        "de pensamiento, palabra, obra y omisión.\n"
        "Por mi culpa, por mi culpa, por mi gran culpa.\n"
        "Por eso ruego a santa María, siempre Virgen,\n"
        "a los ángeles, a los santos\n"
        "y a vosotros, hermanos,\n"
        "que intercedáis por mí ante Dios, nuestro Señor.\n\n"
        "Dios todopoderoso tenga misericordia de nosotros,\n"
        "perdone nuestros pecados\n"
        "y nos lleve a la vida eterna.\n"
        "R. Amén.",
        rubric="El sacerdote invita a los fieles a reconocer sus pecados. Tras un breve silencio se dice el Confíteor (una de las tres fórmulas).",
    ),
    _vern_section(
        2,
        "Señor, ten piedad",
        "Señor, ten piedad.\n"
        "R. Señor, ten piedad.\n"
        "Cristo, ten piedad.\n"
        "R. Cristo, ten piedad.\n"
        "Señor, ten piedad.\n"
        "R. Señor, ten piedad.",
    ),
    _vern_section(
        3,
        "Gloria",
        "Gloria a Dios en el cielo,\n"
        "y en la tierra paz a los hombres que ama el Señor.\n"
        "Por tu inmensa gloria te alabamos, te bendecimos, te adoramos,\n"
        "te glorificamos, te damos gracias,\n"
        "Señor Dios, Rey celestial, Dios Padre todopoderoso.\n\n"
        "Señor, Hijo único, Jesucristo.\n"
        "Señor Dios, Cordero de Dios, Hijo del Padre;\n"
        "tú que quitas el pecado del mundo, ten piedad de nosotros;\n"
        "tú que quitas el pecado del mundo, atiende nuestra súplica;\n"
        "tú que estás sentado a la derecha del Padre, ten piedad de nosotros.\n\n"
        "Porque sólo tú eres Santo, sólo tú Señor,\n"
        "sólo tú Altísimo, Jesucristo,\n"
        "con el Espíritu Santo en la gloria de Dios Padre. Amén.",
        rubric="Se canta o se dice los domingos fuera de Adviento y Cuaresma, en las solemnidades y fiestas.",
    ),
    _vern_section(
        4,
        "Oración Colecta",
        "Oremos.\n\n"
        "[El sacerdote proclama la oración colecta del día.]\n\n"
        "Por nuestro Señor Jesucristo, tu Hijo,\n"
        "que vive y reina contigo en la unidad del Espíritu Santo\n"
        "y es Dios por los siglos de los siglos.\n"
        "R. Amén.",
        rubric="El sacerdote invita a orar. Tras un breve silencio, proclama la colecta, que reúne las intenciones del día. El texto cambia cada día; sólo el diálogo es fijo.",
    ),
    _vern_section(
        5,
        "Liturgia de la Palabra",
        "Después de la primera lectura:\n"
        "Palabra de Dios.\n"
        "R. Te alabamos, Señor.\n\n"
        "Antes del Evangelio:\n"
        "El Señor esté con vosotros.\n"
        "R. Y con tu espíritu.\n"
        "Lectura del santo Evangelio según san N.\n"
        "R. Gloria a ti, Señor.\n\n"
        "Después del Evangelio:\n"
        "Palabra del Señor.\n"
        "R. Gloria a ti, Señor Jesús.\n\n"
        "[A continuación, la homilía.]",
        rubric="Se proclama la primera lectura y el salmo responsorial; los domingos y solemnidades, también la segunda lectura. El aleluya prepara para el Evangelio.",
    ),
    _vern_section(
        6,
        "Profesión de Fe · Credo Niceno",
        "Creo en un solo Dios,\n"
        "Padre todopoderoso,\n"
        "Creador del cielo y de la tierra,\n"
        "de todo lo visible y lo invisible.\n\n"
        "Creo en un solo Señor, Jesucristo,\n"
        "Hijo único de Dios,\n"
        "nacido del Padre antes de todos los siglos:\n"
        "Dios de Dios, Luz de Luz,\n"
        "Dios verdadero de Dios verdadero,\n"
        "engendrado, no creado,\n"
        "de la misma naturaleza que el Padre,\n"
        "por quien todo fue hecho;\n"
        "que por nosotros, los hombres,\n"
        "y por nuestra salvación bajó del cielo,\n"
        "y por obra del Espíritu Santo\n"
        "se encarnó de María, la Virgen, y se hizo hombre;\n"
        "y por nuestra causa fue crucificado\n"
        "en tiempos de Poncio Pilato;\n"
        "padeció y fue sepultado,\n"
        "y resucitó al tercer día, según las Escrituras,\n"
        "y subió al cielo,\n"
        "y está sentado a la derecha del Padre;\n"
        "y de nuevo vendrá con gloria\n"
        "para juzgar a vivos y muertos,\n"
        "y su reino no tendrá fin.\n\n"
        "Creo en el Espíritu Santo, Señor y dador de vida,\n"
        "que procede del Padre y del Hijo,\n"
        "que con el Padre y el Hijo\n"
        "recibe una misma adoración y gloria,\n"
        "y que habló por los profetas.\n\n"
        "Creo en la Iglesia,\n"
        "que es una, santa, católica y apostólica.\n"
        "Confieso que hay un solo Bautismo\n"
        "para el perdón de los pecados.\n"
        "Espero la resurrección de los muertos\n"
        "y la vida del mundo futuro. Amén.",
        rubric="Se dice los domingos y solemnidades. Todos se inclinan a las palabras «y por obra del Espíritu Santo… y se hizo hombre».",
    ),
    _vern_section(
        7,
        "Oración Universal · Oración de los Fieles",
        "Roguemos al Señor.\n"
        "R. Te rogamos, óyenos.\n\n"
        "[Se formulan las intenciones.]\n\n"
        "Escucha, Señor, las oraciones de tu pueblo,\n"
        "y concédenos lo que te pedimos con fe.\n"
        "Por Jesucristo, nuestro Señor.\n"
        "R. Amén.",
    ),
    _vern_section(
        8,
        "Liturgia Eucarística · Presentación de las Ofrendas",
        "Bendito seas, Señor, Dios del universo,\n"
        "por este pan, fruto de la tierra y del trabajo del hombre,\n"
        "que recibimos de tu generosidad y ahora te presentamos;\n"
        "él será para nosotros pan de vida.\n"
        "R. Bendito seas por siempre, Señor.\n\n"
        "Bendito seas, Señor, Dios del universo,\n"
        "por este vino, fruto de la vid y del trabajo del hombre,\n"
        "que recibimos de tu generosidad y ahora te presentamos;\n"
        "él será para nosotros bebida de salvación.\n"
        "R. Bendito seas por siempre, Señor.\n\n"
        "Orad, hermanos,\n"
        "para que este sacrificio, mío y vuestro,\n"
        "sea agradable a Dios, Padre todopoderoso.\n"
        "R. El Señor reciba de tus manos este sacrificio,\n"
        "para alabanza y gloria de su nombre,\n"
        "para nuestro bien y el de toda su santa Iglesia.",
        rubric="Se llevan al altar el pan y el vino.",
    ),
    _vern_section(
        9,
        "Prefacio y Santo",
        "El Señor esté con vosotros.\n"
        "R. Y con tu espíritu.\n"
        "Levantemos el corazón.\n"
        "R. Lo tenemos levantado hacia el Señor.\n"
        "Demos gracias al Señor, nuestro Dios.\n"
        "R. Es justo y necesario.\n\n"
        "[El sacerdote proclama el prefacio del día.]\n\n"
        "Santo, Santo, Santo es el Señor, Dios del universo.\n"
        "Llenos están el cielo y la tierra de tu gloria.\n"
        "Hosanna en el cielo.\n"
        "Bendito el que viene en nombre del Señor.\n"
        "Hosanna en el cielo.",
    ),
    _vern_section(
        10,
        "Plegaria Eucarística II",
        "Santo eres en verdad, Señor, fuente de toda santidad;\n"
        "por eso te pedimos que santifiques estos dones\n"
        "con la efusión de tu Espíritu,\n"
        "de manera que sean para nosotros\n"
        "Cuerpo y Sangre de Jesucristo, nuestro Señor.\n\n"
        "El cual, cuando iba a ser entregado a su Pasión,\n"
        "voluntariamente aceptada,\n"
        "tomó pan, dándote gracias, lo partió,\n"
        "y lo dio a sus discípulos, diciendo:\n"
        "TOMAD Y COMED TODOS DE ÉL,\n"
        "PORQUE ESTO ES MI CUERPO,\n"
        "QUE SERÁ ENTREGADO POR VOSOTROS.\n\n"
        "Del mismo modo, acabada la cena,\n"
        "tomó el cáliz, y, dándote gracias de nuevo,\n"
        "lo pasó a sus discípulos, diciendo:\n"
        "TOMAD Y BEBED TODOS DE ÉL,\n"
        "PORQUE ESTE ES EL CÁLIZ DE MI SANGRE,\n"
        "SANGRE DE LA ALIANZA NUEVA Y ETERNA,\n"
        "QUE SERÁ DERRAMADA POR VOSOTROS Y POR MUCHOS\n"
        "PARA EL PERDÓN DE LOS PECADOS.\n"
        "HACED ESTO EN CONMEMORACIÓN MÍA.\n\n"
        "Este es el Misterio de la fe.\n"
        "R. Anunciamos tu muerte, proclamamos tu resurrección.\n"
        "¡Ven, Señor Jesús!",
        rubric="De las cuatro plegarias eucarísticas principales, la segunda es la más breve, basada en un antiguo texto atribuido a san Hipólito (c. 215).",
    ),
    _vern_section(
        11,
        "Doxología Final",
        "Por Cristo, con él y en él,\n"
        "a ti, Dios Padre omnipotente,\n"
        "en la unidad del Espíritu Santo,\n"
        "todo honor y toda gloria\n"
        "por los siglos de los siglos.\n"
        "R. Amén.",
    ),
    _vern_section(
        12,
        "Rito de la Comunión · Padre Nuestro",
        "Fieles a la recomendación del Salvador\n"
        "y siguiendo su divina enseñanza, nos atrevemos a decir:\n\n"
        "Padre nuestro, que estás en el cielo,\n"
        "santificado sea tu Nombre;\n"
        "venga a nosotros tu reino;\n"
        "hágase tu voluntad en la tierra como en el cielo.\n"
        "Danos hoy nuestro pan de cada día;\n"
        "perdona nuestras ofensas,\n"
        "como también nosotros perdonamos a los que nos ofenden;\n"
        "no nos dejes caer en la tentación,\n"
        "y líbranos del mal.\n\n"
        "Líbranos de todos los males, Señor,\n"
        "y concédenos la paz en nuestros días,\n"
        "para que, ayudados por tu misericordia,\n"
        "vivamos siempre libres de pecado\n"
        "y protegidos de toda perturbación,\n"
        "mientras esperamos la gloriosa venida\n"
        "de nuestro Salvador Jesucristo.\n"
        "R. Tuyo es el reino, tuyo el poder y la gloria, por siempre, Señor.",
    ),
    _vern_section(
        13,
        "Rito de la Paz · Cordero de Dios",
        "Señor Jesucristo, que dijiste a tus apóstoles:\n"
        "«La paz os dejo, mi paz os doy»,\n"
        "no tengas en cuenta nuestros pecados,\n"
        "sino la fe de tu Iglesia\n"
        "y, conforme a tu palabra, concédele la paz y la unidad.\n"
        "Tú que vives y reinas por los siglos de los siglos.\n"
        "R. Amén.\n\n"
        "La paz del Señor esté siempre con vosotros.\n"
        "R. Y con tu espíritu.\n\n"
        "Daos fraternalmente la paz.\n\n"
        "Cordero de Dios, que quitas el pecado del mundo, ten piedad de nosotros.\n"
        "Cordero de Dios, que quitas el pecado del mundo, ten piedad de nosotros.\n"
        "Cordero de Dios, que quitas el pecado del mundo, danos la paz.",
    ),
    _vern_section(
        14,
        "Comunión",
        "Este es el Cordero de Dios,\n"
        "que quita el pecado del mundo.\n"
        "Dichosos los invitados a la cena del Señor.\n\n"
        "R. Señor, no soy digno de que entres en mi casa,\n"
        "pero una palabra tuya bastará para sanarme.\n\n"
        "[En el momento de comulgar:]\n"
        "El Cuerpo de Cristo. R. Amén.\n"
        "La Sangre de Cristo. R. Amén.",
        rubric="El sacerdote muestra al pueblo el pan eucarístico, ligeramente elevado sobre la patena o el cáliz.",
    ),
    _vern_section(
        15,
        "Ritos de Conclusión · Bendición y Despedida",
        "El Señor esté con vosotros.\n"
        "R. Y con tu espíritu.\n\n"
        "La bendición de Dios todopoderoso,\n"
        "Padre, Hijo y Espíritu Santo,\n"
        "descienda sobre vosotros.\n"
        "R. Amén.\n\n"
        "Podéis ir en paz.\n"
        "R. Demos gracias a Dios.",
    ),
]


ITALIAN_NOVUS_ORDO_SECTIONS: List[Dict[str, Any]] = [
    _vern_section(
        0,
        "Riti di Introduzione · Segno della Croce e Saluto",
        "Nel nome del Padre e del Figlio e dello Spirito Santo.\n"
        "R. Amen.\n\n"
        "La grazia del Signore nostro Gesù Cristo, l'amore di Dio Padre e la "
        "comunione dello Spirito Santo siano con tutti voi.\n"
        "R. E con il tuo spirito.",
        rubric="Il sacerdote, insieme al popolo, si fa il segno della croce e saluta l'assemblea.",
    ),
    _vern_section(
        1,
        "Atto Penitenziale",
        "Confesso a Dio onnipotente e a voi, fratelli e sorelle,\n"
        "che ho molto peccato\n"
        "in pensieri, parole, opere e omissioni,\n"
        "per mia colpa, mia colpa, mia grandissima colpa.\n"
        "E supplico la beata sempre Vergine Maria,\n"
        "gli angeli, i santi e voi, fratelli e sorelle,\n"
        "di pregare per me il Signore Dio nostro.\n\n"
        "Dio onnipotente abbia misericordia di noi,\n"
        "perdoni i nostri peccati\n"
        "e ci conduca alla vita eterna.\n"
        "R. Amen.",
        rubric="Il sacerdote invita i fedeli a riconoscere i propri peccati. Dopo una breve pausa di silenzio si dice il Confesso (una delle tre formule).",
    ),
    _vern_section(
        2,
        "Signore, pietà",
        "Signore, pietà.\n"
        "R. Signore, pietà.\n"
        "Cristo, pietà.\n"
        "R. Cristo, pietà.\n"
        "Signore, pietà.\n"
        "R. Signore, pietà.",
    ),
    _vern_section(
        3,
        "Gloria",
        "Gloria a Dio nell'alto dei cieli\n"
        "e pace in terra agli uomini, amati dal Signore.\n"
        "Noi ti lodiamo, ti benediciamo, ti adoriamo, ti glorifichiamo,\n"
        "ti rendiamo grazie per la tua gloria immensa,\n"
        "Signore Dio, Re del cielo, Dio Padre onnipotente.\n\n"
        "Signore, Figlio unigenito, Gesù Cristo,\n"
        "Signore Dio, Agnello di Dio, Figlio del Padre,\n"
        "tu che togli i peccati del mondo, abbi pietà di noi;\n"
        "tu che togli i peccati del mondo, accogli la nostra supplica;\n"
        "tu che siedi alla destra del Padre, abbi pietà di noi.\n\n"
        "Perché tu solo il Santo, tu solo il Signore,\n"
        "tu solo l'Altissimo, Gesù Cristo,\n"
        "con lo Spirito Santo: nella gloria di Dio Padre. Amen.",
        rubric="Si canta o si dice nelle domeniche fuori di Avvento e Quaresima, nelle solennità e nelle feste.",
    ),
    _vern_section(
        4,
        "Colletta",
        "Preghiamo.\n\n"
        "[Il sacerdote proclama la colletta del giorno.]\n\n"
        "Per il nostro Signore Gesù Cristo, tuo Figlio, che è Dio,\n"
        "e vive e regna con te, nell'unità dello Spirito Santo,\n"
        "per tutti i secoli dei secoli.\n"
        "R. Amen.",
        rubric="Il sacerdote invita alla preghiera. Dopo un breve silenzio proclama la colletta, che raccoglie le intenzioni del giorno. Il testo cambia ogni giorno; solo il dialogo è fisso.",
    ),
    _vern_section(
        5,
        "Liturgia della Parola",
        "Dopo la prima lettura:\n"
        "Parola di Dio.\n"
        "R. Rendiamo grazie a Dio.\n\n"
        "Prima del Vangelo:\n"
        "Il Signore sia con voi.\n"
        "R. E con il tuo spirito.\n"
        "Dal Vangelo secondo N.\n"
        "R. Gloria a te, o Signore.\n\n"
        "Dopo il Vangelo:\n"
        "Parola del Signore.\n"
        "R. Lode a te, o Cristo.\n\n"
        "[Segue l'omelia.]",
        rubric="Si proclama la prima lettura e il salmo responsoriale; nelle domeniche e solennità, anche la seconda lettura. Il canto al Vangelo prepara all'ascolto.",
    ),
    _vern_section(
        6,
        "Professione di Fede · Credo Niceno",
        "Credo in un solo Dio, Padre onnipotente,\n"
        "creatore del cielo e della terra,\n"
        "di tutte le cose visibili e invisibili.\n\n"
        "Credo in un solo Signore, Gesù Cristo,\n"
        "unigenito Figlio di Dio,\n"
        "nato dal Padre prima di tutti i secoli:\n"
        "Dio da Dio, Luce da Luce,\n"
        "Dio vero da Dio vero;\n"
        "generato, non creato,\n"
        "della stessa sostanza del Padre;\n"
        "per mezzo di lui tutte le cose sono state create.\n"
        "Per noi uomini e per la nostra salvezza\n"
        "discese dal cielo,\n"
        "e per opera dello Spirito Santo\n"
        "si è incarnato nel seno della Vergine Maria\n"
        "e si è fatto uomo.\n"
        "Fu crocifisso per noi sotto Ponzio Pilato,\n"
        "morì e fu sepolto.\n"
        "Il terzo giorno è risuscitato, secondo le Scritture,\n"
        "è salito al cielo, siede alla destra del Padre.\n"
        "E di nuovo verrà, nella gloria,\n"
        "per giudicare i vivi e i morti,\n"
        "e il suo regno non avrà fine.\n\n"
        "Credo nello Spirito Santo, che è Signore e dà la vita,\n"
        "e procede dal Padre e dal Figlio.\n"
        "Con il Padre e il Figlio è adorato e glorificato,\n"
        "e ha parlato per mezzo dei profeti.\n"
        "Credo la Chiesa, una, santa, cattolica e apostolica.\n"
        "Professo un solo Battesimo per il perdono dei peccati.\n"
        "Aspetto la risurrezione dei morti\n"
        "e la vita del mondo che verrà. Amen.",
        rubric="Si dice nelle domeniche e solennità. Tutti si inchinano alle parole «e per opera dello Spirito Santo… e si è fatto uomo».",
    ),
    _vern_section(
        7,
        "Preghiera Universale · Preghiera dei Fedeli",
        "Preghiamo.\n"
        "R. Ascoltaci, Signore.\n\n"
        "[Si formulano le intenzioni.]\n\n"
        "Accogli, o Padre, le preghiere del tuo popolo,\n"
        "e concedi ciò che con fede ti chiediamo.\n"
        "Per Cristo nostro Signore.\n"
        "R. Amen.",
    ),
    _vern_section(
        8,
        "Liturgia Eucaristica · Presentazione dei Doni",
        "Benedetto sei tu, Signore, Dio dell'universo:\n"
        "dalla tua bontà abbiamo ricevuto questo pane,\n"
        "frutto della terra e del lavoro dell'uomo;\n"
        "lo presentiamo a te, perché diventi per noi cibo di vita eterna.\n"
        "R. Benedetto nei secoli il Signore.\n\n"
        "Benedetto sei tu, Signore, Dio dell'universo:\n"
        "dalla tua bontà abbiamo ricevuto questo vino,\n"
        "frutto della vite e del lavoro dell'uomo;\n"
        "lo presentiamo a te, perché diventi per noi bevanda di salvezza.\n"
        "R. Benedetto nei secoli il Signore.\n\n"
        "Pregate, fratelli e sorelle,\n"
        "perché il mio e vostro sacrificio\n"
        "sia gradito a Dio, Padre onnipotente.\n"
        "R. Il Signore riceva dalle tue mani questo sacrificio\n"
        "a lode e gloria del suo nome,\n"
        "per il bene nostro e di tutta la sua santa Chiesa.",
        rubric="Si portano all'altare il pane e il vino.",
    ),
    _vern_section(
        9,
        "Prefazio e Santo",
        "Il Signore sia con voi.\n"
        "R. E con il tuo spirito.\n"
        "In alto i nostri cuori.\n"
        "R. Sono rivolti al Signore.\n"
        "Rendiamo grazie al Signore, nostro Dio.\n"
        "R. È cosa buona e giusta.\n\n"
        "[Il sacerdote proclama il prefazio del giorno.]\n\n"
        "Santo, Santo, Santo il Signore Dio dell'universo.\n"
        "I cieli e la terra sono pieni della tua gloria.\n"
        "Osanna nell'alto dei cieli.\n"
        "Benedetto colui che viene nel nome del Signore.\n"
        "Osanna nell'alto dei cieli.",
    ),
    _vern_section(
        10,
        "Preghiera Eucaristica II",
        "Veramente santo sei tu, o Padre,\n"
        "fonte di ogni santità.\n"
        "Ti preghiamo: santifica questi doni\n"
        "con la rugiada del tuo Spirito,\n"
        "perché diventino per noi\n"
        "il Corpo e il Sangue del Signore nostro Gesù Cristo.\n\n"
        "Egli, offrendosi liberamente alla sua passione,\n"
        "prese il pane e rese grazie,\n"
        "lo spezzò, lo diede ai suoi discepoli, e disse:\n"
        "PRENDETE, E MANGIATENE TUTTI:\n"
        "QUESTO È IL MIO CORPO\n"
        "OFFERTO IN SACRIFICIO PER VOI.\n\n"
        "Allo stesso modo, dopo aver cenato,\n"
        "prese il calice, di nuovo ti rese grazie,\n"
        "lo diede ai suoi discepoli, e disse:\n"
        "PRENDETE, E BEVETENE TUTTI:\n"
        "QUESTO È IL CALICE DEL MIO SANGUE\n"
        "PER LA NUOVA ED ETERNA ALLEANZA,\n"
        "VERSATO PER VOI E PER TUTTI\n"
        "IN REMISSIONE DEI PECCATI.\n"
        "FATE QUESTO IN MEMORIA DI ME.\n\n"
        "Mistero della fede.\n"
        "R. Annunciamo la tua morte, Signore,\n"
        "proclamiamo la tua risurrezione,\n"
        "nell'attesa della tua venuta.",
        rubric="Delle quattro principali preghiere eucaristiche, la seconda è la più breve, basata su un antico testo attribuito a sant'Ippolito (c. 215).",
    ),
    _vern_section(
        11,
        "Dossologia Finale",
        "Per Cristo, con Cristo e in Cristo,\n"
        "a te, Dio Padre onnipotente,\n"
        "nell'unità dello Spirito Santo,\n"
        "ogni onore e gloria\n"
        "per tutti i secoli dei secoli.\n"
        "R. Amen.",
    ),
    _vern_section(
        12,
        "Riti di Comunione · Padre Nostro",
        "Obbedienti alla parola del Salvatore\n"
        "e formati al suo divino insegnamento, osiamo dire:\n\n"
        "Padre nostro, che sei nei cieli,\n"
        "sia santificato il tuo nome,\n"
        "venga il tuo regno,\n"
        "sia fatta la tua volontà, come in cielo così in terra.\n"
        "Dacci oggi il nostro pane quotidiano,\n"
        "e rimetti a noi i nostri debiti\n"
        "come anche noi li rimettiamo ai nostri debitori,\n"
        "e non abbandonarci alla tentazione,\n"
        "ma liberaci dal male.\n\n"
        "Liberaci, o Signore, da tutti i mali,\n"
        "concedi la pace ai nostri giorni,\n"
        "e con l'aiuto della tua misericordia\n"
        "vivremo sempre liberi dal peccato\n"
        "e sicuri da ogni turbamento,\n"
        "nell'attesa che si compia la beata speranza\n"
        "e venga il nostro Salvatore Gesù Cristo.\n"
        "R. Tuo è il regno, tua la potenza e la gloria nei secoli.",
    ),
    _vern_section(
        13,
        "Rito della Pace · Agnello di Dio",
        "Signore Gesù Cristo, che hai detto ai tuoi apostoli:\n"
        "«Vi lascio la pace, vi do la mia pace»,\n"
        "non guardare ai nostri peccati,\n"
        "ma alla fede della tua Chiesa,\n"
        "e donale unità e pace secondo la tua volontà.\n"
        "Tu che vivi e regni nei secoli dei secoli.\n"
        "R. Amen.\n\n"
        "La pace del Signore sia sempre con voi.\n"
        "R. E con il tuo spirito.\n\n"
        "Scambiatevi un segno di pace.\n\n"
        "Agnello di Dio, che togli i peccati del mondo, abbi pietà di noi.\n"
        "Agnello di Dio, che togli i peccati del mondo, abbi pietà di noi.\n"
        "Agnello di Dio, che togli i peccati del mondo, dona a noi la pace.",
    ),
    _vern_section(
        14,
        "Comunione",
        "Ecco l'Agnello di Dio,\n"
        "ecco colui che toglie i peccati del mondo.\n"
        "Beati gli invitati alla cena dell'Agnello.\n\n"
        "R. O Signore, non sono degno di partecipare alla tua mensa,\n"
        "ma di' soltanto una parola e io sarò salvato.\n\n"
        "[Al momento della comunione:]\n"
        "Il Corpo di Cristo. R. Amen.\n"
        "Il Sangue di Cristo. R. Amen.",
        rubric="Il sacerdote mostra ai fedeli il pane eucaristico, leggermente elevato sulla patena o sul calice.",
    ),
    _vern_section(
        15,
        "Riti di Conclusione · Benedizione e Congedo",
        "Il Signore sia con voi.\n"
        "R. E con il tuo spirito.\n\n"
        "Vi benedica Dio onnipotente,\n"
        "Padre e Figlio e Spirito Santo.\n"
        "R. Amen.\n\n"
        "Andate in pace.\n"
        "R. Rendiamo grazie a Dio.",
    ),
]



# ===========================================================================
# Missal catalogue
# ===========================================================================

MISSALS: List[Dict[str, Any]] = [
    {
        "slug": "novus-ordo",
        "name": "The Roman Missal",
        "subtitle": "Novus Ordo · Ordinary Form (1970)",
        "tradition": "Roman Rite · Ordinary Form",
        "language_note": "English (ICEL 2010) with Latin original",
        "accent_color": "#A87B3E",  # warm gold
        "icon": "book-outline",
        "vernacular_label": "English",
        "intro": (
            "Promulgated by Pope Paul VI in 1969 and received in the Latin editio typica of "
            "1970, the Novus Ordo Missae is the most widely-celebrated form of the Mass in "
            "the Latin Church today. This is the unchanging Order of Mass — the Ordinary — "
            "in English alongside the Latin original."
        ),
        "sections": NOVUS_ORDO_SECTIONS,
    },
    {
        "slug": "tlm",
        "name": "The Traditional Latin Mass",
        "subtitle": "1962 Missale Romanum · Extraordinary Form",
        "tradition": "Roman Rite · Tridentine / Vetus Ordo",
        "language_note": "Latin original with English translation",
        "accent_color": "#6B3A2E",  # ember claret
        "icon": "flame-outline",
        "vernacular_label": "English",
        "intro": (
            "The Tridentine Mass — codified by St. Pius V in 1570 and refined to its 1962 "
            "form by St. John XXIII — is the ancient Mass of the Roman Rite, prayed almost "
            "entirely in Latin and ad orientem (toward the Lord). The Priest's prayers, "
            "many spoken silently, ascend with the rising incense as a perpetual sacrifice "
            "of praise."
        ),
        "sections": TLM_SECTIONS,
    },
    {
        "slug": "ordinariate",
        "name": "Divine Worship · The Missal",
        "subtitle": "The Ordinariate Use (2015)",
        "tradition": "Roman Rite · Anglican Patrimony",
        "language_note": "Sacral (Cranmerian) English",
        "accent_color": "#3F5A4A",  # english sage
        "icon": "leaf-outline",
        "vernacular_label": "English",
        "intro": (
            "Divine Worship: The Missal is the proper missal of the three Personal "
            "Ordinariates for former Anglicans now in full communion with the Catholic "
            "Church. Promulgated by the Congregation for the Doctrine of the Faith in 2015, "
            "it preserves the venerable Anglican patrimony reconciled to Rome — the "
            "Collect for Purity, the Prayer of Humble Access, and the unmatched Tudor "
            "cadence of Cranmer's translations of the Roman liturgy."
        ),
        "sections": ORDINARIATE_SECTIONS,
    },
    {
        "slug": "roman-missal-es",
        "name": "El Misal Romano",
        "subtitle": "Novus Ordo · Forma Ordinaria · Español",
        "tradition": "Rito Romano · Forma Ordinaria",
        "language_note": "Español con el original en latín",
        "accent_color": "#9C5B2E",  # spanish ochre
        "icon": "book-outline",
        "vernacular_label": "Español",
        "intro": (
            "El Ordinario de la Misa del Misal Romano (Forma Ordinaria, 1970) tal como se "
            "celebra en español. Se ofrece el texto litúrgico oficial en castellano junto "
            "al original latino de la editio typica, para rezar y meditar la Misa en la "
            "propia lengua sin perder de vista la lengua de la Iglesia."
        ),
        "sections": SPANISH_NOVUS_ORDO_SECTIONS,
    },
    {
        "slug": "roman-missal-it",
        "name": "Il Messale Romano",
        "subtitle": "Novus Ordo · Forma Ordinaria · Italiano",
        "tradition": "Rito Romano · Forma Ordinaria",
        "language_note": "Italiano con l'originale latino",
        "accent_color": "#3E6B8A",  # italian azure
        "icon": "book-outline",
        "vernacular_label": "Italiano",
        "intro": (
            "L'Ordinario della Messa del Messale Romano (Forma Ordinaria, 1970) come si "
            "celebra in italiano, secondo la terza edizione italiana. Il testo liturgico "
            "ufficiale è posto accanto all'originale latino della editio typica, per "
            "pregare e meditare la Messa nella propria lingua."
        ),
        "sections": ITALIAN_NOVUS_ORDO_SECTIONS,
    },
]

MISSALS_BY_SLUG: Dict[str, Dict[str, Any]] = {m["slug"]: m for m in MISSALS}


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def _summary(m: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "slug": m["slug"],
        "name": m["name"],
        "subtitle": m["subtitle"],
        "tradition": m["tradition"],
        "language_note": m["language_note"],
        "accent_color": m["accent_color"],
        "icon": m["icon"],
        "vernacular_label": m.get("vernacular_label", "English"),
        "section_count": len(m["sections"]),
    }


def _detail(m: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **_summary(m),
        "intro": m["intro"],
        "sections": [
            {
                "index": i,
                "title": s["title"],
                "latin_title": s.get("latin_title"),
                "has_latin": bool(s.get("latin")),
            }
            for i, s in enumerate(m["sections"])
        ],
    }


def _section_payload(m: Dict[str, Any], idx: int) -> Dict[str, Any]:
    sections = m["sections"]
    if idx < 0 or idx >= len(sections):
        raise HTTPException(status_code=404, detail="Section not found")
    s = sections[idx]
    return {
        "slug": m["slug"],
        "missal_name": m["name"],
        "accent_color": m["accent_color"],
        "vernacular_label": m.get("vernacular_label", "English"),
        "index": idx,
        "total": len(sections),
        "title": s["title"],
        "latin_title": s.get("latin_title"),
        "english": s.get("english") or "",
        "latin": s.get("latin"),
        "rubric": s.get("rubric"),
        "note": s.get("note"),
        "prev": idx - 1 if idx > 0 else None,
        "next": idx + 1 if idx + 1 < len(sections) else None,
    }


def build_router(
    db: AsyncIOMotorDatabase,
    get_current_user: Callable,
) -> APIRouter:
    router = APIRouter(prefix="/missals", tags=["missals"])

    @router.get("")
    async def list_missals(user=Depends(get_current_user)):
        return {"items": [_summary(m) for m in MISSALS]}

    @router.get("/{slug}")
    async def get_missal(slug: str, user=Depends(get_current_user)):
        m = MISSALS_BY_SLUG.get(slug)
        if not m:
            raise HTTPException(status_code=404, detail="Missal not found")
        return _detail(m)

    @router.get("/{slug}/sections/{idx}")
    async def get_missal_section(slug: str, idx: int, user=Depends(get_current_user)):
        m = MISSALS_BY_SLUG.get(slug)
        if not m:
            raise HTTPException(status_code=404, detail="Missal not found")
        return _section_payload(m, idx)

    return router

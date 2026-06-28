"""Sanctus — Eastern Catholic Divine Liturgies.

The 23 sui iuris Eastern Catholic Churches worship in five great liturgical
families. This module provides the Order of the Divine Liturgy (the fixed
parts) for the principal liturgy of each tradition, in English, drawn from
public-domain / commonly-cited liturgical translations. As with the Roman
missals, only the unchanging Order is given — not the daily Propers.

Families & liturgies represented:
  * Byzantine (Constantinopolitan): Sts. John Chrysostom & Basil the Great
  * Alexandrian: Coptic Liturgy of St. Basil; Ge'ez (Ethiopic/Eritrean)
  * West Syriac (Antiochene): Maronite Qurbono; Syro-Malankara Liturgy of St. James
  * East Syriac (Chaldean): Holy Qurbana of Addai and Mari; Syro-Malabar Qurbana
  * Armenian: the Divine Liturgy (Patarag / Badarak)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _s(
    title: str,
    english: str,
    rubric: Optional[str] = None,
    original_title: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Eastern section. `original_title` is shown as the section's traditional
    name (e.g., 'Anaphora'); the body is English only."""
    return {
        "title": title,
        "latin_title": original_title.strip() if original_title else None,
        "english": english.strip(),
        "latin": None,
        "rubric": rubric.strip() if rubric else None,
        "note": note.strip() if note else None,
    }


# ===========================================================================
# BYZANTINE — Divine Liturgy of St. John Chrysostom
# ===========================================================================

BYZANTINE_CHRYSOSTOM: List[Dict[str, Any]] = [
    _s(
        "Blessing & Great Litany",
        "Blessed is the Kingdom of the Father, and of the Son, and of the Holy "
        "Spirit, now and ever and unto ages of ages.\nR. Amen.\n\n"
        "In peace let us pray to the Lord.\nR. Lord, have mercy.\n\n"
        "For the peace from above and for the salvation of our souls, let us "
        "pray to the Lord.\nR. Lord, have mercy.\n\n"
        "For the peace of the whole world, for the good estate of the holy "
        "Churches of God, and for the union of all, let us pray to the Lord.\n"
        "R. Lord, have mercy.\n\n"
        "Help us, save us, have mercy on us, and keep us, O God, by Thy grace.\n"
        "Calling to remembrance our all-holy, immaculate, most blessed and "
        "glorious Lady Theotokos and ever-Virgin Mary, with all the Saints, let "
        "us commend ourselves and one another, and all our life unto Christ our "
        "God.\nR. To Thee, O Lord.",
        rubric="The Liturgy of the Catechumens opens with the Deacon's litany of peace.",
        original_title="Synapté · Ἡ Μεγάλη Συναπτή",
    ),
    _s(
        "The Antiphons & Little Entrance",
        "Through the intercessions of the Theotokos, O Saviour, save us.\n\n"
        "O Son of God, who didst rise from the dead, save us who sing to Thee: "
        "Alleluia.\n\n"
        "Only-begotten Son and Word of God, who, being immortal, didst deign "
        "for our salvation to be incarnate of the holy Theotokos and ever-"
        "Virgin Mary, and without change didst become man; who wast crucified, "
        "O Christ our God, trampling down death by death; who art one of the "
        "Holy Trinity, glorified together with the Father and the Holy Spirit: "
        "save us.\n\n"
        "[Little Entrance with the Gospel Book:]\n"
        "Come, let us worship and fall down before Christ. O Son of God, save "
        "us who sing to Thee: Alleluia.",
        rubric="The hymn 'O Only-begotten Son' (Ho Monogenes) is traditionally ascribed to the Emperor St. Justinian.",
        original_title="Τὰ Ἀντίφωνα · Ὁ Μονογενὴς Υἱός",
    ),
    _s(
        "The Trisagion",
        "Holy God, Holy Mighty, Holy Immortal, have mercy on us. (×3)\n\n"
        "Glory to the Father, and to the Son, and to the Holy Spirit, now and "
        "ever and unto ages of ages. Amen.\n\n"
        "Holy Immortal, have mercy on us.\n"
        "Holy God, Holy Mighty, Holy Immortal, have mercy on us.",
        rubric="The Trisagion ('Thrice-Holy') is sung before the Epistle and Gospel.",
        original_title="Τρισάγιον",
    ),
    _s(
        "The Cherubic Hymn & Great Entrance",
        "We who mystically represent the Cherubim, and who sing to the life-"
        "giving Trinity the thrice-holy hymn, let us now lay aside all earthly "
        "cares.\n\n"
        "That we may receive the King of all, who comes invisibly upborne by "
        "the angelic hosts. Alleluia, Alleluia, Alleluia.\n\n"
        "[At the Great Entrance, the gifts are borne to the altar:]\n"
        "May the Lord God remember us all in His Kingdom, now and ever and unto "
        "ages of ages.\nR. Amen.",
        rubric="The Cherubikon accompanies the solemn transfer of the bread and wine to the holy table.",
        original_title="Χερουβικὸς Ὕμνος",
    ),
    _s(
        "The Creed",
        "I believe in one God, the Father Almighty, Maker of heaven and earth, "
        "and of all things visible and invisible.\n"
        "And in one Lord Jesus Christ, the Son of God, the Only-begotten, "
        "begotten of the Father before all ages. Light of Light, true God of "
        "true God, begotten, not made, of one essence with the Father, by whom "
        "all things were made.\n"
        "Who for us men and for our salvation came down from heaven, and was "
        "incarnate of the Holy Spirit and the Virgin Mary, and became man.\n"
        "And was crucified for us under Pontius Pilate, and suffered, and was "
        "buried. And the third day He rose again, according to the Scriptures.\n"
        "And ascended into heaven, and sitteth at the right hand of the Father. "
        "And He shall come again with glory to judge the living and the dead, "
        "whose Kingdom shall have no end.\n"
        "And in the Holy Spirit, the Lord, the Giver of Life, who proceedeth "
        "from the Father, who with the Father and the Son together is "
        "worshipped and glorified, who spake by the prophets.\n"
        "In one, holy, catholic, and apostolic Church. I confess one baptism "
        "for the remission of sins. I look for the resurrection of the dead, "
        "and the life of the age to come. Amen.",
        rubric="The Nicene-Constantinopolitan Creed is recited by all, often while the deacon waves the aër over the gifts.",
        original_title="Σύμβολον τῆς Πίστεως",
    ),
    _s(
        "The Anaphora & Words of Institution",
        "Let us stand aright; let us stand with fear; let us attend, that we "
        "may offer the holy oblation in peace.\nR. A mercy of peace, a "
        "sacrifice of praise.\n\n"
        "The grace of our Lord Jesus Christ, and the love of God the Father, "
        "and the communion of the Holy Spirit be with you all.\n"
        "R. And with thy spirit.\n"
        "Let us lift up our hearts.\nR. We lift them up unto the Lord.\n"
        "Let us give thanks unto the Lord.\nR. It is meet and right.\n\n"
        "Take, eat: this is my Body, which is broken for you for the remission "
        "of sins.\nR. Amen.\n\n"
        "Drink ye all of this: this is my Blood of the New Covenant, which is "
        "shed for you and for many for the remission of sins.\nR. Amen.\n\n"
        "Thine own of Thine own we offer unto Thee, in behalf of all and for "
        "all.\nR. We praise Thee, we bless Thee, we give thanks unto Thee, O "
        "Lord, and we pray unto Thee, O our God.",
        rubric="The Eucharistic Prayer culminates in the Epiklesis, the invocation of the Holy Spirit upon the gifts.",
        original_title="Ἀναφορά",
    ),
    _s(
        "The Hymn to the Theotokos",
        "It is truly meet to bless thee, O Theotokos, ever-blessed and most "
        "pure, and the Mother of our God. More honourable than the Cherubim, "
        "and beyond compare more glorious than the Seraphim; who without "
        "corruption gavest birth to God the Word, the very Theotokos, thee do "
        "we magnify.",
        rubric="The Axion Estin is sung in honour of the Mother of God after the consecration.",
        original_title="Ἄξιόν ἐστιν",
    ),
    _s(
        "The Lord's Prayer & Communion",
        "Our Father, who art in heaven, hallowed be Thy name; Thy Kingdom come; "
        "Thy will be done on earth as it is in heaven. Give us this day our "
        "daily bread, and forgive us our trespasses, as we forgive those who "
        "trespass against us; and lead us not into temptation, but deliver us "
        "from the evil one.\n\n"
        "The holy Things for the holy.\nR. One is holy, one is Lord, Jesus "
        "Christ, to the glory of God the Father. Amen.\n\n"
        "I believe, O Lord, and I confess that Thou art truly the Christ, the "
        "Son of the living God, who camest into the world to save sinners, of "
        "whom I am first. Of Thy Mystical Supper, O Son of God, accept me today "
        "as a communicant; for I will not speak of Thy Mystery to Thine "
        "enemies, neither will I give Thee a kiss as did Judas; but like the "
        "thief will I confess Thee: Remember me, O Lord, in Thy Kingdom.",
        rubric="The faithful approach to receive the Holy Mysteries from the chalice with the spoon.",
        original_title="Ἡ Θεία Κοινωνία",
    ),
    _s(
        "Dismissal",
        "Let us depart in peace.\nR. In the name of the Lord.\n\n"
        "Blessed be the name of the Lord, henceforth and for evermore.\n"
        "R. Amen. (×3)\n\n"
        "May Christ our true God, through the intercessions of His most pure "
        "Mother, of the holy and glorious Apostles, of our father among the "
        "saints John Chrysostom, Archbishop of Constantinople, and of all the "
        "Saints, have mercy on us and save us, for He is good and the Lover of "
        "mankind.\nR. Amen.",
        original_title="Ἀπόλυσις",
    ),
]


# ===========================================================================
# BYZANTINE — Divine Liturgy of St. Basil the Great
# ===========================================================================

BYZANTINE_BASIL: List[Dict[str, Any]] = [
    _s(
        "The Order in Common with St. John Chrysostom",
        "The Divine Liturgy of St. Basil the Great follows the same outward "
        "order as the Liturgy of St. John Chrysostom — the Great Litany, the "
        "Antiphons, the Little Entrance, the Trisagion, the readings, the "
        "Cherubic Hymn and Great Entrance, the Creed, and the Communion Rite "
        "are identical in structure. What distinguishes St. Basil's Liturgy "
        "are its far longer and more theologically rich priestly prayers, "
        "especially the Anaphora.",
        rubric="Celebrated ten times a year: the Sundays of Great Lent, Holy Thursday and Holy Saturday, the Vigils of Nativity and Theophany, and the feast of St. Basil (Jan. 1).",
    ),
    _s(
        "The Anaphora of St. Basil (the great thanksgiving)",
        "It is meet and right to hymn Thee, to bless Thee, to praise Thee, to "
        "give thanks unto Thee, and to worship Thee in every place of Thy "
        "dominion. For Thou art God ineffable, inconceivable, invisible, "
        "incomprehensible, ever-existing and eternally the same, Thou and Thine "
        "Only-begotten Son and Thy Holy Spirit.\n\n"
        "Holy art Thou and all-holy, Thou and Thine Only-begotten Son and Thy "
        "Holy Spirit; holy art Thou and all-holy, and magnificent is Thy glory; "
        "who hast so loved Thy world that Thou gavest Thine Only-begotten Son, "
        "that whosoever believeth in Him should not perish, but have "
        "everlasting life.",
        rubric="St. Basil's anaphora recounts at length the whole economy of salvation, from creation to the Incarnation.",
        original_title="Ἀναφορὰ τοῦ Μεγάλου Βασιλείου",
    ),
    _s(
        "The Words of Institution & Hymn to the Theotokos",
        "He gave it to His holy disciples and apostles, saying: Take, eat: this "
        "is my Body, which is broken for you for the remission of sins.\n\n"
        "Drink ye all of this: this is my Blood of the New Covenant, which is "
        "shed for you and for many for the remission of sins.\n\n"
        "[In place of the Axion Estin, St. Basil's Liturgy sings:]\n"
        "All creation rejoiceth in thee, O thou who art full of grace: the "
        "assembly of Angels and the race of men. O sanctified temple and "
        "spiritual paradise, the glory of virgins, of whom God was incarnate "
        "and became a little child, our God who is before the ages. He made "
        "thy body into a throne, and thy womb He made more spacious than the "
        "heavens. All creation rejoiceth in thee, O thou who art full of grace: "
        "glory to thee.",
        original_title="Ἐπὶ σοὶ χαίρει",
    ),
]


# ===========================================================================
# WEST SYRIAC (ANTIOCHENE) — Maronite Holy Qurbono
# ===========================================================================

MARONITE_QURBONO: List[Dict[str, Any]] = [
    _s(
        "Opening & Glory to the Trinity",
        "Glory to the Father, and to the Son, and to the Holy Spirit, now and "
        "for ever. Amen.\n\n"
        "To you, O Lord, we lift up our eyes; to you we offer the glory of "
        "this Holy Sacrifice. Make us worthy, Lord God, to praise you with the "
        "watchful angels, and to sing your glory with the choirs above.",
        rubric="The Maronite Church traces its liturgy to the Antiochene tradition and to St. Maron; its Qurbono ('Offering') is celebrated chiefly in Syriac-Aramaic and the vernacular.",
        original_title="Qurbono",
    ),
    _s(
        "The Hoosoyo (Prayer of Forgiveness)",
        "O Lord, who pardons sins and blots out iniquities, cleanse us from all "
        "our offenses; wash away the stains of our souls by the hyssop of your "
        "mercy, that, made pure, we may offer you a pure offering and a holy "
        "sacrifice, and may glorify you, Father, Son, and Holy Spirit, now and "
        "for ever.\nR. Amen.",
        rubric="The Hoosoyo, with its incense, is a distinctive prayer of propitiation in the West Syriac rites.",
        original_title="Ḥusoyo",
    ),
    _s(
        "The Trisagion",
        "Holy are you, O God.\nHoly are you, O Strong One.\nHoly are you, O "
        "Immortal One.\nYou were crucified for us; have mercy on us. (×3)\n\n"
        "Glory to the Father, and to the Son, and to the Holy Spirit, now and "
        "for ever. Amen.",
        rubric="The Antiochene Trisagion adds 'You were crucified for us,' addressing the hymn to Christ.",
        original_title="Qadishat Aloho",
    ),
    _s(
        "The Anaphora of Sharar / the Twelve Apostles · Words of Institution",
        "Lift up your minds and your hearts.\nR. They are with you, O God.\n"
        "Let us give thanks to the Lord in awe.\nR. It is right and just.\n\n"
        "While he was taking bread in his holy hands, he blessed it, sanctified "
        "it, broke it, and gave it to his disciples, saying: Take and eat from "
        "it; this is my Body, which is broken and given for you and for many "
        "for the forgiveness of sins and for eternal life.\nR. Amen.\n\n"
        "Likewise over the cup he gave thanks, blessed it, and gave it to them, "
        "saying: Take and drink from it, all of you; this is my Blood of the "
        "New Covenant, which is shed for you and for many for the forgiveness "
        "of sins and for eternal life.\nR. Amen.",
        rubric="The Maronite rite preserves the ancient Anaphora of Saint Peter (Sharar), among the oldest Eucharistic prayers in Christendom.",
        original_title="Anaphora",
    ),
    _s(
        "The Lord's Prayer & Communion",
        "Our Father, who art in heaven, hallowed be thy name; thy kingdom come; "
        "thy will be done on earth as it is in heaven. Give us this day our "
        "daily bread, and forgive us our trespasses, as we forgive those who "
        "trespass against us; and lead us not into temptation, but deliver us "
        "from the evil one.\n\n"
        "Holy gifts for the holy and the pure.\n\n"
        "[At Communion:] The Body and Blood of Christ, for the pardon of "
        "offenses and the forgiveness of sins, for eternal life. Amen.",
        original_title="Abun d'bashmayo",
    ),
]


# ===========================================================================
# EAST SYRIAC (CHALDEAN) — Holy Qurbana of Addai and Mari
# ===========================================================================

CHALDEAN_ADDAI_MARI: List[Dict[str, Any]] = [
    _s(
        "Opening Doxology (the Lakhumara)",
        "Glory to God in the highest, and on earth peace and good hope to men, "
        "at all times, for ever. Amen.\n\n"
        "Lord of all, we confess you; Jesus Christ, we glorify you; for you are "
        "the Raiser of our bodies, and the Saviour of our souls.",
        rubric="The Holy Qurbana of the Apostles Addai and Mari is among the most ancient Eucharistic liturgies still in use, dating to the early Church of the East at Edessa.",
        original_title="Qurbana Qadisha",
    ),
    _s(
        "The Trisagion & Readings",
        "Holy God, Holy Mighty, Holy Immortal, have mercy on us. (×3)\n\n"
        "Glory to the Father, and to the Son, and to the Holy Spirit, from "
        "everlasting to everlasting. Amen and amen.\n\n"
        "[The Lessons from the Law and the Prophets, the Epistle of the blessed "
        "Apostle Paul, and the Holy Gospel are proclaimed.]",
        original_title="Qadisha Alaha",
    ),
    _s(
        "The Anaphora & Institution Narrative",
        "The grace of our Lord Jesus Christ, the love of God the Father, and the "
        "fellowship of the Holy Spirit be with us all, now and for ever.\n"
        "R. Amen.\n"
        "Lift up your minds.\nR. Unto you, O God of Abraham, Isaac, and Israel, "
        "O glorious King.\nThe Offering is offered to God, the Lord of all.\n"
        "R. It is meet and right.\n\n"
        "As our Lord Jesus Christ commanded us, we make the memorial of his "
        "Body and his Blood, offering to you, Lord, the living and holy "
        "Sacrifice. Take, eat: this is my Body, which is broken for you for the "
        "forgiveness of sins. This is my Blood of the New Covenant, which is "
        "shed for many for the forgiveness of sins.",
        rubric="In 2001 the Holy See recognized the validity and antiquity of this Anaphora, even in its traditional form.",
        original_title="Anaphora d'Sliha",
    ),
    _s(
        "The Lord's Prayer & Communion",
        "Our Father in heaven, hallowed be your name; your kingdom come; your "
        "will be done, as in heaven so on earth. Give us the bread we need this "
        "day; and forgive us our debts and our sins, as we forgive our debtors; "
        "and do not let us enter into temptation, but deliver us from the evil "
        "one. For yours is the kingdom, the power, and the glory, for ever and "
        "ever. Amen.\n\n"
        "The Holy Thing is given to the holy.\n\n"
        "[At Communion:] The Body of our Lord to the discerning servant for the "
        "pardon of offenses. Amen.",
        original_title="Abun d'bashmayya",
    ),
]


# ===========================================================================
# EAST SYRIAC — Syro-Malabar Holy Qurbana (India)
# ===========================================================================

SYRO_MALABAR: List[Dict[str, Any]] = [
    _s(
        "The Holy Qurbana of the Syro-Malabar Church",
        "The Syro-Malabar Church, of the St. Thomas Christians of India, "
        "celebrates the Holy Qurbana in the East Syriac tradition, the same "
        "Anaphora of Addai and Mari, in Syriac, Malayalam, and other "
        "vernaculars. The Mass opens:\n\n"
        "Glory to God in the highest, and on earth peace and good hope to all "
        "people, now, always, and for ever. Amen.",
        rubric="Tradition holds that the Apostle St. Thomas himself planted the faith in India in A.D. 52.",
        original_title="Qurbana",
    ),
    _s(
        "The Anaphora & Institution",
        "Lift up your minds.\nR. To you, O God of Abraham, Isaac, and Jacob, O "
        "glorious King.\nThe Oblation is offered to God, the Lord of all.\n"
        "R. It is fitting and right.\n\n"
        "Take, eat from this, all of you: this is my Body which is broken for "
        "you for the forgiveness of sins.\n\n"
        "Take, drink from this, all of you: this is my Blood of the New "
        "Covenant which is shed for many for the forgiveness of sins.\n\n"
        "Holy Things to the holy ones, fittingly.",
        original_title="Anaphora",
    ),
]


# ===========================================================================
# WEST SYRIAC — Syro-Malankara Holy Qurbono of St. James (India)
# ===========================================================================

SYRO_MALANKARA: List[Dict[str, Any]] = [
    _s(
        "The Holy Qurbono of Saint James",
        "The Syro-Malankara Catholic Church, also of the St. Thomas Christian "
        "heritage, follows the West Syriac (Antiochene) tradition and "
        "celebrates the venerable Liturgy of St. James — held by tradition to "
        "be the oldest of all the apostolic liturgies, ascribed to St. James "
        "the brother of the Lord, first Bishop of Jerusalem.\n\n"
        "Glory to the Father, and to the Son, and to the living Holy Spirit, "
        "now and for ever. Amen.",
        original_title="Qurbono d'Mar Yaqub",
    ),
    _s(
        "The Trisagion & Anaphora of St. James",
        "Holy art Thou, O God. Holy art Thou, O Almighty. Holy art Thou, O "
        "Immortal, who wast crucified for us; have mercy on us. (×3)\n\n"
        "Lift up your minds and your hearts.\nR. They are with the Lord God.\n"
        "Let us give thanks to the Lord in fear.\nR. It is meet and right.\n\n"
        "Take, eat of it: this is my Body, which is broken and distributed for "
        "the pardon of debts and the forgiveness of sins and for eternal life. "
        "Drink of it, all of you: this is my Blood of the New Covenant, shed "
        "for the life of the world.",
        original_title="Qadishat Aloho · Anaphora",
    ),
]


# ===========================================================================
# ALEXANDRIAN — Coptic Catholic Divine Liturgy of St. Basil
# ===========================================================================

COPTIC_BASIL: List[Dict[str, Any]] = [
    _s(
        "The Coptic Divine Liturgy of St. Basil",
        "The Coptic Catholic Church celebrates the Alexandrian rite, chiefly "
        "the Divine Liturgy of St. Basil, in Coptic, Arabic, and the "
        "vernacular. The Liturgy of the Word and the Liturgy of the Faithful "
        "are framed by the prayer of thanksgiving and the offering of the "
        "Lamb.\n\n"
        "In the name of the Father, and of the Son, and of the Holy Spirit, "
        "one God. Amen. Blessed be God the Father of our Lord Jesus Christ. "
        "Blessed be His only-begotten Son, Jesus Christ. Blessed be the Holy "
        "Spirit, the Paraclete.",
        rubric="The Coptic Church venerates St. Mark the Evangelist as the founder of the See of Alexandria.",
        original_title="Ⲡⲓⲁⲅⲓⲟⲥ · Anaphora of St. Basil",
    ),
    _s(
        "The Institution Narrative",
        "He instituted for us this great mystery of godliness. For having "
        "determined to give Himself up to death for the life of the world, He "
        "took bread into His holy, spotless, unblemished, blessed, and "
        "life-giving hands; He looked up to heaven to You, O God who are His "
        "Father and Master of everyone; He gave thanks, He blessed it, He "
        "sanctified it, He broke it, and gave it to His own holy disciples and "
        "apostles, saying:\n\n"
        "Take, eat of it all of you; for this is My Body, which is broken for "
        "you and for many, to be given for the remission of sins. Do this in "
        "remembrance of Me.\n\n"
        "Likewise the cup after supper: Take, drink of it all of you; for this "
        "is My Blood of the New Covenant, which is shed for you and for many, "
        "to be given for the remission of sins. Do this in remembrance of Me.",
        original_title="Anaphora",
    ),
    _s(
        "Fraction, the Lord's Prayer & Communion",
        "Our Father who art in heaven, hallowed be Thy name; Thy kingdom come; "
        "Thy will be done on earth as it is in heaven. Give us this day our "
        "daily bread, and forgive us our trespasses, as we forgive those who "
        "trespass against us; and lead us not into temptation, but deliver us "
        "from the evil one.\n\n"
        "The Holies for the holy. Blessed be the Lord Jesus Christ, the Son of "
        "God; the sanctification of the Holy Spirit. Amen.\n\n"
        "[At Communion:] The Body and Blood of Emmanuel our God; this is in "
        "truth. Amen.",
        original_title="Ⲡⲉⲛⲓⲱⲧ",
    ),
]


# ===========================================================================
# ALEXANDRIAN — Ge'ez (Ethiopic / Eritrean) Divine Liturgy
# ===========================================================================

GEEZ_LITURGY: List[Dict[str, Any]] = [
    _s(
        "The Divine Liturgy in the Ge'ez Tradition",
        "The Ethiopian and Eritrean Catholic Churches celebrate the Alexandrian "
        "rite in the ancient Ge'ez language. Their principal anaphora is the "
        "Anaphora of the Apostles, one of fourteen anaphoras in their rich "
        "tradition.\n\n"
        "Holy God, Holy Mighty, Holy Immortal and living: have mercy upon us, "
        "O Lord. Glory be to the Father, and to the Son, and to the Holy "
        "Spirit, now and ever and world without end. Amen.",
        rubric="The Ge'ez liturgy is renowned for its sacred chant (zema) and drums, and its solemn antiquity.",
        original_title="Qǝddase",
    ),
    _s(
        "The Anaphora of the Apostles & Institution",
        "Lift up your hearts.\nR. We have lifted them up unto the Lord our God.\n"
        "Let us give thanks unto the Lord.\nR. It is meet and right.\n\n"
        "Who, in the night in which He was betrayed, took bread in His holy, "
        "blessed, and spotless hands; He looked up to heaven unto You, His own "
        "Father; He gave thanks, He blessed, and He brake, and gave to His "
        "disciples, saying: Take, eat; this bread is My Body, which is broken "
        "for you for the remission of sin.\n\n"
        "Likewise the cup of thanksgiving He blessed, and gave to them, saying: "
        "Take, drink; this cup is My Blood, which is shed for you for the "
        "remission of sin. As often as you do this, do it in remembrance of Me.",
        original_title="Anaphora of the Apostles",
    ),
]


# ===========================================================================
# ARMENIAN — The Divine Liturgy (Patarag / Badarak)
# ===========================================================================

ARMENIAN_PATARAG: List[Dict[str, Any]] = [
    _s(
        "Opening & the Monogenes",
        "In the name of the Father, and of the Son, and of the Holy Spirit. "
        "Amen.\n\n"
        "O Only-begotten Son and Word of God, who art immortal, who didst deign "
        "for our salvation to be incarnate of the holy Mother of God and "
        "ever-Virgin Mary; who without change didst become man and wast "
        "crucified; O Christ our God, who by Thy death didst trample down "
        "death, who art one of the Holy Trinity, glorified together with the "
        "Father and the Holy Spirit: save us.",
        rubric="The Armenian Catholic Church preserves the distinctive Armenian rite; its Divine Liturgy is the Patarag (Badarak), 'the Offering.'",
        original_title="Պատարագ · Patarag",
    ),
    _s(
        "The Trisagion (Armenian form)",
        "Holy God, holy and mighty, holy and immortal, who wast crucified for "
        "us, have mercy upon us. (×3)\n\n"
        "Blessed and glorified, ever-worshipped Holy Trinity, who hast granted "
        "us to attain to this hour of the praise of Thy holy name: grant us, O "
        "Lord, peace and mercy.",
        original_title="Surb Astvats",
    ),
    _s(
        "The Anaphora of St. Athanasius & Institution",
        "The grace, the love, and the divine sanctifying power of the Father, "
        "and of the Son, and of the Holy Spirit be with you all.\n"
        "R. Amen, and with thy spirit.\n"
        "The doors, the doors. With all wisdom and good heed lift up your minds "
        "in the fear of God.\nR. We have lifted them up unto Thee, O Lord "
        "Almighty.\nAnd give thanks unto the Lord with the whole heart.\n"
        "R. It is meet and right.\n\n"
        "He took bread in His holy, divine, immortal, spotless, and creative "
        "hands; He blessed, gave thanks, brake, and gave to His chosen, holy "
        "disciples who were seated, saying: Take, eat; this is My Body, which "
        "is distributed for you and for many, for the expiation and remission "
        "of sins.\n\n"
        "Likewise, taking the cup, He blessed, gave thanks, drank, and gave it "
        "to His chosen, holy disciples, saying: Drink ye all of this; this is "
        "My Blood of the New Covenant, which is shed for you and for many, for "
        "the expiation and remission of sins.",
        original_title="Anaphora of St. Athanasius",
    ),
    _s(
        "The Lord's Prayer & Communion",
        "Our Father who art in heaven, hallowed be Thy name; Thy kingdom come; "
        "Thy will be done on earth as it is in heaven. Give us this day our "
        "daily bread, and forgive us our trespasses, as we forgive those who "
        "trespass against us; and lead us not into temptation, but deliver us "
        "from evil. For Thine is the kingdom, and the power, and the glory, for "
        "ever. Amen.\n\n"
        "Unto holiness the holy. The fullness of the Holy Spirit. Amen.\n\n"
        "[At Communion:] This is the Body and Blood of our Lord and Saviour "
        "Jesus Christ, distributed unto us for the expiation and remission of "
        "our sins.",
        original_title="Hayr mer",
    ),
]

"""Sanctus — Eastern Catholic Divine Liturgies (full Order).

The 23 sui iuris Eastern Catholic Churches worship in five great liturgical
families. This module gives the COMPLETE Order of the Divine Liturgy — the
fixed parts, in sequence, with the people's responses — for the principal
liturgy of each tradition, so a worshipper can follow the entire celebration
from the preparation of the gifts to the dismissal. Texts follow public-domain
/ commonly-cited liturgical translations. Only the variable daily Propers
(changing hymns and readings) are omitted, as in the Roman missals.

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
# BYZANTINE — Divine Liturgy of St. John Chrysostom  (full Order)
# ===========================================================================

BYZANTINE_CHRYSOSTOM: List[Dict[str, Any]] = [
    _s(
        "The Proskomedia (Preparation of the Gifts)",
        "Before the Liturgy begins, at the table of preparation, the priest cuts "
        "the Lamb from the prosphora (offering bread) and pours wine and water "
        "into the chalice, commemorating the Theotokos, the angels, the saints, "
        "and the living and the dead.\n\n"
        "Thou hast redeemed us from the curse of the law by Thy precious Blood; "
        "nailed to the Cross and pierced with the lance, Thou hast poured forth "
        "immortality upon mankind. O our Saviour, glory to Thee.\n\n"
        "[As he covers the gifts:] The Lord is King, He is clothed with majesty; "
        "the Lord is clothed with strength and hath girded Himself.",
        rubric="The Proskomedia is prayed quietly by the priest before the people gather; it prepares the bread and wine that will be offered.",
        original_title="Προσκομιδή · the Prothesis",
    ),
    _s(
        "Opening Blessing & the Great Litany",
        "Blessed is the Kingdom of the Father, and of the Son, and of the Holy "
        "Spirit, now and ever and unto ages of ages.\nR. Amen.\n\n"
        "In peace let us pray to the Lord.\nR. Lord, have mercy.\n"
        "For the peace from above and for the salvation of our souls, let us "
        "pray to the Lord.\nR. Lord, have mercy.\n"
        "For the peace of the whole world, for the good estate of the holy "
        "Churches of God, and for the union of all, let us pray to the Lord.\n"
        "R. Lord, have mercy.\n"
        "For this holy temple, and for those who enter it with faith, "
        "reverence, and the fear of God, let us pray to the Lord.\n"
        "R. Lord, have mercy.\n"
        "For seasonable weather, abundance of the fruits of the earth, and "
        "peaceful times, let us pray to the Lord.\nR. Lord, have mercy.\n"
        "Help us, save us, have mercy on us, and keep us, O God, by Thy grace.\n"
        "Calling to remembrance our all-holy, immaculate, most blessed and "
        "glorious Lady Theotokos and ever-Virgin Mary, with all the Saints, let "
        "us commend ourselves and one another, and all our life unto Christ our "
        "God.\nR. To Thee, O Lord.",
        rubric="The Liturgy of the Word opens with the Deacon's Great Litany (the Litany of Peace).",
        original_title="Ἡ Μεγάλη Συναπτή",
    ),
    _s(
        "The Antiphons & 'Only-Begotten Son'",
        "[First Antiphon:] Through the intercessions of the Theotokos, O "
        "Saviour, save us.\n\n"
        "[Second Antiphon:] O Son of God, who didst rise from the dead, save us "
        "who sing to Thee: Alleluia.\n\n"
        "Only-begotten Son and Word of God, who, being immortal, didst deign for "
        "our salvation to be incarnate of the holy Theotokos and ever-Virgin "
        "Mary, and without change didst become man; who wast crucified, O Christ "
        "our God, trampling down death by death; who art one of the Holy "
        "Trinity, glorified together with the Father and the Holy Spirit: save "
        "us.",
        rubric="Between the antiphons the deacon prays the Little Litanies. The hymn 'Ho Monogenes' is ascribed to the Emperor St. Justinian.",
        original_title="Τὰ Ἀντίφωνα · Ὁ Μονογενὴς Υἱός",
    ),
    _s(
        "The Little Entrance",
        "[Third Antiphon — the Beatitudes — is sung as the Gospel Book is carried "
        "in procession. The priest prays:]\n\n"
        "O Master, Lord our God, who hast appointed in heaven orders and hosts "
        "of angels and archangels for the service of Thy glory: grant that with "
        "our entrance there may be an entrance of holy angels, serving with us "
        "and glorifying Thy goodness.\n\n"
        "Wisdom! Let us attend!\nR. Come, let us worship and fall down before "
        "Christ. O Son of God, who didst rise from the dead, save us who sing to "
        "Thee: Alleluia.",
        rubric="The Little Entrance with the Book of the Gospels signifies Christ coming forth to preach.",
        original_title="Ἡ Μικρὰ Εἴσοδος",
    ),
    _s(
        "The Trisagion",
        "Holy God, Holy Mighty, Holy Immortal, have mercy on us. (×3)\n\n"
        "Glory to the Father, and to the Son, and to the Holy Spirit, now and "
        "ever and unto ages of ages. Amen.\n\n"
        "Holy Immortal, have mercy on us.\n"
        "Holy God, Holy Mighty, Holy Immortal, have mercy on us.",
        rubric="The Trisagion ('Thrice-Holy') is sung just before the readings.",
        original_title="Τρισάγιον",
    ),
    _s(
        "The Epistle & Gospel",
        "[Prokeimenon — a verse from the Psalms — is sung. Then:]\n\n"
        "Wisdom! Let us attend! [The Epistle is read.]\n\n"
        "Alleluia, Alleluia, Alleluia. (with verses)\n\n"
        "Wisdom! Arise! Let us hear the holy Gospel. Peace be unto all.\n"
        "R. And to thy spirit.\n"
        "The reading from the holy Gospel according to N.\n"
        "R. Glory to Thee, O Lord, glory to Thee.\n\n"
        "[After the Gospel:]\nR. Glory to Thee, O Lord, glory to Thee.",
        rubric="The proper Epistle and Gospel of the day are proclaimed; a homily follows.",
        original_title="Ὁ Ἀπόστολος καὶ τὸ Εὐαγγέλιον",
    ),
    _s(
        "Litany of Fervent Supplication & for the Catechumens",
        "Let us all say with our whole soul and with our whole mind, let us say:\n"
        "R. Lord, have mercy.\n"
        "Have mercy on us, O God, according to Thy great mercy; we pray Thee, "
        "hearken and have mercy.\nR. Lord, have mercy (×3, after each petition).\n\n"
        "[Litany for the Catechumens:]\nYe catechumens, pray to the Lord.\n"
        "R. Lord, have mercy.\n"
        "That He may reveal unto them the Gospel of righteousness, and unite "
        "them to His holy, catholic, and apostolic Church, let us pray to the "
        "Lord.\nR. Lord, have mercy.\n"
        "As many as are catechumens, depart; ye catechumens, depart. As many as "
        "are of the faithful, again and again in peace let us pray to the Lord.\n"
        "R. Lord, have mercy.",
        rubric="So ends the Liturgy of the Catechumens; the Liturgy of the Faithful begins.",
        original_title="Ἐκτενής · Litany for the Catechumens",
    ),
    _s(
        "The Cherubic Hymn & Great Entrance",
        "We who mystically represent the Cherubim, and who sing to the "
        "life-giving Trinity the thrice-holy hymn, let us now lay aside all "
        "earthly cares;\n\n"
        "That we may receive the King of all, who comes invisibly upborne by "
        "the angelic hosts. Alleluia, Alleluia, Alleluia.\n\n"
        "[At the Great Entrance the gifts are borne to the holy table:]\n"
        "May the Lord God remember us all in His Kingdom, now and ever and unto "
        "ages of ages.\nR. Amen.",
        rubric="The Cherubikon accompanies the solemn transfer of the bread and wine from the table of preparation to the altar.",
        original_title="Χερουβικὸς Ὕμνος · Ἡ Μεγάλη Εἴσοδος",
    ),
    _s(
        "Litany of Supplication & the Kiss of Peace",
        "Let us complete our prayer unto the Lord.\nR. Lord, have mercy.\n"
        "For the precious gifts here set forth, let us pray to the Lord.\n"
        "R. Lord, have mercy.\n"
        "That the whole day may be perfect, holy, peaceful, and sinless, let us "
        "ask of the Lord.\nR. Grant this, O Lord.\n"
        "An angel of peace, a faithful guide, a guardian of our souls and "
        "bodies, let us ask of the Lord.\nR. Grant this, O Lord.\n"
        "A Christian ending to our life, painless, blameless, and peaceful, and "
        "a good defence before the dread judgement seat of Christ, let us ask.\n"
        "R. Grant this, O Lord.\n\n"
        "Let us love one another, that with one mind we may confess:\n"
        "R. The Father, and the Son, and the Holy Spirit: the Trinity, one in "
        "essence and undivided.",
        rubric="The faithful exchange the kiss of peace as the deacon proclaims the unity of the Church.",
        original_title="Πληρωτικά",
    ),
    _s(
        "The Creed",
        "The doors! The doors! In wisdom let us attend.\n\n"
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
        "from the Father, who with the Father and the Son together is worshipped "
        "and glorified, who spake by the prophets.\n"
        "In one, holy, catholic, and apostolic Church. I confess one baptism "
        "for the remission of sins. I look for the resurrection of the dead, and "
        "the life of the age to come. Amen.",
        rubric="The Nicene-Constantinopolitan Creed is recited by all.",
        original_title="Σύμβολον τῆς Πίστεως",
    ),
    _s(
        "The Anaphora — Thanksgiving & the Sanctus",
        "Let us stand aright; let us stand with fear; let us attend, that we may "
        "offer the holy oblation in peace.\nR. A mercy of peace, a sacrifice of "
        "praise.\n\n"
        "The grace of our Lord Jesus Christ, and the love of God the Father, "
        "and the communion of the Holy Spirit be with you all.\n"
        "R. And with thy spirit.\n"
        "Let us lift up our hearts.\nR. We lift them up unto the Lord.\n"
        "Let us give thanks unto the Lord.\nR. It is meet and right to worship "
        "the Father, and the Son, and the Holy Spirit, the Trinity, one in "
        "essence and undivided.\n\n"
        "Singing the triumphant hymn, shouting, proclaiming, and saying:\n"
        "R. Holy, holy, holy, Lord of Sabaoth; heaven and earth are full of Thy "
        "glory. Hosanna in the highest. Blessed is He that cometh in the name of "
        "the Lord. Hosanna in the highest.",
        rubric="The great Eucharistic Prayer begins with the dialogue and the Angelic Hymn.",
        original_title="Ἀναφορά · Ἐπινίκιος Ὕμνος",
    ),
    _s(
        "The Words of Institution & the Epiklesis",
        "Take, eat: this is my Body, which is broken for you for the remission "
        "of sins.\nR. Amen.\n\n"
        "Drink ye all of this: this is my Blood of the New Covenant, which is "
        "shed for you and for many for the remission of sins.\nR. Amen.\n\n"
        "Thine own of Thine own we offer unto Thee, in behalf of all and for "
        "all.\nR. We praise Thee, we bless Thee, we give thanks unto Thee, O "
        "Lord, and we pray unto Thee, O our God.\n\n"
        "[The Epiklesis — invocation of the Holy Spirit:]\nAnd make this bread "
        "the precious Body of Thy Christ; and that which is in this cup, the "
        "precious Blood of Thy Christ; changing them by Thy Holy Spirit.\n"
        "R. Amen. Amen. Amen.",
        rubric="In the East the change is especially attributed to the Epiklesis, the calling-down of the Holy Spirit upon the gifts.",
        original_title="Ἐπίκλησις",
    ),
    _s(
        "Hymn to the Theotokos & Commemorations",
        "Especially for our all-holy, immaculate, most blessed and glorious Lady "
        "Theotokos and ever-Virgin Mary.\n\n"
        "R. It is truly meet to bless thee, O Theotokos, ever-blessed and most "
        "pure, and the Mother of our God. More honourable than the Cherubim, and "
        "beyond compare more glorious than the Seraphim; who without corruption "
        "gavest birth to God the Word, the very Theotokos, thee do we magnify.\n\n"
        "Among the first, remember, O Lord, our Holy Father N., Pope of Rome, "
        "and our Bishop N.; grant them to Thy holy Churches in peace.\n"
        "R. And all mankind.",
        rubric="The Axion Estin is sung in honour of the Mother of God while the priest commemorates the living and the dead.",
        original_title="Ἄξιόν ἐστιν",
    ),
    _s(
        "The Lord's Prayer",
        "And make us worthy, O Master, with boldness and without condemnation, to "
        "dare to call upon Thee, the heavenly God, as Father, and to say:\n\n"
        "R. Our Father, who art in heaven, hallowed be Thy name; Thy Kingdom "
        "come; Thy will be done on earth as it is in heaven. Give us this day our "
        "daily bread, and forgive us our trespasses, as we forgive those who "
        "trespass against us; and lead us not into temptation, but deliver us "
        "from the evil one.\n\n"
        "For Thine is the Kingdom, and the power, and the glory, of the Father, "
        "and of the Son, and of the Holy Spirit, now and ever and unto ages of "
        "ages.\nR. Amen.",
        original_title="Ἡ Κυριακὴ Προσευχή",
    ),
    _s(
        "The Elevation & Holy Communion",
        "Let us attend! The holy Things for the holy.\n"
        "R. One is holy, one is Lord, Jesus Christ, to the glory of God the "
        "Father. Amen.\n\n"
        "[Before receiving, all pray:]\nI believe, O Lord, and I confess that "
        "Thou art truly the Christ, the Son of the living God, who camest into "
        "the world to save sinners, of whom I am first. Of Thy Mystical Supper, "
        "O Son of God, accept me today as a communicant; for I will not speak of "
        "Thy Mystery to Thine enemies, neither will I give Thee a kiss as did "
        "Judas; but like the thief will I confess Thee: Remember me, O Lord, in "
        "Thy Kingdom.\n\n"
        "[The faithful receive the Body and Blood of Christ together from the "
        "chalice, with the spoon.]",
        rubric="The Lamb is broken, a portion placed in the chalice, and warm water (the zeon) added before Communion.",
        original_title="Ἡ Θεία Κοινωνία",
    ),
    _s(
        "Thanksgiving, Prayer Before the Ambo & Dismissal",
        "Let us stand aright. Having received the divine, holy, pure, immortal, "
        "heavenly, and life-giving, fearful Mysteries of Christ, let us worthily "
        "give thanks unto the Lord.\nR. Lord, have mercy.\n\n"
        "Let us depart in peace.\nR. In the name of the Lord.\n\n"
        "[Prayer before the Ambo:] O Lord, who blessest those that bless Thee, "
        "and sanctifiest those that put their trust in Thee: save Thy people and "
        "bless Thine inheritance; preserve the fullness of Thy Church.\n\n"
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
        "How to Follow This Liturgy",
        "The Divine Liturgy of St. Basil the Great follows the SAME order as the "
        "Liturgy of St. John Chrysostom — the Proskomedia, the Great Litany, the "
        "Antiphons and Little Entrance, the Trisagion, the readings, the Cherubic "
        "Hymn and Great Entrance, the Creed, the Communion Rite, and the "
        "Dismissal are identical in structure. To follow those parts, use the "
        "Liturgy of St. John Chrysostom in this app.\n\n"
        "What is proper to St. Basil are the long, theologically magnificent "
        "PRIESTLY PRAYERS — above all the Anaphora and the hymn to the Theotokos "
        "— given below.",
        rubric="Celebrated ten times a year: the Sundays of Great Lent, Holy Thursday and Holy Saturday, the Vigils of the Nativity and Theophany, and the feast of St. Basil (Jan. 1).",
    ),
    _s(
        "The Anaphora of St. Basil — Thanksgiving & Sanctus",
        "The grace of our Lord Jesus Christ, and the love of God the Father, and "
        "the communion of the Holy Spirit be with you all.\nR. And with thy "
        "spirit.\nLet us lift up our hearts.\nR. We lift them up unto the Lord.\n"
        "Let us give thanks unto the Lord.\nR. It is meet and right.\n\n"
        "O Existing One, Master, Lord, God, Father Almighty and adorable: it is "
        "truly meet and right and befitting the majesty of Thy holiness to "
        "praise Thee, to hymn Thee, to bless Thee, to worship Thee, to give "
        "thanks unto Thee, to glorify Thee, the only truly existing God.\n\n"
        "R. Holy, holy, holy, Lord of Sabaoth; heaven and earth are full of Thy "
        "glory. Hosanna in the highest. Blessed is He that cometh in the name of "
        "the Lord. Hosanna in the highest.",
        rubric="St. Basil's anaphora recounts at length the whole economy of salvation, from creation to the Incarnation.",
        original_title="Ἀναφορὰ τοῦ Μεγάλου Βασιλείου",
    ),
    _s(
        "The Words of Institution & Epiklesis",
        "He gave it to His holy disciples and apostles, saying: Take, eat: this "
        "is my Body, which is broken for you for the remission of sins.\nR. Amen.\n\n"
        "Drink ye all of this: this is my Blood of the New Covenant, which is "
        "shed for you and for many for the remission of sins.\nR. Amen.\n\n"
        "Thine own of Thine own we offer unto Thee, in behalf of all and for "
        "all.\nR. We praise Thee, we bless Thee, we give thanks unto Thee, O "
        "Lord, and we pray unto Thee, O our God.\n\n"
        "[Epiklesis:] We pray Thee, send down Thy Holy Spirit upon us and upon "
        "these gifts here set forth, and show this bread to be the precious Body "
        "of our Lord and God and Saviour Jesus Christ, and this cup the precious "
        "Blood of our Lord and God and Saviour Jesus Christ, shed for the life of "
        "the world.\nR. Amen. Amen. Amen.",
        original_title="Ἐπίκλησις",
    ),
    _s(
        "Hymn to the Theotokos (proper to St. Basil)",
        "Especially for our all-holy, immaculate, most blessed and glorious Lady "
        "Theotokos and ever-Virgin Mary.\n\n"
        "R. All creation rejoiceth in thee, O thou who art full of grace: the "
        "assembly of Angels and the race of men. O sanctified temple and "
        "spiritual paradise, the glory of virgins, of whom God was incarnate and "
        "became a little child, our God who is before the ages. He made thy body "
        "into a throne, and thy womb He made more spacious than the heavens. All "
        "creation rejoiceth in thee, O thou who art full of grace: glory to thee.",
        rubric="In place of the Axion Estin, St. Basil's Liturgy sings 'All creation rejoiceth.'",
        original_title="Ἐπὶ σοὶ χαίρει",
    ),
    _s(
        "The Lord's Prayer, Communion & Dismissal",
        "And make us worthy, O Master, to dare to call upon Thee, the heavenly "
        "God, as Father, and to say:\n"
        "R. Our Father, who art in heaven... (as in the Liturgy of St. John "
        "Chrysostom).\n\n"
        "The holy Things for the holy.\nR. One is holy, one is Lord, Jesus "
        "Christ, to the glory of God the Father. Amen.\n\n"
        "[Communion, thanksgiving, and dismissal follow the same order as the "
        "Liturgy of St. John Chrysostom, concluding:]\nMay Christ our true God, "
        "through the intercessions of His most pure Mother, of our father among "
        "the saints Basil the Great, Archbishop of Caesarea in Cappadocia, and "
        "of all the Saints, have mercy on us and save us.\nR. Amen.",
        original_title="Ἀπόλυσις",
    ),
]


# ===========================================================================
# WEST SYRIAC (ANTIOCHENE) — Maronite Holy Qurbono  (full Order)
# ===========================================================================

MARONITE_QURBONO: List[Dict[str, Any]] = [
    _s(
        "Rite of Preparation & Opening Doxology",
        "Glory to the Father, and to the Son, and to the Holy Spirit, now and "
        "for ever. Amen.\n\n"
        "To you, O Lord, we lift up our eyes; to you we offer the glory of this "
        "Holy Sacrifice. Make us worthy, Lord God, to praise you with the "
        "watchful angels, and to sing your glory with the choirs above.\n\n"
        "[Opening hymn, e.g. the 'Lord, have mercy upon us' or a Marian "
        "qolo, is sung.]",
        rubric="The Maronite Church of Lebanon, never separated from Rome, celebrates the Qurbono ('Offering') in the Antiochene tradition, in Syriac-Aramaic and the vernacular.",
        original_title="Qurbono",
    ),
    _s(
        "The Hoosoyo (Prayer of Forgiveness) & Incense",
        "O Lord, who pardons sins and blots out iniquities, cleanse us from all "
        "our offenses; wash away the stains of our souls by the hyssop of your "
        "mercy, that, made pure, we may offer you a pure offering and a holy "
        "sacrifice, and may glorify you, Father, Son, and Holy Spirit.\nR. Amen.\n\n"
        "[The fragrant incense is offered:] May our prayer rise before you, O "
        "Lord, like incense, and the lifting up of our hands like the evening "
        "sacrifice.",
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
        "The Liturgy of the Word",
        "[The Lessons from the Old Testament, the Epistle of St. Paul, and the "
        "Holy Gospel are proclaimed.]\n\n"
        "From the Gospel of our Lord Jesus Christ, the proclamation of life and "
        "salvation to us.\nR. Glory to Christ our Lord.\n\n"
        "[After the Gospel and homily:]\nR. We believe and confess. Glory to "
        "Christ our Lord.",
        rubric="The Liturgy of the Word concludes with the Creed (the Nicene Creed, in the Maronite form).",
        original_title="Qeryono",
    ),
    _s(
        "The Anaphora — Sursum Corda & Sanctus",
        "The love of God the Father, the grace of the Only-Begotten Son, and the "
        "fellowship and descent of the Holy Spirit be with you all, my brothers "
        "and sisters, for ever.\nR. Amen.\n"
        "Lift up your minds and your hearts.\nR. They are with you, O God.\n"
        "Let us give thanks to the Lord in awe.\nR. It is right and just.\n\n"
        "R. Holy, holy, holy, Lord God of hosts; heaven and earth are full of "
        "his glory. Hosanna in the highest. Blessed is he who has come and is to "
        "come in the name of the Lord. Hosanna in the highest.",
        rubric="The Maronite rite preserves the ancient Anaphora of St. Peter (Sharar), among the oldest Eucharistic prayers in Christendom.",
        original_title="Anaphora",
    ),
    _s(
        "The Words of Institution & Epiclesis",
        "While he was taking bread in his holy hands, he blessed it, sanctified "
        "it, broke it, and gave it to his disciples, saying: Take and eat from "
        "it; this is my Body, which is broken and given for you and for many for "
        "the forgiveness of sins and for eternal life.\nR. Amen.\n\n"
        "Likewise over the cup he gave thanks, blessed it, and gave it to them, "
        "saying: Take and drink from it, all of you; this is my Blood of the New "
        "Covenant, which is shed for you and for many for the forgiveness of "
        "sins and for eternal life.\nR. Amen.\n\n"
        "[Epiclesis:] Hear me, O Lord; send your living and Holy Spirit upon us "
        "and upon these gifts, that he may make this bread the holy Body of "
        "Christ and this cup the precious Blood of Christ.\nR. Amen.",
        original_title="Institution & Epiclesis",
    ),
    _s(
        "The Lord's Prayer & Fraction",
        "Our Father, who art in heaven, hallowed be thy name; thy kingdom come; "
        "thy will be done on earth as it is in heaven. Give us this day our daily "
        "bread, and forgive us our trespasses, as we forgive those who trespass "
        "against us; and lead us not into temptation, but deliver us from the "
        "evil one.\n\n"
        "[The priest breaks the Host and signs the Blood with it:] We break the "
        "heavenly Bread and sign the Cup of salvation in the name of the Father, "
        "and of the Son, and of the living Holy Spirit, for ever.\nR. Amen.",
        original_title="Abun d'bashmayo",
    ),
    _s(
        "Holy Communion & Final Blessing",
        "Holy gifts for the holy and the pure.\n\n"
        "[At Communion:] The Body and Blood of Christ, for the pardon of "
        "offenses and the forgiveness of sins, for eternal life.\nR. Amen.\n\n"
        "[Thanksgiving and blessing:] Go in peace, my brothers and sisters, as "
        "we entrust you to the grace and mercy of the Holy Trinity, with the "
        "provisions and the blessing you have received from the propitiatory "
        "altar of the Lord.\nR. Amen.",
        rubric="The faithful receive the Holy Mysteries; the priest blesses and dismisses the assembly.",
        original_title="Communion & Dismissal",
    ),
]


# ===========================================================================
# EAST SYRIAC (CHALDEAN) — Holy Qurbana of Addai and Mari  (full Order)
# ===========================================================================

CHALDEAN_ADDAI_MARI: List[Dict[str, Any]] = [
    _s(
        "Opening Doxology (the Lakhumara)",
        "Glory to God in the highest, and on earth peace and good hope to men, at "
        "all times, for ever. Amen.\n\n"
        "Our Father in heaven, hallowed be your name... (the Lord's Prayer is "
        "said here in the Chaldean use, with the Marmitha — the psalmody).\n\n"
        "Lord of all, we confess you; Jesus Christ, we glorify you; for you are "
        "the Raiser of our bodies, and the Saviour of our souls.",
        rubric="The Holy Qurbana of the Apostles Addai and Mari is among the most ancient Eucharistic liturgies still in use, from the early Church of the East at Edessa.",
        original_title="Qurbana Qadisha",
    ),
    _s(
        "The Trisagion & the Lessons",
        "Holy God, Holy Mighty, Holy Immortal, have mercy on us. (×3)\n\n"
        "Glory to the Father, and to the Son, and to the Holy Spirit, from "
        "everlasting to everlasting. Amen and amen.\n\n"
        "[The Lessons from the Law and the Prophets, the Epistle (Shlikha) of "
        "the blessed Apostle Paul, and the Holy Gospel are proclaimed, with the "
        "chants between them.]\nR. Glory to Christ our Lord.",
        original_title="Qadisha Alaha",
    ),
    _s(
        "Litanies, Creed & the Transfer of the Gifts",
        "Let us all stand well, and pray, and beseech: Lord, have mercy.\n"
        "R. Lord, have mercy.\n\n"
        "[The Creed (the Nicene Creed in the East Syriac form) is professed:]\n"
        "We believe in one God, the Father almighty, maker of all things visible "
        "and invisible... and in one Lord Jesus Christ... and in the one Holy "
        "Spirit... Amen.\n\n"
        "[The gifts of bread and wine are brought to the altar and the Kiss of "
        "Peace is exchanged.]\nGive peace to one another in the love of Christ.",
        original_title="Onitha d'Raze",
    ),
    _s(
        "The Anaphora — Dialogue & Sanctus",
        "The grace of our Lord Jesus Christ, the love of God the Father, and the "
        "fellowship of the Holy Spirit be with us all, now and for ever.\n"
        "R. Amen.\nLift up your minds.\nR. Unto you, O God of Abraham, Isaac, and "
        "Israel, O glorious King.\nThe Offering is offered to God, the Lord of "
        "all.\nR. It is meet and right.\n\n"
        "R. Holy, holy, holy is the Lord God of hosts; heaven and earth are full "
        "of his praises, and of the nature of his being, and of the excellency "
        "of his glorious splendour. Hosanna in the highest.",
        rubric="In 2001 the Holy See recognized the validity and antiquity of this Anaphora, even in its traditional form.",
        original_title="Anaphora d'Sliha",
    ),
    _s(
        "The Anamnesis & Institution Narrative",
        "As our Lord Jesus Christ commanded us, we make the memorial of his Body "
        "and his Blood, offering to you, O Lord, the living and holy Sacrifice.\n\n"
        "Take, eat: this is my Body, which is broken for you for the forgiveness "
        "of sins.\n\n"
        "This is my Blood of the New Covenant, which is shed for many for the "
        "forgiveness of sins.\n\n"
        "[Epiclesis:] May your Holy Spirit, O Lord, come and rest upon this "
        "offering of your servants; may he bless and sanctify it, that it may be "
        "to us for the pardon of offenses and the forgiveness of sins.\nR. Amen.",
        original_title="Institution & Epiclesis",
    ),
    _s(
        "The Lord's Prayer, Fraction & Communion",
        "Our Father in heaven, hallowed be your name; your kingdom come; your "
        "will be done, as in heaven so on earth. Give us the bread we need this "
        "day; and forgive us our debts and our sins, as we forgive our debtors; "
        "and do not let us enter into temptation, but deliver us from the evil "
        "one. For yours is the kingdom, the power, and the glory, for ever and "
        "ever. Amen.\n\n"
        "The Holy Thing is given to the holy.\nR. One holy Father, one holy Son, "
        "one Holy Spirit. Amen.\n\n"
        "[At Communion:] The Body of our Lord to the discerning servant for the "
        "pardon of offenses.\nR. Amen.",
        original_title="Abun d'bashmayya",
    ),
    _s(
        "Thanksgiving & Dismissal",
        "We give you thanks, O Lord our God, and we praise you abundantly, for "
        "the great grace which you have bestowed upon us: for you have clothed us "
        "with our bodies and saved our souls by your grace.\n\n"
        "Go in peace, rejoicing and glad, and pray for me. May the grace and "
        "mercy of the Holy Trinity be with you, and with us, now and for ever.\n"
        "R. Amen.",
        original_title="Huttama · the Sealing",
    ),
]


# ===========================================================================
# EAST SYRIAC — Syro-Malabar Holy Qurbana (India)  (full Order)
# ===========================================================================

SYRO_MALABAR: List[Dict[str, Any]] = [
    _s(
        "Introductory Rites",
        "The Syro-Malabar Church, of the St. Thomas Christians of India, "
        "celebrates the Holy Qurbana in the East Syriac tradition (the Anaphora "
        "of Addai and Mari) in Syriac, Malayalam, and other vernaculars. The "
        "Mass opens:\n\n"
        "Glory to God in the highest, and on earth peace and good hope to all "
        "people, now, always, and for ever. Amen.\n\n"
        "Our Father in heaven... (the Lord's Prayer with the opening psalmody "
        "and the hymn Lakumara).",
        rubric="Tradition holds that the Apostle St. Thomas himself planted the faith in India in A.D. 52.",
        original_title="Qurbana",
    ),
    _s(
        "The Trisagion & the Liturgy of the Word",
        "Holy God, Holy Mighty, Holy Immortal One, have mercy on us. (×3)\n\n"
        "[The Lessons, the Epistle of St. Paul, and the Holy Gospel are "
        "proclaimed, with the Karozutha (litany) and chants.]\n"
        "R. Glory to Christ our Lord.",
        original_title="Qaddisha Alaha",
    ),
    _s(
        "The Creed & Transfer of the Gifts",
        "We believe in one God, the Father almighty, maker of all things, of "
        "things visible and invisible; and in one Lord Jesus Christ, the "
        "Only-Begotten Son of God... and in the Holy Spirit... and in one holy, "
        "catholic and apostolic Church. Amen.\n\n"
        "[The gifts are placed upon the altar; the Kiss of Peace is given.]\n"
        "Give peace to one another, each to his neighbour, in the love of "
        "Christ.",
        original_title="Creed & Rite of Peace",
    ),
    _s(
        "The Anaphora — Dialogue, Sanctus & Institution",
        "Lift up your minds.\nR. To you, O God of Abraham, Isaac, and Jacob, O "
        "glorious King.\nThe Oblation is offered to God, the Lord of all.\n"
        "R. It is fitting and right.\n\n"
        "R. Holy, holy, holy is the Lord, the God of hosts; heaven and earth are "
        "full of his glory. Hosanna in the highest.\n\n"
        "Take, eat from this, all of you: this is my Body which is broken for "
        "you for the forgiveness of sins.\n\n"
        "Take, drink from this, all of you: this is my Blood of the New Covenant "
        "which is shed for many for the forgiveness of sins.",
        original_title="Anaphora",
    ),
    _s(
        "The Epiclesis & the Lord's Prayer",
        "[Epiclesis:] May your Holy Spirit come, O Lord, and rest upon this "
        "offering of your servants, and bless and sanctify it, that it may be to "
        "us for the pardon of debts and the forgiveness of sins.\nR. Amen.\n\n"
        "Our Father in heaven, hallowed be your name; your kingdom come; your "
        "will be done on earth as it is in heaven. Give us this day the bread we "
        "need; and forgive us our debts and sins, as we also forgive our "
        "debtors; and let us not fall into temptation, but deliver us from the "
        "evil one. For yours is the kingdom, the power, and the glory, for ever. "
        "Amen.",
        original_title="Epiclesis · Abun d'bashmayya",
    ),
    _s(
        "Fraction, Communion & Thanksgiving",
        "Holy Things to the holy ones, fittingly.\nR. One holy Father, one holy "
        "Son, one Holy Spirit. Amen.\n\n"
        "[At Communion:] The Body and the Blood of our Lord Jesus Christ for the "
        "pardon of debts and the forgiveness of sins.\nR. Amen.\n\n"
        "We give thanks to you, O Lord, for all your benefits. Go in peace, "
        "rejoicing, and pray for one another. May the grace of our Lord Jesus "
        "Christ be with you all.\nR. Amen.",
        original_title="Communion & Huttama",
    ),
]


# ===========================================================================
# WEST SYRIAC — Syro-Malankara Holy Qurbono of St. James (India)  (full Order)
# ===========================================================================

SYRO_MALANKARA: List[Dict[str, Any]] = [
    _s(
        "Introductory Rites & Opening Glory",
        "The Syro-Malankara Catholic Church, also of the St. Thomas Christian "
        "heritage, follows the West Syriac (Antiochene) tradition and celebrates "
        "the venerable Liturgy of St. James — by tradition the oldest of all the "
        "apostolic liturgies, ascribed to St. James the Brother of the Lord, "
        "first Bishop of Jerusalem.\n\n"
        "Glory to the Father, and to the Son, and to the living Holy Spirit, now "
        "and for ever. Amen.\n\n"
        "[The opening prayer (Promiyon-Sedro) with incense, and the Marian and "
        "saints' hymns, are sung.]",
        original_title="Qurbono d'Mar Yaqub",
    ),
    _s(
        "The Trisagion & the Liturgy of the Word",
        "Holy art thou, O God. Holy art thou, O Almighty. Holy art thou, O "
        "Immortal, who wast crucified for us; have mercy on us. (×3)\n\n"
        "[The Lessons, the Epistle of St. Paul, and the Holy Gospel are "
        "proclaimed.]\nFrom the holy Gospel of our Lord Jesus Christ.\n"
        "R. Glory be to thee, O Lord.",
        original_title="Qadishat Aloho",
    ),
    _s(
        "The Creed & the Kiss of Peace",
        "We believe in one God, the Father almighty, maker of heaven and earth... "
        "and in one Lord Jesus Christ... and in the Holy Spirit, the Lord, the "
        "Giver of life... and in one holy, catholic and apostolic Church... and "
        "we look for the resurrection of the dead and the new life in the world "
        "to come. Amen.\n\n"
        "Give peace to one another with a holy and divine kiss, in the love of "
        "our Lord.\nR. We give you thanks, O Lord, and we bless you.",
        original_title="Creed & Rite of Peace",
    ),
    _s(
        "The Anaphora — Dialogue & Sanctus",
        "The love of God the Father, the grace of the Only-Begotten Son, and the "
        "fellowship and descent of the Holy Spirit be with you all.\nR. Amen.\n"
        "Lift up your minds and your hearts.\nR. They are with the Lord God.\n"
        "Let us give thanks to the Lord in fear.\nR. It is meet and right.\n\n"
        "R. Holy, holy, holy, Lord God almighty, of whose glory heaven and earth "
        "are full. Hosanna in the highest. Blessed is he who has come and is to "
        "come in the name of the Lord. Hosanna in the highest.",
        original_title="Anaphora of St. James",
    ),
    _s(
        "The Words of Institution & Epiclesis",
        "He took bread in his holy hands; he blessed, he sanctified, he broke, "
        "and gave it to his disciples, saying: Take, eat of it; this is my Body, "
        "which is broken and distributed for the pardon of debts and the "
        "forgiveness of sins and for eternal life.\nR. Amen.\n\n"
        "Likewise the cup: Drink of it, all of you; this is my Blood of the New "
        "Covenant, which is shed and offered for the pardon of debts and the "
        "forgiveness of sins and for eternal life.\nR. Amen.\n\n"
        "[Epiclesis:] Send upon us and upon these gifts your living and Holy "
        "Spirit, that he may make this bread the life-giving Body and this cup "
        "the Blood of the New Covenant of our Lord Jesus Christ.\nR. Amen, amen, "
        "amen.",
        original_title="Institution & Epiclesis",
    ),
    _s(
        "The Lord's Prayer, Communion & Dismissal",
        "Our Father, who art in heaven, hallowed be thy name; thy kingdom come; "
        "thy will be done on earth as it is in heaven. Give us this day our daily "
        "bread, and forgive us our debts and sins, as we also have forgiven our "
        "debtors; and lead us not into temptation, but deliver us from the evil "
        "one. For thine is the kingdom, the power, and the glory, for ever. Amen.\n\n"
        "Holy things to the holy.\nR. One holy Father, one holy Son, one living "
        "Holy Spirit. Amen.\n\n"
        "[At Communion:] The propitiatory live coal of the Body and Blood of "
        "Christ our God is given for the pardon of debts and the forgiveness of "
        "sins.\nR. Amen.\n\n"
        "Go in peace, rejoicing and glad; and pray for me. May the love of God "
        "be with you for ever.\nR. Amen.",
        original_title="Abun d'bashmayo · Dismissal",
    ),
]


# ===========================================================================
# ALEXANDRIAN — Coptic Catholic Divine Liturgy of St. Basil  (full Order)
# ===========================================================================

COPTIC_BASIL: List[Dict[str, Any]] = [
    _s(
        "Offering of the Lamb & Opening",
        "The Coptic Catholic Church celebrates the Alexandrian rite — the "
        "tradition of St. Mark — chiefly through the Divine Liturgy of St. Basil, "
        "in Coptic, Arabic, and the vernacular.\n\n"
        "In the name of the Father, and of the Son, and of the Holy Spirit, one "
        "God. Amen. Blessed be God the Father of our Lord Jesus Christ. Blessed "
        "be his only-begotten Son, Jesus Christ. Blessed be the Holy Spirit, the "
        "Paraclete.\n\n"
        "[At the altar the priest chooses and offers the Lamb (the bread) and "
        "pours the wine and a little water into the chalice.]",
        rubric="The Offering of the Lamb prepares the gifts before the Liturgy of the Word.",
        original_title="Anaphora of St. Basil",
    ),
    _s(
        "The Liturgy of the Word",
        "[Incense is offered. The Pauline Epistle, the Catholic Epistle, the Acts "
        "of the Apostles, and the Holy Gospel are proclaimed, with the Trisagion "
        "between them:]\n\n"
        "Holy God, Holy Mighty, Holy Immortal, who was born of the Virgin, have "
        "mercy on us.\nHoly God, Holy Mighty, Holy Immortal, who was crucified "
        "for us, have mercy on us.\nHoly God, Holy Mighty, Holy Immortal, who "
        "rose from the dead and ascended into the heavens, have mercy on us.\n\n"
        "A reading from the Holy Gospel according to N.\nR. Glory to you, O Lord.",
        rubric="The Coptic Trisagion adds the events of salvation; readings follow with the homily.",
        original_title="Liturgy of the Word",
    ),
    _s(
        "The Prayer of Reconciliation, Creed & Kiss of Peace",
        "We believe in one God, God the Father, the Pantocrator, who created "
        "heaven and earth... And in one Lord Jesus Christ, the only-begotten Son "
        "of God... And in the Holy Spirit, the Lord, the Giver of Life... And in "
        "one holy, catholic and apostolic Church... Amen.\n\n"
        "Greet one another with a holy kiss.\n\n"
        "[The Prayer of Reconciliation precedes the Anaphora:]\nO God, who, "
        "because of your unspeakable love for mankind, sent your only-begotten "
        "Son into the world... make us all worthy to greet one another with a "
        "holy kiss.",
        original_title="Creed & Aspasmos",
    ),
    _s(
        "The Anaphora — Dialogue & Sanctus",
        "The Lord be with you all.\nR. And with your spirit.\nLift up your "
        "hearts.\nR. We have them with the Lord.\nLet us give thanks to the "
        "Lord.\nR. It is meet and right.\n\n"
        "R. Holy, holy, holy, Lord of hosts; heaven and earth are full of your "
        "holy glory.",
        original_title="Anaphora",
    ),
    _s(
        "The Institution Narrative & Epiclesis",
        "He took bread into his holy, spotless, unblemished, blessed, and "
        "life-giving hands; he looked up to heaven to you, O God who are his "
        "Father and Master of everyone; he gave thanks, he blessed it, he "
        "sanctified it, he broke it, and gave it to his own holy disciples and "
        "apostles, saying:\n\n"
        "Take, eat of it all of you; for this is my Body, which is broken for "
        "you and for many, to be given for the remission of sins. Do this in "
        "remembrance of me.\nR. Amen.\n\n"
        "Likewise the cup after supper: Take, drink of it all of you; for this "
        "is my Blood of the New Covenant, which is shed for you and for many, to "
        "be given for the remission of sins. Do this in remembrance of me.\n"
        "R. Amen. We proclaim your death, O Lord, and confess your holy "
        "resurrection and ascension.\n\n"
        "[Epiclesis:] We ask you, O Lord, send down the Holy Spirit upon us and "
        "upon these gifts, and make this bread the holy Body and this cup the "
        "precious Blood of your Christ.",
        original_title="Institution & Epiclesis",
    ),
    _s(
        "The Lord's Prayer, Fraction & Communion",
        "Our Father who art in heaven, hallowed be thy name; thy kingdom come; "
        "thy will be done on earth as it is in heaven. Give us this day our daily "
        "bread, and forgive us our trespasses, as we forgive those who trespass "
        "against us; and lead us not into temptation, but deliver us from the "
        "evil one.\n\n"
        "The Holies for the holy. Blessed be the Lord Jesus Christ, the Son of "
        "God; the sanctification of the Holy Spirit. Amen.\nR. One is the "
        "all-holy Father, one is the all-holy Son, one is the Holy Spirit. Amen.\n\n"
        "[At Communion:] The Body and Blood of Emmanuel our God; this is in "
        "truth. Amen.",
        original_title="Pen-iot · the Lord's Prayer",
    ),
    _s(
        "Thanksgiving & Dismissal",
        "Our mouths are filled with gladness and our tongues with joy, for we "
        "have partaken of your immortal Mysteries, O Lord.\n\n"
        "Go in peace; the peace of the Lord be with you all.\nR. And with your "
        "spirit.\n\nMay the grace and blessing of the Holy Trinity remain with "
        "you all.\nR. Amen.",
        original_title="Dismissal",
    ),
]


# ===========================================================================
# ALEXANDRIAN — Ge'ez (Ethiopic / Eritrean) Divine Liturgy  (full Order)
# ===========================================================================

GEEZ_LITURGY: List[Dict[str, Any]] = [
    _s(
        "Preparation & Opening",
        "The Ethiopian and Eritrean Catholic Churches celebrate the Alexandrian "
        "rite in the ancient Ge'ez language, renowned for sacred chant (zema) and "
        "the drum and sistrum. The Liturgy begins with the preparation of the "
        "gifts (the Pre-Anaphora) and the Prayer of Thanksgiving.\n\n"
        "Holy God, Holy Mighty, Holy Immortal and living: have mercy upon us, O "
        "Lord. Glory be to the Father, and to the Son, and to the Holy Spirit, "
        "now and ever and world without end. Amen.",
        rubric="The Ge'ez Liturgy has fourteen anaphoras; the most common is the Anaphora of the Apostles.",
        original_title="Qǝddase",
    ),
    _s(
        "The Liturgy of the Word",
        "[The Pauline Epistle, the Catholic Epistle, the Acts of the Apostles, "
        "and the Holy Gospel are read, with the Trisagion and the Mystagogy.]\n\n"
        "Holy, Holy, Holy, perfect Trinity, grant us to praise you.\n\n"
        "A reading from the Gospel of our Lord and our God and our Saviour Jesus "
        "Christ.\nR. Glory be to you, O Lord, our God, for ever.",
        original_title="Liturgy of the Word",
    ),
    _s(
        "The Creed & the Kiss of Peace",
        "We believe in one God, the Lord, the Father, who holds all things, "
        "maker of heaven and earth, of things seen and unseen... And we believe "
        "in one Lord Jesus Christ... And we believe in the Holy Spirit, the "
        "Lord, the Giver of life... And in one holy, catholic and apostolic "
        "Church... Amen.\n\n"
        "Greet one another with a holy kiss.",
        original_title="Creed & Aspasmos",
    ),
    _s(
        "The Anaphora of the Apostles — Dialogue & Sanctus",
        "The Lord be with you all.\nR. And with your spirit.\nLift up your "
        "hearts.\nR. We have lifted them up unto the Lord our God.\nLet us give "
        "thanks unto the Lord.\nR. It is meet and right.\n\n"
        "R. Holy, Holy, Holy, Lord of hosts; heaven and earth are full of the "
        "holiness of your glory.",
        original_title="Anaphora of the Apostles",
    ),
    _s(
        "The Institution Narrative & Epiclesis",
        "Who, in the night in which he was betrayed, took bread in his holy, "
        "blessed, and spotless hands; he looked up to heaven unto you, his own "
        "Father; he gave thanks, he blessed, and he brake, and gave to his "
        "disciples, saying: Take, eat; this bread is my Body, which is broken "
        "for you for the remission of sin.\nR. Amen, amen, amen; we believe and "
        "we confess.\n\n"
        "Likewise the cup of thanksgiving he blessed, and gave to them, saying: "
        "Take, drink; this cup is my Blood, which is shed for you for the "
        "remission of sin. As often as you do this, do it in remembrance of me.\n\n"
        "[Epiclesis:] Send the Holy Spirit and power upon this bread and upon "
        "this cup; may he make them the Body and Blood of our Lord and Saviour "
        "Jesus Christ for ever.\nR. Amen.",
        original_title="Institution & Epiclesis",
    ),
    _s(
        "The Lord's Prayer, Communion & Dismissal",
        "Our Father who art in heaven, hallowed be thy name; thy kingdom come; "
        "thy will be done on earth as it is in heaven. Give us this day our daily "
        "bread, and forgive us our trespasses, as we forgive those who trespass "
        "against us; and lead us not into temptation, but deliver us from the "
        "evil one.\n\n"
        "Holy things for the holy.\nR. One is the holy Father, one is the holy "
        "Son, one is the Holy Spirit.\n\n"
        "[At Communion:] This is the Body of Emmanuel our God; this is in truth. "
        "Amen. — This is the Blood of Emmanuel our God; this is in truth. Amen.\n\n"
        "Go in the peace of the Lord.\nR. Amen.",
        original_title="Abùna · Communion & Dismissal",
    ),
]


# ===========================================================================
# ARMENIAN — The Divine Liturgy (Patarag / Badarak)  (full Order)
# ===========================================================================

ARMENIAN_PATARAG: List[Dict[str, Any]] = [
    _s(
        "Preparation & 'Only-Begotten Son'",
        "The Armenian Catholic Church preserves the distinctive Armenian rite; "
        "its Divine Liturgy is the Patarag (Badarak, 'the Offering'). It opens "
        "with the vesting and the preparation of the gifts, then the hymn of the "
        "Only-Begotten Son.\n\n"
        "In the name of the Father, and of the Son, and of the Holy Spirit. "
        "Amen.\n\n"
        "O Only-begotten Son and Word of God, who art immortal, who didst deign "
        "for our salvation to be incarnate of the holy Mother of God and "
        "ever-Virgin Mary; who without change didst become man and wast "
        "crucified; O Christ our God, who by thy death didst trample down death, "
        "who art one of the Holy Trinity, glorified together with the Father and "
        "the Holy Spirit: save us.",
        original_title="Պատարագ · Patarag",
    ),
    _s(
        "The Liturgy of the Word",
        "[The Midday Office, the hymns, the censing, and the Scriptures: the "
        "Prophecy, the Epistle of St. Paul, and the Holy Gospel.]\n\n"
        "Proschume! Let us attend. Peace be to all.\nR. And with your spirit.\n"
        "The holy Gospel of Jesus Christ according to N.\nR. Glory to you, O "
        "Lord our God.\n\n"
        "[After the Gospel:]\nR. Glory to you, O Lord our God.",
        original_title="Liturgy of the Word",
    ),
    _s(
        "The Trisagion & the Creed",
        "Holy God, holy and mighty, holy and immortal, who wast crucified for us, "
        "have mercy upon us. (×3)\n\n"
        "We believe in one God, the Father almighty, maker of heaven and earth, "
        "of things visible and invisible. And in one Lord Jesus Christ, the Son "
        "of God... And in the Holy Spirit, the uncreate and the perfect... in "
        "one only, catholic, and apostolic Church... Amen.",
        original_title="Surb Astvats · Creed",
    ),
    _s(
        "The Great Entrance & Kiss of Peace",
        "[The gifts are brought to the altar in solemn procession as the choir "
        "sings:]\nThe body of the Lord and the blood of the Saviour are set "
        "before us. The heavenly hosts invisibly sing and say: Holy, holy, holy, "
        "Lord of hosts.\n\n"
        "Greet one another with a holy kiss.\nR. Christ in our midst has been "
        "revealed.\nR. Blessed is the revelation of Christ.",
        original_title="The Great Entrance",
    ),
    _s(
        "The Anaphora — Dialogue & Sanctus",
        "The grace, the love, and the divine sanctifying power of the Father, and "
        "of the Son, and of the Holy Spirit be with you all.\nR. Amen, and with "
        "thy spirit.\nThe doors, the doors. With all wisdom and good heed lift up "
        "your minds in the fear of God.\nR. We have lifted them up unto thee, O "
        "Lord Almighty.\nAnd give thanks unto the Lord with the whole heart.\n"
        "R. It is meet and right.\n\n"
        "R. Holy, holy, holy, Lord of hosts; heaven and earth are full of thy "
        "glory. Blessing in the highest. Blessed art thou who didst come and art "
        "to come in the name of the Lord. Hosanna in the highest.",
        original_title="Anaphora of St. Athanasius",
    ),
    _s(
        "The Words of Institution & Epiclesis",
        "He took bread in his holy, divine, immortal, spotless, and creative "
        "hands; he blessed, gave thanks, brake, and gave to his chosen, holy "
        "disciples who were seated, saying: Take, eat; this is my Body, which is "
        "distributed for you and for many, for the expiation and remission of "
        "sins.\n\n"
        "Likewise, taking the cup, he blessed, gave thanks, and gave it to them, "
        "saying: Drink ye all of this; this is my Blood of the New Covenant, "
        "which is shed for you and for many, for the expiation and remission of "
        "sins.\nR. Amen.\n\n"
        "[Epiclesis:] We worship and beseech thee, send upon us and upon these "
        "gifts here set forth thy coeternal Holy Spirit; and make this bread the "
        "Body of our Lord and Saviour Jesus Christ, and this cup the Blood of our "
        "Lord and Saviour Jesus Christ.\nR. Amen.",
        original_title="Institution & Epiclesis",
    ),
    _s(
        "The Lord's Prayer, Communion & Dismissal",
        "Our Father who art in heaven, hallowed be thy name; thy kingdom come; "
        "thy will be done on earth as it is in heaven. Give us this day our daily "
        "bread, and forgive us our trespasses, as we forgive those who trespass "
        "against us; and lead us not into temptation, but deliver us from evil. "
        "For thine is the kingdom, and the power, and the glory, for ever. Amen.\n\n"
        "Unto holiness the holy. The fullness of the Holy Spirit. Amen.\n"
        "R. One is holy, one is Lord, Jesus Christ, to the glory of God the "
        "Father. Amen.\n\n"
        "[At Communion:] This is the Body and Blood of our Lord and Saviour "
        "Jesus Christ, distributed unto us for the expiation and remission of "
        "our sins.\nR. Amen.\n\n"
        "Be ye blessed by the grace of the Holy Spirit; go in peace, and the "
        "Lord be with you all.\nR. Amen.",
        original_title="Hayr mer · Communion & Dismissal",
    ),
]

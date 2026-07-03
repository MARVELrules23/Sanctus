/**
 * Catholic Devotions & Prayers — a curated in-app library of the Church's
 * treasured prayers, litanies, the Stations of the Cross, prayers before and
 * after Mass and Communion, acts of faith, and seasonal devotions.
 *
 * Each devotion reuses the BeadStep shape (label + prayer) and is rendered by
 * the shared prayer runner in two styles:
 *   - "steps":  tap-through, one panel at a time (Stations, Way of the Cross)
 *   - "reader": a single calm scroll of the whole prayer (litanies, set prayers)
 *
 * Texts are the traditional public-domain English forms. Users are encouraged
 * to pray slowly and to consult their parish or a Catholic prayer book for any
 * fully proper / approved liturgical texts when desired.
 */
import { BeadStep } from "@/src/rosary";

export type DevotionCategory =
  | "marian"
  | "litany"
  | "stations"
  | "mass"
  | "devotional"
  | "seasonal";

export type Devotion = {
  key: string;
  title: string;
  subtitle: string;
  color: string;
  icon: string;
  duration: string;
  category: DevotionCategory;
  format: "reader" | "steps";
  steps: BeadStep[];
  good_work_for_today: string;
  daily_motto: string;
  note?: string;
};

/* Common building blocks */
const HAIL_MARY = "Hail Mary, full of grace, the Lord is with thee. Blessed art thou amongst women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen.";
const GLORY_BE = "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.";

/* ========================================================================== */
/*                              MARIAN PRAYERS                                */
/* ========================================================================== */

const ANGELUS: BeadStep[] = [
  { label: "The Angelus", prayer: "Prayed morning (6am), noon, and evening (6pm), pausing to recall the Incarnation." },
  { label: "V. / R.", prayer: "V. The Angel of the Lord declared unto Mary,\nR. And she conceived of the Holy Spirit." },
  { label: "Hail Mary", prayer: HAIL_MARY },
  { label: "V. / R.", prayer: "V. Behold the handmaid of the Lord,\nR. Be it done unto me according to thy word." },
  { label: "Hail Mary", prayer: HAIL_MARY },
  { label: "V. / R.", prayer: "V. And the Word was made flesh,\nR. And dwelt among us." },
  { label: "Hail Mary", prayer: HAIL_MARY },
  { label: "V. / R.", prayer: "V. Pray for us, O holy Mother of God,\nR. That we may be made worthy of the promises of Christ." },
  { label: "Let us pray", prayer: "Pour forth, we beseech Thee, O Lord, Thy grace into our hearts, that we to whom the Incarnation of Christ Thy Son was made known by the message of an angel, may by His Passion and Cross be brought to the glory of His Resurrection. Through the same Christ our Lord. Amen." },
];

const REGINA_CAELI: BeadStep[] = [
  { label: "Regina Caeli", prayer: "Prayed in place of the Angelus throughout Eastertide — from Easter Sunday to Pentecost — standing, in joy of the Resurrection." },
  { label: "Regina Caeli", prayer: "Queen of Heaven, rejoice, alleluia.\nFor He whom thou didst merit to bear, alleluia,\nHath risen as He said, alleluia.\nPray for us to God, alleluia." },
  { label: "V. / R.", prayer: "V. Rejoice and be glad, O Virgin Mary, alleluia.\nR. For the Lord is truly risen, alleluia." },
  { label: "Let us pray", prayer: "O God, who through the resurrection of Thy Son, our Lord Jesus Christ, hast vouchsafed to make glad the whole world, grant, we beseech Thee, that through the intercession of the Virgin Mary, His Mother, we may attain the joys of everlasting life. Through the same Christ our Lord. Amen." },
];

const SALVE_REGINA: BeadStep[] = [
  { label: "Salve Regina (Hail Holy Queen)", prayer: "Hail, holy Queen, Mother of Mercy, our life, our sweetness, and our hope. To thee do we cry, poor banished children of Eve. To thee do we send up our sighs, mourning and weeping in this valley of tears. Turn then, most gracious Advocate, thine eyes of mercy toward us, and after this our exile show unto us the blessed fruit of thy womb, Jesus. O clement, O loving, O sweet Virgin Mary." },
  { label: "V. / R.", prayer: "V. Pray for us, O holy Mother of God,\nR. That we may be made worthy of the promises of Christ." },
];

const SUB_TUUM: BeadStep[] = [
  { label: "Sub Tuum Praesidium", prayer: "The oldest known prayer to Our Lady, found on an Egyptian papyrus from around the 3rd century." },
  { label: "We fly to thy protection", prayer: "We fly to thy protection, O holy Mother of God. Despise not our petitions in our necessities, but deliver us always from all dangers, O glorious and blessed Virgin. Amen." },
];

const MEMORARE: BeadStep[] = [
  { label: "The Memorare", prayer: "A beloved prayer of confidence in Our Lady's intercession, made famous by St. Bernard of Clairvaux." },
  { label: "Remember, O most gracious Virgin Mary", prayer: "Remember, O most gracious Virgin Mary, that never was it known that anyone who fled to thy protection, implored thy help, or sought thy intercession was left unaided. Inspired by this confidence, I fly unto thee, O Virgin of virgins, my Mother; to thee do I come, before thee I stand, sinful and sorrowful. O Mother of the Word Incarnate, despise not my petitions, but in thy mercy hear and answer me. Amen." },
];

const MAGNIFICAT: BeadStep[] = [
  { label: "The Magnificat", prayer: "Our Lady's own canticle of praise, spoken at the Visitation (Luke 1:46–55). Prayed each evening at Vespers." },
  { label: "My soul doth magnify the Lord", prayer: "My soul doth magnify the Lord, and my spirit hath rejoiced in God my Saviour. Because He hath regarded the humility of His handmaid; for behold, from henceforth all generations shall call me blessed. Because He that is mighty hath done great things to me, and holy is His name. And His mercy is from generation to generation, to them that fear Him." },
  { label: "He hath shewed might", prayer: "He hath shewed might in His arm; He hath scattered the proud in the conceit of their heart. He hath put down the mighty from their seat, and hath exalted the humble. He hath filled the hungry with good things, and the rich He hath sent empty away. He hath received Israel His servant, being mindful of His mercy. As He spoke to our fathers, to Abraham and to his seed for ever." },
  { label: "Glory Be", prayer: GLORY_BE },
];

/* ========================================================================== */
/*                                 LITANIES                                   */
/* ========================================================================== */

const LITANY_SAINTS: BeadStep[] = [
  { label: "Litany of the Saints", prayer: "The ancient litany imploring the prayers of the whole company of heaven. Prayed at the Easter Vigil, at Baptism, ordinations, and in times of great need. Response unless noted: pray for us." },
  { label: "Kyrie", prayer: "Lord, have mercy. — Lord, have mercy.\nChrist, have mercy. — Christ, have mercy.\nLord, have mercy. — Lord, have mercy." },
  { label: "Our Lady & Angels", prayer: "Holy Mary, Mother of God, — pray for us.\nSaint Michael,\nHoly Angels of God," },
  { label: "Patriarchs & Prophets", prayer: "Saint John the Baptist, — pray for us.\nSaint Joseph,\nSaint Abraham,\nSaint Moses,\nSaint Elijah,\nHoly Patriarchs and Prophets," },
  { label: "Apostles & Disciples", prayer: "Saint Peter and Saint Paul, — pray for us.\nSaint Andrew,\nSaint James,\nSaint John,\nSaint Thomas,\nSaint Matthew,\nAll holy Apostles,\nSaint Luke,\nSaint Mark,\nSaint Barnabas,\nSaint Mary Magdalene,\nAll holy Disciples of the Lord," },
  { label: "Martyrs", prayer: "Saint Stephen, — pray for us.\nSaint Ignatius of Antioch,\nSaint Polycarp,\nSaint Lawrence,\nSaint Cyprian,\nSaint Boniface,\nSaint Thomas Becket,\nSaint John Fisher and Saint Thomas More,\nSaint Paul Miki,\nSaint Charles Lwanga,\nSaint Perpetua and Saint Felicity,\nSaint Agnes,\nSaint Maria Goretti,\nAll holy Martyrs," },
  { label: "Bishops & Doctors", prayer: "Saint Leo and Saint Gregory, — pray for us.\nSaint Ambrose,\nSaint Jerome,\nSaint Augustine,\nSaint Athanasius,\nSaint Basil and Saint Gregory of Nazianzus,\nSaint John Chrysostom,\nSaint Martin,\nSaint Patrick,\nSaint Cyril and Saint Methodius,\nSaint Charles Borromeo,\nSaint Francis de Sales,\nSaint Pius the Tenth," },
  { label: "Priests & Religious", prayer: "Saint Anthony, — pray for us.\nSaint Benedict,\nSaint Bernard,\nSaint Francis and Saint Dominic,\nSaint Thomas Aquinas,\nSaint Ignatius of Loyola,\nSaint Francis Xavier,\nSaint Vincent de Paul,\nSaint John Vianney,\nSaint John Bosco," },
  { label: "Holy Women", prayer: "Saint Catherine of Siena, — pray for us.\nSaint Teresa of Jesus,\nSaint Rose of Lima,\nSaint Thérèse of the Child Jesus,\nSaint Bridget,\nSaint Monica,\nSaint Elizabeth of Hungary,\nAll holy men and women, Saints of God," },
  { label: "Be merciful", prayer: "Response: Lord, deliver us, we pray.\n\nLord, be merciful, — Lord, deliver us, we pray.\nFrom all evil,\nFrom every sin,\nFrom everlasting death,\nBy your Incarnation,\nBy your Death and Resurrection,\nBy the outpouring of the Holy Spirit," },
  { label: "Be merciful to us sinners", prayer: "Response: Lord, we ask you, hear our prayer.\n\nBe merciful to us sinners, — Lord, we ask you, hear our prayer.\nGuide and protect your holy Church,\nKeep the Pope and all the clergy in faithful service to your Church,\nBring all peoples together in trust and peace,\nStrengthen us and keep us in your holy service,\nJesus, Son of the living God," },
  { label: "Christ, hear us / Lamb of God", prayer: "Christ, hear us. — Christ, hear us.\nChrist, graciously hear us. — Christ, graciously hear us.\n\nLamb of God, who takest away the sins of the world, — spare us, O Lord.\nLamb of God, who takest away the sins of the world, — graciously hear us, O Lord.\nLamb of God, who takest away the sins of the world, — have mercy on us." },
];

const LITANY_LORETO: BeadStep[] = [
  { label: "Litany of Loreto", prayer: "The Litany of the Blessed Virgin Mary, named for the shrine of Loreto where it was long sung. Includes the invocations Mother of mercy, Mother of hope, and Solace of migrants added by Pope Francis in 2020. Response unless noted: pray for us." },
  { label: "Kyrie", prayer: "Lord, have mercy. — Christ, have mercy. — Lord, have mercy.\nGod the Father of heaven, — have mercy on us.\nGod the Son, Redeemer of the world, — have mercy on us.\nGod the Holy Spirit, — have mercy on us.\nHoly Trinity, one God, — have mercy on us." },
  { label: "Holy Mary", prayer: "Holy Mary, — pray for us.\nHoly Mother of God,\nHoly Virgin of virgins,\nMother of Christ,\nMother of the Church,\nMother of mercy,\nMother of divine grace,\nMother of hope,\nMother most pure,\nMother most chaste,\nMother inviolate,\nMother undefiled,\nMother most amiable,\nMother most admirable,\nMother of good counsel,\nMother of our Creator,\nMother of our Saviour." },
  { label: "Virgin most...", prayer: "Virgin most prudent, — pray for us.\nVirgin most venerable,\nVirgin most renowned,\nVirgin most powerful,\nVirgin most merciful,\nVirgin most faithful." },
  { label: "Mirror & Seat", prayer: "Mirror of justice, — pray for us.\nSeat of wisdom,\nCause of our joy,\nSpiritual vessel,\nVessel of honour,\nSingular vessel of devotion,\nMystical rose,\nTower of David,\nTower of ivory,\nHouse of gold,\nArk of the covenant,\nGate of heaven,\nMorning star." },
  { label: "Health & Refuge", prayer: "Health of the sick, — pray for us.\nRefuge of sinners,\nSolace of migrants,\nComforter of the afflicted,\nHelp of Christians." },
  { label: "Queen", prayer: "Queen of Angels, — pray for us.\nQueen of Patriarchs,\nQueen of Prophets,\nQueen of Apostles,\nQueen of Martyrs,\nQueen of Confessors,\nQueen of Virgins,\nQueen of all Saints,\nQueen conceived without original sin,\nQueen assumed into heaven,\nQueen of the most holy Rosary,\nQueen of families,\nQueen of peace." },
  { label: "Lamb of God", prayer: "Lamb of God, who takest away the sins of the world, — spare us, O Lord.\nLamb of God, who takest away the sins of the world, — graciously hear us, O Lord.\nLamb of God, who takest away the sins of the world, — have mercy on us.\n\nV. Pray for us, O holy Mother of God.\nR. That we may be made worthy of the promises of Christ." },
];

const LITANY_SACRED_HEART: BeadStep[] = [
  { label: "Litany of the Sacred Heart of Jesus", prayer: "A litany of the Heart of Christ, burning with love for us. Response unless noted: have mercy on us." },
  { label: "Kyrie", prayer: "Lord, have mercy. — Christ, have mercy. — Lord, have mercy.\nGod the Father of heaven, — have mercy on us.\nGod the Son, Redeemer of the world, — have mercy on us.\nGod the Holy Spirit, — have mercy on us.\nHoly Trinity, one God, — have mercy on us." },
  { label: "Heart of Jesus...", prayer: "Heart of Jesus, Son of the Eternal Father, — have mercy on us.\nHeart of Jesus, formed by the Holy Spirit in the womb of the Virgin Mother,\nHeart of Jesus, substantially united to the Word of God,\nHeart of Jesus, of infinite majesty,\nHeart of Jesus, holy temple of God,\nHeart of Jesus, tabernacle of the Most High,\nHeart of Jesus, house of God and gate of heaven,\nHeart of Jesus, burning furnace of charity,\nHeart of Jesus, abode of justice and love,\nHeart of Jesus, full of goodness and love." },
  { label: "Heart of Jesus, fountain...", prayer: "Heart of Jesus, abyss of all virtues, — have mercy on us.\nHeart of Jesus, worthy of all praise,\nHeart of Jesus, king and center of all hearts,\nHeart of Jesus, in whom are all the treasures of wisdom and knowledge,\nHeart of Jesus, in whom dwells the fullness of divinity,\nHeart of Jesus, in whom the Father is well pleased,\nHeart of Jesus, of whose fullness we have all received,\nHeart of Jesus, desire of the everlasting hills,\nHeart of Jesus, patient and most merciful,\nHeart of Jesus, enriching all who invoke Thee,\nHeart of Jesus, fountain of life and holiness." },
  { label: "Heart of Jesus, our peace", prayer: "Heart of Jesus, propitiation for our sins, — have mercy on us.\nHeart of Jesus, loaded down with opprobrium,\nHeart of Jesus, bruised for our offenses,\nHeart of Jesus, obedient unto death,\nHeart of Jesus, pierced with a lance,\nHeart of Jesus, source of all consolation,\nHeart of Jesus, our life and resurrection,\nHeart of Jesus, our peace and reconciliation,\nHeart of Jesus, victim for our sins,\nHeart of Jesus, salvation of those who hope in Thee,\nHeart of Jesus, hope of those who die in Thee,\nHeart of Jesus, delight of all the saints." },
  { label: "Lamb of God", prayer: "Lamb of God, who takest away the sins of the world, — spare us, O Lord.\nLamb of God, who takest away the sins of the world, — graciously hear us, O Lord.\nLamb of God, who takest away the sins of the world, — have mercy on us.\n\nV. Jesus, meek and humble of heart,\nR. Make our hearts like unto Thine." },
];

const LITANY_ST_JOSEPH: BeadStep[] = [
  { label: "Litany of St. Joseph", prayer: "Approved by Pope St. Pius X (1909), with invocations added by Pope Francis. Response unless noted: pray for us." },
  { label: "Kyrie", prayer: "Lord, have mercy. — Christ, have mercy. — Lord, have mercy.\nGod the Father of heaven, — have mercy on us.\nGod the Son, Redeemer of the world, — have mercy on us.\nGod the Holy Spirit, — have mercy on us.\nHoly Trinity, one God, — have mercy on us.\nHoly Mary, — pray for us." },
  { label: "Saint Joseph...", prayer: "Saint Joseph, — pray for us.\nRenowned offspring of David,\nLight of Patriarchs,\nSpouse of the Mother of God,\nGuardian of the Redeemer,\nChaste guardian of the Virgin,\nFoster father of the Son of God,\nDiligent protector of Christ,\nServant of Christ,\nMinister of salvation,\nHead of the Holy Family." },
  { label: "Joseph most...", prayer: "Joseph most just, — pray for us.\nJoseph most chaste,\nJoseph most prudent,\nJoseph most strong,\nJoseph most obedient,\nJoseph most faithful,\nMirror of patience,\nLover of poverty,\nModel of workmen,\nGlory of home life,\nGuardian of virgins,\nPillar of families,\nSupport in difficulties,\nSolace of the wretched,\nHope of the sick,\nPatron of exiles,\nPatron of the afflicted,\nPatron of the poor,\nPatron of the dying,\nTerror of demons,\nProtector of Holy Church." },
  { label: "Lamb of God", prayer: "Lamb of God, who takest away the sins of the world, — spare us, O Lord.\nLamb of God, who takest away the sins of the world, — graciously hear us, O Lord.\nLamb of God, who takest away the sins of the world, — have mercy on us.\n\nV. He made him the lord of His household,\nR. And prince over all His possessions." },
];

const LITANY_HUMILITY: BeadStep[] = [
  { label: "Litany of Humility", prayer: "Composed by Rafael Cardinal Merry del Val (1865–1930), Secretary of State to Pope St. Pius X. A bracing school of humility." },
  { label: "O Jesus, meek and humble of heart", prayer: "O Jesus, meek and humble of heart, — Hear me." },
  { label: "Deliver me, O Jesus", prayer: "From the desire of being esteemed, — Deliver me, O Jesus.\nFrom the desire of being loved,\nFrom the desire of being extolled,\nFrom the desire of being honored,\nFrom the desire of being praised,\nFrom the desire of being preferred to others,\nFrom the desire of being consulted,\nFrom the desire of being approved." },
  { label: "Deliver me, O Jesus", prayer: "From the fear of being humiliated, — Deliver me, O Jesus.\nFrom the fear of being despised,\nFrom the fear of suffering rebukes,\nFrom the fear of being calumniated,\nFrom the fear of being forgotten,\nFrom the fear of being ridiculed,\nFrom the fear of being wronged,\nFrom the fear of being suspected." },
  { label: "Jesus, grant me the grace to desire it", prayer: "That others may be loved more than I, — Jesus, grant me the grace to desire it.\nThat others may be esteemed more than I,\nThat, in the opinion of the world, others may increase and I may decrease,\nThat others may be chosen and I set aside,\nThat others may be praised and I unnoticed,\nThat others may be preferred to me in everything,\nThat others may become holier than I, provided that I may become as holy as I should. Amen." },
];

/* ========================================================================== */
/*                          STATIONS OF THE CROSS                             */
/* ========================================================================== */

const STATION_TITLES = [
  "Jesus is condemned to death",
  "Jesus takes up His Cross",
  "Jesus falls the first time",
  "Jesus meets His sorrowful Mother",
  "Simon of Cyrene helps carry the Cross",
  "Veronica wipes the face of Jesus",
  "Jesus falls the second time",
  "Jesus meets the women of Jerusalem",
  "Jesus falls the third time",
  "Jesus is stripped of His garments",
  "Jesus is nailed to the Cross",
  "Jesus dies on the Cross",
  "Jesus is taken down from the Cross",
  "Jesus is laid in the tomb",
];

const STATION_TRADITIONAL_MEDITATIONS = [
  "Pilate condemns the innocent Lamb. — Lord, when I am judged unjustly, give me Your silence and peace.",
  "He embraces the wood that will save us. — Help me take up my own cross today without complaint.",
  "Beneath the weight, He falls. — When I fall through weakness, teach me to rise again.",
  "Mother and Son meet in love and sorrow. — Mary, stay near me in my own sorrows.",
  "Simon is pressed into service. — Make me willing to carry the burdens of others.",
  "Veronica answers love with a small kindness. — Let me do the small brave good before me.",
  "He falls again, exhausted. — When discouragement returns, do not let me give up.",
  "He comforts the weeping women. — Turn my self-pity into compassion for others.",
  "A third time He falls. — In my repeated failings, keep me from despair.",
  "He is stripped and humiliated. — Strip from me my vanity and pride.",
  "The nails pierce His hands and feet. — Nail my will to Yours, O Lord.",
  "He gives up His spirit for us. — 'Father, into Your hands I commend my spirit.'",
  "He rests in His Mother's arms. — Receive the dead, and console the grieving.",
  "He is buried, and we wait in hope. — In every tomb of my life, prepare the resurrection.",
];

const STATION_SCRIPTURAL = [
  { title: "Jesus in the Garden of Gethsemane", text: "'Father, if it be possible, let this cup pass from me; yet not my will, but Thine be done.' (Lk 22:42)" },
  { title: "Jesus is betrayed by Judas and arrested", text: "'Judas, do you betray the Son of Man with a kiss?' (Lk 22:48)" },
  { title: "Jesus is condemned by the Sanhedrin", text: "'Are you the Son of God, then?' And He said, 'You say that I am.' (Lk 22:70)" },
  { title: "Jesus is denied by Peter", text: "And the Lord turned and looked at Peter… and he went out and wept bitterly. (Lk 22:61–62)" },
  { title: "Jesus is judged by Pilate", text: "'I find no crime in this man.' Yet Pilate handed Him over. (Lk 23:4, 24)" },
  { title: "Jesus is scourged and crowned with thorns", text: "They twisted a crown of thorns and put it on His head. (Mt 27:29)" },
  { title: "Jesus takes up His Cross", text: "Bearing His own cross, He went out to the place called Golgotha. (Jn 19:17)" },
  { title: "Jesus is helped by Simon of Cyrene", text: "They laid the cross on him, to carry it behind Jesus. (Lk 23:26)" },
  { title: "Jesus meets the women of Jerusalem", text: "'Daughters of Jerusalem, do not weep for me, but weep for yourselves.' (Lk 23:28)" },
  { title: "Jesus is crucified", text: "'Father, forgive them, for they know not what they do.' (Lk 23:34)" },
  { title: "Jesus promises His kingdom to the good thief", text: "'Truly, I say to you, today you will be with me in Paradise.' (Lk 23:43)" },
  { title: "Jesus speaks to His Mother and the disciple", text: "'Woman, behold your son.' … 'Behold your mother.' (Jn 19:26–27)" },
  { title: "Jesus dies on the Cross", text: "'Father, into Your hands I commend my spirit.' And He breathed His last. (Lk 23:46)" },
  { title: "Jesus is laid in the tomb", text: "Joseph wrapped Him in a linen shroud and laid Him in a tomb. (Lk 23:53)" },
];

const LIGUORI_MEDITATIONS = [
  "I love Thee, Jesus my love, above all things; I repent with my whole heart of having offended Thee. Never permit me to separate myself from Thee again.",
  "My most beloved Jesus, I embrace all the tribulations Thou hast destined for me until death. I beseech Thee, by the merits of the pain Thou didst suffer in carrying Thy Cross, to give me the help to carry mine with perfect patience.",
  "My Jesus, it is not the weight of the Cross, but my sins, which have made Thee suffer so much. By the merits of this first fall, deliver me from the misfortune of falling into mortal sin.",
  "My most loving Jesus, by the sorrow Thou didst experience in this meeting, grant me the grace of a truly devoted love for Thy most holy Mother.",
  "My beloved Jesus, I will not refuse the Cross as the Cyrenian did; I accept it, I embrace it. I accept in particular the death Thou hast destined for me.",
  "My beloved Jesus, Thy face was beautiful before, but disfigured by sin. Give me strength to seek Thee, that the thought of Thy Passion may ever remain impressed upon my heart.",
  "My gentle Jesus, how many times Thou hast pardoned me, and how many times I have fallen again. By the merits of this new fall, give me grace to persevere in Thy love until death.",
  "My Jesus, laden with sorrows, I weep for the offenses I have committed against Thee, for the pains they have deserved, and still more for the displeasure they have caused Thee.",
  "My outraged Jesus, by the merits of this third fall, give me strength to overcome all human respect and all my wicked passions which have led me to despise Thy friendship.",
  "My innocent Jesus, by the merits of the torment Thou didst feel, help me to strip myself of all affection for the things of earth, that I may place all my love in Thee.",
  "My Jesus, nailed to the Cross for me, nail my heart to Thy feet, that it may ever remain there, to love Thee and never to leave Thee again.",
  "My dying Jesus, I kiss devoutly the Cross on which Thou didst die for love of me. I deserved by my sins to die a miserable death; but Thy death is my hope.",
  "O Mother of Sorrows, for the love of this Son, accept me for thy servant and pray to Him for me. And Thou, my Redeemer, since Thou hast died for me, permit me to love Thee.",
  "My buried Jesus, I kiss the stone that encloses Thee. But Thou didst rise again the third day. By Thy Resurrection, oblige me to rise glorious with Thee at the last day, to be ever united with Thee in heaven.",
];

function buildStations(meditations: string[], scripturalTitles?: { title: string; text: string }[]): BeadStep[] {
  const steps: BeadStep[] = [];
  steps.push({ label: "Opening Prayer", prayer: "Act of Contrition: O my God, I am heartily sorry for having offended Thee. As I make these Stations, let me walk with You the road of Your Passion. At each station we pray: We adore Thee, O Christ, and we bless Thee, because by Thy holy Cross Thou hast redeemed the world." });
  for (let i = 0; i < 14; i++) {
    const num = i + 1;
    const title = scripturalTitles ? scripturalTitles[i].title : STATION_TITLES[i];
    const body = scripturalTitles ? scripturalTitles[i].text : meditations[i];
    const med = scripturalTitles ? meditations[i] : "";
    steps.push({
      label: `Station ${num} — ${title}`,
      prayer: `V. We adore Thee, O Christ, and we bless Thee.\nR. Because by Thy holy Cross Thou hast redeemed the world.\n\n${body}${med ? "\n\n" + med : ""}`,
    });
  }
  steps.push({ label: "Closing Prayer", prayer: "Lord Jesus, by these Stations I have walked with You to Calvary. Keep ever before my eyes the love that bore the Cross for me, and bring me at last to the joy of Your Resurrection. Our Father… Hail Mary… Glory Be… Amen." });
  return steps;
}

/* ========================================================================== */
/*                          MASS & COMMUNION                                  */
/* ========================================================================== */

const BEFORE_MASS: BeadStep[] = [
  { label: "Prayer Before Mass — St. Thomas Aquinas", prayer: "Almighty and everlasting God, behold I come to the Sacrament of Thine only-begotten Son, our Lord Jesus Christ. As one sick I come to the Physician of life; as unclean, to the Fountain of mercy; as blind, to the Light of eternal splendor; as poor and needy, to the Lord of heaven and earth." },
  { label: "Implore His mercy", prayer: "Therefore I implore the abundance of Thy measureless bounty: graciously to heal my sickness, to wash away my defilement, to enlighten my blindness, to enrich my poverty, and to clothe my nakedness; that I may receive the Bread of Angels, the King of kings, the Lord of lords, with such reverence and humility, such contrition and devotion, such purity and faith, such purpose and intention, as may profit my soul's salvation. Amen." },
];

const AFTER_MASS: BeadStep[] = [
  { label: "Thanksgiving After Mass — St. Thomas Aquinas", prayer: "I give Thee thanks, O holy Lord, almighty Father, eternal God, who hast vouchsafed, not for any merit of mine, but out of the condescension of Thy goodness, to feed me, a sinner and Thine unworthy servant, with the precious Body and Blood of Thy Son, our Lord Jesus Christ." },
  { label: "I pray", prayer: "I pray that this Holy Communion may not be to me an offense to be punished, but a saving plea to forgiveness. May it be to me the armor of faith and the shield of good will. May it root out from my heart all vice; may it utterly subdue my evil passions; may it increase charity and patience, humility and obedience; may it be my firm defense against the snares of all my enemies, visible and invisible; the perfect quieting of all my impulses, fleshly and spiritual; my firm cleaving to Thee, the one true God; and a pledge of a blessed end. Amen." },
];

const BEFORE_COMMUNION: BeadStep[] = [
  { label: "Before Communion", prayer: "Lord Jesus, I am not worthy that You should come under my roof, but only say the word and my soul shall be healed. Come to me now in this most holy Sacrament; cleanse my heart and make it a fitting dwelling for You." },
  { label: "Act of Faith & Desire", prayer: "My Lord and my God, I firmly believe that You are truly present in the Most Holy Eucharist — Body, Blood, Soul, and Divinity. I love You above all things, and I desire to receive You into my soul. Since I cannot now receive You sacramentally, come at least spiritually into my heart. I embrace You as if You were already there, and unite myself wholly to You. Never permit me to be separated from You. Amen." },
];

const AFTER_COMMUNION: BeadStep[] = [
  { label: "Anima Christi", prayer: "Soul of Christ, sanctify me.\nBody of Christ, save me.\nBlood of Christ, inebriate me.\nWater from the side of Christ, wash me.\nPassion of Christ, strengthen me.\nO good Jesus, hear me.\nWithin Thy wounds hide me.\nSuffer me not to be separated from Thee.\nFrom the malignant enemy defend me.\nIn the hour of my death call me,\nand bid me come unto Thee,\nthat with Thy saints I may praise Thee\nfor ever and ever. Amen." },
  { label: "Thanksgiving", prayer: "Jesus, You have come to me; I adore You within my heart. I thank You for so great a gift. Take my memory, my understanding, and my whole will. All that I have and possess You have given me; to You I return it. Give me only Your love and Your grace; with these I am rich enough, and ask for nothing more. Amen." },
  { label: "Prayer Before a Crucifix", prayer: "Behold, O good and most sweet Jesus, I cast myself upon my knees in Thy sight, and with the most fervent desire of my soul I pray that Thou wouldst impress upon my heart lively sentiments of faith, hope, and charity, true contrition for my sins, and a firm purpose of amendment, while with deep affection and grief of soul I ponder within myself Thy five most precious wounds. Amen." },
];

/* ========================================================================== */
/*                          DEVOTIONS & ACTS                                  */
/* ========================================================================== */

const ST_MICHAEL_PRAYER: BeadStep[] = [
  { label: "Prayer to St. Michael the Archangel", prayer: "Composed by Pope Leo XIII (1886). Long prayed for protection against evil." },
  { label: "St. Michael the Archangel", prayer: "St. Michael the Archangel, defend us in battle. Be our protection against the wickedness and snares of the devil. May God rebuke him, we humbly pray; and do thou, O Prince of the heavenly host, by the power of God, cast into hell Satan and all the evil spirits who prowl about the world seeking the ruin of souls. Amen." },
];

const MORNING_OFFERING: BeadStep[] = [
  { label: "Morning Offering", prayer: "O Jesus, through the Immaculate Heart of Mary, I offer You my prayers, works, joys, and sufferings of this day, in union with the Holy Sacrifice of the Mass throughout the world. I offer them for all the intentions of Your Sacred Heart: the salvation of souls, reparation for sin, and the reunion of all Christians. I offer them for the intentions of our Holy Father this month. Amen." },
];

const ACTS_FHC: BeadStep[] = [
  { label: "Act of Faith", prayer: "O my God, I firmly believe that You are one God in three divine Persons, Father, Son, and Holy Spirit. I believe that Your divine Son became man and died for our sins, and that He will come to judge the living and the dead. I believe these and all the truths which the holy Catholic Church teaches, because You have revealed them, who can neither deceive nor be deceived. Amen." },
  { label: "Act of Hope", prayer: "O my God, relying on Your almighty power and infinite mercy and promises, I hope to obtain pardon of my sins, the help of Your grace, and life everlasting, through the merits of Jesus Christ, my Lord and Redeemer. Amen." },
  { label: "Act of Charity", prayer: "O my God, I love You above all things, with my whole heart and soul, because You are all-good and worthy of all love. I love my neighbor as myself for the love of You. I forgive all who have injured me, and ask pardon of all whom I have injured. Amen." },
];

const TE_DEUM: BeadStep[] = [
  { label: "Te Deum", prayer: "An ancient hymn of thanksgiving and praise (4th century), sung on great solemnities and in gratitude for blessings received." },
  { label: "We praise Thee, O God", prayer: "We praise Thee, O God; we acknowledge Thee to be the Lord. All the earth doth worship Thee, the Father everlasting. To Thee all Angels cry aloud, the Heavens and all the Powers therein. To Thee Cherubim and Seraphim continually do cry: Holy, Holy, Holy, Lord God of Sabaoth; heaven and earth are full of the majesty of Thy glory." },
  { label: "The glorious company", prayer: "The glorious company of the Apostles praise Thee. The goodly fellowship of the Prophets praise Thee. The white-robed army of Martyrs praise Thee. The holy Church throughout all the world doth acknowledge Thee: the Father of an infinite majesty; Thine adorable, true, and only Son; also the Holy Spirit, the Comforter." },
  { label: "Thou art the King of glory", prayer: "Thou art the King of glory, O Christ. Thou art the everlasting Son of the Father. When Thou tookest upon Thee to deliver man, Thou didst not abhor the Virgin's womb. When Thou hadst overcome the sharpness of death, Thou didst open the Kingdom of Heaven to all believers. We believe that Thou shalt come to be our Judge. We therefore pray Thee, help Thy servants, whom Thou hast redeemed with Thy precious Blood. O Lord, in Thee have I trusted; let me never be confounded. Amen." },
];

const ST_PATRICK: BeadStep[] = [
  { label: "St. Patrick's Breastplate (Lorica)", prayer: "An ancient Irish prayer of protection attributed to St. Patrick (5th century), binding oneself to the strength of the Triune God." },
  { label: "I bind unto myself today", prayer: "I bind unto myself today the strong Name of the Trinity, by invocation of the same, the Three in One and One in Three. I bind this day to me forever, by power of faith, Christ's Incarnation; His baptism in the Jordan river; His death on Cross for my salvation; His bursting from the spiced tomb; His riding up the heavenly way; His coming at the day of doom: I bind unto myself today." },
  { label: "Christ be with me", prayer: "Christ be with me, Christ within me, Christ behind me, Christ before me, Christ beside me, Christ to win me, Christ to comfort and restore me. Christ beneath me, Christ above me, Christ in quiet, Christ in danger, Christ in hearts of all that love me, Christ in mouth of friend and stranger." },
  { label: "Closing", prayer: "I bind unto myself the Name, the strong Name of the Trinity, by invocation of the same, the Three in One and One in Three. Of whom all nature hath creation; eternal Father, Spirit, Word: praise to the Lord of my salvation, salvation is of Christ the Lord. Amen." },
];

const LEONINE_PRAYERS: BeadStep[] = [
  { label: "The Leonine Prayers", prayer: "The prayers ordered by Pope Leo XIII to be said after Low Mass (1884–1965), for the freedom and exaltation of the Church. Still a worthy private devotion." },
  { label: "Three Hail Marys", prayer: HAIL_MARY + "\n\n(Pray the Hail Mary three times.)" },
  { label: "Hail Holy Queen", prayer: "Hail, holy Queen, Mother of Mercy, our life, our sweetness, and our hope. To thee do we cry, poor banished children of Eve. To thee do we send up our sighs, mourning and weeping in this valley of tears. Turn then, most gracious Advocate, thine eyes of mercy toward us, and after this our exile show unto us the blessed fruit of thy womb, Jesus. O clement, O loving, O sweet Virgin Mary.\n\nV. Pray for us, O holy Mother of God. R. That we may be made worthy of the promises of Christ." },
  { label: "Collect", prayer: "O God, our refuge and our strength, look down with mercy upon Thy people who cry to Thee; and by the intercession of the glorious and Immaculate Virgin Mary, Mother of God, of St. Joseph her Spouse, of Thy blessed Apostles Peter and Paul, and of all the Saints, mercifully and graciously hear the prayers which we pour forth for the conversion of sinners and for the liberty and exaltation of Holy Mother Church. Through the same Christ our Lord. Amen." },
  { label: "Prayer to St. Michael", prayer: "St. Michael the Archangel, defend us in battle. Be our protection against the wickedness and snares of the devil. May God rebuke him, we humbly pray; and do thou, O Prince of the heavenly host, by the power of God, cast into hell Satan and all the evil spirits who prowl about the world seeking the ruin of souls. Amen." },
  { label: "Sacred Heart", prayer: "Most Sacred Heart of Jesus, have mercy on us. (three times)" },
];

const DELIVERANCE_PRAYERS: BeadStep[] = [
  { label: "A Note on Exorcism", prayer: "The solemn Rite of Exorcism is reserved to a priest with the express permission of his bishop. The prayers below are private deliverance prayers, approved for use by the lay faithful, asking God's protection from evil — not the formal Rite. In any spiritual struggle, seek the Sacraments and the counsel of a faithful priest." },
  { label: "Prayer for Protection", prayer: "Heavenly Father, by the precious Blood of Your Son Jesus Christ, protect me, my family, and all I love this day. Send Your holy angels to guard us, and let nothing of the evil one have any power over us. I claim the victory of the Cross over every work of darkness." },
  { label: "Prayer to St. Michael", prayer: "St. Michael the Archangel, defend us in battle. Be our protection against the wickedness and snares of the devil. May God rebuke him, we humbly pray; and do thou, O Prince of the heavenly host, by the power of God, cast into hell Satan and all the evil spirits who prowl about the world seeking the ruin of souls. Amen." },
  { label: "In the Name of Jesus", prayer: "In the Name of Jesus Christ, my Lord and Savior, and under the protection of the Blessed Virgin Mary, I renounce every work of the evil one in my life. Lord Jesus, You are my refuge; cover me in Your Precious Blood, and let Your peace reign in my heart. Amen." },
];

const BINDING_HOLY_SPIRIT: BeadStep[] = [
  { label: "Binding Prayer to the Holy Spirit", prayer: "A prayer of surrender, asking the Holy Spirit to take hold of every part of us and bind us to the will of God." },
  { label: "Come, Holy Spirit", prayer: "Come, Holy Spirit, fill the hearts of Thy faithful and kindle in them the fire of Thy love. Send forth Thy Spirit and they shall be created. And Thou shalt renew the face of the earth." },
  { label: "Bind me to God", prayer: "Holy Spirit, take hold of my mind and my thoughts; my heart and my desires; my will and my choices; my words and my works. Bind them fast to the will of the Father. Where I am weak, be my strength; where I am divided, make me whole; where I wander, draw me back. Let nothing in me be left ungoverned by Your grace, that I may belong wholly to Christ. Amen." },
  { label: "Let us pray", prayer: "O God, who didst instruct the hearts of the faithful by the light of the Holy Spirit, grant us in the same Spirit to be truly wise, and ever to rejoice in His consolation. Through Christ our Lord. Amen." },
];

/* ========================================================================== */
/*                                 SEASONAL                                   */
/* ========================================================================== */

const SEASONAL_PRAYERS: BeadStep[] = [
  { label: "Prayers for the Liturgical Seasons", prayer: "Brief prayers to pray with the rhythm of the Church's year. Pray the one that fits the present season." },
  { label: "Advent — Watching in Hope", prayer: "O come, O come, Emmanuel. Lord, in this season of waiting, make my heart ready for Your coming. Stir up Your power and come, that I may welcome the Light that the darkness cannot overcome. Maranatha — Come, Lord Jesus. Amen." },
  { label: "Christmas — The Word Made Flesh", prayer: "O Word made flesh, who didst not abhor the Virgin's womb, be born anew in my heart this day. Let the wonder of Bethlehem make me humble, grateful, and full of joy. Glory to God in the highest. Amen." },
  { label: "Lent — Return to the Lord", prayer: "Merciful God, in these forty days create in me a clean heart. Through prayer, fasting, and almsgiving, draw me back to You. Mark me with the sign of the Cross, that I may die to sin and live for You. Amen." },
  { label: "Easter — Christ is Risen", prayer: "Lord Jesus, risen from the dead, fill me with the joy of Your victory. Raise me from every tomb of sin and fear, and let me walk in newness of life. This is the day the Lord has made. Alleluia! Amen." },
  { label: "Ordinary Time — Walking with Christ", prayer: "Lord, in the ordinary hours of these days, teach me to find You — in my work, my rest, and the people You set before me. Make the small faithfulness of today a path to holiness. Amen." },
];

const FEAST_DAY_PRAYERS: BeadStep[] = [
  { label: "Feast Day Prayers", prayer: "Short prayers for the great solemnities and feasts of the Lord, Our Lady, and the saints. Pray the one nearest the day." },
  { label: "The Most Holy Trinity", prayer: "Glory be to the Father, and to the Son, and to the Holy Spirit. O Triune God, one in three Persons, draw me into the life of Your love, that I may know You here and behold You forever. Amen." },
  { label: "Corpus Christi — The Body of Christ", prayer: "O Sacrament most holy, O Sacrament divine, all praise and all thanksgiving be every moment Thine. O Lord, who in this wonderful Sacrament hast left us a memorial of Thy Passion, grant us so to venerate the sacred mysteries of Thy Body and Blood, that we may ever feel within us the fruit of Thy redemption. Amen." },
  { label: "The Sacred Heart of Jesus", prayer: "O most Sacred Heart of Jesus, fountain of every blessing, I adore You, I love You, and with lively sorrow for my sins I offer You this poor heart of mine. Most Sacred Heart of Jesus, I trust in You. Amen." },
  { label: "The Assumption of Our Lady", prayer: "O glorious Mother, assumed body and soul into heaven, you are the firstfruit of Christ's victory. Lead me along the way you have gone before, that where you are in glory, I too may one day come. Amen." },
  { label: "All Saints", prayer: "O God, the glory of Your Saints, who has brought us to honor all the holy ones in one celebration: grant us, through their manifold intercession, the abundance of Your mercy. Amen." },
];

const FIRST_FRIDAY_SATURDAY: BeadStep[] = [
  { label: "First Friday & First Saturday Devotions", prayer: "Two devotions of reparation: the Sacred Heart of Jesus (First Fridays) and the Immaculate Heart of Mary (First Saturdays), with the great promises attached to them." },
  { label: "First Fridays — Sacred Heart", prayer: "The Nine First Fridays: to receive Holy Communion on the first Friday of nine consecutive months, in reparation to the Sacred Heart. Our Lord promised through St. Margaret Mary the grace of final perseverance to those who keep this devotion." },
  { label: "Act of Reparation to the Sacred Heart", prayer: "Most sweet Jesus, whose overflowing charity for men is requited by so much forgetfulness, negligence, and contempt, behold us prostrate before You, eager to repair by a special act of homage the cruel indifference and injuries to Your loving Heart. Most Sacred Heart of Jesus, I trust in You. Amen." },
  { label: "First Saturdays — Immaculate Heart", prayer: "The Five First Saturdays, requested by Our Lady at Fatima: Confession, Holy Communion, the Rosary, and fifteen minutes' meditation on the mysteries, on the first Saturday of five consecutive months, in reparation to her Immaculate Heart." },
  { label: "Act of Reparation to the Immaculate Heart", prayer: "Immaculate Heart of Mary, pierced by the sword of sorrow and wounded by the sins of your children, I offer you my prayers and sacrifices in reparation for all the offenses against your Immaculate Heart. Lead me to your Son, and keep me ever faithful. Amen." },
];

/* ========================================================================== */
/*                     ADDITIONAL DEVOTIONS & PRAYERS                          */
/* ========================================================================== */

const TO_YOU_BLESSED_JOSEPH: BeadStep[] = [
  { label: "To you, O blessed Joseph", prayer: "The Leonine prayer to St. Joseph (Ad te, beate Ioseph), given to the Church by Pope Leo XIII in 1889 and prayed especially in October after the Rosary." },
  { label: "We fly to you", prayer: "To you, O blessed Joseph, do we come in our tribulation, and having implored the help of your most holy Spouse, we confidently invoke your patronage also. By that charity which united you to the Immaculate Virgin Mother of God, and by the paternal love with which you embraced the Child Jesus, we beseech you and we humbly pray that you would look graciously upon the inheritance which Jesus Christ has purchased by His Blood, and with your power and strength aid us in our necessities." },
  { label: "Guard the family of Jesus", prayer: "O most watchful Guardian of the Holy Family, defend the chosen children of Jesus Christ; O most loving father, ward off from us every contagion of error and corrupting influence; O our most mighty protector, be propitious to us and from heaven assist us in our struggle with the power of darkness." },
  { label: "Deliver us", prayer: "And as once you rescued the Child Jesus from deadly peril, so now protect God's holy Church from the snares of the enemy and from all adversity; shield, too, each one of us by your constant protection, so that, supported by your example and your aid, we may be able to live piously, to die holily, and to obtain eternal happiness in heaven. Amen." },
];

const ANGEL_OF_GOD: BeadStep[] = [
  { label: "The Angel of God", prayer: "The traditional morning and evening prayer to one's Guardian Angel (Angele Dei), beloved by children and saints alike." },
  { label: "Angel of God", prayer: "Angel of God, my guardian dear,\nto whom God's love commits me here,\never this day (or night) be at my side,\nto light and guard, to rule and guide. Amen." },
  { label: "A word of thanks", prayer: "Thank you, dear Angel, for watching over me. Keep me close to God this day, warn me of danger, and lead me at last to heaven, where I may see with you the face of our Father. Amen." },
];

const LITANY_VIRGIN_MARTYRS: BeadStep[] = [
  { label: "Litany of the Virgin Martyrs", prayer: "A litany honoring the holy virgins who gave their lives rather than betray their love for Christ. Response unless noted: pray for us." },
  { label: "Kyrie", prayer: "Lord, have mercy. — Christ, have mercy. — Lord, have mercy.\nChrist, hear us. — Christ, graciously hear us.\nHoly Mary, Queen of Virgins, — pray for us." },
  { label: "Holy Virgin Martyrs", prayer: "Saint Agnes, — pray for us.\nSaint Cecilia,\nSaint Lucy,\nSaint Agatha,\nSaint Barbara,\nSaint Catherine of Alexandria,\nSaint Dorothy,\nSaint Apollonia,\nSaint Anastasia,\nSaint Philomena,\nSaint Maria Goretti." },
  { label: "You who kept the faith", prayer: "All you holy virgins and martyrs, who loved Christ above your own lives, — pray for us.\nYou who kept your lamps burning,\nYou who followed the Lamb whithersoever He goeth,\nYou who overcame by the Blood of the Lamb." },
  { label: "Let us pray", prayer: "O God, who among the other miracles of Your power have given the victory of martyrdom even to tender women, grant, we beseech You, that we who keep the heavenly birthday of Your holy virgin martyrs may, by their example, come to You. Through Christ our Lord. Amen." },
];

const ACT_OF_REPARATION: BeadStep[] = [
  { label: "Act of Reparation to the Sacred Heart", prayer: "The prayer of reparation (Reparatory Prayer) prescribed by Pope Pius XI for the Feast of the Sacred Heart, to console the Heart of Jesus for the coldness and sins of the world." },
  { label: "Most sweet Jesus", prayer: "Most sweet Jesus, whose overflowing charity for men is requited by so much forgetfulness, negligence, and contempt, behold us prostrate before You, eager to repair by a special act of homage the cruel indifference and injuries to which Your loving Heart is everywhere subject." },
  { label: "We make amends", prayer: "Mindful, alas, that we ourselves have had a share in such great indignities, which we now deplore from the depths of our hearts, we humbly ask Your pardon and declare our readiness to atone by voluntary expiation, not only for our own personal offenses, but also for the sins of those who, straying far from the path of salvation, refuse in their obstinate infidelity to follow You." },
  { label: "Reparation", prayer: "Would that we could wash away such abominations with our own blood! Meanwhile, to make amends for the outrages offered to the divine honor, we offer You the same reparation which You once offered Your Father on the Cross, joined to the offerings of Your Virgin Mother and all the Saints and of the faithful. We sincerely promise to make reparation, as far as we can, for former negligence, by lively faith, holy conduct, and perfect obedience to the law of the Gospel. Amen." },
];

const APOSTLES_CREED: BeadStep[] = [
  { label: "The Apostles' Creed", prayer: "The most ancient baptismal creed of the Church of Rome, a summary of the apostolic faith, prayed at the start of the Rosary and in the Divine Office." },
  { label: "I believe in God", prayer: "I believe in God, the Father almighty, Creator of heaven and earth, and in Jesus Christ, His only Son, our Lord, who was conceived by the Holy Spirit, born of the Virgin Mary, suffered under Pontius Pilate, was crucified, died and was buried; He descended into hell; on the third day He rose again from the dead; He ascended into heaven, and is seated at the right hand of God the Father almighty; from there He will come to judge the living and the dead." },
  { label: "I believe in the Holy Spirit", prayer: "I believe in the Holy Spirit, the holy catholic Church, the communion of saints, the forgiveness of sins, the resurrection of the body, and life everlasting. Amen." },
];

const CHAIR_OF_ST_PETER: BeadStep[] = [
  { label: "Devotion to the Chair of St. Peter", prayer: "The Feast of the Chair of St. Peter (Cathedra Petri, Feb 22) honors not a piece of furniture but the teaching authority Christ gave to Peter and his successors — the visible principle of the Church's unity." },
  { label: "Prayer for the Pope", prayer: "V. Let us pray for N., our Pope.\nR. May the Lord preserve him, and give him life, and make him blessed upon the earth, and deliver him not up to the will of his enemies." },
  { label: "Thou art Peter", prayer: "Lord Jesus Christ, who said to blessed Peter, 'Thou art Peter, and upon this rock I will build my Church, and the gates of hell shall not prevail against it': look upon Your Church, and keep her ever faithful to the See of Peter, that in unity of faith and communion she may stand firm against every storm." },
  { label: "Let us pray", prayer: "O God, who by the preaching of the Apostle Peter did instruct the multitude of the nations, grant that we who keep the memory of his taking the Chair may feel the effects of his intercession before You, and be strengthened in the confession of the true faith. Through Christ our Lord. Amen." },
];

const STAY_WITH_ME_LORD: BeadStep[] = [
  { label: "'Stay with me, Lord'", prayer: "The prayer of St. Padre Pio after Holy Communion, a heartfelt plea to Jesus to remain with the soul who has received Him." },
  { label: "Stay with me", prayer: "Stay with me, Lord, for it is necessary to have You present so that I do not forget You. You know how easily I abandon You.\nStay with me, Lord, because I am weak and I need Your strength, that I may not fall so often.\nStay with me, Lord, for You are my life, and without You I am without fervor." },
  { label: "Stay with me, my light", prayer: "Stay with me, Lord, for You are my light, and without You I am in darkness.\nStay with me, Lord, to show me Your will.\nStay with me, Lord, so that I hear Your voice and follow You.\nStay with me, Lord, for I desire to love You very much, and always be in Your company." },
  { label: "Stay with me for the night", prayer: "Stay with me, Lord, if You wish me to be faithful to You.\nStay with me, Lord, for as poor as my soul is, I want it to be a place of consolation for You, a nest of love.\nStay with me, Jesus, for it is getting late and the day is coming to a close, and life passes, death, judgment, eternity approach. It is necessary to renew my strength, so that I will not stop along the way, and for that, I need You. It is getting late and death approaches — I fear the darkness, the temptations, the dryness, the cross, the sorrows. O how I need You, my Jesus, in this night of exile!" },
  { label: "Only You", prayer: "Stay with me tonight, Jesus, in life with all its dangers. I need You. Let me recognize You as Your disciples did at the breaking of bread, so that the Eucharistic Communion be the light which disperses the darkness, the force which sustains me, the unique joy of my heart. Stay with me, Lord, for it is You alone I look for, Your Love, Your Grace, Your Will, Your Heart, Your Spirit, because I love You and ask no other reward but to love You more and more. Amen." },
];

const THE_LITTLE_WAY: BeadStep[] = [
  { label: "The Little Way of St. Thérèse", prayer: "St. Thérèse of Lisieux's 'little way of spiritual childhood' — reaching holiness not by great deeds but by doing small, ordinary things with great love and total trust in God as a little child trusts its Father." },
  { label: "Her own words", prayer: "'Love proves itself by deeds, so how am I to show my love? Great deeds are forbidden me. The only way I can prove my love is by scattering flowers, and these flowers are every little sacrifice, every glance and word, and the doing of the least actions for love.'" },
  { label: "An Act of Oblation", prayer: "O my God, I offer You all my actions of this day for the intentions and for the glory of the Sacred Heart of Jesus. I desire to sanctify every beat of my heart, my every thought, my simplest works, by uniting them to His infinite merits; and I wish to make reparation for my sins by casting them into the furnace of His Merciful Love." },
  { label: "A prayer of little confidence", prayer: "O Jesus, I am too little to do great things, so I offer You my littleness. Take my small acts, my hidden sacrifices, my quiet patience, and my daily duties done with love, and make of them a bouquet for Your glory. Teach me to remain little, to trust You wholly, and to abandon myself into Your arms like a child. My vocation is love. In the heart of the Church, my Mother, I will be love. Amen." },
];

const HOLY_FACE: BeadStep[] = [
  { label: "Devotion to the Holy Face of Jesus", prayer: "A devotion of reparation to the Face of Jesus disfigured in His Passion, dear to St. Thérèse of Lisieux (who added 'of the Holy Face' to her name) and spread by Sr. Marie of St. Peter and Bl. Leo Dupont." },
  { label: "O adorable Face", prayer: "O adorable Face of Jesus, so mercifully bowed down upon the tree of the Cross on the day of Your Passion for the salvation of the world, now once more, we beseech You, incline toward us Your merciful gaze, and have pity on us sinners." },
  { label: "Offering of the Holy Face", prayer: "Eternal Father, we offer You the adorable Face of Your beloved Son, for the honor and glory of Your Name, for the conversion of sinners, and for the salvation of the dying." },
  { label: "St. Thérèse's aspiration", prayer: "O Jesus, who in Your bitter Passion did become 'the most abject of men, a man of sorrows,' I venerate Your Holy Face on which shone the beauty and gentleness of the Divinity. In those disfigured features I recognize Your infinite love, and I long to love You and make You loved. Make the image of Your Face be imprinted upon my soul, that I may resemble You. Amen." },
];

const CONSECRATION_OF_PURITY: BeadStep[] = [
  { label: "Consecration of Purity", prayer: "An offering of one's chastity and heart to Christ — for the single, the engaged, the married, and the consecrated alike — placing this virtue under the protection of Our Lady and the holy virgins." },
  { label: "The Consecration", prayer: "O Jesus, Lover of chastity, Mary, Mother most pure, and Joseph, chaste guardian of the Virgin, to you I come at this hour, begging you to plead with God for me. I earnestly wish to be pure in thought, word, and deed, in imitation of your own holy purity." },
  { label: "Guard my senses", prayer: "Obtain for me, then, a deep sense of modesty which will be reflected in my external conduct. Protect my eyes, the windows of my soul, from anything that might dim the luster of a heart that must mirror only Christ-like purity. And when the 'Bread of Angels' becomes my food in Holy Communion, seal my heart forever against the suggestions of sinful pleasures." },
  { label: "Renewal", prayer: "Heart of Jesus, fount of all purity, have mercy on me. Sweet Heart of Mary, be my salvation. Saint Agnes and all holy virgins, pray that I may keep this resolve, and offer my body and soul, whole and undefiled, to God who is worthy of all love. Amen." },
];

const BENEDICTUS: BeadStep[] = [
  { label: "The Benedictus (Canticle of Zechariah)", prayer: "The song of Zechariah at the birth of his son, St. John the Baptist (Luke 1:68–79). The Church sings it every morning at Lauds (Morning Prayer)." },
  { label: "Blessed be the Lord", prayer: "Blessed be the Lord, the God of Israel; he has come to his people and set them free. He has raised up for us a mighty Saviour, born of the house of his servant David. Through his holy prophets he promised of old that he would save us from our enemies, from the hands of all who hate us." },
  { label: "The oath he swore", prayer: "He promised to show mercy to our fathers and to remember his holy covenant. This was the oath he swore to our father Abraham: to set us free from the hands of our enemies, free to worship him without fear, holy and righteous in his sight all the days of our life." },
  { label: "And you, child", prayer: "You, my child, shall be called the prophet of the Most High; for you will go before the Lord to prepare his way, to give his people knowledge of salvation by the forgiveness of their sins. In the tender compassion of our God the dawn from on high shall break upon us, to shine on those who dwell in darkness and the shadow of death, and to guide our feet into the way of peace." },
  { label: "Glory Be", prayer: GLORY_BE },
];

const LITTLE_OFFICE_BVM: BeadStep[] = [
  { label: "Little Office of the Blessed Virgin Mary", prayer: "A shorter form of the Divine Office in honor of Our Lady, prayed by religious and laity for centuries. It is one of the works traditionally associated with the Brown Scapular. Below is Matins with Lauds; the full Office has all the hours (Prime, Terce, Sext, None, Vespers, Compline)." },
  { label: "A word on the Brown Scapular", prayer: "The Brown Scapular of Our Lady of Mount Carmel is a sign of consecration to Mary and of her maternal protection. Given, by tradition, to St. Simon Stock in 1251, it is worn as a small habit — a pledge to live in her love. Those enrolled by a priest are encouraged to pray a Marian devotion daily, such as this Little Office, the Rosary, or the Church's Office. The Scapular is not a magic charm but a garment of grace: worn with a living faith, chastity according to one's state, and daily prayer to Our Lady." },
  { label: "Opening Versicles", prayer: "V. O Lord, open my lips.\nR. And my mouth shall proclaim your praise.\nV. O God, come to my assistance.\nR. O Lord, make haste to help me.\nGlory be to the Father, and to the Son, and to the Holy Spirit... Alleluia." },
  { label: "Hymn", prayer: "Hail, O Star that pointest toward the port of heaven, thou to whom as maiden God for Son was given. When the salutation Gabriel had spoken, peace was shed upon us, Eva's bonds were broken. (Ave Maris Stella)" },
  { label: "Antiphon & Canticle (Magnificat at Vespers)", prayer: "My soul doth magnify the Lord, and my spirit hath rejoiced in God my Saviour... (Luke 1:46–55). He that is mighty hath done great things to me, and holy is his name." },
  { label: "Concluding Prayer", prayer: "Grant, we beseech thee, O Lord God, that we thy servants may enjoy perpetual health of mind and body; and by the glorious intercession of Blessed Mary ever Virgin, may be delivered from present sorrow, and obtain eternal joy. Through Christ our Lord. Amen." },
];

const TANTUM_ERGO: BeadStep[] = [
  { label: "Tantum Ergo", prayer: "The last two verses of St. Thomas Aquinas' hymn Pange Lingua, sung at Benediction of the Blessed Sacrament as the priest incenses the Host." },
  { label: "Tantum Ergo Sacramentum", prayer: "Down in adoration falling, lo! the sacred Host we hail; lo! o'er ancient forms departing, newer rites of grace prevail; faith for all defects supplying, where the feeble senses fail.\n\n(Tantum ergo Sacramentum veneremur cernui: et antiquum documentum novo cedat ritui: praestet fides supplementum sensuum defectui.)" },
  { label: "Genitori Genitoque", prayer: "To the everlasting Father, and the Son who reigns on high, with the Holy Spirit proceeding forth from each eternally, be salvation, honor, blessing, might and endless majesty. Amen.\n\n(Genitori, Genitoque laus et jubilatio, salus, honor, virtus quoque sit et benedictio: procedenti ab utroque compar sit laudatio. Amen.)" },
  { label: "Versicle & Prayer", prayer: "V. Thou hast given them Bread from heaven. (Alleluia.)\nR. Having within it all sweetness. (Alleluia.)\n\nLet us pray. O God, who in this wonderful Sacrament has left us a memorial of Thy Passion: grant us, we beseech Thee, so to venerate the sacred mysteries of Thy Body and Blood, that we may ever feel within us the fruit of Thy redemption. Who livest and reignest for ever and ever. Amen." },
];

/* ========================================================================== */
/*                                 REGISTRY                                   */
/* ========================================================================== */

export const DEVOTIONS: Record<string, Devotion> = {
  // ---- Marian ----
  angelus: { key: "angelus", title: "The Angelus", subtitle: "Morning, noon & evening — the Word made flesh", color: "#3F62A8", icon: "notifications-outline", duration: "~3 min", category: "marian", format: "reader", steps: ANGELUS, good_work_for_today: "Pause at noon today, wherever you are, to pray the Angelus and recall that God became man for love of you.", daily_motto: "And the Word was made flesh." },
  regina_caeli: { key: "regina_caeli", title: "Regina Caeli", subtitle: "Replaces the Angelus during Eastertide", color: "#C9A227", icon: "sunny-outline", duration: "~2 min", category: "marian", format: "reader", steps: REGINA_CAELI, good_work_for_today: "Carry Easter joy to someone weighed down today — a glad word, a small kindness done with a light heart.", daily_motto: "Queen of Heaven, rejoice! Alleluia.", note: "Prayed from Easter Sunday through Pentecost in place of the Angelus." },
  salve_regina: { key: "salve_regina", title: "Salve Regina (Hail Holy Queen)", subtitle: "Our life, our sweetness, and our hope", color: "#5B3475", icon: "star-outline", duration: "~2 min", category: "marian", format: "reader", steps: SALVE_REGINA, good_work_for_today: "Entrust one worry to Our Lady today and leave it in her hands, returning to it only in prayer.", daily_motto: "Turn thine eyes of mercy toward us." },
  sub_tuum: { key: "sub_tuum", title: "Sub Tuum Praesidium", subtitle: "The oldest known Marian prayer (3rd c.)", color: "#3F62A8", icon: "umbrella-outline", duration: "~1 min", category: "marian", format: "reader", steps: SUB_TUUM, good_work_for_today: "When fear or temptation comes today, fly at once to Our Lady's protection with this short prayer.", daily_motto: "We fly to thy protection." },
  memorare: { key: "memorare", title: "The Memorare", subtitle: "Never was it known that anyone was left unaided", color: "#B5476A", icon: "heart-outline", duration: "~2 min", category: "marian", format: "reader", steps: MEMORARE, good_work_for_today: "Pray the Memorare today for someone who seems beyond help, with bold confidence in Mary's intercession.", daily_motto: "Never was it known that anyone was left unaided." },
  magnificat: { key: "magnificat", title: "The Magnificat", subtitle: "Our Lady's own prayer (Luke 1:46–55)", color: "#3F62A8", icon: "musical-note-outline", duration: "~3 min", category: "marian", format: "reader", steps: MAGNIFICAT, good_work_for_today: "Name three concrete things God has done for you, and magnify Him aloud or in your journal today.", daily_motto: "My soul doth magnify the Lord." },

  // ---- Litanies ----
  litany_saints: { key: "litany_saints", title: "Litany of the Saints", subtitle: "The whole company of heaven, pray for us", color: "#7A5C00", icon: "people-circle-outline", duration: "~8 min", category: "litany", format: "reader", steps: LITANY_SAINTS, good_work_for_today: "Choose one saint named in the litany and read a little of their life today, asking their prayers.", daily_motto: "All you holy men and women, pray for us." },
  litany_loreto: { key: "litany_loreto", title: "Litany of the Blessed Virgin Mary (Loreto)", subtitle: "Mother, Virgin, and Queen", color: "#3F62A8", icon: "flower-outline", duration: "~6 min", category: "litany", format: "reader", steps: LITANY_LORETO, good_work_for_today: "Take one title of Our Lady from the litany that moved you, and live it as your aim today.", daily_motto: "Pray for us, O holy Mother of God." },
  litany_sacred_heart: { key: "litany_sacred_heart", title: "Litany of the Sacred Heart", subtitle: "The Heart of Jesus, fountain of life", color: "#9E1B1B", icon: "flame-outline", duration: "~6 min", category: "litany", format: "reader", steps: LITANY_SACRED_HEART, good_work_for_today: "Make your heart 'meek and humble' in one situation today where you would rather be proud or harsh.", daily_motto: "Jesus, make our hearts like unto Thine." },
  litany_st_joseph: { key: "litany_st_joseph", title: "Litany of St. Joseph", subtitle: "Guardian of the Redeemer, pray for us", color: "#6B4E8E", icon: "construct-outline", duration: "~5 min", category: "litany", format: "reader", steps: LITANY_ST_JOSEPH, good_work_for_today: "Do one quiet, hidden act of service today, as St. Joseph worked — without seeking notice.", daily_motto: "Ite ad Ioseph — Go to Joseph." },
  litany_humility: { key: "litany_humility", title: "Litany of Humility", subtitle: "Cardinal Merry del Val's bracing classic", color: "#4A5568", icon: "leaf-outline", duration: "~4 min", category: "litany", format: "reader", steps: LITANY_HUMILITY, good_work_for_today: "Let someone else be praised or preferred today without correcting the record — and rejoice in it.", daily_motto: "That others may increase, and I may decrease." },

  // ---- Stations ----
  stations_traditional: { key: "stations_traditional", title: "Stations of the Cross — Traditional", subtitle: "The fourteen Stations, with meditations", color: "#5D4037", icon: "walk-outline", duration: "~20 min", category: "stations", format: "steps", steps: buildStations(STATION_TRADITIONAL_MEDITATIONS), good_work_for_today: "Carry one cross today — an annoyance, a pain, a duty — silently and patiently, offered for someone you love.", daily_motto: "We adore Thee, O Christ, and we bless Thee." },
  stations_scriptural: { key: "stations_scriptural", title: "Stations of the Cross — Scriptural", subtitle: "The Way of the Cross drawn from the Gospels", color: "#5D4037", icon: "book-outline", duration: "~20 min", category: "stations", format: "steps", steps: buildStations(STATION_SCRIPTURAL.map((s) => s.text), STATION_SCRIPTURAL), good_work_for_today: "Read slowly one of today's Gospel verses again this evening, and let it shape how you forgive.", daily_motto: "Father, forgive them.", note: "The Scriptural Way of the Cross, in the form prayed by Pope St. John Paul II, drawn entirely from Scripture." },
  way_of_cross_liguori: { key: "way_of_cross_liguori", title: "The Way of the Cross — St. Alphonsus Liguori", subtitle: "The beloved devotion of the Redemptorist saint", color: "#7A3B2E", icon: "rose-outline", duration: "~22 min", category: "stations", format: "steps", steps: buildStations(LIGUORI_MEDITATIONS), good_work_for_today: "Make an act of sorrow for one particular sin today, and a firm, concrete resolution against it.", daily_motto: "I love Thee, Jesus my love, above all things." },

  // ---- Mass & Communion ----
  before_mass: { key: "before_mass", title: "Prayer Before Mass", subtitle: "St. Thomas Aquinas — the Physician of life", color: "#1E5631", icon: "enter-outline", duration: "~3 min", category: "mass", format: "reader", steps: BEFORE_MASS, good_work_for_today: "Arrive a few minutes early to Mass or to prayer today, and quiet your heart before the Lord.", daily_motto: "As one sick I come to the Physician of life." },
  after_mass: { key: "after_mass", title: "Thanksgiving After Mass", subtitle: "St. Thomas Aquinas — grateful thanksgiving", color: "#1E5631", icon: "exit-outline", duration: "~3 min", category: "mass", format: "reader", steps: AFTER_MASS, good_work_for_today: "Stay a few minutes after Mass or prayer today simply to thank God, before rushing to the next thing.", daily_motto: "I give Thee thanks, O holy Lord." },
  before_communion: { key: "before_communion", title: "Prayers Before Communion", subtitle: "Act of faith & spiritual Communion", color: "#9E7B1B", icon: "heart-half-outline", duration: "~2 min", category: "mass", format: "reader", steps: BEFORE_COMMUNION, good_work_for_today: "Make a spiritual Communion at some point today when you cannot be at Mass, inviting Jesus into your heart.", daily_motto: "Only say the word, and my soul shall be healed." },
  after_communion: { key: "after_communion", title: "Prayers After Communion", subtitle: "Anima Christi & thanksgiving", color: "#9E1B1B", icon: "flame-outline", duration: "~3 min", category: "mass", format: "reader", steps: AFTER_COMMUNION, good_work_for_today: "Let your thanksgiving overflow into one act of generosity today, giving freely as you have received.", daily_motto: "Soul of Christ, sanctify me." },

  // ---- Devotions & Acts ----
  st_michael_prayer: { key: "st_michael_prayer", title: "Prayer to St. Michael the Archangel", subtitle: "Pope Leo XIII — defend us in battle", color: "#B22234", icon: "shield-checkmark-outline", duration: "~1 min", category: "devotional", format: "reader", steps: ST_MICHAEL_PRAYER, good_work_for_today: "Stand up for someone under attack today — defend the absent, the weak, or the truth, with charity.", daily_motto: "Quis ut Deus? — Who is like God?" },
  morning_offering: { key: "morning_offering", title: "Morning Offering", subtitle: "Give the whole day to the Heart of Jesus", color: "#C29A3B", icon: "sunny-outline", duration: "~1 min", category: "devotional", format: "reader", steps: MORNING_OFFERING, good_work_for_today: "When something hard comes today, remember you already offered it this morning — and offer it again.", daily_motto: "I offer You my prayers, works, joys, and sufferings." },
  acts_faith_hope_charity: { key: "acts_faith_hope_charity", title: "Acts of Faith, Hope & Charity", subtitle: "The three theological virtues, in prayer", color: "#5B3475", icon: "ribbon-outline", duration: "~2 min", category: "devotional", format: "reader", steps: ACTS_FHC, good_work_for_today: "Practice one of these virtues deliberately today: trust God in a worry, or love someone hard to love.", daily_motto: "Faith, hope, and love — the greatest of these is love." },
  te_deum: { key: "te_deum", title: "Te Deum", subtitle: "Ancient hymn of praise & thanksgiving", color: "#7A5C00", icon: "trophy-outline", duration: "~3 min", category: "devotional", format: "reader", steps: TE_DEUM, good_work_for_today: "Give thanks today for a grace you usually overlook, and tell one person about something good God has done.", daily_motto: "We praise Thee, O God." },
  st_patricks_breastplate: { key: "st_patricks_breastplate", title: "St. Patrick's Breastplate", subtitle: "The Lorica — Christ before me, Christ behind me", color: "#1E5631", icon: "shield-outline", duration: "~3 min", category: "devotional", format: "reader", steps: ST_PATRICK, good_work_for_today: "Begin a difficult task today by binding yourself to Christ — 'Christ before me' — and act with courage.", daily_motto: "Christ with me, Christ within me." },
  leonine_prayers: { key: "leonine_prayers", title: "The Leonine Prayers", subtitle: "The full set once said after Low Mass", color: "#4A5568", icon: "list-outline", duration: "~5 min", category: "devotional", format: "reader", steps: LEONINE_PRAYERS, good_work_for_today: "Pray today for the freedom and exaltation of the Church, and for the conversion of one person by name.", daily_motto: "For the liberty and exaltation of Holy Mother Church." },
  deliverance_prayers: { key: "deliverance_prayers", title: "Prayers of Deliverance & Protection", subtitle: "Private prayers approved for lay use", color: "#3A2F4A", icon: "shield-half-outline", duration: "~3 min", category: "devotional", format: "reader", steps: DELIVERANCE_PRAYERS, good_work_for_today: "Go to Confession soon, and frequent the Sacraments — the surest protection against every evil.", daily_motto: "In the Name of Jesus.", note: "The solemn Rite of Exorcism is reserved to a priest delegated by his bishop. These are private deliverance prayers for the lay faithful, not the formal Rite." },
  binding_holy_spirit: { key: "binding_holy_spirit", title: "Binding Prayer to the Holy Spirit", subtitle: "Surrender every part of yourself to God", color: "#B5476A", icon: "flame-outline", duration: "~2 min", category: "devotional", format: "reader", steps: BINDING_HOLY_SPIRIT, good_work_for_today: "Hand over one area of your life you tend to control today, and let the Holy Spirit lead it.", daily_motto: "Come, Holy Spirit." },

  // ---- Seasonal ----
  seasonal_prayers: { key: "seasonal_prayers", title: "Prayers for the Liturgical Seasons", subtitle: "Advent · Christmas · Lent · Easter · Ordinary Time", color: "#2A5A3B", icon: "leaf-outline", duration: "~3 min", category: "seasonal", format: "reader", steps: SEASONAL_PRAYERS, good_work_for_today: "Live one small practice fitting the season today — an extra penance in Lent, an act of joy in Easter.", daily_motto: "To everything there is a season." },
  feast_day_prayers: { key: "feast_day_prayers", title: "Feast Day Prayers", subtitle: "For the great solemnities & feasts", color: "#C9A227", icon: "star-outline", duration: "~3 min", category: "seasonal", format: "reader", steps: FEAST_DAY_PRAYERS, good_work_for_today: "Keep today's feast (or the nearest one) with a little extra joy — a special prayer, or a kindness in its honor.", daily_motto: "Rejoice in the Lord always." },
  first_friday_saturday: { key: "first_friday_saturday", title: "First Friday & First Saturday Devotions", subtitle: "Reparation to the Sacred & Immaculate Hearts", color: "#9E1B1B", icon: "calendar-outline", duration: "~4 min", category: "seasonal", format: "reader", steps: FIRST_FRIDAY_SATURDAY, good_work_for_today: "Resolve to begin (or continue) the Nine First Fridays or Five First Saturdays this month.", daily_motto: "Reparation, in love, to the Two Hearts." },

  // ---- Added devotions (deep-linked from companions) ----
  to_you_blessed_joseph: { key: "to_you_blessed_joseph", title: "To You, O Blessed Joseph", subtitle: "The Leonine prayer to St. Joseph, protector of the Church", color: "#6B4E8E", icon: "shield-half-outline", duration: "~2 min", category: "devotional", format: "reader", steps: TO_YOU_BLESSED_JOSEPH, good_work_for_today: "Entrust one worry about your family or the Church to St. Joseph today, and do one quiet act of protection or provision for someone in your care.", daily_motto: "Ite ad Ioseph — Go to Joseph." },
  angel_of_god: { key: "angel_of_god", title: "The Angel of God", subtitle: "The morning & evening prayer to your Guardian Angel", color: "#4A7C8C", icon: "sparkles-outline", duration: "~1 min", category: "devotional", format: "reader", steps: ANGEL_OF_GOD, good_work_for_today: "Pray to your Guardian Angel morning and night today, and pause once to ask his help before a hard moment.", daily_motto: "Ever this day be at my side." },
  litany_virgin_martyrs: { key: "litany_virgin_martyrs", title: "Litany of the Virgin Martyrs", subtitle: "The holy virgins who loved Christ above their lives", color: "#8A2E5B", icon: "rose-outline", duration: "~4 min", category: "litany", format: "reader", steps: LITANY_VIRGIN_MARTYRS, good_work_for_today: "Ask the holy virgin martyrs for courage today to do one right thing that costs you something.", daily_motto: "They followed the Lamb whithersoever He goeth." },
  act_of_reparation: { key: "act_of_reparation", title: "Act of Reparation to the Sacred Heart", subtitle: "To console the Heart of Jesus, so often forgotten", color: "#9E1B1B", icon: "flame-outline", duration: "~3 min", category: "devotional", format: "reader", steps: ACT_OF_REPARATION, good_work_for_today: "Make one small act of reparation today — a kindness offered where Jesus is forgotten, or a sin of yours amended.", daily_motto: "Most Sacred Heart of Jesus, I trust in You." },
  apostles_creed: { key: "apostles_creed", title: "The Apostles' Creed", subtitle: "The ancient summary of the apostolic faith", color: "#2A5A3B", icon: "book-outline", duration: "~1 min", category: "devotional", format: "reader", steps: APOSTLES_CREED, good_work_for_today: "Profess the Creed slowly today, and live one article of it — forgive someone, in the faith of the 'forgiveness of sins.'", daily_motto: "I believe — help my unbelief." },
  chair_of_st_peter: { key: "chair_of_st_peter", title: "Devotion to the Chair of St. Peter", subtitle: "For fidelity and unity around the See of Peter", color: "#B08D3F", icon: "key-outline", duration: "~2 min", category: "devotional", format: "reader", steps: CHAIR_OF_ST_PETER, good_work_for_today: "Pray for the Pope today by name, and for the unity of the Church wherever it is wounded.", daily_motto: "Thou art Peter, and upon this rock." },
  stay_with_me_lord: { key: "stay_with_me_lord", title: "'Stay with Me, Lord'", subtitle: "St. Padre Pio's prayer after Holy Communion", color: "#5D4037", icon: "heart-half-outline", duration: "~3 min", category: "mass", format: "reader", steps: STAY_WITH_ME_LORD, good_work_for_today: "After Mass or a spiritual Communion today, stay a few extra minutes with Jesus and simply ask Him to remain with you.", daily_motto: "Stay with me, Lord." },
  the_little_way: { key: "the_little_way", title: "The Little Way of St. Thérèse", subtitle: "Holiness through small things done with great love", color: "#B5476A", icon: "flower-outline", duration: "~3 min", category: "devotional", format: "reader", steps: THE_LITTLE_WAY, good_work_for_today: "Do three small, hidden acts of love today with great care — and offer them to Jesus without seeking notice.", daily_motto: "My vocation is love." },
  holy_face: { key: "holy_face", title: "Devotion to the Holy Face", subtitle: "Reparation to the Face of Jesus in His Passion", color: "#7A3B2E", icon: "eye-outline", duration: "~3 min", category: "devotional", format: "reader", steps: HOLY_FACE, good_work_for_today: "Offer the Holy Face today for a sinner or a dying soul, and bear one small humiliation in reparation.", daily_motto: "Make me love You, and make You loved." },
  consecration_of_purity: { key: "consecration_of_purity", title: "Consecration of Purity", subtitle: "Offer your chastity and heart to Christ", color: "#3F62A8", icon: "shield-checkmark-outline", duration: "~2 min", category: "devotional", format: "reader", steps: CONSECRATION_OF_PURITY, good_work_for_today: "Guard your eyes and heart today in one concrete way — turn away from one impure image or thought, and renew this offering.", daily_motto: "Blessed are the pure in heart." },
  benedictus: { key: "benedictus", title: "The Benedictus", subtitle: "The Canticle of Zechariah (Luke 1:68–79)", color: "#1E5631", icon: "sunny-outline", duration: "~2 min", category: "devotional", format: "reader", steps: BENEDICTUS, good_work_for_today: "Prepare the way of the Lord today by repenting of one thing and helping one person walk toward the light.", daily_motto: "The dawn from on high shall break upon us." },
  little_office_bvm: { key: "little_office_bvm", title: "Little Office of the Blessed Virgin Mary", subtitle: "The ancient Marian hours — and the Brown Scapular", color: "#3F62A8", icon: "book-outline", duration: "~8 min", category: "marian", format: "reader", steps: LITTLE_OFFICE_BVM, good_work_for_today: "Wear or honor your Brown Scapular today as a sign of consecration to Mary, and pray at least one hour of her Office.", daily_motto: "Hail, O Star of the sea.", note: "The full Little Office has all the hours. Enrollment in the Brown Scapular is done by a priest; those enrolled are encouraged to pray a Marian devotion daily." },
  tantum_ergo: { key: "tantum_ergo", title: "Tantum Ergo", subtitle: "St. Thomas Aquinas' hymn at Benediction", color: "#9E7B1B", icon: "wine-outline", duration: "~2 min", category: "mass", format: "reader", steps: TANTUM_ERGO, good_work_for_today: "Make a visit to the Blessed Sacrament today, however brief, and adore the Lord truly present.", daily_motto: "Down in adoration falling." },
};

export const DEVOTION_CATEGORIES: { key: DevotionCategory; label: string; keys: string[] }[] = [
  { key: "marian", label: "Marian Prayers", keys: ["angelus", "regina_caeli", "salve_regina", "sub_tuum", "memorare", "magnificat", "little_office_bvm"] },
  { key: "litany", label: "Litanies", keys: ["litany_saints", "litany_loreto", "litany_sacred_heart", "litany_st_joseph", "litany_humility", "litany_virgin_martyrs"] },
  { key: "stations", label: "Stations of the Cross", keys: ["stations_traditional", "stations_scriptural", "way_of_cross_liguori"] },
  { key: "mass", label: "Mass & Communion", keys: ["before_mass", "after_mass", "before_communion", "after_communion", "stay_with_me_lord", "tantum_ergo"] },
  { key: "devotional", label: "Devotions & Acts", keys: ["st_michael_prayer", "morning_offering", "acts_faith_hope_charity", "te_deum", "st_patricks_breastplate", "leonine_prayers", "deliverance_prayers", "binding_holy_spirit", "apostles_creed", "angel_of_god", "to_you_blessed_joseph", "act_of_reparation", "chair_of_st_peter", "the_little_way", "holy_face", "consecration_of_purity", "benedictus"] },
  { key: "seasonal", label: "Seasonal & Feast Day", keys: ["seasonal_prayers", "feast_day_prayers", "first_friday_saturday"] },
];

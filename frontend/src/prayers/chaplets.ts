/**
 * Catholic Chaplets — a small in-app library of devotional bead prayers.
 *
 * Each chaplet exposes:
 *  - a structured ordered list of "steps" (label + prayer text)
 *  - a "good_work_for_today" — a small practical, virtuous action to live
 *    the chaplet's grace beyond the bead.
 *
 * Sources / traditions:
 *  - St Michael: Devotion revealed to Antonia d'Astonac (1751); 9 salutations + 4 Our Fathers.
 *  - Immaculate Heart of Mary: "Twelve Stars" Marian devotion (Rev 12:1).
 *  - Sacred Heart of Jesus: 33-invocation devotion (St Marie Martha Chambon tradition).
 *  - St Lucy: Sicilian patronal devotion; 13 Hail Marys for the light of her witness.
 *  - St Padre Pio: 6 Glory Bes for intercession ("Padre Pio Crown").
 *  - Sts Peter & Paul: Apostolic pillars; 6 decades (3 for each).
 *
 * We keep prayers short and accurate to their core forms; users are encouraged
 * to pray slowly and to consult their parish or a Catholic prayer book for the
 * fully traditional texts when desired.
 */

import { BeadStep } from "@/src/rosary";

export type ChapletKey =
  | "divine_mercy"
  | "st_michael"
  | "guardian_angel"
  | "immaculate_heart"
  | "sacred_heart"
  | "st_lucy"
  | "st_padre_pio"
  | "peter_and_paul"
  | "st_joseph_renewal"
  | "marian_renewal"
  | "sacred_heart_renewal"
  | "st_joseph_chaplet"
  | "franciscan_crown";

export type Chaplet = {
  key: ChapletKey;
  title: string;
  /** Short subtitle shown on the hub card */
  subtitle: string;
  /** Theme color (hex) */
  color: string;
  /** Ionicons name for the hub card */
  icon: string;
  /** Approximate prayer time, e.g. "~10 min" */
  duration: string;
  /** Build the ordered list of steps for the chaplet */
  steps: BeadStep[];
  /** Practical virtue/action to live the chaplet's grace today */
  good_work_for_today: string;
  /** Short verse / motto to anchor the day */
  daily_motto: string;
  /** Optional highlighted note shown before the prayer (e.g. consecration guidance) */
  note?: string;
};

/* -------------------------------------------------------------------------- */
/*                              CHAPLET OF ST MICHAEL                          */
/* -------------------------------------------------------------------------- */

const ST_MICHAEL_CHOIRS: { name: string; petition: string }[] = [
  { name: "Seraphim", petition: "By the intercession of St. Michael and the celestial Choir of Seraphim, may the Lord make us worthy to burn with the fire of perfect charity. Amen." },
  { name: "Cherubim", petition: "By the intercession of St. Michael and the celestial Choir of Cherubim, may the Lord grant us the grace to leave the ways of sin and run in the paths of Christian perfection. Amen." },
  { name: "Thrones", petition: "By the intercession of St. Michael and the celestial Choir of Thrones, may the Lord infuse into our hearts a true and sincere spirit of humility. Amen." },
  { name: "Dominations", petition: "By the intercession of St. Michael and the celestial Choir of Dominations, may the Lord give us the grace to govern our senses and overcome any unruly passions. Amen." },
  { name: "Virtues", petition: "By the intercession of St. Michael and the celestial Choir of Virtues, may the Lord preserve us from evil and falling into temptation. Amen." },
  { name: "Powers", petition: "By the intercession of St. Michael and the celestial Choir of Powers, may the Lord protect our souls against the snares and temptations of the devil. Amen." },
  { name: "Principalities", petition: "By the intercession of St. Michael and the celestial Choir of Principalities, may God fill our souls with a true spirit of obedience. Amen." },
  { name: "Archangels", petition: "By the intercession of St. Michael and the celestial Choir of Archangels, may the Lord give us perseverance in faith and in all good works, that we may attain the glory of Heaven. Amen." },
  { name: "Angels", petition: "By the intercession of St. Michael and the celestial Choir of Angels, may the Lord grant us to be protected by them in this mortal life, and conducted hereafter to eternal glory. Amen." },
];

function buildStMichael(): BeadStep[] {
  const steps: BeadStep[] = [];
  steps.push({
    label: "Sign of the Cross",
    prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  });
  steps.push({
    label: "Opening Invocation",
    prayer:
      "O God, come to my assistance. O Lord, make haste to help me.\n\nGlory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.",
  });

  ST_MICHAEL_CHOIRS.forEach((c, i) => {
    steps.push({
      label: `${i + 1}. Salutation — ${c.name}`,
      prayer: c.petition,
    });
    steps.push({ label: "Our Father", prayer: "Our Father, Who art in heaven, hallowed be Thy name; Thy kingdom come; Thy will be done on earth as it is in heaven. Give us this day our daily bread; and forgive us our trespasses, as we forgive those who trespass against us; and lead us not into temptation, but deliver us from evil. Amen." });
    for (let j = 1; j <= 3; j++) {
      steps.push({ label: `Hail Mary (${j}/3)`, prayer: "Hail Mary, full of grace, the Lord is with thee. Blessed art thou amongst women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen." });
    }
  });

  // 4 Our Fathers
  steps.push({
    label: "Our Father — in honor of St. Michael the Archangel",
    prayer: "Glorious prince St. Michael, chief and commander of the heavenly hosts, defend us in battle.",
  });
  steps.push({
    label: "Our Father — in honor of St. Gabriel the Archangel",
    prayer: "St. Gabriel, faithful herald of the Incarnation, pray for us.",
  });
  steps.push({
    label: "Our Father — in honor of St. Raphael the Archangel",
    prayer: "St. Raphael, healer and guide of travelers, pray for us.",
  });
  steps.push({
    label: "Our Father — for our Guardian Angel",
    prayer:
      "Angel of God, my guardian dear, to whom God's love commits me here, ever this day be at my side, to light and guard, to rule and guide. Amen.",
  });

  steps.push({
    label: "Closing Prayer",
    prayer:
      "O glorious prince St. Michael, chief and commander of the heavenly hosts, guardian of souls, vanquisher of rebel spirits, servant in the house of the Divine King — be our defender against the wickedness and snares of the devil, that we may not perish at the dreadful judgment. We humbly entreat thee. Amen.",
  });
  steps.push({
    label: "Sign of the Cross",
    prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  });
  return steps;
}

/* -------------------------------------------------------------------------- */
/*                     CHAPLET OF THE HOLY GUARDIAN ANGEL                     */
/* -------------------------------------------------------------------------- */

const GUARDIAN_ANGEL_OFFICES: { role: string; petition: string }[] = [
  { role: "To Light", petition: "O holy Angel, given me by God to enlighten my mind, drive far from me the darkness of error and sin, and lead me always in the light of truth. Amen." },
  { role: "To Guard", petition: "O faithful Angel, appointed to guard me, protect me this day from every harm of body and soul, and keep me under the shadow of your wings. Amen." },
  { role: "To Rule", petition: "O loving Angel, sent to govern me, help me to master my passions and desires, that in all things I may seek only the will of God. Amen." },
  { role: "To Guide", petition: "O watchful Angel, given to guide me, direct my every step in the way of holiness, and turn me back whenever I begin to stray. Amen." },
  { role: "To Bring Me Home", petition: "O blessed Angel, my companion on the way, lead me safely through this life and bring me at last to the vision of God in heaven. Amen." },
];

function buildGuardianAngel(): BeadStep[] {
  const steps: BeadStep[] = [];
  steps.push({
    label: "Sign of the Cross",
    prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  });
  steps.push({
    label: "Opening Invocation",
    prayer:
      "O God, come to my assistance. O Lord, make haste to help me.\n\nGlory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.",
  });

  GUARDIAN_ANGEL_OFFICES.forEach((o, i) => {
    steps.push({ label: `${i + 1}. Salutation — ${o.role}`, prayer: o.petition });
    steps.push({
      label: "Angel of God",
      prayer:
        "Angel of God, my guardian dear, to whom God's love commits me here, ever this day (or night) be at my side, to light and guard, to rule and guide. Amen.",
    });
    steps.push({
      label: "Glory Be",
      prayer:
        "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.",
    });
  });

  steps.push({
    label: "Prayer to One's Guardian Angel",
    prayer:
      "O most holy Angel of God, appointed by Him to be my guardian, I give you thanks for all the benefits you have ever bestowed on me in body and in soul. I praise and glorify you that you condescended to assist me with such patient fidelity, and to defend me against all the assaults of my enemies. Blessed be the hour in which you were assigned me for my guardian, my defender, and my patron. Amen.",
  });
  steps.push({
    label: "Collect — Feast of the Holy Guardian Angels (Oct 2)",
    prayer:
      "O God, who in your unfathomable providence are pleased to send your holy Angels to guard us, hear our supplication as we cry to you, that we may always be defended by their protection and rejoice eternally in their company. Through Christ our Lord. Amen.",
  });
  steps.push({
    label: "Sign of the Cross",
    prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  });
  return steps;
}

/* -------------------------------------------------------------------------- */
/*                      CHAPLET OF THE IMMACULATE HEART                        */
/* -------------------------------------------------------------------------- */

const IH_MARY_MEDITATIONS: { name: string; reflection: string }[] = [
  { name: "Star of Faith", reflection: "Mary's fiat — 'Be it done unto me according to thy word.'" },
  { name: "Star of Hope", reflection: "She bore Christ within her, the hope of all the world." },
  { name: "Star of Charity", reflection: "She hastened to her cousin Elizabeth, charity in motion." },
  { name: "Star of Humility", reflection: "'He hath regarded the humility of his handmaid.'" },
  { name: "Star of Purity", reflection: "She is the dawn that goes before the Sun of Justice." },
  { name: "Star of Obedience", reflection: "The Holy Family, obedient even to the Temple of the Law." },
  { name: "Star of Patience", reflection: "She stood beside the Cross — patient unto the end." },
  { name: "Star of Mercy", reflection: "Mother of mercy, refuge of sinners, pray for us." },
  { name: "Star of Wisdom", reflection: "She kept all these things, pondering them in her heart." },
  { name: "Star of Compassion", reflection: "Her Immaculate Heart, pierced by the sword of sorrow." },
  { name: "Star of Fidelity", reflection: "Faithful to the end at Calvary, faithful at Pentecost." },
  { name: "Star of Glory", reflection: "A great sign appeared in heaven: a woman crowned with twelve stars." },
];

function buildImmaculateHeart(): BeadStep[] {
  const steps: BeadStep[] = [];
  steps.push({
    label: "Sign of the Cross",
    prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  });
  steps.push({
    label: "Opening",
    prayer:
      "O Immaculate Heart of Mary, full of love for God and mankind, and of compassion for sinners, I consecrate myself to thee. I entrust to thee the care of my own salvation. Through this thy Immaculate Heart, become my refuge and the way that leads to God.",
  });
  steps.push({
    label: "Our Father",
    prayer: "Our Father, Who art in heaven, hallowed be Thy name; Thy kingdom come; Thy will be done on earth as it is in heaven. Give us this day our daily bread; and forgive us our trespasses, as we forgive those who trespass against us; and lead us not into temptation, but deliver us from evil. Amen.",
  });

  IH_MARY_MEDITATIONS.forEach((m, i) => {
    steps.push({ label: `${i + 1}. ${m.name}`, prayer: m.reflection });
    steps.push({
      label: `Hail Mary (${i + 1}/12)`,
      prayer:
        "Hail Mary, full of grace, the Lord is with thee. Blessed art thou amongst women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen.",
    });
  });

  steps.push({
    label: "Glory Be",
    prayer:
      "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.",
  });
  steps.push({
    label: "Closing Prayer",
    prayer:
      "Sweet Heart of Mary, be my salvation. Most pure Heart of Mary, fashion me after the Heart of thy Son. Amen.",
  });
  steps.push({
    label: "Sign of the Cross",
    prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  });
  return steps;
}

/* -------------------------------------------------------------------------- */
/*                       CHAPLET OF THE SACRED HEART                           */
/* -------------------------------------------------------------------------- */

function buildSacredHeart(): BeadStep[] {
  const steps: BeadStep[] = [];
  steps.push({
    label: "Sign of the Cross",
    prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  });
  steps.push({
    label: "Opening",
    prayer:
      "O Most Sacred Heart of Jesus, fountain of every blessing, I adore Thee, I love Thee, and with lively sorrow for my sins, I offer Thee this poor heart of mine. Make me humble, patient, pure and wholly obedient to Thy will.",
  });
  steps.push({
    label: "Our Father",
    prayer: "Our Father, Who art in heaven, hallowed be Thy name; Thy kingdom come; Thy will be done on earth as it is in heaven. Give us this day our daily bread; and forgive us our trespasses, as we forgive those who trespass against us; and lead us not into temptation, but deliver us from evil. Amen.",
  });
  steps.push({
    label: "Hail Mary",
    prayer: "Hail Mary, full of grace, the Lord is with thee. Blessed art thou amongst women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen.",
  });

  // 33 invocations — 11 sets of 3, each set = (1 Sacred Heart invocation + 2 short petitions)
  // Simplest accurate form: 33 repetitions of the principal aspiration.
  for (let i = 1; i <= 33; i++) {
    steps.push({
      label: `Invocation ${i}/33`,
      prayer:
        "Sweet Heart of my Jesus, grant that I may ever love Thee more and more.",
    });
  }

  steps.push({
    label: "Glory Be",
    prayer: "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.",
  });
  steps.push({
    label: "Closing Prayer",
    prayer:
      "Most Sacred Heart of Jesus, I trust in Thee. Heart of Jesus, burning with love for me, set my heart on fire with love of Thee. Amen.",
  });
  steps.push({
    label: "Sign of the Cross",
    prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  });
  return steps;
}

/* -------------------------------------------------------------------------- */
/*                            CHAPLET OF ST LUCY                               */
/* -------------------------------------------------------------------------- */

function buildStLucy(): BeadStep[] {
  const steps: BeadStep[] = [];
  steps.push({
    label: "Sign of the Cross",
    prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  });
  steps.push({
    label: "Opening",
    prayer:
      "O glorious St. Lucy — virgin and martyr, whose name signifies light — obtain for us the grace to walk as children of the light. Pray for us, that the eyes of our soul may be cleansed of all that dims them.",
  });
  steps.push({ label: "Our Father", prayer: "Our Father, Who art in heaven, hallowed be Thy name; Thy kingdom come; Thy will be done on earth as it is in heaven. Give us this day our daily bread; and forgive us our trespasses, as we forgive those who trespass against us; and lead us not into temptation, but deliver us from evil. Amen." });

  // 13 Hail Marys (her feast is Dec 13)
  for (let i = 1; i <= 13; i++) {
    steps.push({
      label: `Hail Mary (${i}/13)`,
      prayer: "Hail Mary, full of grace, the Lord is with thee. Blessed art thou amongst women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen.",
    });
  }

  steps.push({
    label: "St. Lucy Petition",
    prayer:
      "St. Lucy, who chose Christ above every earthly love, intercede for me. Grant me clarity of vision, both of body and of soul, that I may walk uprightly in the light of Christ.",
  });
  steps.push({
    label: "Glory Be",
    prayer: "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.",
  });
  steps.push({
    label: "Closing Prayer",
    prayer:
      "Lord Jesus, by the prayers of St. Lucy, drive far from us all the dark things that obscure Thee from our gaze, and let us see Thy face. Amen.",
  });
  steps.push({
    label: "Sign of the Cross",
    prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  });
  return steps;
}

/* -------------------------------------------------------------------------- */
/*                          CHAPLET OF ST PADRE PIO                            */
/* -------------------------------------------------------------------------- */

const PADRE_PIO_INTENTIONS = [
  "for the conversion of sinners",
  "for the holy souls in Purgatory",
  "for the Holy Father and the Church",
  "for those who suffer in body and spirit",
  "for our families and loved ones",
  "for all who have asked our prayers",
];

function buildStPadrePio(): BeadStep[] {
  const steps: BeadStep[] = [];
  steps.push({
    label: "Sign of the Cross",
    prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  });
  steps.push({
    label: "Opening",
    prayer:
      "O St. Padre Pio, faithful son of Christ, who bore the wounds of our Lord in your own flesh — I come to you trusting in your intercession before the Throne of Mercy.",
  });

  PADRE_PIO_INTENTIONS.forEach((intention, i) => {
    steps.push({
      label: `Intention ${i + 1}/6`,
      prayer: `Let us pray ${intention}.`,
    });
    steps.push({
      label: `Our Father (${i + 1}/6)`,
      prayer: "Our Father, Who art in heaven, hallowed be Thy name; Thy kingdom come; Thy will be done on earth as it is in heaven. Give us this day our daily bread; and forgive us our trespasses, as we forgive those who trespass against us; and lead us not into temptation, but deliver us from evil. Amen.",
    });
    steps.push({
      label: `Hail Mary (${i + 1}/6)`,
      prayer: "Hail Mary, full of grace, the Lord is with thee. Blessed art thou amongst women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen.",
    });
    steps.push({
      label: `Glory Be (${i + 1}/6)`,
      prayer:
        "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.",
    });
  });

  steps.push({
    label: "Padre Pio's Counsel",
    prayer: "Pray, hope, and don't worry. Anxiety doesn't help at all. Our Merciful Lord will listen to your prayer.",
  });
  steps.push({
    label: "Closing Prayer",
    prayer:
      "O glorious St. Padre Pio, who labored to lead souls to God, obtain for me from the Sacred Heart of Jesus the grace I ask through your intercession. Amen.",
  });
  steps.push({
    label: "Sign of the Cross",
    prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  });
  return steps;
}

/* -------------------------------------------------------------------------- */
/*                       CHAPLET OF STS PETER AND PAUL                         */
/* -------------------------------------------------------------------------- */

const PETER_PAUL_DECADES = [
  { saint: "Peter", focus: "His confession: 'Thou art the Christ, the Son of the living God.'" },
  { saint: "Peter", focus: "His repentance after denying the Lord, and the look of Christ that restored him." },
  { saint: "Peter", focus: "His shepherding of the flock, in obedience to the threefold 'Feed my sheep.'" },
  { saint: "Paul", focus: "His conversion on the road to Damascus — Saul becoming Paul." },
  { saint: "Paul", focus: "His tireless missionary journeys and his fidelity in chains." },
  { saint: "Paul", focus: "His martyrdom in Rome: 'I have fought the good fight; I have kept the faith.'" },
];

function buildPeterAndPaul(): BeadStep[] {
  const steps: BeadStep[] = [];
  steps.push({
    label: "Sign of the Cross",
    prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  });
  steps.push({
    label: "Opening",
    prayer:
      "O God, who didst consecrate this day by the martyrdom of Thy Apostles Peter and Paul, grant that Thy Church may in all things follow the teaching of those through whom she first received the faith. Amen.",
  });

  PETER_PAUL_DECADES.forEach((d, i) => {
    steps.push({
      label: `${i + 1}. ${d.saint} — Meditation`,
      prayer: d.focus,
    });
    steps.push({
      label: "Our Father",
      prayer: "Our Father, Who art in heaven, hallowed be Thy name; Thy kingdom come; Thy will be done on earth as it is in heaven. Give us this day our daily bread; and forgive us our trespasses, as we forgive those who trespass against us; and lead us not into temptation, but deliver us from evil. Amen.",
    });
    for (let j = 1; j <= 3; j++) {
      steps.push({
        label: `Hail Mary (${j}/3)`,
        prayer: "Hail Mary, full of grace, the Lord is with thee. Blessed art thou amongst women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen.",
      });
    }
    steps.push({
      label: "Glory Be",
      prayer: "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.",
    });
    steps.push({
      label: `${d.saint}'s Petition`,
      prayer:
        d.saint === "Peter"
          ? "St. Peter, rock of the Church, keeper of the keys — pray for us."
          : "St. Paul, apostle to the nations, vessel of election — pray for us.",
    });
  });

  steps.push({
    label: "Closing Prayer",
    prayer:
      "Holy Apostles Peter and Paul, pray for us. Defend Christ's Church in our day, and keep her bound to the faith you handed on. Amen.",
  });
  steps.push({
    label: "Sign of the Cross",
    prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  });
  return steps;
}

/* -------------------------------------------------------------------------- */
/*                       CHAPLET OF DIVINE MERCY                              */
/* -------------------------------------------------------------------------- */

function buildDivineMercy(): BeadStep[] {
  const OUR_FATHER = "Our Father, Who art in heaven, hallowed be Thy name; Thy kingdom come; Thy will be done on earth as it is in heaven. Give us this day our daily bread; and forgive us our trespasses, as we forgive those who trespass against us; and lead us not into temptation, but deliver us from evil. Amen.";
  const HAIL_MARY = "Hail Mary, full of grace, the Lord is with thee. Blessed art thou amongst women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen.";
  const ETERNAL_FATHER = "Eternal Father, I offer You the Body and Blood, Soul and Divinity of Your dearly beloved Son, Our Lord Jesus Christ, in atonement for our sins and those of the whole world.";
  const FOR_SAKE = "For the sake of His sorrowful Passion, have mercy on us and on the whole world.";

  const steps: BeadStep[] = [];
  steps.push({ label: "Sign of the Cross", prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen." });
  steps.push({ label: "Optional Opening", prayer: "You expired, O Jesus, but the source of life gushed forth for souls, and an ocean of mercy opened up for the whole world. O Fount of Life, unfathomable Divine Mercy, envelop the whole world and empty Yourself out upon us.\n\n(3x) O Blood and Water, which gushed forth from the Heart of Jesus as a fount of Mercy for us, I trust in You!" });
  steps.push({ label: "Our Father", prayer: OUR_FATHER });
  steps.push({ label: "Hail Mary", prayer: HAIL_MARY });
  steps.push({ label: "The Apostles' Creed", prayer: "I believe in God, the Father almighty, Creator of heaven and earth, and in Jesus Christ, His only Son, our Lord, who was conceived by the Holy Spirit, born of the Virgin Mary, suffered under Pontius Pilate, was crucified, died and was buried; He descended into hell; on the third day He rose again from the dead; He ascended into heaven, and is seated at the right hand of God the Father almighty; from there He will come to judge the living and the dead. I believe in the Holy Spirit, the holy catholic Church, the communion of saints, the forgiveness of sins, the resurrection of the body, and life everlasting. Amen." });

  for (let d = 1; d <= 5; d++) {
    steps.push({ label: `Decade ${d} — On the Our Father bead`, prayer: ETERNAL_FATHER });
    for (let j = 1; j <= 10; j++) {
      steps.push({ label: `Decade ${d} — ${j}/10`, prayer: FOR_SAKE });
    }
  }

  steps.push({ label: "Conclusion (3×)", prayer: "Holy God, Holy Mighty One, Holy Immortal One, have mercy on us and on the whole world. (Repeat three times.)" });
  steps.push({ label: "Closing Prayer", prayer: "Eternal God, in whom mercy is endless and the treasury of compassion inexhaustible, look kindly upon us and increase Your mercy in us, that in difficult moments we might not despair nor become despondent, but with great confidence submit ourselves to Your holy will, which is Love and Mercy itself. Amen." });
  steps.push({ label: "Sign of the Cross", prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen." });
  return steps;
}

/* -------------------------------------------------------------------------- */
/*                            CHAPLET OF ST JOSEPH                             */
/* -------------------------------------------------------------------------- */

const ST_JOSEPH_MYSTERIES: { title: string; reflection: string }[] = [
  { title: "The Annunciation to Joseph & the Flight into Egypt", reflection: "The doubt of Joseph, and the message of the Angel; the birth of Jesus, and the flight into Egypt." },
  { title: "The Poverty of Bethlehem & the joy of the Nativity", reflection: "The hardship of the stable, turned to the joy of the Saviour's birth." },
  { title: "The Circumcision & the Holy Name of Jesus", reflection: "The pain of the Child's blood, and the sweetness of naming Him 'Jesus.'" },
  { title: "The Prophecy of Simeon & the joy of salvation", reflection: "The sword foretold, and the light for the Gentiles." },
  { title: "The Life in Egypt & the fall of the idols", reflection: "The exile among strangers, comforted by the presence of God made flesh." },
  { title: "The Return from Egypt & the fear of Archelaus", reflection: "The dread of the tyrant, and the peace of the return to Nazareth." },
  { title: "The Loss & Finding of Jesus in the Temple", reflection: "The three days of anguish, turned to the joy of finding Him about His Father's business." },
];

function buildStJosephChaplet(): BeadStep[] {
  const OUR_FATHER = "Our Father, Who art in heaven, hallowed be Thy name; Thy kingdom come; Thy will be done on earth as it is in heaven. Give us this day our daily bread; and forgive us our trespasses, as we forgive those who trespass against us; and lead us not into temptation, but deliver us from evil. Amen.";
  const HAIL_MARY = "Hail Mary, full of grace, the Lord is with thee. Blessed art thou amongst women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen.";
  const steps: BeadStep[] = [];
  steps.push({ label: "Sign of the Cross", prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen." });
  steps.push({ label: "Opening", prayer: "O God, come to my assistance. O Lord, make haste to help me. Glory be… This chaplet honors the Seven Sorrows and Seven Joys of St. Joseph, praying an Our Father and a Hail Mary for each." });
  ST_JOSEPH_MYSTERIES.forEach((m, i) => {
    steps.push({ label: `${i + 1}. Sorrow & Joy — ${m.title}`, prayer: m.reflection });
    steps.push({ label: "Our Father", prayer: OUR_FATHER });
    steps.push({ label: "Hail Mary", prayer: HAIL_MARY });
  });
  steps.push({ label: "Antiphon", prayer: "V. Pray for us, O holy Joseph.\nR. That we may be made worthy of the promises of Christ." });
  steps.push({ label: "Closing Prayer", prayer: "O God, who in Your ineffable providence chose blessed Joseph to be the spouse of Your most holy Mother, grant, we beseech You, that we may deserve to have him for our intercessor in heaven, whom we venerate as our protector on earth. Who lives and reigns forever. Amen." });
  steps.push({ label: "Sign of the Cross", prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen." });
  return steps;
}

/* -------------------------------------------------------------------------- */
/*                    THE FRANCISCAN CROWN (SERAPHIC ROSARY)                   */
/* -------------------------------------------------------------------------- */

const SEVEN_JOYS_OF_MARY = [
  "The Annunciation — Gabriel greets Mary, and the Word is made flesh in her.",
  "The Visitation — Mary hastens to Elizabeth, and Elizabeth calls her blessed.",
  "The Nativity — Mary brings forth her Son, and lays Him in the manger.",
  "The Adoration of the Magi — the nations come to worship the newborn King.",
  "The Finding of Jesus in the Temple — after three days, joy in finding Him.",
  "The Resurrection — Mary rejoices to see her Son risen from the dead.",
  "The Assumption & Coronation — Mary is taken up and crowned Queen of Heaven.",
];

function buildFranciscanCrown(): BeadStep[] {
  const OUR_FATHER = "Our Father, Who art in heaven, hallowed be Thy name; Thy kingdom come; Thy will be done on earth as it is in heaven. Give us this day our daily bread; and forgive us our trespasses, as we forgive those who trespass against us; and lead us not into temptation, but deliver us from evil. Amen.";
  const HAIL_MARY = "Hail Mary, full of grace, the Lord is with thee. Blessed art thou amongst women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen.";
  const GLORY = "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.";
  const steps: BeadStep[] = [];
  steps.push({ label: "Sign of the Cross", prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen." });
  steps.push({ label: "The Seraphic Rosary", prayer: "The Franciscan Crown (Seraphic Rosary) commemorates the Seven Joys of Our Lady in seven decades. It began among the Friars Minor in the 15th century. At the end, two extra Hail Marys are added (to complete 72, the traditional years of Our Lady's life)." });
  SEVEN_JOYS_OF_MARY.forEach((joy, i) => {
    steps.push({ label: `${i + 1}. Joy — Meditation`, prayer: joy });
    steps.push({ label: "Our Father", prayer: OUR_FATHER });
    for (let j = 1; j <= 10; j++) {
      steps.push({ label: `Decade ${i + 1} — Hail Mary ${j}/10`, prayer: HAIL_MARY });
    }
    steps.push({ label: "Glory Be", prayer: GLORY });
  });
  steps.push({ label: "Two Hail Marys", prayer: "Pray two more Hail Marys to complete the seventy-two, in honor of the years of Our Lady's earthly life.\n\n" + HAIL_MARY });
  steps.push({ label: "Our Father & Hail Mary", prayer: "Conclude with one Our Father and one Hail Mary for the intentions of the Holy Father.\n\n" + OUR_FATHER });
  steps.push({ label: "Closing Prayer", prayer: "O Mary, Queen of the Seraphim, who didst rejoice in these seven joys, obtain for us to share thy gladness now by grace, and hereafter in the joy of heaven. Through Christ our Lord. Amen." });
  steps.push({ label: "Sign of the Cross", prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen." });
  return steps;
}

/* -------------------------------------------------------------------------- */
/*                                 REGISTRY                                    */
/* -------------------------------------------------------------------------- */

function renewalSteps(prayer: string): BeadStep[] {
  return [
    {
      label: "Sign of the Cross",
      prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
    },
    { label: "Act of Renewal", prayer },
  ];
}

export const CHAPLETS: Record<ChapletKey, Chaplet> = {
  divine_mercy: {
    key: "divine_mercy",
    title: "Chaplet of Divine Mercy",
    subtitle: "Revealed to St. Faustina · prayed on rosary beads",
    color: "#1E73BE",
    icon: "water-outline",
    duration: "~10 min",
    steps: buildDivineMercy(),
    good_work_for_today:
      "Perform one work of mercy today — a kind deed, a merciful word, or a prayer for someone. Where you would judge, choose mercy instead.",
    daily_motto: "Jesus, I trust in You.",
    note:
      "Prayed on ordinary rosary beads. It is especially powerful at 3:00 p.m., the Hour of Great Mercy, the hour of the Lord's death.",
  },
  st_michael: {
    key: "st_michael",
    title: "Chaplet of St. Michael",
    subtitle: "Nine choirs of angels · defender in battle",
    color: "#B22234",
    icon: "shield-checkmark-outline",
    duration: "~15 min",
    steps: buildStMichael(),
    good_work_for_today:
      "Defend someone today who cannot defend themselves — speak well of an absent person who is being spoken ill of, or quietly intercede for someone facing trial.",
    daily_motto: "Quis ut Deus? — Who is like God?",
  },
  guardian_angel: {
    key: "guardian_angel",
    title: "Chaplet of the Holy Guardian Angel",
    subtitle: "To light and guard, to rule and guide",
    color: "#4A7C8C",
    icon: "sparkles-outline",
    duration: "~10 min",
    steps: buildGuardianAngel(),
    good_work_for_today:
      "Pause once today and thank your Guardian Angel by name of office — for lighting, guarding, ruling, and guiding you — then do one small kindness for someone who feels unseen.",
    daily_motto: "Ever this day be at my side.",
  },
  immaculate_heart: {
    key: "immaculate_heart",
    title: "Chaplet of the Immaculate Heart of Mary",
    subtitle: "Twelve stars · refuge for sinners",
    color: "#3F62A8",
    icon: "heart-outline",
    duration: "~10 min",
    steps: buildImmaculateHeart(),
    good_work_for_today:
      "Offer a hidden act of charity for someone today — give a small sacrifice, kept secret between you and the Lord, in union with the Immaculate Heart.",
    daily_motto: "Through her, to Him.",
  },
  sacred_heart: {
    key: "sacred_heart",
    title: "Chaplet of the Sacred Heart of Jesus",
    subtitle: "33 invocations · the Heart that loves us still",
    color: "#9E1B1B",
    icon: "flame-outline",
    duration: "~12 min",
    steps: buildSacredHeart(),
    good_work_for_today:
      "Spend ten unhurried minutes today in silent prayer before a crucifix or image of the Sacred Heart. Bring Him the heaviness of your day.",
    daily_motto: "Most Sacred Heart of Jesus, I trust in Thee.",
  },
  st_lucy: {
    key: "st_lucy",
    title: "Chaplet of St. Lucy",
    subtitle: "Virgin & martyr · light against the dark",
    color: "#C9A227",
    icon: "sunny-outline",
    duration: "~8 min",
    steps: buildStLucy(),
    good_work_for_today:
      "Bring light to someone in darkness — write a brief message of hope to a friend who is struggling, or sit with someone alone today.",
    daily_motto: "Walk while you have the light.",
  },
  st_padre_pio: {
    key: "st_padre_pio",
    title: "Chaplet of St. Padre Pio",
    subtitle: "Six Glory Bes · pray, hope, don't worry",
    color: "#5D4037",
    icon: "rose-outline",
    duration: "~10 min",
    steps: buildStPadrePio(),
    good_work_for_today:
      "Carry one anxiety to God today without speaking of it to anyone else. Replace worry with prayer each time the thought returns.",
    daily_motto: "Pray, hope, and don't worry.",
  },
  peter_and_paul: {
    key: "peter_and_paul",
    title: "Chaplet of Sts. Peter and Paul",
    subtitle: "Apostolic pillars · the rock and the herald",
    color: "#2A5A3B",
    icon: "key-outline",
    duration: "~12 min",
    steps: buildPeterAndPaul(),
    good_work_for_today:
      "Speak of Christ to someone today, however briefly — a kind word, a question, a small witness. As Peter and Paul did, hand the faith forward.",
    daily_motto: "I have kept the faith.",
  },
  st_joseph_renewal: {
    key: "st_joseph_renewal",
    title: "Daily Consecration to St. Joseph — Renewal",
    subtitle: "Renew your entrustment to the Guardian of the Redeemer",
    color: "#6B4E8E",
    icon: "shield-half-outline",
    duration: "~3 min",
    steps: renewalSteps(
      "O glorious St. Joseph, faithful guardian of Jesus and chaste spouse of the Blessed Virgin Mary, I renew today my consecration to you. To you I entrust my body and my soul, my labors and my rest, my life and my death. Be my father, my protector, and my guide in the way of salvation. Teach me to love Jesus as you loved Him, to serve in silence, to work with integrity, and to trust completely in the Father's providence. Obtain for me a great purity of heart, a fervent love of the interior life, and the grace of a holy death in the arms of Jesus and Mary. St. Joseph, to you I belong; never let me be separated from you. Amen.",
    ),
    good_work_for_today:
      "Do one hidden task today with care and without complaint — an act of quiet, Josephine labor offered for your family or community.",
    daily_motto: "Ite ad Ioseph — Go to Joseph.",
    note:
      "This renewal is usually prayed by those who have already consecrated themselves to St. Joseph. If you haven't yet, consider doing so — you can begin the 33-day St. Joseph Consecration Challenge in the Challenges section.",
  },
  marian_renewal: {
    key: "marian_renewal",
    title: "Daily Marian Consecration — Renewal",
    subtitle: "Renew your total entrustment to Jesus through Mary",
    color: "#3F62A8",
    icon: "heart-half-outline",
    duration: "~3 min",
    steps: renewalSteps(
      "O Mary, Immaculate Mother of God and my Mother, I renew today my consecration to your Immaculate Heart. I am all yours, and all that I have is yours. Take me wholly to yourself: my body and my soul, my thoughts, my words, and my deeds, that through your hands every gift may be offered to Jesus. Form me into the image of your Son, keep me ever close to His Sacred Heart, and lead me safely home to Heaven. My Queen and my Mother, I am all yours; do with me whatever you will. Totus tuus — I am all yours. Amen.",
    ),
    good_work_for_today:
      "Offer one small hidden sacrifice today through Our Lady's hands — kept secret between you and the Lord, in union with her Immaculate Heart.",
    daily_motto: "Totus tuus — Through her, to Him.",
    note:
      "This renewal is usually prayed by those who have already made a Marian consecration. If you haven't yet, consider doing so — you can begin the 33-day Marian Consecration Challenge in the Challenges section.",
  },
  sacred_heart_renewal: {
    key: "sacred_heart_renewal",
    title: "Daily Consecration to the Sacred Heart — Renewal",
    subtitle: "Renew your self-offering to the Heart of Jesus",
    color: "#9E1B1B",
    icon: "flame",
    duration: "~3 min",
    steps: renewalSteps(
      "O most Sacred Heart of Jesus, fountain of every blessing, I renew today my consecration to You. I give You my heart in return for the love with which You have loved me. Reign in my mind by Your truth, in my will by Your law, and in my heart by Your love. Make my heart meek and humble like unto Your own. Console me in trial, defend me in temptation, sanctify my work, and at the hour of my death receive me into the refuge of Your wounded Heart. Most Sacred Heart of Jesus, I place all my trust in You; in You alone do I find my rest. Amen.",
    ),
    good_work_for_today:
      "Make one act of reparation today — a small kindness offered to console the Heart of Jesus where He is forgotten or rejected.",
    daily_motto: "Most Sacred Heart of Jesus, I trust in Thee.",
    note:
      "This renewal is usually prayed by those who have already consecrated themselves to the Sacred Heart of Jesus. If you haven't yet, consider doing so — you can begin the 33-day Sacred Heart Consecration Challenge in the Challenges section.",
  },
  st_joseph_chaplet: {
    key: "st_joseph_chaplet",
    title: "Chaplet of St. Joseph",
    subtitle: "Seven Sorrows & Joys of the Guardian of the Redeemer",
    color: "#6B4E8E",
    icon: "hammer-outline",
    duration: "~12 min",
    steps: buildStJosephChaplet(),
    good_work_for_today:
      "Do one hidden, patient work today in Joseph's spirit — labor offered quietly for your family, without seeking notice.",
    daily_motto: "Ite ad Ioseph — Go to Joseph.",
  },
  franciscan_crown: {
    key: "franciscan_crown",
    title: "The Franciscan Crown (Seraphic Rosary)",
    subtitle: "Seven decades of Our Lady's Joys — the Franciscan tradition",
    color: "#5B4A2E",
    icon: "flower-outline",
    duration: "~20 min",
    steps: buildFranciscanCrown(),
    good_work_for_today:
      "Bring a small joy to someone today — a glad word, a kindness done cheerfully — in honor of Our Lady's gladness.",
    daily_motto: "Rejoice with Mary in her seven joys.",
  },
};

export const CHAPLET_ORDER: ChapletKey[] = [
  "divine_mercy",
  "st_michael",
  "guardian_angel",
  "immaculate_heart",
  "sacred_heart",
  "st_lucy",
  "st_padre_pio",
  "peter_and_paul",
  "st_joseph_chaplet",
  "franciscan_crown",
  "st_joseph_renewal",
  "marian_renewal",
  "sacred_heart_renewal",
];

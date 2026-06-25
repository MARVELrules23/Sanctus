/**
 * Rosary engine: chooses today's mystery & exposes prayer sequence.
 *
 * Mystery rotation (traditional):
 *   Monday    → Joyful
 *   Tuesday   → Sorrowful
 *   Wednesday → Glorious
 *   Thursday  → Luminous
 *   Friday    → Sorrowful
 *   Saturday  → Joyful
 *   Sunday    → Glorious (default), Joyful in Advent/Christmas, Sorrowful in Lent
 */

export type Mystery = {
  name: string;
  fruit: string;
  reflection: string;
};

export type MysterySet = {
  key: "joyful" | "sorrowful" | "glorious" | "luminous";
  title: string;
  color: string;
  mysteries: Mystery[];
  /** Practical virtue/action to live the mystery set today */
  good_work_for_today: string;
  /** Short motto for the day */
  daily_motto: string;
};

export const MYSTERY_SETS: Record<MysterySet["key"], MysterySet> = {
  joyful: {
    key: "joyful",
    title: "Joyful Mysteries",
    color: "#D4AF37",
    mysteries: [
      { name: "The Annunciation", fruit: "Humility", reflection: "Mary's fiat — let it be done unto me according to thy word." },
      { name: "The Visitation", fruit: "Charity", reflection: "Mary hastens to serve Elizabeth; charity in motion." },
      { name: "The Nativity", fruit: "Poverty of Spirit", reflection: "The King of Kings born in a manger." },
      { name: "The Presentation", fruit: "Obedience", reflection: "The Holy Family fulfills the Law in the Temple." },
      { name: "Finding in the Temple", fruit: "Piety", reflection: "I must be about my Father's business." },
    ],
    good_work_for_today:
      "Visit or serve a family member today — do one quiet errand, write a note, or pray for them by name. Imitate Mary's haste to serve Elizabeth.",
    daily_motto: "Be it done unto me according to Thy word.",
  },
  sorrowful: {
    key: "sorrowful",
    title: "Sorrowful Mysteries",
    color: "#9E1B1B",
    mysteries: [
      { name: "Agony in the Garden", fruit: "Sorrow for Sin", reflection: "Not my will, but Thine be done." },
      { name: "Scourging at the Pillar", fruit: "Purity", reflection: "He bore the stripes by which we are healed." },
      { name: "Crowning with Thorns", fruit: "Moral Courage", reflection: "The King of Glory mocked for love of us." },
      { name: "Carrying of the Cross", fruit: "Patience", reflection: "Take up your cross and follow Me." },
      { name: "Crucifixion and Death", fruit: "Self-Denial", reflection: "It is finished. Greater love hath no man than this." },
    ],
    good_work_for_today:
      "Take up one small cross today without complaint — skip a comfort (a meal between meals, a screen, a comfort food) and offer it for someone who is suffering.",
    daily_motto: "Not my will, but Thine be done.",
  },
  glorious: {
    key: "glorious",
    title: "Glorious Mysteries",
    color: "#1C2841",
    mysteries: [
      { name: "The Resurrection", fruit: "Faith", reflection: "Why seek ye the living among the dead?" },
      { name: "The Ascension", fruit: "Hope", reflection: "I go to prepare a place for you." },
      { name: "Descent of the Holy Spirit", fruit: "Love of God", reflection: "Tongues of fire upon the Apostles at Pentecost." },
      { name: "Assumption of Mary", fruit: "Grace of a Holy Death", reflection: "She is taken up, body and soul, into glory." },
      { name: "Coronation of Mary", fruit: "Devotion to Mary", reflection: "A great sign appeared in heaven: a woman crowned with twelve stars." },
    ],
    good_work_for_today:
      "Bring resurrection news to someone today — speak a word of hope to a person heavy with discouragement. Hope is contagious.",
    daily_motto: "He is risen — He is risen indeed.",
  },
  luminous: {
    key: "luminous",
    title: "Luminous Mysteries",
    color: "#2A5A3B",
    mysteries: [
      { name: "Baptism in the Jordan", fruit: "Openness to the Holy Spirit", reflection: "This is My beloved Son; listen to Him." },
      { name: "Wedding at Cana", fruit: "Faith in Mary's Intercession", reflection: "Do whatever He tells you." },
      { name: "Proclamation of the Kingdom", fruit: "Conversion", reflection: "Repent, and believe in the Gospel." },
      { name: "The Transfiguration", fruit: "Desire for Holiness", reflection: "His face shone like the sun." },
      { name: "Institution of the Eucharist", fruit: "Eucharistic Love", reflection: "This is My Body, given for you." },
    ],
    good_work_for_today:
      "Do whatever He tells you. Pick the one duty you've been putting off — a hard conversation, a long-overdue task — and do it today, for love.",
    daily_motto: "Do whatever He tells you.",
  },
};

export function mysteryForDate(d: Date, season?: string): MysterySet {
  const dow = d.getDay(); // Sun=0
  if (dow === 0) {
    if (season === "Advent" || season === "Christmas") return MYSTERY_SETS.joyful;
    if (season === "Lent") return MYSTERY_SETS.sorrowful;
    return MYSTERY_SETS.glorious;
  }
  if (dow === 1) return MYSTERY_SETS.joyful;
  if (dow === 2) return MYSTERY_SETS.sorrowful;
  if (dow === 3) return MYSTERY_SETS.glorious;
  if (dow === 4) return MYSTERY_SETS.luminous;
  if (dow === 5) return MYSTERY_SETS.sorrowful;
  return MYSTERY_SETS.joyful; // Saturday
}

/**
 * Each decade: 1 Our Father + 10 Hail Marys + 1 Glory Be + 1 Fatima prayer.
 * We treat the decade as 13 "beads" (OF + 10 HMs + GB + Fatima) plus the
 * mystery announcement. Total per rosary: 5 decades × 13 = 65 beads,
 * plus opening (Sign + Apostles' Creed + OF + 3 HMs + GB) ≈ 6 beads.
 */
export type BeadStep = {
  label: string;
  prayer: string;
};

export function openingBeads(): BeadStep[] {
  return [
    { label: "Sign of the Cross", prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen." },
    {
      label: "Apostles' Creed",
      prayer:
        "I believe in God, the Father almighty, Creator of heaven and earth, and in Jesus Christ, His only Son, our Lord, who was conceived by the Holy Spirit, born of the Virgin Mary, suffered under Pontius Pilate, was crucified, died and was buried; He descended into hell; on the third day He rose again from the dead; He ascended into heaven, and is seated at the right hand of God the Father almighty; from there He will come to judge the living and the dead. I believe in the Holy Spirit, the holy catholic Church, the communion of saints, the forgiveness of sins, the resurrection of the body, and life everlasting. Amen.",
    },
    { label: "Our Father", prayer: "Our Father, Who art in heaven, hallowed be Thy name; Thy kingdom come; Thy will be done on earth as it is in heaven. Give us this day our daily bread; and forgive us our trespasses, as we forgive those who trespass against us; and lead us not into temptation, but deliver us from evil. Amen." },
    { label: "Hail Mary (for Faith)", prayer: "Hail Mary, full of grace, the Lord is with thee. Blessed art thou amongst women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen." },
    { label: "Hail Mary (for Hope)", prayer: "Hail Mary, full of grace, the Lord is with thee. Blessed art thou amongst women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen." },
    { label: "Hail Mary (for Charity)", prayer: "Hail Mary, full of grace, the Lord is with thee. Blessed art thou amongst women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen." },
    { label: "Glory Be", prayer: "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen." },
  ];
}

export function decadeBeads(idx: number, mystery: Mystery): BeadStep[] {
  const beads: BeadStep[] = [];
  beads.push({
    label: `${idx + 1}. ${mystery.name}`,
    prayer: `${mystery.reflection}\nFruit: ${mystery.fruit}.`,
  });
  beads.push({ label: "Our Father", prayer: "Our Father, Who art in heaven, hallowed be Thy name; Thy kingdom come; Thy will be done on earth as it is in heaven. Give us this day our daily bread; and forgive us our trespasses, as we forgive those who trespass against us; and lead us not into temptation, but deliver us from evil. Amen." });
  for (let i = 1; i <= 10; i++) {
    beads.push({ label: `Hail Mary (${i}/10)`, prayer: "Hail Mary, full of grace, the Lord is with thee. Blessed art thou amongst women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen." });
  }
  beads.push({ label: "Glory Be", prayer: "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen." });
  beads.push({
    label: "Fatima Prayer",
    prayer:
      "O my Jesus, forgive us our sins, save us from the fires of hell. Lead all souls to heaven, especially those in most need of Thy mercy.",
  });
  return beads;
}

export function closingBeads(): BeadStep[] {
  return [
    {
      label: "Hail Holy Queen",
      prayer:
        "Hail, holy Queen, Mother of mercy, our life, our sweetness and our hope. To thee do we cry, poor banished children of Eve; to thee do we send up our sighs, mourning and weeping in this valley of tears. Turn then, most gracious advocate, thine eyes of mercy toward us; and after this our exile, show unto us the blessed fruit of thy womb, Jesus. O clement, O loving, O sweet Virgin Mary. Pray for us, O holy Mother of God, that we may be made worthy of the promises of Christ. Amen.",
    },
    { label: "Sign of the Cross", prayer: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen." },
  ];
}

export function fullRosary(set: MysterySet): BeadStep[] {
  const steps: BeadStep[] = [...openingBeads()];
  set.mysteries.forEach((m, i) => steps.push(...decadeBeads(i, m)));
  steps.push(...closingBeads());
  return steps;
}

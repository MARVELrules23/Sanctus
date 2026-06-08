/**
 * Scripture verses + saint quotes for the Meditation screen.
 * One rotates into view roughly every 25 seconds while audio plays.
 */

export interface SanctuaryQuote {
  text: string;
  source: string;          // book/chapter:verse, or saint name + work
  kind: "scripture" | "saint";
}

export const SANCTUARY_QUOTES: SanctuaryQuote[] = [
  // ───── Scripture ─────
  {
    text: "Be still, and know that I am God.",
    source: "Psalm 46:10",
    kind: "scripture",
  },
  {
    text: "The Lord is my shepherd; I shall not want.",
    source: "Psalm 23:1",
    kind: "scripture",
  },
  {
    text: "Come to me, all who labor and are heavy laden, and I will give you rest.",
    source: "Matthew 11:28",
    kind: "scripture",
  },
  {
    text: "In returning and rest you shall be saved; in quietness and trust shall be your strength.",
    source: "Isaiah 30:15",
    kind: "scripture",
  },
  {
    text: "My soul finds rest in God alone; my salvation comes from him.",
    source: "Psalm 62:1",
    kind: "scripture",
  },
  {
    text: "Peace I leave with you; my peace I give to you.",
    source: "John 14:27",
    kind: "scripture",
  },
  {
    text: "He leads me beside still waters; he restores my soul.",
    source: "Psalm 23:2–3",
    kind: "scripture",
  },
  {
    text: "Cast your burden on the Lord, and he will sustain you.",
    source: "Psalm 55:22",
    kind: "scripture",
  },
  {
    text: "Do not be anxious about anything, but in everything by prayer let your requests be made known to God.",
    source: "Philippians 4:6",
    kind: "scripture",
  },
  {
    text: "Whatever is true, whatever is honorable, whatever is just — think about these things.",
    source: "Philippians 4:8",
    kind: "scripture",
  },

  // ───── Saints ─────
  {
    text: "You have made us for yourself, O Lord, and our heart is restless until it rests in you.",
    source: "St. Augustine — Confessions",
    kind: "saint",
  },
  {
    text: "Let nothing disturb you. Let nothing frighten you. All things are passing. God alone suffices.",
    source: "St. Teresa of Ávila",
    kind: "saint",
  },
  {
    text: "Silence is the language God speaks, and everything else is a bad translation.",
    source: "Thomas Keating",
    kind: "saint",
  },
  {
    text: "Prayer is nothing else than being on terms of friendship with God.",
    source: "St. Teresa of Ávila",
    kind: "saint",
  },
  {
    text: "Do small things with great love.",
    source: "St. Mother Teresa",
    kind: "saint",
  },
  {
    text: "Charity is the soul of holiness; it is the queen of virtues.",
    source: "St. Francis de Sales",
    kind: "saint",
  },
  {
    text: "Without prayer, nothing good is done. God's works are done with our hands joined.",
    source: "St. John Bosco",
    kind: "saint",
  },
  {
    text: "Where there is no love, put love — and you will find love.",
    source: "St. John of the Cross",
    kind: "saint",
  },
  {
    text: "The soul that walks in love neither rests nor grows tired.",
    source: "St. John of the Cross",
    kind: "saint",
  },
  {
    text: "It is in giving that we receive; it is in pardoning that we are pardoned.",
    source: "St. Francis of Assisi",
    kind: "saint",
  },
  {
    text: "Joy is the infallible sign of the presence of God.",
    source: "Léon Bloy",
    kind: "saint",
  },
  {
    text: "Real love is always creative — and that is why prayer is creative.",
    source: "St. John Paul II",
    kind: "saint",
  },
];

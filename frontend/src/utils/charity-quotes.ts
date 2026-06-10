/**
 * Catholic quotes on charity, almsgiving, and love of the poor —
 * from Saints, Blesseds, Venerables, and Doctors of the Church.
 *
 * Used at the bottom of the Charity detail screen (`/charities/[id]`)
 * to anchor the act of giving in the Church's living tradition.
 */

export interface CharityQuote {
  text: string;
  /** "St. Name", "Bl. Name", "Ven. Name", "Servant of God Name" */
  source: string;
  /** Optional book / sermon / encyclical for attribution */
  context?: string;
}

export const CHARITY_QUOTES: CharityQuote[] = [
  // ─── Doctors & Fathers of the Church ───
  {
    text: "Charity is the bond of perfection. Without it, the rich man is poor; with it, the poor man is rich.",
    source: "St. Augustine of Hippo",
    context: "Sermon 350",
  },
  {
    text: "Not to enable the poor to share in our goods is to steal from them and deprive them of life. The goods we possess are not ours, but theirs.",
    source: "St. John Chrysostom",
    context: "Homily on Lazarus",
  },
  {
    text: "The bread which you do not use is the bread of the hungry; the garment hanging in your wardrobe is the garment of the one who is naked.",
    source: "St. Basil the Great",
    context: "Sermon to the Rich",
  },
  {
    text: "If you wish to be perfect, give what you have to the poor and you will have treasure in heaven.",
    source: "St. Ambrose of Milan",
  },
  {
    text: "Charity is the form of all the virtues. It is the soul of every other virtue.",
    source: "St. Thomas Aquinas",
    context: "Summa Theologiae II-II, q.23",
  },

  // ─── Saints of Charity ───
  {
    text: "It is not enough to give bread. We must give the bread of love, the bread of dignity.",
    source: "St. Vincent de Paul",
  },
  {
    text: "You will find out that charity is a heavy burden to carry, heavier than the bowl of soup and the full basket. But you will keep your gentleness and your smile.",
    source: "St. Vincent de Paul",
  },
  {
    text: "Spread love everywhere you go. Let no one ever come to you without leaving happier.",
    source: "St. Teresa of Calcutta",
  },
  {
    text: "Not all of us can do great things. But we can do small things with great love.",
    source: "St. Teresa of Calcutta",
  },
  {
    text: "The fruit of love is service, which is compassion in action.",
    source: "St. Teresa of Calcutta",
  },
  {
    text: "Charity is certainly greater than any rule. Moreover, all rules must lead to charity.",
    source: "St. Vincent de Paul",
  },
  {
    text: "He who distributes the milk of human kindness cannot help but receive it again upon his own lips.",
    source: "St. Francis de Sales",
    context: "Introduction to the Devout Life",
  },
  {
    text: "Charity is patient, is kind. Without it, our works are as nothing.",
    source: "St. Paul the Apostle",
    context: "1 Corinthians 13:4",
  },
  {
    text: "Remember that you have only one soul; that you have only one death to die; that you have only one life. If you do this, there will be many things about which you care nothing.",
    source: "St. Teresa of Ávila",
  },

  // ─── Modern Saints, Blesseds, Venerables ───
  {
    text: "Whenever a Christian sees a poor person, he must see in him the face of Christ.",
    source: "St. John Paul II",
    context: "Homily, 1985",
  },
  {
    text: "Even the smallest act of love is a stone laid in the foundation of God's Kingdom.",
    source: "Bl. Pier Giorgio Frassati",
  },
  {
    text: "I see Jesus in every human being. I say to myself, this is hungry Jesus, I must feed him.",
    source: "St. Teresa of Calcutta",
  },
  {
    text: "The measure of love is to love without measure.",
    source: "St. Francis de Sales",
  },
  {
    text: "The poor are not a problem; they are a resource from which to draw to welcome and live the essence of the Gospel.",
    source: "Pope Francis",
    context: "Message for the World Day of the Poor",
  },
  {
    text: "Charity is the cement which binds communities to God and persons to one another.",
    source: "Ven. Fulton J. Sheen",
  },
  {
    text: "Love is repaid by love alone.",
    source: "St. Thérèse of Lisieux",
  },
  {
    text: "I have found the paradox, that if you love until it hurts, there can be no more hurt, only more love.",
    source: "St. Teresa of Calcutta",
  },
  {
    text: "Real charity does the most good to those who receive it, and asks the least in return.",
    source: "Ven. Solanus Casey",
  },
  {
    text: "Do not be afraid of holiness. It will take away none of your energy, vitality, or joy.",
    source: "Pope Francis",
    context: "Gaudete et Exsultate",
  },
  {
    text: "I would rather make mistakes in kindness than work miracles in unkindness.",
    source: "St. Teresa of Calcutta",
  },
  {
    text: "It is in giving that we receive; it is in pardoning that we are pardoned; it is in dying that we are born to eternal life.",
    source: "St. Francis of Assisi",
    context: "Peace Prayer",
  },
  {
    text: "Start by doing what's necessary; then do what's possible; and suddenly you are doing the impossible.",
    source: "St. Francis of Assisi",
  },
  {
    text: "If you really want to love Jesus, first learn to suffer, because suffering teaches you to love.",
    source: "St. Gemma Galgani",
  },
  {
    text: "The poor person is a scandal who is also our salvation, for in him Christ comes to meet us.",
    source: "Bl. Frédéric Ozanam",
    context: "Founder of the Society of St. Vincent de Paul",
  },
  {
    text: "When you have given alms, you have done nothing. You owe a debt of love which only love can repay.",
    source: "St. Augustine of Hippo",
  },
];

/**
 * Pick a deterministic quote for a given key (e.g. a charity_id) so the
 * same charity always shows the same quote, but different charities show
 * different quotes. Falls back to a random pick when no key is provided.
 */
export function pickCharityQuote(key?: string | null): CharityQuote {
  if (!key) {
    const i = Math.floor(Math.random() * CHARITY_QUOTES.length);
    return CHARITY_QUOTES[i];
  }
  // Simple stable hash → index
  let h = 0;
  for (let i = 0; i < key.length; i++) {
    h = (h * 31 + key.charCodeAt(i)) | 0;
  }
  const idx = Math.abs(h) % CHARITY_QUOTES.length;
  return CHARITY_QUOTES[idx];
}

/**
 * Same deterministic pick algorithm but over an arbitrary pool (e.g. quotes
 * fetched from the admin-curated API). Returns null when the pool is empty.
 */
export function pickQuoteFromPool<T extends CharityQuote>(
  pool: T[],
  key?: string | null,
): T | null {
  if (!pool || pool.length === 0) return null;
  if (!key) {
    return pool[Math.floor(Math.random() * pool.length)];
  }
  let h = 0;
  for (let i = 0; i < key.length; i++) {
    h = (h * 31 + key.charCodeAt(i)) | 0;
  }
  return pool[Math.abs(h) % pool.length];
}

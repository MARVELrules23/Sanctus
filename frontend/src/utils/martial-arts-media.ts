/**
 * Curated film / series / anime recommendations per discipline.
 * Each entry highlights a work where the martial art is a CENTRAL element.
 * `catholic: true` flags works with significant Catholic / Christian
 * themes (devout protagonist, Catholic redemption arc, priest as moral
 * compass, etc.) — used by the UI to surface a small cross icon.
 */

export type MediaKind = "Film" | "Series" | "Anime" | "Documentary";

export type MediaRec = {
  title: string;
  year: number;
  kind: MediaKind;
  /** Optional language / origin tag, e.g. "Japan", "Thailand" */
  origin?: string;
  /** Strong Catholic / Christian themes present */
  catholic: boolean;
  /** 1-2 sentence note on how the discipline is central + any Catholic angle */
  why: string;
};

export const MARTIAL_ARTS_MEDIA: Record<string, MediaRec[]> = {
  /* --------------------------------- BJJ -------------------------------- */
  bjj: [
    {
      title: "Redbelt",
      year: 2008,
      kind: "Film",
      catholic: false,
      why: "David Mamet's drama on a BJJ instructor whose code of honor (\"there's always an escape\") drives every scene — pure jiu-jitsu philosophy on screen.",
    },
    {
      title: "Choke",
      year: 1999,
      kind: "Documentary",
      catholic: false,
      why: "Rickson Gracie's road to Vale Tudo Japan — the most intimate look at the Gracie family's BJJ lineage ever filmed.",
    },
    {
      title: "Warrior",
      year: 2011,
      kind: "Film",
      catholic: true,
      why: "Two estranged Catholic brothers (one a Marine, one a teacher) reunite through MMA; BJJ is at the heart of the climactic final, and the family-and-forgiveness arc reads almost like a parable.",
    },
    {
      title: "Like Water",
      year: 2011,
      kind: "Documentary",
      catholic: true,
      why: "Anderson Silva at his peak — a devout Catholic fighter whose ground game is built on BJJ. Includes him praying and reading scripture before fights.",
    },
    {
      title: "Grappler Baki",
      year: 2001,
      kind: "Anime",
      origin: "Japan",
      catholic: false,
      why: "Hyper-stylized fighting tournament series with extended arcs dedicated to BJJ specialists and Gracie-inspired characters.",
    },
    {
      title: "Kengan Ashura",
      year: 2019,
      kind: "Anime",
      origin: "Japan",
      catholic: false,
      why: "Tournament anime that gives entire fights to BJJ-style submission specialists — chokes, joint locks, and positional play depicted with technical accuracy.",
    },
  ],

  /* ------------------------------ WRESTLING ----------------------------- */
  wrestling: [
    {
      title: "Foxcatcher",
      year: 2014,
      kind: "Film",
      catholic: false,
      why: "Olympic wrestling at its highest level — the Schultz brothers' training is the spine of the film, with technique shot like ballet.",
    },
    {
      title: "Vision Quest",
      year: 1985,
      kind: "Film",
      catholic: false,
      why: "The original high-school wrestling cult classic. Weight-cuts, mat practice, and the discipline of \"making weight\" treated with reverence.",
    },
    {
      title: "Win Win",
      year: 2011,
      kind: "Film",
      catholic: false,
      why: "Small-town New Jersey wrestling coach (Paul Giamatti) takes in a runaway grappler — quiet film, deeply about virtue under pressure.",
    },
    {
      title: "The Wrestler",
      year: 2008,
      kind: "Film",
      catholic: true,
      why: "Pro wrestling, but Aronofsky frames Mickey Rourke's Randy \"The Ram\" as a Christ-figure — crucifixion-pose entrance, body broken for the crowd, explicit Passion imagery.",
    },
    {
      title: "Takedown: The DNA of GSP",
      year: 2014,
      kind: "Documentary",
      catholic: true,
      why: "GSP (a Catholic Quebecois) credits wrestling as the foundation of his MMA dominance; documentary leans into his discipline, faith, and family.",
    },
    {
      title: "Baki Hanma",
      year: 2021,
      kind: "Anime",
      origin: "Japan",
      catholic: false,
      why: "Multiple arcs dedicated to wrestling and grappling specialists, including a famous Pickle saga that's pure wrestling instinct.",
    },
  ],

  /* ------------------------------- BOXING ------------------------------- */
  boxing: [
    {
      title: "Rocky",
      year: 1976,
      kind: "Film",
      catholic: true,
      why: "The blueprint. A working-class Italian-American Catholic prays before every fight, kisses a crucifix, and faces the champion as much for dignity as victory.",
    },
    {
      title: "On the Waterfront",
      year: 1954,
      kind: "Film",
      catholic: true,
      why: "Ex-boxer Terry Malloy (Brando) finds his conscience under Father Barry's preaching — one of the most explicitly Catholic films ever made, and the boxing past haunts every frame.",
    },
    {
      title: "Cinderella Man",
      year: 2005,
      kind: "Film",
      catholic: true,
      why: "James J. Braddock, devout Catholic and Depression-era heavyweight, fought to feed his family. He attended Mass before every bout — the film honors his faith openly.",
    },
    {
      title: "Raging Bull",
      year: 1980,
      kind: "Film",
      catholic: true,
      why: "Scorsese's masterpiece on Jake LaMotta — Catholic guilt, brother-betrayal, and a final monologue (\"I am not an animal\") that quotes the prodigal son in spirit.",
    },
    {
      title: "Hajime no Ippo",
      year: 2000,
      kind: "Anime",
      origin: "Japan",
      catholic: false,
      why: "The definitive boxing anime. 126+ episodes that treat boxing technique — counters, weaving, gloves' geometry — with technical reverence.",
    },
    {
      title: "Megalo Box",
      year: 2018,
      kind: "Anime",
      origin: "Japan",
      catholic: false,
      why: "Cyberpunk boxing homage to Ashita no Joe — gritty, stripped-down, and the only mecha-boxing show that actually feels like boxing.",
    },
    {
      title: "Ashita no Joe",
      year: 1970,
      kind: "Anime",
      origin: "Japan",
      catholic: false,
      why: "The grandfather of fighting anime — a slum boxer's tragic rise. Influenced every boxing story in Japanese media since.",
    },
  ],

  /* ------------------------------ MUAY THAI ----------------------------- */
  muay_thai: [
    {
      title: "Ong-Bak",
      year: 2003,
      kind: "Film",
      origin: "Thailand",
      catholic: false,
      why: "Tony Jaa, no wires, no doubles, no CGI — pure Muay Boran and Muay Thai. The film that put Thai martial arts on the global map.",
    },
    {
      title: "The Protector (Tom-Yum-Goong)",
      year: 2005,
      kind: "Film",
      origin: "Thailand",
      catholic: false,
      why: "Tony Jaa again — includes one of the most extended Muay Thai sequences ever filmed (the famous restaurant single-take staircase fight).",
    },
    {
      title: "Beautiful Boxer",
      year: 2003,
      kind: "Film",
      origin: "Thailand",
      catholic: false,
      why: "Biopic of Nong Toom — devout Buddhist Muay Thai fighter. Includes traditional wai khru ram muay rituals in detail.",
    },
    {
      title: "Kickboxer",
      year: 1989,
      kind: "Film",
      catholic: false,
      why: "Van Damme's classic. The training montages in a Thai temple are an entry point for an entire generation into Muay Thai.",
    },
    {
      title: "Born to Fight",
      year: 2004,
      kind: "Film",
      origin: "Thailand",
      catholic: false,
      why: "Panna Rittikrai's choreography showcase — full of Muay Boran techniques rarely seen elsewhere on screen.",
    },
    {
      title: "Chocolate",
      year: 2008,
      kind: "Film",
      origin: "Thailand",
      catholic: false,
      why: "Yanin Vismitananda's debut — a young autistic woman who learns Muay Thai by watching her neighbors. Some of the cleanest knee/elbow choreography on film.",
    },
  ],

  /* ------------------------------ GŌJŪ-RYŪ ----------------------------- */
  goju_ryu: [
    {
      title: "Black Belt (Kuro-Obi)",
      year: 2007,
      kind: "Film",
      origin: "Japan",
      catholic: false,
      why: "Cast entirely with real karateka — no stunt doubles. The film engages directly with Gōjū / Gōjū-ryū lineage debates and the meaning of the black belt itself.",
    },
    {
      title: "The Karate Kid",
      year: 1984,
      kind: "Film",
      catholic: false,
      why: "Mr. Miyagi's style is Okinawan karate — the same family of arts as Gōjū-ryū. \"Wax on, wax off\" is conditioning through repetition: pure Okinawan pedagogy.",
    },
    {
      title: "Cobra Kai",
      year: 2018,
      kind: "Series",
      catholic: false,
      why: "Five seasons of competing karate philosophies (Cobra Kai aggression vs. Miyagi-Do balance) — the Miyagi-Do thread leans heavily on Okinawan-style principles.",
    },
    {
      title: "Karate Bullfighter (Champion of Death)",
      year: 1975,
      kind: "Film",
      origin: "Japan",
      catholic: false,
      why: "Sonny Chiba's portrayal of Mas Oyama (Kyokushin's founder, trained in Gōjū-ryū). The hill-running, bull-fighting training scenes are legendary.",
    },
    {
      title: "Fearless",
      year: 2006,
      kind: "Film",
      origin: "China",
      catholic: false,
      why: "Jet Li as Huo Yuanjia — though Chinese, the film's philosophy of \"hard meets soft\" mirrors the Gō-Jū (hard-soft) principle at the heart of Gōjū-ryū.",
    },
    {
      title: "Karate Shōkōshi Kohinata Minoru",
      year: 2006,
      kind: "Anime",
      origin: "Japan",
      catholic: false,
      why: "Karate-focused anime that follows a Shōrinji-kempō practitioner crossing into full-contact karate — includes detailed conditioning and kata work.",
    },
  ],

  /* --------------------------- KENDO & IAIDO --------------------------- */
  kendo: [
    {
      title: "The Twilight Samurai (Tasogare Seibei)",
      year: 2002,
      kind: "Film",
      origin: "Japan",
      catholic: false,
      why: "Yōji Yamada's quiet masterpiece — a low-ranking samurai whose swordsmanship is rooted in restraint and humility. Best portrayal of iaido ethics on film.",
    },
    {
      title: "Harakiri (Seppuku)",
      year: 1962,
      kind: "Film",
      origin: "Japan",
      catholic: false,
      why: "Kobayashi's devastating critique of bushidō hypocrisy — the kendo / kenjutsu duels are some of the most technically clean swordplay ever shot.",
    },
    {
      title: "Silence",
      year: 2016,
      kind: "Film",
      catholic: true,
      why: "Scorsese's adaptation of Endō Shūsaku's novel. Not a kendo film per se, but a Catholic masterpiece set in samurai-era Japan where the sword is the instrument of martyrdom — essential viewing for Catholic swordsmen.",
    },
    {
      title: "Seven Samurai",
      year: 1954,
      kind: "Film",
      origin: "Japan",
      catholic: false,
      why: "Kurosawa's epic — Kambei's serenity in combat and Kyūzō's silent, deadly draw embody the iaido ideal: one cut, perfectly timed, ego absent.",
    },
    {
      title: "13 Assassins",
      year: 2010,
      kind: "Film",
      origin: "Japan",
      catholic: false,
      why: "Miike's remake — forty-five minutes of continuous swordplay grounded in real kenjutsu schools. Honor-and-duty themes that Catholics will recognize as natural law.",
    },
    {
      title: "Rurouni Kenshin",
      year: 1996,
      kind: "Anime",
      origin: "Japan",
      catholic: false,
      why: "Meiji-era swordsman who has forsworn killing — a redemption arc resembling a samurai's penitential life. Hitokiri Battōsai's reverse-blade is iaido-inspired.",
    },
    {
      title: "Sword of the Stranger",
      year: 2007,
      kind: "Anime",
      origin: "Japan",
      catholic: false,
      why: "Stunning standalone film with arguably the most realistic and physically accurate sword-choreography ever animated.",
    },
    {
      title: "Bamboo Blade",
      year: 2007,
      kind: "Anime",
      origin: "Japan",
      catholic: false,
      why: "Slice-of-life anime set in a high-school kendō club — the only major anime where kendō practice, scoring, and tournament etiquette take center stage.",
    },
  ],
};

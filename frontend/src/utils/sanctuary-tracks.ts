/**
 * Curated sacred music for the Sanctuary section.
 *
 * Sources:
 *  - `mp3`  — Internet Archive public-domain recordings (verified streaming).
 *  - `youtube` — Embedded via react-native-youtube-iframe, from the public
 *    "catholic lofi" YouTube channel and friends.
 *
 * Encoding the filename portion is intentional — Archive paths contain spaces
 * and accents, and React Native's networking layer needs them URI-encoded.
 */

export type TrackKind = "piano" | "harp" | "chant" | "lofi";
export type TrackSource =
  | { kind: "mp3"; uri: string }
  | { kind: "youtube"; videoId: string };

export interface SanctuaryTrack {
  id: string;
  title: string;
  artist: string;
  kind: TrackKind;
  durationLabel?: string;        // human-readable, display only
  description: string;
  source: TrackSource;
}

const IA = "https://archive.org/download";
const enc = encodeURIComponent;

/* -------------------------------------------------------------------------- */
/*  MEDITATION  ─ piano, harp, and Gregorian chant                            */
/* -------------------------------------------------------------------------- */

export const MEDITATION_TRACKS: SanctuaryTrack[] = [
  {
    id: "med-ave-maria-piano",
    title: "Ave Maria",
    artist: "Schubert — solo piano",
    kind: "piano",
    durationLabel: "3:07",
    description: "The classic Marian prayer, rendered gently on piano.",
    source: { kind: "mp3", uri: `${IA}/Ave_Maria/${enc("AveMaria.mp3")}` },
  },
  {
    id: "med-pachelbel-canon-piano",
    title: "Canon in D",
    artist: "Pachelbel — piano",
    kind: "piano",
    durationLabel: "5:55",
    description: "Baroque devotion, simplified for solo piano.",
    source: {
      kind: "mp3",
      uri: `${IA}/pachelbell-canon-in-d-piano-1-hour/${enc("Canon in D Major.mp3")}`,
    },
  },
  {
    id: "med-clair-de-lune",
    title: "Clair de Lune",
    artist: "Debussy — solo piano",
    kind: "piano",
    durationLabel: "5:02",
    description: "Moonlight stillness — a favorite for evening prayer.",
    source: {
      kind: "mp3",
      uri: `${IA}/claude-debussy-clair-de-lune_202211/${enc("CLAUDE DEBUSSY-  CLAIR DE LUNE.mp3")}`,
    },
  },
  {
    id: "med-schubert-ave-maria-organ",
    title: "Ave Maria — Organ Voicing",
    artist: "H. Robinson Cleaver",
    kind: "harp",
    durationLabel: "2:57",
    description: "A reverent, hymn-like rendition for quiet adoration.",
    source: {
      kind: "mp3",
      uri: `${IA}/78_ave-maria_h-robinson-cleaver-schubert_gbia7024971a/${enc("Ave Maria... - H. ROBINSON CLEAVER - Schubert.mp3")}`,
    },
  },
  {
    id: "med-regina-caeli-clervaux",
    title: "Regina Caeli",
    artist: "Benedictine Monks of Clervaux",
    kind: "chant",
    durationLabel: "23:58",
    description: "Queen of Heaven — sung by Benedictines for deep meditation.",
    source: {
      kind: "mp3",
      uri: `${IA}/2-clervaux-regina-caeli-philips-6527-073/${enc("1 Clervaux - Regina caeli Philips 6527 073.mp3")}`,
    },
  },
  {
    id: "med-salve-festa-dies",
    title: "Salve Festa Dies",
    artist: "Benedictine Monks of Clervaux",
    kind: "chant",
    durationLabel: "8:04",
    description: "An Easter chant — slow, deliberate, contemplative.",
    source: {
      kind: "mp3",
      uri: `${IA}/salve-festa-dies-gregorian-chants-sung-by-the-venedictine-monks-of-clervaux/${enc("1 SALVE FESTA DIES.mp3")}`,
    },
  },
  {
    id: "med-panis-angelicus",
    title: "Panis Angelicus",
    artist: "Niels Brincker / Københavns Kammerkor",
    kind: "chant",
    durationLabel: "3:40",
    description: "Bread of the angels — a Eucharistic hymn for adoration.",
    source: {
      kind: "mp3",
      uri: `${IA}/78_panis-angelicus_niels-brincker-kbenhavns-kammerkor-rich-h-jrgensen-csar-franck_gbia7013494a/${enc("Panis Angelicus - Niels Brincker - Københavns Kammerkor.mp3")}`,
    },
  },
];

/* -------------------------------------------------------------------------- */
/*  STUDY  ─ Catholic Lofi (YouTube) + a sacred piano fallback                */
/* -------------------------------------------------------------------------- */

export const STUDY_TRACKS: SanctuaryTrack[] = [
  {
    id: "study-sacred-heart-chant",
    title: "Sacred Heart — Lofi + Gregorian",
    artist: "catholic lofi",
    kind: "lofi",
    durationLabel: "1:06",
    description: "Mellow beats woven around Sacred Heart chant — pure focus.",
    source: { kind: "youtube", videoId: "7oijjSxs1ic" },
  },
  {
    id: "study-midnight-flow",
    title: "Midnight Study Flow",
    artist: "catholic lofi",
    kind: "lofi",
    durationLabel: "1:00",
    description: "Late-night lofi for deep focus and quiet thesis nights.",
    source: { kind: "youtube", videoId: "Ob9QSVnkZps" },
  },
  {
    id: "study-247-radio",
    title: "24/7 Catholic Lofi Radio",
    artist: "catholic lofi",
    kind: "lofi",
    durationLabel: "Live",
    description: "Endless beats to study and relax to — always on.",
    source: { kind: "youtube", videoId: "2Y4PKTECpy8" },
  },
  {
    id: "study-morning-dawn",
    title: "A Bright, Beautiful Dawn",
    artist: "catholic lofi",
    kind: "lofi",
    durationLabel: "1:00",
    description: "Morning lofi to start your study session with light.",
    source: { kind: "youtube", videoId: "Dh3QINIHUkg" },
  },
  {
    id: "study-christian-lofi-yoni",
    title: "Christian Lofi — Still the Mind",
    artist: "Yoni Charis",
    kind: "lofi",
    durationLabel: "1:00",
    description: "Christian lofi to relax, chill, and still the mind.",
    source: { kind: "youtube", videoId: "wNQ1feyK9rQ" },
  },
  {
    id: "study-canon-piano-loop",
    title: "Canon in D — Long Piano Mix",
    artist: "Pachelbel (public domain)",
    kind: "piano",
    durationLabel: "5:55",
    description: "When even lofi feels too busy — pure sacred piano.",
    source: {
      kind: "mp3",
      uri: `${IA}/pachelbell-canon-in-d-piano-1-hour/${enc("Pachelbel - Canon In D.mp3")}`,
    },
  },
];

export const ALL_TRACKS: SanctuaryTrack[] = [...MEDITATION_TRACKS, ...STUDY_TRACKS];

export function trackById(id: string): SanctuaryTrack | undefined {
  return ALL_TRACKS.find((t) => t.id === id);
}

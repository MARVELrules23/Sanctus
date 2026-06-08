/**
 * Self-defense follow-up suggestions:
 * After a session is completed, we recommend a "tomorrow's focus" — a
 * complementary discipline shift that supports recovery, technical refinement,
 * or virtue formation. We also build a seed for the journal so the user can
 * record their experience without staring at a blank page.
 */

import { SDSession } from "@/src/api";

export type FollowUp = {
  /** A short title for tomorrow's focus, e.g. "Footwork only — no strikes" */
  focus_title: string;
  /** Longer description / explanation of the focus */
  focus_description: string;
  /** Suggested duration in minutes */
  duration_min: number;
  /** Companion virtue from a Catholic angle */
  virtue: string;
  /** Short scripture or saint quote */
  motto: string;
  /** Pre-filled journal title */
  journal_title: string;
  /** Pre-filled journal body with prompts */
  journal_body: string;
};

type Suggestion = Omit<FollowUp, "journal_title" | "journal_body">;

/**
 * Per-discipline rotating pool. We pick deterministically based on
 * `sessions_completed` so the user gets variety as they progress.
 */
const POOLS: Record<string, Suggestion[]> = {
  bjj: [
    {
      focus_title: "Solo movement flow",
      focus_description:
        "Twenty minutes of shrimping, technical stand-ups, bridges, and granby rolls. No partner, no resistance — just breath and clean mechanics.",
      duration_min: 20,
      virtue: "Patience",
      motto: "Slow is smooth, smooth is fast.",
    },
    {
      focus_title: "Hip mobility & breath",
      focus_description:
        "Fifteen minutes of pigeon, deep squat, and 90/90 hip switches. Long nasal breath through every pose.",
      duration_min: 15,
      virtue: "Temperance",
      motto: "The body is the soul's neighbor — care for it.",
    },
    {
      focus_title: "Mental review",
      focus_description:
        "Watch one short BJJ technique video and write three notes. Mental reps are reps. Cross-train the brain.",
      duration_min: 15,
      virtue: "Studiousness",
      motto: "Take heed how you hear.",
    },
  ],
  wrestling: [
    {
      focus_title: "Shadow wrestling",
      focus_description:
        "Twenty minutes of solo level changes, sprawls, and stance & motion. Imagine a partner. Stay heavy on the hips.",
      duration_min: 20,
      virtue: "Perseverance",
      motto: "Wrestle Jacob's prayer — I will not let Thee go until Thou bless me.",
    },
    {
      focus_title: "Posterior chain strength",
      focus_description:
        "Three rounds: 15 bodyweight squats, 10 lunges per leg, 30 seconds wall sit. Build the engine.",
      duration_min: 20,
      virtue: "Fortitude",
      motto: "Be strong, and let your heart take courage.",
    },
    {
      focus_title: "Mobility & humility",
      focus_description:
        "Fifteen minutes of hip openers and thoracic mobility. Strong men stretch quietly.",
      duration_min: 15,
      virtue: "Humility",
      motto: "He giveth grace to the humble.",
    },
  ],
  boxing: [
    {
      focus_title: "Footwork only — no strikes",
      focus_description:
        "Three rounds of 3 minutes pure footwork: pivot, angle off, in-and-out. Move like water. Don't throw a single punch.",
      duration_min: 12,
      virtue: "Discipline",
      motto: "He who controls his spirit is mightier than he that taketh a city.",
    },
    {
      focus_title: "Defense & head movement",
      focus_description:
        "Three rounds of slip-rolls, parries, and pulls in a mirror. The art of being hit — without being hit.",
      duration_min: 12,
      virtue: "Prudence",
      motto: "Be ye therefore wise as serpents, and harmless as doves.",
    },
    {
      focus_title: "Recovery & breath",
      focus_description:
        "Twenty minutes of light skipping, shoulder mobility, and box breathing (4-4-4-4). Let the body settle.",
      duration_min: 20,
      virtue: "Temperance",
      motto: "In returning and rest shall ye be saved.",
    },
  ],
  muay_thai: [
    {
      focus_title: "Hip & ankle mobility",
      focus_description:
        "Twenty minutes of deep squat sit, cossack stretch, and calf raises. Kicks come from supple hips and strong ankles.",
      duration_min: 20,
      virtue: "Temperance",
      motto: "Take care of the temple — the body is the temple of the Holy Spirit.",
    },
    {
      focus_title: "Clinch position work",
      focus_description:
        "Stand with a wall or post. Twenty quiet minutes practicing clinch posture: long arms, strong elbows, hips forward.",
      duration_min: 15,
      virtue: "Fortitude",
      motto: "Stand firm.",
    },
    {
      focus_title: "Shadow flow — long combinations",
      focus_description:
        "Three rounds of slow, deliberate shadow Muay Thai. Three-strike combinations only, with full hip turn.",
      duration_min: 12,
      virtue: "Diligence",
      motto: "Whatsoever thy hand findeth to do, do it with thy might.",
    },
  ],
  goju_ryu: [
    {
      focus_title: "Sanchin breathing",
      focus_description:
        "Ten minutes of standing Sanchin: rooted stance, slow nasal inhale, long sharp exhale. The mind quiets.",
      duration_min: 10,
      virtue: "Recollection",
      motto: "Be still, and know that I am God.",
    },
    {
      focus_title: "Kata review — slow",
      focus_description:
        "Walk through one kata three times — slowly, with full intention on each technique. Understanding before speed.",
      duration_min: 15,
      virtue: "Studiousness",
      motto: "The kingdom is like a treasure hidden in a field.",
    },
    {
      focus_title: "Iron body — gentle",
      focus_description:
        "Light forearm conditioning against your own forearms (hojo undō). Build the wrists, ankles, and shins gradually.",
      duration_min: 12,
      virtue: "Fortitude",
      motto: "Strength through gentleness.",
    },
  ],
  kendo: [
    {
      focus_title: "Suburi — 100 cuts",
      focus_description:
        "One hundred slow vertical men cuts (or bokken substitute). Each cut deliberate. Center the breath.",
      duration_min: 12,
      virtue: "Constancy",
      motto: "Many waters cannot quench love.",
    },
    {
      focus_title: "Stillness practice",
      focus_description:
        "Ten minutes of seiza or standing zanshin. Speak less today. Listen more. The sword rests in the saya.",
      duration_min: 10,
      virtue: "Silence",
      motto: "In quietness and confidence shall be your strength.",
    },
    {
      focus_title: "Footwork — suri-ashi",
      focus_description:
        "Three rounds of sliding footwork. Stay low. The feet betray the swordsman; let yours be silent.",
      duration_min: 12,
      virtue: "Discipline",
      motto: "Watch over your steps when you go to the house of God.",
    },
  ],
};

function prettyDiscipline(id: string): string {
  const map: Record<string, string> = {
    bjj: "Brazilian Jiu-Jitsu",
    wrestling: "Wrestling",
    boxing: "Boxing",
    muay_thai: "Muay Thai",
    goju_ryu: "Gōjū-ryū",
    kendo: "Kendo & Iaido",
  };
  return map[id] || id;
}

export function buildSelfDefenseFollowUp(
  session: SDSession,
  sessionsCompletedBefore: number = 0,
): FollowUp {
  const disciplineId = session.discipline_id;
  const pool = POOLS[disciplineId] || POOLS.bjj;
  // Deterministic rotation across pool — different focus each completed session
  const idx = Math.max(0, sessionsCompletedBefore) % pool.length;
  const s = pool[idx];

  const niceDiscipline = prettyDiscipline(disciplineId);
  const today = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const journal_title = `${session.discipline_name} — ${today}`;
  const intensity = session.intensity_actual || session.plan?.intensity || "moderate";
  const journal_body = [
    `Discipline: ${niceDiscipline}`,
    `Session: ${session.plan?.title || ""}`,
    `Focus: ${session.plan?.technique_focus || ""}`,
    `Duration: ${session.duration_minutes} min · Intensity: ${intensity}`,
    "",
    "How did the body feel?",
    "",
    "What was hardest? What clicked?",
    "",
    "Where did I sense the Lord today — in effort, in breath, in patience?",
    "",
    `Tomorrow's focus: ${s.focus_title}`,
    `Virtue to grow: ${s.virtue}`,
    "",
  ].join("\n");

  return {
    ...s,
    journal_title,
    journal_body,
  };
}

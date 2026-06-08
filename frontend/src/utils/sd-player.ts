import { SDSession } from "@/src/api";
import { classifyMotion, MotionMode } from "@/src/utils/motion-classifier";

export type PlayerStep = {
  /** Stable id used for keys and analytics */
  id: string;
  /** Section label e.g. "Warm-up · 1 of 4" */
  section: string;
  /** Section short tag for the top progress chip */
  sectionTag: "WARM-UP" | "DRILL" | "TECHNIQUE" | "LIVE" | "COOL-DOWN" | "REST";
  /** Step title shown big */
  title: string;
  /** Sub-detail (sets/reps/intensity) */
  detail?: string;
  /** Coach notes / cues */
  notes?: string;
  /** Bullets — used for technique block key points */
  bullets?: string[];
  /** Total seconds for this step (>= 5) */
  durationSec: number;
  /** Whether this step is a rest interval */
  isRest: boolean;
  /** SVG silhouette motion mode */
  motion: MotionMode;
  /** Whether the step requires a partner (informational) */
  requiresPartner?: boolean;
  /** Voice intro spoken at start of step (when voice is on) */
  voiceIntro: string;
  /** Pointer into source block (for badges) */
  source: "warmup" | "drill" | "drill_rest" | "technique" | "live" | "cooldown";
};

const DEFAULT_DRILL_TOTAL = 90;
const DRILL_SET_SECS = 30;
const DRILL_REST_SECS = 10;
const DRILL_SET_COUNT = 3; // default fallback when unparseable
const TECHNIQUE_REVIEW_SECS = 90;
const LIVE_APP_SECS = 60;
const MIN_STEP_SECS = 5;

/** Parse strings like "3x30s", "3 x 30 sec", "4 rounds of 1 minute", "60s". Returns {sets, secPerSet} or null. */
function parseSets(input?: string): { sets: number; secPerSet: number } | null {
  if (!input) return null;
  const text = input.toLowerCase();
  // 3x30s / 3 x 30s / 3 × 30 s
  let m = text.match(/(\d+)\s*[x×]\s*(\d+)\s*(s|sec|seconds?|m|min|minutes?)?/);
  if (m) {
    const sets = Math.max(1, parseInt(m[1], 10));
    const num = parseInt(m[2], 10);
    const unit = m[3] || "s";
    const secPerSet = unit.startsWith("m") ? num * 60 : num;
    return { sets, secPerSet };
  }
  // 3 rounds of 30s / 3 rounds of 1 minute
  m = text.match(/(\d+)\s*rounds?\s*(?:of)?\s*(\d+)\s*(s|sec|seconds?|m|min|minutes?)/);
  if (m) {
    const sets = parseInt(m[1], 10);
    const num = parseInt(m[2], 10);
    const unit = m[3];
    const secPerSet = unit.startsWith("m") ? num * 60 : num;
    return { sets, secPerSet };
  }
  // 30s only (no sets)
  m = text.match(/^\s*(\d+)\s*(s|sec|seconds?|m|min|minutes?)\s*$/);
  if (m) {
    const num = parseInt(m[1], 10);
    const unit = m[2];
    const secPerSet = unit.startsWith("m") ? num * 60 : num;
    return { sets: 1, secPerSet };
  }
  return null;
}

/** Build a flat, ordered list of player steps from an SDSession. */
export function buildPlayerSteps(session: SDSession): PlayerStep[] {
  const steps: PlayerStep[] = [];
  const plan = session.plan || ({} as SDSession["plan"]);
  const disciplineId = session.discipline_id;

  // ---- WARM-UP ----
  const warmup = plan.warmup || [];
  warmup.forEach((w, i) => {
    const dur = Math.max(MIN_STEP_SECS, w.duration_seconds || 45);
    const motion = classifyMotion(w.name, disciplineId);
    steps.push({
      id: `warmup-${i}`,
      section: `Warm-up · ${i + 1} of ${warmup.length}`,
      sectionTag: "WARM-UP",
      title: w.name,
      detail: `${dur}s`,
      notes: w.notes,
      durationSec: dur,
      isRest: false,
      motion,
      voiceIntro: `Warm up. ${w.name}. ${w.notes || "Move gently, breathe evenly."}`,
      source: "warmup",
    });
  });

  // ---- DRILLS (with set/rest cadence) ----
  const drills = plan.drills || [];
  drills.forEach((d, i) => {
    const parsed = parseSets(d.sets);
    const sets = parsed?.sets ?? DRILL_SET_COUNT;
    const secPerSet = parsed?.secPerSet ?? DRILL_SET_SECS;
    const motion = classifyMotion(d.name, disciplineId);
    const partnerNeeded = d.solo_safe === false;

    for (let s = 0; s < sets; s++) {
      steps.push({
        id: `drill-${i}-set-${s}`,
        section: `Drill ${i + 1} · set ${s + 1} of ${sets}`,
        sectionTag: "DRILL",
        title: d.name,
        detail: sets > 1 ? `Set ${s + 1}/${sets} · ${secPerSet}s` : `${secPerSet}s`,
        notes: d.notes,
        durationSec: secPerSet,
        isRest: false,
        motion,
        requiresPartner: partnerNeeded,
        voiceIntro:
          s === 0
            ? `Drill ${i + 1}. ${d.name}. ${d.notes || "Stay technical, breathe through each rep."}`
            : `Set ${s + 1}. ${d.name}.`,
        source: "drill",
      });
      // Rest between sets (not after final)
      if (s < sets - 1) {
        steps.push({
          id: `drill-${i}-rest-${s}`,
          section: `Drill ${i + 1} · rest`,
          sectionTag: "REST",
          title: "Rest",
          detail: `${DRILL_REST_SECS}s · shake out`,
          notes: "Breathe deeply. Re-set your stance.",
          durationSec: DRILL_REST_SECS,
          isRest: true,
          motion: "breathing",
          voiceIntro: "Rest. Breathe.",
          source: "drill_rest",
        });
      }
    }
  });

  // Suppress unused warning
  void DEFAULT_DRILL_TOTAL;

  // ---- TECHNIQUE BLOCK ----
  if (plan.technique_block?.name) {
    const tb = plan.technique_block;
    const motion = classifyMotion(tb.name, disciplineId);
    const bullets = (tb.key_points || []).slice(0, 5);
    steps.push({
      id: "technique",
      section: "Technique focus",
      sectionTag: "TECHNIQUE",
      title: tb.name,
      detail: `${TECHNIQUE_REVIEW_SECS}s · review the cues`,
      notes: tb.progression_hint,
      bullets,
      durationSec: TECHNIQUE_REVIEW_SECS,
      isRest: false,
      motion,
      voiceIntro: `Technique focus. ${tb.name}. ${bullets.length ? "Key points: " + bullets.slice(0, 2).join(". ") : ""}`,
      source: "technique",
    });
  }

  // ---- LIVE APPLICATION ----
  const live = plan.live_application || [];
  live.forEach((l, i) => {
    const motion = classifyMotion(l.name, disciplineId);
    steps.push({
      id: `live-${i}`,
      section: `Live application · ${i + 1} of ${live.length}`,
      sectionTag: "LIVE",
      title: l.name,
      detail: `${LIVE_APP_SECS}s`,
      notes: l.description,
      durationSec: LIVE_APP_SECS,
      isRest: false,
      motion,
      requiresPartner: !!l.requires_partner,
      voiceIntro: `Live application. ${l.name}. ${l.description || ""}`,
      source: "live",
    });
  });

  // ---- COOL-DOWN ----
  const cooldown = plan.cooldown || [];
  cooldown.forEach((c, i) => {
    const dur = Math.max(MIN_STEP_SECS, c.duration_seconds || 45);
    const motion = classifyMotion(c.name, disciplineId);
    steps.push({
      id: `cooldown-${i}`,
      section: `Cool-down · ${i + 1} of ${cooldown.length}`,
      sectionTag: "COOL-DOWN",
      title: c.name,
      detail: `${dur}s`,
      durationSec: dur,
      isRest: false,
      motion,
      voiceIntro: `Cool down. ${c.name}. Settle the breath, soften the body.`,
      source: "cooldown",
    });
  });

  return steps;
}

export function totalDurationSec(steps: PlayerStep[]): number {
  return steps.reduce((a, s) => a + s.durationSec, 0);
}

export function findStartIndexFromBlock(
  steps: PlayerStep[],
  block: "warmup" | "drill" | "technique" | "live" | "cooldown",
  itemIndex?: number,
): number {
  if (block === "drill" && typeof itemIndex === "number") {
    // Find FIRST set of that drill
    return steps.findIndex((s) => s.id === `drill-${itemIndex}-set-0`);
  }
  if (block === "warmup" && typeof itemIndex === "number") {
    return steps.findIndex((s) => s.id === `warmup-${itemIndex}`);
  }
  if (block === "live" && typeof itemIndex === "number") {
    return steps.findIndex((s) => s.id === `live-${itemIndex}`);
  }
  if (block === "cooldown" && typeof itemIndex === "number") {
    return steps.findIndex((s) => s.id === `cooldown-${itemIndex}`);
  }
  if (block === "technique") {
    return steps.findIndex((s) => s.id === "technique");
  }
  return -1;
}

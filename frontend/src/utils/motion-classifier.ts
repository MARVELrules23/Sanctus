/**
 * Classifies an exercise name into one of a small set of motion modes
 * used by the animated silhouette. Falls back to "idle" when nothing matches.
 */
export type MotionMode =
  | "idle"
  | "breathing"
  | "punch"
  | "kick"
  | "knee"
  | "elbow"
  | "squat"
  | "sprawl"
  | "shrimp"
  | "sword_cut"
  | "stretch";

const PATTERNS: Array<{ mode: MotionMode; keywords: string[] }> = [
  // Breath / warmup centering
  {
    mode: "breathing",
    keywords: ["breath", "sanchin", "tensho", "ibuki", "center", "meditat", "kiai", "zanshin"],
  },
  // Striking — hands
  {
    mode: "punch",
    keywords: [
      "punch",
      "jab",
      "cross",
      "hook",
      "uppercut",
      "straight",
      "shadow box",
      "shadowbox",
      "combo",
      "1-2",
      "1,2",
      "guard",
      "parry",
      "slip",
      "tsuki", // also kendo thrust, but visual is similar
    ],
  },
  // Elbow strikes
  {
    mode: "elbow",
    keywords: ["elbow", "sok"],
  },
  // Knee strikes
  {
    mode: "knee",
    keywords: ["knee", "khao", "clinch"],
  },
  // Kicks
  {
    mode: "kick",
    keywords: [
      "kick",
      "round",
      "teep",
      "push kick",
      "low kick",
      "front kick",
      "side kick",
      "mawashi",
      "mae geri",
    ],
  },
  // Sword work — kendo/iaido
  {
    mode: "sword_cut",
    keywords: [
      "suburi",
      "kiritsuke",
      "nukitsuke",
      "men",
      "kote",
      "dou",
      "dō",
      "noto",
      "nōtō",
      "kata",
      "chiburi",
      "iaido",
      "cut",
      "sword",
    ],
  },
  // Wrestling / grappling — top
  {
    mode: "sprawl",
    keywords: ["sprawl", "shot", "double leg", "single leg", "takedown", "level change", "duck under", "snap down"],
  },
  // Wrestling / BJJ — bottom / hip movement
  {
    mode: "shrimp",
    keywords: [
      "shrimp",
      "hip escape",
      "hip movement",
      "guard retention",
      "frame",
      "bridge",
      "upa",
      "technical stand",
      "granby",
      "invert",
      "pass",
      "side control",
      "mount",
      "back take",
      "submission",
      "choke",
      "kakie",
      "drill",
    ],
  },
  // Strength / conditioning legs
  {
    mode: "squat",
    keywords: [
      "squat",
      "lunge",
      "burpee",
      "jumping jack",
      "wall sit",
      "calisthen",
      "step",
      "footwork",
      "stance",
      "shuffle",
      "kihon",
      "bunkai",
    ],
  },
  // Stretch / cool down
  {
    mode: "stretch",
    keywords: [
      "stretch",
      "cooldown",
      "cool down",
      "cool-down",
      "mobility",
      "foam roll",
      "downward dog",
      "child's pose",
      "yoga",
      "lengthen",
      "decompress",
    ],
  },
];

/** Classify the motion mode for a given exercise name (and optional discipline hint). */
export function classifyMotion(name?: string, disciplineId?: string): MotionMode {
  const text = (name || "").toLowerCase().trim();
  if (!text) {
    if (disciplineId === "boxing") return "punch";
    if (disciplineId === "muay_thai") return "kick";
    if (disciplineId === "kendo") return "sword_cut";
    if (disciplineId === "bjj" || disciplineId === "wrestling") return "shrimp";
    return "idle";
  }
  for (const { mode, keywords } of PATTERNS) {
    for (const kw of keywords) {
      if (text.includes(kw)) return mode;
    }
  }
  // Discipline-based fallback
  if (disciplineId === "boxing") return "punch";
  if (disciplineId === "muay_thai") return "kick";
  if (disciplineId === "kendo") return "sword_cut";
  if (disciplineId === "goju_ryu") return "punch";
  if (disciplineId === "bjj" || disciplineId === "wrestling") return "shrimp";
  return "idle";
}

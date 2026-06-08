/**
 * Detailed movement breakdowns that replace the previous stick-figure
 * silhouette animations. Each entry returns clear, mobile-friendly
 * instructions: setup, the movement itself, key cues, and common errors.
 *
 * We choose the description in priority:
 *   1. Exact-name override (e.g. "Jumping jacks", "Shrimp drill")
 *   2. Keyword/substring match against the step title
 *   3. Motion-mode default (from motion-classifier)
 *   4. Generic fallback
 *
 * No images are used — descriptions are written so a user can perform
 * the movement from the text alone.
 */
import { MotionMode } from "@/src/utils/motion-classifier";

export type Breakdown = {
  /** Short heading shown above the breakdown */
  headline: string;
  /** 2-5 ordered "how to do it" steps */
  how_to: string[];
  /** Posture / form cues (3-4 bullets) */
  cues: string[];
  /** Common errors to avoid (1-3 bullets, optional) */
  errors?: string[];
  /** Ionicons name for the breakdown header */
  icon: string;
};

/* -------------------------------------------------------------------------- */
/*                          MOTION-MODE DEFAULTS                              */
/* -------------------------------------------------------------------------- */

const MODE_DEFAULTS: Record<MotionMode, Breakdown> = {
  idle: {
    headline: "Centered stance",
    icon: "body-outline",
    how_to: [
      "Stand tall, feet shoulder-width apart, weight evenly on both feet.",
      "Knees soft (not locked). Spine long, crown of the head lifted.",
      "Hands at the sides or in a relaxed guard.",
    ],
    cues: [
      "Shoulders down and back.",
      "Breath slow through the nose.",
      "Eyes forward, soft focus.",
    ],
  },

  breathing: {
    headline: "Breath & centering",
    icon: "leaf-outline",
    how_to: [
      "Sit or stand tall with the spine long and shoulders relaxed.",
      "Inhale slowly through the nose for a 4-count, filling the belly first, then the chest.",
      "Hold gently for a 2-count without straining.",
      "Exhale through the nose (or pursed lips) for a 6-count, releasing the jaw and shoulders.",
      "Repeat for the prescribed duration, letting each breath grow a little slower.",
    ],
    cues: [
      "Belly first, chest second — diaphragmatic breathing.",
      "If the mind wanders, return to the count.",
      "Soften the face, soften the hands.",
    ],
    errors: [
      "Don't force a deeper breath than feels natural — quality over volume.",
      "Avoid raising the shoulders on the inhale.",
    ],
  },

  punch: {
    headline: "Punching mechanics",
    icon: "fitness-outline",
    how_to: [
      "Start in a boxing stance: lead foot forward, rear foot at ~45°, knees slightly bent, weight even.",
      "Hands up, chin tucked behind the lead shoulder, elbows in.",
      "Drive the punch from the back foot — pivot the heel, rotate the hip, then the shoulder.",
      "Exhale sharply as the fist extends, rotating the fist palm-down at impact.",
      "Snap the hand back along the same line — return is faster than the throw.",
    ],
    cues: [
      "Power comes from the floor up: foot → hip → shoulder → fist.",
      "Keep the non-punching hand glued to the cheek.",
      "Stay on the balls of the feet, slight bounce.",
    ],
    errors: [
      "Don't lean in — keep the head over the hips.",
      "Don't drop the rear hand when you punch.",
    ],
  },

  kick: {
    headline: "Kicking mechanics",
    icon: "walk-outline",
    how_to: [
      "From a fighting stance, step the lead foot slightly off the centerline so the hips can open.",
      "Pivot hard on the standing foot — the heel turns to face the target.",
      "Lift the kicking knee toward the line of the target, then whip the shin or instep through.",
      "Keep the same-side hand high; the opposite hand can post downward for balance.",
      "Recover by snapping the leg back to the stance — no rest with the leg out.",
    ],
    cues: [
      "Pivot fully — open hips deliver the kick.",
      "Look where you kick, then look back behind your guard.",
      "Strike with shin (round kicks) or ball/heel of the foot (front/teep).",
    ],
    errors: [
      "Don't kick with a flat standing foot — pivot or you'll twist the knee.",
      "Don't drop both hands when kicking.",
    ],
  },

  knee: {
    headline: "Knee strike mechanics",
    icon: "triangle-outline",
    how_to: [
      "From a clinch posture (or shadow clinch), pull the partner's head/imagined collar tie downward.",
      "Drive the rear knee up and through the target line, pointing the toe to extend the strike.",
      "Thrust the hips forward at impact — the knee is not a leg-curl; it's a hip drive.",
      "Recover the foot back to base, hands stay tight on the head/neck.",
    ],
    cues: [
      "Knee through, not at — drive the hips past the target.",
      "Hands pull as the knee strikes — opposing forces multiply impact.",
      "Toe pointed lengthens the femur and adds 2-3 inches of reach.",
    ],
    errors: [
      "Don't lean back — bring the hips, not the chest, into the strike.",
    ],
  },

  elbow: {
    headline: "Elbow strike mechanics",
    icon: "flag-outline",
    how_to: [
      "From a high guard, shift your weight onto the lead foot for a horizontal elbow.",
      "Rotate the hip and shoulder as one unit — the elbow tip is the cutting edge.",
      "Strike across (slashing), upward (uppercut elbow), or downward (chopping) depending on the angle.",
      "Snap back to the guard — exhale at impact.",
    ],
    cues: [
      "Drive with the same-side hip — it's a short-range punch with bone instead of fist.",
      "Tighten the fist on impact to lock the forearm and shoulder.",
      "Eyes through the target, never down.",
    ],
    errors: [
      "Don't over-rotate past your balance line.",
    ],
  },

  squat: {
    headline: "Squat / lower-body mechanics",
    icon: "barbell-outline",
    how_to: [
      "Feet shoulder-width apart (or slightly wider), toes pointed slightly out.",
      "Brace the core, inhale, and sit the hips back and down — chest stays tall.",
      "Descend until the thighs are roughly parallel to the floor (or as deep as form allows).",
      "Drive through the whole foot — heels rooted — and exhale as you stand.",
      "Lock out the hips at the top without overarching the lower back.",
    ],
    cues: [
      "Knees track over the toes — don't let them collapse inward.",
      "Weight in the mid-foot and heels, not the toes.",
      "Chest proud, eyes on a fixed point ahead.",
    ],
    errors: [
      "Don't round the lower back at the bottom.",
      "Don't bounce out of the bottom — control the ascent.",
    ],
  },

  sprawl: {
    headline: "Sprawl & shot defense",
    icon: "git-network-outline",
    how_to: [
      "From wrestling stance — feet wide, hips loaded, hands ready.",
      "When the shot comes, fire both legs straight back and hips down to the mat.",
      "Drop your chest onto the partner's shoulders (or imagined opponent), arms framing under the armpits or behind the head.",
      "Pop the hips down hard — heavy hips = stuffed shot.",
      "Recover by circling away or scrambling to a dominant angle.",
    ],
    cues: [
      "Hips first, hands second — the legs save you, not the arms.",
      "Don't catch the head with your hands; control the hips/shoulders instead.",
      "Heavy chest on, heavy hips down.",
    ],
    errors: [
      "Don't backpedal — that loses base and lets the shot land.",
    ],
  },

  shrimp: {
    headline: "Hip escape (shrimping)",
    icon: "git-compare-outline",
    how_to: [
      "Lie on your back, knees bent, feet flat on the mat (or imagined mat).",
      "Plant one foot, push off it to lift the hip off the mat to the opposite side.",
      "As the hip lifts, slide your shoulder and chest away from where your hip just was — creating space.",
      "Land softly, re-set, and continue in the same direction down the mat.",
      "Alternate sides on the way back.",
    ],
    cues: [
      "Push with the foot, not with the hands.",
      "Lead with the hip — the shoulders follow.",
      "Make space between your elbow and your hip on the escaping side.",
    ],
    errors: [
      "Don't simply scoot the shoulders — the hip is the key joint.",
    ],
  },

  sword_cut: {
    headline: "Vertical cut (suburi)",
    icon: "cut-outline",
    how_to: [
      "Stand in chūdan (middle) stance: lead foot forward, hips squared, tip of the sword/bokken at throat level.",
      "Inhale and raise the sword overhead — elbows in, hands at the centerline.",
      "Exhale sharply (kiai) as you cut straight down: arms extend, hips drop, the tip drives forward and down to roughly chin level.",
      "Squeeze the bottom three fingers of the left hand at the moment of cut (tenouchi) — the right hand is loose.",
      "Pause one full breath in stillness (zanshin) before raising again.",
    ],
    cues: [
      "Cut from the center of the body, not the arms.",
      "Sword stops sharply — no wobble at the bottom.",
      "Feet stay quiet; hips and breath move the sword.",
    ],
    errors: [
      "Don't grip too tightly with the right (forward) hand — it slows the cut.",
      "Don't let the sword drift to the side; it travels the centerline.",
    ],
  },

  stretch: {
    headline: "Mobility / cool-down",
    icon: "moon-outline",
    how_to: [
      "Enter the stretch slowly — never bounce into end-range.",
      "Inhale to lengthen, exhale to deepen by a small amount.",
      "Hold for the prescribed time (usually 20-45 seconds per side), breathing evenly.",
      "Switch sides if applicable — match time evenly to keep the body balanced.",
      "Come out of the stretch slowly and shake the limb out before the next one.",
    ],
    cues: [
      "Discomfort yes, sharp pain no — back off if you feel a pinch.",
      "Soft jaw, soft eyes, slow breath.",
      "Where the breath goes, the tissue follows.",
    ],
    errors: [
      "Don't hold the breath — that locks the tissue.",
      "Don't compare your range with anyone else's.",
    ],
  },
};

/* -------------------------------------------------------------------------- */
/*                        EXACT-NAME / KEYWORD OVERRIDES                      */
/* -------------------------------------------------------------------------- */

type Override = { match: (lc: string) => boolean; bd: Breakdown };

const OVERRIDES: Override[] = [
  {
    match: (s) => /jumping jacks?/.test(s),
    bd: {
      headline: "Jumping jacks",
      icon: "expand-outline",
      how_to: [
        "Stand tall, feet together, arms at the sides.",
        "Jump the feet wide while sweeping the arms overhead to clap (or stop just before).",
        "Jump the feet back together as the arms come down to the sides.",
        "Land softly through the balls of the feet; keep a steady rhythm.",
      ],
      cues: [
        "Keep the core lightly braced.",
        "Breath: inhale 2 reps, exhale 2 reps.",
      ],
      errors: ["Avoid heavy heel landings — knees take less load when you land soft."],
    },
  },
  {
    match: (s) => /burpee/.test(s),
    bd: {
      headline: "Burpee",
      icon: "flash-outline",
      how_to: [
        "Drop into a low squat, plant the hands on the floor in front of you.",
        "Kick or step the feet back to a plank position with a straight body line.",
        "(Optional) lower the chest to the floor; press back up.",
        "Hop or step the feet back to the squat.",
        "Drive up explosively into a jump — arms reaching overhead.",
      ],
      cues: ["Keep the hips in line in plank — don't sag.", "Soft landing on the jump."],
    },
  },
  {
    match: (s) => /(jab|cross|hook|uppercut|1-?2|combination|combo)/.test(s),
    bd: {
      ...MODE_DEFAULTS.punch,
      headline: "Punch combination",
      how_to: [
        ...MODE_DEFAULTS.punch.how_to,
        "For combinations, return the first hand fully before launching the second — no overlap, no flailing.",
      ],
    },
  },
  {
    match: (s) => /shadow.?box/.test(s),
    bd: {
      headline: "Shadow boxing",
      icon: "person-outline",
      how_to: [
        "Move around your space in a fighting stance — circle, cut angles, change directions.",
        "Throw single shots and short 2-3 punch combinations against an imagined opponent.",
        "Mix in head movement: slip, roll, pull back, parry.",
        "Reset to guard after every exchange. Stay light on the feet.",
      ],
      cues: [
        "Pretend the opponent throws back — defend after every combination.",
        "Quality over speed: see each technique land cleanly in the mind.",
      ],
    },
  },
  {
    match: (s) => /(round.?kick|roundhouse|mawashi)/.test(s),
    bd: {
      ...MODE_DEFAULTS.kick,
      headline: "Round kick",
      how_to: [
        "From a fighting stance, take a small step out and forward with the lead foot — opens the hips.",
        "Pivot hard on the standing foot, heel toward the target.",
        "Whip the rear leg through, contact with the shin a few inches above the ankle.",
        "Same-side hand drives down; opposite hand stays high to guard.",
        "Snap the leg back to stance — never finish with the leg hanging.",
      ],
      cues: [
        "It's not a leg lift — it's a hip swing.",
        "Aim with the shin, not the foot.",
      ],
    },
  },
  {
    match: (s) => /(teep|push.?kick|front.?kick|mae.?geri)/.test(s),
    bd: {
      ...MODE_DEFAULTS.kick,
      headline: "Push / front kick",
      how_to: [
        "Lift the kicking knee high toward the chest.",
        "Drive the foot straight forward, hips pressing through.",
        "Contact with the ball of the foot (front kick) or the whole sole (teep).",
        "Snap the leg back immediately — never leave it extended.",
      ],
      cues: ["Knee up first, kick second.", "Hips through the target."],
    },
  },
  {
    match: (s) => /(shrimp|hip.?escape)/.test(s),
    bd: MODE_DEFAULTS.shrimp,
  },
  {
    match: (s) => /(bridge|upa)/.test(s),
    bd: {
      headline: "Bridge / upa",
      icon: "git-branch-outline",
      how_to: [
        "Lie on your back, knees bent, feet flat and close to your seat.",
        "Plant the heels, drive through the floor, and explosively lift the hips toward the ceiling.",
        "At the top, the hips are above the shoulders — chest tall, neck neutral.",
        "Lower with control and repeat — or, in escapes, turn over the same-side shoulder as you bridge.",
      ],
      cues: ["Heels close to the hips — short lever, big drive.", "Drive into the floor, don't push with the hands."],
    },
  },
  {
    match: (s) => /technical stand/.test(s),
    bd: {
      headline: "Technical stand-up",
      icon: "person-add-outline",
      how_to: [
        "From a seated position, post the same-side hand and foot behind you.",
        "Lift the hips and pass the trailing leg back underneath you to base out.",
        "Stand up directly into a fighting stance, never crossing your feet.",
      ],
      cues: ["Eyes forward the whole time.", "Don't put the second hand down — keep it ready to defend."],
    },
  },
  {
    match: (s) => /(sprawl|shot|takedown|level change|double.?leg|single.?leg)/.test(s),
    bd: MODE_DEFAULTS.sprawl,
  },
  {
    match: (s) => /(suburi|men.?cut|kiritsuke|kata)/.test(s),
    bd: MODE_DEFAULTS.sword_cut,
  },
  {
    match: (s) => /(sanchin|tensho|ibuki)/.test(s),
    bd: {
      headline: "Sanchin breathing",
      icon: "leaf-outline",
      how_to: [
        "Stand in sanchin-dachi: feet shoulder-width, toes turned slightly in, knees gently flexed inward.",
        "Hold a tight middle-block guard: forearms vertical, fists at solar plexus height.",
        "Inhale slowly through the nose for 4-6 counts, filling the dantian (lower belly).",
        "Exhale through pursed teeth with audible tension (ibuki) — every muscle subtly engaged.",
        "Hold the stance still — only the breath moves.",
      ],
      cues: [
        "Stance is rooted — feel the floor under every part of the foot.",
        "Tense on exhale, relax on inhale — but never collapse the posture.",
      ],
    },
  },
  {
    match: (s) => /(plank|hollow|dead bug|deadbug)/.test(s),
    bd: {
      headline: "Core hold",
      icon: "tablet-portrait-outline",
      how_to: [
        "From the floor, set forearms (or hands) on the ground shoulder-width apart.",
        "Step the feet back so the body forms a straight line from heels to shoulders.",
        "Tuck the pelvis slightly — ribs down, glutes firm.",
        "Breathe steadily — do not hold the breath.",
      ],
      cues: ["Glutes squeezed, abs braced like bracing for a punch.", "Eyes a foot in front of the hands."],
      errors: ["Don't let the hips sag or pike upward."],
    },
  },
  {
    match: (s) => /(pigeon|hip opener|cossack|90.?90)/.test(s),
    bd: {
      headline: "Hip opener",
      icon: "infinite-outline",
      how_to: [
        "Enter the stretch slowly, settling into the position.",
        "On the inhale, lengthen the spine; on the exhale, soften 1-2% deeper.",
        "Hold steady for 20-45 seconds, breathing evenly.",
        "Switch sides and match the duration.",
      ],
      cues: ["Breath into the tight spot.", "Sharp pain = back off. Discomfort = stay."],
    },
  },
  {
    match: (s) => /(child.?s pose|downward dog|cat.?cow)/.test(s),
    bd: {
      headline: "Restorative pose",
      icon: "moon-outline",
      how_to: [
        "Enter the pose without forcing — let gravity do the work.",
        "Hold for the prescribed time with slow nasal breathing.",
        "Soften the jaw, soften the eyes, soften the hands.",
      ],
      cues: ["This is a pause, not a workout. Recover here."],
    },
  },
];

/**
 * Return a structured breakdown for a step.
 */
export function describeMovement(
  stepTitle: string | undefined,
  motion: MotionMode,
): Breakdown {
  const lc = (stepTitle || "").toLowerCase().trim();
  if (lc) {
    for (const o of OVERRIDES) {
      if (o.match(lc)) return o.bd;
    }
  }
  return MODE_DEFAULTS[motion] || MODE_DEFAULTS.idle;
}

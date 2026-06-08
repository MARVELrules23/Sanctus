"""Sanctus Self-Defense — disciplines, patron saints, and AI prompt scaffolding.

Six disciplines, each paired with a deliberately-chosen Catholic patron.
Kendo includes solo Iaido form work when the user is training without a partner.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---- Patron saints -------------------------------------------------------
# Each saint is hand-picked to align with the discipline's tradition,
# scriptural roots, or charism.
PATRON_SAINTS: Dict[str, Dict[str, Any]] = {
    "bjj": {
        "name": "St. Paul the Apostle",
        "title": "Apostle to the Gentiles",
        "feast_day": "June 29",
        "icon": "flame-outline",
        "why_aligned": (
            "St. Paul drew on the agon — the wrestler's match — to describe the Christian life: "
            "\"we wrestle not against flesh and blood, but against principalities\" (Ephesians 6:12). "
            "His perseverance and tactical mind mirror the patience and chained sequences of jiu-jitsu."
        ),
        "scripture": "Ephesians 6:10-13",
        "short_prayer": (
            "Lord, through the intercession of St. Paul, give me a steady mind on the mat. "
            "Let every grip and breath teach me to wrestle against the principalities of my own sin, "
            "and to finish well the race set before me. Amen."
        ),
    },
    "goju_ryu": {
        "name": "St. Paul Miki, SJ",
        "title": "Japanese Jesuit Martyr, of samurai descent",
        "feast_day": "February 6",
        "icon": "leaf-outline",
        "why_aligned": (
            "Born of a samurai house in Japan, Paul Miki embodied martial discipline transfigured by Christ. "
            "Crucified at Nagasaki in 1597, he forgave his executioners from the cross. "
            "Gōjū-ryū's union of hard (gō) and soft (jū) reflects the same paradox: strength governed by mercy."
        ),
        "scripture": "Matthew 5:44",
        "short_prayer": (
            "St. Paul Miki, who in your Japanese homeland breathed hardness and softness in one body, "
            "obtain for me a karate that hardens against sin and softens toward neighbor. "
            "May my kata become a prayer. Amen."
        ),
    },
    "wrestling": {
        "name": "Jacob, Patriarch of Israel",
        "title": "He who strives with God",
        "feast_day": "—",
        "icon": "trail-sign-outline",
        "why_aligned": (
            "At the Jabbok ford, Jacob wrestled the angel until dawn and would not let go without a blessing "
            "(Genesis 32:24-30). He emerged limping — and renamed Israel. Every wrestler knows the lesson: "
            "you do not leave the mat unchanged."
        ),
        "scripture": "Genesis 32:24-30",
        "short_prayer": (
            "God of Jacob, You bless those who grip You and refuse to let go. "
            "Make me a wrestler who endures the long round, who walks away limping with Your blessing rather than upright without it. Amen."
        ),
    },
    "boxing": {
        "name": "St. Sebastian",
        "title": "Soldier-Martyr, Patron of Athletes",
        "feast_day": "January 20",
        "icon": "shield-outline",
        "why_aligned": (
            "A Roman soldier who endured a hail of arrows for Christ and lived to confront Diocletian a second time. "
            "Long-standing patron of athletes — including pugilists — for his capacity to absorb blows without breaking. "
            "Boxers learn what Sebastian lived: take the strike, keep your guard, answer with truth."
        ),
        "scripture": "1 Corinthians 9:26",
        "short_prayer": (
            "St. Sebastian, who took the arrows and kept your stance, teach me to keep my hands up and my heart open. "
            "May I not box as one beating the air, but as one running to win. Amen."
        ),
    },
    "muay_thai": {
        "name": "St. Michael the Archangel",
        "title": "Prince of the Heavenly Host",
        "feast_day": "September 29",
        "icon": "flash-outline",
        "why_aligned": (
            "Muay Thai is called the Art of Eight Limbs — fists, elbows, knees, shins. "
            "St. Michael leads the heavenly armies, casts down evil with decisive strike, and defends the weak. "
            "Striking arts find no truer patron than the Archangel who strikes only in defense of the innocent."
        ),
        "scripture": "Revelation 12:7-9",
        "short_prayer": (
            "St. Michael the Archangel, defend me in battle. "
            "Let every elbow and knee remember that strength is given to defend the weak, not to crush them. "
            "May my clinch be governed by your justice. Amen."
        ),
    },
    "kendo": {
        "name": "Bl. Justo Takayama Ukon",
        "title": "Catholic Samurai of Japan",
        "feast_day": "February 3",
        "icon": "ribbon-outline",
        "why_aligned": (
            "Daimyō and master swordsman, Takayama Ukon surrendered his lands and lived in exile rather than renounce Christ. "
            "Beatified in 2017. He carried the katana under the Cross — exactly the synthesis Kendo's 'Way of the Sword' aspires to: "
            "discipline of blade as discipline of soul."
        ),
        "scripture": "Matthew 26:52",
        "short_prayer": (
            "Bl. Justo, samurai of Christ, who held both the sword and the rosary without contradiction — "
            "make my cuts clean, my posture upright, and my spirit yielded to the only Lord worth dying for. Amen."
        ),
    },
}


# ---- Disciplines ---------------------------------------------------------
DISCIPLINES: List[Dict[str, Any]] = [
    {
        "id": "bjj",
        "name": "Brazilian Jiu-Jitsu",
        "tradition": "Brazilian (Gracie lineage)",
        "tagline": "The gentle art — leverage over force.",
        "description": (
            "Ground-based grappling system focused on positional control and submissions. "
            "Teaches that a smaller, technical fighter can prevail over a larger, untrained one. "
            "Sessions emphasize hip movement, frames, guard play, and chained sub-attempts."
        ),
        "skill_areas": [
            "Guard retention", "Passing", "Side control / mount", "Back take",
            "Submissions (chokes, joint locks)", "Escapes & defense", "Sweeps", "Drilling combinations",
        ],
        "equipment_options": ["solo", "partner", "mats", "gi", "no_gi"],
        "icon": "git-merge-outline",
    },
    {
        "id": "goju_ryu",
        "name": "Gōjū-ryū Karate",
        "tradition": "Okinawan / Japanese",
        "tagline": "Hard and soft — gō (剛) and jū (柔) in one body.",
        "description": (
            "An Okinawan karate style integrating linear striking (gō, hard) with circular evasion and breathing (jū, soft). "
            "Heavy emphasis on sanchin breathing, kata, kakie (sticky-hands), and conditioning."
        ),
        "skill_areas": [
            "Sanchin / Tensho breathing", "Kihon (basics)", "Kata (Seipai, Saifa, Kururunfa)",
            "Kakie sticky-hands", "Bunkai application", "Conditioning (makiwara, hojo undo)",
        ],
        "equipment_options": ["solo", "partner", "makiwara", "bag"],
        "icon": "leaf-outline",
    },
    {
        "id": "wrestling",
        "name": "Wrestling",
        "tradition": "Folkstyle / Freestyle",
        "tagline": "The original combat sport — take him down, hold him down.",
        "description": (
            "Standing and ground wrestling: takedowns, takedown defense, top/bottom control, escapes. "
            "Builds explosive strength, neck/grip endurance, and the most useful base for any other combat art."
        ),
        "skill_areas": [
            "Stance & motion", "Penetration step", "Single & double leg",
            "Sprawl & defense", "Top riding & turns", "Bottom escapes & stand-ups", "Tie-ups & pummeling",
        ],
        "equipment_options": ["solo", "partner", "mats"],
        "icon": "people-circle-outline",
    },
    {
        "id": "boxing",
        "name": "Boxing",
        "tradition": "Western (Marquess of Queensberry)",
        "tagline": "The Sweet Science — hands, head, heart.",
        "description": (
            "Pure hand striking with strict footwork and head movement. "
            "Develops timing, distance management, defensive layers (parry / slip / roll / block), and conditioning."
        ),
        "skill_areas": [
            "Stance & guard", "Jab mechanics", "Cross & lead hook", "Body shots",
            "Head movement (slip / roll / pull)", "Footwork & angles", "Combinations", "Counter-punching",
        ],
        "equipment_options": ["solo", "partner", "bag", "pads", "mitts"],
        "icon": "hand-left-outline",
    },
    {
        "id": "muay_thai",
        "name": "Muay Thai",
        "tradition": "Thai — the Art of Eight Limbs",
        "tagline": "Fists, elbows, knees, shins — and the clinch.",
        "description": (
            "Thai striking art using all eight points of contact plus a dominant clinch game. "
            "Sessions emphasize teeps, leg kicks, elbow setups, knee strikes from clinch, and shin conditioning."
        ),
        "skill_areas": [
            "Stance & teep", "Round kick (low/mid/high)", "Knee strikes", "Elbow strikes",
            "Clinch — neck control, knees, sweeps", "Block & check kicks", "Combinations", "Shin conditioning",
        ],
        "equipment_options": ["solo", "partner", "bag", "pads", "mitts"],
        "icon": "flash-outline",
    },
    {
        "id": "kendo",
        "name": "Kendo (with Iaido solo)",
        "tradition": "Japanese — the Way of the Sword",
        "tagline": "Ken (剣) — the sword. Dō (道) — the way.",
        "description": (
            "Japanese sword art using shinai (bamboo) and bokken (wooden). "
            "Emphasizes posture, kiai (spirit-shout), kihon strikes (men, kote, dō, tsuki), suburi, and kata. "
            "When training solo, the session draws on Iaido — drawing, cutting, chiburi (blood-shake), and resheathing — "
            "to preserve the form and dignity of the sword tradition."
        ),
        "skill_areas": [
            "Kamae (stance)", "Suburi (cut repetitions)", "Footwork (suri-ashi, fumikomi)",
            "Men / Kote / Dō / Tsuki strikes", "Kata (Nihon Kendo Kata)",
            "Iaido (solo): nukitsuke draw-cut, kiritsuke, chiburi, nōtō resheath",
            "Zanshin (lingering awareness)",
        ],
        "equipment_options": ["solo", "partner", "shinai", "bokken", "iaito"],
        "icon": "ribbon-outline",
    },
]

DISCIPLINE_IDS = {d["id"] for d in DISCIPLINES}


def get_discipline(discipline_id: str) -> Optional[Dict[str, Any]]:
    for d in DISCIPLINES:
        if d["id"] == discipline_id:
            return d
    return None


def get_patron(discipline_id: str) -> Optional[Dict[str, Any]]:
    return PATRON_SAINTS.get(discipline_id)


# ---- Level progression ---------------------------------------------------
LEVEL_ORDER = ["beginner", "intermediate", "advanced"]
PROMOTION_THRESHOLDS = {"beginner": 12, "intermediate": 30}  # sessions_completed to next level


def next_level(level: str) -> str:
    try:
        idx = LEVEL_ORDER.index(level)
        return LEVEL_ORDER[min(idx + 1, len(LEVEL_ORDER) - 1)]
    except ValueError:
        return "beginner"


def determine_level(progress: Dict[str, Any]) -> str:
    """Promote level based on completed sessions; ignore generated-but-not-completed."""
    completed = int(progress.get("sessions_completed") or 0)
    current = progress.get("current_level") or "beginner"
    if current == "beginner" and completed >= PROMOTION_THRESHOLDS["beginner"]:
        return "intermediate"
    if current == "intermediate" and completed >= PROMOTION_THRESHOLDS["intermediate"]:
        return "advanced"
    return current


# ---- Safety disclaimer ---------------------------------------------------
SAFETY_DISCLAIMER = (
    "Self-Defense training carries real risk of injury. "
    "Sanctus's AI-generated sessions are for educational reference and solo conditioning. "
    "Live sparring, partner drills with full resistance, and weapons work — including bokken, shinai, and iaito — "
    "should always be done under the supervision of a qualified instructor at a reputable gym, dojo, or club. "
    "Never spar without a trained coach present. Never practice live blade work without supervision. "
    "Warm up properly, tap early, and respect your training partners as fellow children of God. "
    "By proceeding you acknowledge that you assume the risks inherent to combat sports and martial training, "
    "and that Sanctus is not a substitute for in-person instruction."
)


# ---- AI prompt builders --------------------------------------------------
def build_session_system_prompt() -> str:
    return (
        "You are a Catholic martial-arts coach for the Sanctus app, generating structured self-defense training sessions. "
        "Your tone is disciplined, charitable, and grounded — like a coach who is also a believer. "
        "You honor the tradition of the discipline (terminology, etiquette, lineage). "
        "Safety is paramount: never recommend live sparring or live-blade work without supervision; "
        "always indicate intensity level (low/medium/high) on every block. "
        "Always return strictly valid JSON. No prose outside JSON."
    )


def build_session_user_prompt(
    discipline: Dict[str, Any],
    patron: Dict[str, Any],
    level: str,
    duration_minutes: int,
    equipment: List[str],
    has_partner: bool,
    sessions_completed: int,
    recent_focus: List[str],
    include_patron_reflection: bool,
) -> str:
    eq_str = ", ".join(equipment) if equipment else "bodyweight only"
    recent = "; ".join(recent_focus[-3:]) if recent_focus else "none on record (first session)"
    partner_note = "with a training partner" if has_partner else "training SOLO — no partner drills, no live resistance"
    iaido_note = ""
    if discipline["id"] == "kendo" and not has_partner:
        iaido_note = (
            "Because the user is solo, build the body of this session around Iaido form practice "
            "(nukitsuke draw-cut, kiritsuke, chiburi blood-shake, nōtō resheath) and Kendo suburi, "
            "rather than partner-required waza."
        )
    reflection_note = (
        f"Include a one-paragraph patron reflection tying the work to {patron['name']} "
        f"and one short prayer (2-3 sentences) invoking his/her intercession. "
        f"Patron context: {patron['why_aligned']}"
        if include_patron_reflection
        else "Do NOT include a patron reflection block (set patron_reflection to null and prayer to null)."
    )
    return (
        f"Generate the next training session for this user.\n\n"
        f"DISCIPLINE: {discipline['name']} ({discipline['tradition']})\n"
        f"TAGLINE: {discipline['tagline']}\n"
        f"CORE SKILL AREAS: {', '.join(discipline['skill_areas'])}\n"
        f"PATRON: {patron['name']} — {patron['title']}\n\n"
        f"USER LEVEL: {level}\n"
        f"USER PROGRESS: {sessions_completed} session(s) completed in this discipline.\n"
        f"RECENT FOCUS AREAS (last 3 sessions): {recent}\n"
        f"TARGET DURATION: {duration_minutes} minutes\n"
        f"EQUIPMENT AVAILABLE: {eq_str}\n"
        f"PARTNER STATUS: {partner_note}\n"
        f"{iaido_note}\n\n"
        f"Rotate the technique_focus to avoid repeating the most recent focus exactly; "
        f"build on the previous progression where it makes sense.\n\n"
        f"{reflection_note}\n\n"
        f"Return JSON shaped EXACTLY like:\n"
        "{\n"
        "  \"title\": str,                              // e.g. 'Guard Retention & Hip Escapes'\n"
        "  \"technique_focus\": str,                    // one short label, used for progression tracking\n"
        "  \"intensity\": \"low\"|\"medium\"|\"high\",\n"
        "  \"duration_minutes\": int,\n"
        "  \"warmup\": [{\"name\": str, \"duration_seconds\": int, \"notes\": str}],\n"
        "  \"drills\": [{\"name\": str, \"sets\": str, \"notes\": str, \"solo_safe\": bool}],\n"
        "  \"technique_block\": {\n"
        "    \"name\": str,\n"
        "    \"key_points\": [str, str, str],\n"
        "    \"common_errors\": [str, str],\n"
        "    \"progression_hint\": str                  // what to focus on NEXT session\n"
        "  },\n"
        "  \"live_application\": [{\"name\": str, \"description\": str, \"requires_partner\": bool}],\n"
        "  \"cooldown\": [{\"name\": str, \"duration_seconds\": int}],\n"
        "  \"patron_reflection\": str | null,\n"
        "  \"patron_prayer\": str | null,\n"
        "  \"coach_note\": str                          // 1-2 sentence motivational close from the coach\n"
        "}"
    )

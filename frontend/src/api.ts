/**
 * Tiny API client for Sanctus.
 * Reads token from secure storage and attaches Bearer header.
 */
import { storage } from "@/src/utils/storage";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL ?? "";
const TOKEN_KEY = "sanctus_session_token";

export async function getToken(): Promise<string | null> {
  return await storage.secureGet<string>(TOKEN_KEY, "");
}

export async function setToken(token: string): Promise<void> {
  await storage.secureSet(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  await storage.secureRemove(TOKEN_KEY);
}

type FetchOpts = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  auth?: boolean;
};

export async function api<T = unknown>(path: string, opts: FetchOpts = {}): Promise<T> {
  const url = `${BASE}/api${path}`;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (opts.auth !== false) {
    const token = await getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(url, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const text = await res.text();
  let parsed: unknown = undefined;
  try {
    parsed = text ? JSON.parse(text) : undefined;
  } catch {
    parsed = text;
  }
  if (!res.ok) {
    const detail =
      (parsed && typeof parsed === "object" && "detail" in parsed
        ? (parsed as { detail: unknown }).detail
        : null) ?? text ?? `HTTP ${res.status}`;
    const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    (err as Error & { status?: number }).status = res.status;
    throw err;
  }
  return parsed as T;
}

export type LiturgicalDay = {
  date: string;
  season: string;
  color: string;
  feast: string | null;
  rank: string;
  is_abstinence: boolean;
  is_fast: boolean;
  is_sunday: boolean;
};

export type User = {
  user_id: string;
  email: string;
  name: string;
  picture?: string | null;
};

export type GoalMode = "liturgical" | "goals";

export type BibleColor = "rose" | "gold" | "sage" | "violet";

export type BibleBook = {
  slug: string;
  name: string;
  dr_name: string;
  abbr: string;
  section: "ot" | "deutero" | "nt";
  order: number;
  chapters: number;
};

export type BibleVerse = { n: number; text: string };

export type BibleChapter = {
  book_slug: string;
  book_name: string;
  dr_name: string;
  chapter: number;
  chapters_total: number;
  verses: BibleVerse[];
  highlights: { verse: number; color: BibleColor }[];
};

export type BibleHighlight = {
  book_slug: string;
  chapter: number;
  verse: number;
  color: BibleColor;
  citation: string;
  updated_at?: string;
  created_at?: string;
};

export async function updateMe(patch: { name?: string; picture?: string | null }): Promise<User> {
  // Backend accepts empty string to clear picture; pass through null as empty.
  const body: Record<string, string> = {};
  if (patch.name !== undefined) body.name = patch.name;
  if (patch.picture !== undefined) body.picture = patch.picture ?? "";
  return await api<User>("/auth/me", { method: "PUT", body });
}

export type MealPlan = {
  breakfast: { name: string; description: string; ingredients: string[]; prep_minutes: number };
  lunch: { name: string; description: string; ingredients: string[]; prep_minutes: number };
  dinner: { name: string; description: string; ingredients: string[]; prep_minutes: number };
  reflection: string;
};

export type WorkoutPlan = {
  title: string;
  focus: string;
  duration_minutes: number;
  exercises: { name: string; sets: string; notes: string }[];
  opening_prayer: string;
  closing_prayer: string;
  reflection: string;
};

export type DayDoc<T> = {
  user_id: string;
  date: string;
  liturgical: LiturgicalDay;
  plan: T;
  updated_at: string;
};

export type Readings = {
  date: string;
  liturgical: LiturgicalDay;
  liturgical_title: string;
  source: "universalis" | "usccb" | "ai-fallback";
  first_reading: string;
  first_reading_excerpt: string;
  psalm: string;
  psalm_excerpt: string;
  second_reading: string;
  second_reading_excerpt: string;
  gospel: string;
  gospel_excerpt: string;
  gospel_acclamation: string;
  gospel_acclamation_excerpt: string;
  reflection: string;
  usccb_url: string;
};

export type JournalMood =
  | "grateful"
  | "joyful"
  | "sorrowful"
  | "contrite"
  | "hopeful"
  | "weary"
  | null;

export type JournalKind = "free" | "examen" | "examination";

export type JournalEntry = {
  entry_id: string;
  date: string;
  title: string;
  body: string;
  mood: JournalMood;
  kind?: JournalKind;
  structured?: Record<string, unknown> | null;
  liturgical?: LiturgicalDay;
  confessed_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type ExamenPrompt = {
  key: string;
  title: string;
  prompt: string;
  icon: string;
};

export type ExaminationSection = {
  key: string;
  title: string;
  prompts: string[];
};

export type GroceryItem = { name: string; count: number };
export type GroceryWeek = { start: string; end: string; items: GroceryItem[]; days_with_meals: number };

export type MealItem = MealPlan["breakfast"];
export type ExerciseItem = WorkoutPlan["exercises"][number];

export type WellnessProfile = {
  weight_kg: number | null;
  height_cm: number | null;
  target_weight_kg: number | null;
  target_date: string | null;
  goal_type: "lose" | "maintain" | "gain" | null;
  activity_level: "sedentary" | "light" | "moderate" | "very_active" | null;
  weekly_rate_kg: number | null;
  units: "metric" | "imperial";
  notes: string | null;
  updated_at?: string | null;
};

export type WeightLog = {
  log_id: string;
  date: string;
  weight_kg: number;
  note?: string | null;
  created_at?: string;
};

export type WellnessSuggestion = {
  calorie_target: number;
  macro_focus: string;
  meal_focus: string[];
  workout_focus: string[];
  weekly_split: string;
  encouragement: string;
  based_on: string;
};

export type ChurchItem = {
  church_id: string;
  name: string;
  lat: number;
  lng: number;
  distance_km?: number;
  address?: string;
  denomination?: string;
  website?: string;
  phone?: string;
  mass_times?: string[];
  confession_times?: string[];
  mass_times_raw?: string;
  opening_hours?: string;
  schedule_source?: string;
  is_starred?: boolean;
  notes?: string;
  saved_at?: string | null;
};

// ---- Community types ----
export type CommunityTopic = { slug: string | null; label: string; icon: string };
export type CommunityUserPublic = { user_id: string; name: string; picture: string | null | undefined };

export type CommunityPost = {
  post_id: string;
  author: CommunityUserPublic;
  body: string;
  topic: string | null;
  liturgical_color?: string | null;
  liturgical_season?: string | null;
  created_at: string;
  like_count: number;
  reply_count: number;
  liked_by_me: boolean;
  image?: string | null;
  is_pinned?: boolean;
};

export type CommunityReply = {
  reply_id: string;
  post_id: string;
  author: CommunityUserPublic;
  body: string;
  created_at: string;
};

export type CommunityFeed = {
  items: CommunityPost[];
  next_cursor: string | null;
  topic: string | null;
};

export type CommunityDMThread = {
  thread_id: string;
  other: CommunityUserPublic | null;
  last_message: string | null;
  last_message_at: string | null;
  unread: number;
};

export type CommunityDMMessage = {
  message_id: string;
  thread_id: string;
  sender_id: string;
  body: string;
  created_at: string;
};

export const REPORT_REASONS_FALLBACK = [
  "Inappropriate content",
  "Harassment or hateful speech",
  "Spam or misleading",
  "Doctrinal error / scandal",
  "Other",
];

// ---- Self-Defense (Phase 4) ----
export type SDPatron = {
  name: string;
  title?: string;
  feast_day?: string;
  icon?: string;
  why_aligned?: string;
  scripture?: string;
  short_prayer?: string;
};

export type SDDiscipline = {
  id: string;
  name: string;
  tradition: string;
  tagline: string;
  description: string;
  skill_areas: string[];
  equipment_options: string[];
  icon: string;
  patron?: SDPatron;
};

export type SDProgress = {
  user_id?: string;
  discipline_id: string;
  current_level: "beginner" | "intermediate" | "advanced";
  sessions_generated?: number;
  sessions_completed: number;
  recent_focus?: string[];
  last_session_at?: string | null;
  last_completed_at?: string | null;
};

export type SDSessionPlan = {
  title: string;
  technique_focus: string;
  intensity?: "low" | "medium" | "high";
  duration_minutes?: number;
  warmup?: Array<{ name: string; duration_seconds?: number; notes?: string }>;
  drills?: Array<{ name: string; sets?: string; notes?: string; solo_safe?: boolean }>;
  technique_block?: {
    name: string;
    key_points?: string[];
    common_errors?: string[];
    progression_hint?: string;
  };
  live_application?: Array<{ name: string; description: string; requires_partner?: boolean }>;
  cooldown?: Array<{ name: string; duration_seconds?: number }>;
  patron_reflection?: string | null;
  patron_prayer?: string | null;
  coach_note?: string;
};

export type SDSession = {
  session_id: string;
  discipline_id: string;
  discipline_name: string;
  tradition: string;
  level: "beginner" | "intermediate" | "advanced";
  duration_minutes: number;
  equipment: string[];
  has_partner: boolean;
  include_patron_reflection: boolean;
  patron: SDPatron;
  plan: SDSessionPlan;
  generated_at: string;
  completed_at: string | null;
  completion_notes: string | null;
  intensity_actual: "low" | "medium" | "high" | null;
  source: "generated" | "redo";
  parent_session_id: string | null;
};

// ---- Daily Practice ----
export type DailyPractice = {
  id: string;
  category: string;
  title: string;
  body: string;
  why: string;
  virtue: string;
  intensity: "easy" | "moderate" | "hard";
  date: string | null;
  completed_at: string | null;
  note: string | null;
};

export type DailyPracticeHistory = {
  items: DailyPractice[];
  total_pool: number;
};


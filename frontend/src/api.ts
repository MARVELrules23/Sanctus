/**
 * Tiny API client for Sanctus.
 * Reads token from secure storage and attaches Bearer header.
 */
import { storage } from "@/src/utils/storage";
import { getLang } from "@/src/i18n";

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
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Accept-Language": getLang(),
  };
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
  // Traditional (1962) calendar extras — present only on /tridentine responses.
  is_holy_day?: boolean;
  holy_day_note?: string | null;
  observance?: string | null;
  abstinence_type?: "complete" | "partial" | null;
  calendar?: string;
};

export type RiteKey =
  | "latin"
  | "byzantine"
  | "maronite"
  | "chaldean"
  | "syro_malabar"
  | "syro_malankara"
  | "coptic"
  | "armenian"
  | "syriac"
  | "ordinariate";

// Human-readable labels for each Catholic rite/particular Church in communion
// with Rome. Keys mirror the backend catholic_filter.RITE_LABELS.
export const RITE_LABELS: Record<RiteKey, string> = {
  latin: "Latin (Roman)",
  byzantine: "Byzantine",
  maronite: "Maronite",
  chaldean: "Chaldean",
  syro_malabar: "Syro-Malabar",
  syro_malankara: "Syro-Malankara",
  coptic: "Coptic",
  armenian: "Armenian",
  syriac: "Syriac",
  ordinariate: "Ordinariate",
};

// Ordered list for pickers (most common first).
export const RITE_OPTIONS: { key: RiteKey; label: string }[] = (
  [
    "latin",
    "byzantine",
    "maronite",
    "chaldean",
    "syro_malabar",
    "syro_malankara",
    "coptic",
    "armenian",
    "syriac",
    "ordinariate",
  ] as RiteKey[]
).map((key) => ({ key, label: RITE_LABELS[key] }));

export function riteLabel(key?: string | null): string {
  if (!key) return "";
  return RITE_LABELS[key as RiteKey] ?? "";
}

export type User = {
  user_id: string;
  email: string;
  name: string;
  picture?: string | null;
  denomination?: "catholic" | "protestant" | "orthodox" | null;
  tradition_path?: "convert" | "revert" | "cradle" | null;
  rite?: RiteKey | null;
  age?: number | null;
  show_attribution?: boolean | null;
  is_admin?: boolean | null;
  is_premium?: boolean | null;
  premium?: {
    active?: boolean;
    tier?: "monthly" | "annual" | null;
    status?: string | null;
    current_period_end?: number | null;
    cancel_at_period_end?: boolean;
    trial_end?: number | null;
  } | null;
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

export async function updateMe(patch: {
  name?: string;
  picture?: string | null;
  denomination?: "catholic" | "protestant" | "orthodox" | null;
  tradition_path?: "convert" | "revert" | "cradle" | null;
  rite?: RiteKey | null;
  age?: number | null;
  show_attribution?: boolean | null;
}): Promise<User> {
  // Backend accepts empty string to clear picture; pass through null as empty.
  const body: Record<string, unknown> = {};
  if (patch.name !== undefined) body.name = patch.name;
  if (patch.picture !== undefined) body.picture = patch.picture ?? "";
  if (patch.denomination !== undefined) body.denomination = patch.denomination ?? "";
  if (patch.tradition_path !== undefined) body.tradition_path = patch.tradition_path ?? "";
  if (patch.rite !== undefined) body.rite = patch.rite ?? "";
  if (patch.age !== undefined) body.age = patch.age == null ? 0 : patch.age;
  if (patch.show_attribution !== undefined) body.show_attribution = !!patch.show_attribution;
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
  first_reading_full?: string;
  psalm: string;
  psalm_excerpt: string;
  psalm_full?: string;
  second_reading: string;
  second_reading_excerpt: string;
  second_reading_full?: string;
  gospel: string;
  gospel_excerpt: string;
  gospel_full?: string;
  gospel_acclamation: string;
  gospel_acclamation_excerpt: string;
  gospel_acclamation_full?: string;
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

export type JournalKind = "free" | "examen" | "examination" | "catechism";

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
  rite?: RiteKey | string;
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
  // Community-submitted churches carry these so the UI can render a credit
  // badge ("Added by …") and offer a flag button.
  source?: "osm" | "community" | string;
  submitted_by_name?: string;
  // Editor count from community overlays — UI shows "Edited by N people".
  editor_count?: number;
  contributors?: string[];
  last_edited_by?: string | null;
};

export type ChurchOverlay = {
  church_id: string;
  mass_times: string[];
  confession_times: string[];
  website: string;
  phone: string;
  notes: string;
  editor_count: number;
  contributors?: string[];
  last_edited_by?: string | null;
  updated_at: string | null;
};

// ---- Parish Events ----
export type ParishEventType =
  | "mass"
  | "confession"
  | "adoration"
  | "talk"
  | "retreat"
  | "service"
  | "young_adult"
  | "social"
  | "rosary"
  | "other";

export type EventRecurrence = "once" | "weekly" | "biweekly" | "monthly" | "annually";

export type ParishEvent = {
  id: string;
  type: ParishEventType;
  type_label: string;
  title: string;
  description: string;
  start_at: string; // ISO
  end_at: string | null;
  recurrence?: EventRecurrence;
  recurrence_label?: string;
  occurrence_key?: string;
  church_id: string | null;
  church_name: string | null;
  address: string;
  lat: number;
  lng: number;
  organizer_user_id: string;
  organizer_name: string;
  created_at: string;
  flag_count: number;
  going?: boolean;
  going_count?: number;
  is_owner: boolean;
  has_flagged: boolean;
  distance_km?: number;
};

export async function rsvpEvent(id: string): Promise<{ going: boolean; going_count: number }> {
  return await api(`/parish-events/${id}/rsvp`, { method: "POST", body: {} });
}

export async function listAttendingEvents(days = 120): Promise<{ items: ParishEvent[] }> {
  return await api(`/parish-events/mine/attending?days=${days}`);
}

// ---- Community types ----
export type CommunityTopic = { slug: string | null; label: string; icon: string };
export type CommunityUserPublic = { user_id: string; name: string; picture: string | null | undefined; denomination?: string | null; tradition_path?: string | null; age?: number | null };

export type CommunityChallengeRef = {
  slug: string;
  name?: string | null;
  day_index?: number | null;
  day_title?: string | null;
  color?: string | null;
  icon?: string | null;
};

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
  challenge?: CommunityChallengeRef | null;
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
  is_group: boolean;
  name: string | null;
  auto_name?: string | null;
  members?: CommunityUserPublic[] | null;
  created_by?: string | null;
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

// ---- Friendships ----
export type FriendStatus = "none" | "pending" | "accepted" | "self";

export type Friendship = {
  friendship_id: string;
  user: CommunityUserPublic | null;
  status: "pending" | "accepted";
  requested_by: string;
  created_at: string;
  accepted_at: string | null;
};

export async function friendStatus(userId: string): Promise<{ status: FriendStatus; requested_by: string | null }> {
  return await api(`/community/friends/status/${encodeURIComponent(userId)}`);
}

export async function friendRequest(userId: string): Promise<Friendship> {
  return await api(`/community/friends/request`, { method: "POST", body: { user_id: userId } });
}

export async function friendAccept(userId: string): Promise<Friendship> {
  return await api(`/community/friends/accept`, { method: "POST", body: { user_id: userId } });
}

export async function friendDecline(userId: string): Promise<{ ok: boolean }> {
  return await api(`/community/friends/decline`, { method: "POST", body: { user_id: userId } });
}

export async function friendRemove(userId: string): Promise<{ ok: boolean }> {
  return await api(`/community/friends/${encodeURIComponent(userId)}`, { method: "DELETE" });
}

export async function friendList(status: "accepted" | "incoming" | "outgoing" = "accepted"): Promise<{ items: Friendship[]; count: number }> {
  return await api(`/community/friends/list?status=${status}`);
}

// ---- Community Prayer Journal (shared intentions) ----
export type PrayerIntention = {
  prayer_id: string;
  body: string;
  anonymous: boolean;
  author: { user_id: string; name: string; picture?: string | null } | null;
  created_at: string;
  pray_count: number;
  prayed_by_me: boolean;
  is_mine: boolean;
};

export async function listPrayerIntentions(before?: string): Promise<{ items: PrayerIntention[]; next_cursor: string | null }> {
  const q = before ? `?before=${encodeURIComponent(before)}` : "";
  return await api(`/community/prayers${q}`);
}

export async function createPrayerIntention(body: string, anonymous = false): Promise<PrayerIntention> {
  return await api(`/community/prayers`, { method: "POST", body: { body, anonymous } });
}

export async function togglePrayForIntention(prayerId: string): Promise<{ prayed: boolean; pray_count: number }> {
  return await api(`/community/prayers/${encodeURIComponent(prayerId)}/pray`, { method: "POST" });
}

export async function deletePrayerIntention(prayerId: string): Promise<{ ok: boolean }> {
  return await api(`/community/prayers/${encodeURIComponent(prayerId)}`, { method: "DELETE" });
}

// ---- App-wide Bookmarks ----
export type BookmarkKind = "prayer" | "bible" | "catechism" | "book" | "encyclical";

export type Bookmark = {
  bookmark_id: string;
  kind: BookmarkKind;
  ref_id: string;
  title: string;
  subtitle?: string | null;
  route: string;
  params: Record<string, string>;
  created_at: string;
};

export type BookmarkInput = {
  kind: BookmarkKind;
  ref_id: string;
  title: string;
  subtitle?: string;
  route: string;
  params?: Record<string, string>;
};

export async function listBookmarks(kind?: BookmarkKind): Promise<{ items: Bookmark[] }> {
  const q = kind ? `?kind=${kind}` : "";
  return await api(`/bookmarks${q}`);
}

export async function addBookmark(input: BookmarkInput): Promise<Bookmark> {
  return await api(`/bookmarks`, { method: "POST", body: input });
}

export async function removeBookmark(kind: BookmarkKind, refId: string): Promise<{ ok: boolean }> {
  return await api(`/bookmarks?kind=${kind}&ref_id=${encodeURIComponent(refId)}`, { method: "DELETE" });
}

// ---- Group DMs ----
export async function dmCreateGroup(memberIds: string[], name?: string | null): Promise<CommunityDMThread> {
  return await api(`/community/dm/threads/group`, {
    method: "POST",
    body: { member_ids: memberIds, name: name ?? null },
  });
}

// ---- Unread DM notification badge ----
export type DMUnreadResponse = {
  total: number;
  threads: { thread_id: string; unread: number }[];
};

export async function getDMUnreadCount(): Promise<DMUnreadResponse> {
  return await api<DMUnreadResponse>(`/community/dm/unread-count`);
}

export async function dmRenameGroup(threadId: string, name: string | null): Promise<CommunityDMThread> {
  return await api(`/community/dm/threads/${encodeURIComponent(threadId)}/name`, {
    method: "PUT",
    body: { name },
  });
}

export async function dmAddGroupMember(threadId: string, userId: string): Promise<CommunityDMThread> {
  return await api(`/community/dm/threads/${encodeURIComponent(threadId)}/members`, {
    method: "POST",
    body: { user_id: userId },
  });
}

export async function dmRemoveGroupMember(threadId: string, userId: string): Promise<{ ok: boolean; deleted: boolean }> {
  return await api(`/community/dm/threads/${encodeURIComponent(threadId)}/members/${encodeURIComponent(userId)}`, {
    method: "DELETE",
  });
}

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

// ---- Catechism in 90 seconds ----
export type CatechismTeaching = {
  id: string;
  ccc_ref: string;
  theme: string;
  title: string;
  quote: string;
  expansion: string;
  reflection_prompt: string;
  date: string | null;
  saved_to_journal: boolean;
  reflection: string | null;
};

export type CatechismReflectResponse = {
  reflection: string;
  teaching_id: string;
};


// ---- Legal & Support ----
export type LegalSection = { title: string; body: string };
export type PrivacyPolicyResponse = {
  app: string;
  last_updated: string;
  support_email: string;
  sections: LegalSection[];
};

export type FAQItem = { q: string; a: string };
export type SupportInfoResponse = {
  app: string;
  last_updated: string;
  support_email: string;
  faq: FAQItem[];
};

export async function getPrivacyPolicy(): Promise<PrivacyPolicyResponse> {
  return await api(`/legal/privacy.json`, { auth: false });
}

export async function getSupportInfo(): Promise<SupportInfoResponse> {
  return await api(`/legal/support.json`, { auth: false });
}

export async function submitSupportTicket(payload: {
  subject: string;
  message: string;
  email?: string;
  category?: string;
}): Promise<{ ok: boolean; ticket_id: string; message: string }> {
  return await api(`/legal/support/contact`, { method: "POST", body: payload });
}


// ---- Saints of the Day ----
export type SaintRank = "saint" | "blessed" | "venerable";
export type SaintPublic = {
  saint_id: string;
  name: string;
  rank: SaintRank;
  feast_date: string | null; // MM-DD
  is_primary: boolean;
  picture_url: string | null;
  picture_source: string | null;
  quote: string;
  quote_source: string;
  biography: string;
  recommended_action: string;
};
export type SaintAdmin = SaintPublic & {
  status: "draft" | "approved" | "rejected";
  proposed_by_ai: boolean;
  proposed_at: string | null;
  approved_at: string | null;
  approved_by: string | null;
  last_shown_at: string | null;
};
export type SaintsTodayResponse = {
  date: string;
  primary: SaintPublic | null;
  others: SaintPublic[];
};

export async function getSaintsToday(date: string): Promise<SaintsTodayResponse> {
  return await api(`/saints/today?date=${encodeURIComponent(date)}`);
}

export async function getSaint(saintId: string): Promise<SaintPublic> {
  return await api(`/saints/${encodeURIComponent(saintId)}`);
}

export async function adminListSaints(status?: string): Promise<{ items: SaintAdmin[]; count: number }> {
  const qs = status ? `?status=${encodeURIComponent(status)}&limit=500` : "?limit=500";
  return await api(`/saints/admin/list${qs}`);
}

export async function adminProposeSaint(payload: {
  date: string;
  rank_hint?: string;
  name_hint?: string;
  is_primary?: boolean;
}): Promise<SaintAdmin> {
  return await api(`/saints/admin/propose`, { method: "POST", body: payload });
}

export async function adminUpdateSaint(saintId: string, patch: Partial<SaintPublic>): Promise<SaintAdmin> {
  return await api(`/saints/admin/${encodeURIComponent(saintId)}`, { method: "PATCH", body: patch });
}

export async function adminApproveSaint(saintId: string): Promise<SaintAdmin> {
  return await api(`/saints/admin/${encodeURIComponent(saintId)}/approve`, { method: "POST" });
}

export async function adminRejectSaint(saintId: string): Promise<{ ok: boolean }> {
  return await api(`/saints/admin/${encodeURIComponent(saintId)}/reject`, { method: "POST" });
}

export async function adminDeleteSaint(saintId: string): Promise<{ ok: boolean }> {
  return await api(`/saints/admin/${encodeURIComponent(saintId)}`, { method: "DELETE" });
}

// ===== Shop =====

export type ShopProduct = {
  product_id: string;
  name: string;
  description: string;
  price_cents: number;
  currency: string;
  image_url?: string | null;
  stock?: number | null;
  status: "active" | "archived";
  shipping_amount_cents: number;
};

export type ShopOrder = {
  order_id: string;
  user_id: string;
  product_id: string;
  product_name?: string | null;
  product_image_url?: string | null;
  quantity: number;
  currency: string;
  unit_amount_cents?: number;
  shipping_amount_cents: number;
  total_cents?: number;
  status: "pending" | "paid" | "cancelled" | "failed";
  shipping_details?: any;
  customer_email?: string | null;
  tracking_number?: string | null;
  created_at?: string | null;
  paid_at?: string | null;
};

export async function listShopProducts(): Promise<{
  products: ShopProduct[];
  shipping_amount_cents: number;
  currency: string;
}> {
  return await api(`/shop/products`);
}

export async function getShopProduct(productId: string): Promise<ShopProduct> {
  return await api(`/shop/products/${encodeURIComponent(productId)}`);
}

export async function createShopCheckout(body: {
  product_id: string;
  quantity?: number;
  return_origin: string;
  client_token?: string;
}): Promise<{ url: string; order_id: string }> {
  return await api(`/shop/checkout`, { method: "POST", body });
}

export async function reconcileShopSession(
  sessionId: string,
): Promise<{ order: ShopOrder; payment_status: string }> {
  return await api(`/shop/reconcile/${encodeURIComponent(sessionId)}`, { method: "POST" });
}

export async function listMyOrders(): Promise<{ orders: ShopOrder[] }> {
  return await api(`/shop/orders`);
}

export async function getMyOrder(orderId: string): Promise<ShopOrder> {
  return await api(`/shop/orders/${encodeURIComponent(orderId)}`);
}

// ----- Admin shop -----

export async function adminListProducts(): Promise<{ products: ShopProduct[] }> {
  return await api(`/shop/admin/products`);
}

export async function adminCreateProduct(body: {
  name: string;
  description?: string;
  price_cents: number;
  image_url?: string | null;
  stock?: number | null;
}): Promise<ShopProduct> {
  return await api(`/shop/admin/products`, { method: "POST", body });
}

export async function adminUpdateProduct(
  productId: string,
  body: Partial<{
    name: string;
    description: string;
    price_cents: number;
    image_url: string | null;
    stock: number | null;
    status: "active" | "archived";
  }>,
): Promise<ShopProduct> {
  return await api(`/shop/admin/products/${encodeURIComponent(productId)}`, {
    method: "PATCH",
    body,
  });
}

export async function adminArchiveProduct(productId: string): Promise<{ ok: boolean }> {
  return await api(`/shop/admin/products/${encodeURIComponent(productId)}`, { method: "DELETE" });
}

export async function adminListOrders(params?: { status?: string }): Promise<{
  orders: ShopOrder[];
}> {
  const qs = params?.status ? `?status=${encodeURIComponent(params.status)}` : "";
  return await api(`/shop/admin/orders${qs}`);
}

export async function adminSetOrderTracking(
  orderId: string,
  tracking_number: string,
): Promise<ShopOrder> {
  return await api(`/shop/admin/orders/${encodeURIComponent(orderId)}/tracking`, {
    method: "POST",
    body: { tracking_number },
  });
}


// ===== Charity Hub =====

export type CharityCategory =
  | "food_bank" | "homeless" | "pro_life" | "education" | "missions"
  | "youth" | "elderly" | "refugees" | "healthcare" | "disability"
  | "addiction_recovery" | "prison_ministry" | "general";

export type CharityStatus = "pending" | "approved" | "archived" | "rejected";

export type Charity = {
  charity_id: string;
  name: string;
  mission: string;
  category: CharityCategory;
  city: string;
  state: string;
  country: string;
  website?: string | null;
  email?: string | null;
  phone?: string | null;
  logo_url?: string | null;
  status: CharityStatus;
  claimed_by?: string | null;
  created_at?: string | null;
  approved_at?: string | null;
  submitted_by?: string | null;
  approved_by?: string | null;
  claim_status?: string | null;
  updated_at?: string | null;
};

export type CharityCategoryLabel = { key: CharityCategory; label: string };

export async function listCharities(params?: {
  q?: string;
  category?: string;
  state?: string;
  country?: string;
  limit?: number;
  offset?: number;
}): Promise<{ items: Charity[]; total: number; categories: CharityCategory[] }> {
  const qs = new URLSearchParams();
  if (params?.q) qs.set("q", params.q);
  if (params?.category) qs.set("category", params.category);
  if (params?.state) qs.set("state", params.state);
  if (params?.country) qs.set("country", params.country);
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.offset) qs.set("offset", String(params.offset));
  const s = qs.toString();
  return await api(`/charities${s ? `?${s}` : ""}`);
}

export async function getCharityCategories(): Promise<{ categories: CharityCategoryLabel[] }> {
  return await api(`/charities/categories`);
}

export async function getCharity(charityId: string): Promise<Charity> {
  return await api(`/charities/${encodeURIComponent(charityId)}`);
}

export async function submitCharity(body: {
  name: string;
  mission: string;
  category: string;
  city?: string;
  state?: string;
  country?: string;
  website?: string | null;
  email?: string | null;
  phone?: string | null;
  logo_url?: string | null;
}): Promise<Charity> {
  return await api(`/charities/submit`, { method: "POST", body });
}

export async function listMyCharitySubmissions(): Promise<{ items: Charity[] }> {
  return await api(`/charities/mine/submissions`);
}

export async function requestCharityClaim(
  charityId: string,
  message: string,
): Promise<{ ok: boolean; claim_id: string; status: string }> {
  return await api(`/charities/${encodeURIComponent(charityId)}/claim`, {
    method: "POST",
    body: { message },
  });
}

export async function contactCharity(
  charityId: string,
  message: string,
): Promise<{ ok: boolean; contact_id: string; charity_email?: string | null; note: string }> {
  return await api(`/charities/${encodeURIComponent(charityId)}/contact`, {
    method: "POST",
    body: { message },
  });
}

// ----- Admin -----

export async function adminListCharities(status?: string): Promise<{ items: Charity[] }> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return await api(`/charities/admin/list${qs}`);
}

export async function adminApproveCharity(charityId: string): Promise<Charity> {
  return await api(`/charities/admin/${encodeURIComponent(charityId)}/approve`, { method: "POST" });
}

export async function adminRejectCharity(charityId: string): Promise<{ ok: boolean }> {
  return await api(`/charities/admin/${encodeURIComponent(charityId)}/reject`, { method: "POST" });
}

export async function adminPatchCharity(
  charityId: string,
  body: Partial<Charity>,
): Promise<Charity> {
  return await api(`/charities/admin/${encodeURIComponent(charityId)}`, {
    method: "PATCH",
    body,
  });
}

export async function adminArchiveCharity(charityId: string): Promise<{ ok: boolean }> {
  return await api(`/charities/admin/${encodeURIComponent(charityId)}`, { method: "DELETE" });
}

export async function adminListCharityClaims(status: string = "pending"): Promise<{
  items: Array<{
    claim_id: string;
    charity_id: string;
    charity_name?: string | null;
    charity_location?: string | null;
    user_id: string;
    user_email?: string | null;
    user_name?: string | null;
    message?: string | null;
    status: string;
    requested_at?: string | null;
  }>;
}> {
  return await api(`/charities/admin/claims?status=${encodeURIComponent(status)}`);
}

export async function adminApproveClaim(claimId: string): Promise<{ ok: boolean }> {
  return await api(`/charities/admin/claims/${encodeURIComponent(claimId)}/approve`, { method: "POST" });
}

export async function adminRejectClaim(claimId: string): Promise<{ ok: boolean }> {
  return await api(`/charities/admin/claims/${encodeURIComponent(claimId)}/reject`, { method: "POST" });
}

export async function adminListCharityContacts(charityId?: string): Promise<{
  items: Array<{
    contact_id: string;
    charity_id: string;
    user_id: string;
    user_email?: string | null;
    user_name?: string | null;
    message?: string | null;
    created_at?: string | null;
  }>;
}> {
  const qs = charityId ? `?charity_id=${encodeURIComponent(charityId)}` : "";
  return await api(`/charities/admin/contacts${qs}`);
}

// ===== Charity Quotes =====

export interface CharityQuoteApi {
  quote_id: string;
  text: string;
  source: string;
  context?: string | null;
}

export interface AdminCharityQuoteApi extends CharityQuoteApi {
  active: boolean;
  seed: boolean;
  created_by?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export async function listCharityQuotes(): Promise<{ items: CharityQuoteApi[] }> {
  return await api(`/charities/quotes`);
}

export async function adminListCharityQuotes(): Promise<{ items: AdminCharityQuoteApi[] }> {
  return await api(`/charities/admin/quotes`);
}

export async function adminCreateCharityQuote(payload: {
  text: string;
  source: string;
  context?: string | null;
  active?: boolean;
}): Promise<AdminCharityQuoteApi> {
  return await api(`/charities/admin/quotes`, {
    method: "POST",
    body: JSON.stringify({
      text: payload.text,
      source: payload.source,
      context: payload.context ?? null,
      active: payload.active !== false,
    }),
  });
}

export async function adminUpdateCharityQuote(
  quoteId: string,
  payload: { text?: string; source?: string; context?: string | null; active?: boolean },
): Promise<AdminCharityQuoteApi> {
  return await api(`/charities/admin/quotes/${encodeURIComponent(quoteId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function adminToggleCharityQuote(quoteId: string): Promise<AdminCharityQuoteApi> {
  return await api(`/charities/admin/quotes/${encodeURIComponent(quoteId)}/toggle`, { method: "POST" });
}

export async function adminDeleteCharityQuote(quoteId: string): Promise<{ ok: boolean }> {
  return await api(`/charities/admin/quotes/${encodeURIComponent(quoteId)}`, { method: "DELETE" });
}


// ===== Liturgical Challenges =====

export type ChallengeSlug = "hallowtide" | "advent" | "lent" | string;
export type ChallengeStatus = "draft" | "published" | "archived";

export type ChallengePrayerItem = {
  item_id?: string;
  kind: string;
  title: string;
  detail?: string | null;
};

export type ChallengePrepRecipe = {
  yield?: string;
  ingredients?: string[];
  steps?: string[];
};

export type ChallengePrepContent = {
  title?: string;
  intro?: string;
  recipe?: ChallengePrepRecipe;
  encouragement?: string;
} | null;

export type ChallengeSummary = {
  challenge_id: string;
  slug: ChallengeSlug;
  name: string;
  subtitle?: string | null;
  season?: string | null;
  color?: string | null;
  icon?: string | null;
  patron_saint?: string | null;
  blurb?: string | null;
  opening_prayer?: string | null;
  closing_prayer?: string | null;
  preparation_content?: ChallengePrepContent;
  start_date: string | null; // ISO datetime
  end_date: string | null;
  status: ChallengeStatus;
  total_days: number;
  published_days: number;
  enrolled?: boolean;
  completed_days?: number;
  streak?: number;
};

export type ChallengeDay = {
  day_id: string;
  challenge_id: string;
  day_index: number;
  date: string | null;
  title?: string | null;
  theme?: string | null;
  patron_saint?: string | null;
  patron_blurb?: string | null;
  reflection?: string | null;
  prayer_items: ChallengePrayerItem[];
  status: "draft" | "published";
};

export type ChallengeEnrollment = {
  joined_at?: string | null;
  start_date?: string | null;
  current_streak: number;
  total_days_completed: number;
  last_checkin_date?: string | null;
};

export type ChallengeTodayCheckin = {
  items_done: string[];
  reflection: string | null;
  completed: boolean;
};

export type ChallengeDetail = ChallengeSummary & {
  days: ChallengeDay[];
  enrolled: boolean;
  enrollment?: ChallengeEnrollment;
  today_checkin?: ChallengeTodayCheckin | null;
};

export type AdminChallenge = ChallengeSummary & {
  ai_generation_notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export async function listChallenges(): Promise<{ items: ChallengeSummary[] }> {
  return await api(`/challenges`);
}

export type ChallengeWindow = {
  challenge_id: string;
  slug: ChallengeSlug;
  name: string;
  subtitle?: string | null;
  season?: string | null;
  color?: string | null;
  icon?: string | null;
  patron_saint?: string | null;
  start_date: string; // ISO date (YYYY-MM-DD)
  end_date: string;
  total_days: number;
  status: ChallengeStatus;
};

// Every liturgical challenge's window computed for a given calendar year, so
// the calendar can overlay all tracks in whatever year is being browsed.
export async function listChallengeWindows(year: number): Promise<{ items: ChallengeWindow[] }> {
  return await api(`/challenges/windows?year=${year}`);
}

// ---- Custom (user-created) challenges ----
export type CustomChallengeItem = { category: string; text: string };
export type CustomChallengeDay = { day: number; items: CustomChallengeItem[] };
export type CustomChallenge = {
  challenge_id: string;
  title: string;
  color: string;
  length_days: number;
  start_date: string;
  end_date: string;
  days: CustomChallengeDay[];
  completed: Record<string, boolean>;
  created_at?: string | null;
};

export const CUSTOM_CHALLENGE_CATEGORIES: { key: string; label: string; icon: string }[] = [
  { key: "abstinence", label: "Abstinence", icon: "remove-circle-outline" },
  { key: "prayer", label: "Prayer / Devotional", icon: "book-outline" },
  { key: "charity", label: "Work of Charity", icon: "heart-outline" },
  { key: "adoration", label: "Adoration", icon: "flame-outline" },
  { key: "virtue", label: "Virtue to grow", icon: "leaf-outline" },
  { key: "other", label: "Other", icon: "ellipse-outline" },
];

export async function createCustomChallenge(payload: {
  title: string;
  color?: string;
  length_days: number;
  start_date: string;
  days: CustomChallengeDay[];
}): Promise<CustomChallenge> {
  return await api("/custom-challenges", { method: "POST", body: payload });
}

export async function listCustomChallenges(): Promise<{ items: CustomChallenge[] }> {
  return await api("/custom-challenges");
}

export async function listCustomChallengeWindows(year: number): Promise<{ items: ChallengeWindow[] }> {
  return await api(`/custom-challenges/windows?year=${year}`);
}

export async function getCustomChallenge(id: string): Promise<CustomChallenge> {
  return await api(`/custom-challenges/${encodeURIComponent(id)}`);
}

export async function checkinCustomChallenge(
  id: string,
  day: number,
  itemIndex: number,
  done: boolean,
): Promise<CustomChallenge> {
  return await api(`/custom-challenges/${encodeURIComponent(id)}/checkin`, {
    method: "POST",
    body: { day, item_index: itemIndex, done },
  });
}

export async function deleteCustomChallenge(id: string): Promise<{ ok: boolean }> {
  return await api(`/custom-challenges/${encodeURIComponent(id)}`, { method: "DELETE" });
}

// ---- Personal prayers & devotionals ----
export type MyPrayer = { prayer_id: string; title: string; body: string; created_at?: string | null };
export type MyDevotion = {
  devotion_id: string;
  title: string;
  saint_name: string;
  saint_slug?: string | null;
  intro: string;
  practices: string[];
  created_at?: string | null;
};

export async function createMyPrayer(payload: { title: string; body: string }): Promise<MyPrayer> {
  return await api("/my/prayers", { method: "POST", body: payload });
}
export async function listMyPrayers(): Promise<{ items: MyPrayer[] }> {
  return await api("/my/prayers");
}
export async function deleteMyPrayer(id: string): Promise<{ ok: boolean }> {
  return await api(`/my/prayers/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export async function createMyDevotion(payload: {
  title: string;
  saint_name: string;
  saint_slug?: string | null;
  intro?: string;
  practices: string[];
}): Promise<MyDevotion> {
  return await api("/my/devotions", { method: "POST", body: payload });
}
export async function listMyDevotions(): Promise<{ items: MyDevotion[] }> {
  return await api("/my/devotions");
}
export async function getMyDevotion(id: string): Promise<MyDevotion> {
  return await api(`/my/devotions/${encodeURIComponent(id)}`);
}
export async function deleteMyDevotion(id: string): Promise<{ ok: boolean }> {
  return await api(`/my/devotions/${encodeURIComponent(id)}`, { method: "DELETE" });
}

// ---- Vestments reference ----
export type Vestment = { name: string; meaning: string; image: string | null };
export type VestmentRite = { key: string; label: string; blurb: string; vestments: Vestment[] };
export async function getVestments(): Promise<{ rites: VestmentRite[] }> {
  return await api("/vestments");
}

// ---- Traditional Latin Mass (1962) readings ----
export type TLMReadingPart = { citation: string; verses: { n: number; text: string }[] };
export type TLMReadings = {
  date: string;
  available: boolean;
  proper_key?: string;
  feria_fallback?: boolean;
  epistle?: TLMReadingPart;
  gospel?: TLMReadingPart;
};
export async function getTLMReadings(date: string): Promise<TLMReadings> {
  return await api(`/tridentine/readings?date=${encodeURIComponent(date)}`);
}

// ---- Byzantine (Eastern Catholic) Divine Liturgy readings ----
export type ByzantineReadingPart = { citation: string; verses: { n: number; text: string; ch?: number }[] };
export type ByzantineReadings = {
  date: string;
  available: boolean;
  proper_key?: string;
  feria_fallback?: boolean;
  calendar?: string;
  epistle?: ByzantineReadingPart;
  gospel?: ByzantineReadingPart;
};
export async function getByzantineReadings(date: string, calendar = "new"): Promise<ByzantineReadings> {
  return await api(`/eastern/readings?date=${encodeURIComponent(date)}&calendar=${calendar}`);
}


export async function getChallenge(slug: string): Promise<ChallengeDetail> {
  return await api(`/challenges/${encodeURIComponent(slug)}`);
}

export type ChallengeStartOption = "today" | "tomorrow" | "liturgical";

export async function enrollChallenge(
  slug: string,
  startOption: ChallengeStartOption = "liturgical",
): Promise<{ ok: boolean; already?: boolean; start_date?: string }> {
  return await api(`/challenges/${encodeURIComponent(slug)}/enroll`, {
    method: "POST",
    body: { start_option: startOption },
  });
}

export async function unenrollChallenge(slug: string): Promise<{ ok: boolean; removed?: number }> {
  return await api(`/challenges/${encodeURIComponent(slug)}/enroll`, { method: "DELETE" });
}

export async function checkinChallenge(
  slug: string,
  payload: { date: string; items_done?: string[]; reflection?: string | null; completed?: boolean },
): Promise<{ ok: boolean; current_streak: number; total_days_completed: number }> {
  return await api(`/challenges/${encodeURIComponent(slug)}/checkin`, {
    method: "POST",
    body: {
      date: payload.date,
      items_done: payload.items_done ?? [],
      reflection: payload.reflection ?? null,
      completed: payload.completed !== false,
    },
  });
}

export async function getChallengeProgress(slug: string): Promise<{
  enrolled: boolean;
  current_streak: number;
  longest_streak: number;
  total_days_completed: number;
  checkins: Array<{ date_str: string; items_done: string[]; completed: boolean; reflection?: string | null }>;
}> {
  return await api(`/challenges/${encodeURIComponent(slug)}/my-progress`);
}

// ---- Admin ----

export async function adminListChallenges(): Promise<{ items: AdminChallenge[] }> {
  return await api(`/challenges/admin/all`);
}

export async function adminPatchChallenge(
  slug: string,
  body: Partial<{
    name: string;
    subtitle: string;
    blurb: string;
    patron_saint: string;
    opening_prayer: string;
    closing_prayer: string;
    preparation_content: ChallengePrepContent;
    start_date: string;
    end_date: string;
    status: ChallengeStatus;
  }>,
): Promise<AdminChallenge> {
  return await api(`/challenges/admin/${encodeURIComponent(slug)}`, { method: "PATCH", body });
}

export async function adminListChallengeDays(slug: string): Promise<{ items: ChallengeDay[] }> {
  return await api(`/challenges/admin/${encodeURIComponent(slug)}/days`);
}

export async function adminPatchChallengeDay(
  dayId: string,
  body: Partial<{
    title: string;
    theme: string;
    patron_saint: string;
    patron_blurb: string;
    reflection: string;
    prayer_items: ChallengePrayerItem[];
    status: "draft" | "published";
  }>,
): Promise<ChallengeDay> {
  return await api(`/challenges/admin/days/${encodeURIComponent(dayId)}`, { method: "PATCH", body });
}

export async function adminGenerateChallengeDays(
  slug: string,
  body: { overwrite?: boolean; days?: string[] } = {},
): Promise<{
  ok: boolean;
  results: Array<{ day_index: number; date: string; day_id?: string; skipped?: boolean }>;
  failures: Array<{ day_index: number; date: string; error: string }>;
}> {
  return await api(`/challenges/admin/${encodeURIComponent(slug)}/generate-days`, {
    method: "POST",
    body,
  });
}

export async function adminPublishChallenge(slug: string): Promise<AdminChallenge> {
  return await api(`/challenges/admin/${encodeURIComponent(slug)}/publish`, { method: "POST" });
}

export async function adminUnpublishChallenge(slug: string): Promise<AdminChallenge> {
  return await api(`/challenges/admin/${encodeURIComponent(slug)}/unpublish`, { method: "POST" });
}



// ---- Companions (Phase 2: friends walking with you) ----
export type ChallengeCompanion = {
  user_id: string;
  name: string | null;
  picture: string | null;
  current_streak: number;
  total_days_completed: number;
};

export async function getChallengeCompanions(
  slug: string,
  limit: number = 20,
): Promise<{ items: ChallengeCompanion[]; total: number }> {
  return await api(
    `/challenges/${encodeURIComponent(slug)}/companions?limit=${limit}`,
  );
}

// ---- Share to Feed (Phase 2) ----
export async function createCommunityPost(payload: {
  body: string;
  topic?: string | null;
  image?: string | null;
  challenge?: CommunityChallengeRef | null;
}): Promise<CommunityPost> {
  return await api(`/community/posts`, {
    method: "POST",
    body: {
      body: payload.body,
      topic: payload.topic ?? null,
      image: payload.image ?? null,
      challenge: payload.challenge ?? null,
    },
  });
}

// ============================================================
// Sanctus Library (Phase 1: Books)
// ============================================================

export type LibraryChapter = {
  index: number;
  title: string;
  word_count: number;
  body_md?: string;
};

export type LibraryBook = {
  book_id: string;
  slug: string;
  title: string;
  author: string;
  year?: number | null;
  blurb?: string | null;
  tradition: string;
  cover_color?: string | null;
  cover_icon?: string | null;
  type: "embedded" | "external";
  source_url?: string | null;
  status: string;
  chapter_count: number;
  chapters: LibraryChapter[];
  is_premium?: boolean;
  progress?: {
    chapter_index: number;
    scroll_pct: number;
    updated_at: string;
  } | null;
};

export type LibraryChapterDetail = {
  book_id: string;
  slug: string;
  chapter_index: number;
  title: string;
  subtitle?: string;
  body_md: string;
  is_last: boolean;
  word_count: number;
};

export async function listLibraryBooks(): Promise<{ items: LibraryBook[]; total: number }> {
  return await api(`/library/books`);
}

export async function getLibraryBook(slug: string): Promise<LibraryBook> {
  return await api(`/library/books/${encodeURIComponent(slug)}`);
}

export async function getLibraryChapter(
  slug: string,
  idx: number,
): Promise<LibraryChapterDetail> {
  return await api(`/library/books/${encodeURIComponent(slug)}/chapters/${idx}`);
}

export async function saveLibraryProgress(
  slug: string,
  chapter_index: number,
  scroll_pct: number = 0,
): Promise<{ ok: boolean }> {
  return await api(`/library/books/${encodeURIComponent(slug)}/progress`, {
    method: "POST",
    body: { chapter_index, scroll_pct },
  });
}

// ---- Admin ----
export async function adminListLibraryBooks(): Promise<{ items: LibraryBook[]; total: number }> {
  return await api(`/library/admin/books`);
}

export type LibraryBookCreate = {
  slug: string;
  title: string;
  author: string;
  year?: number | null;
  blurb?: string | null;
  tradition?: string;
  cover_color?: string | null;
  cover_icon?: string | null;
  type: "embedded" | "external";
  source_url?: string | null;
  chapters?: { title: string; body_md: string }[];
  status?: "draft" | "published";
};

export async function adminCreateLibraryBook(payload: LibraryBookCreate): Promise<LibraryBook> {
  return await api(`/library/admin/books`, { method: "POST", body: payload });
}

export async function adminPatchLibraryBook(
  slug: string,
  patch: Partial<LibraryBookCreate>,
): Promise<LibraryBook> {
  return await api(`/library/admin/books/${encodeURIComponent(slug)}`, {
    method: "PATCH",
    body: patch,
  });
}

export async function adminDeleteLibraryBook(slug: string): Promise<{ ok: boolean }> {
  return await api(`/library/admin/books/${encodeURIComponent(slug)}`, { method: "DELETE" });
}

export async function adminUpsertLibraryChapter(
  slug: string,
  payload: { index?: number | null; title: string; body_md: string },
): Promise<{ ok: boolean; chapter_index: number; chapter_count: number }> {
  return await api(`/library/admin/books/${encodeURIComponent(slug)}/chapters`, {
    method: "POST",
    body: payload,
  });
}

export async function adminDeleteLibraryChapter(
  slug: string,
  idx: number,
): Promise<{ ok: boolean; chapter_count: number }> {
  return await api(`/library/admin/books/${encodeURIComponent(slug)}/chapters/${idx}`, {
    method: "DELETE",
  });
}

// ============================================================
// Sanctus Library — Phase 2: Radio
// ============================================================

export type LibraryStation = {
  station_id: string;
  slug: string;
  name: string;
  blurb?: string | null;
  country?: string | null;
  language?: string | null;
  stream_url: string;
  website_url?: string | null;
  accent_color?: string | null;
  icon?: string | null;
  status: string;
};

export type LibraryStationCreate = {
  slug: string;
  name: string;
  blurb?: string | null;
  country?: string | null;
  language?: string | null;
  stream_url: string;
  website_url?: string | null;
  accent_color?: string | null;
  icon?: string | null;
  status?: "draft" | "published";
};

export async function listLibraryStations(): Promise<{ items: LibraryStation[]; total: number }> {
  return await api(`/library/radio`);
}

export async function adminListLibraryStations(): Promise<{ items: LibraryStation[]; total: number }> {
  return await api(`/library/admin/radio`);
}

export async function adminCreateLibraryStation(payload: LibraryStationCreate): Promise<LibraryStation> {
  return await api(`/library/admin/radio`, { method: "POST", body: payload });
}

export async function adminPatchLibraryStation(
  slug: string,
  patch: Partial<LibraryStationCreate>,
): Promise<LibraryStation> {
  return await api(`/library/admin/radio/${encodeURIComponent(slug)}`, {
    method: "PATCH",
    body: patch,
  });
}

export async function adminDeleteLibraryStation(slug: string): Promise<{ ok: boolean }> {
  return await api(`/library/admin/radio/${encodeURIComponent(slug)}`, { method: "DELETE" });
}

// ============================================================
// Sanctus Library — Phase 3: Films
// ============================================================

export type LibraryFilmCategory = "saints" | "doctrine" | "animated" | "documentary";

export type LibraryFilm = {
  film_id: string;
  slug: string;
  title: string;
  blurb?: string | null;
  youtube_id: string;
  duration_label?: string | null;
  category: LibraryFilmCategory;
  accent_color?: string | null;
  status: string;
};

export type LibraryFilmCreate = {
  slug: string;
  title: string;
  blurb?: string | null;
  youtube_id: string;
  duration_label?: string | null;
  category: LibraryFilmCategory;
  accent_color?: string | null;
  status?: "draft" | "published";
};

export async function listLibraryFilms(
  category?: LibraryFilmCategory,
): Promise<{ items: LibraryFilm[]; total: number }> {
  const qs = category ? `?category=${encodeURIComponent(category)}` : "";
  return await api(`/library/films${qs}`);
}

export async function getLibraryFilm(slug: string): Promise<LibraryFilm> {
  return await api(`/library/films/${encodeURIComponent(slug)}`);
}

export async function adminListLibraryFilms(): Promise<{ items: LibraryFilm[]; total: number }> {
  return await api(`/library/admin/films`);
}

export async function adminCreateLibraryFilm(payload: LibraryFilmCreate): Promise<LibraryFilm> {
  return await api(`/library/admin/films`, { method: "POST", body: payload });
}

export async function adminPatchLibraryFilm(
  slug: string,
  patch: Partial<LibraryFilmCreate>,
): Promise<LibraryFilm> {
  return await api(`/library/admin/films/${encodeURIComponent(slug)}`, {
    method: "PATCH",
    body: patch,
  });
}

export async function adminDeleteLibraryFilm(slug: string): Promise<{ ok: boolean }> {
  return await api(`/library/admin/films/${encodeURIComponent(slug)}`, { method: "DELETE" });
}


// ===== Sanctus Premium (Stripe Subscriptions) =====

export type PremiumPricing = {
  monthly: { amount_cents: number; interval: "month"; label: string };
  annual: { amount_cents: number; interval: "year"; label: string };
};

export type PremiumStatus = {
  is_premium: boolean;
  is_admin_premium: boolean;
  tier: "monthly" | "annual" | null;
  status: string | null;
  current_period_end: number | null;
  cancel_at_period_end: boolean;
  trial_end: number | null;
  pricing: PremiumPricing;
  trial_days: number;
  stripe_ready: boolean;
};

export async function getPremiumStatus(): Promise<PremiumStatus> {
  return await api<PremiumStatus>("/subscriptions/status");
}

export async function createPremiumCheckout(body: {
  plan: "monthly" | "annual";
  return_origin: string;
}): Promise<{ url: string | null; session_id?: string; plan?: string; already_premium?: boolean }> {
  return await api(`/subscriptions/create-checkout-session`, { method: "POST", body });
}

export async function reconcilePremiumSession(sessionId: string): Promise<{
  reconciled: boolean;
  premium: PremiumStatus["status"] extends infer _ ? Record<string, unknown> : never;
}> {
  return await api(`/subscriptions/reconcile/${encodeURIComponent(sessionId)}`, { method: "POST" });
}

export async function openPremiumPortal(return_origin: string): Promise<{ url: string }> {
  return await api(`/subscriptions/customer-portal`, {
    method: "POST",
    body: { return_origin },
  });
}


// ---------------------------------------------------------------------------
// Missals (Mass Hub)
// ---------------------------------------------------------------------------

export type MissalSummary = {
  slug: string;
  name: string;
  subtitle: string;
  tradition: string;
  language_note: string;
  accent_color: string;
  icon: string;
  vernacular_label: string;
  section_count: number;
};

export type MissalSectionMeta = {
  index: number;
  title: string;
  latin_title?: string | null;
  has_latin: boolean;
};

export type MissalDetail = MissalSummary & {
  intro: string;
  sections: MissalSectionMeta[];
};

export type MissalSection = {
  slug: string;
  missal_name: string;
  accent_color: string;
  vernacular_label: string;
  index: number;
  total: number;
  title: string;
  latin_title?: string | null;
  english: string;
  latin?: string | null;
  rubric?: string | null;
  note?: string | null;
  prev: number | null;
  next: number | null;
};

export async function listMissals(): Promise<{ items: MissalSummary[] }> {
  return await api(`/missals`);
}

export async function getMissal(slug: string): Promise<MissalDetail> {
  return await api(`/missals/${encodeURIComponent(slug)}`);
}

export async function getMissalSection(slug: string, idx: number): Promise<MissalSection> {
  return await api(`/missals/${encodeURIComponent(slug)}/sections/${idx}`);
}

// ---------------------------------------------------------------------------
// Liturgy of the Hours (Divine Office)
// ---------------------------------------------------------------------------

export type LiturgyHourSummary = {
  slug: string;
  name: string;
  subtitle: string;
  latin_name: string;
  icon: string;
  accent_color: string;
  time_of_day: string;
  duration: string;
  psalms_vary_by_day: boolean;
};

export type LiturgyDay = {
  key: string;
  name: string;
  latin_name: string;
  weekday_index: number;
};

export type LiturgyExternalLink = {
  url: string;
  label: string;
  description: string;
};

export type LiturgyIndex = {
  hours: LiturgyHourSummary[];
  days: LiturgyDay[];
  today: string;
  external_link: LiturgyExternalLink;
};

export type LiturgyHourDetail = LiturgyHourSummary & {
  intro: string;
  section_count_per_day: number;
  days: LiturgyDay[];
};

export type LiturgySection = {
  index: number;
  title: string;
  latin_title?: string | null;
  english: string;
  latin?: string | null;
  rubric?: string | null;
  note?: string | null;
};

export type LiturgyDayPayload = {
  hour: LiturgyHourSummary;
  day: LiturgyDay;
  today: string;
  sections: LiturgySection[];
};

export async function listLiturgyHours(): Promise<LiturgyIndex> {
  return await api(`/liturgy`);
}

export async function getLiturgyHour(slug: string): Promise<LiturgyHourDetail> {
  return await api(`/liturgy/${encodeURIComponent(slug)}`);
}

export async function getLiturgyDay(slug: string, dayKey: string): Promise<LiturgyDayPayload> {
  return await api(`/liturgy/${encodeURIComponent(slug)}/${encodeURIComponent(dayKey)}`);
}

// ---------------------------------------------------------------------------
// Virtus (virtues study + plans)
// ---------------------------------------------------------------------------

export type VirtueMeta = {
  slug: string;
  name: string;
  kind: "virtue" | "topic" | "saints";
  icon: string;
  accent_color: string;
  tagline: string;
  opposite_vice?: string | null;
};

export type VirtueListItem = VirtueMeta & { has_content: boolean };

export type VirtueSaint = { name: string; years?: string; why?: string; prayer?: string };
export type VirtueResource = { title: string; kind?: string; author?: string; description?: string };
export type SaintsByVirtue = { virtue: string; saints: VirtueSaint[] };

export type VirtueContent = VirtueMeta & {
  edited: boolean;
  is_premium_resources: boolean;
  has_resources: boolean;
  resource_count: number;
  user_is_premium: boolean;
  // virtue/topic kind
  what_is?: string;
  life_stages?: { singleness: string; dating: string; marriage: string };
  overcoming_vice?: string;
  saints?: VirtueSaint[];
  // saints kind
  intro?: string;
  saints_by_virtue?: SaintsByVirtue[];
  // admin full only
  resources?: VirtueResource[];
};

export type VirtuePlanGoal = {
  id: string;
  virtue_slug: string;
  type: "do" | "refrain";
  text: string;
  done: boolean;
  done_at?: string | null;
};

export type VirtuePlan = {
  id: string;
  virtue_slugs: string[];
  virtues: VirtueMeta[];
  start_date: string;
  end_date: string;
  days: number;
  note?: string | null;
  goals: VirtuePlanGoal[];
  total: number;
  completed: number;
  checkins: Record<string, string[]>;
  journal: Record<string, string>;
  days_logged: number;
  today: string;
  badge?: {
    tier: "gold" | "silver" | "bronze" | "none";
    fallen: number;
    completed_days: number;
    elapsed: number;
    gold_max: number;
    silver_max: number;
    final: boolean;
  };
  active: boolean;
  created_at: string;
};

export async function listVirtues(): Promise<{ items: VirtueListItem[]; user_is_premium: boolean; is_admin: boolean }> {
  return await api(`/virtues`);
}
export async function getVirtue(slug: string): Promise<VirtueContent> {
  return await api(`/virtues/${encodeURIComponent(slug)}`);
}
export async function getVirtueResources(slug: string): Promise<{ slug: string; resources: VirtueResource[] }> {
  return await api(`/virtues/${encodeURIComponent(slug)}/resources`);
}
export async function adminGetVirtue(slug: string): Promise<VirtueContent> {
  return await api(`/virtues/${encodeURIComponent(slug)}/admin`);
}
export async function adminEditVirtue(slug: string, body: Partial<{
  what_is: string;
  life_stages: { singleness?: string; dating?: string; marriage?: string };
  overcoming_vice: string;
  saints: VirtueSaint[];
  resources: VirtueResource[];
  intro: string;
  saints_by_virtue: SaintsByVirtue[];
}>): Promise<VirtueContent> {
  return await api(`/virtues/${encodeURIComponent(slug)}`, { method: "PUT", body });
}
export async function adminRegenerateVirtue(slug: string): Promise<VirtueContent> {
  return await api(`/virtues/${encodeURIComponent(slug)}/regenerate`, { method: "POST" });
}
export async function listVirtuePlans(): Promise<{ items: VirtuePlan[] }> {
  return await api(`/virtues/plans`);
}
export async function createVirtuePlan(body: { virtue_slugs: string[]; days: number; note?: string }): Promise<VirtuePlan> {
  return await api(`/virtues/plans`, { method: "POST", body });
}
export async function getVirtuePlan(id: string): Promise<VirtuePlan> {
  return await api(`/virtues/plans/${encodeURIComponent(id)}`);
}
export async function toggleVirtueGoal(planId: string, goalId: string): Promise<VirtuePlan> {
  return await api(`/virtues/plans/${encodeURIComponent(planId)}/goals/${encodeURIComponent(goalId)}/toggle`, { method: "POST" });
}
export async function checkinVirtueGoal(planId: string, date: string, goalId: string): Promise<VirtuePlan> {
  return await api(`/virtues/plans/${encodeURIComponent(planId)}/checkin`, { method: "POST", body: { date, goal_id: goalId } });
}
export async function saveVirtueJournal(planId: string, date: string, text: string): Promise<VirtuePlan> {
  return await api(`/virtues/plans/${encodeURIComponent(planId)}/journal`, { method: "PUT", body: { date, text } });
}
export async function translateTexts(texts: string[], target: string): Promise<string[]> {
  if ((target !== "es" && target !== "it") || texts.length === 0) return texts;
  const res = await api<{ items: string[] }>("/translate", { method: "POST", body: { texts, target } });
  return res.items;
}

export type CatholicSite = {
  site_id: string;
  slug: string;
  name: string;
  type: "basilica" | "cathedral" | "shrine" | "apparition" | "monastery" | "church";
  city: string;
  country: string;
  lat: number;
  lng: number;
  founded?: string;
  blurb?: string;
  history?: string;
  relics: string[];
  saints: string[];
  miracles: string[];
  source_url?: string;
  persecuted?: boolean;
  persecution_note?: string;
  distance_km?: number;
  osm?: boolean;
  address?: string;
  street?: string;
  state?: string;
  postcode?: string;
  website?: string;
  phone?: string;
};
export async function listCatholicSites(): Promise<{ items: CatholicSite[]; total: number }> {
  return await api(`/sites`);
}
export type NearbyResponse = {
  items: CatholicSite[];
  featured: CatholicSite | null;
  nearby_churches: CatholicSite[];
  total: number;
};
export async function nearbyCatholicSites(lat?: number, lng?: number): Promise<NearbyResponse> {
  const q = lat != null && lng != null ? `?lat=${lat}&lng=${lng}` : "";
  return await api(`/sites/nearby${q}`);
}
export type BboxMarker = {
  site_id: string;
  slug: string;
  name: string;
  type: CatholicSite["type"];
  lat: number;
  lng: number;
  persecuted?: boolean;
  osm?: boolean;
  city?: string;
  country?: string;
  address?: string;
  street?: string;
  state?: string;
  postcode?: string;
  website?: string;
  phone?: string;
};
export async function sitesInBbox(
  south: number, west: number, north: number, east: number, zoom: number,
): Promise<{ items: BboxMarker[]; total: number; osm_count: number }> {
  const q = `?south=${south}&west=${west}&north=${north}&east=${east}&zoom=${Math.round(zoom)}`;
  return await api(`/sites/bbox${q}`);
}

export type VocationCompanion = { slug: string; name: string; why: string; prayer: string; devotions?: VocationItem[] };
export type VocationItem = { title: string; body: string };
export type VocationReading = { title: string; author?: string; kind?: "book" | "encyclical"; note?: string; slug?: string };
export type VocationDevotionalRec = { title: string; body: string; route?: string };
export type VocationGuide = {
  has_vocation: boolean;
  vocation?: string;
  state?: "discerning" | "living";
  label?: string;
  intro?: string;
  morning_prayer?: { title: string; body: string };
  afternoon_prayer?: { title: string; body: string };
  night_prayer?: { title: string; body: string };
  companions?: VocationCompanion[];
  ideas?: VocationItem[];
  traditions?: VocationItem[];
  readings?: VocationReading[];
  devotional_recs?: VocationDevotionalRec[];
  companion_saint?: string;
};
export async function getVocationGuide(): Promise<VocationGuide> {
  return await api(`/vocation/guide`);
}

// ---- Companion saints ----
export type CompanionVirtue = { name: string; how: string };
export type CompanionTradition = { title: string; body: string; route?: string };
export type CompanionDetail = {
  slug: string;
  name: string;
  feast?: string;
  importance: string;
  daily_prayer?: string;
  virtues: CompanionVirtue[];
  novena_slug?: string;
  daily_act: { text: string; index: number; total: number };
  church_traditions: CompanionTradition[];
  daily_traditions: CompanionTradition[];
  vocation_traditions: { label: string; items: CompanionTradition[] } | null;
  saint_devotions: CompanionTradition[];
  vocation_devotions: { label: string; items: CompanionTradition[] } | null;
  has_consecration: boolean;
  is_joseph: boolean;
  note?: string | null;
  do_not_name?: boolean;
  linked?: { slug: string; name: string } | null;
};
export type CompanionListItem = {
  slug: string; name: string; feast?: string; tagline: string;
  selected: boolean; is_vocation_companion: boolean; is_permanent?: boolean; linked?: string | null;
};
export async function listCompanions(): Promise<{
  companions: CompanionListItem[]; selected: string[]; max: number; vocation_companion: string;
}> {
  return await api(`/companions`);
}
export async function selectCompanion(slug: string, action: "add" | "remove" | "toggle" = "toggle"): Promise<{ selected: string[]; max: number }> {
  return await api(`/companions/select`, { method: "POST", body: { slug, action } });
}
export async function getCompanion(slug: string): Promise<CompanionDetail> {
  return await api(`/companions/${slug}`);
}
export async function getCompanionImage(slug: string): Promise<{ image: string | null }> {
  return await api(`/companions/${slug}/image`);
}

// Lazily-generated lo-fi backdrop of St. Joseph at his carpenter's bench
// (used by the Sanctuary "St. Joseph's Workshop" study mode).
export async function getSanctuaryStudyImage(): Promise<{ image: string | null }> {
  return await api(`/sanctuary/study-image`);
}

// ---- 33-Day Consecration to St. Joseph ----
export type ConsecrationDay = { day: number; title: string; theme: string };
export type ConsecrationActive = {
  start_date: string; end_date: string; completed_days: number[];
  status: string; current_day: number; total_days: number;
} | null;
export type ConsecrationOverview = {
  title: string; intro: string; total_days: number;
  set_times: { start: string; feast: string }[];
  days: ConsecrationDay[];
  daily_prayer: string; act_of_consecration: string;
  active: ConsecrationActive;
};
export async function getConsecration(): Promise<ConsecrationOverview> {
  return await api(`/consecration`);
}
export async function startConsecration(start_date: string): Promise<{ active: ConsecrationActive }> {
  return await api(`/consecration/start`, { method: "POST", body: { start_date } });
}
export async function stopConsecration(): Promise<{ ok: boolean }> {
  return await api(`/consecration/stop`, { method: "POST" });
}
export async function completeConsecrationDay(day: number): Promise<{ active: ConsecrationActive; status: string }> {
  return await api(`/consecration/complete-day`, { method: "POST", body: { day } });
}
export type ConsecrationDayContent = {
  day: number; total_days: number; title: string; theme: string;
  meditation: string; daily_prayer: string; act_of_consecration: string | null;
};
export async function getConsecrationDay(day: number): Promise<ConsecrationDayContent> {
  return await api(`/consecration/day/${day}`);
}



export type WorldIssue = { slug: string; title: string; icon: string; accent: string; blurb: string };
export type WorldContent = WorldIssue & {
  summary: string;
  church_teaching: string;
  principles: string[];
  where_the_church_is_clear: string;
  prudential_judgment: string;
  how_to_engage: string;
  prayer: string;
  lang?: string;
};
export async function getWorldIssues(): Promise<{ items: WorldIssue[] }> {
  return await api("/in-the-world");
}
export async function getWorldIssue(slug: string): Promise<WorldContent> {
  return await api(`/in-the-world/${encodeURIComponent(slug)}`);
}
export async function deleteVirtuePlan(id: string): Promise<{ ok: boolean }> {
  return await api(`/virtues/plans/${encodeURIComponent(id)}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Schedule
// ---------------------------------------------------------------------------

export type ScheduleKind = "meal" | "workout" | "virtue" | "challenge" | "pilgrimage" | "custom";

export type ScheduleItem = {
  id: string;
  kind: ScheduleKind;
  title: string;
  note?: string | null;
  recurrence: "weekly" | "once";
  days_of_week: number[]; // 0=Sun..6=Sat
  date?: string | null;   // YYYY-MM-DD for once
  time?: string | null;   // 24h HH:MM, null = all day
  ref_slug?: string | null;
  ref_id?: string | null;
  icon?: string | null;
  color?: string | null;
  notify: boolean;
  notif_ids: string[];
  ics_token?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type ScheduleItemInput = {
  kind: ScheduleKind;
  title: string;
  note?: string;
  recurrence: "weekly" | "once";
  days_of_week?: number[];
  date?: string | null;
  time?: string | null;
  ref_slug?: string | null;
  ref_id?: string | null;
  icon?: string | null;
  color?: string | null;
  notify?: boolean;
  notif_ids?: string[];
};

export type ScheduleSources = {
  virtue_plans: { ref_id: string; title: string; end_date?: string }[];
  challenges: { ref_slug: string; title: string; color?: string; icon?: string; patron_saint?: string }[];
};

export async function listSchedule(): Promise<{ items: ScheduleItem[] }> {
  return await api(`/schedule`);
}
export async function scheduleForDay(date: string): Promise<{ date: string; items: ScheduleItem[] }> {
  return await api(`/schedule/day/${encodeURIComponent(date)}`);
}
export async function getScheduleSources(): Promise<ScheduleSources> {
  return await api(`/schedule/sources`);
}
export async function createScheduleItem(body: ScheduleItemInput): Promise<ScheduleItem> {
  return await api(`/schedule`, { method: "POST", body });
}
export async function updateScheduleItem(id: string, body: ScheduleItemInput): Promise<ScheduleItem> {
  return await api(`/schedule/${encodeURIComponent(id)}`, { method: "PUT", body });
}
export async function setScheduleNotifIds(id: string, notif_ids: string[]): Promise<{ ok: boolean }> {
  return await api(`/schedule/${encodeURIComponent(id)}/notif-ids`, { method: "PUT", body: { notif_ids } });
}
export async function deleteScheduleItem(id: string): Promise<{ ok: boolean; notif_ids: string[] }> {
  return await api(`/schedule/${encodeURIComponent(id)}`, { method: "DELETE" });
}

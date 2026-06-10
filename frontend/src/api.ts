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
  denomination?: "catholic" | "protestant" | "orthodox" | null;
  tradition_path?: "convert" | "revert" | "cradle" | null;
  age?: number | null;
  show_attribution?: boolean | null;
  is_admin?: boolean | null;
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
  age?: number | null;
  show_attribution?: boolean | null;
}): Promise<User> {
  // Backend accepts empty string to clear picture; pass through null as empty.
  const body: Record<string, unknown> = {};
  if (patch.name !== undefined) body.name = patch.name;
  if (patch.picture !== undefined) body.picture = patch.picture ?? "";
  if (patch.denomination !== undefined) body.denomination = patch.denomination ?? "";
  if (patch.tradition_path !== undefined) body.tradition_path = patch.tradition_path ?? "";
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

export type ParishEvent = {
  id: string;
  type: ParishEventType;
  type_label: string;
  title: string;
  description: string;
  start_at: string; // ISO
  end_at: string | null;
  church_id: string | null;
  church_name: string | null;
  address: string;
  lat: number;
  lng: number;
  organizer_user_id: string;
  organizer_name: string;
  created_at: string;
  flag_count: number;
  is_owner: boolean;
  has_flagged: boolean;
  distance_km?: number;
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

// ---- Group DMs ----
export async function dmCreateGroup(memberIds: string[], name?: string | null): Promise<CommunityDMThread> {
  return await api(`/community/dm/threads/group`, {
    method: "POST",
    body: { member_ids: memberIds, name: name ?? null },
  });
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
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
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



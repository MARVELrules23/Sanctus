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

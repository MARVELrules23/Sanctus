/**
 * NotificationsContext — single source of truth for unread DM counts
 * driving the badges on the Parish tab and the Inbox icon.
 *
 * Behavior:
 *  - Lazily starts polling once a user is signed in.
 *  - Polls `/api/community/dm/unread-count` every 30s while the app is
 *    in the foreground; pauses when backgrounded; refreshes on resume.
 *  - Exposes `refresh()` so screens that just marked a thread as read
 *    can immediately drop the badge instead of waiting for the next tick.
 *  - Silent on errors — a missing badge is much better than a crashing
 *    one. The console gets a warning during development.
 */
import React, {
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { AppState, AppStateStatus } from "react-native";

import { getDMUnreadCount, DMUnreadResponse } from "@/src/api";
import { useAuth } from "@/src/auth-context";

const POLL_INTERVAL_MS = 30_000;

type NotificationsState = {
  unreadDMTotal: number;
  unreadByThread: Record<string, number>;
  refresh: () => Promise<void>;
  /** Optimistically clear a thread's unread count locally (we already
   *  hit the read-mark endpoint server-side). Call after entering a
   *  thread so the badge feels instant. */
  markThreadRead: (threadId: string) => void;
};

const Ctx = createContext<NotificationsState>({
  unreadDMTotal: 0,
  unreadByThread: {},
  refresh: async () => {},
  markThreadRead: () => {},
});

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [unreadDMTotal, setTotal] = useState(0);
  const [unreadByThread, setByThread] = useState<Record<string, number>>({});
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);
  const inFlightRef = useRef(false);
  const appStateRef = useRef<AppStateStatus>(AppState.currentState);

  const apply = useCallback((res: DMUnreadResponse | null) => {
    if (!mountedRef.current) return;
    if (!res) {
      setTotal(0);
      setByThread({});
      return;
    }
    setTotal(Math.max(0, res.total || 0));
    const map: Record<string, number> = {};
    for (const t of res.threads || []) {
      if (t.thread_id) map[t.thread_id] = Math.max(0, t.unread || 0);
    }
    setByThread(map);
  }, []);

  const refresh = useCallback(async () => {
    if (!user) {
      apply(null);
      return;
    }
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    try {
      const res = await getDMUnreadCount();
      apply(res);
    } catch (e) {
      // Soft-fail; keep previous count visible rather than zeroing on a
      // transient network error.
      if (__DEV__) console.warn("dm unread-count fetch failed", e);
    } finally {
      inFlightRef.current = false;
    }
  }, [user, apply]);

  const markThreadRead = useCallback((threadId: string) => {
    if (!threadId) return;
    setByThread((prev) => {
      if (!prev[threadId]) return prev;
      const next = { ...prev };
      const dropped = next[threadId] || 0;
      delete next[threadId];
      setTotal((t) => Math.max(0, t - dropped));
      return next;
    });
  }, []);

  // Lifecycle: poll while signed in + foregrounded
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!user) {
      apply(null);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }
    // initial fetch
    void refresh();
    // start interval
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      if (appStateRef.current === "active") {
        void refresh();
      }
    }, POLL_INTERVAL_MS);
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [user, refresh, apply]);

  // Refresh when the app returns to foreground
  useEffect(() => {
    const sub = AppState.addEventListener("change", (state) => {
      const prev = appStateRef.current;
      appStateRef.current = state;
      if (prev !== "active" && state === "active" && user) {
        void refresh();
      }
    });
    return () => sub.remove();
  }, [user, refresh]);

  const value = useMemo(
    () => ({ unreadDMTotal, unreadByThread, refresh, markThreadRead }),
    [unreadDMTotal, unreadByThread, refresh, markThreadRead],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useNotifications() {
  return useContext(Ctx);
}

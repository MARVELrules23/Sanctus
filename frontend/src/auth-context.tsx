/**
 * AuthContext — handles Emergent-managed Google Sign-In flow on Expo + web.
 */
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Platform } from "react-native";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";
import { useRouter } from "expo-router";

import { api, clearToken, getToken, setToken, User } from "@/src/api";

type AuthState = {
  user: User | null;
  loading: boolean;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  setUser: (u: User | null) => void;
};

const AuthCtx = createContext<AuthState>({
  user: null,
  loading: true,
  signIn: async () => {},
  signOut: async () => {},
  setUser: () => {},
});

const AUTH_URL = "https://auth.emergentagent.com/?redirect=";

function extractSessionId(url: string): string | null {
  try {
    const u = new URL(url);
    const hash = u.hash.replace(/^#/, "");
    const params = new URLSearchParams(hash || u.search);
    return params.get("session_id");
  } catch {
    const m = url.match(/[?#&]session_id=([^&]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const exchange = useCallback(async (sessionId: string) => {
    const res = await api<{ session_token: string; user: User }>("/auth/session", {
      method: "POST",
      body: { session_id: sessionId },
      auth: false,
    });
    await setToken(res.session_token);
    setUser(res.user);
  }, []);

  const refresh = useCallback(async () => {
    const t = await getToken();
    if (!t) {
      setUser(null);
      return;
    }
    try {
      const me = await api<User>("/auth/me");
      setUser(me);
    } catch {
      await clearToken();
      setUser(null);
    }
  }, []);

  // Bootstrap: parse session_id from URL (web), check existing token, listen for deep links (mobile).
  useEffect(() => {
    let cancelled = false;
    let urlSub: { remove: () => void } | undefined;

    const boot = async () => {
      try {
        if (Platform.OS === "web" && typeof window !== "undefined") {
          const sid = extractSessionId(window.location.href);
          if (sid) {
            await exchange(sid);
            try {
              window.history.replaceState(null, "", window.location.pathname);
            } catch {}
          } else {
            await refresh();
          }
        } else {
          const initial = await Linking.getInitialURL();
          const sid = initial ? extractSessionId(initial) : null;
          if (sid) {
            await exchange(sid);
          } else {
            await refresh();
          }
          urlSub = Linking.addEventListener("url", async ({ url }) => {
            const sid2 = extractSessionId(url);
            if (sid2) {
              try {
                await exchange(sid2);
                router.replace("/(tabs)");
              } catch (e) {
                console.warn("session exchange failed", e);
              }
            }
          });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    boot();
    return () => {
      cancelled = true;
      urlSub?.remove?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signIn = useCallback(async () => {
    if (Platform.OS === "web" && typeof window !== "undefined") {
      const redirect = window.location.origin + "/";
      window.location.href = AUTH_URL + encodeURIComponent(redirect);
      return;
    }
    const redirect = Linking.createURL("auth");
    const authUrl = AUTH_URL + encodeURIComponent(redirect);
    const result = await WebBrowser.openAuthSessionAsync(authUrl, redirect);
    if (result.type === "success" && result.url) {
      const sid = extractSessionId(result.url);
      if (sid) {
        await exchange(sid);
        router.replace("/(tabs)");
      }
    }
  }, [exchange, router]);

  const signOut = useCallback(async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {}
    await clearToken();
    setUser(null);
    router.replace("/login");
  }, [router]);

  const value = useMemo(() => ({ user, loading, signIn, signOut, setUser }), [user, loading, signIn, signOut]);
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth() {
  return useContext(AuthCtx);
}

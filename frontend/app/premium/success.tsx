/**
 * Sanctus Premium — post-checkout success screen.
 *
 * Route: /premium/success?session_id=cs_test_...
 *
 * Stripe redirects here. We call the reconcile endpoint, which retrieves the
 * Checkout Session + Subscription from Stripe and flips the local user to
 * Premium. The frontend then refreshes the auth context and routes the user
 * back to /premium (now showing the active card) or wherever they came from.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";

import { reconcilePremiumSession } from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

export default function PremiumSuccessScreen() {
  const router = useRouter();
  const { session_id, plan } = useLocalSearchParams<{ session_id?: string; plan?: string }>();
  const { refresh } = useAuth();
  const [state, setState] = useState<"working" | "ok" | "fail">("working");
  const [msg, setMsg] = useState<string>("Finishing up your subscription…");
  const triedRef = useRef(false);

  const run = useCallback(async () => {
    if (triedRef.current) return;
    triedRef.current = true;
    const sid = (Array.isArray(session_id) ? session_id[0] : session_id) || "";
    if (!sid) {
      setState("fail");
      setMsg("Missing checkout session id.");
      return;
    }
    try {
      const res = await reconcilePremiumSession(sid);
      if (res?.reconciled) {
        setState("ok");
        setMsg("You're in. Welcome to Sanctus Premium.");
      } else {
        // Subscription not yet attached; retry once after a short pause —
        // sometimes Stripe needs a beat after redirect.
        await new Promise((r) => setTimeout(r, 1500));
        const res2 = await reconcilePremiumSession(sid);
        if (res2?.reconciled) {
          setState("ok");
          setMsg("You're in. Welcome to Sanctus Premium.");
        } else {
          setState("fail");
          setMsg("Your payment is processing. Premium will activate within a minute.");
        }
      }
      await refresh();
    } catch (e: any) {
      setState("fail");
      setMsg(e?.message || "We couldn't confirm the subscription. Try refreshing.");
    }
  }, [session_id, refresh]);

  useEffect(() => {
    void run();
  }, [run]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.body}>
        <View style={styles.crest}>
          {state === "working" ? (
            <ActivityIndicator color={colors.gold} />
          ) : state === "ok" ? (
            <Ionicons name="checkmark-circle" size={56} color={colors.gold} />
          ) : (
            <Ionicons name="hourglass-outline" size={48} color={colors.gold} />
          )}
        </View>
        <Text style={styles.title}>
          {state === "ok" ? "Welcome to Premium" : state === "fail" ? "Almost there" : "One moment…"}
        </Text>
        <Text style={styles.msg}>{msg}</Text>
        {plan ? (
          <Text style={styles.meta}>
            {String(plan) === "annual" ? "Annual plan" : "Monthly plan"}
          </Text>
        ) : null}

        <Pressable
          testID="premium-continue"
          onPress={() => router.replace("/(tabs)" as any)}
          style={({ pressed }) => [styles.primaryBtn, pressed && { opacity: 0.85 }]}
        >
          <Ionicons name="arrow-forward" size={16} color={colors.gold} />
          <Text style={styles.primaryBtnText}>Continue</Text>
        </Pressable>

        <Pressable
          testID="premium-view-status"
          onPress={() => router.replace("/premium" as any)}
          style={({ pressed }) => [styles.secondaryBtn, pressed && { opacity: 0.7 }]}
        >
          <Text style={styles.secondaryBtnText}>View Premium status</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  body: {
    flex: 1, alignItems: "center", justifyContent: "center",
    paddingHorizontal: spacing.xl, gap: spacing.md,
  },
  crest: {
    width: 96, height: 96, borderRadius: 48,
    backgroundColor: colors.primary,
    alignItems: "center", justifyContent: "center",
    ...shadow.card,
    marginBottom: spacing.md,
  },
  title: {
    fontFamily: fonts.headingBold, fontSize: 24, color: colors.textPrimary,
    textAlign: "center",
  },
  msg: {
    fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary,
    textAlign: "center", lineHeight: 20, paddingHorizontal: spacing.md,
  },
  meta: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold, letterSpacing: 0.6, textTransform: "uppercase" },
  primaryBtn: {
    marginTop: spacing.lg,
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 8, paddingVertical: 14, paddingHorizontal: spacing.xl,
    borderRadius: radius.round, backgroundColor: colors.primary,
  },
  primaryBtnText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.gold, letterSpacing: 0.6 },
  secondaryBtn: { marginTop: spacing.sm, paddingVertical: spacing.sm },
  secondaryBtnText: { fontFamily: fonts.uiMedium, fontSize: 13, color: colors.textSecondary, textAlign: "center" },
});

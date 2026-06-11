/**
 * Sanctus Premium — Paywall + subscription management screen.
 *
 * Route: /premium
 *
 * Behavior:
 *  - If the user is already a Sanctus Premium subscriber (paid or admin
 *    override), shows their plan + a "Manage subscription" CTA that opens
 *    the Stripe Billing Portal.
 *  - Otherwise renders the marketing paywall with Monthly / Annual cards,
 *    benefits, and a single "Start free trial" CTA that creates a Stripe
 *    Checkout Session and opens it.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import * as WebBrowser from "expo-web-browser";

import {
  PremiumStatus,
  createPremiumCheckout,
  getPremiumStatus,
  openPremiumPortal,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import {
  describeStatus,
  formatCents,
  publicOrigin,
} from "@/src/premium-utils";

type Plan = "monthly" | "annual";

const BENEFITS: { icon: keyof typeof Ionicons.glyphMap; title: string; copy: string }[] = [
  {
    icon: "trophy-outline",
    title: "Every Liturgical Challenge",
    copy: "Lent, Advent, 33 Days to Mary — full check-ins, prayers, and streak tracking.",
  },
  {
    icon: "book-outline",
    title: "The full Sanctus Library",
    copy: "Doctors, mystics, and spiritual classics — read in-app, chapter by chapter. Encyclicals always free.",
  },
  {
    icon: "people-outline",
    title: "Group DMs with your parish",
    copy: "Spin up private group chats for ministries, small groups, or family.",
  },
  {
    icon: "infinite-outline",
    title: "Everything you already use, plus what's next",
    copy: "Daily Mass, Saints of the Day, Catechism, and every Premium feature we ship from here on.",
  },
];

export default function PremiumScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ cancelled?: string; plan?: string }>();
  const { user, refresh } = useAuth();
  const [status, setStatus] = useState<PremiumStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedPlan, setSelectedPlan] = useState<Plan>("annual");
  const [busy, setBusy] = useState<"checkout" | "portal" | null>(null);

  const load = useCallback(async () => {
    try {
      const s = await getPremiumStatus();
      setStatus(s);
    } catch (e: any) {
      Alert.alert("Couldn't load Premium", e?.message || "Try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (params?.cancelled === "1") {
      // Soft notice; no Alert spam.
    }
  }, [params?.cancelled]);

  const monthlyCents = status?.pricing.monthly.amount_cents ?? 499;
  const annualCents = status?.pricing.annual.amount_cents ?? 3999;
  const annualSavings = useMemo(() => {
    const yearlyAtMonthly = monthlyCents * 12;
    if (yearlyAtMonthly <= 0) return 0;
    const pct = Math.round(((yearlyAtMonthly - annualCents) / yearlyAtMonthly) * 100);
    return Math.max(0, pct);
  }, [monthlyCents, annualCents]);
  const trialDays = status?.trial_days ?? 7;

  const startCheckout = useCallback(async () => {
    if (busy) return;
    setBusy("checkout");
    try {
      const origin = publicOrigin();
      const res = await createPremiumCheckout({ plan: selectedPlan, return_origin: origin });
      if (res.already_premium || !res.url) {
        await refresh();
        await load();
        Alert.alert("You're already Premium", "Thanks for supporting Sanctus.");
        return;
      }
      if (Platform.OS === "web" && typeof window !== "undefined") {
        window.location.href = res.url;
      } else {
        const successUrl = `${origin}/premium/success`;
        await WebBrowser.openAuthSessionAsync(res.url, successUrl).catch(() => {});
        // Refresh state after the browser closes — webhook may not have
        // landed yet but reconcile (on success URL) usually has.
        await refresh();
        await load();
      }
    } catch (e: any) {
      Alert.alert("Checkout unavailable", e?.message || "Please try again.");
    } finally {
      setBusy(null);
    }
  }, [busy, selectedPlan, refresh, load]);

  const openPortal = useCallback(async () => {
    if (busy) return;
    setBusy("portal");
    try {
      const origin = publicOrigin();
      const { url } = await openPremiumPortal(origin);
      if (Platform.OS === "web" && typeof window !== "undefined") {
        window.location.href = url;
      } else {
        await WebBrowser.openAuthSessionAsync(url, `${origin}/premium`).catch(() => {});
        await refresh();
        await load();
      }
    } catch (e: any) {
      Alert.alert("Couldn't open billing", e?.message || "Try again later.");
    } finally {
      setBusy(null);
    }
  }, [busy, refresh, load]);

  if (loading || !status) {
    return (
      <SafeAreaView style={styles.safe}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
        </View>
      </SafeAreaView>
    );
  }

  const isPremium = !!status.is_premium;
  const stripeReady = !!status.stripe_ready;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable hitSlop={12} onPress={() => router.back()} testID="premium-back">
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
        </Pressable>
        <Text style={styles.headerTitle}>Sanctus Premium</Text>
        <View style={{ width: 22 }} />
      </View>

      <ScrollView contentContainerStyle={styles.body}>
        <View style={styles.hero}>
          <View style={styles.crest}>
            <Ionicons name="ribbon" size={36} color={colors.gold} />
          </View>
          <Text style={styles.heroTitle}>Pray. Read. Walk together.</Text>
          <Text style={styles.heroSub}>
            One subscription unlocks every Liturgical Challenge, the full Library, and
            Group DMs.
          </Text>
          {user?.email ? (
            <Text style={styles.heroEmail} numberOfLines={1}>Signed in as {user.email}</Text>
          ) : null}
        </View>

        {isPremium ? (
          <View style={styles.activeCard}>
            <View style={styles.activeBadge}>
              <Ionicons name="checkmark-circle" size={16} color={colors.gold} />
              <Text style={styles.activeBadgeText}>Sanctus Premium · Active</Text>
            </View>
            <Text style={styles.activeLine}>
              {status.is_admin_premium
                ? "Founder access — granted permanently."
                : describeStatus(status.status, status.trial_end)}
            </Text>
            {status.tier ? (
              <Text style={styles.activeLineSecondary}>
                Plan: {status.tier === "annual" ? "Annual" : "Monthly"}
                {status.cancel_at_period_end ? " · Cancels at period end" : ""}
              </Text>
            ) : null}
            {!status.is_admin_premium ? (
              <Pressable
                onPress={openPortal}
                testID="premium-manage"
                disabled={busy === "portal"}
                style={({ pressed }) => [
                  styles.primaryBtn,
                  pressed && { opacity: 0.85 },
                  busy === "portal" && { opacity: 0.6 },
                ]}
              >
                {busy === "portal" ? (
                  <ActivityIndicator color={colors.gold} />
                ) : (
                  <>
                    <Ionicons name="settings-outline" size={16} color={colors.gold} />
                    <Text style={styles.primaryBtnText}>Manage subscription</Text>
                  </>
                )}
              </Pressable>
            ) : null}
          </View>
        ) : (
          <>
            <View style={styles.planRow}>
              <PlanCard
                label="Monthly"
                price={formatCents(monthlyCents)}
                cadence="/ month"
                selected={selectedPlan === "monthly"}
                onPress={() => setSelectedPlan("monthly")}
                testID="plan-monthly"
              />
              <PlanCard
                label="Annual"
                price={formatCents(annualCents)}
                cadence="/ year"
                selected={selectedPlan === "annual"}
                onPress={() => setSelectedPlan("annual")}
                badge={annualSavings > 0 ? `Save ${annualSavings}%` : "Best value"}
                testID="plan-annual"
              />
            </View>

            <Text style={styles.trialNote}>
              {trialDays}-day free trial. Cancel anytime before it ends.
            </Text>

            <Pressable
              onPress={startCheckout}
              testID="premium-start-trial"
              disabled={busy === "checkout" || !stripeReady}
              style={({ pressed }) => [
                styles.primaryBtn,
                pressed && { opacity: 0.85 },
                (busy === "checkout" || !stripeReady) && { opacity: 0.6 },
              ]}
            >
              {busy === "checkout" ? (
                <ActivityIndicator color={colors.gold} />
              ) : (
                <>
                  <Ionicons name="lock-open-outline" size={16} color={colors.gold} />
                  <Text style={styles.primaryBtnText}>
                    Start {trialDays}-day free trial
                  </Text>
                </>
              )}
            </Pressable>

            {!stripeReady ? (
              <Text style={styles.disabledNote}>
                Payments are activated when this app is deployed. The button will
                light up there.
              </Text>
            ) : null}

            <Text style={styles.secureNote}>Secure checkout by Stripe</Text>
          </>
        )}

        <View style={styles.benefits}>
          <Text style={styles.section}>What&apos;s included</Text>
          {BENEFITS.map((b) => (
            <View key={b.title} style={styles.benefit}>
              <View style={styles.benefitIcon}>
                <Ionicons name={b.icon} size={18} color={colors.gold} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.benefitTitle}>{b.title}</Text>
                <Text style={styles.benefitCopy}>{b.copy}</Text>
              </View>
            </View>
          ))}
        </View>

        <View style={styles.faq}>
          <Text style={styles.section}>Good to know</Text>
          <Text style={styles.faqLine}>
            • Encyclicals stay free for everyone — they always will.
          </Text>
          <Text style={styles.faqLine}>
            • 1-on-1 DMs and the Parish feed are free. Premium adds group chats and
            full Library access.
          </Text>
          <Text style={styles.faqLine}>
            • Cancel anytime in the Stripe billing portal &mdash; your access continues
            through the period you paid for.
          </Text>
        </View>

        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function PlanCard({
  label,
  price,
  cadence,
  selected,
  onPress,
  badge,
  testID,
}: {
  label: string;
  price: string;
  cadence: string;
  selected: boolean;
  onPress: () => void;
  badge?: string;
  testID?: string;
}) {
  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      style={({ pressed }) => [
        styles.plan,
        selected && styles.planSelected,
        pressed && { opacity: 0.9 },
      ]}
    >
      {badge ? (
        <View style={styles.planBadge}>
          <Text style={styles.planBadgeText}>{badge}</Text>
        </View>
      ) : null}
      <Text style={styles.planLabel}>{label}</Text>
      <Text style={styles.planPrice}>{price}</Text>
      <Text style={styles.planCadence}>{cadence}</Text>
      <View style={[styles.radio, selected && styles.radioSelected]}>
        {selected ? <View style={styles.radioDot} /> : null}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: spacing.lg, paddingVertical: spacing.md,
  },
  headerTitle: {
    flex: 1, marginHorizontal: spacing.md, textAlign: "center",
    fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary,
  },
  body: { paddingHorizontal: spacing.lg, paddingBottom: spacing.xl },

  hero: {
    alignItems: "center", paddingVertical: spacing.lg,
  },
  crest: {
    width: 72, height: 72, borderRadius: 36,
    backgroundColor: colors.primary,
    alignItems: "center", justifyContent: "center", marginBottom: spacing.md,
    ...shadow.card,
  },
  heroTitle: {
    fontFamily: fonts.headingBold, fontSize: 24, color: colors.textPrimary,
    textAlign: "center", lineHeight: 28,
  },
  heroSub: {
    fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary,
    textAlign: "center", lineHeight: 20, marginTop: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  heroEmail: {
    fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted,
    marginTop: spacing.sm,
  },

  planRow: { flexDirection: "row", gap: spacing.md, marginTop: spacing.lg },
  plan: {
    flex: 1, backgroundColor: colors.surface,
    borderRadius: radius.lg, borderWidth: 2, borderColor: colors.borderSoft,
    padding: spacing.md, alignItems: "center",
    minHeight: 144,
    justifyContent: "center",
    ...shadow.card,
  },
  planSelected: { borderColor: colors.gold },
  planBadge: {
    position: "absolute", top: -10, alignSelf: "center",
    backgroundColor: colors.gold,
    paddingHorizontal: 10, paddingVertical: 3, borderRadius: radius.round,
  },
  planBadgeText: {
    fontFamily: fonts.uiSemi, fontSize: 10, color: colors.primary,
    letterSpacing: 0.6, textTransform: "uppercase",
  },
  planLabel: {
    fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textMuted,
    textTransform: "uppercase", letterSpacing: 1.2, marginBottom: 4,
  },
  planPrice: { fontFamily: fonts.headingBold, fontSize: 28, color: colors.textPrimary },
  planCadence: {
    fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textSecondary,
    marginTop: 2,
  },
  radio: {
    width: 18, height: 18, borderRadius: 9, borderWidth: 1.5,
    borderColor: colors.borderSoft, marginTop: spacing.sm,
    alignItems: "center", justifyContent: "center",
  },
  radioSelected: { borderColor: colors.gold },
  radioDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.gold },

  trialNote: {
    fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textSecondary,
    textAlign: "center", marginTop: spacing.lg,
  },

  primaryBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 8, paddingVertical: 14, borderRadius: radius.round,
    marginTop: spacing.md,
    backgroundColor: colors.primary,
  },
  primaryBtnText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.gold, letterSpacing: 0.6 },

  secureNote: {
    fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted,
    textAlign: "center", marginTop: spacing.sm,
  },
  disabledNote: {
    fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textMuted,
    textAlign: "center", marginTop: spacing.sm, lineHeight: 18,
    paddingHorizontal: spacing.md,
  },

  activeCard: {
    marginTop: spacing.lg, padding: spacing.lg, borderRadius: radius.lg,
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.gold,
    ...shadow.card,
  },
  activeBadge: {
    flexDirection: "row", alignItems: "center", gap: 6,
    alignSelf: "flex-start",
    backgroundColor: colors.primary,
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.round,
    marginBottom: spacing.sm,
  },
  activeBadgeText: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.gold, letterSpacing: 0.6 },
  activeLine: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.textPrimary, marginTop: 2 },
  activeLineSecondary: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, marginTop: 2 },

  benefits: { marginTop: spacing.xl, gap: spacing.md },
  benefit: { flexDirection: "row", gap: spacing.md, alignItems: "flex-start" },
  benefitIcon: {
    width: 32, height: 32, borderRadius: 16,
    backgroundColor: colors.primary,
    alignItems: "center", justifyContent: "center",
  },
  benefitTitle: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.textPrimary },
  benefitCopy: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, lineHeight: 18, marginTop: 2 },

  section: {
    fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary,
    marginBottom: spacing.sm,
  },

  faq: { marginTop: spacing.xl, gap: 4 },
  faqLine: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, lineHeight: 20 },
});

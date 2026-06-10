/**
 * Liturgical Challenges Hub — lists Hallowtide, Advent, Lent (and any
 * other tracks) with enroll/unenroll toggle and a tap-through to detail.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import {
  ChallengeSummary,
  enrollChallenge,
  listChallenges,
  unenrollChallenge,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { todayISO, formatLongFromISO } from "@/src/date-utils";

function iso(s: string | null | undefined): string | null {
  if (!s) return null;
  return s.slice(0, 10);
}

function windowState(c: ChallengeSummary, today: string): {
  label: string;
  tone: "now" | "upcoming" | "past";
  dayIndex: number | null;
  totalDays: number;
} {
  const start = iso(c.start_date);
  const end = iso(c.end_date);
  const totalDays = c.total_days || 0;
  if (!start || !end) {
    return { label: "Dates pending", tone: "upcoming", dayIndex: null, totalDays };
  }
  if (today < start) {
    return {
      label: `Begins ${formatLongFromISO(start)}`,
      tone: "upcoming",
      dayIndex: null,
      totalDays,
    };
  }
  if (today > end) {
    return {
      label: `Ended ${formatLongFromISO(end)}`,
      tone: "past",
      dayIndex: null,
      totalDays,
    };
  }
  const startDate = new Date(`${start}T00:00:00`);
  const todayDate = new Date(`${today}T00:00:00`);
  const dayIndex = Math.floor((todayDate.getTime() - startDate.getTime()) / 86_400_000) + 1;
  return { label: `Day ${dayIndex} of ${totalDays}`, tone: "now", dayIndex, totalDays };
}

export default function ChallengesHub() {
  const router = useRouter();
  const { user } = useAuth();
  const [items, setItems] = useState<ChallengeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<string | null>(null);
  const today = todayISO();

  const load = useCallback(async () => {
    try {
      const r = await listChallenges();
      setItems(r.items || []);
    } catch (e: any) {
      Alert.alert("Couldn't load", e?.message || "Try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const onToggle = async (c: ChallengeSummary, next: boolean) => {
    if (toggling) return;
    setToggling(c.slug);
    try {
      if (next) {
        await enrollChallenge(c.slug);
      } else {
        await unenrollChallenge(c.slug);
      }
      // Optimistic local update
      setItems((prev) =>
        prev.map((p) => (p.slug === c.slug ? { ...p, enrolled: next } : p)),
      );
    } catch (e: any) {
      Alert.alert("Couldn't update", e?.message || "Try again.");
    } finally {
      setToggling(null);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="challenges-hub">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="challenges-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Liturgical Challenges</Text>
        {user?.is_admin ? (
          <Pressable
            onPress={() => router.push("/admin/challenges")}
            hitSlop={10}
            testID="challenges-admin-link"
          >
            <Ionicons name="settings-outline" size={22} color={colors.primary} />
          </Pressable>
        ) : (
          <View style={{ width: 26 }} />
        )}
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.intro}>
          Three sacred journeys through the Church&apos;s year — Hallowtide,
          Advent, and Lent — built around small daily practices, a patron
          saint, and a steady rhythm of prayer.
        </Text>

        {loading ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
        ) : items.length === 0 ? (
          <Text style={styles.empty}>No challenges available yet.</Text>
        ) : (
          items.map((c) => {
            const state = windowState(c, today);
            const accent = c.color || colors.gold;
            const isToggling = toggling === c.slug;
            return (
              <View
                key={c.challenge_id}
                testID={`challenge-card-${c.slug}`}
                style={[styles.card, { borderColor: accent }]}
              >
                <Pressable
                  onPress={() => router.push({ pathname: "/challenges/[slug]", params: { slug: c.slug } })}
                  style={({ pressed }) => [{ opacity: pressed ? 0.85 : 1 }]}
                >
                  <View style={styles.cardHead}>
                    <Ionicons
                      name={(c.icon as keyof typeof Ionicons.glyphMap) || "flame-outline"}
                      size={20}
                      color={accent}
                    />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.cardName}>{c.name}</Text>
                      {c.subtitle ? (
                        <Text style={styles.cardSubtitle}>{c.subtitle}</Text>
                      ) : null}
                    </View>
                    <View
                      style={[
                        styles.statePill,
                        state.tone === "now" && { backgroundColor: accent },
                        state.tone === "past" && { backgroundColor: colors.borderSoft },
                      ]}
                    >
                      <Text
                        style={[
                          styles.statePillText,
                          state.tone === "now" && { color: colors.gold },
                        ]}
                      >
                        {state.label}
                      </Text>
                    </View>
                  </View>
                  {c.blurb ? (
                    <Text style={styles.cardBlurb} numberOfLines={4}>{c.blurb}</Text>
                  ) : null}
                  {c.enrolled && (c.completed_days || c.streak) ? (
                    <View style={styles.statRow}>
                      <View style={styles.statChip}>
                        <Ionicons name="flame" size={12} color={colors.gold} />
                        <Text style={styles.statText}>{c.streak || 0}-day streak</Text>
                      </View>
                      <View style={styles.statChip}>
                        <Ionicons name="checkmark-circle" size={12} color={accent} />
                        <Text style={styles.statText}>
                          {c.completed_days || 0} / {c.total_days || 0} days
                        </Text>
                      </View>
                    </View>
                  ) : null}
                </Pressable>

                <View style={styles.cardFoot}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.toggleLabel}>
                      {c.enrolled ? "Walking with you" : "Walk this season"}
                    </Text>
                    <Text style={styles.toggleSub}>
                      {c.enrolled
                        ? "On Home card + Calendar"
                        : "Tap the toggle to enroll"}
                    </Text>
                  </View>
                  {isToggling ? (
                    <ActivityIndicator size="small" color={accent} />
                  ) : (
                    <Switch
                      testID={`challenge-toggle-${c.slug}`}
                      value={!!c.enrolled}
                      onValueChange={(v) => onToggle(c, v)}
                      trackColor={{ false: colors.borderSoft, true: accent }}
                      thumbColor={colors.gold}
                    />
                  )}
                </View>
              </View>
            );
          })
        )}

        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  scroll: { padding: spacing.lg, paddingBottom: spacing.xxl },
  intro: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 14,
    lineHeight: 22,
    color: colors.textSecondary,
    marginBottom: spacing.lg,
  },
  empty: {
    textAlign: "center",
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textMuted,
    marginTop: spacing.xl,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1.5,
    marginBottom: spacing.md,
    ...shadow.card,
  },
  cardHead: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  cardName: { fontFamily: fonts.headingSemi, fontSize: 20, color: colors.textPrimary },
  cardSubtitle: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: 2,
  },
  statePill: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.round,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  statePillText: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1,
    color: colors.textSecondary,
    textTransform: "uppercase",
  },
  cardBlurb: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
    marginTop: spacing.sm,
  },
  statRow: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm, flexWrap: "wrap" },
  statChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.round,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  statText: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.textPrimary },
  cardFoot: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    marginTop: spacing.md,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
  },
  toggleLabel: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textPrimary },
  toggleSub: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
});

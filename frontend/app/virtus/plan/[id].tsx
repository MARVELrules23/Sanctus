/**
 * Virtus — plan detail.
 *
 * Shows a personal virtue plan with its AI-generated goals grouped by virtue.
 * Each goal (do / refrain) can be checked off; progress updates live. The plan
 * can be deleted.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import {
  deleteVirtuePlan,
  getVirtuePlan,
  toggleVirtueGoal,
  VirtuePlan,
} from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

export default function VirtuePlanScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [plan, setPlan] = useState<VirtuePlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setPlan(await getVirtuePlan(id));
    } catch (e: any) {
      setError(e?.message || "Could not load this plan.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  const toggle = async (goalId: string) => {
    if (!id || busy) return;
    setBusy(goalId);
    try {
      setPlan(await toggleVirtueGoal(id, goalId));
    } catch {
      /* ignore */
    } finally {
      setBusy(null);
    }
  };

  const confirmDelete = () => {
    Alert.alert("Delete plan?", "This virtue plan and its goals will be removed.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          if (!id) return;
          try {
            await deleteVirtuePlan(id);
            router.back();
          } catch {
            /* ignore */
          }
        },
      },
    ]);
  };

  const grouped = useMemo(() => {
    if (!plan) return [] as { virtue: { slug: string; name: string; accent_color: string; icon: string }; goals: VirtuePlan["goals"] }[];
    return plan.virtues.map((v) => ({
      virtue: v,
      goals: plan.goals.filter((g) => g.virtue_slug === v.slug),
    }));
  }, [plan]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="virtus-plan-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="virtus-plan-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.headerTitle}>Your Virtue Plan</Text>
        </View>
        <Pressable testID="virtus-plan-delete" onPress={confirmDelete} hitSlop={10}>
          <Ionicons name="trash-outline" size={20} color={colors.textMuted} />
        </Pressable>
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      ) : error || !plan ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error || "Not found."}</Text>
          <Pressable onPress={load} style={({ pressed }) => [styles.retry, pressed && { opacity: 0.7 }]}>
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.summary}>
            <Text style={styles.summaryTitle}>{plan.virtues.map((v) => v.name).join(" · ")}</Text>
            <Text style={styles.summarySub}>
              {plan.start_date} → {plan.end_date} · {plan.days} days
            </Text>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${plan.total ? (plan.completed / plan.total) * 100 : 0}%` }]} />
            </View>
            <Text style={styles.progressLabel}>{plan.completed} of {plan.total} goals complete</Text>
            {plan.note ? <Text style={styles.note}>“{plan.note}”</Text> : null}
          </View>

          {grouped.map(({ virtue, goals }) => (
            <View key={virtue.slug} style={[styles.group, { borderTopColor: virtue.accent_color }]}>
              <View style={styles.groupHead}>
                <Ionicons name={(virtue.icon as keyof typeof Ionicons.glyphMap) || "ellipse-outline"} size={18} color={virtue.accent_color} />
                <Text style={styles.groupTitle}>{virtue.name}</Text>
              </View>
              {goals.map((g) => (
                <Pressable
                  key={g.id}
                  testID={`virtus-goal-${g.id}`}
                  onPress={() => toggle(g.id)}
                  style={({ pressed }) => [styles.goalRow, pressed && { opacity: 0.8 }]}
                >
                  <View style={[styles.checkbox, g.done && { backgroundColor: virtue.accent_color, borderColor: virtue.accent_color }]}>
                    {busy === g.id ? (
                      <ActivityIndicator size="small" color={g.done ? colors.gold : virtue.accent_color} />
                    ) : g.done ? (
                      <Ionicons name="checkmark" size={15} color={colors.gold} />
                    ) : null}
                  </View>
                  <View style={{ flex: 1 }}>
                    <View style={[styles.typeTag, g.type === "refrain" ? styles.refrainTag : styles.doTag]}>
                      <Ionicons
                        name={g.type === "refrain" ? "hand-left-outline" : "checkmark-circle-outline"}
                        size={10}
                        color={g.type === "refrain" ? "#9C3B2E" : "#5B7553"}
                      />
                      <Text style={[styles.typeTagText, { color: g.type === "refrain" ? "#9C3B2E" : "#5B7553" }]}>
                        {g.type === "refrain" ? "REFRAIN" : "DO"}
                      </Text>
                    </View>
                    <Text style={[styles.goalText, g.done && styles.goalDone]}>{g.text}</Text>
                  </View>
                </Pressable>
              ))}
            </View>
          ))}

          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row", alignItems: "center",
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
    borderBottomWidth: 1, borderBottomColor: colors.borderSoft, gap: spacing.md,
  },
  headerTitleWrap: { flex: 1, alignItems: "center" },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 18, color: colors.textPrimary },
  scroll: { padding: spacing.lg, gap: spacing.md },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.md },
  errorText: { fontFamily: fonts.bodyRegular, color: colors.textSecondary, textAlign: "center" },
  retry: { paddingHorizontal: spacing.lg, paddingVertical: 10, backgroundColor: colors.primary, borderRadius: radius.round },
  retryText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 13 },

  summary: {
    padding: spacing.lg, borderRadius: radius.lg, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: colors.borderSoft, ...shadow.card, gap: 6,
  },
  summaryTitle: { fontFamily: fonts.headingBold, fontSize: 18, color: colors.textPrimary },
  summarySub: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textMuted },
  progressTrack: { height: 8, borderRadius: 4, backgroundColor: colors.borderSoft, marginTop: 8, overflow: "hidden" },
  progressFill: { height: 8, borderRadius: 4, backgroundColor: colors.gold },
  progressLabel: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  note: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13, color: colors.textSecondary, marginTop: spacing.sm },

  group: {
    padding: spacing.md, borderRadius: radius.lg, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: colors.borderSoft, borderTopWidth: 3, ...shadow.card,
  },
  groupHead: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: spacing.sm },
  groupTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  goalRow: { flexDirection: "row", gap: spacing.sm, alignItems: "flex-start", paddingVertical: spacing.sm, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.borderSoft },
  checkbox: {
    width: 26, height: 26, borderRadius: 13, borderWidth: 1.5, borderColor: colors.borderSoft,
    alignItems: "center", justifyContent: "center", backgroundColor: colors.background, marginTop: 2,
  },
  typeTag: { flexDirection: "row", alignItems: "center", gap: 3, alignSelf: "flex-start", paddingHorizontal: 6, paddingVertical: 2, borderRadius: radius.round, marginBottom: 4 },
  doTag: { backgroundColor: "#5B755322" },
  refrainTag: { backgroundColor: "#9C3B2E22" },
  typeTagText: { fontFamily: fonts.uiSemi, fontSize: 8.5, letterSpacing: 0.8 },
  goalText: { fontFamily: fonts.bodyRegular, fontSize: 14, lineHeight: 21, color: colors.textPrimary },
  goalDone: { textDecorationLine: "line-through", color: colors.textMuted },
});

/**
 * Virtus — hub.
 *
 * Lists the virtues, lets the user build a personal virtue plan (pick one or
 * more virtues + a timeframe → AI-generated goals to do/refrain), and shows
 * their active plans. Free for all; the per-virtue Resources are Premium.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useFocusEffect, useRouter } from "expo-router";

import {
  createVirtuePlan,
  listVirtuePlans,
  listVirtues,
  VirtueListItem,
  VirtuePlan,
} from "@/src/api";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const DAY_OPTIONS = [7, 14, 30, 60];

export default function VirtusIndexScreen() {
  const router = useRouter();
  const [items, setItems] = useState<VirtueListItem[]>([]);
  const [plans, setPlans] = useState<VirtuePlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [days, setDays] = useState(14);
  const [note, setNote] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [v, p] = await Promise.all([listVirtues(), listVirtuePlans()]);
      setItems(v.items || []);
      setPlans(p.items || []);
    } catch (e: any) {
      setError(e?.message || "Could not load Virtus.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useFocusEffect(useCallback(() => { void load(); }, [load]));

  const planVirtues = useMemo(() => items.filter((v) => v.kind !== "saints"), [items]);
  const activePlans = useMemo(() => plans.filter((p) => p.active), [plans]);

  const toggle = (slug: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  };

  const create = async () => {
    if (selected.size === 0 || creating) return;
    setCreating(true);
    setCreateError(null);
    try {
      const plan = await createVirtuePlan({
        virtue_slugs: Array.from(selected),
        days,
        note: note.trim() || undefined,
      });
      setSelected(new Set());
      setNote("");
      router.push({ pathname: "/virtus/plan/[id]", params: { id: plan.id } } as any);
    } catch (e: any) {
      setCreateError(e?.message || "Could not build your plan. Please try again.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="virtus-index">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="virtus-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.headerTitle}>Virtus</Text>
          <Text style={styles.headerSub}>Grow in holiness, one virtue at a time</Text>
        </View>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      ) : error ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable onPress={load} style={({ pressed }) => [styles.retry, pressed && { opacity: 0.7 }]}>
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      ) : (
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
          <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
            <View style={styles.heroIntro}>
              <Ornament />
              <Text style={styles.heroTitle}>The school of virtue</Text>
              <Text style={styles.heroSub}>
                Study the virtues, learn to live them in every season of life, and
                set a goal to grow in the ones the Lord is calling you toward.
              </Text>
            </View>

            {/* Plan builder */}
            <View style={styles.planCard} testID="virtus-plan-builder">
              <Text style={styles.planTitle}>Work on a virtue</Text>
              <Text style={styles.planHint}>Choose one or more virtues to focus on.</Text>
              <View style={styles.chipWrap}>
                {planVirtues.map((v) => {
                  const on = selected.has(v.slug);
                  return (
                    <Pressable
                      key={v.slug}
                      testID={`virtus-plan-virtue-${v.slug}`}
                      onPress={() => toggle(v.slug)}
                      style={({ pressed }) => [
                        styles.chip,
                        on && { backgroundColor: v.accent_color, borderColor: v.accent_color },
                        pressed && { opacity: 0.85 },
                      ]}
                    >
                      <Ionicons
                        name={(v.icon as keyof typeof Ionicons.glyphMap) || "ellipse-outline"}
                        size={13}
                        color={on ? colors.gold : v.accent_color}
                      />
                      <Text style={[styles.chipText, on && { color: colors.gold }]}>{v.name}</Text>
                    </Pressable>
                  );
                })}
              </View>

              <Text style={[styles.planHint, { marginTop: spacing.md }]}>Over what timeframe?</Text>
              <View style={styles.chipWrap}>
                {DAY_OPTIONS.map((d) => {
                  const on = days === d;
                  return (
                    <Pressable
                      key={d}
                      testID={`virtus-plan-days-${d}`}
                      onPress={() => setDays(d)}
                      style={({ pressed }) => [
                        styles.chip,
                        on && { backgroundColor: colors.primary, borderColor: colors.primary },
                        pressed && { opacity: 0.85 },
                      ]}
                    >
                      <Text style={[styles.chipText, on && { color: colors.gold }]}>{d} days</Text>
                    </Pressable>
                  );
                })}
              </View>

              <TextInput
                testID="virtus-plan-note"
                value={note}
                onChangeText={setNote}
                placeholder="Anything you'd like the plan to address? (optional)"
                placeholderTextColor={colors.textMuted}
                style={styles.noteInput}
                multiline
              />

              {createError ? <Text style={styles.createError}>{createError}</Text> : null}

              <Pressable
                testID="virtus-create-plan"
                disabled={selected.size === 0 || creating}
                onPress={create}
                style={({ pressed }) => [
                  styles.createBtn,
                  (selected.size === 0 || creating) && { opacity: 0.5 },
                  pressed && { opacity: 0.85 },
                ]}
              >
                {creating ? (
                  <ActivityIndicator color={colors.gold} size="small" />
                ) : (
                  <>
                    <Ionicons name="sparkles" size={15} color={colors.gold} />
                    <Text style={styles.createBtnText}>
                      {selected.size === 0 ? "Pick a virtue to begin" : `Build my ${days}-day plan`}
                    </Text>
                  </>
                )}
              </Pressable>
            </View>

            {/* Active plans */}
            {activePlans.length > 0 ? (
              <View style={styles.section}>
                <Text style={styles.sectionLabel}>YOUR PLANS</Text>
                {activePlans.map((p) => (
                  <Pressable
                    key={p.id}
                    testID={`virtus-plan-row-${p.id}`}
                    onPress={() => router.push({ pathname: "/virtus/plan/[id]", params: { id: p.id } } as any)}
                    style={({ pressed }) => [styles.planRow, pressed && { opacity: 0.85 }]}
                  >
                    <View style={{ flex: 1 }}>
                      <Text style={styles.planRowTitle} numberOfLines={1}>
                        {p.virtues.map((v) => v.name).join(" · ")}
                      </Text>
                      <Text style={styles.planRowSub}>
                        {p.completed}/{p.total} goals · ends {p.end_date}
                      </Text>
                      <View style={styles.progressTrack}>
                        <View
                          style={[
                            styles.progressFill,
                            { width: `${p.total ? (p.completed / p.total) * 100 : 0}%` },
                          ]}
                        />
                      </View>
                    </View>
                    <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
                  </Pressable>
                ))}
              </View>
            ) : null}

            {/* Virtue catalogue */}
            <View style={styles.section}>
              <Text style={styles.sectionLabel}>THE VIRTUES</Text>
              {items.map((v) => (
                <Pressable
                  key={v.slug}
                  testID={`virtus-card-${v.slug}`}
                  onPress={() => router.push({ pathname: "/virtus/[slug]", params: { slug: v.slug } } as any)}
                  style={({ pressed }) => [
                    styles.virtueTile,
                    { borderLeftColor: v.accent_color },
                    pressed && { opacity: 0.85 },
                  ]}
                >
                  <View style={[styles.virtueIcon, { backgroundColor: v.accent_color + "22", borderColor: v.accent_color }]}>
                    <Ionicons name={(v.icon as keyof typeof Ionicons.glyphMap) || "ellipse-outline"} size={22} color={v.accent_color} />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.virtueName}>{v.name}</Text>
                    <Text style={styles.virtueTagline} numberOfLines={2}>{v.tagline}</Text>
                    {v.opposite_vice ? (
                      <Text style={styles.virtueVice}>vs. {v.opposite_vice}</Text>
                    ) : null}
                  </View>
                  <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
                </Pressable>
              ))}
            </View>

            <View style={{ height: spacing.xxl }} />
          </ScrollView>
        </KeyboardAvoidingView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
    gap: spacing.md,
  },
  headerTitleWrap: { flex: 1, alignItems: "center" },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.textPrimary },
  headerSub: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, fontSize: 11, marginTop: 1 },
  scroll: { padding: spacing.lg, gap: spacing.lg },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.md },
  errorText: { fontFamily: fonts.bodyRegular, color: colors.textSecondary, textAlign: "center" },
  retry: { paddingHorizontal: spacing.lg, paddingVertical: 10, backgroundColor: colors.primary, borderRadius: radius.round },
  retryText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 13 },

  heroIntro: { alignItems: "center", gap: spacing.sm },
  heroTitle: { fontFamily: fonts.headingBold, fontSize: 22, color: colors.textPrimary, textAlign: "center", marginTop: spacing.sm },
  heroSub: { fontFamily: fonts.bodyRegular, fontSize: 14, lineHeight: 22, color: colors.textSecondary, textAlign: "center", paddingHorizontal: spacing.sm },

  planCard: {
    padding: spacing.lg,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
    gap: spacing.xs,
  },
  planTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  planHint: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary },
  chipWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 8 },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.background,
  },
  chipText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary },
  noteInput: {
    marginTop: spacing.md,
    minHeight: 44,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textPrimary,
    backgroundColor: colors.background,
    textAlignVertical: "top",
  },
  createError: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.danger || "#B23A48", marginTop: spacing.sm },
  createBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    marginTop: spacing.md,
    paddingVertical: 13,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
  },
  createBtnText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.gold, letterSpacing: 0.4 },

  section: { gap: spacing.sm },
  sectionLabel: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 1.4, color: colors.textMuted, marginBottom: 2 },

  planRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  planRowTitle: { fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary },
  planRowSub: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textMuted, marginTop: 2 },
  progressTrack: { height: 6, borderRadius: 3, backgroundColor: colors.borderSoft, marginTop: 8, overflow: "hidden" },
  progressFill: { height: 6, borderRadius: 3, backgroundColor: colors.gold },

  virtueTile: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderLeftWidth: 4,
    ...shadow.card,
  },
  virtueIcon: { width: 46, height: 46, borderRadius: 23, alignItems: "center", justifyContent: "center", borderWidth: 1.5 },
  virtueName: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  virtueTagline: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textSecondary, marginTop: 2 },
  virtueVice: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 11, color: colors.textMuted, marginTop: 3 },
});

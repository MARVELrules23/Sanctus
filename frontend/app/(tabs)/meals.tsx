import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";

import { api, DayDoc, GoalMode, LiturgicalDay, MealPlan } from "@/src/api";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import Ornament from "@/src/components/Ornament";
import GoalModeToggle from "@/src/components/GoalModeToggle";
import AISuggestionModal from "@/src/components/AISuggestionModal";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { addDaysISO, parseISO, startOfWeekISO, todayISO } from "@/src/date-utils";
import { loadGoalMode, saveGoalMode } from "@/src/utils/goal-mode";

const DOW_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function MealsScreen() {
  const router = useRouter();
  const [weekStart, setWeekStart] = useState(() => startOfWeekISO(todayISO()));
  const [selected, setSelected] = useState(() => todayISO());
  const [meals, setMeals] = useState<Record<string, DayDoc<MealPlan> | null>>({});
  const [lit, setLit] = useState<LiturgicalDay | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [goalMode, setGoalMode] = useState<GoalMode>("liturgical");
  const [hasWellness, setHasWellness] = useState(false);
  const [aiOpen, setAiOpen] = useState(false);
  // Last note per ISO date used in this session — persists only in memory.
  const [notes, setNotes] = useState<Record<string, string>>({});

  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => addDaysISO(weekStart, i)), [weekStart]);

  // Load persisted goal_mode once.
  useEffect(() => {
    (async () => setGoalMode(await loadGoalMode()))();
  }, []);

  // Re-check wellness profile every time the tab is focused so the toggle stays accurate.
  useFocusEffect(
    useCallback(() => {
      let active = true;
      (async () => {
        try {
          const w = await api<{ weight_kg?: number; height_cm?: number; goal_type?: string }>(
            "/wellness/profile",
          );
          if (active) setHasWellness(!!(w?.weight_kg || w?.target_weight_kg || w?.goal_type));
        } catch {
          if (active) setHasWellness(false);
        }
      })();
      return () => {
        active = false;
      };
    }, []),
  );

  const loadWeek = useCallback(async () => {
    const res = await api<Record<string, DayDoc<MealPlan> | null>>(`/meals/week?start=${weekStart}`);
    setMeals(res);
  }, [weekStart]);

  const loadLit = useCallback(async (date: string) => {
    const l = await api<LiturgicalDay>(`/liturgical/day?date=${date}`);
    setLit(l);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await Promise.all([loadWeek(), loadLit(selected)]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadWeek, loadLit, selected]);

  const onSelect = async (d: string) => {
    setSelected(d);
    await loadLit(d);
  };

  const onPrev = () => {
    const ns = addDaysISO(weekStart, -7);
    setWeekStart(ns);
  };
  const onNext = () => {
    const ns = addDaysISO(weekStart, 7);
    setWeekStart(ns);
  };

  const generate = async (noteOverride?: string | null) => {
    setGenerating(true);
    // `null` clears the note. `undefined` keeps the existing one.
    const noteToUse =
      noteOverride === null ? "" : (noteOverride ?? notes[selected] ?? "");
    try {
      const body: Record<string, unknown> = { date: selected, goal_mode: goalMode };
      if (noteToUse.trim()) body.user_note = noteToUse.trim();
      const res = await api<DayDoc<MealPlan>>("/meals/generate", {
        method: "POST",
        body,
      });
      setMeals((m) => ({ ...m, [selected]: res }));
      setNotes((n) => ({ ...n, [selected]: noteToUse.trim() }));
    } catch (e) {
      console.warn("meals gen failed", e);
    } finally {
      setGenerating(false);
    }
  };

  const submitAiSuggestion = async (note: string) => {
    setAiOpen(false);
    await generate(note);
  };

  const clearNote = () => {
    setNotes((n) => ({ ...n, [selected]: "" }));
  };

  const onGoalModeChange = (m: GoalMode) => {
    setGoalMode(m);
    void saveGoalMode(m);
  };

  const current = meals[selected];
  const d = parseISO(selected);
  const weekStartObj = parseISO(weekStart);
  const weekEndObj = parseISO(addDaysISO(weekStart, 6));
  const weekLabel = `${weekStartObj.toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${weekEndObj.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="meals-screen">
      {/* Sticky header */}
      <View style={styles.header}>
        <Text style={styles.title}>Meals</Text>
        <Text style={styles.subtitle}>A weekly table set by the Church&apos;s seasons.</Text>
        <View style={styles.weekRow}>
          <Pressable testID="meals-prev-week" onPress={onPrev} hitSlop={12} style={({ pressed }) => pressed && styles.pressed}>
            <Ionicons name="chevron-back" size={22} color={colors.primary} />
          </Pressable>
          <Text style={styles.weekLabel}>{weekLabel}</Text>
          <Pressable testID="meals-next-week" onPress={onNext} hitSlop={12} style={({ pressed }) => pressed && styles.pressed}>
            <Ionicons name="chevron-forward" size={22} color={colors.primary} />
          </Pressable>
        </View>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.chipsRow}
        >
          {days.map((dateStr, i) => {
            const dd = parseISO(dateStr);
            const isSel = dateStr === selected;
            return (
              <Pressable
                key={dateStr}
                testID={`meals-day-chip-${i}`}
                onPress={() => onSelect(dateStr)}
                style={[styles.chip, isSel && styles.chipSel]}
              >
                <Text style={[styles.chipDow, isSel && styles.chipSelText]}>{DOW_SHORT[i]}</Text>
                <Text style={[styles.chipNum, isSel && styles.chipSelText]}>{dd.getDate()}</Text>
              </Pressable>
            );
          })}
        </ScrollView>
        <View style={styles.toggleWrap}>
          <GoalModeToggle
            testID="meals-goal-toggle"
            value={goalMode}
            onChange={onGoalModeChange}
            goalsDisabled={!hasWellness}
            onGoalsDisabledPress={() => router.push("/(tabs)/wellness")}
          />
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {lit ? (
          <View style={styles.litRow}>
            <LiturgicalBadge color={lit.color} label={lit.season} />
            {lit.is_abstinence && <LiturgicalBadge color="red" label="Abstinence" />}
            {lit.is_fast && <LiturgicalBadge color="purple" label="Fast" />}
            {lit.is_sunday && <LiturgicalBadge color="gold" label="Lord's Day" />}
          </View>
        ) : null}
        {lit?.feast ? <Text style={styles.feast}>{lit.feast}</Text> : null}
        <Text style={styles.dayHeader}>
          {d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
        </Text>

        <View style={styles.actionRow}>
          <Pressable
            testID="meals-custom-button"
            onPress={() => router.push({ pathname: "/edit-meal", params: { date: selected } })}
            style={({ pressed }) => [styles.actionBtn, pressed && styles.pressed]}
          >
            <Ionicons name="create-outline" size={14} color={colors.primary} />
            <Text style={styles.actionBtnText}>Custom plan</Text>
          </Pressable>
          <Pressable
            testID="meals-grocery-button"
            onPress={() => router.push({ pathname: "/grocery", params: { start: weekStart } })}
            style={({ pressed }) => [styles.actionBtn, pressed && styles.pressed]}
          >
            <Ionicons name="cart-outline" size={14} color={colors.primary} />
            <Text style={styles.actionBtnText}>Grocery list</Text>
          </Pressable>
          <Pressable
            testID="meals-ai-suggest-button"
            onPress={() => setAiOpen(true)}
            style={({ pressed }) => [styles.actionBtn, styles.actionBtnAccent, pressed && styles.pressed]}
          >
            <Ionicons name="sparkles-outline" size={14} color={colors.gold} />
            <Text style={[styles.actionBtnText, styles.actionBtnTextAccent]}>Suggest to AI</Text>
          </Pressable>
        </View>

        <Ornament />

        {loading ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
        ) : current ? (
          <>
            <MealCard label="Breakfast" plan={current.plan.breakfast} />
            <MealCard label="Lunch" plan={current.plan.lunch} />
            <MealCard label="Dinner" plan={current.plan.dinner} />
            <View style={styles.reflectionCard} testID="meals-reflection">
              <Ionicons name="leaf-outline" size={20} color={colors.liturgical.purple} />
              <Text style={styles.reflectionText}>{current.plan.reflection}</Text>
            </View>
            {notes[selected] ? (
              <Pressable
                testID="meals-applied-note"
                onPress={() => setAiOpen(true)}
                style={({ pressed }) => [styles.appliedNote, pressed && styles.pressed]}
              >
                <Ionicons name="sparkles" size={14} color={colors.gold} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.appliedNoteLabel}>YOUR NOTE TO THE AI</Text>
                  <Text style={styles.appliedNoteText} numberOfLines={2}>
                    {notes[selected]}
                  </Text>
                </View>
                <Pressable
                  onPress={clearNote}
                  hitSlop={10}
                  testID="meals-clear-note"
                  style={{ padding: 4 }}
                >
                  <Ionicons name="close" size={16} color={colors.textMuted} />
                </Pressable>
              </Pressable>
            ) : null}
            <Pressable
              testID="meals-regenerate-button"
              onPress={() => generate()}
              disabled={generating}
              style={({ pressed }) => [styles.regenBtn, pressed && styles.pressed]}
            >
              {generating ? (
                <ActivityIndicator color={colors.primary} />
              ) : (
                <>
                  <Ionicons name="refresh-outline" size={16} color={colors.primary} />
                  <Text style={styles.regenBtnText}>Regenerate this day</Text>
                </>
              )}
            </Pressable>
          </>
        ) : (
          <View style={styles.empty}>
            <Ionicons name="restaurant-outline" size={36} color={colors.gold} />
            <Text style={styles.emptyTitle}>No meals yet for this day</Text>
            <Text style={styles.emptyText}>
              Sanctus will craft breakfast, lunch &amp; dinner — observing fasts, feasts and abstinence as the calendar requires.
            </Text>
            <Pressable
              testID="meals-generate-button"
              onPress={() => generate()}
              disabled={generating}
              style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
            >
              {generating ? (
                <ActivityIndicator color={colors.gold} />
              ) : (
                <>
                  <Ionicons name="sparkles-outline" size={16} color={colors.gold} />
                  <Text style={styles.primaryBtnText}>Generate Day&apos;s Meals</Text>
                </>
              )}
            </Pressable>
          </View>
        )}

        <View style={{ height: spacing.xxl }} />
      </ScrollView>
      <AISuggestionModal
        visible={aiOpen}
        title="Talk to the AI about today's meals"
        subtitle="Your note guides the AI — abstinence on Fridays and Lenten fasts still hold."
        placeholder="e.g. More protein, less carbs. I have leftover chicken to use."
        initialValue={notes[selected] || ""}
        examples={[
          "More protein, less carbs",
          "Use leftovers from yesterday",
          "Mediterranean — fish and vegetables",
          "Quick prep, under 20 minutes per meal",
          "Family-friendly meals my kids will eat",
          "Higher calorie, I'm bulking",
        ]}
        submitting={generating}
        onClose={() => setAiOpen(false)}
        onSubmit={submitAiSuggestion}
      />
    </SafeAreaView>
  );
}

function MealCard({ label, plan }: { label: string; plan: MealPlan["breakfast"] }) {
  return (
    <View style={styles.mealCard} testID={`meal-card-${label.toLowerCase()}`}>
      <Text style={styles.mealLabel}>{label.toUpperCase()}</Text>
      <Text style={styles.mealName}>{plan.name}</Text>
      <Text style={styles.mealDesc}>{plan.description}</Text>
      <View style={styles.mealMeta}>
        <Ionicons name="time-outline" size={14} color={colors.textMuted} />
        <Text style={styles.mealMetaText}>{plan.prep_minutes} min prep</Text>
        <Ionicons name="leaf-outline" size={14} color={colors.textMuted} style={{ marginLeft: spacing.md }} />
        <Text style={styles.mealMetaText}>{plan.ingredients.length} ingredients</Text>
      </View>
      <View style={styles.ingredients}>
        {plan.ingredients.map((ing, idx) => (
          <View key={idx} style={styles.ingredientPill}>
            <Text style={styles.ingredientText}>{ing}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
    backgroundColor: colors.background,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  title: { fontFamily: fonts.headingBold, fontSize: 30, color: colors.textPrimary },
  subtitle: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: 2,
  },
  weekRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: spacing.md,
  },
  weekLabel: { fontFamily: fonts.uiSemi, color: colors.textPrimary, fontSize: 14 },
  chipsRow: { gap: spacing.sm, paddingVertical: spacing.sm, paddingRight: spacing.sm },
  toggleWrap: { alignItems: "center", paddingBottom: spacing.sm },
  chip: {
    width: 52,
    height: 64,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
    flexShrink: 0,
  },
  chipSel: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  chipDow: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, letterSpacing: 0.6 },
  chipNum: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.textPrimary, marginTop: 2 },
  chipSelText: { color: colors.gold },
  scroll: { paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  litRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  feast: {
    fontFamily: fonts.headingSemi,
    color: colors.liturgical.red,
    fontSize: 18,
    marginTop: spacing.sm,
  },
  dayHeader: {
    fontFamily: fonts.headingBold,
    fontSize: 26,
    color: colors.textPrimary,
    marginTop: spacing.xs,
  },
  mealCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginTop: spacing.md,
    ...shadow.card,
  },
  mealLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.5,
    color: colors.gold,
    marginBottom: spacing.xs,
  },
  mealName: { fontFamily: fonts.headingSemi, fontSize: 22, color: colors.textPrimary },
  mealDesc: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textSecondary, lineHeight: 22, marginTop: 4 },
  mealMeta: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: spacing.sm },
  mealMetaText: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textMuted },
  ingredients: { flexDirection: "row", flexWrap: "wrap", gap: spacing.xs, marginTop: spacing.sm },
  ingredientPill: {
    backgroundColor: colors.borderSoft,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.round,
  },
  ingredientText: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textPrimary },
  reflectionCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    backgroundColor: "#F5EDE0",
    padding: spacing.md,
    borderRadius: radius.md,
    marginTop: spacing.md,
    borderLeftWidth: 3,
    borderLeftColor: colors.liturgical.purple,
  },
  reflectionText: {
    flex: 1,
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textPrimary,
    fontSize: 14,
    lineHeight: 22,
  },
  regenBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: colors.primary,
    paddingVertical: 12,
    borderRadius: radius.md,
    marginTop: spacing.md,
  },
  regenBtnText: { fontFamily: fonts.uiSemi, color: colors.primary, fontSize: 14 },
  empty: { alignItems: "center", padding: spacing.xl, gap: spacing.sm },
  emptyTitle: { fontFamily: fonts.headingSemi, fontSize: 20, color: colors.textPrimary },
  emptyText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: "center",
    lineHeight: 22,
  },
  primaryBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 14,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  primaryBtnText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 15, letterSpacing: 0.6 },
  actionRow: {
    flexDirection: "row",
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  actionBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 10,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  actionBtnText: {
    fontFamily: fonts.uiSemi,
    fontSize: 13,
    color: colors.primary,
    letterSpacing: 0.3,
  },
  actionBtnAccent: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  actionBtnTextAccent: {
    color: colors.gold,
  },
  appliedNote: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: "#FBF6E8",
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginTop: spacing.md,
  },
  appliedNoteLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1.2,
    color: colors.gold,
  },
  appliedNoteText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textPrimary,
    marginTop: 2,
  },
  pressed: { opacity: 0.7 },
});

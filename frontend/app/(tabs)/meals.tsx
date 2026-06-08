import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";

import { api, DayDoc, LiturgicalDay, MealPlan } from "@/src/api";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { addDaysISO, parseISO, startOfWeekISO, todayISO } from "@/src/date-utils";

const DOW_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function MealsScreen() {
  const [weekStart, setWeekStart] = useState(() => startOfWeekISO(todayISO()));
  const [selected, setSelected] = useState(() => todayISO());
  const [meals, setMeals] = useState<Record<string, DayDoc<MealPlan> | null>>({});
  const [lit, setLit] = useState<LiturgicalDay | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => addDaysISO(weekStart, i)), [weekStart]);

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

  const generate = async () => {
    setGenerating(true);
    try {
      const res = await api<DayDoc<MealPlan>>("/meals/generate", { method: "POST", body: { date: selected } });
      setMeals((m) => ({ ...m, [selected]: res }));
    } catch (e) {
      console.warn("meals gen failed", e);
    } finally {
      setGenerating(false);
    }
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
            <Pressable
              testID="meals-regenerate-button"
              onPress={generate}
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
              onPress={generate}
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
  pressed: { opacity: 0.7 },
});

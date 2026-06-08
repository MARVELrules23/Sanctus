import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  ImageBackground,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";

import { api, DayDoc, GoalMode, LiturgicalDay, WorkoutPlan } from "@/src/api";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import GoalModeToggle from "@/src/components/GoalModeToggle";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { addDaysISO, parseISO, startOfWeekISO, todayISO } from "@/src/date-utils";
import { loadGoalMode, saveGoalMode } from "@/src/utils/goal-mode";

const HERO_IMAGE =
  "https://images.unsplash.com/photo-1758520704946-74b96f67ded3?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2MzR8MHwxfHNlYXJjaHwzfHxvdXRkb29yJTIwd29ya291dCUyMG5hdHVyZSUyMGZpdG5lc3N8ZW58MHx8fHwxNzgwODg4OTA4fDA&ixlib=rb-4.1.0&q=85";

const DOW_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function WorkoutsScreen() {
  const router = useRouter();
  const [weekStart, setWeekStart] = useState(() => startOfWeekISO(todayISO()));
  const [selected, setSelected] = useState(() => todayISO());
  const [workouts, setWorkouts] = useState<Record<string, DayDoc<WorkoutPlan> | null>>({});
  const [lit, setLit] = useState<LiturgicalDay | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [goalMode, setGoalMode] = useState<GoalMode>("liturgical");
  const [hasWellness, setHasWellness] = useState(false);

  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => addDaysISO(weekStart, i)), [weekStart]);

  useEffect(() => {
    (async () => setGoalMode(await loadGoalMode()))();
  }, []);

  useFocusEffect(
    useCallback(() => {
      let active = true;
      (async () => {
        try {
          const w = await api<{ weight_kg?: number; target_weight_kg?: number; goal_type?: string }>(
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

  const load = useCallback(async () => {
    const [w, l] = await Promise.all([
      api<Record<string, DayDoc<WorkoutPlan> | null>>(`/workouts/week?start=${weekStart}`),
      api<LiturgicalDay>(`/liturgical/day?date=${selected}`),
    ]);
    setWorkouts(w);
    setLit(l);
  }, [weekStart, selected]);

  useEffect(() => {
    let c = false;
    (async () => {
      try {
        await load();
      } finally {
        if (!c) setLoading(false);
      }
    })();
    return () => {
      c = true;
    };
  }, [load]);

  const generate = async () => {
    setGenerating(true);
    try {
      const res = await api<DayDoc<WorkoutPlan>>("/workouts/generate", {
        method: "POST",
        body: { date: selected, goal_mode: goalMode },
      });
      setWorkouts((w) => ({ ...w, [selected]: res }));
    } catch (e) {
      console.warn("workout gen failed", e);
    } finally {
      setGenerating(false);
    }
  };

  const onGoalModeChange = (m: GoalMode) => {
    setGoalMode(m);
    void saveGoalMode(m);
  };

  const current = workouts[selected];
  const weekStartObj = parseISO(weekStart);
  const weekEndObj = parseISO(addDaysISO(weekStart, 6));
  const weekLabel = `${weekStartObj.toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${weekEndObj.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="workouts-screen">
      <View style={styles.header}>
        <Text style={styles.title}>Discipline</Text>
        <Text style={styles.subtitle}>Body and soul, ordered to the seasons.</Text>
        <View style={styles.weekRow}>
          <Pressable testID="workouts-prev-week" onPress={() => setWeekStart(addDaysISO(weekStart, -7))} hitSlop={12}>
            <Ionicons name="chevron-back" size={22} color={colors.primary} />
          </Pressable>
          <Text style={styles.weekLabel}>{weekLabel}</Text>
          <Pressable testID="workouts-next-week" onPress={() => setWeekStart(addDaysISO(weekStart, 7))} hitSlop={12}>
            <Ionicons name="chevron-forward" size={22} color={colors.primary} />
          </Pressable>
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipsRow}>
          {days.map((dateStr, i) => {
            const dd = parseISO(dateStr);
            const isSel = dateStr === selected;
            const hasW = !!workouts[dateStr];
            return (
              <Pressable
                key={dateStr}
                testID={`workouts-day-chip-${i}`}
                onPress={() => setSelected(dateStr)}
                style={[styles.chip, isSel && styles.chipSel]}
              >
                <Text style={[styles.chipDow, isSel && styles.chipSelText]}>{DOW_SHORT[i]}</Text>
                <Text style={[styles.chipNum, isSel && styles.chipSelText]}>{dd.getDate()}</Text>
                {hasW ? <View style={[styles.chipDot, { backgroundColor: isSel ? colors.gold : colors.primary }]} /> : <View style={styles.chipDot} />}
              </Pressable>
            );
          })}
        </ScrollView>
        <View style={styles.toggleWrap}>
          <GoalModeToggle
            testID="workouts-goal-toggle"
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
            {lit.is_sunday && <LiturgicalBadge color="gold" label="Day of Rest" />}
          </View>
        ) : null}

        <View style={styles.actionRow}>
          <Pressable
            testID="workouts-custom-button"
            onPress={() => router.push({ pathname: "/edit-workout", params: { date: selected } })}
            style={({ pressed }) => [styles.actionBtn, pressed && styles.pressed]}
          >
            <Ionicons name="create-outline" size={14} color={colors.primary} />
            <Text style={styles.actionBtnText}>Custom plan</Text>
          </Pressable>
          <Pressable
            testID="workouts-rosary-button"
            onPress={() => router.push("/rosary")}
            style={({ pressed }) => [styles.actionBtn, pressed && styles.pressed]}
          >
            <Ionicons name="flower-outline" size={14} color={colors.primary} />
            <Text style={styles.actionBtnText}>Rosary</Text>
          </Pressable>
        </View>

        {loading ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
        ) : current ? (
          <>
            <ImageBackground source={{ uri: HERO_IMAGE }} style={styles.hero} imageStyle={styles.heroImg}>
              <LinearGradient
                colors={["rgba(28,40,65,0.2)", "rgba(28,40,65,0.85)"]}
                style={StyleSheet.absoluteFillObject}
              />
              <View style={styles.heroContent}>
                <Text style={styles.heroFocus}>{current.plan.focus.toUpperCase()}</Text>
                <Text style={styles.heroTitle}>{current.plan.title}</Text>
                <View style={styles.heroMetaRow}>
                  <Ionicons name="time-outline" size={14} color={colors.gold} />
                  <Text style={styles.heroMeta}>{current.plan.duration_minutes} min</Text>
                  <Ionicons name="barbell-outline" size={14} color={colors.gold} style={{ marginLeft: 12 }} />
                  <Text style={styles.heroMeta}>{current.plan.exercises.length} movements</Text>
                </View>
              </View>
            </ImageBackground>

            <View style={styles.prayerCard} testID="opening-prayer">
              <View style={styles.cardHeader}>
                <Ionicons name="rose-outline" size={16} color={colors.gold} />
                <Text style={styles.cardHeaderText}>OPENING PRAYER</Text>
              </View>
              <Text style={styles.prayerText}>{current.plan.opening_prayer}</Text>
            </View>

            <Text style={styles.sectionTitle}>The Discipline</Text>
            {current.plan.exercises.map((ex, idx) => (
              <View key={idx} style={styles.exerciseCard} testID={`exercise-${idx}`}>
                <View style={styles.exerciseNum}>
                  <Text style={styles.exerciseNumText}>{idx + 1}</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.exerciseName}>{ex.name}</Text>
                  <Text style={styles.exerciseSets}>{ex.sets}</Text>
                  {ex.notes ? <Text style={styles.exerciseNotes}>{ex.notes}</Text> : null}
                </View>
              </View>
            ))}

            <View style={styles.prayerCard} testID="closing-prayer">
              <View style={styles.cardHeader}>
                <Ionicons name="flower-outline" size={16} color={colors.gold} />
                <Text style={styles.cardHeaderText}>CLOSING PRAYER</Text>
              </View>
              <Text style={styles.prayerText}>{current.plan.closing_prayer}</Text>
            </View>

            <View style={styles.reflectionCard}>
              <Text style={styles.reflectionText}>{current.plan.reflection}</Text>
            </View>

            <Pressable
              testID="workouts-regenerate-button"
              onPress={generate}
              disabled={generating}
              style={({ pressed }) => [styles.regenBtn, pressed && styles.pressed]}
            >
              {generating ? (
                <ActivityIndicator color={colors.primary} />
              ) : (
                <>
                  <Ionicons name="refresh-outline" size={16} color={colors.primary} />
                  <Text style={styles.regenBtnText}>Regenerate this workout</Text>
                </>
              )}
            </Pressable>
          </>
        ) : (
          <View style={styles.empty}>
            <Ionicons name="barbell-outline" size={36} color={colors.gold} />
            <Text style={styles.emptyTitle}>No workout planned</Text>
            <Text style={styles.emptyText}>
              Sanctus will shape a workout — penitential in Lent, joyful in Easter, restful on Sundays.
            </Text>
            <Pressable
              testID="workouts-generate-button"
              onPress={generate}
              disabled={generating}
              style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
            >
              {generating ? (
                <ActivityIndicator color={colors.gold} />
              ) : (
                <>
                  <Ionicons name="sparkles-outline" size={16} color={colors.gold} />
                  <Text style={styles.primaryBtnText}>Generate Workout</Text>
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
  weekRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: spacing.md },
  weekLabel: { fontFamily: fonts.uiSemi, color: colors.textPrimary, fontSize: 14 },
  chipsRow: { gap: spacing.sm, paddingVertical: spacing.sm, paddingRight: spacing.sm },
  toggleWrap: { alignItems: "center", paddingBottom: spacing.sm },
  chip: {
    width: 52,
    height: 70,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
    flexShrink: 0,
    paddingTop: 6,
  },
  chipSel: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipDow: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, letterSpacing: 0.6 },
  chipNum: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.textPrimary, marginTop: 2 },
  chipSelText: { color: colors.gold },
  chipDot: { width: 5, height: 5, borderRadius: 3, marginTop: 5, backgroundColor: "transparent" },
  scroll: { paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  litRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
  hero: {
    height: 180,
    borderRadius: radius.lg,
    overflow: "hidden",
    justifyContent: "flex-end",
    ...shadow.card,
  },
  heroImg: { borderRadius: radius.lg },
  heroContent: { padding: spacing.lg },
  heroFocus: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 11, letterSpacing: 1.5 },
  heroTitle: { fontFamily: fonts.headingBold, color: "#FAF9F6", fontSize: 26, marginTop: 4 },
  heroMetaRow: { flexDirection: "row", alignItems: "center", marginTop: spacing.sm, gap: 4 },
  heroMeta: { fontFamily: fonts.uiMedium, color: colors.gold, fontSize: 12 },
  prayerCard: {
    backgroundColor: "#F5EDE0",
    padding: spacing.lg,
    borderRadius: radius.lg,
    marginTop: spacing.md,
    borderLeftWidth: 3,
    borderLeftColor: colors.gold,
  },
  cardHeader: { flexDirection: "row", alignItems: "center", gap: spacing.xs, marginBottom: spacing.xs },
  cardHeaderText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.5,
    color: colors.gold,
  },
  prayerText: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textPrimary,
    fontSize: 16,
    lineHeight: 26,
  },
  sectionTitle: { fontFamily: fonts.headingBold, fontSize: 22, color: colors.textPrimary, marginTop: spacing.lg, marginBottom: spacing.sm },
  exerciseCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.md,
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginBottom: spacing.sm,
  },
  exerciseNum: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  exerciseNumText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 14 },
  exerciseName: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  exerciseSets: { fontFamily: fonts.uiMedium, fontSize: 13, color: colors.gold, marginTop: 2 },
  exerciseNotes: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, marginTop: 4, lineHeight: 20 },
  reflectionCard: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.lg,
    borderRadius: radius.md,
    marginTop: spacing.md,
  },
  reflectionText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.liturgical.purple, fontSize: 14, lineHeight: 22 },
  regenBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
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
    marginTop: spacing.md,
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
  pressed: { opacity: 0.7 },
});

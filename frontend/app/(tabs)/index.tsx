import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";

import { api, DayDoc, LiturgicalDay, MealPlan, WorkoutPlan } from "@/src/api";
import { useAuth } from "@/src/auth-context";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { formatLong, todayISO } from "@/src/date-utils";

const DEVOTIONS = [
  {
    title: "Morning Offering",
    text: "O Jesus, through the Immaculate Heart of Mary, I offer You my prayers, works, joys and sufferings of this day in union with the Holy Sacrifice of the Mass.",
  },
  {
    title: "Glory Be",
    text: "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.",
  },
  {
    title: "Anima Christi",
    text: "Soul of Christ, sanctify me. Body of Christ, save me. Blood of Christ, inebriate me. Water from the side of Christ, wash me.",
  },
];

function pickDevotion(dateStr: string) {
  const d = new Date(dateStr);
  return DEVOTIONS[d.getDate() % DEVOTIONS.length];
}

export default function TodayScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const [date] = useState(() => todayISO());
  const [lit, setLit] = useState<LiturgicalDay | null>(null);
  const [meal, setMeal] = useState<DayDoc<MealPlan> | null>(null);
  const [workout, setWorkout] = useState<DayDoc<WorkoutPlan> | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [genMeal, setGenMeal] = useState(false);
  const [genWorkout, setGenWorkout] = useState(false);

  const load = useCallback(async () => {
    const [l, m, w] = await Promise.all([
      api<LiturgicalDay>(`/liturgical/day?date=${date}`),
      api<DayDoc<MealPlan> | Record<string, never>>(`/meals?date=${date}`),
      api<DayDoc<WorkoutPlan> | Record<string, never>>(`/workouts?date=${date}`),
    ]);
    setLit(l);
    setMeal("plan" in m ? (m as DayDoc<MealPlan>) : null);
    setWorkout("plan" in w ? (w as DayDoc<WorkoutPlan>) : null);
  }, [date]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await load();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await load();
    } finally {
      setRefreshing(false);
    }
  }, [load]);

  const generateMeal = async () => {
    setGenMeal(true);
    try {
      const res = await api<DayDoc<MealPlan>>("/meals/generate", { method: "POST", body: { date } });
      setMeal(res);
    } catch (e) {
      console.warn("meal gen failed", e);
    } finally {
      setGenMeal(false);
    }
  };

  const generateWorkout = async () => {
    setGenWorkout(true);
    try {
      const res = await api<DayDoc<WorkoutPlan>>("/workouts/generate", { method: "POST", body: { date } });
      setWorkout(res);
    } catch (e) {
      console.warn("workout gen failed", e);
    } finally {
      setGenWorkout(false);
    }
  };

  const devotion = pickDevotion(date);
  const longDate = formatLong(new Date(date));
  const firstName = user?.name?.split(" ")[0] ?? "friend";

  if (loading) {
    return (
      <SafeAreaView style={styles.safe} edges={["top"]} testID="today-screen">
        <View style={styles.loadingWrap}>
          <ActivityIndicator color={colors.gold} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="today-screen">
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
      >
        {/* Header */}
        <Text style={styles.greeting}>Pax tecum, {firstName}.</Text>
        <Text style={styles.date}>{longDate}</Text>
        {lit ? (
          <View style={styles.badgeRow}>
            <LiturgicalBadge color={lit.color} label={lit.season} testID="today-season-badge" />
            {lit.is_abstinence && (
              <LiturgicalBadge color="red" label="Abstinence" testID="today-abstinence-badge" />
            )}
            {lit.is_fast && <LiturgicalBadge color="purple" label="Fast" testID="today-fast-badge" />}
          </View>
        ) : null}
        {lit?.feast ? <Text style={styles.feast}>{lit.feast}</Text> : null}

        <Ornament />

        {/* Devotion */}
        <View style={styles.card} testID="devotion-card">
          <View style={styles.cardHeader}>
            <Ionicons name="book-outline" size={18} color={colors.gold} />
            <Text style={styles.cardHeaderText}>DAILY DEVOTION</Text>
          </View>
          <Text style={styles.devotionTitle}>{devotion.title}</Text>
          <Text style={styles.devotionText}>{devotion.text}</Text>
        </View>

        {/* Meal */}
        <View style={styles.card} testID="today-meal-card">
          <View style={styles.cardHeader}>
            <Ionicons name="restaurant-outline" size={18} color={colors.gold} />
            <Text style={styles.cardHeaderText}>TODAY&apos;S NOURISHMENT</Text>
          </View>
          {meal ? (
            <>
              <Text style={styles.mealName}>{meal.plan.dinner.name}</Text>
              <Text style={styles.mealDesc}>{meal.plan.dinner.description}</Text>
              <Text style={styles.reflection}>{meal.plan.reflection}</Text>
              <Pressable
                testID="view-meals-button"
                onPress={() => router.push("/(tabs)/meals")}
                style={({ pressed }) => [styles.linkBtn, pressed && styles.pressed]}
              >
                <Text style={styles.linkBtnText}>View all meals</Text>
                <Ionicons name="chevron-forward" size={16} color={colors.gold} />
              </Pressable>
            </>
          ) : (
            <>
              <Text style={styles.empty}>
                {lit?.is_abstinence
                  ? "A day of abstinence — let us prepare a humble fish or vegetable meal."
                  : "No meal planned yet. Let Sanctus craft one fit for today."}
              </Text>
              <Pressable
                testID="generate-today-meal-button"
                onPress={generateMeal}
                disabled={genMeal}
                style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
              >
                {genMeal ? (
                  <ActivityIndicator color={colors.gold} />
                ) : (
                  <>
                    <Ionicons name="sparkles-outline" size={16} color={colors.gold} />
                    <Text style={styles.primaryBtnText}>Generate Meal Plan</Text>
                  </>
                )}
              </Pressable>
            </>
          )}
        </View>

        {/* Workout */}
        <View style={styles.card} testID="today-workout-card">
          <View style={styles.cardHeader}>
            <Ionicons name="barbell-outline" size={18} color={colors.gold} />
            <Text style={styles.cardHeaderText}>TODAY&apos;S DISCIPLINE</Text>
          </View>
          {workout ? (
            <>
              <Text style={styles.mealName}>{workout.plan.title}</Text>
              <Text style={styles.mealDesc}>
                {workout.plan.focus} · {workout.plan.duration_minutes} min
              </Text>
              <Text style={styles.reflection}>{workout.plan.reflection}</Text>
              <Pressable
                testID="view-workouts-button"
                onPress={() => router.push("/(tabs)/workouts")}
                style={({ pressed }) => [styles.linkBtn, pressed && styles.pressed]}
              >
                <Text style={styles.linkBtnText}>Begin with prayer</Text>
                <Ionicons name="chevron-forward" size={16} color={colors.gold} />
              </Pressable>
            </>
          ) : (
            <>
              <Text style={styles.empty}>
                {lit?.is_sunday
                  ? "The Lord's Day — a day of rest. Sanctus will suggest gentle movement only."
                  : "No workout planned yet. Let Sanctus shape one to the season."}
              </Text>
              <Pressable
                testID="generate-today-workout-button"
                onPress={generateWorkout}
                disabled={genWorkout}
                style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
              >
                {genWorkout ? (
                  <ActivityIndicator color={colors.gold} />
                ) : (
                  <>
                    <Ionicons name="sparkles-outline" size={16} color={colors.gold} />
                    <Text style={styles.primaryBtnText}>Generate Workout</Text>
                  </>
                )}
              </Pressable>
            </>
          )}
        </View>

        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  scroll: { paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: spacing.xl },
  loadingWrap: { flex: 1, alignItems: "center", justifyContent: "center" },
  greeting: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 16,
    color: colors.textSecondary,
    marginBottom: 4,
  },
  date: {
    fontFamily: fonts.headingBold,
    fontSize: 32,
    color: colors.textPrimary,
    lineHeight: 38,
  },
  badgeRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.sm },
  feast: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.liturgical.red,
    marginTop: spacing.sm,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginTop: spacing.md,
    ...shadow.card,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  cardHeaderText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.5,
    color: colors.gold,
  },
  devotionTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 22,
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  devotionText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 16,
    color: colors.textSecondary,
    lineHeight: 26,
    fontStyle: "italic",
  },
  mealName: {
    fontFamily: fonts.headingSemi,
    fontSize: 22,
    color: colors.textPrimary,
    marginBottom: 4,
  },
  mealDesc: {
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textSecondary,
    lineHeight: 22,
  },
  reflection: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 14,
    color: colors.liturgical.purple,
    marginTop: spacing.md,
    lineHeight: 22,
  },
  empty: {
    fontFamily: fonts.bodyRegular,
    fontStyle: "italic",
    fontSize: 15,
    color: colors.textSecondary,
    lineHeight: 22,
    marginBottom: spacing.md,
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
    marginTop: spacing.xs,
  },
  primaryBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 15,
    letterSpacing: 0.6,
  },
  linkBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: spacing.md,
  },
  linkBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 14,
  },
  pressed: { opacity: 0.7 },
});

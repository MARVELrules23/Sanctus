import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
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

import { api, DayDoc, JournalEntry, LiturgicalDay, MealPlan, Readings, WorkoutPlan } from "@/src/api";
import { useAuth } from "@/src/auth-context";
import DailyPracticeCard from "@/src/components/DailyPracticeCard";
import CatechismCard from "@/src/components/CatechismCard";
import SaintOfTheDayCard from "@/src/components/SaintOfTheDayCard";
import ChallengeHomeCard from "@/src/components/ChallengeHomeCard";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { formatLongFromISO, parseISO, todayISO } from "@/src/date-utils";

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
  const d = parseISO(dateStr);
  return DEVOTIONS[d.getDate() % DEVOTIONS.length];
}

export default function TodayScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const [date] = useState(() => todayISO());
  const [lit, setLit] = useState<LiturgicalDay | null>(null);
  const [meal, setMeal] = useState<DayDoc<MealPlan> | null>(null);
  const [workout, setWorkout] = useState<DayDoc<WorkoutPlan> | null>(null);
  const [readings, setReadings] = useState<Readings | null>(null);
  const [journals, setJournals] = useState<JournalEntry[]>([]);
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
    // Readings + journal are slower / non-critical — load in background.
    api<Readings>(`/readings?date=${date}`).then(setReadings).catch(() => undefined);
    api<{ items: JournalEntry[] }>(`/journal?limit=3`).then((r) => setJournals(r.items || [])).catch(() => undefined);
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
  const longDate = formatLongFromISO(date);
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

        {/* Quick actions */}
        <View style={styles.quickRow} testID="quick-actions-row">
          <QuickTile
            testID="quick-rosary"
            icon="flower-outline"
            label="Prayer"
            onPress={() => router.push("/prayer")}
          />
          <QuickTile
            testID="quick-journal"
            icon="create-outline"
            label="Journal"
            onPress={() => router.push("/journal-list")}
          />
          <QuickTile
            testID="quick-grocery"
            icon="cart-outline"
            label="Grocery"
            onPress={() => router.push("/grocery")}
          />
        </View>
        <View style={styles.quickRow}>
          <QuickTile
            testID="quick-bible"
            icon="book-outline"
            label="Bible"
            onPress={() => router.push("/bible")}
          />
          <QuickTile
            testID="quick-calendar"
            icon="calendar-outline"
            label="Calendar"
            onPress={() => router.push("/(tabs)/calendar")}
          />
          <QuickTile
            testID="quick-churches"
            icon="home-outline"
            label="Churches"
            onPress={() => router.push("/churches")}
          />
        </View>
        <View style={styles.quickRow}>
          <QuickTile
            testID="quick-examen"
            icon="sunny-outline"
            label="Examen"
            onPress={() => router.push({ pathname: "/journal", params: { date, mode: "examen" } })}
          />
          <QuickTile
            testID="quick-selfdefense"
            icon="shield-outline"
            label="Self-Defense"
            onPress={() => router.push("/self-defense")}
          />
          <QuickTile
            testID="quick-charities"
            icon="heart-circle-outline"
            label="Charities"
            onPress={() => router.push("/charities")}
          />
        </View>

        {/* Mass Readings */}
        <Pressable
          testID="readings-card"
          onPress={() => router.push({ pathname: "/readings", params: { date } })}
          style={({ pressed }) => [styles.card, pressed && styles.pressed]}
        >
          <View style={styles.cardHeader}>
            <Ionicons name="bookmark-outline" size={18} color={colors.gold} />
            <Text style={styles.cardHeaderText}>MASS READINGS</Text>
            <View style={{ flex: 1 }} />
            <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
          </View>
          {readings ? (
            <>
              <Text style={styles.mealName}>
                {readings.liturgical_title || lit?.feast || lit?.season}
              </Text>
              {readings.gospel ? (
                <View style={styles.readingRow}>
                  <Text style={styles.readingLabel}>Gospel</Text>
                  <Text style={styles.readingCite}>{readings.gospel}</Text>
                </View>
              ) : null}
              {readings.first_reading ? (
                <View style={styles.readingRow}>
                  <Text style={styles.readingLabel}>1st</Text>
                  <Text style={styles.readingCite}>{readings.first_reading}</Text>
                </View>
              ) : null}
              {readings.psalm ? (
                <View style={styles.readingRow}>
                  <Text style={styles.readingLabel}>Psalm</Text>
                  <Text style={styles.readingCite}>{readings.psalm}</Text>
                </View>
              ) : null}
            </>
          ) : (
            <Text style={styles.empty}>Loading today&apos;s Mass readings…</Text>
          )}
        </Pressable>

        {/* Today's practice */}
        <DailyPracticeCard date={date} />

        {/* Liturgical Challenge — only shown when enrolled AND today is within window */}
        <ChallengeHomeCard date={date} />

        {/* Saint / Blessed / Venerable of the Day */}
        <SaintOfTheDayCard date={date} />

        {/* Catechism in 90 seconds */}
        <CatechismCard date={date} />

        {/* Journal preview */}
        <View style={styles.card} testID="journal-preview-card">
          <View style={styles.cardHeader}>
            <Ionicons name="create-outline" size={18} color={colors.gold} />
            <Text style={styles.cardHeaderText}>JOURNAL</Text>
            <View style={{ flex: 1 }} />
            <Pressable
              testID="journal-new-button"
              onPress={() => router.push({ pathname: "/journal", params: { date } })}
              hitSlop={8}
            >
              <Ionicons name="add" size={22} color={colors.gold} />
            </Pressable>
          </View>
          {journals.length === 0 ? (
            <>
              <Text style={styles.empty}>
                Where did you meet the Lord today? A line is enough.
              </Text>
              <Pressable
                testID="journal-empty-add"
                onPress={() => router.push({ pathname: "/journal", params: { date } })}
                style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
              >
                <Ionicons name="add" size={16} color={colors.gold} />
                <Text style={styles.primaryBtnText}>Write today&apos;s entry</Text>
              </Pressable>
            </>
          ) : (
            <>
              {journals.slice(0, 2).map((j) => (
                <Pressable
                  key={j.entry_id}
                  testID={`journal-preview-${j.entry_id}`}
                  onPress={() => router.push({ pathname: "/journal", params: { entry: j.entry_id } })}
                  style={({ pressed }) => [styles.journalRow, pressed && styles.pressed]}
                >
                  <View style={{ flex: 1 }}>
                    {j.title ? (
                      <Text style={styles.journalTitle} numberOfLines={1}>{j.title}</Text>
                    ) : null}
                    <Text style={styles.journalBody} numberOfLines={2}>
                      {j.body}
                    </Text>
                  </View>
                  <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
                </Pressable>
              ))}
              <Pressable
                testID="view-journal-button"
                onPress={() => router.push("/journal-list")}
                style={({ pressed }) => [styles.linkBtn, pressed && styles.pressed]}
              >
                <Text style={styles.linkBtnText}>View all entries</Text>
                <Ionicons name="chevron-forward" size={16} color={colors.gold} />
              </Pressable>
            </>
          )}
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

function QuickTile({
  testID,
  icon,
  label,
  onPress,
}: {
  testID: string;
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable testID={testID} onPress={onPress} style={({ pressed }) => [styles.tile, pressed && styles.pressed]}>
      <Ionicons name={icon} size={22} color={colors.gold} />
      <Text style={styles.tileLabel}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  scroll: { paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: spacing.xl },
  loadingWrap: { flex: 1, alignItems: "center", justifyContent: "center" },  greeting: {
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
  quickRow: {
    flexDirection: "row",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  tile: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    gap: 6,
    ...shadow.card,
  },
  tileLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.textPrimary,
    letterSpacing: 0.6,
  },
  readingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginTop: 6,
  },
  readingLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1.2,
    color: colors.textMuted,
    width: 46,
  },
  readingCite: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textPrimary,
    flex: 1,
  },
  journalRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  journalTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 16,
    color: colors.textPrimary,
  },
  journalBody: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 20,
    marginTop: 2,
  },
  pressed: { opacity: 0.7 },
});

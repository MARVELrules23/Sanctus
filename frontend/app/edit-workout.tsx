import React, { useCallback, useEffect, useState } from "react";
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
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { api, DayDoc, ExerciseItem, LiturgicalDay, WorkoutPlan } from "@/src/api";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { formatLong, parseISO, todayISO } from "@/src/date-utils";

type Draft = {
  title: string;
  focus: string;
  duration_minutes: number;
  exercises: ExerciseItem[];
  opening_prayer: string;
  closing_prayer: string;
  reflection: string;
};

const empty = (): Draft => ({
  title: "",
  focus: "",
  duration_minutes: 30,
  exercises: [],
  opening_prayer: "",
  closing_prayer: "",
  reflection: "",
});

export default function EditWorkoutScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ date?: string }>();
  const date = typeof params.date === "string" ? params.date : todayISO();
  const [lit, setLit] = useState<LiturgicalDay | null>(null);
  const [draft, setDraft] = useState<Draft>(empty());
  const [loading, setLoading] = useState(true);
  const [suggesting, setSuggesting] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const [l, existing] = await Promise.all([
      api<LiturgicalDay>(`/liturgical/day?date=${date}`),
      api<DayDoc<WorkoutPlan> | Record<string, never>>(`/workouts?date=${date}`),
    ]);
    setLit(l);
    if ("plan" in existing) {
      const p = (existing as DayDoc<WorkoutPlan>).plan;
      setDraft({
        title: p.title || "",
        focus: p.focus || "",
        duration_minutes: p.duration_minutes || 30,
        exercises: p.exercises || [],
        opening_prayer: p.opening_prayer || "",
        closing_prayer: p.closing_prayer || "",
        reflection: p.reflection || "",
      });
    }
  }, [date]);

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

  const suggest = async () => {
    setSuggesting(true);
    try {
      const item = await api<Draft>("/workouts/suggest", {
        method: "POST",
        body: { date, focus: draft.focus || null, hint: draft.title || null },
      });
      setDraft({
        title: item.title || "",
        focus: item.focus || "",
        duration_minutes: item.duration_minutes || 30,
        exercises: item.exercises || [],
        opening_prayer: item.opening_prayer || "",
        closing_prayer: item.closing_prayer || "",
        reflection: draft.reflection,
      });
    } catch (e) {
      console.warn("suggest failed", e);
    } finally {
      setSuggesting(false);
    }
  };

  const save = async () => {
    setSaving(true);
    try {
      await api<DayDoc<WorkoutPlan>>("/workouts/save", {
        method: "POST",
        body: { date, ...draft },
      });
      router.back();
    } catch (e) {
      console.warn("save failed", e);
    } finally {
      setSaving(false);
    }
  };

  const addExercise = () =>
    setDraft({ ...draft, exercises: [...draft.exercises, { name: "", sets: "", notes: "" }] });
  const updateExercise = (i: number, patch: Partial<ExerciseItem>) =>
    setDraft({
      ...draft,
      exercises: draft.exercises.map((e, idx) => (idx === i ? { ...e, ...patch } : e)),
    });
  const removeExercise = (i: number) =>
    setDraft({ ...draft, exercises: draft.exercises.filter((_, idx) => idx !== i) });

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="edit-workout-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.headerRow}>
        <Pressable testID="edit-workout-close" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="close" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Plan Workout</Text>
        <Pressable
          testID="edit-workout-save"
          onPress={save}
          disabled={saving || loading}
          style={({ pressed }) => pressed && styles.pressed}
        >
          {saving ? <ActivityIndicator color={colors.gold} /> : <Text style={styles.saveText}>Save</Text>}
        </Pressable>
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={20}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <Text style={styles.date}>{formatLong(parseISO(date))}</Text>
          {lit && (
            <View style={styles.badgeRow}>
              <LiturgicalBadge color={lit.color} label={lit.season} />
              {lit.is_sunday && <LiturgicalBadge color="gold" label="Day of Rest" />}
            </View>
          )}

          {loading ? (
            <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
          ) : (
            <>
              <Pressable
                testID="suggest-workout-outline"
                onPress={suggest}
                disabled={suggesting}
                style={({ pressed }) => [styles.suggestOutline, pressed && styles.pressed]}
              >
                {suggesting ? (
                  <ActivityIndicator color={colors.gold} />
                ) : (
                  <>
                    <Ionicons name="sparkles-outline" size={16} color={colors.gold} />
                    <Text style={styles.suggestOutlineText}>AI suggest full workout</Text>
                  </>
                )}
              </Pressable>

              <Text style={styles.fieldLabel}>Title</Text>
              <TextInput
                testID="workout-title"
                style={styles.input}
                placeholder="e.g. Lenten Penitential Strength"
                placeholderTextColor={colors.textMuted}
                value={draft.title}
                onChangeText={(t) => setDraft({ ...draft, title: t })}
              />
              <Text style={styles.fieldLabel}>Focus</Text>
              <TextInput
                testID="workout-focus"
                style={styles.input}
                placeholder="e.g. Strength, mobility, cardio"
                placeholderTextColor={colors.textMuted}
                value={draft.focus}
                onChangeText={(t) => setDraft({ ...draft, focus: t })}
              />
              <Text style={styles.fieldLabel}>Duration (minutes)</Text>
              <TextInput
                testID="workout-duration"
                style={[styles.input, { width: 120 }]}
                keyboardType="number-pad"
                placeholder="30"
                placeholderTextColor={colors.textMuted}
                value={String(draft.duration_minutes || "")}
                onChangeText={(t) => setDraft({ ...draft, duration_minutes: parseInt(t || "0", 10) || 0 })}
              />

              <Text style={styles.fieldLabel}>Opening Prayer</Text>
              <TextInput
                testID="workout-opening-prayer"
                style={[styles.input, styles.multi]}
                multiline
                placeholder="A short prayer intention…"
                placeholderTextColor={colors.textMuted}
                value={draft.opening_prayer}
                onChangeText={(t) => setDraft({ ...draft, opening_prayer: t })}
              />

              <View style={styles.sectionHeader}>
                <Text style={styles.section}>Exercises</Text>
                <Pressable
                  testID="add-exercise"
                  onPress={addExercise}
                  style={({ pressed }) => [styles.smallBtn, pressed && styles.pressed]}
                >
                  <Ionicons name="add" size={16} color={colors.gold} />
                  <Text style={styles.smallBtnText}>Add</Text>
                </Pressable>
              </View>
              {draft.exercises.length === 0 ? (
                <Text style={styles.emptyHint}>No exercises yet — add one or tap “AI suggest”.</Text>
              ) : (
                draft.exercises.map((ex, i) => (
                  <View key={i} style={styles.exCard} testID={`exercise-edit-${i}`}>
                    <View style={styles.exCardHeader}>
                      <Text style={styles.exNum}>#{i + 1}</Text>
                      <Pressable
                        testID={`exercise-remove-${i}`}
                        onPress={() => removeExercise(i)}
                        hitSlop={10}
                      >
                        <Ionicons name="trash-outline" size={16} color={colors.liturgical.red} />
                      </Pressable>
                    </View>
                    <TextInput
                      testID={`exercise-${i}-name`}
                      style={styles.input}
                      placeholder="Movement (e.g. Push-ups)"
                      placeholderTextColor={colors.textMuted}
                      value={ex.name}
                      onChangeText={(t) => updateExercise(i, { name: t })}
                    />
                    <TextInput
                      testID={`exercise-${i}-sets`}
                      style={styles.input}
                      placeholder="Sets / reps (e.g. 3 × 12)"
                      placeholderTextColor={colors.textMuted}
                      value={ex.sets}
                      onChangeText={(t) => updateExercise(i, { sets: t })}
                    />
                    <TextInput
                      testID={`exercise-${i}-notes`}
                      style={[styles.input, styles.multi]}
                      multiline
                      placeholder="Notes / form cues"
                      placeholderTextColor={colors.textMuted}
                      value={ex.notes}
                      onChangeText={(t) => updateExercise(i, { notes: t })}
                    />
                  </View>
                ))
              )}

              <Text style={styles.fieldLabel}>Closing Prayer</Text>
              <TextInput
                testID="workout-closing-prayer"
                style={[styles.input, styles.multi]}
                multiline
                placeholder="A closing prayer of thanksgiving…"
                placeholderTextColor={colors.textMuted}
                value={draft.closing_prayer}
                onChangeText={(t) => setDraft({ ...draft, closing_prayer: t })}
              />

              <Text style={styles.fieldLabel}>Reflection (optional)</Text>
              <TextInput
                testID="workout-reflection"
                style={[styles.input, styles.multi]}
                multiline
                placeholder="Tie this discipline to the liturgical season…"
                placeholderTextColor={colors.textMuted}
                value={draft.reflection}
                onChangeText={(t) => setDraft({ ...draft, reflection: t })}
              />
            </>
          )}
          <View style={{ height: spacing.xl }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 22, color: colors.textPrimary },
  saveText: { fontFamily: fonts.uiSemi, fontSize: 16, color: colors.gold },
  scroll: { padding: spacing.lg },
  date: { fontFamily: fonts.headingBold, fontSize: 26, color: colors.textPrimary },
  badgeRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.sm, marginBottom: spacing.md },
  suggestOutline: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    paddingVertical: 12,
    borderRadius: radius.md,
    backgroundColor: colors.primary,
    marginTop: spacing.sm,
  },
  suggestOutlineText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 14 },
  fieldLabel: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textMuted, letterSpacing: 0.8, marginTop: spacing.md },
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textPrimary,
    marginTop: spacing.xs,
  },
  multi: { minHeight: 64, textAlignVertical: "top" },
  sectionHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: spacing.lg },
  section: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.textPrimary },
  smallBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: colors.primary,
    borderRadius: radius.round,
  },
  smallBtnText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold },
  exCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginTop: spacing.sm,
    ...shadow.card,
  },
  exCardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  exNum: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 12, letterSpacing: 1 },
  emptyHint: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textMuted,
    fontSize: 14,
    marginTop: spacing.sm,
  },
  pressed: { opacity: 0.7 },
});

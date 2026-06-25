import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";

import { api, WeightLog, WellnessProfile, WellnessSuggestion } from "@/src/api";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { todayISO } from "@/src/date-utils";

const GOAL_OPTIONS: { value: "lose" | "maintain" | "gain"; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { value: "lose", label: "Lose", icon: "trending-down-outline" },
  { value: "maintain", label: "Maintain", icon: "remove-outline" },
  { value: "gain", label: "Gain", icon: "trending-up-outline" },
];

const ACTIVITY_OPTIONS: { value: "sedentary" | "light" | "moderate" | "very_active"; label: string }[] = [
  { value: "sedentary", label: "Sedentary" },
  { value: "light", label: "Light" },
  { value: "moderate", label: "Moderate" },
  { value: "very_active", label: "Very active" },
];

const EMPTY_PROFILE: WellnessProfile = {
  weight_kg: null,
  height_cm: null,
  target_weight_kg: null,
  target_date: null,
  goal_type: null,
  activity_level: null,
  weekly_rate_kg: null,
  units: "metric",
  notes: null,
};

function toNum(v: string): number | null {
  const t = v.trim();
  if (!t) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

export default function WellnessScreen() {
  const [profile, setProfile] = useState<WellnessProfile>(EMPTY_PROFILE);
  const [logs, setLogs] = useState<WeightLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [logging, setLogging] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [brief, setBrief] = useState<WellnessSuggestion | null>(null);

  // form input strings
  const [weight, setWeight] = useState("");
  const [height, setHeight] = useState("");
  const [target, setTarget] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [rate, setRate] = useState("");
  const [notes, setNotes] = useState("");

  // weight log input
  const [logWeight, setLogWeight] = useState("");
  const [logNote, setLogNote] = useState("");

  const applyProfile = useCallback((p: WellnessProfile) => {
    setProfile(p);
    setWeight(p.weight_kg != null ? String(p.weight_kg) : "");
    setHeight(p.height_cm != null ? String(p.height_cm) : "");
    setTarget(p.target_weight_kg != null ? String(p.target_weight_kg) : "");
    setTargetDate(p.target_date ?? "");
    setRate(p.weekly_rate_kg != null ? String(p.weekly_rate_kg) : "");
    setNotes(p.notes ?? "");
  }, []);

  const load = useCallback(async () => {
    const [p, l] = await Promise.all([
      api<WellnessProfile>("/wellness/profile"),
      api<{ items: WeightLog[] }>("/wellness/log?limit=60"),
    ]);
    applyProfile(p);
    setLogs(l.items || []);
  }, [applyProfile]);

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

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await load();
    } finally {
      setRefreshing(false);
    }
  };

  const save = async () => {
    setSaving(true);
    try {
      const payload: Partial<WellnessProfile> = {
        weight_kg: toNum(weight),
        height_cm: toNum(height),
        target_weight_kg: toNum(target),
        target_date: targetDate.trim() || null,
        goal_type: profile.goal_type,
        activity_level: profile.activity_level,
        weekly_rate_kg: toNum(rate),
        units: "metric",
        notes: notes.trim() || null,
      };
      // Remove nulls so backend keeps existing values where blank.
      const body: Record<string, unknown> = {};
      Object.entries(payload).forEach(([k, v]) => {
        if (v !== null) body[k] = v;
      });
      const p = await api<WellnessProfile>("/wellness/profile", { method: "PUT", body });
      applyProfile(p);
      Alert.alert("Saved", "Your wellness profile has been updated.");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "";
      Alert.alert("Save failed", msg || "Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const addLog = async () => {
    const w = toNum(logWeight);
    if (!w || w <= 0) {
      Alert.alert("Enter a weight", "Please enter a positive number.");
      return;
    }
    setLogging(true);
    try {
      await api("/wellness/log", {
        method: "POST",
        body: { date: todayISO(), weight_kg: w, note: logNote.trim() || null },
      });
      setLogWeight("");
      setLogNote("");
      await load();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "";
      Alert.alert("Log failed", msg || "Please try again.");
    } finally {
      setLogging(false);
    }
  };

  const removeLog = async (logId: string) => {
    Alert.alert("Delete weigh-in?", "", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await api(`/wellness/log/${logId}`, { method: "DELETE" });
            setLogs((arr) => arr.filter((l) => l.log_id !== logId));
          } catch (e) {
            console.warn("delete log failed", e);
          }
        },
      },
    ]);
  };

  const askBrief = async () => {
    if (!profile.goal_type) {
      Alert.alert("Set a goal first", "Choose lose, maintain, or gain and save.");
      return;
    }
    setSuggesting(true);
    try {
      const res = await api<WellnessSuggestion>("/wellness/suggest", { method: "POST" });
      setBrief(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "";
      Alert.alert("Brief failed", msg || "Please try again later.");
    } finally {
      setSuggesting(false);
    }
  };

  // Sparkline: last 30 logs by date asc
  const sparkline = useMemo(() => {
    const sorted = [...logs].sort((a, b) => a.date.localeCompare(b.date)).slice(-30);
    if (sorted.length < 2) return null;
    const vals = sorted.map((l) => l.weight_kg);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const span = max - min || 1;
    return { sorted, min, max, span };
  }, [logs]);

  if (loading) {
    return (
      <SafeAreaView style={styles.safe} edges={["top"]} testID="wellness-screen">
        <View style={styles.loadingWrap}>
          <ActivityIndicator color={colors.gold} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="wellness-screen">
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />
          }
        >
          <Text style={styles.title}>Wellness</Text>
          <Text style={styles.sub}>
            The body is a temple of the Holy Spirit — caring for it is itself an act of prayer.
          </Text>

          <Ornament />

          {/* AI Brief */}
          <View style={styles.card} testID="wellness-brief-card">
            <View style={styles.cardHeader}>
              <Ionicons name="sparkles-outline" size={18} color={colors.gold} />
              <Text style={styles.cardHeaderText}>AI COACHING BRIEF</Text>
            </View>
            {brief ? (
              <>
                <Text style={styles.briefHeadline}>{brief.calorie_target.toLocaleString()} kcal / day</Text>
                <Text style={styles.briefSub}>{brief.macro_focus}</Text>
                {brief.meal_focus.length > 0 && (
                  <View style={styles.section}>
                    <Text style={styles.sectionLabel}>Meal focus</Text>
                    {brief.meal_focus.map((m, i) => (
                      <Text key={i} style={styles.bullet}>•  {m}</Text>
                    ))}
                  </View>
                )}
                {brief.workout_focus.length > 0 && (
                  <View style={styles.section}>
                    <Text style={styles.sectionLabel}>Workout focus</Text>
                    {brief.workout_focus.map((m, i) => (
                      <Text key={i} style={styles.bullet}>•  {m}</Text>
                    ))}
                  </View>
                )}
                {brief.weekly_split ? (
                  <View style={styles.section}>
                    <Text style={styles.sectionLabel}>Weekly split</Text>
                    <Text style={styles.bullet}>{brief.weekly_split}</Text>
                  </View>
                ) : null}
                {brief.encouragement ? (
                  <Text style={styles.encouragement}>“{brief.encouragement}”</Text>
                ) : null}
              </>
            ) : (
              <Text style={styles.empty}>
                Save your goal below and tap Generate to receive a calorie target, meal & workout focus, and an encouragement rooted in faith.
              </Text>
            )}
            <Pressable
              testID="wellness-brief-btn"
              onPress={askBrief}
              disabled={suggesting}
              style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
            >
              {suggesting ? (
                <ActivityIndicator color={colors.gold} />
              ) : (
                <>
                  <Ionicons name="sparkles-outline" size={16} color={colors.gold} />
                  <Text style={styles.primaryBtnText}>{brief ? "Refresh brief" : "Generate brief"}</Text>
                </>
              )}
            </Pressable>
          </View>

          {/* Weight log */}
          <View style={styles.card} testID="wellness-log-card">
            <View style={styles.cardHeader}>
              <Ionicons name="scale-outline" size={18} color={colors.gold} />
              <Text style={styles.cardHeaderText}>WEIGH-IN</Text>
            </View>
            <View style={styles.logRow}>
              <TextInput
                testID="wellness-log-weight"
                style={[styles.input, { flex: 1 }]}
                value={logWeight}
                onChangeText={setLogWeight}
                placeholder="kg"
                placeholderTextColor={colors.textMuted}
                keyboardType="decimal-pad"
              />
              <TextInput
                testID="wellness-log-note"
                style={[styles.input, { flex: 2 }]}
                value={logNote}
                onChangeText={setLogNote}
                placeholder="Note (optional)"
                placeholderTextColor={colors.textMuted}
              />
              <Pressable
                testID="wellness-log-add"
                onPress={addLog}
                disabled={logging}
                style={({ pressed }) => [styles.iconBtn, pressed && styles.pressed]}
              >
                {logging ? (
                  <ActivityIndicator color={colors.gold} />
                ) : (
                  <Ionicons name="add" size={22} color={colors.gold} />
                )}
              </Pressable>
            </View>

            {sparkline ? (
              <View style={styles.sparkRow}>
                {sparkline.sorted.map((l, i) => {
                  const pct = (l.weight_kg - sparkline.min) / sparkline.span;
                  const h = 6 + pct * 38;
                  return <View key={i} style={[styles.sparkBar, { height: h }]} />;
                })}
              </View>
            ) : null}

            {logs.length === 0 ? (
              <Text style={styles.empty}>No weigh-ins yet. Log one above to start tracking.</Text>
            ) : (
              logs.slice(0, 10).map((l) => (
                <View key={l.log_id} style={styles.logItem} testID={`log-${l.log_id}`}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.logDate}>{l.date}</Text>
                    {l.note ? <Text style={styles.logNote}>{l.note}</Text> : null}
                  </View>
                  <Text style={styles.logWeight}>{l.weight_kg.toFixed(1)} kg</Text>
                  <Pressable
                    testID={`log-del-${l.log_id}`}
                    onPress={() => removeLog(l.log_id)}
                    hitSlop={8}
                    style={({ pressed }) => pressed && styles.pressed}
                  >
                    <Ionicons name="trash-outline" size={16} color={colors.textMuted} />
                  </Pressable>
                </View>
              ))
            )}
          </View>

          {/* Profile */}
          <View style={styles.card} testID="wellness-profile-card">
            <View style={styles.cardHeader}>
              <Ionicons name="person-circle-outline" size={18} color={colors.gold} />
              <Text style={styles.cardHeaderText}>YOUR PROFILE</Text>
            </View>

            <Text style={styles.fieldLabel}>Goal</Text>
            <View style={styles.chipRow}>
              {GOAL_OPTIONS.map((g) => {
                const active = profile.goal_type === g.value;
                return (
                  <Pressable
                    key={g.value}
                    testID={`goal-${g.value}`}
                    onPress={() => setProfile((p) => ({ ...p, goal_type: g.value }))}
                    style={[styles.chip, active && styles.chipActive]}
                  >
                    <Ionicons name={g.icon} size={14} color={active ? colors.gold : colors.textSecondary} />
                    <Text style={[styles.chipText, active && styles.chipTextActive]}>{g.label}</Text>
                  </Pressable>
                );
              })}
            </View>

            <Text style={styles.fieldLabel}>Activity level</Text>
            <View style={styles.chipRow}>
              {ACTIVITY_OPTIONS.map((a) => {
                const active = profile.activity_level === a.value;
                return (
                  <Pressable
                    key={a.value}
                    testID={`activity-${a.value}`}
                    onPress={() => setProfile((p) => ({ ...p, activity_level: a.value }))}
                    style={[styles.chip, active && styles.chipActive]}
                  >
                    <Text style={[styles.chipText, active && styles.chipTextActive]}>{a.label}</Text>
                  </Pressable>
                );
              })}
            </View>

            <View style={styles.twoCol}>
              <View style={styles.col}>
                <Text style={styles.fieldLabel}>Weight (kg)</Text>
                <TextInput
                  testID="profile-weight"
                  style={styles.input}
                  value={weight}
                  onChangeText={setWeight}
                  keyboardType="decimal-pad"
                  placeholder="e.g. 75.2"
                  placeholderTextColor={colors.textMuted}
                />
              </View>
              <View style={styles.col}>
                <Text style={styles.fieldLabel}>Height (cm)</Text>
                <TextInput
                  testID="profile-height"
                  style={styles.input}
                  value={height}
                  onChangeText={setHeight}
                  keyboardType="decimal-pad"
                  placeholder="e.g. 178"
                  placeholderTextColor={colors.textMuted}
                />
              </View>
            </View>

            <View style={styles.twoCol}>
              <View style={styles.col}>
                <Text style={styles.fieldLabel}>Target weight (kg)</Text>
                <TextInput
                  testID="profile-target"
                  style={styles.input}
                  value={target}
                  onChangeText={setTarget}
                  keyboardType="decimal-pad"
                  placeholder="e.g. 70"
                  placeholderTextColor={colors.textMuted}
                />
              </View>
              <View style={styles.col}>
                <Text style={styles.fieldLabel}>By date</Text>
                <TextInput
                  testID="profile-target-date"
                  style={styles.input}
                  value={targetDate}
                  onChangeText={setTargetDate}
                  placeholder="YYYY-MM-DD"
                  placeholderTextColor={colors.textMuted}
                  autoCapitalize="none"
                />
              </View>
            </View>

            <Text style={styles.fieldLabel}>Weekly rate (kg)</Text>
            <TextInput
              testID="profile-rate"
              style={styles.input}
              value={rate}
              onChangeText={setRate}
              keyboardType="decimal-pad"
              placeholder="e.g. 0.5"
              placeholderTextColor={colors.textMuted}
            />

            <Text style={styles.fieldLabel}>Notes</Text>
            <TextInput
              testID="profile-notes"
              style={[styles.input, styles.notesInput]}
              value={notes}
              onChangeText={setNotes}
              multiline
              placeholder="Anything else for the coach to know"
              placeholderTextColor={colors.textMuted}
            />

            <Pressable
              testID="wellness-save"
              onPress={save}
              disabled={saving}
              style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
            >
              {saving ? (
                <ActivityIndicator color={colors.gold} />
              ) : (
                <Text style={styles.primaryBtnText}>Save profile</Text>
              )}
            </Pressable>
          </View>

          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  scroll: { paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: spacing.xl },
  loadingWrap: { flex: 1, alignItems: "center", justifyContent: "center" },
  title: { fontFamily: fonts.headingBold, fontSize: 32, color: colors.textPrimary },
  sub: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textSecondary,
    fontSize: 14,
    marginTop: 4,
    lineHeight: 22,
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
  cardHeader: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.sm },
  cardHeaderText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.5,
    color: colors.gold,
  },
  fieldLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.2,
    color: colors.gold,
    marginTop: spacing.md,
    marginBottom: 4,
  },
  input: {
    backgroundColor: colors.background,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.sm,
    paddingHorizontal: 12,
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textPrimary,
  },
  notesInput: {
    minHeight: 70,
    textAlignVertical: "top",
  },
  twoCol: { flexDirection: "row", gap: spacing.sm },
  col: { flex: 1 },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary },
  chipTextActive: { color: colors.gold },
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
  primaryBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 15,
    letterSpacing: 0.6,
  },
  briefHeadline: { fontFamily: fonts.headingBold, fontSize: 28, color: colors.textPrimary },
  briefSub: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, marginTop: 2 },
  section: { marginTop: spacing.md },
  sectionLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.2,
    color: colors.textMuted,
    marginBottom: 4,
  },
  bullet: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary, lineHeight: 22 },
  encouragement: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.liturgical.purple,
    fontSize: 14,
    marginTop: spacing.md,
    lineHeight: 22,
  },
  empty: {
    fontFamily: fonts.bodyRegular,
    fontStyle: "italic",
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
  },
  logRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  iconBtn: {
    width: 40,
    height: 40,
    borderRadius: radius.md,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  sparkRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 2,
    height: 50,
    marginTop: spacing.md,
  },
  sparkBar: {
    flex: 1,
    backgroundColor: colors.gold,
    borderRadius: 2,
    opacity: 0.85,
  },
  logItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  logDate: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textPrimary },
  logNote: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textMuted, marginTop: 2 },
  logWeight: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  pressed: { opacity: 0.7 },
});

/**
 * Virtus — plan detail.
 *
 * A virtue plan with its do/refrain goals. Goals are checked off PER DAY:
 * a horizontal calendar strip spans the plan's days, and the selected day
 * shows its checklist plus a journal box for the user to examine their
 * thoughts. Progress and journals are stored per date on the plan.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
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

import {
  checkinVirtueGoal,
  deleteVirtuePlan,
  getVirtuePlan,
  saveVirtueJournal,
  VirtuePlan,
} from "@/src/api";
import { confirm } from "@/src/utils/confirm";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function addDaysISO(iso: string, n: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() + n);
  return dt.toISOString().slice(0, 10);
}
function datesBetween(start: string, end: string): string[] {
  const out: string[] = [];
  let cur = start;
  for (let i = 0; i < 400 && cur <= end; i++) {
    out.push(cur);
    cur = addDaysISO(cur, 1);
  }
  return out;
}
function weekdayShort(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return WEEKDAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
}
function dayNum(iso: string): number {
  return Number(iso.split("-")[2]);
}
function clampDate(target: string, lo: string, hi: string): string {
  if (target < lo) return lo;
  if (target > hi) return hi;
  return target;
}

export default function VirtuePlanScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [plan, setPlan] = useState<VirtuePlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [journalText, setJournalText] = useState("");
  const [journalDirty, setJournalDirty] = useState(false);
  const [savingJournal, setSavingJournal] = useState(false);
  const stripRef = useRef<ScrollView | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const p = await getVirtuePlan(id);
      setPlan(p);
      setSelectedDate((cur) => cur ?? clampDate(p.today, p.start_date, p.end_date));
    } catch (e: any) {
      setError(e?.message || "Could not load this plan.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  // When the selected day changes (or plan reloads), sync the journal box.
  useEffect(() => {
    if (!plan || !selectedDate) return;
    setJournalText(plan.journal?.[selectedDate] || "");
    setJournalDirty(false);
  }, [selectedDate, plan]);

  const days = useMemo(
    () => (plan ? datesBetween(plan.start_date, plan.end_date) : []),
    [plan],
  );

  const isFuture = !!plan && !!selectedDate && selectedDate > plan.today;

  const toggle = async (goalId: string) => {
    if (!id || !selectedDate || busy || isFuture) return;
    setBusy(goalId);
    try {
      setPlan(await checkinVirtueGoal(id, selectedDate, goalId));
    } catch {
      /* ignore */
    } finally {
      setBusy(null);
    }
  };

  const saveJournal = async () => {
    if (!id || !selectedDate || !journalDirty) return;
    setSavingJournal(true);
    try {
      setPlan(await saveVirtueJournal(id, selectedDate, journalText));
      setJournalDirty(false);
    } catch {
      /* ignore */
    } finally {
      setSavingJournal(false);
    }
  };

  const confirmDelete = async () => {
    if (!id) return;
    const ok = await confirm({
      title: "Delete plan?",
      message: "This virtue plan, its goals, and journal entries will be removed.",
      confirmText: "Delete",
      destructive: true,
    });
    if (!ok) return;
    try {
      await deleteVirtuePlan(id);
      router.back();
    } catch {
      /* ignore */
    }
  };

  const doneSet = useMemo(
    () => new Set(plan && selectedDate ? plan.checkins?.[selectedDate] || [] : []),
    [plan, selectedDate],
  );

  const grouped = useMemo(() => {
    if (!plan) return [] as { virtue: VirtuePlan["virtues"][number]; goals: VirtuePlan["goals"] }[];
    return plan.virtues.map((v) => ({
      virtue: v,
      goals: plan.goals.filter((g) => g.virtue_slug === v.slug),
    }));
  }, [plan]);

  const selectedLabel = useMemo(() => {
    if (!selectedDate) return "";
    const [y, m, d] = selectedDate.split("-").map(Number);
    const dt = new Date(Date.UTC(y, m - 1, d));
    return dt.toLocaleDateString(undefined, {
      weekday: "long", month: "long", day: "numeric", timeZone: "UTC",
    });
  }, [selectedDate]);

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
        <KeyboardAvoidingView
          style={{ flex: 1 }}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
            <View style={styles.summary}>
              <Text style={styles.summaryTitle}>{plan.virtues.map((v) => v.name).join(" · ")}</Text>
              <Text style={styles.summarySub}>
                {plan.start_date} → {plan.end_date} · {plan.days} days
              </Text>
              <View style={styles.statsRow}>
                <View style={styles.statPill}>
                  <Ionicons name="flame-outline" size={13} color={colors.gold} />
                  <Text style={styles.statText}>{plan.days_logged} {plan.days_logged === 1 ? "day" : "days"} logged</Text>
                </View>
                <View style={styles.statPill}>
                  <Ionicons name="checkmark-done-outline" size={13} color={colors.gold} />
                  <Text style={styles.statText}>{doneSet.size}/{plan.total} today</Text>
                </View>
              </View>
              {plan.note ? <Text style={styles.note}>“{plan.note}”</Text> : null}
            </View>

            {/* Calendar day strip */}
            <Text style={styles.sectionLabel}>CALENDAR</Text>
            <ScrollView
              ref={stripRef}
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.strip}
            >
              {days.map((d) => {
                const count = (plan.checkins?.[d] || []).length;
                const ratio = plan.total ? count / plan.total : 0;
                const sel = d === selectedDate;
                const isToday = d === plan.today;
                const future = d > plan.today;
                return (
                  <Pressable
                    key={d}
                    testID={`virtus-day-${d}`}
                    onPress={() => setSelectedDate(d)}
                    style={[styles.dayChip, sel && styles.dayChipSel, future && styles.dayChipFuture]}
                  >
                    <Text style={[styles.dayWk, sel && styles.dayTextSel]}>{weekdayShort(d)}</Text>
                    <Text style={[styles.dayNum, sel && styles.dayTextSel]}>{dayNum(d)}</Text>
                    <View
                      style={[
                        styles.dayDot,
                        ratio >= 1
                          ? { backgroundColor: colors.gold, borderColor: colors.gold }
                          : ratio > 0
                          ? { backgroundColor: "transparent", borderColor: colors.gold }
                          : { backgroundColor: "transparent", borderColor: sel ? "#E8DCB5" : colors.borderSoft },
                      ]}
                    />
                    {isToday ? <View style={styles.todayBar} /> : null}
                  </Pressable>
                );
              })}
            </ScrollView>

            <Text style={styles.selectedDateLabel}>
              {selectedLabel}{isFuture ? "  ·  upcoming" : ""}
            </Text>

            {/* Daily checklist */}
            {grouped.map(({ virtue, goals }) => (
              <View key={virtue.slug} style={[styles.group, { borderTopColor: virtue.accent_color }]}>
                <View style={styles.groupHead}>
                  <Ionicons name={(virtue.icon as keyof typeof Ionicons.glyphMap) || "ellipse-outline"} size={18} color={virtue.accent_color} />
                  <Text style={styles.groupTitle}>{virtue.name}</Text>
                </View>
                {goals.map((g) => {
                  const checked = doneSet.has(g.id);
                  return (
                    <Pressable
                      key={g.id}
                      testID={`virtus-goal-${g.id}`}
                      onPress={() => toggle(g.id)}
                      disabled={isFuture}
                      style={({ pressed }) => [styles.goalRow, pressed && !isFuture && { opacity: 0.8 }, isFuture && { opacity: 0.5 }]}
                    >
                      <View style={[styles.checkbox, checked && { backgroundColor: virtue.accent_color, borderColor: virtue.accent_color }]}>
                        {busy === g.id ? (
                          <ActivityIndicator size="small" color={checked ? colors.gold : virtue.accent_color} />
                        ) : checked ? (
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
                        <Text style={[styles.goalText, checked && styles.goalDone]}>{g.text}</Text>
                      </View>
                    </Pressable>
                  );
                })}
              </View>
            ))}

            {/* Journal box */}
            <View style={styles.journalCard}>
              <View style={styles.journalHead}>
                <Ionicons name="create-outline" size={16} color={colors.gold} />
                <Text style={styles.journalTitle}>Examine your thoughts</Text>
              </View>
              <Text style={styles.journalHint}>
                How did you live these virtues today? Where did you struggle or grow?
              </Text>
              <TextInput
                testID="virtus-journal-input"
                value={journalText}
                onChangeText={(t) => { setJournalText(t); setJournalDirty(true); }}
                onBlur={saveJournal}
                placeholder="Write a short reflection for this day…"
                placeholderTextColor={colors.textMuted}
                style={styles.journalInput}
                multiline
                textAlignVertical="top"
              />
              <Pressable
                testID="virtus-journal-save"
                onPress={saveJournal}
                disabled={!journalDirty || savingJournal}
                style={({ pressed }) => [
                  styles.journalSave,
                  (!journalDirty || savingJournal) && styles.journalSaveDisabled,
                  pressed && { opacity: 0.8 },
                ]}
              >
                {savingJournal ? (
                  <ActivityIndicator size="small" color={colors.gold} />
                ) : (
                  <Text style={styles.journalSaveText}>{journalDirty ? "Save reflection" : "Saved"}</Text>
                )}
              </Pressable>
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
  statsRow: { flexDirection: "row", gap: spacing.sm, marginTop: 8 },
  statPill: {
    flexDirection: "row", alignItems: "center", gap: 5,
    backgroundColor: colors.background, borderWidth: 1, borderColor: colors.borderSoft,
    paddingHorizontal: 10, paddingVertical: 5, borderRadius: radius.round,
  },
  statText: { fontFamily: fonts.uiSemi, fontSize: 11.5, color: colors.textSecondary },
  note: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13, color: colors.textSecondary, marginTop: spacing.sm },

  sectionLabel: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 2, color: colors.gold, marginTop: spacing.xs },
  strip: { gap: 8, paddingVertical: 2, paddingRight: spacing.lg },
  dayChip: {
    width: 50, paddingVertical: 8, borderRadius: radius.md, alignItems: "center", gap: 3,
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft,
  },
  dayChipSel: { backgroundColor: colors.primary, borderColor: colors.primary },
  dayChipFuture: { opacity: 0.55 },
  dayWk: { fontFamily: fonts.uiMedium, fontSize: 10, color: colors.textMuted, letterSpacing: 0.5 },
  dayNum: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  dayTextSel: { color: colors.gold },
  dayDot: { width: 8, height: 8, borderRadius: 4, borderWidth: 1.5, marginTop: 2 },
  todayBar: { width: 16, height: 2, borderRadius: 1, backgroundColor: colors.gold, marginTop: 1 },
  selectedDateLabel: { fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary, marginTop: spacing.xs },

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

  journalCard: {
    padding: spacing.lg, borderRadius: radius.lg, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: colors.borderSoft, ...shadow.card, gap: spacing.sm,
  },
  journalHead: { flexDirection: "row", alignItems: "center", gap: 8 },
  journalTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  journalHint: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12, color: colors.textMuted, lineHeight: 18 },
  journalInput: {
    minHeight: 110, borderWidth: 1, borderColor: colors.borderSoft, borderRadius: radius.md,
    backgroundColor: colors.background, padding: spacing.md, fontFamily: fonts.bodyRegular,
    fontSize: 14, lineHeight: 21, color: colors.textPrimary,
  },
  journalSave: {
    alignSelf: "flex-end", paddingHorizontal: spacing.lg, paddingVertical: 10,
    borderRadius: radius.round, backgroundColor: colors.primary, minWidth: 130, alignItems: "center",
  },
  journalSaveDisabled: { backgroundColor: colors.borderSoft },
  journalSaveText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 13 },
});

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text as RNText,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { api } from "@/src/api";
import { todayISO } from "@/src/date-utils";
import { AutoText } from "@/src/auto-text";
import { colors, fonts, radius, spacing } from "@/src/theme";

type Enrollment = { slug: string; start_date: string; end_date: string; completed_days: number[]; status: string; total_days: number };
type JournalEntry = { id: string; slug: string; text: string; created_at: string };
type Detail = {
  slug: string; name: string; patron: string; feast: string; theme: string; intro: string;
  color: string; icon: string; main_prayer: string; day_intentions: string[] | null;
  enrollment: Enrollment | null;
};

function addDays(iso: string, n: number): string {
  const d = new Date(iso + "T00:00:00");
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}
function daysBetween(fromIso: string, toIso: string): number {
  const a = new Date(fromIso + "T00:00:00").getTime();
  const b = new Date(toIso + "T00:00:00").getTime();
  return Math.round((b - a) / 86400000);
}

export default function NovenaDetailScreen() {
  const router = useRouter();
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const [d, setD] = useState<Detail | null>(null);
  const [startDate, setStartDate] = useState(todayISO());
  const [busy, setBusy] = useState(false);
  const [selDay, setSelDay] = useState(1);
  const [reflection, setReflection] = useState<Record<number, string>>({});
  const [journal, setJournal] = useState<JournalEntry[]>([]);
  const [journalText, setJournalText] = useState("");
  const [journalBusy, setJournalBusy] = useState(false);

  const load = useCallback(async () => {
    const res = await api<Detail>(`/novenas/${slug}`);
    setD(res);
    if (res.enrollment) {
      const cur = Math.min(9, Math.max(1, daysBetween(res.enrollment.start_date, todayISO()) + 1));
      setSelDay(cur);
    }
    try {
      const j = await api<{ items: JournalEntry[] }>(`/novenas/${slug}/journal`);
      setJournal(j.items || []);
    } catch { /* ignore */ }
  }, [slug]);

  useEffect(() => { load(); }, [load]);

  const enr = d?.enrollment || null;
  const currentDay = useMemo(() => (enr ? Math.min(9, Math.max(1, daysBetween(enr.start_date, todayISO()) + 1)) : 0), [enr]);
  const completed = useMemo(() => new Set(enr?.completed_days || []), [enr]);

  const loadReflection = useCallback(async (day: number) => {
    if (reflection[day]) return;
    try {
      const r = await api<{ reflection: string }>(`/novenas/${slug}/reflection/${day}`);
      setReflection((p) => ({ ...p, [day]: r.reflection || "" }));
    } catch { /* ignore */ }
  }, [slug, reflection]);

  useEffect(() => {
    if (enr && selDay <= currentDay) loadReflection(selDay);
  }, [enr, selDay, currentDay, loadReflection]);

  const start = async () => {
    setBusy(true);
    try {
      await api(`/novenas/${slug}/start`, { method: "POST", body: { start_date: startDate } });
      await load();
    } catch (e: any) {
      Alert.alert("Could not start", String(e?.detail || e?.message || e));
    } finally {
      setBusy(false);
    }
  };

  const completeDay = async (day: number) => {
    setBusy(true);
    try {
      await api(`/novenas/${slug}/complete-day`, { method: "POST", body: { day } });
      await load();
    } finally { setBusy(false); }
  };

  const restart = () => {
    Alert.alert("Restart novena?", "This resets your progress and starts again.", [
      { text: "Cancel", style: "cancel" },
      { text: "Restart", onPress: async () => { await api(`/novenas/${slug}/start`, { method: "POST", body: { start_date: todayISO() } }); await load(); } },
    ]);
  };
  const stop = () => {
    Alert.alert("Stop novena?", "Your progress will be cleared. Your journal entries are kept.", [
      { text: "Cancel", style: "cancel" },
      { text: "Stop", style: "destructive", onPress: async () => { await api(`/novenas/${slug}/stop`, { method: "POST" }); await load(); } },
    ]);
  };

  const addJournal = async () => {
    const text = journalText.trim();
    if (!text) return;
    setJournalBusy(true);
    try {
      const entry = await api<JournalEntry>(`/novenas/${slug}/journal`, { method: "POST", body: { text } });
      setJournal((p) => [entry, ...p]);
      setJournalText("");
    } catch (e: any) {
      Alert.alert("Could not save", String(e?.detail || e?.message || e));
    } finally { setJournalBusy(false); }
  };

  const deleteJournal = (id: string) => {
    Alert.alert("Delete entry?", "This intention will be removed.", [
      { text: "Cancel", style: "cancel" },
      { text: "Delete", style: "destructive", onPress: async () => {
        await api(`/novenas/${slug}/journal/${id}`, { method: "DELETE" });
        setJournal((p) => p.filter((x) => x.id !== id));
      } },
    ]);
  };

  if (!d) {
    return (
      <SafeAreaView style={styles.safe} edges={["top"]}>
        <Stack.Screen options={{ headerShown: false }} />
        <ActivityIndicator color={colors.gold} style={{ marginTop: 80 }} />
      </SafeAreaView>
    );
  }

  const quick = [
    { label: "Today", val: todayISO() },
    { label: "Tomorrow", val: addDays(todayISO(), 1) },
    { label: "In 3 days", val: addDays(todayISO(), 3) },
  ];

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="novena-detail-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}><Ionicons name="chevron-back" size={26} color={colors.primary} /></Pressable>
        <RNText style={styles.headerTitle} numberOfLines={1}>{d.name}</RNText>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: spacing.xxl }}>
        <View style={[styles.hero, { borderColor: d.color }]}>
          <View style={[styles.iconWrap, { backgroundColor: d.color }]}>
            <Ionicons name={d.icon as any} size={26} color="#FAF9F6" />
          </View>
          <RNText style={styles.patron}>{d.patron}</RNText>
          <AutoText style={styles.feast}>{`Feast · ${d.feast}`}</AutoText>
          <RNText style={styles.intro}>{d.intro}</RNText>
        </View>

        {!enr ? (
          <View style={styles.startBox}>
            <AutoText style={styles.sectionLabel}>Choose your start date</AutoText>
            <View style={styles.quickRow}>
              {quick.map((q) => (
                <Pressable key={q.label} onPress={() => setStartDate(q.val)}
                  style={[styles.quickChip, startDate === q.val && { backgroundColor: d.color, borderColor: d.color }]}>
                  <AutoText style={[styles.quickText, startDate === q.val && { color: "#fff" }]}>{q.label}</AutoText>
                </Pressable>
              ))}
            </View>
            <TextInput value={startDate} onChangeText={setStartDate} placeholder="YYYY-MM-DD"
              placeholderTextColor={colors.textMuted} style={styles.input} autoCapitalize="none" testID="novena-start-date" />
            <AutoText style={styles.hint}>The novena runs 9 consecutive days from this date.</AutoText>
            <Pressable onPress={start} disabled={busy} testID="novena-start-btn"
              style={({ pressed }) => [styles.primaryBtn, { backgroundColor: d.color }, (pressed || busy) && { opacity: 0.7 }]}>
              {busy ? <ActivityIndicator color="#fff" /> : <AutoText style={styles.primaryBtnText}>Start Novena</AutoText>}
            </Pressable>
          </View>
        ) : (
          <>
            <View style={styles.progressRow}>
              <AutoText style={styles.progressText}>{`Day ${currentDay} of 9`}</AutoText>
              <AutoText style={styles.progressDone}>{`${completed.size} completed`}</AutoText>
            </View>
            <View style={styles.dayDots}>
              {Array.from({ length: 9 }, (_, i) => i + 1).map((day) => {
                const locked = day > currentDay;
                const done = completed.has(day);
                const sel = day === selDay;
                return (
                  <Pressable key={day} disabled={locked} onPress={() => setSelDay(day)}
                    style={[styles.dot, sel && { borderColor: d.color, borderWidth: 2 }, done && { backgroundColor: d.color }, locked && { opacity: 0.4 }]}>
                    {done ? <Ionicons name="checkmark" size={14} color="#fff" />
                      : locked ? <Ionicons name="lock-closed" size={11} color={colors.textMuted} />
                      : <RNText style={[styles.dotText, sel && { color: d.color }]}>{day}</RNText>}
                  </Pressable>
                );
              })}
            </View>

            {/* Selected day */}
            <View style={styles.dayCard}>
              <AutoText style={styles.dayTitle}>{`Day ${selDay}`}</AutoText>
              {d.day_intentions && d.day_intentions[selDay - 1] ? (
                <RNText style={styles.intention}>{d.day_intentions[selDay - 1]}</RNText>
              ) : null}
              <AutoText style={styles.prayerLabel}>PRAYER</AutoText>
              <RNText style={styles.prayer}>{d.main_prayer}</RNText>

              {selDay <= currentDay ? (
                <>
                  <AutoText style={styles.prayerLabel}>CONTEMPLATION</AutoText>
                  {reflection[selDay] ? (
                    <RNText style={styles.reflection}>{reflection[selDay]}</RNText>
                  ) : (
                    <ActivityIndicator color={colors.gold} style={{ alignSelf: "flex-start", marginTop: 4 }} />
                  )}
                </>
              ) : (
                <AutoText style={styles.lockedNote}>Available on this day of your novena.</AutoText>
              )}

              {!completed.has(selDay) && selDay <= currentDay ? (
                <Pressable onPress={() => completeDay(selDay)} disabled={busy} testID="novena-complete-day"
                  style={({ pressed }) => [styles.primaryBtn, { backgroundColor: d.color, marginTop: spacing.md }, (pressed || busy) && { opacity: 0.7 }]}>
                  <AutoText style={styles.primaryBtnText}>{`Mark Day ${selDay} Complete`}</AutoText>
                </Pressable>
              ) : completed.has(selDay) ? (
                <View style={styles.doneTag}><Ionicons name="checkmark-circle" size={16} color={d.color} /><AutoText style={[styles.doneTagText, { color: d.color }]}>Completed</AutoText></View>
              ) : null}
            </View>

            <View style={styles.footerRow}>
              <Pressable onPress={restart} style={styles.secBtn} testID="novena-restart"><Ionicons name="refresh-outline" size={15} color={colors.primary} /><AutoText style={styles.secText}>Restart</AutoText></Pressable>
              <Pressable onPress={stop} style={styles.secBtn} testID="novena-stop"><Ionicons name="close-outline" size={16} color="#9E1B1B" /><AutoText style={[styles.secText, { color: "#9E1B1B" }]}>Stop</AutoText></Pressable>
            </View>
          </>
        )}

        {/* Intentions journal — available whether or not the novena is active */}
        <View style={styles.journalBox} testID="novena-journal">
          <View style={styles.journalHead}>
            <Ionicons name="create-outline" size={16} color={d.color} />
            <AutoText style={styles.journalTitle}>Intentions journal</AutoText>
          </View>
          <AutoText style={styles.journalHint}>Write the intentions you are carrying into this novena and return to them as you pray.</AutoText>
          <TextInput
            value={journalText}
            onChangeText={setJournalText}
            placeholder="What are you praying for?"
            placeholderTextColor={colors.textMuted}
            style={styles.journalInput}
            multiline
            testID="novena-journal-input"
          />
          <Pressable onPress={addJournal} disabled={journalBusy || !journalText.trim()} testID="novena-journal-add"
            style={({ pressed }) => [styles.journalAddBtn, { backgroundColor: d.color }, (pressed || journalBusy || !journalText.trim()) && { opacity: 0.6 }]}>
            {journalBusy ? <ActivityIndicator color="#fff" /> : <AutoText style={styles.journalAddText}>Add intention</AutoText>}
          </Pressable>

          {journal.length === 0 ? (
            <AutoText style={styles.journalEmpty}>No intentions written yet.</AutoText>
          ) : (
            journal.map((j) => (
              <View key={j.id} style={styles.journalEntry} testID={`novena-journal-entry-${j.id}`}>
                <View style={{ flex: 1 }}>
                  <RNText style={styles.journalEntryText}>{j.text}</RNText>
                  <RNText style={styles.journalDate}>{new Date(j.created_at).toLocaleDateString()}</RNText>
                </View>
                <Pressable onPress={() => deleteJournal(j.id)} hitSlop={10} testID={`novena-journal-del-${j.id}`}>
                  <Ionicons name="trash-outline" size={16} color={colors.textMuted} />
                </Pressable>
              </View>
            ))
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 17, color: colors.textPrimary, flex: 1, textAlign: "center", marginHorizontal: spacing.sm },
  hero: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1.5, padding: spacing.lg, alignItems: "center", marginBottom: spacing.lg },
  iconWrap: { width: 52, height: 52, borderRadius: 26, alignItems: "center", justifyContent: "center", marginBottom: spacing.sm },
  patron: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.primary },
  feast: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.gold, letterSpacing: 1, marginTop: 2 },
  intro: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, lineHeight: 21, marginTop: spacing.sm, textAlign: "center" },
  startBox: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.borderSoft, padding: spacing.md },
  sectionLabel: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.primary, marginBottom: spacing.sm },
  quickRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.sm },
  quickChip: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.round, paddingHorizontal: 12, paddingVertical: 7 },
  quickText: { fontFamily: fonts.uiSemi, fontSize: 12.5, color: colors.textPrimary },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, padding: 11, fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary },
  hint: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textMuted, marginTop: 6 },
  primaryBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", borderRadius: radius.md, paddingVertical: 13, marginTop: spacing.md },
  primaryBtnText: { fontFamily: fonts.uiSemi, fontSize: 15, color: "#fff" },
  progressRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.sm },
  progressText: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.primary },
  progressDone: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textMuted },
  dayDots: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: spacing.md },
  dot: { width: 34, height: 34, borderRadius: 17, borderWidth: 1, borderColor: colors.border, alignItems: "center", justifyContent: "center", backgroundColor: colors.surface },
  dotText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textSecondary },
  dayCard: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.borderSoft, padding: spacing.md },
  dayTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.primary },
  intention: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 14, color: colors.textSecondary, marginTop: 6, lineHeight: 21 },
  prayerLabel: { fontFamily: fonts.uiSemi, fontSize: 10.5, color: colors.gold, letterSpacing: 1.5, marginTop: spacing.md, marginBottom: 4 },
  prayer: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary, lineHeight: 23 },
  reflection: { fontFamily: fonts.bodyRegular, fontSize: 14.5, color: colors.textPrimary, lineHeight: 22, fontStyle: "italic" },
  lockedNote: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13, color: colors.textMuted },
  doneTag: { flexDirection: "row", alignItems: "center", gap: 5, marginTop: spacing.md },
  doneTagText: { fontFamily: fonts.uiSemi, fontSize: 13 },
  footerRow: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.lg },
  secBtn: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 5, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, paddingVertical: 10 },
  secText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.primary },
  journalBox: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.borderSoft, padding: spacing.md, marginTop: spacing.lg },
  journalHead: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 4 },
  journalTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.primary },
  journalHint: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textSecondary, lineHeight: 19, marginBottom: spacing.sm },
  journalInput: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, padding: 11, fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary, minHeight: 70, textAlignVertical: "top" },
  journalAddBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", borderRadius: radius.md, paddingVertical: 11, marginTop: spacing.sm },
  journalAddText: { fontFamily: fonts.uiSemi, fontSize: 14, color: "#fff" },
  journalEmpty: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13, color: colors.textMuted, marginTop: spacing.md },
  journalEntry: { flexDirection: "row", alignItems: "flex-start", gap: spacing.sm, paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  journalEntryText: { fontFamily: fonts.bodyRegular, fontSize: 14.5, color: colors.textPrimary, lineHeight: 21 },
  journalDate: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 3 },
});

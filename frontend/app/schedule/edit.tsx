/**
 * Schedule editor — add or edit a schedule item.
 *
 * Supports meals, workouts, an active virtue plan, an enrolled liturgical
 * challenge, or a custom entry; weekly (multi-day) or one-off (single date)
 * recurrence; an optional 12-hour (AM/PM) time; and an on-device reminder.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import {
  createScheduleItem,
  deleteScheduleItem,
  getScheduleSources,
  listSchedule,
  ScheduleItem,
  ScheduleItemInput,
  ScheduleKind,
  ScheduleSources,
  setScheduleNotifIds,
  updateScheduleItem,
} from "@/src/api";
import {
  cancelNotifications,
  ensureNotificationPermission,
  notificationsSupported,
  scheduleItemNotifications,
} from "@/src/notifications";
import { build24, DOW_SHORT, parse24 } from "@/src/schedule-utils";
import { googleCalUrl, icsLink } from "@/src/calendar-export";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { formatLongFromISO, todayISO } from "@/src/date-utils";

const KINDS: { key: ScheduleKind; label: string; icon: keyof typeof Ionicons.glyphMap; color: string }[] = [
  { key: "meal", label: "Meal", icon: "restaurant-outline", color: "#C99A4A" },
  { key: "workout", label: "Workout", icon: "barbell-outline", color: "#3E5C76" },
  { key: "virtue", label: "Virtue", icon: "sparkles-outline", color: "#8A4A6C" },
  { key: "challenge", label: "Challenge", icon: "flame-outline", color: "#9C3B2E" },
  { key: "custom", label: "Custom", icon: "create-outline", color: "#5B7553" },
];
const HOURS = [12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
const MINUTES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55];

function shiftISO(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function ScheduleEditScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ id?: string; dow?: string; date?: string; rec?: string }>();
  const editing = !!params.id;

  const [loading, setLoading] = useState(editing);
  const [saving, setSaving] = useState(false);
  const [original, setOriginal] = useState<ScheduleItem | null>(null);
  const [sources, setSources] = useState<ScheduleSources | null>(null);

  const [kind, setKind] = useState<ScheduleKind>("custom");
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [refId, setRefId] = useState<string | null>(null);
  const [refSlug, setRefSlug] = useState<string | null>(null);
  const [color, setColor] = useState<string | null>(null);
  const [icon, setIcon] = useState<string | null>(null);

  const [recurrence, setRecurrence] = useState<"weekly" | "once">(
    params.rec === "once" ? "once" : "weekly",
  );
  const [days, setDays] = useState<number[]>(
    params.dow != null ? [Number(params.dow)] : [new Date().getDay()],
  );
  const [date, setDate] = useState<string>(params.date || todayISO());

  const [allDay, setAllDay] = useState(true);
  const [h12, setH12] = useState(9);
  const [minute, setMinute] = useState(0);
  const [ampm, setAmpm] = useState<"AM" | "PM">("AM");
  const [notify, setNotify] = useState(false);

  // Load sources + (if editing) the item.
  const load = useCallback(async () => {
    try {
      const [src] = await Promise.all([getScheduleSources().catch(() => null)]);
      if (src) setSources(src);
      if (editing) {
        const all = await listSchedule();
        const it = (all.items || []).find((x) => x.id === params.id) || null;
        if (it) {
          setOriginal(it);
          setKind(it.kind);
          setTitle(it.title);
          setNote(it.note || "");
          setRefId(it.ref_id || null);
          setRefSlug(it.ref_slug || null);
          setColor(it.color || null);
          setIcon(it.icon || null);
          setRecurrence(it.recurrence);
          setDays(it.days_of_week || []);
          if (it.date) setDate(it.date);
          if (it.time) {
            const p = parse24(it.time);
            setAllDay(false);
            setH12(p.h12); setMinute(p.minute); setAmpm(p.ampm);
          } else {
            setAllDay(true);
          }
          setNotify(it.notify);
        }
      }
    } finally {
      setLoading(false);
    }
  }, [editing, params.id]);

  useEffect(() => { void load(); }, [load]);

  const kindMeta = useMemo(() => KINDS.find((k) => k.key === kind)!, [kind]);

  const pickKind = (k: ScheduleKind) => {
    setKind(k);
    setRefId(null); setRefSlug(null);
    const km = KINDS.find((x) => x.key === k)!;
    setColor(km.color); setIcon(km.icon);
    if (k === "meal" && !title) setTitle("Breakfast");
    if (k === "workout" && !title) setTitle("Workout");
  };

  const toggleDay = (d: number) =>
    setDays((prev) => (prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]));

  const onToggleNotify = async (v: boolean) => {
    setNotify(v);
    if (v && notificationsSupported) {
      const perm = await ensureNotificationPermission();
      if (!perm.granted && !perm.canAskAgain) {
        Alert.alert(
          "Reminders are off",
          "Enable notifications for Sanctus in Settings to get schedule reminders.",
          [
            { text: "Not now", style: "cancel" },
            { text: "Open Settings", onPress: () => Linking.openSettings() },
          ],
        );
      }
    }
  };

  const save = async () => {
    if (saving) return;
    const t = title.trim();
    if (!t) { Alert.alert("Add a title", "Give this item a name."); return; }
    if (recurrence === "weekly" && days.length === 0) {
      Alert.alert("Pick a day", "Choose at least one day of the week."); return;
    }
    setSaving(true);
    const body: ScheduleItemInput = {
      kind,
      title: t,
      note: note.trim() || undefined,
      recurrence,
      days_of_week: recurrence === "weekly" ? days : [],
      date: recurrence === "once" ? date : null,
      time: allDay ? null : build24(h12, minute, ampm),
      ref_id: refId,
      ref_slug: refSlug,
      color,
      icon,
      notify,
    };
    try {
      const saved = editing && params.id
        ? await updateScheduleItem(params.id, body)
        : await createScheduleItem(body);

      // Reschedule reminders (cancel previous, schedule new, persist IDs).
      if (notificationsSupported) {
        if (original?.notif_ids?.length) await cancelNotifications(original.notif_ids);
        const ids = await scheduleItemNotifications(saved);
        if (ids.length) await setScheduleNotifIds(saved.id, ids).catch(() => undefined);
      }
      router.back();
    } catch (e: any) {
      Alert.alert("Couldn't save", e?.message || "Please try again.");
      setSaving(false);
    }
  };

  const confirmDelete = () => {
    Alert.alert("Delete this item?", "It will be removed from your schedule.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          if (!params.id) return;
          try {
            const r = await deleteScheduleItem(params.id);
            await cancelNotifications(r.notif_ids);
            router.back();
          } catch { /* ignore */ }
        },
      },
    ]);
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safe} edges={["top"]}>
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      </SafeAreaView>
    );
  }

  const showSources = kind === "virtue" || kind === "challenge";
  const sourceList = kind === "virtue" ? (sources?.virtue_plans || []) : (sources?.challenges || []);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="schedule-edit-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="schedule-edit-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.headerTitle}>{editing ? "Edit item" : "Add to schedule"}</Text>
        </View>
        {editing ? (
          <Pressable testID="schedule-edit-delete" onPress={confirmDelete} hitSlop={10}>
            <Ionicons name="trash-outline" size={20} color={colors.textMuted} />
          </Pressable>
        ) : <View style={{ width: 26 }} />}
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {/* Kind */}
          <Text style={styles.label}>TYPE</Text>
          <View style={styles.chipWrap}>
            {KINDS.map((k) => {
              const on = kind === k.key;
              return (
                <Pressable
                  key={k.key}
                  testID={`schedule-kind-${k.key}`}
                  onPress={() => pickKind(k.key)}
                  style={({ pressed }) => [styles.chip, on && { backgroundColor: k.color, borderColor: k.color }, pressed && { opacity: 0.85 }]}
                >
                  <Ionicons name={k.icon} size={14} color={on ? colors.gold : k.color} />
                  <Text style={[styles.chipText, on && { color: colors.gold }]}>{k.label}</Text>
                </Pressable>
              );
            })}
          </View>

          {/* Source picker for virtue/challenge */}
          {showSources ? (
            <View style={{ marginTop: spacing.md }}>
              <Text style={styles.label}>{kind === "virtue" ? "ACTIVE VIRTUE PLAN" : "ENROLLED CHALLENGE"}</Text>
              {sourceList.length === 0 ? (
                <Text style={styles.hint}>
                  {kind === "virtue" ? "No active virtue plans — start one in Virtus." : "You're not enrolled in any challenges yet."}
                </Text>
              ) : (
                <View style={styles.chipWrap}>
                  {sourceList.map((s: any) => {
                    const id = s.ref_id || s.ref_slug;
                    const on = (kind === "virtue" ? refId : refSlug) === id;
                    return (
                      <Pressable
                        key={id}
                        testID={`schedule-source-${id}`}
                        onPress={() => {
                          setTitle(s.title);
                          if (kind === "virtue") { setRefId(s.ref_id); setRefSlug(null); }
                          else { setRefSlug(s.ref_slug); setRefId(null); if (s.color) setColor(s.color); if (s.icon) setIcon(s.icon); }
                        }}
                        style={({ pressed }) => [styles.chip, on && { backgroundColor: colors.primary, borderColor: colors.primary }, pressed && { opacity: 0.85 }]}
                      >
                        <Text style={[styles.chipText, on && { color: colors.gold }]} numberOfLines={1}>{s.title}</Text>
                      </Pressable>
                    );
                  })}
                </View>
              )}
            </View>
          ) : null}

          {/* Title */}
          <Text style={[styles.label, { marginTop: spacing.md }]}>TITLE</Text>
          <TextInput
            testID="schedule-title"
            value={title}
            onChangeText={setTitle}
            placeholder={kind === "meal" ? "e.g. Breakfast" : kind === "workout" ? "e.g. Leg day" : "What is it?"}
            placeholderTextColor={colors.textMuted}
            style={styles.input}
          />

          {/* Recurrence */}
          <Text style={[styles.label, { marginTop: spacing.md }]}>REPEATS</Text>
          <View style={styles.segment}>
            {(["weekly", "once"] as const).map((r) => {
              const on = recurrence === r;
              return (
                <Pressable
                  key={r}
                  testID={`schedule-rec-${r}`}
                  onPress={() => setRecurrence(r)}
                  style={[styles.segItem, on && styles.segItemOn]}
                >
                  <Text style={[styles.segText, on && styles.segTextOn]}>{r === "weekly" ? "Weekly" : "One date"}</Text>
                </Pressable>
              );
            })}
          </View>

          {recurrence === "weekly" ? (
            <View style={styles.dowRow}>
              {DOW_SHORT.map((label, i) => {
                const on = days.includes(i);
                return (
                  <Pressable
                    key={i}
                    testID={`schedule-day-${i}`}
                    onPress={() => toggleDay(i)}
                    style={[styles.dayBtn, on && styles.dayBtnOn]}
                  >
                    <Text style={[styles.dayBtnText, on && styles.dayBtnTextOn]}>{label[0]}</Text>
                  </Pressable>
                );
              })}
            </View>
          ) : (
            <View style={styles.dateRow}>
              <Pressable
                testID="schedule-date-prev"
                onPress={() => setDate((d) => (d > todayISO() ? shiftISO(d, -1) : d))}
                style={styles.dateArrow}
                hitSlop={8}
              >
                <Ionicons name="chevron-back" size={20} color={date > todayISO() ? colors.primary : colors.borderSoft} />
              </Pressable>
              <Text style={styles.dateLabel}>{formatLongFromISO(date)}</Text>
              <Pressable testID="schedule-date-next" onPress={() => setDate((d) => shiftISO(d, 1))} style={styles.dateArrow} hitSlop={8}>
                <Ionicons name="chevron-forward" size={20} color={colors.primary} />
              </Pressable>
            </View>
          )}

          {/* Time */}
          <View style={[styles.label, styles.timeHead] as any}>
            <Text style={styles.label}>TIME</Text>
            <View style={{ flex: 1 }} />
            <Text style={styles.allDayLabel}>All day</Text>
            <Switch
              testID="schedule-allday"
              value={allDay}
              onValueChange={setAllDay}
              trackColor={{ false: colors.borderSoft, true: colors.gold }}
              thumbColor={colors.surface}
            />
          </View>
          {!allDay ? (
            <View style={styles.timeCard}>
              <Text style={styles.timeSub}>Hour</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.timeScroll}>
                {HOURS.map((h) => (
                  <Pressable key={h} testID={`schedule-hour-${h}`} onPress={() => setH12(h)} style={[styles.timeChip, h12 === h && styles.timeChipOn]}>
                    <Text style={[styles.timeChipText, h12 === h && styles.timeChipTextOn]}>{h}</Text>
                  </Pressable>
                ))}
              </ScrollView>
              <Text style={styles.timeSub}>Minute</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.timeScroll}>
                {MINUTES.map((m) => (
                  <Pressable key={m} testID={`schedule-min-${m}`} onPress={() => setMinute(m)} style={[styles.timeChip, minute === m && styles.timeChipOn]}>
                    <Text style={[styles.timeChipText, minute === m && styles.timeChipTextOn]}>{String(m).padStart(2, "0")}</Text>
                  </Pressable>
                ))}
              </ScrollView>
              <View style={styles.ampmRow}>
                {(["AM", "PM"] as const).map((p) => (
                  <Pressable key={p} testID={`schedule-ampm-${p}`} onPress={() => setAmpm(p)} style={[styles.ampmChip, ampm === p && styles.ampmChipOn]}>
                    <Text style={[styles.ampmText, ampm === p && styles.timeChipTextOn]}>{p}</Text>
                  </Pressable>
                ))}
                <View style={{ flex: 1 }} />
                <Text style={styles.timePreview}>{h12}:{String(minute).padStart(2, "0")} {ampm}</Text>
              </View>
            </View>
          ) : null}

          {/* Notify */}
          <View style={styles.notifyRow}>
            <Ionicons name="notifications-outline" size={18} color={notify ? colors.gold : colors.textMuted} />
            <View style={{ flex: 1 }}>
              <Text style={styles.notifyTitle}>Remind me</Text>
              <Text style={styles.notifyHint}>
                {notificationsSupported ? "A notification at the scheduled time." : "Reminders fire on the built app, not in preview."}
              </Text>
            </View>
            <Switch
              testID="schedule-notify"
              value={notify}
              onValueChange={onToggleNotify}
              trackColor={{ false: colors.borderSoft, true: colors.gold }}
              thumbColor={colors.surface}
            />
          </View>

          {/* Note */}
          <Text style={[styles.label, { marginTop: spacing.md }]}>NOTE (OPTIONAL)</Text>
          <TextInput
            testID="schedule-note"
            value={note}
            onChangeText={setNote}
            placeholder="Anything to remember…"
            placeholderTextColor={colors.textMuted}
            style={[styles.input, { minHeight: 60 }]}
            multiline
          />

          {/* Add to external calendar (saved items only) */}
          {editing && original?.ics_token ? (
            <View style={styles.exportCard} testID="schedule-export">
              <Text style={styles.label}>ADD TO YOUR CALENDAR</Text>
              <Text style={styles.exportHint}>
                Put this on Google or your phone's calendar so it sends the reminders.
              </Text>
              <Pressable
                testID="export-google"
                onPress={() => Linking.openURL(googleCalUrl(original))}
                style={({ pressed }) => [styles.exportBtn, pressed && { opacity: 0.85 }]}
              >
                <Ionicons name="logo-google" size={16} color={colors.primary} />
                <Text style={styles.exportBtnText}>Google Calendar</Text>
                <Ionicons name="open-outline" size={15} color={colors.textMuted} />
              </Pressable>
              <Pressable
                testID="export-ics"
                onPress={() => { const u = icsLink(original); if (u) Linking.openURL(u); }}
                style={({ pressed }) => [styles.exportBtn, pressed && { opacity: 0.85 }]}
              >
                <Ionicons name="calendar-outline" size={16} color={colors.primary} />
                <Text style={styles.exportBtnText}>Apple / phone calendar</Text>
                <Ionicons name="download-outline" size={15} color={colors.textMuted} />
              </Pressable>
            </View>
          ) : null}

          <Pressable
            testID="schedule-save"
            onPress={save}
            disabled={saving}
            style={({ pressed }) => [styles.saveBtn, { backgroundColor: kindMeta.color }, saving && { opacity: 0.6 }, pressed && { opacity: 0.85 }]}
          >
            {saving ? <ActivityIndicator size="small" color={colors.gold} /> : (
              <>
                <Ionicons name="checkmark" size={18} color={colors.gold} />
                <Text style={styles.saveText}>{editing ? "Save changes" : "Add to schedule"}</Text>
              </>
            )}
          </Pressable>
          <View style={{ height: spacing.xxl * 2 }} />
        </ScrollView>
      </KeyboardAvoidingView>
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
  scroll: { padding: spacing.lg },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  label: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 1.2, color: colors.textMuted, marginBottom: 8 },
  hint: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13, color: colors.textMuted },
  chipWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    flexDirection: "row", alignItems: "center", gap: 5,
    paddingHorizontal: spacing.md, paddingVertical: 8, borderRadius: radius.round,
    borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surface, maxWidth: 260,
  },
  chipText: { fontFamily: fonts.uiSemi, fontSize: 12.5, color: colors.textSecondary },
  input: {
    borderWidth: 1, borderColor: colors.borderSoft, borderRadius: radius.md,
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm + 2,
    fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary,
    backgroundColor: colors.surface, textAlignVertical: "top",
  },
  segment: { flexDirection: "row", backgroundColor: colors.surface, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, padding: 3 },
  segItem: { flex: 1, alignItems: "center", paddingVertical: 9, borderRadius: radius.round },
  segItemOn: { backgroundColor: colors.primary },
  segText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textSecondary },
  segTextOn: { color: colors.gold },
  dowRow: { flexDirection: "row", justifyContent: "space-between", marginTop: spacing.md },
  dayBtn: {
    width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center",
    borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surface,
  },
  dayBtnOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  dayBtnText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textSecondary },
  dayBtnTextOn: { color: colors.gold },
  dateRow: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    marginTop: spacing.md, padding: spacing.sm, borderRadius: radius.md,
    borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surface,
  },
  dateArrow: { padding: 6 },
  dateLabel: { flex: 1, textAlign: "center", fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary },
  timeHead: { flexDirection: "row", alignItems: "center", marginTop: spacing.lg, marginBottom: 0 },
  allDayLabel: { fontFamily: fonts.uiMedium, fontSize: 13, color: colors.textSecondary, marginRight: 8 },
  timeCard: { marginTop: spacing.sm, padding: spacing.md, borderRadius: radius.md, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surface },
  timeSub: { fontFamily: fonts.uiSemi, fontSize: 10.5, letterSpacing: 1, color: colors.textMuted, marginBottom: 6, marginTop: 4 },
  timeScroll: { gap: 6, paddingRight: spacing.md },
  timeChip: {
    minWidth: 38, height: 38, paddingHorizontal: 6, borderRadius: 19, alignItems: "center", justifyContent: "center",
    borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.background,
  },
  timeChipOn: { backgroundColor: colors.gold, borderColor: colors.gold },
  timeChipText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textSecondary },
  timeChipTextOn: { color: colors.surface },
  ampmRow: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: spacing.md },
  ampmChip: { paddingHorizontal: spacing.md, paddingVertical: 8, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.background },
  ampmChipOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  ampmText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textSecondary },
  timePreview: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  notifyRow: {
    flexDirection: "row", alignItems: "center", gap: spacing.sm,
    marginTop: spacing.lg, padding: spacing.md, borderRadius: radius.md,
    borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surface,
  },
  notifyTitle: { fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary },
  notifyHint: { fontFamily: fonts.bodyRegular, fontSize: 11.5, color: colors.textMuted, marginTop: 2, lineHeight: 16 },
  saveBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    marginTop: spacing.xl, paddingVertical: 14, borderRadius: radius.round, ...shadow.card,
  },
  saveText: { fontFamily: fonts.uiSemi, fontSize: 15, color: colors.gold, letterSpacing: 0.4 },
  exportCard: {
    marginTop: spacing.lg, padding: spacing.md, borderRadius: radius.md,
    borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surface, gap: spacing.sm,
  },
  exportHint: { fontFamily: fonts.bodyRegular, fontSize: 12.5, lineHeight: 18, color: colors.textMuted, marginTop: -4 },
  exportBtn: {
    flexDirection: "row", alignItems: "center", gap: 10,
    paddingVertical: 11, paddingHorizontal: spacing.md, borderRadius: radius.md,
    borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.background,
  },
  exportBtnText: { flex: 1, fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
});

import React, { useMemo, useState } from "react";
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
import { Stack, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import {
  createCustomChallenge,
  CUSTOM_CHALLENGE_CATEGORIES,
  CustomChallengeItem,
} from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

const LENGTHS = [7, 14, 30, 60];

function isoOf(d: Date): string {
  return d.toISOString().slice(0, 10);
}
function longDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00Z`);
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export default function NewCustomChallenge() {
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const [title, setTitle] = useState("");
  const [lengthDays, setLengthDays] = useState(7);
  const [startIso, setStartIso] = useState(isoOf(new Date()));
  const [activeDay, setActiveDay] = useState(1);
  const [daysMap, setDaysMap] = useState<Record<number, CustomChallengeItem[]>>({});
  const [category, setCategory] = useState("prayer");
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);

  const items = daysMap[activeDay] || [];

  const shiftStart = (delta: number) => {
    const d = new Date(`${startIso}T00:00:00Z`);
    d.setUTCDate(d.getUTCDate() + delta);
    setStartIso(isoOf(d));
  };

  const addItem = () => {
    const t = text.trim();
    if (!t) return;
    setDaysMap((m) => ({ ...m, [activeDay]: [...(m[activeDay] || []), { category, text: t }] }));
    setText("");
  };

  const removeItem = (idx: number) => {
    setDaysMap((m) => ({ ...m, [activeDay]: (m[activeDay] || []).filter((_, i) => i !== idx) }));
  };

  const applyToAll = () => {
    const src = daysMap[activeDay] || [];
    const next: Record<number, CustomChallengeItem[]> = {};
    for (let d = 1; d <= lengthDays; d++) next[d] = src.map((x) => ({ ...x }));
    setDaysMap(next);
  };

  const totalItems = useMemo(
    () => Object.values(daysMap).reduce((n, arr) => n + arr.length, 0),
    [daysMap],
  );

  const canSave = title.trim().length > 0 && totalItems > 0 && !saving;

  const save = async () => {
    if (!canSave) return;
    setSaving(true);
    try {
      const days = Object.entries(daysMap)
        .filter(([, arr]) => arr.length > 0)
        .map(([d, arr]) => ({ day: Number(d), items: arr }));
      await createCustomChallenge({
        title: title.trim(),
        length_days: lengthDays,
        start_date: startIso,
        days,
      });
      router.back();
    } catch {
      setSaving(false);
    }
  };

  const catIcon = (key: string) =>
    (CUSTOM_CHALLENGE_CATEGORIES.find((c) => c.key === key)?.icon ||
      "ellipse-outline") as keyof typeof Ionicons.glyphMap;

  return (
    <View style={{ flex: 1, backgroundColor: colors.background, paddingTop: insets.top }}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="cc-back" onPress={() => router.back()} hitSlop={12} style={styles.iconBtn}>
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
        </Pressable>
        <Text style={styles.headerTitle}>New Challenge</Text>
        <Pressable
          testID="cc-save"
          onPress={save}
          disabled={!canSave}
          style={[styles.saveBtn, !canSave && { opacity: 0.4 }]}
        >
          {saving ? (
            <ActivityIndicator color={colors.surface} size="small" />
          ) : (
            <Text style={styles.saveText}>Save</Text>
          )}
        </Pressable>
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: 60 }}>
          <Text style={styles.label}>Title</Text>
          <TextInput
            testID="cc-title"
            value={title}
            onChangeText={setTitle}
            placeholder="e.g. Lenten reset, 30 days for my family"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
          />

          <Text style={styles.label}>Length</Text>
          <View style={styles.rowWrap}>
            {LENGTHS.map((n) => {
              const sel = lengthDays === n;
              return (
                <Pressable
                  key={n}
                  testID={`cc-length-${n}`}
                  onPress={() => {
                    setLengthDays(n);
                    if (activeDay > n) setActiveDay(1);
                  }}
                  style={[styles.chip, sel && styles.chipSel]}
                >
                  <Text style={[styles.chipText, sel && styles.chipTextSel]}>{n} days</Text>
                </Pressable>
              );
            })}
          </View>

          <Text style={styles.label}>Start date</Text>
          <View style={styles.dateRow}>
            <Pressable testID="cc-date-prev" onPress={() => shiftStart(-1)} style={styles.dateBtn}>
              <Ionicons name="chevron-back" size={18} color={colors.gold} />
            </Pressable>
            <Text style={styles.dateText}>{longDate(startIso)}</Text>
            <Pressable testID="cc-date-next" onPress={() => shiftStart(1)} style={styles.dateBtn}>
              <Ionicons name="chevron-forward" size={18} color={colors.gold} />
            </Pressable>
          </View>
          <Pressable onPress={() => setStartIso(isoOf(new Date()))}>
            <Text style={styles.todayLink}>Set to today</Text>
          </Pressable>

          <Text style={[styles.label, { marginTop: spacing.lg }]}>Daily plan</Text>
          <Text style={styles.hint}>Pick a day, then add practices. Use “Copy to all days” to repeat.</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginVertical: spacing.sm }}>
            <View style={{ flexDirection: "row", gap: 6 }}>
              {Array.from({ length: lengthDays }, (_, i) => i + 1).map((d) => {
                const sel = activeDay === d;
                const has = (daysMap[d] || []).length > 0;
                return (
                  <Pressable
                    key={d}
                    testID={`cc-day-${d}`}
                    onPress={() => setActiveDay(d)}
                    style={[styles.dayPill, sel && styles.dayPillSel, has && !sel && styles.dayPillHas]}
                  >
                    <Text style={[styles.dayPillText, sel && styles.chipTextSel]}>{d}</Text>
                  </Pressable>
                );
              })}
            </View>
          </ScrollView>

          <Text style={styles.dayHeading}>Day {activeDay}</Text>
          {items.map((it, idx) => (
            <View key={idx} style={styles.itemRow}>
              <Ionicons name={catIcon(it.category)} size={16} color={colors.gold} />
              <Text style={styles.itemText}>{it.text}</Text>
              <Pressable testID={`cc-remove-${idx}`} onPress={() => removeItem(idx)} hitSlop={8}>
                <Ionicons name="close-circle" size={18} color={colors.textMuted} />
              </Pressable>
            </View>
          ))}

          <View style={styles.rowWrap}>
            {CUSTOM_CHALLENGE_CATEGORIES.map((c) => {
              const sel = category === c.key;
              return (
                <Pressable
                  key={c.key}
                  testID={`cc-cat-${c.key}`}
                  onPress={() => setCategory(c.key)}
                  style={[styles.catChip, sel && styles.chipSel]}
                >
                  <Ionicons
                    name={c.icon as keyof typeof Ionicons.glyphMap}
                    size={13}
                    color={sel ? colors.surface : colors.gold}
                  />
                  <Text style={[styles.chipText, sel && styles.chipTextSel]}>{c.label}</Text>
                </Pressable>
              );
            })}
          </View>
          <View style={styles.addRow}>
            <TextInput
              testID="cc-item-text"
              value={text}
              onChangeText={setText}
              placeholder="Describe the practice…"
              placeholderTextColor={colors.textMuted}
              style={[styles.input, { flex: 1, marginBottom: 0 }]}
              onSubmitEditing={addItem}
            />
            <Pressable testID="cc-add-item" onPress={addItem} style={styles.addBtn}>
              <Ionicons name="add" size={22} color={colors.surface} />
            </Pressable>
          </View>

          {items.length > 0 ? (
            <Pressable testID="cc-copy-all" onPress={applyToAll} style={styles.copyAllBtn}>
              <Ionicons name="copy-outline" size={15} color={colors.gold} />
              <Text style={styles.copyAllText}>Copy Day {activeDay} to all {lengthDays} days</Text>
            </Pressable>
          ) : null}
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  iconBtn: { padding: 4 },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  saveBtn: { backgroundColor: colors.gold, paddingHorizontal: 16, paddingVertical: 7, borderRadius: radius.round, minWidth: 60, alignItems: "center" },
  saveText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.surface },
  label: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary, marginBottom: spacing.sm, marginTop: spacing.sm },
  hint: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, lineHeight: 19 },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  rowWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surface },
  chipSel: { backgroundColor: colors.gold, borderColor: colors.gold },
  chipText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textSecondary },
  chipTextSel: { color: colors.surface },
  catChip: { flexDirection: "row", alignItems: "center", gap: 5, paddingHorizontal: 12, paddingVertical: 8, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surface },
  dateRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft, borderRadius: radius.md, paddingHorizontal: spacing.sm, paddingVertical: 6 },
  dateBtn: { padding: 8 },
  dateText: { flex: 1, textAlign: "center", fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  todayLink: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold, marginTop: 6 },
  dayPill: { minWidth: 38, height: 38, borderRadius: 19, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surface },
  dayPillSel: { backgroundColor: colors.gold, borderColor: colors.gold },
  dayPillHas: { borderColor: colors.gold },
  dayPillText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textSecondary },
  dayHeading: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary, marginBottom: spacing.sm },
  itemRow: { flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft, borderRadius: radius.md, paddingHorizontal: spacing.md, paddingVertical: 10, marginBottom: 6 },
  itemText: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary },
  addRow: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: spacing.sm },
  addBtn: { backgroundColor: colors.gold, width: 44, height: 44, borderRadius: radius.md, alignItems: "center", justifyContent: "center" },
  copyAllBtn: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: spacing.md, alignSelf: "flex-start" },
  copyAllText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold },
});

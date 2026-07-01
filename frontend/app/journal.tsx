import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import {
  api,
  ExamenPrompt,
  ExaminationSection,
  JournalEntry,
  JournalKind,
  JournalMood,
  LiturgicalDay,
} from "@/src/api";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import { MOODS } from "@/src/journal-mood";
import { confirmAction } from "@/src/confirm";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { formatLong, parseISO, todayISO } from "@/src/date-utils";

type ExamenAnswers = Record<string, string>;
type ExamItem = { checked: boolean; note?: string };
type ExaminationAnswers = Record<string, Record<number, ExamItem>>;

const MODE_CHIPS: { value: JournalKind; label: string; icon: keyof typeof import("@expo/vector-icons/Ionicons")["glyphMap"] }[] = [
  { value: "free", label: "Free", icon: "create-outline" },
  { value: "examen", label: "Examen", icon: "sunny-outline" },
  { value: "examination", label: "Confession", icon: "leaf-outline" },
];

function composeExamenBody(prompts: ExamenPrompt[], answers: ExamenAnswers): string {
  return prompts
    .map((p) => {
      const a = (answers[p.key] || "").trim();
      if (!a) return null;
      return `${p.title}\n${a}`;
    })
    .filter(Boolean)
    .join("\n\n");
}

function composeExaminationBody(sections: ExaminationSection[], answers: ExaminationAnswers): string {
  const out: string[] = [];
  for (const s of sections) {
    const sec = answers[s.key] || {};
    const items: string[] = [];
    s.prompts.forEach((p, idx) => {
      const a = sec[idx];
      if (a?.checked) {
        const note = (a.note || "").trim();
        items.push(note ? `• ${p} — ${note}` : `• ${p}`);
      }
    });
    if (items.length) {
      out.push(`${s.title}\n${items.join("\n")}`);
    }
  }
  return out.join("\n\n");
}

export default function JournalScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ date?: string; entry?: string; mode?: string; verse_ref?: string; verse_text?: string; seed_title?: string; seed_body?: string }>();
  const initialDate = typeof params.date === "string" ? params.date : todayISO();
  const entryId = typeof params.entry === "string" ? params.entry : null;
  const initialMode: JournalKind = ((typeof params.mode === "string" && ["free", "examen", "examination"].includes(params.mode)) ? params.mode : "free") as JournalKind;
  const incomingVerseRef = typeof params.verse_ref === "string" ? params.verse_ref : "";
  const incomingVerseText = typeof params.verse_text === "string" ? params.verse_text : "";
  const incomingSeedTitle = typeof params.seed_title === "string" ? params.seed_title : "";
  const incomingSeedBody = typeof params.seed_body === "string" ? params.seed_body : "";

  const [date, setDate] = useState(initialDate);
  const [kind, setKind] = useState<JournalKind>(initialMode);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [mood, setMood] = useState<JournalMood>(null);
  const [confessedAt, setConfessedAt] = useState<string | null>(null);

  // Examen state
  const [examenPrompts, setExamenPrompts] = useState<ExamenPrompt[]>([]);
  const [examenAnswers, setExamenAnswers] = useState<ExamenAnswers>({});

  // Examination state
  const [examinationSections, setExaminationSections] = useState<ExaminationSection[]>([]);
  const [examinationAnswers, setExaminationAnswers] = useState<ExaminationAnswers>({});
  const [examinationNotes, setExaminationNotes] = useState("");

  const [lit, setLit] = useState<LiturgicalDay | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [marking, setMarking] = useState(false);

  const loadTemplates = useCallback(async () => {
    try {
      const [a, b] = await Promise.all([
        api<{ prompts: ExamenPrompt[] }>("/prayers/examen"),
        api<{ sections: ExaminationSection[] }>("/prayers/examination"),
      ]);
      setExamenPrompts(a.prompts || []);
      setExaminationSections(b.sections || []);
    } catch (e) {
      console.warn("templates load failed", e);
    }
  }, []);

  const load = useCallback(async () => {
    const l = await api<LiturgicalDay>(`/liturgical/day?date=${date}`);
    setLit(l);
    if (entryId) {
      try {
        const e = await api<JournalEntry>(`/journal/${entryId}`);
        setTitle(e.title || "");
        setBody(e.body || "");
        setMood(e.mood);
        setDate(e.date);
        const k = (e.kind || "free") as JournalKind;
        setKind(k);
        setConfessedAt(e.confessed_at || null);
        const s = (e.structured || {}) as Record<string, unknown>;
        if (k === "examen") {
          setExamenAnswers((s.answers as ExamenAnswers) || {});
        } else if (k === "examination") {
          setExaminationAnswers((s.sections as ExaminationAnswers) || {});
          setExaminationNotes((s.notes as string) || "");
        }
      } catch (err) {
        console.warn("failed to load entry", err);
      }
    }
  }, [date, entryId]);

  useEffect(() => {
    let c = false;
    (async () => {
      try {
        await Promise.all([load(), loadTemplates()]);
        // If a verse deep-link was supplied, prefill (only for new free-mode entries).
        if (!entryId && incomingVerseRef && incomingVerseText) {
          setKind("free");
          setTitle((prev) => prev || incomingVerseRef);
          setBody((prev) => {
            if (prev.trim()) return prev;
            return `“${incomingVerseText}”\n— ${incomingVerseRef}\n\n`;
          });
        }
        // Generic seed (e.g. from a completed self-defense session or chaplet)
        if (!entryId && (incomingSeedTitle || incomingSeedBody)) {
          setKind("free");
          if (incomingSeedTitle) setTitle((prev) => prev || incomingSeedTitle);
          if (incomingSeedBody) {
            setBody((prev) => {
              if (prev.trim()) return prev;
              return incomingSeedBody;
            });
          }
        }
      } finally {
        if (!c) setLoading(false);
      }
    })();
    return () => {
      c = true;
    };
  }, [load, loadTemplates, entryId, incomingVerseRef, incomingVerseText, incomingSeedTitle, incomingSeedBody]);

  const computedBody = useMemo(() => {
    if (kind === "examen") return composeExamenBody(examenPrompts, examenAnswers);
    if (kind === "examination") {
      const main = composeExaminationBody(examinationSections, examinationAnswers);
      const notes = examinationNotes.trim();
      return notes ? `${main}\n\nNotes for confession\n${notes}` : main;
    }
    return body;
  }, [kind, examenPrompts, examenAnswers, examinationSections, examinationAnswers, examinationNotes, body]);

  const save = async () => {
    const finalBody = computedBody;
    if (!finalBody.trim()) {
      Alert.alert("Empty entry", "Please write or check something before saving.");
      return;
    }
    setSaving(true);
    try {
      let structured: Record<string, unknown> | null = null;
      let finalTitle = title.trim();
      if (kind === "examen") {
        structured = { answers: examenAnswers };
        if (!finalTitle) finalTitle = "Daily Examen";
      } else if (kind === "examination") {
        structured = { sections: examinationAnswers, notes: examinationNotes };
        if (!finalTitle) finalTitle = "Examination of Conscience";
      }
      const payload = {
        date,
        title: finalTitle,
        body: finalBody,
        mood: kind === "free" ? mood : null,
        kind,
        structured,
      };
      if (entryId) {
        await api<JournalEntry>(`/journal/${entryId}`, { method: "PUT", body: payload });
      } else {
        await api<JournalEntry>("/journal", { method: "POST", body: payload });
      }
      router.back();
    } catch (e) {
      console.warn("journal save failed", e);
      Alert.alert("Save failed", "Please try again in a moment.");
    } finally {
      setSaving(false);
    }
  };

  const doDelete = async () => {
    if (!entryId) return;
    setDeleting(true);
    try {
      await api<{ ok: boolean }>(`/journal/${entryId}`, { method: "DELETE" });
      router.back();
    } catch (e) {
      console.warn("journal delete failed", e);
      Alert.alert("Delete failed", "Please try again in a moment.");
    } finally {
      setDeleting(false);
    }
  };

  const confirmDelete = async () => {
    const ok = await confirmAction("Delete this entry?", "This cannot be undone.");
    if (ok) doDelete();
  };

  const markConfessed = async () => {
    if (!entryId) {
      Alert.alert("Save first", "Save this examination before marking it confessed.");
      return;
    }
    setMarking(true);
    try {
      const updated = await api<JournalEntry>(`/journal/${entryId}/confess`, { method: "POST" });
      setConfessedAt(updated.confessed_at || new Date().toISOString());
      Alert.alert(
        "Marked confessed",
        "Deo gratias. May the peace of Christ rule in your heart.",
      );
    } catch (e) {
      console.warn("confess mark failed", e);
      Alert.alert("Could not mark", "Please try again.");
    } finally {
      setMarking(false);
    }
  };

  const setExamenAnswer = (key: string, v: string) =>
    setExamenAnswers((a) => ({ ...a, [key]: v }));

  const toggleExamPrompt = (sectionKey: string, idx: number) => {
    setExaminationAnswers((prev) => {
      const sec = { ...(prev[sectionKey] || {}) };
      const cur = sec[idx] || { checked: false };
      sec[idx] = { ...cur, checked: !cur.checked };
      return { ...prev, [sectionKey]: sec };
    });
  };

  const setExamPromptNote = (sectionKey: string, idx: number, note: string) => {
    setExaminationAnswers((prev) => {
      const sec = { ...(prev[sectionKey] || {}) };
      const cur = sec[idx] || { checked: true };
      sec[idx] = { ...cur, note };
      return { ...prev, [sectionKey]: sec };
    });
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="journal-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.headerRow}>
        <Pressable testID="journal-close" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="close" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>{entryId ? "Edit Entry" : "New Entry"}</Text>
        <Pressable
          testID="journal-save"
          onPress={save}
          disabled={saving || loading}
          style={({ pressed }) => pressed && styles.pressed}
        >
          {saving ? <ActivityIndicator color={colors.gold} /> : <Text style={styles.saveText}>Save</Text>}
        </Pressable>
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={20}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="interactive"
        >
          <Text style={styles.dateLine}>{formatLong(parseISO(date))}</Text>
          {lit && (
            <View style={styles.badgeRow}>
              <LiturgicalBadge color={lit.color} label={lit.season} />
              {lit.feast ? <Text style={styles.feastLine}>{lit.feast}</Text> : null}
            </View>
          )}

          {/* Mode switcher */}
          <View style={styles.modeRow} testID="journal-mode-row">
            {MODE_CHIPS.map((m) => {
              const active = kind === m.value;
              return (
                <Pressable
                  key={m.value}
                  testID={`mode-${m.value}`}
                  onPress={() => setKind(m.value)}
                  style={[styles.modeChip, active && styles.modeChipActive]}
                >
                  <Ionicons
                    name={m.icon}
                    size={14}
                    color={active ? colors.gold : colors.textSecondary}
                  />
                  <Text style={[styles.modeText, active && styles.modeTextActive]}>{m.label}</Text>
                </Pressable>
              );
            })}
          </View>

          {confessedAt && kind === "examination" ? (
            <View style={styles.confessedBanner}>
              <Ionicons name="checkmark-circle" size={18} color={colors.liturgical.green} />
              <Text style={styles.confessedText}>
                Confessed on {new Date(confessedAt).toLocaleDateString()}
              </Text>
            </View>
          ) : null}

          {loading ? (
            <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
          ) : kind === "free" ? (
            <>
              <Text style={styles.fieldLabel}>Title (optional)</Text>
              <TextInput
                testID="journal-title"
                style={styles.titleInput}
                placeholder="A name for today's reflection…"
                placeholderTextColor={colors.textMuted}
                value={title}
                onChangeText={setTitle}
                maxLength={120}
              />

              <Text style={styles.fieldLabel}>Movement of the heart</Text>
              <View style={styles.moodRow}>
                {MOODS.map((m) => {
                  const active = mood === m.value;
                  return (
                    <Pressable
                      key={m.value}
                      testID={`mood-${m.value}`}
                      onPress={() => setMood(active ? null : m.value)}
                      style={[styles.moodChip, active && { backgroundColor: m.color, borderColor: m.color }]}
                    >
                      <Ionicons name={m.icon as React.ComponentProps<typeof Ionicons>["name"]} size={14} color={active ? "#fff" : m.color} />
                      <Text style={[styles.moodTextChip, active && styles.moodTextActive]}>{m.label}</Text>
                    </Pressable>
                  );
                })}
              </View>

              <Text style={styles.fieldLabel}>Reflection</Text>
              <TextInput
                testID="journal-body"
                style={styles.bodyInput}
                placeholder="Lord, where did I see You today?…"
                placeholderTextColor={colors.textMuted}
                value={body}
                onChangeText={setBody}
                multiline
                textAlignVertical="top"
              />
            </>
          ) : kind === "examen" ? (
            <>
              <Text style={styles.modeIntro}>
                A short daily Examen in five movements — pray slowly through each step, answering as the
                Lord prompts.
              </Text>
              {examenPrompts.map((p) => (
                <View key={p.key} style={styles.examenBlock} testID={`examen-${p.key}`}>
                  <View style={styles.examenHead}>
                    <Ionicons name={p.icon as React.ComponentProps<typeof Ionicons>["name"]} size={18} color={colors.gold} />
                    <Text style={styles.examenTitle}>{p.title}</Text>
                  </View>
                  <Text style={styles.examenPrompt}>{p.prompt}</Text>
                  <TextInput
                    testID={`examen-input-${p.key}`}
                    style={styles.examenInput}
                    value={examenAnswers[p.key] || ""}
                    onChangeText={(t) => setExamenAnswer(p.key, t)}
                    placeholder="Speak with the Lord…"
                    placeholderTextColor={colors.textMuted}
                    multiline
                    textAlignVertical="top"
                  />
                </View>
              ))}
            </>
          ) : (
            // examination
            <>
              <Text style={styles.modeIntro}>
                A traditional examination of conscience before sacramental confession. Check what
                applies and add a brief note if needed. This is private to you.
              </Text>
              {examinationSections.map((s) => {
                const sec = examinationAnswers[s.key] || {};
                const checkedCount = Object.values(sec).filter((v) => v?.checked).length;
                return (
                  <View key={s.key} style={styles.examBlock} testID={`examination-${s.key}`}>
                    <View style={styles.examHead}>
                      <Text style={styles.examTitle}>{s.title}</Text>
                      {checkedCount > 0 ? (
                        <View style={styles.countPill}>
                          <Text style={styles.countPillText}>{checkedCount}</Text>
                        </View>
                      ) : null}
                    </View>
                    {s.prompts.map((p, idx) => {
                      const it = sec[idx] || { checked: false };
                      return (
                        <View key={idx} style={styles.promptRow}>
                          <Pressable
                            testID={`exam-check-${s.key}-${idx}`}
                            onPress={() => toggleExamPrompt(s.key, idx)}
                            style={styles.checkBtn}
                            hitSlop={6}
                          >
                            <Ionicons
                              name={it.checked ? "checkbox" : "square-outline"}
                              size={22}
                              color={it.checked ? colors.liturgical.purple : colors.textMuted}
                            />
                          </Pressable>
                          <View style={{ flex: 1 }}>
                            <Text style={styles.promptText}>{p}</Text>
                            {it.checked ? (
                              <TextInput
                                testID={`exam-note-${s.key}-${idx}`}
                                style={styles.promptNote}
                                value={it.note || ""}
                                onChangeText={(t) => setExamPromptNote(s.key, idx, t)}
                                placeholder="Note (optional, private)"
                                placeholderTextColor={colors.textMuted}
                                multiline
                              />
                            ) : null}
                          </View>
                        </View>
                      );
                    })}
                  </View>
                );
              })}

              <Text style={styles.fieldLabel}>Notes for confession</Text>
              <TextInput
                testID="examination-notes"
                style={styles.bodyInput}
                value={examinationNotes}
                onChangeText={setExaminationNotes}
                placeholder="Anything else to bring to the sacrament…"
                placeholderTextColor={colors.textMuted}
                multiline
                textAlignVertical="top"
              />

              {entryId ? (
                <Pressable
                  testID="exam-mark-confessed"
                  onPress={markConfessed}
                  disabled={marking}
                  style={({ pressed }) => [styles.confessBtn, pressed && styles.pressed]}
                >
                  {marking ? (
                    <ActivityIndicator color={colors.liturgical.green} />
                  ) : (
                    <>
                      <Ionicons name="checkmark-done" size={16} color={colors.liturgical.green} />
                      <Text style={styles.confessBtnText}>
                        {confessedAt ? "Mark confessed again" : "Mark as confessed"}
                      </Text>
                    </>
                  )}
                </Pressable>
              ) : null}
            </>
          )}

          {entryId && (
            <Pressable
              testID="journal-delete"
              onPress={confirmDelete}
              disabled={deleting}
              style={({ pressed }) => [styles.deleteBtn, pressed && styles.pressed]}
            >
              {deleting ? (
                <ActivityIndicator color={colors.liturgical.red} />
              ) : (
                <>
                  <Ionicons name="trash-outline" size={16} color={colors.liturgical.red} />
                  <Text style={styles.deleteText}>Delete entry</Text>
                </>
              )}
            </Pressable>
          )}
          <View style={{ height: spacing.xxl }} />
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
  dateLine: { fontFamily: fonts.headingBold, fontSize: 26, color: colors.textPrimary },
  badgeRow: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: spacing.sm, marginTop: spacing.sm },
  feastLine: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13, color: colors.liturgical.red },
  modeRow: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.lg },
  modeChip: {
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
  modeChipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  modeText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary },
  modeTextActive: { color: colors.gold },
  modeIntro: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textSecondary,
    fontSize: 14,
    marginTop: spacing.md,
    lineHeight: 22,
  },
  fieldLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.5,
    color: colors.gold,
    marginTop: spacing.lg,
  },
  titleInput: {
    fontFamily: fonts.headingSemi,
    fontSize: 20,
    color: colors.textPrimary,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  moodRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.sm },
  moodChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  moodTextChip: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary },
  moodTextActive: { color: "#fff" },
  bodyInput: {
    minHeight: 220,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.md,
    fontFamily: fonts.bodyRegular,
    fontSize: 16,
    color: colors.textPrimary,
    lineHeight: 24,
    marginTop: spacing.sm,
    ...shadow.card,
  },
  examenBlock: {
    marginTop: spacing.md,
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  examenHead: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  examenTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  examenPrompt: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 22,
    marginTop: 4,
  },
  examenInput: {
    marginTop: spacing.sm,
    minHeight: 80,
    backgroundColor: colors.background,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: 10,
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textPrimary,
    lineHeight: 22,
  },
  examBlock: {
    marginTop: spacing.md,
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  examHead: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.sm },
  examTitle: { fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary, flex: 1 },
  countPill: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: radius.round,
    backgroundColor: colors.liturgical.purple,
  },
  countPillText: { fontFamily: fonts.uiSemi, color: "#fff", fontSize: 11 },
  promptRow: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm, alignItems: "flex-start" },
  checkBtn: { paddingTop: 2 },
  promptText: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary, lineHeight: 20 },
  promptNote: {
    marginTop: 6,
    backgroundColor: colors.background,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: 8,
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textPrimary,
    minHeight: 36,
  },
  confessBtn: {
    marginTop: spacing.lg,
    paddingVertical: 12,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.liturgical.green,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
  },
  confessBtnText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.liturgical.green },
  confessedBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: "#E8F2EB",
    padding: spacing.sm,
    borderRadius: radius.md,
    marginTop: spacing.md,
  },
  confessedText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.liturgical.green },
  deleteBtn: {
    marginTop: spacing.xl,
    paddingVertical: 12,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.liturgical.red,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    alignSelf: "center",
  },
  deleteText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.liturgical.red },
  pressed: { opacity: 0.7 },
});

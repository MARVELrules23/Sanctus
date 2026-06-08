import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
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

import { api, JournalEntry, JournalMood, LiturgicalDay } from "@/src/api";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import { MOODS } from "@/src/journal-mood";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { formatLong, parseISO, todayISO } from "@/src/date-utils";

export default function JournalScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ date?: string; entry?: string }>();
  const initialDate = typeof params.date === "string" ? params.date : todayISO();
  const entryId = typeof params.entry === "string" ? params.entry : null;

  const [date, setDate] = useState(initialDate);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [mood, setMood] = useState<JournalMood>(null);
  const [lit, setLit] = useState<LiturgicalDay | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

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
      } catch (err) {
        console.warn("failed to load entry", err);
      }
    }
  }, [date, entryId]);

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

  const save = async () => {
    if (!body.trim()) {
      Alert.alert("Empty entry", "Please write something before saving.");
      return;
    }
    setSaving(true);
    try {
      const payload = { date, title: title.trim(), body: body.trim(), mood };
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

  const confirmDelete = () => {
    Alert.alert(
      "Delete this entry?",
      "This cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        { text: "Delete", style: "destructive", onPress: doDelete },
      ],
      { cancelable: true },
    );
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

          {loading ? (
            <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
          ) : (
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
                      <Text style={[styles.moodText, active && styles.moodTextActive]}>{m.label}</Text>
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
            </>
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
  moodText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary },
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

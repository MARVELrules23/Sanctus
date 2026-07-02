import React, { useState } from "react";
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
import { createMyDevotion } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

const SUGGESTIONS = [
  "The Blessed Virgin Mary",
  "St. Michael the Archangel",
  "My Guardian Angel",
  "St. Joseph",
  "The Sacred Heart of Jesus",
  "St. Thérèse of Lisieux",
];

export default function NewDevotional() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [title, setTitle] = useState("");
  const [saint, setSaint] = useState("");
  const [intro, setIntro] = useState("");
  const [practices, setPractices] = useState<string[]>([]);
  const [practice, setPractice] = useState("");
  const [saving, setSaving] = useState(false);

  const canSave = title.trim().length > 0 && saint.trim().length > 0 && practices.length > 0 && !saving;

  const addPractice = () => {
    const t = practice.trim();
    if (!t) return;
    setPractices((p) => [...p, t]);
    setPractice("");
  };

  const save = async () => {
    if (!canSave) return;
    setSaving(true);
    try {
      await createMyDevotion({
        title: title.trim(),
        saint_name: saint.trim(),
        intro: intro.trim(),
        practices,
      });
      router.back();
    } catch {
      setSaving(false);
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.background, paddingTop: insets.top }}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="nd-back" onPress={() => router.back()} hitSlop={12} style={styles.iconBtn}>
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
        </Pressable>
        <Text style={styles.headerTitle}>New Devotional</Text>
        <Pressable testID="nd-save" onPress={save} disabled={!canSave} style={[styles.saveBtn, !canSave && { opacity: 0.4 }]}>
          {saving ? <ActivityIndicator color={colors.surface} size="small" /> : <Text style={styles.saveText}>Save</Text>}
        </Pressable>
      </View>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: 60 }}>
          <Text style={styles.label}>To which saint or angel?</Text>
          <TextInput
            testID="nd-saint"
            value={saint}
            onChangeText={setSaint}
            placeholder="Type any saint or angel…"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
          />
          <View style={styles.suggestRow}>
            {SUGGESTIONS.map((s) => (
              <Pressable key={s} onPress={() => setSaint(s)} style={styles.suggestChip}>
                <Text style={styles.suggestText}>{s}</Text>
              </Pressable>
            ))}
          </View>

          <Text style={styles.label}>Title</Text>
          <TextInput
            testID="nd-title"
            value={title}
            onChangeText={setTitle}
            placeholder="e.g. My daily devotion to St. Joseph"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
          />

          <Text style={styles.label}>Intro (optional)</Text>
          <TextInput
            testID="nd-intro"
            value={intro}
            onChangeText={setIntro}
            placeholder="Why this devotion matters to you…"
            placeholderTextColor={colors.textMuted}
            multiline
            style={[styles.input, { minHeight: 90, textAlignVertical: "top", lineHeight: 22 }]}
          />

          <Text style={styles.label}>Practices / criteria</Text>
          {practices.map((p, i) => (
            <View key={i} style={styles.itemRow}>
              <Ionicons name="flower" size={14} color={colors.gold} />
              <Text style={styles.itemText}>{p}</Text>
              <Pressable testID={`nd-remove-${i}`} onPress={() => setPractices((arr) => arr.filter((_, j) => j !== i))} hitSlop={8}>
                <Ionicons name="close-circle" size={18} color={colors.textMuted} />
              </Pressable>
            </View>
          ))}
          <View style={styles.addRow}>
            <TextInput
              testID="nd-practice"
              value={practice}
              onChangeText={setPractice}
              placeholder="Add a practice (e.g. Pray a daily Rosary)"
              placeholderTextColor={colors.textMuted}
              style={[styles.input, { flex: 1 }]}
              onSubmitEditing={addPractice}
            />
            <Pressable testID="nd-add-practice" onPress={addPractice} style={styles.addBtn}>
              <Ionicons name="add" size={22} color={colors.surface} />
            </Pressable>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  iconBtn: { padding: 4 },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  saveBtn: { backgroundColor: colors.gold, paddingHorizontal: 16, paddingVertical: 7, borderRadius: radius.round, minWidth: 60, alignItems: "center" },
  saveText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.surface },
  label: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary, marginBottom: spacing.sm, marginTop: spacing.sm },
  input: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft, borderRadius: radius.md, paddingHorizontal: spacing.md, paddingVertical: 12, fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary },
  suggestRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: spacing.sm },
  suggestChip: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surface },
  suggestText: { fontFamily: fonts.uiRegular, fontSize: 12, color: colors.textSecondary },
  itemRow: { flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft, borderRadius: radius.md, paddingHorizontal: spacing.md, paddingVertical: 10, marginBottom: 6 },
  itemText: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary },
  addRow: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: spacing.sm },
  addBtn: { backgroundColor: colors.gold, width: 44, height: 44, borderRadius: radius.md, alignItems: "center", justifyContent: "center" },
});

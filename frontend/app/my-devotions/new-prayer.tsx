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
import { createMyPrayer } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

export default function NewPrayer() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [saving, setSaving] = useState(false);
  const canSave = title.trim().length > 0 && body.trim().length > 0 && !saving;

  const save = async () => {
    if (!canSave) return;
    setSaving(true);
    try {
      await createMyPrayer({ title: title.trim(), body: body.trim() });
      router.back();
    } catch {
      setSaving(false);
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.background, paddingTop: insets.top }}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="np-back" onPress={() => router.back()} hitSlop={12} style={styles.iconBtn}>
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
        </Pressable>
        <Text style={styles.headerTitle}>Write a Prayer</Text>
        <Pressable testID="np-save" onPress={save} disabled={!canSave} style={[styles.saveBtn, !canSave && { opacity: 0.4 }]}>
          {saving ? <ActivityIndicator color={colors.surface} size="small" /> : <Text style={styles.saveText}>Save</Text>}
        </Pressable>
      </View>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: 60 }}>
          <Text style={styles.label}>Title</Text>
          <TextInput
            testID="np-title"
            value={title}
            onChangeText={setTitle}
            placeholder="e.g. A prayer for patience"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
          />
          <Text style={styles.label}>Prayer</Text>
          <TextInput
            testID="np-body"
            value={body}
            onChangeText={setBody}
            placeholder="Write your prayer here…"
            placeholderTextColor={colors.textMuted}
            multiline
            style={[styles.input, styles.bodyInput]}
          />
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
  bodyInput: { minHeight: 220, textAlignVertical: "top", lineHeight: 24 },
});

import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { api } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

type Claim = {
  claim_id: string;
  title: string;
  summary: string;
  type: string;
  verdict: string;
  location?: string | null;
  reported_year?: string | null;
  source_name?: string | null;
  source_url: string;
  state: string;
  origin: string;
};

const VERDICTS: { key: string; label: string; color: string }[] = [
  { key: "reported", label: "Reported", color: "#5C5C60" },
  { key: "investigating", label: "Investigating", color: "#C5A059" },
  { key: "approved", label: "Approved", color: "#2A5A3B" },
  { key: "not_supernatural", label: "Not Supernatural", color: "#9E1B1B" },
];

export default function AdminMiraclesScreen() {
  const router = useRouter();
  const [items, setItems] = useState<Claim[] | null>(null);
  const [generating, setGenerating] = useState(false);
  const [focus, setFocus] = useState("");

  const load = useCallback(async () => {
    try {
      const res = await api<{ items: Claim[] }>("/miracles/admin/all");
      setItems(res.items || []);
    } catch {
      setItems([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const generate = async () => {
    setGenerating(true);
    try {
      const res = await api<{ created: number }>("/miracles/admin/generate", {
        method: "POST",
        body: { focus: focus.trim() || undefined },
      });
      Alert.alert("AI draft complete", `${res.created} new draft(s) added for review.`);
      setFocus("");
      await load();
    } catch (e: any) {
      Alert.alert("Generation failed", String(e?.message || e));
    } finally {
      setGenerating(false);
    }
  };

  const setVerdict = async (id: string, verdict: string) => {
    await api(`/miracles/admin/${id}`, { method: "PATCH", body: { verdict } });
    setItems((prev) => prev?.map((c) => (c.claim_id === id ? { ...c, verdict } : c)) ?? null);
  };

  const togglePublish = async (c: Claim) => {
    const action = c.state === "published" ? "unpublish" : "publish";
    await api(`/miracles/admin/${c.claim_id}/${action}`, { method: "POST" });
    setItems((prev) =>
      prev?.map((x) => (x.claim_id === c.claim_id ? { ...x, state: action === "publish" ? "published" : "draft" } : x)) ?? null,
    );
  };

  const remove = (c: Claim) => {
    Alert.alert("Delete claim?", c.title, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          await api(`/miracles/admin/${c.claim_id}`, { method: "DELETE" });
          setItems((prev) => prev?.filter((x) => x.claim_id !== c.claim_id) ?? null);
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10}>
          <Ionicons name="chevron-back" size={24} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Miracles · Review</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: spacing.md, paddingBottom: spacing.xxl }}>
        <View style={styles.genBox}>
          <Text style={styles.genTitle}>Draft from the web with AI</Text>
          <Text style={styles.genHint}>
            Claude searches the live web for recent reported Catholic miracle claims and saves them as
            drafts for your review. Nothing publishes automatically.
          </Text>
          <TextInput
            value={focus}
            onChangeText={setFocus}
            placeholder="Optional focus (e.g. Eucharistic miracles 2026)"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
          />
          <Pressable
            onPress={generate}
            disabled={generating}
            style={({ pressed }) => [styles.genBtn, (pressed || generating) && { opacity: 0.7 }]}
            testID="miracles-generate"
          >
            {generating ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <Ionicons name="sparkles" size={16} color="#fff" />
                <Text style={styles.genBtnText}>Generate drafts</Text>
              </>
            )}
          </Pressable>
          {generating ? <Text style={styles.genHint}>Searching the web… this can take ~30s.</Text> : null}
        </View>

        {items === null ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.lg }} />
        ) : (
          items.map((c) => (
            <View key={c.claim_id} style={styles.card}>
              <View style={styles.rowBetween}>
                <View style={[styles.stateChip, { backgroundColor: c.state === "published" ? "#2A5A3B" : "#8A8A8E" }]}>
                  <Text style={styles.stateChipText}>{c.state === "published" ? "PUBLISHED" : "DRAFT"}</Text>
                </View>
                <Text style={styles.origin}>{c.origin === "ai" ? "AI" : c.origin === "seed" ? "Seed" : "Admin"}</Text>
              </View>
              <Text style={styles.title}>{c.title}</Text>
              <Text style={styles.metaLine}>
                {[c.type, c.location, c.reported_year].filter(Boolean).join(" · ")}
              </Text>
              <Text style={styles.summary} numberOfLines={4}>{c.summary}</Text>

              <Text style={styles.fieldLabel}>Church status</Text>
              <View style={styles.verdictRow}>
                {VERDICTS.map((v) => {
                  const sel = c.verdict === v.key;
                  return (
                    <Pressable
                      key={v.key}
                      onPress={() => setVerdict(c.claim_id, v.key)}
                      style={[styles.verdictChip, { borderColor: v.color }, sel && { backgroundColor: v.color }]}
                    >
                      <Text style={[styles.verdictChipText, { color: sel ? "#fff" : v.color }]}>{v.label}</Text>
                    </Pressable>
                  );
                })}
              </View>

              <View style={styles.actions}>
                <Pressable onPress={() => togglePublish(c)} style={[styles.actBtn, { backgroundColor: colors.primary }]}>
                  <Ionicons name={c.state === "published" ? "eye-off-outline" : "checkmark-done-outline"} size={15} color="#fff" />
                  <Text style={styles.actText}>{c.state === "published" ? "Unpublish" : "Publish"}</Text>
                </Pressable>
                <Pressable onPress={() => remove(c)} style={[styles.actBtn, { backgroundColor: "#9E1B1B" }]}>
                  <Ionicons name="trash-outline" size={15} color="#fff" />
                  <Text style={styles.actText}>Delete</Text>
                </Pressable>
              </View>
            </View>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
    backgroundColor: colors.surface,
  },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 20, color: colors.primary },
  genBox: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: StyleSheet.hairlineWidth, borderColor: colors.border, padding: spacing.md, marginBottom: spacing.md },
  genTitle: { fontFamily: fonts.headingSemi, fontSize: 17, color: colors.primary },
  genHint: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textSecondary, marginTop: 4, lineHeight: 18 },
  input: { borderWidth: StyleSheet.hairlineWidth, borderColor: colors.border, borderRadius: radius.md, padding: 10, marginTop: spacing.sm, fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary },
  genBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, backgroundColor: colors.gold, borderRadius: radius.md, paddingVertical: 11, marginTop: spacing.sm },
  genBtnText: { fontFamily: fonts.uiSemi, fontSize: 14, color: "#fff" },
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: StyleSheet.hairlineWidth, borderColor: colors.border, padding: spacing.md, marginBottom: spacing.md },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  stateChip: { borderRadius: radius.round, paddingHorizontal: 8, paddingVertical: 3 },
  stateChipText: { fontFamily: fonts.uiSemi, fontSize: 10, color: "#fff", letterSpacing: 0.5 },
  origin: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted },
  title: { fontFamily: fonts.headingSemi, fontSize: 17, color: colors.primary, lineHeight: 21 },
  metaLine: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textMuted, marginTop: 2 },
  summary: { fontFamily: fonts.bodyRegular, fontSize: 13.5, color: colors.textPrimary, lineHeight: 20, marginTop: 6 },
  fieldLabel: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary, marginTop: spacing.sm, marginBottom: 6 },
  verdictRow: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  verdictChip: { borderWidth: 1, borderRadius: radius.round, paddingHorizontal: 10, paddingVertical: 5 },
  verdictChipText: { fontFamily: fonts.uiSemi, fontSize: 11.5 },
  actions: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.md },
  actBtn: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 5, borderRadius: radius.md, paddingVertical: 9 },
  actText: { fontFamily: fonts.uiSemi, fontSize: 13, color: "#fff" },
});

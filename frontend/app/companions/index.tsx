import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { listCompanions, selectCompanion, CompanionListItem } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

export default function CompanionsHub() {
  const router = useRouter();
  const [items, setItems] = useState<CompanionListItem[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [vocation, setVocation] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string>("");

  const load = useCallback(async () => {
    try {
      const r = await listCompanions();
      setItems(r.companions);
      setSelected(r.selected);
      setVocation(r.vocation_companion);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggle = async (slug: string) => {
    const isSel = selected.includes(slug);
    if (!isSel && selected.length >= 3) {
      Alert.alert("Up to 3 companions", "You can walk with up to 3 daily companions. Remove one to add another.");
      return;
    }
    setBusy(slug);
    try {
      const r = await selectCompanion(slug, isSel ? "remove" : "add");
      setSelected(r.selected);
    } catch (e: any) {
      Alert.alert("Could not update", e?.message || "Please try again.");
    } finally {
      setBusy("");
    }
  };

  const vocationItem = items.find((i) => i.slug === vocation);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="companions-hub">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="companions-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Daily Companions</Text>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <Text style={styles.intro}>
            Choose up to 3 saints to walk with each day, alongside your vocation companion. Tap a name to enter their space.
          </Text>
          <Text style={styles.counter}>{selected.length} / 3 chosen</Text>

          {vocationItem ? (
            <Pressable
              testID="companions-vocation-card"
              onPress={() => router.push(`/companion/${vocationItem.slug}` as any)}
              style={({ pressed }) => [styles.card, styles.vocationCard, pressed && { opacity: 0.9 }]}
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.vocTag}>YOUR VOCATION COMPANION</Text>
                <Text style={styles.name}>{vocationItem.name}</Text>
                <Text style={styles.tagline} numberOfLines={2}>{vocationItem.tagline}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={colors.gold} />
            </Pressable>
          ) : null}

          {items.filter((i) => !i.is_vocation_companion).map((c) => {
            const isSel = selected.includes(c.slug);
            return (
              <View key={c.slug} style={[styles.card, isSel && styles.cardSel]}>
                <Pressable
                  testID={`companion-card-${c.slug}`}
                  onPress={() => router.push(`/companion/${c.slug}` as any)}
                  style={styles.cardMain}
                >
                  <View style={{ flex: 1 }}>
                    <View style={styles.nameRow}>
                      <Text style={styles.name}>{c.name}</Text>
                      {c.linked ? <Ionicons name="link-outline" size={13} color={colors.textMuted} /> : null}
                    </View>
                    {c.feast ? <Text style={styles.feast}>Feast · {c.feast}</Text> : null}
                    <Text style={styles.tagline} numberOfLines={2}>{c.tagline}</Text>
                  </View>
                  <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
                </Pressable>
                <Pressable
                  testID={`companion-toggle-${c.slug}`}
                  onPress={() => toggle(c.slug)}
                  disabled={busy === c.slug}
                  style={({ pressed }) => [styles.selectBtn, isSel && styles.selectBtnOn, pressed && { opacity: 0.85 }]}
                >
                  {busy === c.slug ? (
                    <ActivityIndicator size="small" color={isSel ? "#FFF8EA" : colors.primary} />
                  ) : (
                    <>
                      <Ionicons name={isSel ? "checkmark-circle" : "add-circle-outline"} size={16} color={isSel ? "#FFF8EA" : colors.primary} />
                      <Text style={[styles.selectText, isSel && { color: "#FFF8EA" }]}>{isSel ? "Walking with" : "Add"}</Text>
                    </>
                  )}
                </Pressable>
              </View>
            );
          })}
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingSemi, fontSize: 18, color: colors.primary },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  scroll: { padding: spacing.lg },
  intro: { fontFamily: fonts.bodyRegular, fontSize: 14.5, color: colors.textSecondary, lineHeight: 22 },
  counter: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold, marginTop: spacing.sm, marginBottom: spacing.md },
  card: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft, borderRadius: radius.lg, padding: spacing.md, marginBottom: spacing.sm },
  cardSel: { borderColor: colors.gold, backgroundColor: "#FBF4DF" },
  vocationCard: { flexDirection: "row", alignItems: "center", borderColor: colors.gold, backgroundColor: "#FAF3E2" },
  vocTag: { fontFamily: fonts.uiSemi, fontSize: 10.5, letterSpacing: 1.2, color: colors.gold },
  cardMain: { flexDirection: "row", alignItems: "center", gap: 8 },
  nameRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  name: { fontFamily: fonts.headingSemi, fontSize: 17, color: colors.primary },
  feast: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textMuted, marginTop: 1 },
  tagline: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, lineHeight: 19, marginTop: 3 },
  selectBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, marginTop: spacing.sm, paddingVertical: 8, borderRadius: radius.md, borderWidth: 1, borderColor: colors.gold, backgroundColor: "transparent" },
  selectBtnOn: { backgroundColor: colors.gold, borderColor: colors.gold },
  selectText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.primary },
});

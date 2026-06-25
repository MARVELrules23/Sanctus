import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { getWorldIssues, WorldIssue } from "@/src/api";
import { useI18n } from "@/src/i18n";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

export default function InTheWorldScreen() {
  const router = useRouter();
  const { lang } = useI18n();
  const es = lang === "es";
  const [items, setItems] = useState<WorldIssue[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await getWorldIssues();
      setItems(r.items);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="in-the-world-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>{es ? "En el Mundo" : "In the World"}</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.intro}>
          <Text style={styles.eyebrow}>FIDES ET RATIO</Text>
          <Text style={styles.introTitle}>{es ? "La fe en la vida pública" : "Faith in public life"}</Text>
          <Text style={styles.introBody}>
            {es
              ? "Los grandes temas de la vida pública a la luz de la Doctrina Social de la Iglesia — sin partidismo, pero con claridad donde la Iglesia enseña con firmeza."
              : "The great questions of public life through the Church's Social Teaching — non-partisan, yet clear where the Church teaches definitively."}
          </Text>
        </View>

        {loading ? (
          <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
        ) : (
          items.map((it) => (
            <Pressable
              key={it.slug}
              testID={`world-issue-${it.slug}`}
              onPress={() => router.push(`/in-the-world/${it.slug}`)}
              style={({ pressed }) => [styles.row, { borderLeftColor: it.accent }, pressed && styles.pressed]}
            >
              <View style={[styles.iconWrap, { backgroundColor: it.accent + "1A" }]}>
                <Ionicons name={it.icon as keyof typeof Ionicons.glyphMap} size={22} color={it.accent} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.rowTitle}>{it.title}</Text>
                <Text style={styles.rowBlurb}>{it.blurb}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
            </Pressable>
          ))
        )}
        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft, gap: spacing.md,
  },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingBold, fontSize: 18, color: colors.textPrimary },
  scroll: { padding: spacing.lg, gap: spacing.sm },
  center: { paddingVertical: spacing.xl, alignItems: "center" },
  intro: { marginBottom: spacing.sm },
  eyebrow: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 2, color: colors.gold },
  introTitle: { fontFamily: fonts.headingBold, fontSize: 24, color: colors.textPrimary, marginTop: 4 },
  introBody: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textSecondary, lineHeight: 23, marginTop: 6 },
  row: {
    flexDirection: "row", alignItems: "center", gap: spacing.md, padding: spacing.md,
    backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.borderSoft,
    borderLeftWidth: 4, ...shadow.card,
  },
  iconWrap: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center" },
  rowTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  rowBlurb: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, lineHeight: 19, marginTop: 2 },
  pressed: { opacity: 0.7 },
});

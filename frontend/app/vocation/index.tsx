import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { api, getVocationGuide, VocationGuide } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

export default function VocationScreen() {
  const router = useRouter();
  const [guide, setGuide] = useState<VocationGuide | null>(null);
  const [loading, setLoading] = useState(true);
  const [companion, setCompanion] = useState<string>("");

  const load = useCallback(async () => {
    try {
      const g = await getVocationGuide();
      setGuide(g);
      setCompanion(g.companion_saint || "");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const chooseCompanion = async (slug: string) => {
    setCompanion(slug);
    try {
      // Merge into existing preferences so nothing else is overwritten.
      const prefs = await api<Record<string, any>>("/preferences");
      await api("/preferences", { method: "PUT", body: { ...prefs, companion_saint: slug } });
    } catch {
      /* ignore */
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="vocation-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="vocation-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.headerTitle}>{guide?.label || "Your Vocation"}</Text>
        </View>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      ) : !guide?.has_vocation ? (
        <View style={styles.center}>
          <Text style={styles.empty}>Choose your path in Profile to receive a tailored guide.</Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          {guide.state ? (
            <View style={styles.stateTag}>
              <Ionicons name={guide.state === "discerning" ? "compass-outline" : "home-outline"} size={13} color={colors.gold} />
              <Text style={styles.stateTagText}>{guide.state === "discerning" ? "Discerning" : "Living"}</Text>
            </View>
          ) : null}
          {guide.intro ? <Text style={styles.intro}>{guide.intro}</Text> : null}

          {/* Morning prayer */}
          {guide.morning_prayer ? (
            <View style={styles.prayerCard} testID="vocation-prayer">
              <View style={styles.cardHead}>
                <Ionicons name="sunny-outline" size={16} color={colors.gold} />
                <Text style={styles.cardHeadText}>Morning Prayer</Text>
              </View>
              <Text style={styles.prayerTitle}>{guide.morning_prayer.title}</Text>
              <Text style={styles.prayerBody}>{guide.morning_prayer.body}</Text>
            </View>
          ) : null}

          {/* Companions */}
          {guide.companions && guide.companions.length > 0 ? (
            <>
              <Text style={styles.section}>Choose a companion to walk with</Text>
              {guide.companions.map((c) => {
                const sel = companion === c.slug;
                return (
                  <Pressable
                    key={c.slug}
                    testID={`vocation-companion-${c.slug}`}
                    onPress={() => chooseCompanion(c.slug)}
                    style={[styles.companion, sel && styles.companionSel]}
                  >
                    <Ionicons
                      name={sel ? "checkmark-circle" : "ellipse-outline"}
                      size={20}
                      color={sel ? colors.gold : colors.textMuted}
                    />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.companionName}>{c.name}</Text>
                      <Text style={styles.companionWhy}>{c.why}</Text>
                      {sel ? <Text style={styles.companionPrayer}>“{c.prayer}”</Text> : null}
                      {sel && c.devotions && c.devotions.length > 0 ? (
                        <View style={styles.devBox} testID={`companion-devotions-${c.slug}`}>
                          <Text style={styles.devHeader}>Ways to grow closer to {c.name}</Text>
                          {c.devotions.map((d, i) => (
                            <View key={i} style={styles.devItem}>
                              <Ionicons name="leaf-outline" size={13} color={colors.goldDark} style={{ marginTop: 2 }} />
                              <View style={{ flex: 1 }}>
                                <Text style={styles.devTitle}>{d.title}</Text>
                                <Text style={styles.devBody}>{d.body}</Text>
                              </View>
                            </View>
                          ))}
                        </View>
                      ) : null}
                      <Pressable
                        testID={`vocation-open-companion-${c.slug}`}
                        onPress={() => router.push(`/companion/${c.slug}` as any)}
                        style={styles.visitRow}
                      >
                        <Text style={styles.visitText}>Open {c.name}'s space</Text>
                        <Ionicons name="arrow-forward-circle" size={20} color={colors.gold} />
                      </Pressable>
                    </View>
                  </Pressable>
                );
              })}
            </>
          ) : null}

          {/* Ideas to draw closer */}
          {guide.ideas && guide.ideas.length > 0 ? (
            <View style={styles.ideaBox} testID="vocation-ideas">
              <View style={styles.cardHead}>
                <Ionicons name="flame-outline" size={16} color={colors.gold} />
                <Text style={styles.cardHeadText}>Draw closer to your vocation</Text>
              </View>
              {guide.ideas.map((it, i) => (
                <View key={i} style={styles.item}>
                  <Text style={styles.itemTitle}>{it.title}</Text>
                  <Text style={styles.itemBody}>{it.body}</Text>
                </View>
              ))}

              {/* Nested traditions box */}
              {guide.traditions && guide.traditions.length > 0 ? (
                <View style={styles.tradBox} testID="vocation-traditions">
                  <View style={styles.cardHead}>
                    <Ionicons name="ribbon-outline" size={16} color={colors.gold} />
                    <Text style={styles.cardHeadText}>Traditions to build as you grow</Text>
                  </View>
                  {guide.traditions.map((it, i) => (
                    <View key={i} style={styles.item}>
                      <Text style={styles.itemTitle}>{it.title}</Text>
                      <Text style={styles.itemBody}>{it.body}</Text>
                    </View>
                  ))}
                </View>
              ) : null}
            </View>
          ) : null}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row", alignItems: "center",
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
    borderBottomWidth: 1, borderBottomColor: colors.borderSoft,
  },
  headerTitleWrap: { flex: 1, alignItems: "center" },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.primary },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.lg },
  empty: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, textAlign: "center" },
  scroll: { padding: spacing.md, paddingBottom: spacing.xl },
  stateTag: { flexDirection: "row", alignItems: "center", gap: 5, alignSelf: "flex-start", marginBottom: spacing.sm },
  stateTagText: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 0.5, textTransform: "uppercase", color: colors.textSecondary },
  intro: { fontFamily: fonts.bodyItalic, fontSize: 15, color: colors.textSecondary, lineHeight: 23, marginBottom: spacing.md },
  prayerCard: {
    backgroundColor: colors.surfaceDark, borderRadius: radius.lg, padding: spacing.lg, marginBottom: spacing.lg,
  },
  cardHead: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 8 },
  cardHeadText: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 0.6, textTransform: "uppercase", color: colors.gold },
  prayerTitle: { fontFamily: fonts.headingSemi, fontSize: 19, color: "#FBF6E9", marginBottom: 8 },
  prayerBody: { fontFamily: fonts.bodyRegular, fontSize: 15, color: "#E9E2D0", lineHeight: 24, fontStyle: "italic" },
  section: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.primary, marginBottom: spacing.sm },
  companion: {
    flexDirection: "row", gap: spacing.sm, alignItems: "flex-start",
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft,
    borderRadius: radius.md, padding: spacing.md, marginBottom: spacing.sm,
  },
  companionSel: { borderColor: colors.gold, backgroundColor: "#FBF4DF" },
  companionName: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.primary },
  companionWhy: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, marginTop: 2, lineHeight: 19 },
  companionPrayer: { fontFamily: fonts.bodyItalic, fontSize: 13.5, color: colors.goldDark, marginTop: 6, fontStyle: "italic" },
  devBox: { marginTop: 10, borderTopWidth: 1, borderTopColor: "#EBDDB4", paddingTop: 8, gap: 8 },
  devHeader: { fontFamily: fonts.uiSemi, fontSize: 11.5, letterSpacing: 0.4, textTransform: "uppercase", color: colors.goldDark, marginBottom: 2 },
  devItem: { flexDirection: "row", gap: 6, alignItems: "flex-start" },
  devTitle: { fontFamily: fonts.uiSemi, fontSize: 13.5, color: colors.primary },
  devBody: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, lineHeight: 19, marginTop: 1 },
  visitRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 10, paddingTop: 8, borderTopWidth: 1, borderTopColor: "#EBDDB4" },
  visitText: { fontFamily: fonts.uiSemi, fontSize: 13.5, color: colors.gold },
  ideaBox: {
    marginTop: spacing.lg, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft,
    borderRadius: radius.lg, padding: spacing.md,
  },
  item: { marginBottom: spacing.md },
  itemTitle: { fontFamily: fonts.uiSemi, fontSize: 15, color: colors.primary, marginBottom: 2 },
  itemBody: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, lineHeight: 21 },
  tradBox: {
    marginTop: spacing.sm, backgroundColor: "#FBF4DF", borderWidth: 1, borderColor: "#EBDDB4",
    borderRadius: radius.md, padding: spacing.md,
  },
});

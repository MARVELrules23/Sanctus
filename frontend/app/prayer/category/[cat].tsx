/**
 * Prayer category screen — opens from a category "box" on the Prayer hub and
 * lists every prayer within that group (e.g. all Chaplets, all Marian prayers,
 * all Litanies, Mass & Communion, etc). Each row opens the prayer runner.
 */
import React, { useMemo } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { CHAPLETS, CHAPLET_ORDER } from "@/src/prayers/chaplets";
import { DEVOTIONS, DEVOTION_CATEGORIES } from "@/src/prayers/devotions";
import { useI18n } from "@/src/i18n";
import { useTranslator } from "@/src/translate";

type Row = { key: string; title: string; subtitle: string; meta: string; color: string; icon: string };

const CATEGORY_META: Record<string, { label: string; blurb: string }> = {
  chaplets: { label: "Chaplets", blurb: "Prayed on beads — a rhythm of repetition that quiets the heart." },
  marian: { label: "Marian Prayers", blurb: "Prayers to Our Lady, the first and surest path to her Son." },
  litany: { label: "Litanies", blurb: "Call-and-response prayers invoking heaven's help, title by title." },
  stations: { label: "Stations of the Cross", blurb: "Walk the way of the Cross with Christ to Calvary." },
  mass: { label: "Mass & Communion", blurb: "Prepare for and give thanks after the Holy Sacrifice." },
  devotional: { label: "Devotions & Acts", blurb: "Daily acts of faith, protection, and praise." },
  seasonal: { label: "Seasonal & Feast Day", blurb: "Prayers that move with the rhythm of the Church's year." },
};

export default function PrayerCategoryScreen() {
  const router = useRouter();
  const { lang } = useI18n();
  const { cat } = useLocalSearchParams<{ cat: string }>();
  const catKey = String(cat || "");

  const rows: Row[] = useMemo(() => {
    if (catKey === "chaplets") {
      return CHAPLET_ORDER.map((k) => {
        const c = CHAPLETS[k];
        return { key: k, title: c.title, subtitle: c.subtitle, meta: c.duration, color: c.color, icon: c.icon };
      });
    }
    const group = DEVOTION_CATEGORIES.find((g) => g.key === catKey);
    if (!group) return [];
    return group.keys
      .map((k) => DEVOTIONS[k])
      .filter(Boolean)
      .map((d) => ({ key: d.key, title: d.title, subtitle: d.subtitle, meta: d.duration, color: d.color, icon: d.icon }));
  }, [catKey]);

  const meta = CATEGORY_META[catKey] || { label: "Prayers", blurb: "" };

  const allStrings = useMemo(() => {
    const a: string[] = [meta.label, meta.blurb];
    rows.forEach((r) => a.push(r.title, r.subtitle, r.meta));
    return a;
  }, [rows, meta.label, meta.blurb]);
  const { tr } = useTranslator(allStrings);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={`prayer-category-${catKey}`}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="prayer-category-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle} numberOfLines={1}>{tr(meta.label)}</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {meta.blurb ? <Text style={styles.blurb}>{tr(meta.blurb)}</Text> : null}

        {rows.map((r) => (
          <Pressable
            key={r.key}
            testID={`prayer-card-${r.key}`}
            onPress={() => router.push({ pathname: "/prayer/[kind]", params: { kind: r.key } })}
            style={({ pressed }) => [styles.card, pressed && styles.pressed]}
          >
            <View style={[styles.iconWrap, { backgroundColor: r.color }]}>
              <Ionicons name={r.icon as any} size={22} color={"#FAF9F6"} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.cardTitle}>{tr(r.title)}</Text>
              <Text style={styles.cardSub}>{tr(r.subtitle)}</Text>
              <Text style={styles.cardMeta}>{tr(r.meta)}</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          </Pressable>
        ))}

        {rows.length === 0 ? (
          <Text style={styles.empty}>{lang === "es" ? "No hay oraciones aquí." : lang === "it" ? "Nessuna preghiera qui." : "No prayers here yet."}</Text>
        ) : null}
        <View style={{ height: spacing.xxl }} />
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
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary, flex: 1, textAlign: "center", marginHorizontal: spacing.sm },
  scroll: { padding: spacing.lg },
  blurb: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, lineHeight: 22, marginBottom: spacing.lg },
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  iconWrap: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center" },
  cardTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary, flexShrink: 1 },
  cardSub: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  cardMeta: { fontFamily: fonts.uiMedium, fontSize: 10, color: colors.gold, marginTop: 4, letterSpacing: 1.4 },
  empty: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 14, color: colors.textMuted, textAlign: "center", marginTop: spacing.xl },
  pressed: { opacity: 0.7 },
});

import React, { useMemo } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { mysteryForDate, MYSTERY_SETS, MysterySet } from "@/src/rosary";
import { CHAPLET_ORDER } from "@/src/prayers/chaplets";
import { DEVOTION_CATEGORIES } from "@/src/prayers/devotions";
import { todayISO } from "@/src/date-utils";
import { useI18n } from "@/src/i18n";
import { useTranslator } from "@/src/translate";

type CardItem = {
  testID: string;
  title: string;
  subtitle: string;
  meta: string;
  color: string;
  icon: string;
  onPress: () => void;
  featured?: boolean;
};

export default function PrayerHubScreen() {
  const router = useRouter();
  const today = todayISO();

  const todayMystery: MysterySet = useMemo(() => mysteryForDate(new Date()), []);

  const items: CardItem[] = useMemo(() => {
    const chapletCount = CHAPLET_ORDER.length;
    const countFor = (key: string) => DEVOTION_CATEGORIES.find((c) => c.key === key)?.keys.length || 0;
    const arr: CardItem[] = [];
    // Rosary featured first — opens the prayer directly with today's mysteries.
    arr.push({
      testID: "prayer-card-rosary",
      title: "Holy Rosary",
      subtitle: `Today: ${todayMystery.title}`,
      meta: "~20 min",
      color: todayMystery.color,
      icon: "flower-outline",
      onPress: () =>
        router.push({ pathname: "/prayer/[kind]", params: { kind: "rosary", date: today } }),
      featured: true,
    });
    // Category boxes — each opens a screen listing the prayers within.
    arr.push({
      testID: "prayer-cat-chaplets",
      title: "Chaplets",
      subtitle: "Divine Mercy, St. Michael, Sacred Heart & more",
      meta: `${chapletCount} CHAPLETS`,
      color: "#1E73BE",
      icon: "ellipsis-horizontal-circle-outline",
      onPress: () => router.push({ pathname: "/prayer/category/[cat]", params: { cat: "chaplets" } }),
    });
    arr.push({
      testID: "prayer-cat-marian",
      title: "Marian Prayers",
      subtitle: "Angelus, Memorare, Salve Regina, Magnificat…",
      meta: `${countFor("marian")} PRAYERS`,
      color: "#3F62A8",
      icon: "flower-outline",
      onPress: () => router.push({ pathname: "/prayer/category/[cat]", params: { cat: "marian" } }),
    });
    arr.push({
      testID: "prayer-cat-litany",
      title: "Litanies",
      subtitle: "Of the Saints, Loreto, Sacred Heart, Humility…",
      meta: `${countFor("litany")} LITANIES`,
      color: "#7A5C00",
      icon: "people-circle-outline",
      onPress: () => router.push({ pathname: "/prayer/category/[cat]", params: { cat: "litany" } }),
    });
    arr.push({
      testID: "prayer-cat-stations",
      title: "Stations of the Cross",
      subtitle: "Traditional, Scriptural & St. Alphonsus' Way",
      meta: `${countFor("stations")} VERSIONS`,
      color: "#5D4037",
      icon: "walk-outline",
      onPress: () => router.push({ pathname: "/prayer/category/[cat]", params: { cat: "stations" } }),
    });
    arr.push({
      testID: "prayer-cat-mass",
      title: "Mass & Communion",
      subtitle: "Prayers before & after Mass and Communion",
      meta: `${countFor("mass")} PRAYERS`,
      color: "#1E5631",
      icon: "wine-outline",
      onPress: () => router.push({ pathname: "/prayer/category/[cat]", params: { cat: "mass" } }),
    });
    arr.push({
      testID: "prayer-cat-devotional",
      title: "Devotions & Acts",
      subtitle: "St. Michael, Morning Offering, Te Deum…",
      meta: `${countFor("devotional")} PRAYERS`,
      color: "#5B3475",
      icon: "ribbon-outline",
      onPress: () => router.push({ pathname: "/prayer/category/[cat]", params: { cat: "devotional" } }),
    });
    arr.push({
      testID: "prayer-cat-seasonal",
      title: "Seasonal & Feast Day",
      subtitle: "Prayers for Advent, Lent, Easter & feasts",
      meta: `${countFor("seasonal")} PRAYERS`,
      color: "#C9A227",
      icon: "leaf-outline",
      onPress: () => router.push({ pathname: "/prayer/category/[cat]", params: { cat: "seasonal" } }),
    });
    // Multi-day journeys (their own routes).
    arr.push({
      testID: "prayer-card-novenas",
      title: "Novenas",
      subtitle: "Nine days of prayer — choose your start date",
      meta: "9 DAYS",
      color: "#5B3475",
      icon: "calendar-outline",
      onPress: () => router.push("/novenas"),
    });
    arr.push({
      testID: "prayer-card-consecration",
      title: "Consecration to St. Joseph",
      subtitle: "33-day preparation — give yourself to Jesus through St. Joseph",
      meta: "33 DAYS",
      color: "#C29A3B",
      icon: "shield-half-outline",
      onPress: () => router.push("/consecration" as any),
    });
    arr.push({
      testID: "prayer-card-companions",
      title: "Daily Companions",
      subtitle: "Choose up to 3 saints to walk with each day",
      meta: "SAINTS",
      color: "#7A86C4",
      icon: "people-outline",
      onPress: () => router.push("/companions" as any),
    });
    return arr;
  }, [router, today, todayMystery]);

  const { lang } = useI18n();
  const introTitle = "Anchor the day in prayer.";
  const introBody = "Choose the Rosary or a chaplet. Each prayer closes with a small good work — a way to live the grace into your day.";
  const allStrings = useMemo(() => {
    const a: string[] = [introTitle, introBody];
    items.forEach((it) => { a.push(it.title, it.subtitle, it.meta || ""); });
    return a;
  }, [items]);
  const { tr } = useTranslator(allStrings);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="prayer-hub-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="prayer-hub-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>{lang === "es" ? "Oración" : lang === "it" ? "Preghiera" : "Prayer"}</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.intro}>
          <Text style={styles.eyebrow}>ORATIO</Text>
          <Text style={styles.introTitle}>{tr(introTitle)}</Text>
          <Text style={styles.introBody}>
            {tr(introBody)}
          </Text>
        </View>

        {items.map((it) => (
          <Pressable
            key={it.testID}
            testID={it.testID}
            onPress={it.onPress}
            style={({ pressed }) => [
              styles.card,
              it.featured && styles.cardFeatured,
              pressed && styles.pressed,
            ]}
          >
            <View style={[styles.iconWrap, { backgroundColor: it.color }]}>
              <Ionicons name={it.icon as any} size={22} color={"#FAF9F6"} />
            </View>
            <View style={{ flex: 1 }}>
              <View style={styles.titleRow}>
                <Text style={styles.cardTitle}>{tr(it.title)}</Text>
                {it.featured ? (
                  <View style={styles.featuredPill}>
                    <Text style={styles.featuredPillText}>{lang === "es" ? "HOY" : lang === "it" ? "OGGI" : "TODAY"}</Text>
                  </View>
                ) : null}
              </View>
              <Text style={styles.cardSub}>{tr(it.subtitle)}</Text>
              <Text style={styles.cardMeta}>{tr(it.meta)}</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          </Pressable>
        ))}

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
  headerTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
    flex: 1,
    textAlign: "center",
    marginHorizontal: spacing.sm,
  },
  scroll: { padding: spacing.lg },
  sectionHeader: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 1.6, color: colors.gold, marginTop: spacing.md, marginBottom: spacing.sm, textTransform: "uppercase" },
  intro: { marginBottom: spacing.lg },
  eyebrow: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 2.5,
    color: colors.gold,
  },
  introTitle: {
    fontFamily: fonts.headingBold,
    fontSize: 26,
    color: colors.textPrimary,
    marginTop: 6,
  },
  introBody: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
    marginTop: spacing.sm,
  },
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
  cardFeatured: {
    borderColor: colors.gold,
    borderWidth: 1.5,
  },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  titleRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  cardTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary, flexShrink: 1 },
  cardSub: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  cardMeta: { fontFamily: fonts.uiMedium, fontSize: 10, color: colors.gold, marginTop: 4, letterSpacing: 1.4 },
  featuredPill: {
    backgroundColor: colors.gold,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: radius.round,
  },
  featuredPillText: { fontFamily: fonts.uiSemi, color: colors.primary, fontSize: 9, letterSpacing: 1.2 },
  pressed: { opacity: 0.7 },
});

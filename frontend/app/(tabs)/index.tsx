import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";

import { api, LiturgicalDay, Readings } from "@/src/api";
import { useAuth } from "@/src/auth-context";
import DailyPracticeCard from "@/src/components/DailyPracticeCard";
import CatechismCard from "@/src/components/CatechismCard";
import VirtusHomeCard from "@/src/components/VirtusHomeCard";
import { useI18n } from "@/src/i18n";
import { AutoText } from "@/src/auto-text";
import SaintOfTheDayCard from "@/src/components/SaintOfTheDayCard";
import ChallengeHomeCard from "@/src/components/ChallengeHomeCard";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { formatLongFromISO, parseISO, todayISO } from "@/src/date-utils";

const DEVOTIONS = [
  {
    title: "Morning Offering",
    text: "O Jesus, through the Immaculate Heart of Mary, I offer You my prayers, works, joys and sufferings of this day in union with the Holy Sacrifice of the Mass.",
  },
  {
    title: "Glory Be",
    text: "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.",
  },
  {
    title: "Anima Christi",
    text: "Soul of Christ, sanctify me. Body of Christ, save me. Blood of Christ, inebriate me. Water from the side of Christ, wash me.",
  },
];

function pickDevotion(dateStr: string) {
  const d = parseISO(dateStr);
  return DEVOTIONS[d.getDate() % DEVOTIONS.length];
}

export default function TodayScreen() {
  const { user } = useAuth();
  const { t, lang, setLang } = useI18n();
  const router = useRouter();
  const [date] = useState(() => todayISO());
  const [lit, setLit] = useState<LiturgicalDay | null>(null);
  const [readings, setReadings] = useState<Readings | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const l = await api<LiturgicalDay>(`/liturgical/day?date=${date}`);
    setLit(l);
    // Readings are slower / non-critical — load in background.
    api<Readings>(`/readings?date=${date}`).then(setReadings).catch(() => undefined);
  }, [date]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await load();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await load();
    } finally {
      setRefreshing(false);
    }
  }, [load]);

  const devotion = pickDevotion(date);
  const longDate = formatLongFromISO(date);
  const firstName = user?.name?.split(" ")[0] ?? "friend";

  if (loading) {
    return (
      <SafeAreaView style={styles.safe} edges={["top"]} testID="today-screen">
        <View style={styles.loadingWrap}>
          <ActivityIndicator color={colors.gold} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="today-screen">
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
      >
        {/* Language toggle */}
        <View style={styles.langRow}>
          <Pressable
            testID="lang-en"
            onPress={() => setLang("en")}
            style={[styles.langChip, lang === "en" && styles.langChipOn]}
          >
            <Text style={[styles.langText, lang === "en" && styles.langTextOn]}>EN</Text>
          </Pressable>
          <Pressable
            testID="lang-es"
            onPress={() => setLang("es")}
            style={[styles.langChip, lang === "es" && styles.langChipOn]}
          >
            <Text style={[styles.langText, lang === "es" && styles.langTextOn]}>Español</Text>
          </Pressable>
          <Pressable
            testID="lang-it"
            onPress={() => setLang("it")}
            style={[styles.langChip, lang === "it" && styles.langChipOn]}
          >
            <Text style={[styles.langText, lang === "it" && styles.langTextOn]}>Italiano</Text>
          </Pressable>
        </View>

        {/* Header */}
        <Text style={styles.greeting}>Pax tecum, {firstName}.</Text>
        <AutoText style={styles.date}>{longDate}</AutoText>
        {lit ? (
          <View style={styles.badgeRow}>
            <LiturgicalBadge color={lit.color} label={lit.season} testID="today-season-badge" />
            {lit.is_abstinence && (
              <LiturgicalBadge color="red" label="Abstinence" testID="today-abstinence-badge" />
            )}
            {lit.is_fast && <LiturgicalBadge color="purple" label="Fast" testID="today-fast-badge" />}
          </View>
        ) : null}
        {lit?.feast ? <Text style={styles.feast}>{lit.feast}</Text> : null}

        <Ornament />

        {/* Devotion */}
        <View style={styles.card} testID="devotion-card">
          <View style={styles.cardHeader}>
            <Ionicons name="book-outline" size={18} color={colors.gold} />
            <Text style={styles.cardHeaderText}>DAILY DEVOTION</Text>
          </View>
          <AutoText style={styles.devotionTitle}>{devotion.title}</AutoText>
          <AutoText style={styles.devotionText}>{devotion.text}</AutoText>
        </View>

        {/* Quick actions */}
        <View style={styles.quickRow} testID="quick-actions-row">
          <QuickTile
            testID="quick-rosary"
            icon="flower-outline"
            label={t("home.prayer")}
            onPress={() => router.push("/prayer")}
          />
          <QuickTile
            testID="quick-journal"
            icon="create-outline"
            label={t("home.journal")}
            onPress={() => router.push("/journal-list")}
          />
          <QuickTile
            testID="quick-grocery"
            icon="cart-outline"
            label={t("home.grocery")}
            onPress={() => router.push("/grocery")}
          />
        </View>
        <View style={styles.quickRow}>
          <QuickTile
            testID="quick-bible"
            icon="book-outline"
            label={t("home.bible")}
            onPress={() => router.push("/bible")}
          />
          <QuickTile
            testID="quick-calendar"
            icon="calendar-outline"
            label={t("home.calendar")}
            onPress={() => router.push("/(tabs)/calendar")}
          />
          <QuickTile
            testID="quick-churches"
            icon="home-outline"
            label={t("home.churches")}
            onPress={() => router.push("/churches")}
          />
        </View>
        <View style={styles.quickRow}>
          <QuickTile
            testID="quick-examen"
            icon="sunny-outline"
            label={t("home.examen")}
            onPress={() => router.push({ pathname: "/journal", params: { date, mode: "examen" } })}
          />
          <QuickTile
            testID="quick-selfdefense"
            icon="shield-outline"
            label={t("home.selfDefense")}
            onPress={() => router.push("/self-defense")}
          />
          <QuickTile
            testID="quick-charities"
            icon="heart-circle-outline"
            label={t("home.charities")}
            onPress={() => router.push("/charities")}
          />
        </View>

        {/* Mass Readings */}
        <Pressable
          testID="readings-card"
          onPress={() => router.push({ pathname: "/readings", params: { date } })}
          style={({ pressed }) => [styles.card, pressed && styles.pressed]}
        >
          <View style={styles.cardHeader}>
            <Ionicons name="bookmark-outline" size={18} color={colors.gold} />
            <AutoText style={styles.cardHeaderText}>MASS READINGS</AutoText>
            <View style={{ flex: 1 }} />
            <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
          </View>
          {readings ? (
            <>
              <AutoText style={styles.mealName}>
                {readings.liturgical_title || lit?.feast || lit?.season}
              </AutoText>
              {readings.gospel ? (
                <View style={styles.readingRow}>
                  <AutoText style={styles.readingLabel}>Gospel</AutoText>
                  <Text style={styles.readingCite}>{readings.gospel}</Text>
                </View>
              ) : null}
              {readings.first_reading ? (
                <View style={styles.readingRow}>
                  <AutoText style={styles.readingLabel}>1st</AutoText>
                  <Text style={styles.readingCite}>{readings.first_reading}</Text>
                </View>
              ) : null}
              {readings.psalm ? (
                <View style={styles.readingRow}>
                  <AutoText style={styles.readingLabel}>Psalm</AutoText>
                  <Text style={styles.readingCite}>{readings.psalm}</Text>
                </View>
              ) : null}
            </>
          ) : (
            <AutoText style={styles.empty}>Loading today&apos;s Mass readings…</AutoText>
          )}
        </Pressable>

        {/* Today's practice */}
        <DailyPracticeCard date={date} />

        {/* Liturgical Challenge — only shown when enrolled AND today is within window */}
        <ChallengeHomeCard date={date} />

        {/* Saint / Blessed / Venerable of the Day */}
        <SaintOfTheDayCard date={date} />

        {/* Catechism in 90 seconds */}
        <CatechismCard date={date} />

        {/* Virtus — grow in virtue */}
        <VirtusHomeCard />

        {/* Schedule + In the World — side by side */}
        <View style={styles.featureRow}>
          <FeatureBox
            testID="feature-schedule"
            icon="time-outline"
            title={t("home.schedule")}
            subtitle={t("home.scheduleSub")}
            accent={colors.liturgical.purple}
            onPress={() => router.push("/schedule")}
          />
          <FeatureBox
            testID="feature-world"
            icon="earth-outline"
            title={t("home.world")}
            subtitle={t("home.worldSub")}
            accent={colors.liturgical.red}
            onPress={() => router.push("/in-the-world")}
          />
        </View>

        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function FeatureBox({
  testID,
  icon,
  title,
  subtitle,
  accent,
  onPress,
}: {
  testID: string;
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle: string;
  accent: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      style={({ pressed }) => [styles.featureBox, { borderTopColor: accent }, pressed && styles.pressed]}
    >
      <View style={[styles.featureIconWrap, { backgroundColor: accent + "1A" }]}>
        <Ionicons name={icon} size={22} color={accent} />
      </View>
      <Text style={styles.featureTitle}>{title}</Text>
      <Text style={styles.featureSubtitle}>{subtitle}</Text>
    </Pressable>
  );
}

function QuickTile({
  testID,
  icon,
  label,
  onPress,
}: {
  testID: string;
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable testID={testID} onPress={onPress} style={({ pressed }) => [styles.tile, pressed && styles.pressed]}>
      <Ionicons name={icon} size={22} color={colors.gold} />
      <Text style={styles.tileLabel}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  scroll: { paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: spacing.xl },
  loadingWrap: { flex: 1, alignItems: "center", justifyContent: "center" },  greeting: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 16,
    color: colors.textSecondary,
    marginBottom: 4,
  },
  date: {
    fontFamily: fonts.headingBold,
    fontSize: 32,
    color: colors.textPrimary,
    lineHeight: 38,
  },
  badgeRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.sm },
  feast: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.liturgical.red,
    marginTop: spacing.sm,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginTop: spacing.md,
    ...shadow.card,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  cardHeaderText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.5,
    color: colors.gold,
  },
  devotionTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 22,
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  devotionText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 16,
    color: colors.textSecondary,
    lineHeight: 26,
    fontStyle: "italic",
  },
  mealName: {
    fontFamily: fonts.headingSemi,
    fontSize: 22,
    color: colors.textPrimary,
    marginBottom: 4,
  },
  mealDesc: {
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textSecondary,
    lineHeight: 22,
  },
  reflection: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 14,
    color: colors.liturgical.purple,
    marginTop: spacing.md,
    lineHeight: 22,
  },
  empty: {
    fontFamily: fonts.bodyRegular,
    fontStyle: "italic",
    fontSize: 15,
    color: colors.textSecondary,
    lineHeight: 22,
    marginBottom: spacing.md,
  },
  primaryBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 14,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
  primaryBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 15,
    letterSpacing: 0.6,
  },
  linkBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: spacing.md,
  },
  linkBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 14,
  },
  langRow: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: 6,
    marginBottom: 4,
  },
  langChip: {
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.surface,
  },
  langChipOn: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  langText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 0.4,
    color: colors.textSecondary,
  },
  langTextOn: {
    color: colors.gold,
  },
  quickRow: {
    flexDirection: "row",
    gap: spacing.sm,    marginTop: spacing.md,
  },
  tile: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    gap: 6,
    ...shadow.card,
  },
  tileLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.textPrimary,
    letterSpacing: 0.6,
  },
  featureRow: {
    flexDirection: "row",
    gap: spacing.md,
    marginTop: spacing.md,
  },
  featureBox: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderTopWidth: 3,
    padding: spacing.lg,
    gap: spacing.sm,
    ...shadow.card,
  },
  featureIconWrap: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  featureTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 17,
    color: colors.textPrimary,
  },
  featureSubtitle: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 19,
  },
  readingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginTop: 6,
  },
  readingLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1.2,
    color: colors.textMuted,
    width: 46,
  },
  readingCite: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textPrimary,
    flex: 1,
  },
  journalRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  journalTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 16,
    color: colors.textPrimary,
  },
  journalBody: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 20,
    marginTop: 2,
  },
  pressed: { opacity: 0.7 },
});

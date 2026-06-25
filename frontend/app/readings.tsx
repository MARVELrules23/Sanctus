import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { api, Readings } from "@/src/api";
import { useI18n } from "@/src/i18n";
import { AutoText } from "@/src/auto-text";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { formatLong, parseISO, todayISO } from "@/src/date-utils";

type Section = {
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  citation: string;
  excerpt: string;
  accent?: string;
};

export default function ReadingsScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ date?: string }>();
  const date = typeof params.date === "string" ? params.date : todayISO();
  const { lang } = useI18n();
  const [data, setData] = useState<Readings | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const res = await api<Readings>(`/readings?date=${date}`);
    setData(res);
  }, [date, lang]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await load();
      } catch (e) {
        console.warn("readings load failed", e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await load();
    } finally {
      setRefreshing(false);
    }
  };

  const openUSCCB = () => {
    if (data?.usccb_url) Linking.openURL(data.usccb_url).catch(() => undefined);
  };

  const sections: Section[] = data
    ? ([
        { label: "First Reading", icon: "book-outline" as const, citation: data.first_reading, excerpt: data.first_reading_excerpt },
        { label: "Responsorial Psalm", icon: "musical-notes-outline" as const, citation: data.psalm, excerpt: data.psalm_excerpt, accent: colors.liturgical.purple },
        { label: "Second Reading", icon: "book-outline" as const, citation: data.second_reading, excerpt: data.second_reading_excerpt },
        { label: "Gospel Acclamation", icon: "flower-outline" as const, citation: data.gospel_acclamation, excerpt: data.gospel_acclamation_excerpt, accent: colors.gold },
        { label: "Gospel", icon: "sparkles-outline" as const, citation: data.gospel, excerpt: data.gospel_excerpt, accent: colors.liturgical.red },
      ] as Section[]).filter((s) => s.citation || s.excerpt)
    : [];

  const sourceLabel: Record<NonNullable<Readings["source"]>, string> = {
    universalis: "Live · Universalis lectionary",
    usccb: "Live · USCCB",
    "ai-fallback": "AI-suggested citations",
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="readings-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.headerRow}>
        <Pressable testID="readings-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <AutoText style={styles.headerTitle}>Mass Readings</AutoText>
        <Pressable
          testID="readings-usccb-link"
          onPress={openUSCCB}
          hitSlop={12}
          disabled={!data?.usccb_url}
        >
          <Ionicons name="open-outline" size={22} color={data?.usccb_url ? colors.gold : colors.textMuted} />
        </Pressable>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
      >
        {loading ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xxl }} />
        ) : !data ? (
          <AutoText style={styles.empty}>Unable to load readings. Pull to refresh.</AutoText>
        ) : (
          <>
            <AutoText style={styles.dateLine}>{formatLong(parseISO(date))}</AutoText>
            <AutoText style={styles.litTitle}>{data.liturgical_title || data.liturgical?.feast || data.liturgical?.season}</AutoText>

            <View style={styles.badgeRow}>
              {data.liturgical?.color && (
                <LiturgicalBadge color={data.liturgical.color} label={data.liturgical.season} />
              )}
              {data.liturgical?.is_sunday && <LiturgicalBadge color="gold" label="Lord's Day" />}
              {data.liturgical?.is_abstinence && <LiturgicalBadge color="red" label="Abstinence" />}
              {data.liturgical?.is_fast && <LiturgicalBadge color="purple" label="Fast" />}
            </View>

            <Ornament />

            {sections.map((s) => (
              <View key={s.label} style={styles.card} testID={`reading-${s.label.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
                <View style={styles.cardHeader}>
                  <Ionicons name={s.icon} size={16} color={s.accent ?? colors.gold} />
                  <AutoText style={[styles.cardHeaderText, { color: s.accent ?? colors.gold }]}>{s.label.toUpperCase()}</AutoText>
                </View>
                {s.citation ? <Text style={styles.citation}>{s.citation}</Text> : null}
                {s.excerpt ? <Text style={styles.excerpt}>{s.excerpt}</Text> : null}
              </View>
            ))}

            {data.reflection ? (
              <View style={styles.reflectionCard}>
                <View style={styles.cardHeader}>
                  <Ionicons name="leaf-outline" size={16} color={colors.liturgical.purple} />
                  <AutoText style={[styles.cardHeaderText, { color: colors.liturgical.purple }]}>REFLECTION</AutoText>
                </View>
                <Text style={styles.reflectionText}>{data.reflection}</Text>
              </View>
            ) : null}

            <Pressable
              testID="readings-open-full"
              onPress={openUSCCB}
              style={({ pressed }) => [styles.cta, pressed && styles.pressed]}
              disabled={!data.usccb_url}
            >
              <Ionicons name="open-outline" size={16} color={colors.gold} />
              <AutoText style={styles.ctaText}>Read full text on USCCB</AutoText>
            </Pressable>

            <AutoText style={styles.sourceLine}>{sourceLabel[data.source] ?? data.source}</AutoText>
          </>
        )}
        <View style={{ height: spacing.xxl }} />
      </ScrollView>
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
  scroll: { padding: spacing.lg },
  dateLine: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 14, color: colors.textSecondary },
  litTitle: { fontFamily: fonts.headingBold, fontSize: 26, color: colors.textPrimary, marginTop: spacing.xs, lineHeight: 32 },
  badgeRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.md },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginTop: spacing.md,
    ...shadow.card,
  },
  cardHeader: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.xs },
  cardHeaderText: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 1.5, color: colors.gold },
  citation: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary, marginTop: 4 },
  excerpt: {
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textSecondary,
    lineHeight: 24,
    marginTop: spacing.sm,
    fontStyle: "italic",
  },
  reflectionCard: {
    backgroundColor: "#F6F2EB",
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginTop: spacing.md,
  },
  reflectionText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.liturgical.purple,
    lineHeight: 24,
    marginTop: spacing.xs,
  },
  cta: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    backgroundColor: colors.primary,
    paddingVertical: 14,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    marginTop: spacing.lg,
  },
  ctaText: { fontFamily: fonts.uiSemi, fontSize: 15, color: colors.gold, letterSpacing: 0.6 },
  sourceLine: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textMuted,
    textAlign: "center",
    marginTop: spacing.md,
    letterSpacing: 0.6,
  },
  empty: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textSecondary, textAlign: "center", marginTop: spacing.xxl },
  pressed: { opacity: 0.7 },
});

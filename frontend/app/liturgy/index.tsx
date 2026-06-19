/**
 * Sanctus — Liturgy of the Hours hub.
 *
 * Lists the three principal Hours of the Divine Office (Lauds, Vespers,
 * Compline) in the traditional Roman Breviary form. Free for all
 * authenticated users — no premium gate.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { listLiturgyHours, LiturgyIndex } from "@/src/api";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

export default function LiturgyIndexScreen() {
  const router = useRouter();
  const [data, setData] = useState<LiturgyIndex | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await listLiturgyHours();
      setData(r);
    } catch (e: any) {
      setError(e?.message || "Could not load the Divine Office.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const todayName =
    data?.days.find((d) => d.key === data?.today)?.name || "";

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="liturgy-index">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="liturgy-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.headerTitle}>Liturgy of the Hours</Text>
          <Text style={styles.headerSub}>Divine Office · Latin & English</Text>
        </View>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      ) : error || !data ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error || "Something went wrong."}</Text>
          <Pressable testID="liturgy-retry" onPress={load} style={({ pressed }) => [styles.retry, pressed && { opacity: 0.7 }]}>
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.heroIntro}>
            <Ornament />
            <Text style={styles.heroIntroTitle}>Pray with the whole Church</Text>
            <Text style={styles.heroIntroSub}>
              The Liturgy of the Hours sanctifies the day with psalms, hymns,
              and canticles. Pray Lauds at daybreak, Vespers at sunset, and
              Compline before sleep — the traditional Roman Breviary, in Latin
              and English.
            </Text>
            {todayName ? (
              <View style={styles.todayPill}>
                <Ionicons name="calendar-outline" size={12} color={colors.gold} />
                <Text style={styles.todayPillText}>Today is {todayName}</Text>
              </View>
            ) : null}
          </View>

          {data.hours.map((h) => (
            <Pressable
              key={h.slug}
              testID={`liturgy-tile-${h.slug}`}
              onPress={() => router.push({ pathname: "/liturgy/[hour]", params: { hour: h.slug } } as any)}
              style={({ pressed }) => [
                styles.tile,
                { borderColor: h.accent_color },
                pressed && { opacity: 0.85, transform: [{ scale: 0.99 }] },
              ]}
            >
              <View style={[styles.tileIconWrap, { backgroundColor: h.accent_color + "22", borderColor: h.accent_color }]}>
                <Ionicons
                  name={(h.icon as keyof typeof Ionicons.glyphMap) || "book-outline"}
                  size={26}
                  color={h.accent_color}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.tileLatin}>{h.latin_name.toUpperCase()}</Text>
                <Text style={styles.tileName}>{h.name}</Text>
                <Text style={styles.tileSubtitle}>{h.subtitle} · {h.time_of_day}</Text>
                <View style={styles.tileMetaRow}>
                  <View style={[styles.metaPill, { borderColor: h.accent_color }]}>
                    <Ionicons name="time-outline" size={11} color={h.accent_color} />
                    <Text style={[styles.metaPillText, { color: h.accent_color }]}>{h.duration}</Text>
                  </View>
                  <View style={styles.metaPill}>
                    <Ionicons name="repeat" size={11} color={colors.textMuted} />
                    <Text style={styles.metaPillText}>
                      {h.psalms_vary_by_day ? "Varies by weekday" : "Same every night"}
                    </Text>
                  </View>
                </View>
              </View>
              <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
            </Pressable>
          ))}

          {/* External link to iBreviary for the modern form */}
          {data.external_link ? (
            <Pressable
              testID="liturgy-external-link"
              onPress={() => Linking.openURL(data.external_link.url)}
              style={({ pressed }) => [styles.extCard, pressed && { opacity: 0.85 }]}
            >
              <Ionicons name="open-outline" size={20} color={colors.primary} />
              <View style={{ flex: 1 }}>
                <Text style={styles.extTitle}>{data.external_link.label}</Text>
                <Text style={styles.extSub}>{data.external_link.description}</Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
            </Pressable>
          ) : null}

          <View style={styles.footnote}>
            <Text style={styles.footnoteText}>
              These Hours present the public-domain pre-1962 Roman Breviary
              (Latin Vulgate + Douay-Rheims English). Modern ICEL texts are
              copyrighted; tap the link above for the current proper.
            </Text>
          </View>
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
    gap: spacing.md,
  },
  headerTitleWrap: { flex: 1, alignItems: "center" },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 19, color: colors.textPrimary },
  headerSub: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, fontSize: 11, marginTop: 1 },
  scroll: { padding: spacing.lg, gap: spacing.md },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.md },
  errorText: { fontFamily: fonts.bodyRegular, color: colors.textSecondary, textAlign: "center" },
  retry: {
    paddingHorizontal: spacing.lg,
    paddingVertical: 10,
    backgroundColor: colors.primary,
    borderRadius: radius.round,
  },
  retryText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 13, letterSpacing: 0.6 },

  heroIntro: { alignItems: "center", paddingVertical: spacing.lg, gap: spacing.sm },
  heroIntroTitle: {
    fontFamily: fonts.headingBold,
    fontSize: 22,
    color: colors.textPrimary,
    textAlign: "center",
    marginTop: spacing.sm,
  },
  heroIntroSub: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    lineHeight: 22,
    color: colors.textSecondary,
    textAlign: "center",
    paddingHorizontal: spacing.md,
  },
  todayPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
    marginTop: spacing.xs,
  },
  todayPillText: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.gold, letterSpacing: 0.4 },

  tile: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    ...shadow.card,
  },
  tileIconWrap: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1.5,
  },
  tileLatin: { fontFamily: fonts.uiSemi, fontSize: 9, letterSpacing: 1.4, color: colors.textMuted },
  tileName: { fontFamily: fonts.headingSemi, fontSize: 17, color: colors.textPrimary, marginTop: 2 },
  tileSubtitle: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  tileMetaRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 8 },
  metaPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.background,
  },
  metaPillText: { fontFamily: fonts.uiSemi, fontSize: 10, color: colors.textMuted, letterSpacing: 0.4 },

  extCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginTop: spacing.xs,
  },
  extTitle: { fontFamily: fonts.headingSemi, fontSize: 14, color: colors.textPrimary },
  extSub: { fontFamily: fonts.bodyRegular, fontSize: 11.5, lineHeight: 17, color: colors.textMuted, marginTop: 2 },

  footnote: {
    marginTop: spacing.md,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderStyle: "dashed",
  },
  footnoteText: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 12,
    lineHeight: 18,
    color: colors.textMuted,
    textAlign: "center",
  },
});

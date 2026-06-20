import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { getWorldIssue, WorldContent } from "@/src/api";
import { useI18n } from "@/src/i18n";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

export default function WorldIssueScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const router = useRouter();
  const { lang } = useI18n();
  const es = lang === "es";
  const [data, setData] = useState<WorldContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    if (!slug) return;
    setLoading(true);
    setError(false);
    try {
      setData(await getWorldIssue(slug));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [slug]);
  useEffect(() => { void load(); }, [load]);

  const L = {
    teaching: es ? "Lo que enseña la Iglesia" : "What the Church teaches",
    principles: es ? "Principios en juego" : "Principles at play",
    clear: es ? "Donde la Iglesia es clara" : "Where the Church is clear",
    prudential: es ? "Juicio prudencial" : "Prudential judgment",
    engage: es ? "Cómo participar" : "How to engage",
    prayer: es ? "Oración" : "A prayer",
    retry: es ? "Reintentar" : "Try again",
    forming: es ? "Formando esta reflexión…" : "Forming this reflection…",
  };

  const accent = data?.accent || colors.gold;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="world-issue-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle} numberOfLines={1}>{data?.title || (es ? "En el Mundo" : "In the World")}</Text>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
          <Text style={styles.loadingText}>{L.forming}</Text>
        </View>
      ) : error || !data ? (
        <View style={styles.center}>
          <Text style={styles.loadingText}>{es ? "No se pudo cargar." : "Couldn't load this."}</Text>
          <Pressable onPress={load} style={({ pressed }) => [styles.retry, pressed && styles.pressed]}>
            <Text style={styles.retryText}>{L.retry}</Text>
          </Pressable>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <View style={[styles.hero, { borderTopColor: accent }]}>
            <View style={[styles.iconWrap, { backgroundColor: accent + "1A" }]}>
              <Ionicons name={(data.icon as keyof typeof Ionicons.glyphMap) || "globe-outline"} size={26} color={accent} />
            </View>
            <Text style={styles.heroTitle}>{data.title}</Text>
            <Text style={styles.summary}>{data.summary}</Text>
          </View>

          <Section title={L.teaching} accent={accent} body={data.church_teaching} />

          {data.principles?.length ? (
            <View style={styles.card}>
              <Text style={[styles.sectionLabel, { color: accent }]}>{L.principles.toUpperCase()}</Text>
              {data.principles.map((p, i) => (
                <View key={i} style={styles.bulletRow}>
                  <Ionicons name="ellipse" size={7} color={accent} style={{ marginTop: 7 }} />
                  <Text style={styles.bulletText}>{p}</Text>
                </View>
              ))}
            </View>
          ) : null}

          <View style={[styles.card, styles.clearCard, { borderColor: accent }]}>
            <View style={styles.clearHead}>
              <Ionicons name="alert-circle" size={16} color={accent} />
              <Text style={[styles.sectionLabel, { color: accent, marginBottom: 0 }]}>{L.clear.toUpperCase()}</Text>
            </View>
            <Text style={styles.body}>{data.where_the_church_is_clear}</Text>
          </View>

          <Section title={L.prudential} accent={accent} body={data.prudential_judgment} />
          <Section title={L.engage} accent={accent} body={data.how_to_engage} />

          {data.prayer ? (
            <View style={[styles.card, styles.prayerCard]}>
              <Text style={[styles.sectionLabel, { color: colors.gold }]}>{L.prayer.toUpperCase()}</Text>
              <Text style={styles.prayerText}>{data.prayer}</Text>
            </View>
          ) : null}
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

function Section({ title, body, accent }: { title: string; body: string; accent: string }) {
  if (!body) return null;
  return (
    <View style={styles.card}>
      <Text style={[styles.sectionLabel, { color: accent }]}>{title.toUpperCase()}</Text>
      <Text style={styles.body}>{body}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft, gap: spacing.md,
  },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingBold, fontSize: 18, color: colors.textPrimary },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.md, padding: spacing.xl },
  loadingText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textSecondary, textAlign: "center" },
  retry: { paddingHorizontal: spacing.lg, paddingVertical: 10, backgroundColor: colors.primary, borderRadius: radius.round },
  retryText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 13 },
  scroll: { padding: spacing.lg, gap: spacing.md },
  hero: {
    padding: spacing.lg, borderRadius: radius.lg, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: colors.borderSoft, borderTopWidth: 3, ...shadow.card, gap: spacing.sm,
  },
  iconWrap: { width: 48, height: 48, borderRadius: 24, alignItems: "center", justifyContent: "center" },
  heroTitle: { fontFamily: fonts.headingBold, fontSize: 24, color: colors.textPrimary },
  summary: { fontFamily: fonts.bodyRegular, fontSize: 16, color: colors.textSecondary, lineHeight: 25 },
  card: {
    padding: spacing.lg, borderRadius: radius.lg, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: colors.borderSoft, ...shadow.card,
  },
  sectionLabel: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 1.5, marginBottom: spacing.sm },
  body: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary, lineHeight: 24 },
  bulletRow: { flexDirection: "row", gap: spacing.sm, marginTop: 6 },
  bulletText: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary, lineHeight: 23 },
  clearCard: { borderWidth: 1.5 },
  clearHead: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: spacing.sm },
  prayerCard: { backgroundColor: colors.primary },
  prayerText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 15, color: "#FAF9F6", lineHeight: 24 },
  pressed: { opacity: 0.7 },
});

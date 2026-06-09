import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { SaintPublic, getSaint } from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const RANK_BADGE: Record<SaintPublic["rank"], string> = {
  saint: "SAINT",
  blessed: "BLESSED",
  venerable: "VENERABLE",
};

export default function SaintDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [saint, setSaint] = useState<SaintPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const s = await getSaint(id);
      setSaint(s);
    } catch (e: any) {
      setError(e?.message || "Couldn't load this entry.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="saint-detail-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="saint-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Today&apos;s Holy One</Text>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      ) : error || !saint ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error || "Not found."}</Text>
          <Pressable onPress={load} style={({ pressed }) => [styles.retry, pressed && styles.pressed]}>
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.badgeRow}>
            <Text style={styles.badge}>{RANK_BADGE[saint.rank]}</Text>
            {saint.feast_date ? (
              <Text style={styles.feast}>Feast · {saint.feast_date}</Text>
            ) : null}
          </View>
          <Text style={styles.name} testID="saint-detail-name">{saint.name}</Text>

          {saint.picture_url ? (
            <Image
              source={{ uri: saint.picture_url }}
              style={styles.hero}
              resizeMode="cover"
              testID="saint-detail-portrait"
            />
          ) : (
            <View style={[styles.hero, styles.heroFallback]}>
              <Ionicons name="flower-outline" size={48} color={colors.gold} />
            </View>
          )}
          {saint.picture_source ? (
            <Text style={styles.attribution}>{saint.picture_source}</Text>
          ) : null}

          {saint.quote ? (
            <View style={styles.quoteCard} testID="saint-detail-quote">
              <Ionicons name="chatbox-ellipses-outline" size={16} color={colors.gold} />
              <View style={{ flex: 1 }}>
                <Text style={styles.quoteText}>“{saint.quote}”</Text>
                <Text style={styles.quoteSource}>— {saint.quote_source}</Text>
              </View>
            </View>
          ) : null}

          <Text style={styles.sectionLabel}>Life</Text>
          <Text style={styles.body} testID="saint-detail-bio">{saint.biography}</Text>

          <Text style={styles.sectionLabel}>In their honor</Text>
          <View style={styles.actionCard} testID="saint-detail-action">
            <Ionicons name="heart-outline" size={18} color={colors.gold} />
            <Text style={styles.actionText}>{saint.recommended_action}</Text>
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
    justifyContent: "space-between",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  scroll: { padding: spacing.lg },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.lg, gap: spacing.md },
  errorText: { fontFamily: fonts.bodyRegular, color: colors.textSecondary, textAlign: "center" },
  retry: { paddingHorizontal: spacing.lg, paddingVertical: 10, borderRadius: radius.round, backgroundColor: colors.primary },
  retryText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 13 },
  pressed: { opacity: 0.7 },
  badgeRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.xs,
  },
  badge: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 3,
    color: colors.gold,
  },
  feast: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12, color: colors.textMuted },
  name: {
    fontFamily: fonts.headingBold,
    fontSize: 26,
    color: colors.textPrimary,
    marginBottom: spacing.md,
  },
  hero: {
    width: "100%",
    height: 260,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  heroFallback: { alignItems: "center", justifyContent: "center" },
  attribution: {
    fontFamily: fonts.uiMedium,
    fontSize: 10,
    color: colors.textMuted,
    textAlign: "right",
    marginTop: 4,
  },
  quoteCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderLeftWidth: 3,
    borderLeftColor: colors.gold,
    padding: spacing.md,
    borderRadius: radius.sm,
    marginTop: spacing.md,
    ...shadow.card,
  },
  quoteText: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 15,
    lineHeight: 22,
    color: colors.textPrimary,
  },
  quoteSource: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  sectionLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 2.5,
    color: colors.gold,
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
  },
  body: {
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    lineHeight: 23,
    color: colors.textSecondary,
  },
  actionCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    backgroundColor: colors.primary,
    padding: spacing.md,
    borderRadius: radius.md,
    ...shadow.card,
  },
  actionText: {
    flex: 1,
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    lineHeight: 20,
    color: colors.gold,
  },
});

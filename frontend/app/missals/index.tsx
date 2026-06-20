/**
 * Sanctus Missals Hub — selector screen.
 *
 * Lists the three Roman-rite missals supported in-app. Free to all
 * authenticated users (no premium gate).
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { listMissals, MissalSummary } from "@/src/api";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

export default function MissalsIndexScreen() {
  const router = useRouter();
  const [items, setItems] = useState<MissalSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await listMissals();
      setItems(r.items || []);
    } catch (e: any) {
      setError(e?.message || "Could not load the missals.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="missals-index">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="missals-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.headerTitle}>Mass Missals</Text>
          <Text style={styles.headerSub}>Order of Mass · Latin, English, Español & Italiano</Text>
        </View>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      ) : error ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable testID="missals-retry" onPress={load} style={({ pressed }) => [styles.retry, pressed && { opacity: 0.7 }]}>
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.heroIntro}>
            <Ornament />
            <Text style={styles.heroIntroTitle}>Read the Mass with us</Text>
            <Text style={styles.heroIntroSub}>
              Follow along in the pew, on retreat, or at home. Five missals of
              the Roman Rite — the Ordinary Form, the Traditional Latin Mass,
              the Ordinariate Use, and the Order of Mass in Spanish and Italian —
              each with the unchanging Order of Mass.
            </Text>
          </View>

          {items.map((m) => (
            <Pressable
              key={m.slug}
              testID={`missal-tile-${m.slug}`}
              onPress={() => router.push({ pathname: "/missals/[slug]", params: { slug: m.slug } } as any)}
              style={({ pressed }) => [
                styles.tile,
                { borderColor: m.accent_color },
                pressed && { opacity: 0.85, transform: [{ scale: 0.99 }] },
              ]}
            >
              <View style={[styles.tileIconWrap, { backgroundColor: m.accent_color + "22", borderColor: m.accent_color }]}>
                <Ionicons
                  name={(m.icon as keyof typeof Ionicons.glyphMap) || "book-outline"}
                  size={26}
                  color={m.accent_color}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.tileTradition}>{m.tradition.toUpperCase()}</Text>
                <Text style={styles.tileName}>{m.name}</Text>
                <Text style={styles.tileSubtitle}>{m.subtitle}</Text>
                <View style={styles.tileMetaRow}>
                  <View style={[styles.metaPill, { borderColor: m.accent_color }]}>
                    <Ionicons name="language" size={11} color={m.accent_color} />
                    <Text style={[styles.metaPillText, { color: m.accent_color }]}>{m.language_note}</Text>
                  </View>
                  <View style={styles.metaPill}>
                    <Ionicons name="list" size={11} color={colors.textMuted} />
                    <Text style={styles.metaPillText}>{m.section_count} sections</Text>
                  </View>
                </View>
              </View>
              <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
            </Pressable>
          ))}

          <View style={styles.footnote}>
            <Text style={styles.footnoteText}>
              These missals cover the unchanging Order of Mass only. For Sunday
              and daily Propers, consult your parish missalette or a printed
              Sunday/daily Missal.
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
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.textPrimary },
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

  heroIntro: {
    alignItems: "center",
    paddingVertical: spacing.lg,
    gap: spacing.sm,
  },
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
  tileTradition: {
    fontFamily: fonts.uiSemi,
    fontSize: 9,
    letterSpacing: 1.4,
    color: colors.textMuted,
  },
  tileName: {
    fontFamily: fonts.headingSemi,
    fontSize: 17,
    color: colors.textPrimary,
    marginTop: 2,
  },
  tileSubtitle: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  tileMetaRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginTop: 8,
  },
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
  metaPillText: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    color: colors.textMuted,
    letterSpacing: 0.4,
  },

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

/**
 * VocationHomeCard — a tailored Home-screen box for the user's state of life.
 *
 * Shows only when the user has chosen a vocation (singleness / religious life /
 * marriage) in their Walk with Christ. Surfaces a morning prayer and a saint
 * companion; tapping opens the full vocation guide. Hidden entirely otherwise.
 */
import React, { useCallback, useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useRouter } from "expo-router";

import { getVocationGuide, VocationGuide } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

export default function VocationHomeCard() {
  const router = useRouter();
  const [guide, setGuide] = useState<VocationGuide | null>(null);

  const load = useCallback(async () => {
    try {
      const g = await getVocationGuide();
      setGuide(g.has_vocation ? g : null);
    } catch {
      setGuide(null);
    }
  }, []);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  if (!guide) return null;

  const chosen =
    (guide.companions || []).find((c) => c.slug === guide.companion_saint) ||
    (guide.companions || [])[0];

  return (
    <Pressable
      testID="vocation-home-card"
      onPress={() => router.push("/vocation" as any)}
      style={({ pressed }) => [styles.card, pressed && { opacity: 0.92 }]}
    >
      <View style={styles.cardHeader}>
        <Ionicons name="rose-outline" size={18} color={colors.gold} />
        <Text style={styles.cardHeaderText}>{(guide.label || "Your Vocation").toUpperCase()}</Text>
        <View style={{ flex: 1 }} />
        <Ionicons name="arrow-forward" size={20} color={colors.gold} />
      </View>

      {guide.morning_prayer ? (
        <>
          <View style={styles.row}>
            <Ionicons name="sunny-outline" size={14} color={colors.goldDark} />
            <Text style={styles.prayerLabel}>Morning prayer</Text>
          </View>
          <Text style={styles.prayerTitle} numberOfLines={1}>{guide.morning_prayer.title}</Text>
          <Text style={styles.prayerSnippet} numberOfLines={2}>{guide.morning_prayer.body}</Text>
        </>
      ) : null}

      {chosen ? (
        <View style={styles.companionRow}>
          <Ionicons name="person-circle-outline" size={18} color={colors.gold} />
          <Text style={styles.companionText}>
            Walking with <Text style={styles.companionName}>{chosen.name}</Text>
          </Text>
        </View>
      ) : null}

      <Text style={styles.hint}>Tap for prayers, ideas & traditions to grow →</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.lg,
    gap: 6,
  },
  cardHeader: { flexDirection: "row", alignItems: "center", gap: 8 },
  cardHeaderText: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 1.4, color: colors.textMuted },
  row: { flexDirection: "row", alignItems: "center", gap: 5, marginTop: 2 },
  prayerLabel: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 0.5, textTransform: "uppercase", color: colors.goldDark },
  prayerTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  prayerSnippet: { fontFamily: fonts.bodyRegular, fontSize: 13.5, color: colors.textSecondary, lineHeight: 20, fontStyle: "italic" },
  companionRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 6 },
  companionText: { fontFamily: fonts.bodyRegular, fontSize: 13.5, color: colors.textSecondary },
  companionName: { fontFamily: fonts.headingSemi, fontSize: 13.5, color: colors.primary },
  hint: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.gold, marginTop: 8 },
});

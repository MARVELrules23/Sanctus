/**
 * VocationHomeCard — a tailored Home-screen box for the user's state of life.
 *
 * Shows only when the user has chosen a vocation (singleness / religious life /
 * marriage) in their Walk with Christ. Surfaces a morning prayer and a saint
 * companion; tapping opens the full vocation guide. Hidden entirely otherwise.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Image, Pressable, StyleSheet, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useRouter } from "expo-router";

import { getCompanionImage, getVocationGuide, VocationGuide } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

export default function VocationHomeCard() {
  const router = useRouter();
  const [guide, setGuide] = useState<VocationGuide | null>(null);
  const [image, setImage] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const g = await getVocationGuide();
      setGuide(g.has_vocation ? g : null);
    } catch {
      setGuide(null);
    }
  }, []);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  const chosen =
    (guide?.companions || []).find((c) => c.slug === guide?.companion_saint) ||
    (guide?.companions || [])[0];

  // Fetch the companion's portrait once we know who we're walking with.
  useEffect(() => {
    let cancelled = false;
    if (!chosen?.slug) {
      setImage(null);
      return;
    }
    (async () => {
      try {
        const r = await getCompanionImage(chosen.slug);
        if (!cancelled) setImage(r.image || null);
      } catch {
        if (!cancelled) setImage(null);
      }
    })();
    return () => { cancelled = true; };
  }, [chosen?.slug]);

  if (!guide) return null;

  return (
    <View style={styles.card} testID="vocation-home-card">
      <View style={styles.cardHeader}>
        <Ionicons name="rose-outline" size={18} color={colors.gold} />
        <Text style={styles.cardHeaderText}>MY VOCATION COMPANION</Text>
      </View>

      {chosen ? (
        <Pressable
          testID="vocation-companion-readmore"
          onPress={() => router.push(`/companion/${chosen.slug}` as any)}
          style={({ pressed }) => [styles.companionBlock, pressed && { opacity: 0.9 }]}
        >
          <View style={styles.avatarWrap}>
            {image ? (
              <Image source={{ uri: image }} style={styles.avatar} resizeMode="cover" />
            ) : (
              <View style={[styles.avatar, styles.avatarFallback]}>
                <Ionicons name="person" size={34} color={colors.gold} />
              </View>
            )}
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.walkingLabel}>Walking with</Text>
            <Text style={styles.companionName} numberOfLines={2}>{chosen.name}</Text>
            <Text style={styles.companionWhy} numberOfLines={2}>{chosen.why}</Text>
            <View style={styles.readMoreRow}>
              <Text style={styles.readMore}>Click to read more</Text>
              <Ionicons name="arrow-forward-circle" size={18} color={colors.gold} />
            </View>
          </View>
        </Pressable>
      ) : (
        <Text style={styles.prayerSnippet}>Choose a companion in your Vocation guide to walk with.</Text>
      )}

      {/* Tile that opens the full Vocation page */}
      <Pressable
        testID="vocation-open-guide"
        onPress={() => router.push("/vocation" as any)}
        style={({ pressed }) => [styles.guideTile, pressed && { opacity: 0.85 }]}
      >
        <Ionicons name="book-outline" size={18} color={colors.gold} />
        <View style={{ flex: 1 }}>
          <Text style={styles.guideTitle}>{guide.label || "My Vocation"}</Text>
          <Text style={styles.guideSub}>Prayers, reading, novenas & traditions to grow</Text>
        </View>
        <Ionicons name="chevron-forward" size={20} color={colors.gold} />
      </Pressable>

      {guide.daily_verse && guide.daily_verse.text ? (
        <View style={styles.verseLine} testID="vocation-card-verse">
          <Text style={styles.verseText} numberOfLines={3}>“{guide.daily_verse.text}”</Text>
          <Text style={styles.verseRef}>— {guide.daily_verse.reference}</Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.lg,
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  cardHeader: { flexDirection: "row", alignItems: "center", gap: 8 },
  cardHeaderText: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 1.4, color: colors.textMuted },
  companionBlock: { flexDirection: "row", gap: spacing.md, alignItems: "center", marginTop: 2 },
  avatarWrap: {
    width: 78, height: 78, borderRadius: 39,
    borderWidth: 2, borderColor: colors.gold,
    overflow: "hidden", alignItems: "center", justifyContent: "center",
    backgroundColor: colors.surfaceDark,
  },
  avatar: { width: "100%", height: "100%" },
  avatarFallback: { alignItems: "center", justifyContent: "center" },
  walkingLabel: { fontFamily: fonts.uiSemi, fontSize: 10.5, letterSpacing: 0.6, textTransform: "uppercase", color: colors.goldDark },
  companionName: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.primary, marginTop: 1 },
  companionWhy: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textSecondary, lineHeight: 18, marginTop: 2 },
  readMoreRow: { flexDirection: "row", alignItems: "center", gap: 5, marginTop: 6 },
  readMore: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold },
  prayerSnippet: { fontFamily: fonts.bodyRegular, fontSize: 13.5, color: colors.textSecondary, lineHeight: 20, fontStyle: "italic" },
  guideTile: {
    flexDirection: "row", alignItems: "center", gap: spacing.sm,
    backgroundColor: colors.surfaceDark, borderRadius: radius.md,
    paddingVertical: spacing.sm, paddingHorizontal: spacing.md, marginTop: 4,
  },
  guideTitle: { fontFamily: fonts.headingSemi, fontSize: 14.5, color: "#FBF6E9" },
  guideSub: { fontFamily: fonts.bodyRegular, fontSize: 12, color: "#E9E2D0", marginTop: 1 },
  verseLine: { marginTop: spacing.sm, borderLeftWidth: 3, borderLeftColor: colors.gold, paddingLeft: spacing.sm },
  verseText: { fontFamily: fonts.bodyItalic, fontSize: 13.5, color: colors.textSecondary, lineHeight: 20 },
  verseRef: { fontFamily: fonts.uiSemi, fontSize: 11.5, color: colors.gold, marginTop: 3 },
});

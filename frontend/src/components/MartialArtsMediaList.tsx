import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { colors, fonts, radius, spacing } from "@/src/theme";
import { MARTIAL_ARTS_MEDIA, MediaKind, MediaRec } from "@/src/utils/martial-arts-media";

type Props = {
  /** Discipline id, e.g. "boxing", "kendo", "goju_ryu", "bjj"… */
  disciplineId: string;
  /** Discipline display name, used in the section title */
  disciplineName: string;
  /** Initially collapsed (true) or expanded (false) */
  initiallyCollapsed?: boolean;
};

const KIND_ICON: Record<MediaKind, string> = {
  Film: "film-outline",
  Series: "tv-outline",
  Anime: "color-palette-outline",
  Documentary: "videocam-outline",
};

/**
 * Curated list of films, anime, series, and documentaries where the
 * chosen martial art is a central element. Designed to be read BEFORE
 * a training session, as cultural / formational context.
 *
 * Catholic-themed works get a small cross icon for quick scanning.
 */
export default function MartialArtsMediaList({
  disciplineId,
  disciplineName,
  initiallyCollapsed = true,
}: Props) {
  const items: MediaRec[] = MARTIAL_ARTS_MEDIA[disciplineId] || [];
  const [collapsed, setCollapsed] = useState<boolean>(initiallyCollapsed);

  if (items.length === 0) return null;

  const catholicCount = items.filter((m) => m.catholic).length;

  return (
    <View style={styles.card} testID="sd-media-card">
      <Pressable
        onPress={() => setCollapsed((c) => !c)}
        style={({ pressed }) => [styles.header, pressed && { opacity: 0.7 }]}
        accessibilityRole="button"
        accessibilityLabel={`${collapsed ? "Show" : "Hide"} films and anime for ${disciplineName}`}
        testID="sd-media-toggle"
      >
        <View style={styles.headerLeft}>
          <Ionicons name="film" size={16} color={colors.gold} />
          <View style={{ flex: 1 }}>
            <Text style={styles.eyebrow}>BEFORE YOU TRAIN</Text>
            <Text style={styles.title}>Films &amp; anime · {disciplineName}</Text>
          </View>
        </View>
        <View style={styles.headerRight}>
          <Text style={styles.count}>{items.length}</Text>
          <Ionicons
            name={collapsed ? "chevron-down" : "chevron-up"}
            size={18}
            color={colors.textSecondary}
          />
        </View>
      </Pressable>

      {/* Sub-line summary */}
      {collapsed ? (
        <Text style={styles.subSummary} testID="sd-media-summary">
          {items.length} recommendations
          {catholicCount > 0 ? `  ·  ${catholicCount} with Catholic themes` : ""}
        </Text>
      ) : null}

      {/* Expanded list */}
      {!collapsed ? (
        <View style={styles.list} testID="sd-media-list">
          {items.map((m, i) => (
            <View
              key={`${m.title}-${m.year}`}
              style={[styles.item, i < items.length - 1 && styles.itemDivider]}
              testID={`sd-media-item-${i}`}
            >
              <View style={styles.itemHeader}>
                <View style={styles.kindBadge}>
                  <Ionicons name={KIND_ICON[m.kind] as any} size={11} color={colors.gold} />
                  <Text style={styles.kindBadgeText}>{m.kind.toUpperCase()}</Text>
                </View>
                {m.catholic ? (
                  <View style={styles.catholicBadge} testID={`sd-media-catholic-${i}`}>
                    <Ionicons name="rose-outline" size={11} color={colors.liturgical.purple} />
                    <Text style={styles.catholicBadgeText}>CATHOLIC</Text>
                  </View>
                ) : null}
                {m.origin ? <Text style={styles.origin}>{m.origin}</Text> : null}
              </View>
              <Text style={styles.itemTitle} numberOfLines={2}>
                {m.title} <Text style={styles.itemYear}>({m.year})</Text>
              </Text>
              <Text style={styles.itemWhy}>{m.why}</Text>
            </View>
          ))}
          <Text style={styles.footnote} testID="sd-media-footnote">
            Watch with discernment — not every work is suitable for every viewer.
            These are listed for the martial-arts content, not as blanket endorsements.
          </Text>
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
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.sm,
  },
  headerLeft: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  headerRight: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
  },
  eyebrow: {
    fontFamily: fonts.uiSemi,
    fontSize: 9,
    letterSpacing: 1.8,
    color: colors.gold,
  },
  title: {
    fontFamily: fonts.headingSemi,
    fontSize: 15,
    color: colors.textPrimary,
    marginTop: 1,
  },
  count: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.textSecondary,
    backgroundColor: colors.borderSoft,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: radius.round,
    minWidth: 22,
    textAlign: "center",
  },
  subSummary: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: spacing.xs,
    marginLeft: spacing.lg + 4,
  },
  list: {
    marginTop: spacing.sm,
  },
  item: {
    paddingVertical: spacing.sm,
  },
  itemDivider: {
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  itemHeader: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 6,
    marginBottom: 4,
  },
  kindBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: "rgba(212,175,55,0.12)",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: "rgba(212,175,55,0.3)",
  },
  kindBadgeText: {
    fontFamily: fonts.uiSemi,
    fontSize: 9,
    letterSpacing: 0.8,
    color: colors.gold,
  },
  catholicBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: "rgba(89,75,121,0.12)",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: "rgba(89,75,121,0.3)",
  },
  catholicBadgeText: {
    fontFamily: fonts.uiSemi,
    fontSize: 9,
    letterSpacing: 0.8,
    color: colors.liturgical.purple,
  },
  origin: {
    fontFamily: fonts.uiMedium,
    fontSize: 10,
    color: colors.textMuted,
    marginLeft: 2,
  },
  itemTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 15,
    color: colors.textPrimary,
    marginBottom: 4,
  },
  itemYear: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textSecondary,
  },
  itemWhy: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 20,
  },
  footnote: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 11,
    color: colors.textMuted,
    marginTop: spacing.sm,
    textAlign: "center",
    paddingHorizontal: spacing.xs,
  },
});

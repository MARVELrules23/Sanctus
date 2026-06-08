import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { colors, fonts, radius, spacing } from "@/src/theme";
import { MotionMode } from "@/src/utils/motion-classifier";
import { describeMovement } from "@/src/utils/movement-descriptions";

type Props = {
  /** Display name of the step (e.g. "Round kick") */
  title?: string;
  /** Classified motion mode (used as fallback when title doesn't match an override) */
  motion: MotionMode;
  /** Whether the step is purely a rest interval — render a calmer card */
  isRest?: boolean;
};

/**
 * MovementBreakdown — a clean, text-first replacement for the prior
 * stick-figure silhouette. Reads like a coach's cue card.
 */
export default function MovementBreakdown({ title, motion, isRest }: Props) {
  const bd = describeMovement(title, motion);

  if (isRest) {
    return (
      <View style={[styles.card, styles.restCard]} testID="movement-breakdown-rest">
        <View style={styles.headerRow}>
          <View style={[styles.iconBubble, { backgroundColor: colors.textMuted }]}>
            <Ionicons name="pause" size={18} color="#FAF9F6" />
          </View>
          <Text style={styles.headline}>Rest & reset</Text>
        </View>
        <Text style={styles.restBody}>
          Lower the hands. Shake out the legs. Inhale through the nose, exhale long.
          Reset your stance for the next round.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.card} testID="movement-breakdown">
      {/* Header */}
      <View style={styles.headerRow}>
        <View style={styles.iconBubble}>
          <Ionicons name={bd.icon as any} size={18} color={colors.gold} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.eyebrow}>MOVEMENT BREAKDOWN</Text>
          <Text style={styles.headline} numberOfLines={2}>{bd.headline}</Text>
        </View>
      </View>

      {/* How to */}
      <View style={styles.section}>
        <Text style={styles.sectionLabel}>HOW TO PERFORM</Text>
        {bd.how_to.map((s, i) => (
          <View key={i} style={styles.stepRow}>
            <View style={styles.stepNum}>
              <Text style={styles.stepNumText}>{i + 1}</Text>
            </View>
            <Text style={styles.stepText}>{s}</Text>
          </View>
        ))}
      </View>

      {/* Cues */}
      {bd.cues && bd.cues.length > 0 ? (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>CUES</Text>
          {bd.cues.map((c, i) => (
            <View key={i} style={styles.cueRow}>
              <Ionicons name="ellipse" size={6} color={colors.gold} style={{ marginTop: 7, marginRight: 8 }} />
              <Text style={styles.cueText}>{c}</Text>
            </View>
          ))}
        </View>
      ) : null}

      {/* Errors */}
      {bd.errors && bd.errors.length > 0 ? (
        <View style={styles.errorSection}>
          <Text style={styles.errorLabel}>AVOID</Text>
          {bd.errors.map((e, i) => (
            <View key={i} style={styles.cueRow}>
              <Ionicons name="close" size={12} color={colors.liturgical.red} style={{ marginTop: 3, marginRight: 6 }} />
              <Text style={styles.errorText}>{e}</Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    alignSelf: "stretch",
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.md,
    marginVertical: spacing.sm,
  },
  restCard: {
    backgroundColor: "rgba(28,40,65,0.04)",
    borderColor: colors.borderSoft,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  iconBubble: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  eyebrow: {
    fontFamily: fonts.uiSemi,
    fontSize: 9,
    letterSpacing: 1.8,
    color: colors.gold,
  },
  headline: {
    fontFamily: fonts.headingSemi,
    fontSize: 16,
    color: colors.textPrimary,
    marginTop: 1,
  },
  section: {
    marginTop: spacing.sm,
    paddingTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
  },
  sectionLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1.6,
    color: colors.primary,
    marginBottom: spacing.sm,
  },
  stepRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  stepNum: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 1,
  },
  stepNumText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 11,
  },
  stepText: {
    flex: 1,
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textPrimary,
    lineHeight: 21,
  },
  cueRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 6,
  },
  cueText: {
    flex: 1,
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 20,
  },
  errorSection: {
    marginTop: spacing.sm,
    paddingTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
  },
  errorLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1.6,
    color: colors.liturgical.red,
    marginBottom: spacing.xs,
  },
  errorText: {
    flex: 1,
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.liturgical.red,
    lineHeight: 20,
  },
  restBody: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
    textAlign: "center",
    paddingHorizontal: spacing.sm,
  },
});

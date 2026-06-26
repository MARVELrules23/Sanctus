import React from "react";
import { View, Text, StyleSheet, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { AutoText } from "@/src/auto-text";
import { colors, fonts, radius, spacing } from "@/src/theme";

export type BadgeTier = "gold" | "silver" | "bronze" | "none";

export type BadgeInfo = {
  tier: BadgeTier;
  fallen: number;
  completed_days: number;
  elapsed: number;
  gold_max: number;
  silver_max: number;
  final: boolean;
};

const TIER_META: Record<Exclude<BadgeTier, "none">, { label: string; color: string; ring: string }> = {
  gold: { label: "Gold", color: "#C8A24B", ring: "#F1E2B0" },
  silver: { label: "Silver", color: "#9AA3AD", ring: "#E2E6EA" },
  bronze: { label: "Bronze", color: "#B07A4E", ring: "#E8CDB6" },
};

/** Small medal pill — used in plan lists. */
export function BadgePill({ badge }: { badge?: BadgeInfo }) {
  if (!badge || badge.tier === "none") return null;
  const m = TIER_META[badge.tier];
  return (
    <View style={[pill.wrap, { borderColor: m.color }]} testID={`badge-pill-${badge.tier}`}>
      <Ionicons name="medal" size={12} color={m.color} />
      <AutoText style={[pill.text, { color: m.color }]}>{m.label}</AutoText>
    </View>
  );
}

const pill = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    borderWidth: 1,
    borderRadius: radius.round,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  text: { fontFamily: fonts.uiMedium, fontSize: 11, letterSpacing: 0.3 },
});

/** Full perseverance card — used in plan detail. Shows the medal, the rule, and an "info" tap. */
export default function PerseveranceBadge({ badge, days }: { badge?: BadgeInfo; days: number }) {
  const [open, setOpen] = React.useState(false);
  if (!badge) return null;
  const isNone = badge.tier === "none";
  const m = isNone ? { label: "Not started", color: colors.textMuted, ring: colors.borderSoft } : TIER_META[badge.tier as Exclude<BadgeTier, "none">];

  return (
    <View style={card.wrap} testID="perseverance-badge">
      <View style={[card.medal, { borderColor: m.ring, backgroundColor: isNone ? "transparent" : m.ring + "44" }]}>
        <Ionicons name={isNone ? "ribbon-outline" : "medal"} size={26} color={m.color} />
      </View>
      <View style={{ flex: 1 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
          <AutoText style={[card.tier, { color: m.color }]}>{m.label}</AutoText>
          {badge.final ? <AutoText style={card.finalTag}>Final</AutoText> : !isNone ? <AutoText style={card.liveTag}>Current standing</AutoText> : null}
          <Pressable onPress={() => setOpen((o) => !o)} hitSlop={10} testID="badge-info-toggle">
            <Ionicons name="information-circle-outline" size={16} color={colors.textMuted} />
          </Pressable>
        </View>
        {isNone ? (
          <AutoText style={card.sub}>Begin checking off your days to earn a medal of perseverance.</AutoText>
        ) : (
          <AutoText style={card.sub}>
            {badge.completed_days} of {badge.elapsed} days kept · {badge.fallen} missed
          </AutoText>
        )}
        {open ? (
          <View style={card.rule}>
            <AutoText style={card.ruleText}>
              Perseverance, not perfection. Over {days} days: Gold = up to {badge.gold_max} missed, Silver = up to {badge.silver_max} missed, Bronze = beyond that. The saints fell and rose again — so can you.
            </AutoText>
          </View>
        ) : null}
      </View>
    </View>
  );
}

const card = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginTop: spacing.sm,
  },
  medal: {
    width: 52,
    height: 52,
    borderRadius: 26,
    borderWidth: 2,
    alignItems: "center",
    justifyContent: "center",
  },
  tier: { fontFamily: fonts.headingSemi, fontSize: 18 },
  finalTag: {
    fontFamily: fonts.uiMedium,
    fontSize: 10,
    color: colors.gold,
    letterSpacing: 0.5,
    textTransform: "uppercase",
  },
  liveTag: {
    fontFamily: fonts.bodyRegular,
    fontSize: 10,
    color: colors.textMuted,
    letterSpacing: 0.3,
  },
  sub: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textSecondary, marginTop: 2 },
  rule: {
    marginTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
    paddingTop: spacing.sm,
  },
  ruleText: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textSecondary, lineHeight: 18, fontStyle: "italic" },
});

/**
 * SaintOfTheDayCard — surfaces today's Saint / Blessed / Venerable on the
 * Home tab. Tap takes the user to the detail screen.
 *
 * Renders nothing while loading (rather than a skeleton) when there is no
 * approved entry for the day, so users never see an empty card.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";

import { SaintPublic, getSaintsToday } from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const RANK_LABEL: Record<SaintPublic["rank"], string> = {
  saint: "SAINT OF THE DAY",
  blessed: "BLESSED OF THE DAY",
  venerable: "VENERABLE OF THE DAY",
};

export default function SaintOfTheDayCard({ date }: { date: string }) {
  const router = useRouter();
  const { user } = useAuth();
  const [primary, setPrimary] = useState<SaintPublic | null>(null);
  const [others, setOthers] = useState<SaintPublic[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    // Don't even try when we have no auth context yet — the endpoint is
    // logged-in-only and an anonymous call would just log 401s.
    if (!user) {
      setPrimary(null);
      setOthers([]);
      setLoaded(true);
      return;
    }
    try {
      const r = await getSaintsToday(date);
      setPrimary(r.primary);
      setOthers(r.others || []);
    } catch {
      setPrimary(null);
      setOthers([]);
    } finally {
      setLoaded(true);
    }
  }, [date, user]);

  useEffect(() => { void load(); }, [load]);

  // Until the first response, render nothing so we don't push other home-tab
  // cards down with a flickering skeleton.
  if (!loaded || !primary) return null;

  const onOpen = () => router.push({ pathname: "/saints/[id]", params: { id: primary.saint_id } });

  return (
    <View testID="saint-of-day-card" style={styles.card}>
      <View style={styles.headerRow}>
        <Ionicons name="sparkles-outline" size={16} color={colors.gold} />
        <Text style={styles.headerLabel}>{RANK_LABEL[primary.rank]}</Text>
      </View>

      <Pressable
        testID="saint-of-day-tap"
        onPress={onOpen}
        style={({ pressed }) => [styles.body, pressed && styles.pressed]}
      >
        {primary.picture_url ? (
          <Image
            source={{ uri: primary.picture_url }}
            style={styles.portrait}
            resizeMode="cover"
            testID="saint-of-day-portrait"
            accessible
            accessibilityLabel={primary.name}
          />
        ) : (
          <View style={[styles.portrait, styles.portraitFallback]}>
            <Ionicons name="flower-outline" size={28} color={colors.gold} />
          </View>
        )}
        <View style={styles.textCol}>
          <Text style={styles.name} numberOfLines={2} testID="saint-of-day-name">
            {primary.name}
          </Text>
          {primary.quote ? (
            <Text style={styles.quote} numberOfLines={4}>
              “{primary.quote}”
            </Text>
          ) : null}
          <View style={styles.tapHint}>
            <Text style={styles.tapHintText}>Read more</Text>
            <Ionicons name="chevron-forward" size={12} color={colors.gold} />
          </View>
        </View>
      </Pressable>

      {others.length > 0 ? (
        <View style={styles.expandWrap}>
          <Pressable
            testID="saint-of-day-toggle-others"
            onPress={() => setExpanded((v) => !v)}
            hitSlop={8}
            style={({ pressed }) => [styles.expandRow, pressed && styles.pressed]}
          >
            <Text style={styles.expandLabel}>
              {expanded ? "Hide" : `${others.length} more from today`}
            </Text>
            <Ionicons
              name={expanded ? "chevron-up" : "chevron-down"}
              size={14}
              color={colors.gold}
            />
          </Pressable>
          {expanded
            ? others.map((o) => (
                <Pressable
                  key={o.saint_id}
                  testID={`saint-of-day-other-${o.saint_id}`}
                  onPress={() => router.push({ pathname: "/saints/[id]", params: { id: o.saint_id } })}
                  style={({ pressed }) => [styles.otherRow, pressed && styles.pressed]}
                >
                  {o.picture_url ? (
                    <Image source={{ uri: o.picture_url }} style={styles.otherThumb} resizeMode="cover" />
                  ) : (
                    <View style={[styles.otherThumb, styles.portraitFallback]}>
                      <Ionicons name="flower-outline" size={14} color={colors.gold} />
                    </View>
                  )}
                  <View style={{ flex: 1 }}>
                    <Text style={styles.otherName} numberOfLines={1}>{o.name}</Text>
                    <Text style={styles.otherRank}>
                      {o.rank === "saint" ? "Saint" : o.rank === "blessed" ? "Blessed" : "Venerable"}
                    </Text>
                  </View>
                  <Ionicons name="chevron-forward" size={14} color={colors.textMuted} />
                </Pressable>
              ))
            : null}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    marginHorizontal: spacing.lg,
    marginBottom: spacing.lg,
    padding: spacing.lg,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: spacing.sm,
  },
  headerLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 2.5,
    color: colors.gold,
  },
  body: {
    flexDirection: "row",
    gap: spacing.md,
  },
  portrait: {
    width: 92,
    height: 110,
    borderRadius: radius.sm,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  portraitFallback: {
    alignItems: "center",
    justifyContent: "center",
  },
  textCol: {
    flex: 1,
    justifyContent: "space-between",
    paddingVertical: 2,
  },
  name: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
  },
  quote: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 13,
    lineHeight: 18,
    color: colors.textSecondary,
    marginTop: 4,
  },
  tapHint: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 8,
  },
  tapHintText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.2,
    color: colors.gold,
  },
  pressed: { opacity: 0.7 },
  expandWrap: {
    marginTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
    paddingTop: spacing.sm,
  },
  expandRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 4,
  },
  expandLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    letterSpacing: 1.2,
    color: colors.gold,
  },
  otherRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: 8,
  },
  otherThumb: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  otherName: {
    fontFamily: fonts.uiSemi,
    fontSize: 13,
    color: colors.textPrimary,
  },
  otherRank: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 1,
  },
});

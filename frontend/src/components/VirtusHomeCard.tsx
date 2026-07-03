/**
 * VirtusHomeCard — home-screen card (replaces the old Journal preview box).
 *
 * Shows the user's active virtue plan with progress, or a friendly CTA to
 * explore the virtues. Free for all.
 */
import React, { useCallback, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useRouter } from "expo-router";

import { listVirtuePlans, VirtuePlan } from "@/src/api";
import { todayISO } from "@/src/date-utils";
import { colors, fonts, radius, spacing } from "@/src/theme";

export default function VirtusHomeCard() {
  const router = useRouter();
  const [plan, setPlan] = useState<VirtuePlan | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await listVirtuePlans();
      const active = (r.items || []).find((p) => p.active) || null;
      setPlan(active);
    } catch {
      setPlan(null);
    }
  }, []);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  return (
    <View style={styles.card} testID="virtus-home-card">
      <View style={styles.cardHeader}>
        <Ionicons name="sparkles-outline" size={18} color={colors.gold} />
        <Text style={styles.cardHeaderText}>VIRTUS</Text>
        <View style={{ flex: 1 }} />
        <Pressable testID="virtus-home-open" onPress={() => router.push("/virtus" as any)} hitSlop={8}>
          <Ionicons name="arrow-forward" size={20} color={colors.gold} />
        </Pressable>
      </View>

      {plan ? (
        <Pressable
          testID="virtus-home-plan"
          onPress={() => router.push({ pathname: "/virtus/plan/[id]", params: { id: plan.id } } as any)}
          style={({ pressed }) => [styles.planRow, pressed && { opacity: 0.85 }]}
        >
          <View style={{ flex: 1 }}>
            <Text style={styles.planTitle} numberOfLines={1}>
              {plan.virtues.map((v) => v.name).join(" · ")}
            </Text>
            <Text style={styles.planSub}>{(plan.checkins?.[todayISO()] || []).length}/{plan.total} today · ends {plan.end_date}</Text>
            <View style={styles.track}>
              <View style={[styles.fill, { width: `${plan.total ? (plan.completed / plan.total) * 100 : 0}%` }]} />
            </View>
          </View>
          <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
        </Pressable>
      ) : (
        <>
          <Text style={styles.empty}>
            Grow in holiness — study a virtue and set a goal to live it well.
          </Text>
          <Pressable
            testID="virtus-home-explore"
            onPress={() => router.push("/virtus" as any)}
            style={({ pressed }) => [styles.primaryBtn, pressed && { opacity: 0.85 }]}
          >
            <Ionicons name="sparkles" size={16} color={colors.gold} />
            <Text style={styles.primaryBtnText}>Explore the virtues</Text>
          </Pressable>
        </>
      )}
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
  },
  cardHeader: { flexDirection: "row", alignItems: "center", gap: 8 },
  cardHeaderText: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 1.4, color: colors.textMuted },
  empty: { fontFamily: fonts.bodyRegular, fontSize: 14, lineHeight: 21, color: colors.textSecondary },
  primaryBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    paddingVertical: 12, borderRadius: radius.round, backgroundColor: colors.primary, marginTop: 2,
  },
  primaryBtnText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.gold, letterSpacing: 0.4 },
  planRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  planTitle: { fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary },
  planSub: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textMuted, marginTop: 2 },
  track: { height: 6, borderRadius: 3, backgroundColor: colors.borderSoft, marginTop: 8, overflow: "hidden" },
  fill: { height: 6, borderRadius: 3, backgroundColor: colors.gold },
});

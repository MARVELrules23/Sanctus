import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { api } from "@/src/api";
import { useI18n } from "@/src/i18n";
import { AutoText as Text } from "@/src/auto-text";
import { colors, fonts, radius, spacing } from "@/src/theme";

export type MiracleClaim = {
  claim_id: string;
  title: string;
  summary: string;
  type: string;
  verdict: string;
  location?: string | null;
  reported_year?: string | null;
  source_name?: string | null;
  source_url: string;
};

const VERDICT_META: Record<string, { label: string; color: string; icon: string }> = {
  approved: { label: "Approved by the Church", color: "#2A5A3B", icon: "checkmark-circle" },
  investigating: { label: "Under Investigation", color: "#C5A059", icon: "search-circle" },
  reported: { label: "Reported Claim", color: "#5C5C60", icon: "ellipse-outline" },
  not_supernatural: { label: "Declared Not Supernatural", color: "#9E1B1B", icon: "close-circle" },
};

const TYPE_ICON: Record<string, string> = {
  eucharistic: "flame-outline",
  marian: "flower-outline",
  healing: "medkit-outline",
  incorruptible: "body-outline",
  apparition: "sparkles-outline",
  other: "star-outline",
};

function VerdictBadge({ verdict }: { verdict: string }) {
  const m = VERDICT_META[verdict] ?? VERDICT_META.reported;
  return (
    <View style={[styles.badge, { backgroundColor: m.color + "1A", borderColor: m.color + "55" }]}>
      <Ionicons name={m.icon as any} size={13} color={m.color} />
      <Text style={[styles.badgeText, { color: m.color }]}>{m.label}</Text>
    </View>
  );
}

function ClaimCard({ claim }: { claim: MiracleClaim }) {
  const m = VERDICT_META[claim.verdict] ?? VERDICT_META.reported;
  const meta = [claim.location, claim.reported_year].filter(Boolean).join(" · ");
  return (
    <View style={styles.card}>
      <View style={styles.cardHead}>
        <View style={[styles.typeIcon, { backgroundColor: m.color + "14" }]}>
          <Ionicons name={(TYPE_ICON[claim.type] ?? TYPE_ICON.other) as any} size={20} color={m.color} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>{claim.title}</Text>
          {meta ? <Text style={styles.meta}>{meta}</Text> : null}
        </View>
      </View>

      <VerdictBadge verdict={claim.verdict} />

      <Text style={styles.summary}>{claim.summary}</Text>

      {claim.source_url ? (
        <Pressable
          onPress={() => Linking.openURL(claim.source_url)}
          style={({ pressed }) => [styles.sourceBtn, pressed && { opacity: 0.6 }]}
          testID={`miracle-source-${claim.claim_id}`}
        >
          <Ionicons name="open-outline" size={15} color={colors.primary} />
          <Text style={styles.sourceText}>
            Read the report{claim.source_name ? ` · ${claim.source_name}` : ""}
          </Text>
        </Pressable>
      ) : null}
    </View>
  );
}

export default function MiraclesScreen() {
  const router = useRouter();
  const { lang } = useI18n();
  const [items, setItems] = useState<MiracleClaim[] | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await api<{ items: MiracleClaim[] }>("/miracles");
      setItems(res.items || []);
    } catch {
      setItems([]);
    }
  }, [lang]);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={24} color={colors.primary} />
        </Pressable>
        <View style={{ flex: 1 }}>
          <Text style={styles.headerTitle}>Live Feed</Text>
          <Text style={styles.headerSub}>Reported miracles & their Church status</Text>
        </View>
        <Ionicons name="sparkles" size={20} color={colors.gold} />
      </View>

      <ScrollView
        contentContainerStyle={{ padding: spacing.md, paddingBottom: spacing.xxl }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
      >
        <View style={styles.disclaimer}>
          <Ionicons name="information-circle-outline" size={16} color={colors.textMuted} />
          <Text style={styles.disclaimerText}>
            Each entry is a reported claim. The badge shows the Church&apos;s current standing — always
            consult the source and your local Church.
          </Text>
        </View>

        {items === null ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
        ) : items.length === 0 ? (
          <Text style={styles.empty}>No reports yet. Pull to refresh.</Text>
        ) : (
          items.map((c) => <ClaimCard key={c.claim_id} claim={c} />)
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
    backgroundColor: colors.surface,
  },
  backBtn: { padding: 2 },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 22, color: colors.primary },
  headerSub: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textMuted },
  disclaimer: {
    flexDirection: "row",
    gap: 6,
    backgroundColor: colors.borderSoft,
    borderRadius: radius.md,
    padding: spacing.sm,
    marginBottom: spacing.md,
  },
  disclaimerText: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textSecondary, lineHeight: 17 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  cardHead: { flexDirection: "row", gap: spacing.sm, alignItems: "center", marginBottom: spacing.sm },
  typeIcon: { width: 40, height: 40, borderRadius: radius.md, alignItems: "center", justifyContent: "center" },
  title: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.primary, lineHeight: 22 },
  meta: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textMuted, marginTop: 2 },
  badge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    alignSelf: "flex-start",
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: radius.round,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginBottom: spacing.sm,
  },
  badgeText: { fontFamily: fonts.uiSemi, fontSize: 11.5 },
  summary: { fontFamily: fonts.bodyRegular, fontSize: 14.5, color: colors.textPrimary, lineHeight: 21 },
  sourceBtn: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: spacing.sm },
  sourceText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.primary },
  empty: { fontFamily: fonts.bodyItalic, fontSize: 14, color: colors.textMuted, textAlign: "center", marginTop: spacing.xl },
});

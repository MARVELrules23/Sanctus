import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useFocusEffect, useRouter } from "expo-router";

import { api } from "@/src/api";
import { useI18n } from "@/src/i18n";
import { AutoText as Text } from "@/src/auto-text";
import { colors, fonts, radius, spacing } from "@/src/theme";

type ProcessStage = { label: string; done: boolean; current: boolean };
type MiracleProcess = { name: string; stages: ProcessStage[]; current_label: string; note: string };

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
  process?: MiracleProcess;
  updated_at?: string | null;
  created_at?: string | null;
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

const VERDICT_FILTERS = [
  { k: "", label: "All" },
  { k: "approved", label: "Approved" },
  { k: "investigating", label: "Investigating" },
  { k: "reported", label: "Reported" },
  { k: "not_supernatural", label: "Not supernatural" },
];

const TYPE_FILTERS = [
  { k: "", label: "All types" },
  { k: "eucharistic", label: "Eucharistic" },
  { k: "marian", label: "Marian" },
  { k: "apparition", label: "Apparition" },
  { k: "healing", label: "Healing" },
  { k: "incorruptible", label: "Incorruptible" },
  { k: "other", label: "Other" },
];

function relTime(iso?: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (isNaN(then)) return "";
  const s = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function ProcessLadder({ process }: { process: MiracleProcess }) {
  return (
    <View style={styles.process} testID="miracle-process">
      <View style={styles.processHead}>
        <Ionicons name="git-commit-outline" size={14} color={colors.primary} />
        <Text style={styles.processName}>{process.name}</Text>
      </View>
      {process.stages.map((s, i) => (
        <View key={i} style={styles.stageRow}>
          <View
            style={[
              styles.stageDot,
              s.done && styles.stageDotDone,
              s.current && styles.stageDotCurrent,
            ]}
          >
            {s.done ? (
              <Ionicons name="checkmark" size={11} color="#FFF" />
            ) : s.current ? (
              <View style={styles.stageInner} />
            ) : null}
          </View>
          <Text style={[styles.stageLabel, s.current && styles.stageLabelCurrent]}>{s.label}</Text>
          {s.current ? <Text style={styles.nowTag}>now</Text> : null}
        </View>
      ))}
      {process.note ? (
        <View style={styles.handledBox}>
          <Text style={styles.handledLabel}>How it&apos;s being handled</Text>
          <Text style={styles.handledText}>{process.note}</Text>
        </View>
      ) : null}
    </View>
  );
}

function VerdictBadge({ verdict, currentLabel }: { verdict: string; currentLabel?: string }) {
  const m = VERDICT_META[verdict] ?? VERDICT_META.reported;
  return (
    <View style={[styles.badge, { backgroundColor: m.color + "1A", borderColor: m.color + "55" }]}>
      <Ionicons name={m.icon as any} size={13} color={m.color} />
      <Text style={[styles.badgeText, { color: m.color }]}>{currentLabel || m.label}</Text>
    </View>
  );
}

function ClaimCard({ claim }: { claim: MiracleClaim }) {
  const m = VERDICT_META[claim.verdict] ?? VERDICT_META.reported;
  const meta = [claim.location, claim.reported_year].filter(Boolean).join(" · ");
  return (
    <View style={styles.card} testID={`miracle-card-${claim.claim_id}`}>
      <View style={styles.cardHead}>
        <View style={[styles.typeIcon, { backgroundColor: m.color + "14" }]}>
          <Ionicons name={(TYPE_ICON[claim.type] ?? TYPE_ICON.other) as any} size={20} color={m.color} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>{claim.title}</Text>
          {meta ? <Text style={styles.meta}>{meta}</Text> : null}
        </View>
      </View>

      <VerdictBadge verdict={claim.verdict} currentLabel={claim.process?.current_label} />

      <Text style={styles.summary}>{claim.summary}</Text>

      {claim.process ? <ProcessLadder process={claim.process} /> : null}

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
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [typeF, setTypeF] = useState("");
  const [verdictF, setVerdictF] = useState("");
  const [updatedAt, setUpdatedAt] = useState<number>(0);
  const [tick, setTick] = useState(0); // re-render to refresh relative time
  const newestRef = useRef<string>("");

  // Debounce the search box.
  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 350);
    return () => clearTimeout(t);
  }, [query]);

  const load = useCallback(
    async (silent = false) => {
      try {
        const params = new URLSearchParams();
        if (debounced) params.set("q", debounced);
        if (typeF) params.set("type", typeF);
        if (verdictF) params.set("verdict", verdictF);
        const qs = params.toString();
        const res = await api<{ items: MiracleClaim[] }>(`/miracles${qs ? `?${qs}` : ""}`);
        const next = res.items || [];
        setItems(next);
        setUpdatedAt(Date.now());
        newestRef.current = next[0]?.created_at || "";
      } catch {
        if (!silent) setItems([]);
      }
    },
    [debounced, typeF, verdictF, lang],
  );

  useEffect(() => {
    setItems(null);
    load();
  }, [load]);

  // Live updates: poll every 45s while the screen is focused, and tick the
  // "updated X ago" label every 20s.
  useFocusEffect(
    useCallback(() => {
      const poll = setInterval(() => load(true), 45000);
      const timeTick = setInterval(() => setTick((t) => t + 1), 20000);
      return () => {
        clearInterval(poll);
        clearInterval(timeTick);
      };
    }, [load]),
  );

  const onRefresh = async () => {
    setRefreshing(true);
    await load(true);
    setRefreshing(false);
  };

  const updatedLabel = updatedAt ? relTime(new Date(updatedAt).toISOString()) : "";

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={24} color={colors.primary} />
        </Pressable>
        <View style={{ flex: 1 }}>
          <Text style={styles.headerTitle}>Live Feed</Text>
          <View style={styles.liveRow}>
            <View style={styles.liveDot} />
            <Text style={styles.headerSub} key={tick}>
              {updatedLabel ? `Live · updated ${updatedLabel}` : "Reported miracles & their Church status"}
            </Text>
          </View>
        </View>
        <Ionicons name="sparkles" size={20} color={colors.gold} />
      </View>

      {/* Search engine */}
      <View style={styles.searchWrap}>
        <View style={styles.searchBox}>
          <Ionicons name="search" size={16} color={colors.textMuted} />
          <TextInput
            testID="miracle-search"
            value={query}
            onChangeText={setQuery}
            placeholder="Search miracles, places, saints…"
            placeholderTextColor={colors.textMuted}
            style={styles.searchInput}
            returnKeyType="search"
          />
          {query ? (
            <Pressable onPress={() => setQuery("")} hitSlop={8} testID="miracle-search-clear">
              <Ionicons name="close-circle" size={16} color={colors.textMuted} />
            </Pressable>
          ) : null}
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
          {VERDICT_FILTERS.map((f) => (
            <Pressable
              key={`v-${f.k || "all"}`}
              testID={`miracle-verdict-${f.k || "all"}`}
              onPress={() => setVerdictF(f.k)}
              style={[styles.chip, verdictF === f.k && styles.chipActive]}
            >
              <Text style={[styles.chipText, verdictF === f.k && styles.chipTextActive]}>{f.label}</Text>
            </Pressable>
          ))}
        </ScrollView>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
          {TYPE_FILTERS.map((f) => (
            <Pressable
              key={`t-${f.k || "all"}`}
              testID={`miracle-type-${f.k || "all"}`}
              onPress={() => setTypeF(f.k)}
              style={[styles.chipSm, typeF === f.k && styles.chipActive]}
            >
              <Text style={[styles.chipTextSm, typeF === f.k && styles.chipTextActive]}>{f.label}</Text>
            </Pressable>
          ))}
        </ScrollView>
      </View>

      <ScrollView
        contentContainerStyle={{ padding: spacing.md, paddingBottom: spacing.xxl }}
        keyboardShouldPersistTaps="handled"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
      >
        <View style={styles.disclaimer}>
          <Ionicons name="information-circle-outline" size={16} color={colors.textMuted} />
          <Text style={styles.disclaimerText}>
            Each entry is a reported claim. The ladder shows the Church&apos;s process and where it
            currently stands — always consult the source and your local Church.
          </Text>
        </View>

        {items === null ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
        ) : items.length === 0 ? (
          <Text style={styles.empty}>
            {debounced || typeF || verdictF ? "No matching reports. Try a different search or filter." : "No reports yet. Pull to refresh."}
          </Text>
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
  liveRow: { flexDirection: "row", alignItems: "center", gap: 5 },
  liveDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: "#2A5A3B" },
  headerSub: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textMuted },
  searchWrap: {
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: spacing.xs,
    backgroundColor: colors.surface,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
    gap: spacing.xs,
  },
  searchBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.background,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.md,
    height: 40,
  },
  searchInput: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary, paddingVertical: 0 },
  chipRow: { gap: 8, paddingVertical: 4, paddingRight: spacing.md },
  chip: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: radius.round, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.background },
  chipSm: { paddingHorizontal: 12, paddingVertical: 5, borderRadius: radius.round, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.background },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textSecondary },
  chipTextSm: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textSecondary },
  chipTextActive: { color: colors.gold },
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
  process: {
    marginTop: spacing.md,
    backgroundColor: colors.background,
    borderRadius: radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    padding: spacing.sm,
  },
  processHead: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: spacing.sm },
  processName: { flex: 1, fontFamily: fonts.uiSemi, fontSize: 12.5, color: colors.primary },
  stageRow: { flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 3 },
  stageDot: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 1.5,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  stageDotDone: { backgroundColor: "#2A5A3B", borderColor: "#2A5A3B" },
  stageDotCurrent: { borderColor: colors.gold, borderWidth: 2 },
  stageInner: { width: 7, height: 7, borderRadius: 4, backgroundColor: colors.gold },
  stageLabel: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary },
  stageLabelCurrent: { fontFamily: fonts.uiSemi, color: colors.primary },
  nowTag: { fontFamily: fonts.uiSemi, fontSize: 10, color: colors.gold, letterSpacing: 0.5 },
  handledBox: { marginTop: spacing.sm, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border, paddingTop: spacing.sm },
  handledLabel: { fontFamily: fonts.uiSemi, fontSize: 10.5, letterSpacing: 1, color: colors.textMuted, textTransform: "uppercase", marginBottom: 2 },
  handledText: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textPrimary, lineHeight: 19 },
  sourceBtn: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: spacing.md },
  sourceText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.primary },
  empty: { fontFamily: fonts.bodyItalic, fontSize: 14, color: colors.textMuted, textAlign: "center", marginTop: spacing.xl },
});

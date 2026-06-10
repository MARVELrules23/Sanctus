import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import {
  Charity,
  adminApproveCharity,
  adminApproveClaim,
  adminArchiveCharity,
  adminListCharities,
  adminListCharityClaims,
  adminRejectCharity,
  adminRejectClaim,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { CHARITY_QUOTES } from "@/src/utils/charity-quotes";

type Tab = "pending" | "approved" | "rejected" | "claims" | "quotes";

export default function AdminCharitiesScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("pending");
  const [items, setItems] = useState<Charity[]>([]);
  const [claims, setClaims] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [quoteSearch, setQuoteSearch] = useState("");

  const load = useCallback(async () => {
    if (!user?.is_admin) return;
    if (tab === "quotes") {
      // Static data — nothing to fetch.
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      if (tab === "claims") {
        const r = await adminListCharityClaims("pending");
        setClaims(r.items);
      } else {
        const r = await adminListCharities(tab);
        setItems(r.items);
      }
    } catch (e) {
      console.warn("admin charities load failed", e);
    } finally { setLoading(false); }
  }, [tab, user]);

  useEffect(() => { load(); }, [load]);

  const filteredQuotes = useMemo(() => {
    const q = quoteSearch.trim().toLowerCase();
    if (!q) return CHARITY_QUOTES;
    return CHARITY_QUOTES.filter(
      (item) =>
        item.text.toLowerCase().includes(q) ||
        item.source.toLowerCase().includes(q) ||
        (item.context || "").toLowerCase().includes(q),
    );
  }, [quoteSearch]);

  if (!user?.is_admin) {
    return (
      <SafeAreaView style={styles.safe}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.center}><Text style={styles.gateText}>Admins only.</Text></View>
      </SafeAreaView>
    );
  }

  const approve = async (id: string) => { try { await adminApproveCharity(id); load(); } catch (e: any) { Alert.alert("Failed", e?.message || ""); } };
  const reject = async (id: string) => { try { await adminRejectCharity(id); load(); } catch (e: any) { Alert.alert("Failed", e?.message || ""); } };
  const archive = (id: string) => {
    Alert.alert("Archive charity?", "It will be hidden from the public list.", [
      { text: "Cancel", style: "cancel" },
      { text: "Archive", style: "destructive", onPress: async () => { try { await adminArchiveCharity(id); load(); } catch (e: any) { Alert.alert("Failed", e?.message || ""); } } },
    ]);
  };
  const approveClaim = async (id: string) => { try { await adminApproveClaim(id); load(); } catch (e: any) { Alert.alert("Failed", e?.message || ""); } };
  const rejectClaim = async (id: string) => { try { await adminRejectClaim(id); load(); } catch (e: any) { Alert.alert("Failed", e?.message || ""); } };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.headerBtn}><Ionicons name="chevron-back" size={24} color={colors.primary} /></Pressable>
        <Text style={styles.headerTitle}>Charities · Admin</Text>
        <View style={styles.headerBtn} />
      </View>

      <View style={styles.tabs}>
        {(["pending", "approved", "rejected", "claims", "quotes"] as Tab[]).map((t) => (
          <Pressable key={t} onPress={() => setTab(t)} style={({ pressed }) => [styles.tab, tab === t && styles.tabActive, pressed && { opacity: 0.7 }]}>
            <Text style={[styles.tabText, tab === t && styles.tabTextActive]} numberOfLines={1}>{t === "claims" ? "Claims" : t === "quotes" ? "Quotes" : t[0].toUpperCase() + t.slice(1)}</Text>
          </Pressable>
        ))}
      </View>

      {tab === "quotes" ? (
        <View style={styles.quoteSearchWrap}>
          <Ionicons name="search" size={16} color={colors.textMuted} />
          <TextInput
            testID="admin-quote-search"
            value={quoteSearch}
            onChangeText={setQuoteSearch}
            placeholder="Search saints, quotes, or sources…"
            placeholderTextColor={colors.textMuted}
            style={styles.quoteSearchInput}
            autoCapitalize="none"
            autoCorrect={false}
          />
          {quoteSearch ? (
            <Pressable onPress={() => setQuoteSearch("")} hitSlop={10}>
              <Ionicons name="close-circle" size={18} color={colors.textMuted} />
            </Pressable>
          ) : null}
        </View>
      ) : null}

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.primary} /></View>
      ) : (
        <ScrollView contentContainerStyle={styles.list}>
          {tab === "quotes" ? (
            <>
              <View style={styles.quoteHeader}>
                <Ionicons name="rose-outline" size={14} color={colors.gold} />
                <Text style={styles.quoteHeaderText}>
                  {filteredQuotes.length}
                  {quoteSearch ? ` / ${CHARITY_QUOTES.length}` : ""}
                  {" "}quote{filteredQuotes.length === 1 ? "" : "s"} on charity — Saints, Blesseds &amp; Venerables
                </Text>
              </View>
              {filteredQuotes.length === 0 ? (
                <Text style={styles.empty}>No quotes match &ldquo;{quoteSearch}&rdquo;.</Text>
              ) : (
                filteredQuotes.map((q, i) => (
                  <View key={`${q.source}-${i}`} style={styles.quoteRow}>
                    <Text style={styles.quoteMark}>&ldquo;</Text>
                    <Text style={styles.quoteBody}>{q.text}</Text>
                    <Text style={styles.quoteSource}>— {q.source}</Text>
                    {q.context ? (
                      <Text style={styles.quoteCtx}>{q.context}</Text>
                    ) : null}
                  </View>
                ))
              )}
            </>
          ) : tab === "claims" ? (
            claims.length === 0 ? (
              <Text style={styles.empty}>No pending claim requests.</Text>
            ) : (
              claims.map((c) => (
                <View key={c.claim_id} style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.rowName}>{c.charity_name || c.charity_id}</Text>
                    <Text style={styles.rowMeta}>{c.user_name} · {c.user_email}</Text>
                    <Text style={styles.rowMeta}>{c.charity_location}</Text>
                    {c.message ? <Text style={styles.rowMessage} numberOfLines={4}>“{c.message}”</Text> : null}
                  </View>
                  <View style={styles.actionStack}>
                    <Pressable onPress={() => approveClaim(c.claim_id)} style={({ pressed }) => [styles.approveBtn, pressed && { opacity: 0.7 }]}><Ionicons name="checkmark" size={16} color="#fff" /></Pressable>
                    <Pressable onPress={() => rejectClaim(c.claim_id)} style={({ pressed }) => [styles.rejectBtn, pressed && { opacity: 0.7 }]}><Ionicons name="close" size={16} color="#fff" /></Pressable>
                  </View>
                </View>
              ))
            )
          ) : items.length === 0 ? (
            <Text style={styles.empty}>Nothing in &ldquo;{tab}&rdquo;.</Text>
          ) : (
            items.map((c) => (
              <Pressable key={c.charity_id} onPress={() => router.push(`/charities/${c.charity_id}`)} style={({ pressed }) => [styles.row, pressed && { opacity: 0.85 }]}>
                {c.logo_url ? (
                  <Image source={{ uri: c.logo_url }} style={styles.thumb} resizeMode="cover" />
                ) : (
                  <View style={[styles.thumb, styles.thumbPh]}><Ionicons name="heart-circle-outline" size={22} color={colors.gold} /></View>
                )}
                <View style={{ flex: 1 }}>
                  <Text style={styles.rowName} numberOfLines={1}>{c.name}</Text>
                  <Text style={styles.rowMeta} numberOfLines={1}>{[c.city, c.state].filter(Boolean).join(", ")} · {c.category}</Text>
                  <Text style={styles.rowMission} numberOfLines={2}>{c.mission}</Text>
                </View>
                <View style={styles.actionStack}>
                  {tab === "pending" ? (
                    <>
                      <Pressable onPress={() => approve(c.charity_id)} style={({ pressed }) => [styles.approveBtn, pressed && { opacity: 0.7 }]}><Ionicons name="checkmark" size={16} color="#fff" /></Pressable>
                      <Pressable onPress={() => reject(c.charity_id)} style={({ pressed }) => [styles.rejectBtn, pressed && { opacity: 0.7 }]}><Ionicons name="close" size={16} color="#fff" /></Pressable>
                    </>
                  ) : (
                    <Pressable onPress={() => archive(c.charity_id)} style={({ pressed }) => [styles.archiveBtn, pressed && { opacity: 0.7 }]}><Ionicons name="archive-outline" size={16} color={colors.textMuted} /></Pressable>
                  )}
                </View>
              </Pressable>
            ))
          )}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, backgroundColor: colors.surface },
  headerBtn: { padding: spacing.xs, width: 44, alignItems: "center" },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingBold, fontSize: 18, color: colors.primary },
  tabs: { flexDirection: "row", padding: spacing.sm, gap: 6, backgroundColor: colors.surface, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  tab: { flex: 1, paddingVertical: 8, borderRadius: radius.round, alignItems: "center", backgroundColor: colors.background },
  tabActive: { backgroundColor: colors.primary },
  tabText: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.textSecondary },
  tabTextActive: { color: "#fff" },
  list: { padding: spacing.md, gap: spacing.sm },
  empty: { textAlign: "center", color: colors.textMuted, paddingVertical: spacing.xl, fontFamily: fonts.bodyRegular, fontSize: 14 },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.sm, padding: spacing.sm, backgroundColor: colors.surface, borderRadius: radius.lg, ...shadow.card, marginBottom: spacing.sm },
  thumb: { width: 52, height: 52, borderRadius: radius.md, backgroundColor: colors.background },
  thumbPh: { alignItems: "center", justifyContent: "center" },
  rowName: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  rowMeta: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  rowMission: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textMuted, marginTop: 2 },
  rowMessage: { fontFamily: fonts.bodyItalic, fontSize: 12, color: colors.textSecondary, marginTop: 4, lineHeight: 17 },
  actionStack: { gap: 6 },
  approveBtn: { width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center", backgroundColor: colors.liturgical.green },
  rejectBtn: { width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center", backgroundColor: colors.liturgical.red },
  archiveBtn: { width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.borderSoft },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  gateText: { fontFamily: fonts.bodyRegular, fontSize: 16, color: colors.textSecondary },

  // Quote review tab
  quoteSearchWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginHorizontal: spacing.md,
    marginTop: spacing.sm,
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: colors.surface,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.border,
  },
  quoteSearchInput: {
    flex: 1,
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textPrimary,
    paddingVertical: 0,
  },
  quoteHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: spacing.xs,
    paddingTop: spacing.xs,
    paddingBottom: spacing.sm,
  },
  quoteHeaderText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.gold,
    letterSpacing: 0.6,
    textTransform: "uppercase",
    flex: 1,
  },
  quoteRow: {
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.gold + "22",
    marginBottom: spacing.sm,
    ...shadow.card,
  },
  quoteMark: {
    fontFamily: fonts.headingBold,
    fontSize: 28,
    lineHeight: 28,
    color: colors.gold,
    marginBottom: -4,
  },
  quoteBody: {
    fontFamily: fonts.bodyItalic,
    fontSize: 14,
    lineHeight: 21,
    color: colors.textPrimary,
  },
  quoteSource: {
    marginTop: spacing.sm,
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.primary,
  },
  quoteCtx: {
    marginTop: 2,
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textMuted,
  },
});

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import {
  AdminCharityQuoteApi,
  Charity,
  adminApproveCharity,
  adminApproveClaim,
  adminArchiveCharity,
  adminCreateCharityQuote,
  adminDeleteCharityQuote,
  adminListCharities,
  adminListCharityClaims,
  adminListCharityQuotes,
  adminRejectCharity,
  adminRejectClaim,
  adminToggleCharityQuote,
  adminUpdateCharityQuote,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type Tab = "pending" | "approved" | "rejected" | "claims" | "quotes";

interface QuoteDraft {
  quote_id?: string;
  text: string;
  source: string;
  context: string;
  active: boolean;
}

const EMPTY_DRAFT: QuoteDraft = { text: "", source: "", context: "", active: true };

export default function AdminCharitiesScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("pending");
  const [items, setItems] = useState<Charity[]>([]);
  const [claims, setClaims] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [quoteSearch, setQuoteSearch] = useState("");
  const [quotes, setQuotes] = useState<AdminCharityQuoteApi[]>([]);
  const [editorOpen, setEditorOpen] = useState(false);
  const [draft, setDraft] = useState<QuoteDraft>(EMPTY_DRAFT);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!user?.is_admin) return;
    setLoading(true);
    try {
      if (tab === "quotes") {
        const r = await adminListCharityQuotes();
        setQuotes(r.items);
      } else if (tab === "claims") {
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
    if (!q) return quotes;
    return quotes.filter(
      (item) =>
        item.text.toLowerCase().includes(q) ||
        item.source.toLowerCase().includes(q) ||
        (item.context || "").toLowerCase().includes(q),
    );
  }, [quoteSearch, quotes]);

  const openNewQuote = () => { setDraft(EMPTY_DRAFT); setEditorOpen(true); };
  const openEditQuote = (q: AdminCharityQuoteApi) => {
    setDraft({
      quote_id: q.quote_id,
      text: q.text,
      source: q.source,
      context: q.context || "",
      active: q.active,
    });
    setEditorOpen(true);
  };

  const submitQuote = async () => {
    const text = draft.text.trim();
    const source = draft.source.trim();
    if (text.length < 4) { Alert.alert("Quote required", "Please enter the full quote text (at least 4 characters)."); return; }
    if (!source) { Alert.alert("Attribution required", "Please enter the saint, blessed, or venerable who said this."); return; }
    setSaving(true);
    try {
      if (draft.quote_id) {
        const updated = await adminUpdateCharityQuote(draft.quote_id, {
          text, source, context: draft.context.trim() || null, active: draft.active,
        });
        setQuotes((prev) => prev.map((q) => q.quote_id === updated.quote_id ? updated : q));
      } else {
        const created = await adminCreateCharityQuote({
          text, source, context: draft.context.trim() || null, active: draft.active,
        });
        setQuotes((prev) => [...prev, created]);
      }
      setEditorOpen(false);
    } catch (e: any) {
      Alert.alert("Couldn't save", e?.message || "Please try again.");
    } finally { setSaving(false); }
  };

  const toggleQuote = async (q: AdminCharityQuoteApi) => {
    try {
      const updated = await adminToggleCharityQuote(q.quote_id);
      setQuotes((prev) => prev.map((it) => it.quote_id === updated.quote_id ? updated : it));
    } catch (e: any) {
      Alert.alert("Toggle failed", e?.message || "Please try again.");
    }
  };

  const deleteQuote = (q: AdminCharityQuoteApi) => {
    Alert.alert(
      "Delete quote?",
      `"${q.text.slice(0, 80)}${q.text.length > 80 ? "…" : ""}"\n— ${q.source}`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            try {
              await adminDeleteCharityQuote(q.quote_id);
              setQuotes((prev) => prev.filter((it) => it.quote_id !== q.quote_id));
            } catch (e: any) {
              Alert.alert("Delete failed", e?.message || "Please try again.");
            }
          },
        },
      ],
    );
  };

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
        <View style={styles.quoteToolbar}>
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
          <Pressable
            testID="admin-quote-add"
            onPress={openNewQuote}
            style={({ pressed }) => [styles.quoteAddBtn, pressed && { opacity: 0.85 }]}
          >
            <Ionicons name="add" size={20} color="#fff" />
          </Pressable>
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
                  {quoteSearch ? ` / ${quotes.length}` : ""}
                  {" "}quote{filteredQuotes.length === 1 ? "" : "s"} · tap to edit
                </Text>
              </View>
              {filteredQuotes.length === 0 ? (
                <Text style={styles.empty}>
                  {quoteSearch
                    ? `No quotes match "${quoteSearch}".`
                    : "No quotes yet — tap + to add the first one."}
                </Text>
              ) : (
                filteredQuotes.map((q) => (
                  <Pressable
                    key={q.quote_id}
                    testID={`admin-quote-row-${q.quote_id}`}
                    onPress={() => openEditQuote(q)}
                    style={({ pressed }) => [
                      styles.quoteRow,
                      !q.active && styles.quoteRowHidden,
                      pressed && { opacity: 0.85 },
                    ]}
                  >
                    {!q.active ? (
                      <View style={styles.quoteHiddenPill}>
                        <Ionicons name="eye-off-outline" size={11} color={colors.textMuted} />
                        <Text style={styles.quoteHiddenPillText}>Hidden</Text>
                      </View>
                    ) : null}
                    <Text style={styles.quoteMark}>&ldquo;</Text>
                    <Text style={styles.quoteBody}>{q.text}</Text>
                    <Text style={styles.quoteSource}>— {q.source}</Text>
                    {q.context ? (
                      <Text style={styles.quoteCtx}>{q.context}</Text>
                    ) : null}
                    <View style={styles.quoteActions}>
                      <Pressable
                        testID={`admin-quote-toggle-${q.quote_id}`}
                        onPress={(e) => { e.stopPropagation?.(); toggleQuote(q); }}
                        hitSlop={8}
                        style={({ pressed }) => [styles.quoteActionBtn, pressed && { opacity: 0.65 }]}
                      >
                        <Ionicons
                          name={q.active ? "eye-outline" : "eye-off-outline"}
                          size={16}
                          color={q.active ? colors.primary : colors.textMuted}
                        />
                        <Text style={[styles.quoteActionText, !q.active && { color: colors.textMuted }]}>
                          {q.active ? "Active" : "Hidden"}
                        </Text>
                      </Pressable>
                      <Pressable
                        testID={`admin-quote-edit-${q.quote_id}`}
                        onPress={(e) => { e.stopPropagation?.(); openEditQuote(q); }}
                        hitSlop={8}
                        style={({ pressed }) => [styles.quoteActionBtn, pressed && { opacity: 0.65 }]}
                      >
                        <Ionicons name="create-outline" size={16} color={colors.primary} />
                        <Text style={styles.quoteActionText}>Edit</Text>
                      </Pressable>
                      <Pressable
                        testID={`admin-quote-delete-${q.quote_id}`}
                        onPress={(e) => { e.stopPropagation?.(); deleteQuote(q); }}
                        hitSlop={8}
                        style={({ pressed }) => [styles.quoteActionBtn, pressed && { opacity: 0.65 }]}
                      >
                        <Ionicons name="trash-outline" size={16} color="#c0392b" />
                        <Text style={[styles.quoteActionText, { color: "#c0392b" }]}>Delete</Text>
                      </Pressable>
                    </View>
                  </Pressable>
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

      {/* ---- Quote editor modal (admin add / edit) ---- */}
      <Modal
        visible={editorOpen}
        animationType="slide"
        transparent
        onRequestClose={() => setEditorOpen(false)}
      >
        <View style={styles.modalScrim}>
          <View style={styles.modalSheet}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                {draft.quote_id ? "Edit quote" : "New quote"}
              </Text>
              <Pressable onPress={() => setEditorOpen(false)} hitSlop={10}>
                <Ionicons name="close" size={22} color={colors.textPrimary} />
              </Pressable>
            </View>

            <ScrollView contentContainerStyle={{ paddingBottom: spacing.lg }}>
              <Text style={styles.fieldLabel}>Quote</Text>
              <TextInput
                testID="admin-quote-text-input"
                value={draft.text}
                onChangeText={(t) => setDraft((d) => ({ ...d, text: t }))}
                placeholder='e.g. "Spread love everywhere you go."'
                placeholderTextColor={colors.textMuted}
                multiline
                style={[styles.fieldInput, styles.fieldInputMulti]}
              />

              <Text style={styles.fieldLabel}>Attribution</Text>
              <TextInput
                testID="admin-quote-source-input"
                value={draft.source}
                onChangeText={(t) => setDraft((d) => ({ ...d, source: t }))}
                placeholder="e.g. St. Teresa of Calcutta"
                placeholderTextColor={colors.textMuted}
                style={styles.fieldInput}
                autoCapitalize="words"
              />

              <Text style={styles.fieldLabel}>Context · optional</Text>
              <TextInput
                testID="admin-quote-context-input"
                value={draft.context}
                onChangeText={(t) => setDraft((d) => ({ ...d, context: t }))}
                placeholder="Sermon, encyclical, book, or year"
                placeholderTextColor={colors.textMuted}
                style={styles.fieldInput}
              />

              <View style={styles.activeRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.fieldLabel}>Show on charity pages</Text>
                  <Text style={styles.fieldHint}>
                    Turn off to hide this quote from the public pool without deleting it.
                  </Text>
                </View>
                <Switch
                  testID="admin-quote-active-switch"
                  value={draft.active}
                  onValueChange={(v) => setDraft((d) => ({ ...d, active: v }))}
                  trackColor={{ true: colors.primary, false: colors.borderSoft }}
                />
              </View>

              <Pressable
                testID="admin-quote-save"
                onPress={submitQuote}
                disabled={saving}
                style={({ pressed }) => [styles.saveBtn, (pressed || saving) && { opacity: 0.7 }]}
              >
                {saving ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <>
                    <Ionicons name="checkmark" size={18} color="#fff" />
                    <Text style={styles.saveBtnText}>
                      {draft.quote_id ? "Save changes" : "Add quote"}
                    </Text>
                  </>
                )}
              </Pressable>
            </ScrollView>
          </View>
        </View>
      </Modal>
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
  quoteToolbar: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginHorizontal: spacing.md,
    marginTop: spacing.sm,
  },
  quoteSearchWrap: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
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
  quoteAddBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    ...shadow.card,
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
  quoteRowHidden: {
    opacity: 0.55,
    borderColor: colors.borderSoft,
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
  quoteHiddenPill: {
    position: "absolute",
    top: 8,
    right: 8,
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    backgroundColor: colors.background,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  quoteHiddenPillText: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    color: colors.textMuted,
    letterSpacing: 0.5,
    textTransform: "uppercase",
  },
  quoteActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginTop: spacing.md,
    paddingTop: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.borderSoft,
  },
  quoteActionBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingVertical: 4,
    paddingHorizontal: 6,
  },
  quoteActionText: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.primary,
  },

  // Editor modal
  modalScrim: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.45)",
    justifyContent: "flex-end",
  },
  modalSheet: {
    backgroundColor: colors.background,
    borderTopLeftRadius: radius.xl,
    borderTopRightRadius: radius.xl,
    padding: spacing.lg,
    maxHeight: "92%",
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.md,
  },
  modalTitle: {
    fontFamily: fonts.headingBold,
    fontSize: 20,
    color: colors.primary,
  },
  fieldLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.textSecondary,
    letterSpacing: 0.5,
    textTransform: "uppercase",
    marginTop: spacing.sm,
    marginBottom: 6,
  },
  fieldHint: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textMuted,
    marginTop: 2,
  },
  fieldInput: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: 12,
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textPrimary,
    backgroundColor: colors.surface,
  },
  fieldInputMulti: {
    minHeight: 110,
    textAlignVertical: "top",
  },
  activeRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    marginTop: spacing.md,
    paddingHorizontal: 4,
  },
  saveBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: colors.primary,
    borderRadius: radius.round,
    paddingVertical: 14,
    marginTop: spacing.lg,
  },
  saveBtnText: {
    fontFamily: fonts.uiSemi,
    fontSize: 15,
    color: "#fff",
    letterSpacing: 0.3,
  },
});

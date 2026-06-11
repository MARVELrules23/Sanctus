import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  KeyboardAvoidingView,
  Linking,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import {
  SaintAdmin,
  SaintRank,
  adminApproveSaint,
  adminDeleteSaint,
  adminListSaints,
  adminProposeSaint,
  adminRejectSaint,
  adminUpdateSaint,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { confirm } from "@/src/utils/confirm";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const RANKS: SaintRank[] = ["saint", "blessed", "venerable"];

const todayISO = () => new Date().toISOString().slice(0, 10);

// ---- Editor modal ----
function EditorModal({
  open,
  entry,
  onClose,
  onSaved,
}: {
  open: boolean;
  entry: SaintAdmin | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [draft, setDraft] = useState<SaintAdmin | null>(entry);
  const [saving, setSaving] = useState(false);
  const [pickingPic, setPickingPic] = useState(false);

  useEffect(() => { setDraft(entry); }, [entry]);

  if (!open || !draft) return null;

  const set = <K extends keyof SaintAdmin>(k: K, v: SaintAdmin[K]) =>
    setDraft({ ...draft, [k]: v });

  const onPickPicture = async () => {
    if (pickingPic) return;
    setPickingPic(true);
    try {
      const perm = await ImagePicker.getMediaLibraryPermissionsAsync();
      let status = perm.status;
      let canAskAgain = perm.canAskAgain;
      if (status !== "granted") {
        if (canAskAgain) {
          const req = await ImagePicker.requestMediaLibraryPermissionsAsync();
          status = req.status;
          canAskAgain = req.canAskAgain;
        }
      }
      if (status !== "granted") {
        if (!canAskAgain) {
          Alert.alert(
            "Photos permission needed",
            "Sanctus needs access to your photos to attach an image to this entry.",
            [
              { text: "Cancel", style: "cancel" },
              { text: "Open Settings", onPress: () => Linking.openSettings() },
            ],
          );
        }
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [3, 4],
        quality: 0.72,
        base64: true,
      });
      if (result.canceled || !result.assets?.length) return;
      const asset = result.assets[0];
      let uri = asset.uri;
      if (asset.base64) {
        const mime = asset.mimeType || "image/jpeg";
        uri = `data:${mime};base64,${asset.base64}`;
      }
      // Hard guard ~2.8 MB to keep Mongo docs small.
      if (uri.startsWith("data:") && uri.length > 2_800_000) {
        Alert.alert("Image too large", "Please pick a smaller photo (max ~2 MB).");
        return;
      }
      setDraft({
        ...draft,
        picture_url: uri,
        // If the source field is empty, pre-fill a sensible default for uploads.
        picture_source: draft.picture_source && draft.picture_source.trim().length > 0
          ? draft.picture_source
          : "Uploaded by admin",
      });
    } catch (e) {
      console.warn("saint image pick failed", e);
      Alert.alert("Could not load that photo", "Please try a different one.");
    } finally {
      setPickingPic(false);
    }
  };

  const clearPicture = () => {
    setDraft({ ...draft, picture_url: null });
  };

  const save = async () => {
    setSaving(true);
    try {
      await adminUpdateSaint(draft.saint_id, {
        name: draft.name,
        rank: draft.rank,
        feast_date: draft.feast_date,
        is_primary: draft.is_primary,
        picture_url: draft.picture_url,
        picture_source: draft.picture_source,
        quote: draft.quote,
        quote_source: draft.quote_source,
        biography: draft.biography,
        recommended_action: draft.recommended_action,
      } as any);
      onSaved();
      onClose();
    } catch (e: any) {
      Alert.alert("Save failed", e?.message || "Try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal visible={open} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.safe} edges={["top"]}>
        <View style={styles.header}>
          <Pressable onPress={onClose} hitSlop={10}>
            <Ionicons name="close" size={26} color={colors.primary} />
          </Pressable>
          <Text style={styles.headerTitle}>Edit entry</Text>
          <Pressable
            testID="admin-edit-save"
            disabled={saving}
            onPress={save}
            style={({ pressed }) => [styles.saveBtn, (pressed || saving) && { opacity: 0.5 }]}
          >
            {saving ? <ActivityIndicator color={colors.gold} size="small" /> : <Text style={styles.saveBtnText}>Save</Text>}
          </Pressable>
        </View>
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
          <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
            <Text style={styles.label}>Name</Text>
            <TextInput value={draft.name} onChangeText={(v) => set("name", v)} style={styles.input} placeholder="Saint Ephrem the Syrian" placeholderTextColor={colors.textMuted} />

            <Text style={styles.label}>Rank</Text>
            <View style={styles.row}>
              {RANKS.map((r) => (
                <Pressable
                  key={r}
                  onPress={() => set("rank", r)}
                  style={({ pressed }) => [styles.chip, draft.rank === r && styles.chipOn, pressed && { opacity: 0.8 }]}
                >
                  <Text style={[styles.chipText, draft.rank === r && styles.chipTextOn]}>{r}</Text>
                </Pressable>
              ))}
            </View>

            <Text style={styles.label}>Feast date (MM-DD)</Text>
            <TextInput value={draft.feast_date || ""} onChangeText={(v) => set("feast_date", v || null)} style={styles.input} placeholder="06-09" placeholderTextColor={colors.textMuted} maxLength={5} />

            <View style={[styles.row, { marginTop: spacing.sm }]}>
              <Pressable
                onPress={() => set("is_primary", !draft.is_primary)}
                style={({ pressed }) => [styles.chip, draft.is_primary && styles.chipOn, pressed && { opacity: 0.8 }]}
              >
                <Ionicons name={draft.is_primary ? "star" : "star-outline"} size={14} color={draft.is_primary ? colors.gold : colors.primary} />
                <Text style={[styles.chipText, draft.is_primary && styles.chipTextOn, { marginLeft: 6 }]}>Primary</Text>
              </Pressable>
            </View>

            <Text style={styles.label}>Picture</Text>
            {draft.picture_url ? (
              <View style={styles.previewWrap}>
                <Image source={{ uri: draft.picture_url }} style={styles.previewImg} resizeMode="cover" />
                <Pressable
                  onPress={clearPicture}
                  style={({ pressed }) => [styles.previewClear, pressed && { opacity: 0.7 }]}
                  hitSlop={8}
                >
                  <Ionicons name="close" size={16} color="#fff" />
                </Pressable>
              </View>
            ) : null}
            <View style={styles.row}>
              <Pressable
                onPress={onPickPicture}
                disabled={pickingPic}
                style={({ pressed }) => [styles.pickerBtn, pressed && { opacity: 0.8 }, pickingPic && { opacity: 0.6 }]}
              >
                {pickingPic ? (
                  <ActivityIndicator size="small" color={colors.primary} />
                ) : (
                  <Ionicons name="image-outline" size={16} color={colors.primary} />
                )}
                <Text style={styles.pickerBtnText}>
                  {pickingPic ? "Loading…" : draft.picture_url ? "Replace from library" : "Upload from library"}
                </Text>
              </Pressable>
            </View>
            <Text style={styles.subtleLabel}>…or paste a public URL (Wikimedia Commons)</Text>
            <TextInput
              value={draft.picture_url && draft.picture_url.startsWith("data:") ? "" : (draft.picture_url || "")}
              onChangeText={(v) => set("picture_url", v || null)}
              style={styles.input}
              placeholder="https://upload.wikimedia.org/..."
              placeholderTextColor={colors.textMuted}
              autoCapitalize="none"
              autoCorrect={false}
              editable={!draft.picture_url || !draft.picture_url.startsWith("data:")}
            />

            <Text style={styles.label}>Picture source / credit</Text>
            <TextInput value={draft.picture_source || ""} onChangeText={(v) => set("picture_source", v || null)} style={styles.input} placeholder="Wikimedia Commons (public domain) or photographer name" placeholderTextColor={colors.textMuted} />

            <Text style={styles.label}>Quote (verbatim)</Text>
            <TextInput value={draft.quote} onChangeText={(v) => set("quote", v)} style={[styles.input, styles.multiline]} multiline placeholder="A short, verified quotation by the person…" placeholderTextColor={colors.textMuted} />

            <Text style={styles.label}>Quote source / citation</Text>
            <TextInput value={draft.quote_source} onChangeText={(v) => set("quote_source", v)} style={styles.input} placeholder="Hymns on Faith 5.17" placeholderTextColor={colors.textMuted} />

            <Text style={styles.label}>Biography</Text>
            <TextInput value={draft.biography} onChangeText={(v) => set("biography", v)} style={[styles.input, styles.bigMultiline]} multiline placeholder="250–400 words of life and works…" placeholderTextColor={colors.textMuted} />

            <Text style={styles.label}>Recommended action</Text>
            <TextInput value={draft.recommended_action} onChangeText={(v) => set("recommended_action", v)} style={[styles.input, styles.multiline]} multiline placeholder="A concrete devotional or charitable act…" placeholderTextColor={colors.textMuted} />

            <View style={{ height: spacing.xxl }} />
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </Modal>
  );
}

// ---- Main admin screen ----

// Mirror the backend's hard-required fields for approving a Saint entry.
// Keep this list in sync with `_validate_for_approval` (or equivalent
// non-empty checks) in /app/backend/saints.py so the UI can warn an admin
// before the API rejects them with a 400.
const REQUIRED_FOR_APPROVAL: Array<{ key: keyof SaintAdmin; label: string; minLen?: number }> = [
  { key: "name", label: "Name" },
  { key: "rank", label: "Rank" },
  { key: "feast_date", label: "Feast date (MM-DD)" },
  { key: "quote", label: "Quote" },
  { key: "quote_source", label: "Quote source" },
  { key: "biography", label: "Biography", minLen: 80 },
  { key: "recommended_action", label: "Recommended action" },
];

function missingApprovalFields(s: SaintAdmin): string[] {
  const missing: string[] = [];
  for (const r of REQUIRED_FOR_APPROVAL) {
    const raw = (s as any)[r.key];
    const v = typeof raw === "string" ? raw.trim() : raw;
    if (!v || (typeof v === "string" && r.minLen && v.length < r.minLen)) {
      missing.push(r.label);
    }
  }
  return missing;
}

export default function AdminSaintsScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [items, setItems] = useState<SaintAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "draft" | "approved" | "rejected">("draft");
  const [propDate, setPropDate] = useState<string>(todayISO());
  const [propRank, setPropRank] = useState<SaintRank | "">("");
  const [propName, setPropName] = useState<string>("");
  const [propPrimary, setPropPrimary] = useState<boolean>(true);
  const [proposing, setProposing] = useState(false);
  const [editing, setEditing] = useState<SaintAdmin | null>(null);

  const isAdmin = !!(user as any)?.is_admin;

  const load = useCallback(async () => {
    if (!isAdmin) return;
    setLoading(true);
    try {
      const r = await adminListSaints(filter === "all" ? undefined : filter);
      setItems(r.items);
    } catch (e: any) {
      Alert.alert("Couldn't load", e?.message || "Try again.");
    } finally {
      setLoading(false);
    }
  }, [filter, isAdmin]);

  useEffect(() => { void load(); }, [load]);

  const propose = async () => {
    setProposing(true);
    try {
      const r = await adminProposeSaint({
        date: propDate,
        rank_hint: propRank || undefined,
        name_hint: propName.trim() || undefined,
        is_primary: propPrimary,
      });
      Alert.alert("Proposed", `${r.name} — review below.`);
      setPropName("");
      await load();
    } catch (e: any) {
      Alert.alert("Proposal failed", e?.message || "Try again.");
    } finally {
      setProposing(false);
    }
  };

  const approve = async (s: SaintAdmin) => {
    // Mirror the backend's hard-required field list so we can warn the
    // admin BEFORE the API rejects the call. Empty `quote_source` is the
    // most common reason approve was "doing nothing" — the LLM proposes a
    // quote but sometimes leaves the source blank, and a 400 surfaced as
    // an opaque alert.
    const missing = missingApprovalFields(s);
    if (missing.length > 0) {
      Alert.alert(
        "Fill these fields first",
        `Missing: ${missing.join(", ")}.\n\nTap Edit to fill them in, then Approve.`,
      );
      return;
    }
    try {
      await adminApproveSaint(s.saint_id);
      await load();
    } catch (e: any) {
      Alert.alert("Couldn't approve", e?.message || "Fill required fields then retry.");
    }
  };

  const reject = async (s: SaintAdmin) => {
    // IMPORTANT: do not use Alert.alert(..., [buttons]) here — on web it
    // collapses to window.alert() and the destructive callback never fires,
    // which is exactly why the Reject button "did nothing" on web preview.
    const ok = await confirm({
      title: "Reject this entry?",
      message: `${s.name} will be hidden from the daily feature.`,
      confirmText: "Reject",
      destructive: true,
    });
    if (!ok) return;
    try {
      await adminRejectSaint(s.saint_id);
      await load();
    } catch (e: any) {
      Alert.alert("Failed", e?.message || "Could not reject. Try again.");
    }
  };

  const del = async (s: SaintAdmin) => {
    const ok = await confirm({
      title: "Delete permanently?",
      message: `${s.name} will be removed. This cannot be undone.`,
      confirmText: "Delete",
      destructive: true,
    });
    if (!ok) return;
    try {
      await adminDeleteSaint(s.saint_id);
      await load();
    } catch (e: any) {
      Alert.alert("Failed", e?.message || "Could not delete. Try again.");
    }
  };

  const grouped = useMemo(() => items, [items]);

  if (!isAdmin) {
    return (
      <SafeAreaView style={styles.safe} edges={["top"]}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={10}><Ionicons name="chevron-back" size={26} color={colors.primary} /></Pressable>
          <Text style={styles.headerTitle}>Admin</Text>
          <View style={{ width: 26 }} />
        </View>
        <View style={styles.center}>
          <Ionicons name="lock-closed" size={36} color={colors.gold} />
          <Text style={styles.gateTitle}>Admin only</Text>
          <Text style={styles.gateText}>This screen reviews and approves Saints content.</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="admin-saints-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10}><Ionicons name="chevron-back" size={26} color={colors.primary} /></Pressable>
        <Text style={styles.headerTitle}>Saints · Review</Text>
        <Pressable onPress={load} hitSlop={10}><Ionicons name="refresh" size={20} color={colors.primary} /></Pressable>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Propose */}
        <View style={styles.proposeCard}>
          <Text style={styles.sectionLabel}>Propose new entry (AI)</Text>
          <Text style={styles.label}>Date (YYYY-MM-DD)</Text>
          <TextInput value={propDate} onChangeText={setPropDate} style={styles.input} placeholder="2026-06-09" placeholderTextColor={colors.textMuted} autoCapitalize="none" />

          <Text style={styles.label}>Rank hint (optional)</Text>
          <View style={styles.row}>
            <Pressable onPress={() => setPropRank("")} style={({ pressed }) => [styles.chip, !propRank && styles.chipOn, pressed && { opacity: 0.8 }]}>
              <Text style={[styles.chipText, !propRank && styles.chipTextOn]}>any</Text>
            </Pressable>
            {RANKS.map((r) => (
              <Pressable key={r} onPress={() => setPropRank(r)} style={({ pressed }) => [styles.chip, propRank === r && styles.chipOn, pressed && { opacity: 0.8 }]}>
                <Text style={[styles.chipText, propRank === r && styles.chipTextOn]}>{r}</Text>
              </Pressable>
            ))}
          </View>

          <Text style={styles.label}>Name hint (optional)</Text>
          <TextInput value={propName} onChangeText={setPropName} style={styles.input} placeholder="e.g. Saint Ephrem the Syrian" placeholderTextColor={colors.textMuted} />

          <View style={[styles.row, { marginTop: spacing.sm }]}>
            <Pressable
              onPress={() => setPropPrimary((v) => !v)}
              style={({ pressed }) => [styles.chip, propPrimary && styles.chipOn, pressed && { opacity: 0.8 }]}
            >
              <Ionicons name={propPrimary ? "star" : "star-outline"} size={14} color={propPrimary ? colors.gold : colors.primary} />
              <Text style={[styles.chipText, propPrimary && styles.chipTextOn, { marginLeft: 6 }]}>Primary card</Text>
            </Pressable>
          </View>

          <Pressable
            testID="admin-propose"
            disabled={proposing}
            onPress={propose}
            style={({ pressed }) => [styles.proposeBtn, (pressed || proposing) && { opacity: 0.6 }]}
          >
            {proposing ? <ActivityIndicator color={colors.gold} /> : (
              <>
                <Ionicons name="sparkles" size={16} color={colors.gold} />
                <Text style={styles.proposeBtnText}>Propose via Claude</Text>
              </>
            )}
          </Pressable>
        </View>

        {/* Filters */}
        <View style={[styles.row, { marginTop: spacing.lg }]}>
          {(["draft", "approved", "rejected", "all"] as const).map((f) => (
            <Pressable
              key={f}
              onPress={() => setFilter(f)}
              style={({ pressed }) => [styles.chip, filter === f && styles.chipOn, pressed && { opacity: 0.8 }]}
            >
              <Text style={[styles.chipText, filter === f && styles.chipTextOn]}>{f}</Text>
            </Pressable>
          ))}
        </View>

        {/* List */}
        {loading ? (
          <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
        ) : grouped.length === 0 ? (
          <Text style={styles.empty}>No entries with status “{filter}”.</Text>
        ) : (
          grouped.map((s) => {
            const missing = missingApprovalFields(s);
            const canApprove = missing.length === 0;
            return (
            <View key={s.saint_id} style={styles.entryCard} testID={`admin-entry-${s.saint_id}`}>
              <View style={styles.entryHeader}>
                {s.picture_url ? (
                  <Image source={{ uri: s.picture_url }} style={styles.thumb} resizeMode="cover" />
                ) : (
                  <View style={[styles.thumb, { alignItems: "center", justifyContent: "center" }]}>
                    <Ionicons name="image-outline" size={20} color={colors.textMuted} />
                  </View>
                )}
                <View style={{ flex: 1 }}>
                  <Text style={styles.entryName}>{s.name}</Text>
                  <Text style={styles.entryMeta}>
                    {s.rank} · feast {s.feast_date || "—"} · {s.status}
                  </Text>
                </View>
              </View>
              {s.quote ? (
                <Text style={styles.entryQuote} numberOfLines={3}>“{s.quote}” — {s.quote_source || <Text style={{ color: colors.liturgical.red }}>NO SOURCE</Text>}</Text>
              ) : (
                <Text style={[styles.entryQuote, { color: colors.liturgical.red }]}>⚠ No quote — fill before approving.</Text>
              )}
              {/* Inline approval-readiness banner — surfaces exactly why the
                  Approve button is greyed out, instead of silently 400ing. */}
              {missing.length > 0 && s.status === "draft" ? (
                <View testID={`admin-missing-${s.saint_id}`} style={styles.missingBanner}>
                  <Ionicons name="alert-circle" size={14} color={colors.liturgical.red} />
                  <Text style={styles.missingBannerText} numberOfLines={2}>
                    Cannot approve — missing: {missing.join(", ")}.
                  </Text>
                </View>
              ) : null}
              <View style={styles.actionRow}>
                <Pressable
                  testID={`admin-edit-${s.saint_id}`}
                  onPress={() => setEditing(s)}
                  style={({ pressed }) => [styles.actionBtn, pressed && { opacity: 0.7 }]}
                >
                  <Ionicons name="create-outline" size={14} color={colors.primary} />
                  <Text style={styles.actionBtnText}>Edit</Text>
                </Pressable>
                {s.status !== "approved" ? (
                  <Pressable
                    testID={`admin-approve-${s.saint_id}`}
                    onPress={() => approve(s)}
                    style={({ pressed }) => [
                      styles.actionBtn,
                      styles.approveBtn,
                      !canApprove && { opacity: 0.45 },
                      pressed && { opacity: 0.7 },
                    ]}
                  >
                    <Ionicons name="checkmark-circle" size={14} color={canApprove ? colors.gold : colors.textMuted} />
                    <Text style={[styles.actionBtnText, { color: canApprove ? colors.gold : colors.textMuted }]}>
                      Approve
                    </Text>
                  </Pressable>
                ) : null}
                {s.status !== "rejected" ? (
                  <Pressable
                    testID={`admin-reject-${s.saint_id}`}
                    onPress={() => reject(s)}
                    style={({ pressed }) => [styles.actionBtn, pressed && { opacity: 0.7 }]}
                  >
                    <Ionicons name="close-circle-outline" size={14} color={colors.liturgical.red} />
                    <Text style={[styles.actionBtnText, { color: colors.liturgical.red }]}>Reject</Text>
                  </Pressable>
                ) : null}
                <Pressable
                  testID={`admin-delete-${s.saint_id}`}
                  onPress={() => del(s)}
                  style={({ pressed }) => [styles.actionBtn, pressed && { opacity: 0.7 }]}
                >
                  <Ionicons name="trash-outline" size={14} color={colors.textMuted} />
                </Pressable>
              </View>
            </View>
          );})
        )}
        <View style={{ height: spacing.xxl }} />
      </ScrollView>

      <EditorModal open={!!editing} entry={editing} onClose={() => setEditing(null)} onSaved={load} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  scroll: { padding: spacing.lg },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.sm },
  gateTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary, marginTop: spacing.sm },
  gateText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, textAlign: "center" },
  proposeCard: {
    padding: spacing.lg,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  sectionLabel: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 2.5, color: colors.gold, marginBottom: spacing.sm },
  label: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 1.2, color: colors.gold, textTransform: "uppercase", marginTop: spacing.md, marginBottom: 4 },
  input: {
    backgroundColor: colors.background,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    paddingHorizontal: spacing.sm,
    paddingVertical: 8,
    fontFamily: fonts.bodyRegular,
    color: colors.textPrimary,
    fontSize: 13,
  },
  multiline: { minHeight: 72, paddingTop: 8, textAlignVertical: "top" as const },
  bigMultiline: { minHeight: 160, paddingTop: 8, textAlignVertical: "top" as const },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 4 },
  chip: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.sm, paddingVertical: 6, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.background },
  chipOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.primary, textTransform: "lowercase" },
  chipTextOn: { color: colors.gold },
  proposeBtn: { marginTop: spacing.md, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, padding: 12, borderRadius: radius.round, backgroundColor: colors.primary },
  proposeBtnText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold },
  saveBtn: { paddingHorizontal: spacing.md, paddingVertical: 6, borderRadius: radius.round, backgroundColor: colors.primary, minWidth: 72, alignItems: "center" },
  saveBtnText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 13 },
  previewImg: { width: "100%", height: 220, borderRadius: radius.sm, marginTop: 8, backgroundColor: colors.background },
  previewWrap: { position: "relative", marginTop: 8 },
  previewClear: { position: "absolute", top: 8, right: 8, width: 26, height: 26, borderRadius: 13, backgroundColor: "rgba(0,0,0,0.55)", alignItems: "center", justifyContent: "center" },
  pickerBtn: { flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 14, paddingVertical: 10, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.background, marginTop: spacing.sm },
  pickerBtnText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.primary },
  subtleLabel: { marginTop: spacing.md, fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted },
  empty: { textAlign: "center", fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, marginTop: spacing.lg },
  entryCard: { marginTop: spacing.md, padding: spacing.md, borderRadius: radius.md, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft, ...shadow.card },
  entryHeader: { flexDirection: "row", gap: spacing.sm, alignItems: "center" },
  thumb: { width: 56, height: 56, borderRadius: radius.sm, backgroundColor: colors.background, borderWidth: 1, borderColor: colors.borderSoft },
  entryName: { fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary },
  entryMeta: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  entryQuote: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12, color: colors.textSecondary, marginTop: spacing.sm },
  missingBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginTop: spacing.sm,
    paddingVertical: 6,
    paddingHorizontal: spacing.sm,
    backgroundColor: "rgba(180, 50, 50, 0.08)",
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: "rgba(180, 50, 50, 0.35)",
  },
  missingBannerText: {
    flex: 1,
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.liturgical.red,
    letterSpacing: 0.2,
  },
  actionRow: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: 6, marginTop: spacing.sm },
  actionBtn: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 10, paddingVertical: 6, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.background },
  approveBtn: { backgroundColor: colors.primary, borderColor: colors.primary },
  actionBtnText: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.primary },
});

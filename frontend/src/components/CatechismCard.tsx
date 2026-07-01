/**
 * CatechismCard — Home-tab card surfacing today's "Catechism in 90 seconds"
 * teaching with a verbatim CCC quote, our short expansion, and a Reflect
 * button that opens a modal asking Claude for a personal reflection that
 * the user can then save to their Journal (filed under "CCC Reflection").
 *
 * Loading is decoupled from initial render: the card renders an instant
 * skeleton so we don't push the rest of the Home feed downward when the
 * fetch resolves a moment later.
 *
 * The Reflect modal:
 *   • Pre-fills the AI request with today's teaching + the user's optional
 *     "what's on your heart today" note.
 *   • Streams the response in (well — awaits it; the backend is not
 *     streaming yet, but the UI is shaped to add streaming later).
 *   • Lets the user save the reflection to their journal in one tap.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";

import { api, CatechismReflectResponse, CatechismTeaching } from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import BookmarkButton from "@/src/components/BookmarkButton";

export default function CatechismCard({ date }: { date: string }) {
  const [teaching, setTeaching] = useState<CatechismTeaching | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      const t = await api<CatechismTeaching>(`/catechism/today?date=${date}`);
      setTeaching(t);
    } catch (e) {
      setError((e as Error).message || "Could not load today's teaching.");
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      await load();
      if (cancelled) return;
    })();
    return () => {
      cancelled = true;
    };
  }, [load]);

  if (loading) {
    return (
      <View style={styles.card} testID="catechism-card">
        <View style={styles.cardHeader}>
          <Ionicons name="library-outline" size={18} color={colors.gold} />
          <Text style={styles.cardHeaderText}>CATECHISM IN 90 SECONDS</Text>
        </View>
        <View style={styles.skeletonRow} />
        <View style={[styles.skeletonRow, { width: "70%" }]} />
        <View style={[styles.skeletonRow, { width: "85%" }]} />
      </View>
    );
  }

  if (error || !teaching) {
    return (
      <View style={styles.card} testID="catechism-card">
        <View style={styles.cardHeader}>
          <Ionicons name="library-outline" size={18} color={colors.gold} />
          <Text style={styles.cardHeaderText}>CATECHISM IN 90 SECONDS</Text>
        </View>
        <Text style={styles.empty}>{error ?? "No teaching available today."}</Text>
        <Pressable
          testID="catechism-retry"
          onPress={() => {
            setLoading(true);
            load();
          }}
          style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
        >
          <Ionicons name="refresh-outline" size={16} color={colors.gold} />
          <Text style={styles.primaryBtnText}>Try again</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <>
      <View style={styles.card} testID="catechism-card">
        <View style={styles.cardHeader}>
          <Ionicons name="library-outline" size={18} color={colors.gold} />
          <Text style={styles.cardHeaderText}>CATECHISM IN 90 SECONDS</Text>
        </View>

        <View style={styles.refRow}>
          <Text style={styles.refText}>{teaching.ccc_ref}</Text>
          <View style={styles.themePill}>
            <Text style={styles.themePillText}>{teaching.theme}</Text>
          </View>
          <View style={{ marginLeft: "auto" }}>
            <BookmarkButton
              input={{
                kind: "catechism",
                ref_id: teaching.ccc_ref,
                title: teaching.title,
                subtitle: teaching.ccc_ref,
                route: "/",
              }}
              size={20}
            />
          </View>
        </View>

        <Text style={styles.title}>{teaching.title}</Text>

        <Text style={styles.quote}>“{teaching.quote}”</Text>

        <Text style={styles.expansion}>{teaching.expansion}</Text>

        <View style={styles.actionsRow}>
          <Pressable
            testID="catechism-reflect-button"
            onPress={() => setModalOpen(true)}
            style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
          >
            <Ionicons name="sparkles-outline" size={16} color={colors.gold} />
            <Text style={styles.primaryBtnText}>Reflect</Text>
          </Pressable>
          {teaching.saved_to_journal ? (
            <View style={styles.savedChip} testID="catechism-saved-chip">
              <Ionicons name="checkmark-circle" size={14} color={colors.liturgical.purple} />
              <Text style={styles.savedChipText}>In Journal</Text>
            </View>
          ) : null}
        </View>
      </View>

      <ReflectModal
        visible={modalOpen}
        teaching={teaching}
        date={date}
        onClose={() => setModalOpen(false)}
        onSaved={() => {
          setTeaching((prev) =>
            prev ? { ...prev, saved_to_journal: true } : prev
          );
          setModalOpen(false);
        }}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Reflect modal
// ---------------------------------------------------------------------------

function ReflectModal({
  visible,
  teaching,
  date,
  onClose,
  onSaved,
}: {
  visible: boolean;
  teaching: CatechismTeaching;
  date: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [note, setNote] = useState("");
  const [reflection, setReflection] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Reset state every time the modal opens.
  useEffect(() => {
    if (visible) {
      setNote("");
      setReflection(null);
      setGenerating(false);
      setSaving(false);
      setErr(null);
    }
  }, [visible]);

  const generate = async () => {
    setGenerating(true);
    setErr(null);
    try {
      const res = await api<CatechismReflectResponse>("/catechism/reflect", {
        method: "POST",
        body: { teaching_id: teaching.id, note: note.trim() || undefined },
      });
      setReflection(res.reflection);
    } catch (e) {
      setErr((e as Error).message || "Reflection failed.");
    } finally {
      setGenerating(false);
    }
  };

  const save = async () => {
    if (!reflection) return;
    setSaving(true);
    setErr(null);
    try {
      await api<{ ok: boolean; entry_id: string }>(
        "/catechism/save-to-journal",
        {
          method: "POST",
          body: {
            date,
            teaching_id: teaching.id,
            reflection,
            user_note: note.trim() || undefined,
          },
        }
      );
      onSaved();
    } catch (e) {
      setErr((e as Error).message || "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView
        style={modalStyles.safe}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View style={modalStyles.headerRow}>
          <Pressable
            testID="catechism-modal-close"
            onPress={onClose}
            hitSlop={12}
            style={({ pressed }) => [modalStyles.iconBtn, pressed && styles.pressed]}
          >
            <Ionicons name="close" size={26} color={colors.textPrimary} />
          </Pressable>
          <Text style={modalStyles.headerTitle}>Reflect</Text>
          <View style={modalStyles.iconBtn} />
        </View>

        <ScrollView
          style={modalStyles.scroll}
          contentContainerStyle={modalStyles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          <View style={modalStyles.refRow}>
            <Text style={styles.refText}>{teaching.ccc_ref}</Text>
            <View style={styles.themePill}>
              <Text style={styles.themePillText}>{teaching.theme}</Text>
            </View>
          </View>
          <Text style={modalStyles.title}>{teaching.title}</Text>
          <Text style={modalStyles.quote}>“{teaching.quote}”</Text>

          <Text style={modalStyles.prompt}>{teaching.reflection_prompt}</Text>

          <Text style={modalStyles.label}>What&apos;s on your heart? (optional)</Text>
          <TextInput
            testID="catechism-note-input"
            style={modalStyles.input}
            multiline
            placeholder="Tell the Lord — no editing. Two sentences is enough."
            placeholderTextColor={colors.textMuted}
            value={note}
            onChangeText={setNote}
            maxLength={600}
            editable={!generating && !saving}
          />

          {reflection ? (
            <View style={modalStyles.reflectionBox} testID="catechism-reflection-box">
              <View style={modalStyles.reflectionHeader}>
                <Ionicons name="sparkles" size={14} color={colors.gold} />
                <Text style={modalStyles.reflectionHeaderText}>Reflection</Text>
              </View>
              <Text style={modalStyles.reflectionText}>{reflection}</Text>
            </View>
          ) : null}

          {err ? <Text style={modalStyles.error}>{err}</Text> : null}

          {!reflection ? (
            <Pressable
              testID="catechism-generate-button"
              disabled={generating}
              onPress={generate}
              style={({ pressed }) => [
                modalStyles.primaryBtn,
                (generating || pressed) && styles.pressed,
              ]}
            >
              {generating ? (
                <ActivityIndicator color={colors.gold} />
              ) : (
                <>
                  <Ionicons name="sparkles-outline" size={16} color={colors.gold} />
                  <Text style={modalStyles.primaryBtnText}>Generate Reflection</Text>
                </>
              )}
            </Pressable>
          ) : (
            <View style={modalStyles.actionsCol}>
              <Pressable
                testID="catechism-save-button"
                disabled={saving}
                onPress={save}
                style={({ pressed }) => [
                  modalStyles.primaryBtn,
                  (saving || pressed) && styles.pressed,
                ]}
              >
                {saving ? (
                  <ActivityIndicator color={colors.gold} />
                ) : (
                  <>
                    <Ionicons name="bookmark-outline" size={16} color={colors.gold} />
                    <Text style={modalStyles.primaryBtnText}>Save to Journal</Text>
                  </>
                )}
              </Pressable>
              <Pressable
                testID="catechism-regenerate-button"
                disabled={generating || saving}
                onPress={generate}
                style={({ pressed }) => [
                  modalStyles.secondaryBtn,
                  pressed && styles.pressed,
                ]}
              >
                <Ionicons name="refresh-outline" size={16} color={colors.textSecondary} />
                <Text style={modalStyles.secondaryBtnText}>Regenerate</Text>
              </Pressable>
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginTop: spacing.md,
    ...shadow.card,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  cardHeaderText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.5,
    color: colors.gold,
  },
  refRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginBottom: spacing.xs,
  },
  refText: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    letterSpacing: 0.8,
    color: colors.textMuted,
  },
  themePill: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.background,
  },
  themePillText: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 0.8,
    color: colors.textSecondary,
  },
  title: {
    fontFamily: fonts.headingSemi,
    fontSize: 20,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  quote: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 15,
    color: colors.textPrimary,
    lineHeight: 24,
    marginBottom: spacing.md,
    paddingLeft: spacing.md,
    borderLeftWidth: 2,
    borderLeftColor: colors.gold,
  },
  expansion: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
    marginBottom: spacing.md,
  },
  actionsRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  primaryBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 12,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    flex: 1,
  },
  primaryBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 14,
    letterSpacing: 0.6,
  },
  savedChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  savedChipText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.liturgical.purple,
    letterSpacing: 0.5,
  },
  empty: {
    fontFamily: fonts.bodyRegular,
    fontStyle: "italic",
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
    marginBottom: spacing.md,
  },
  pressed: { opacity: 0.7 },
  skeletonRow: {
    height: 14,
    borderRadius: 7,
    backgroundColor: colors.borderSoft,
    marginVertical: 6,
  },
});

const modalStyles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.background,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  iconBtn: { width: 40, alignItems: "center" },
  headerTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
  },
  scroll: { flex: 1 },
  scrollContent: { padding: spacing.lg, paddingBottom: spacing.xl },
  refRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginBottom: spacing.xs,
  },
  title: {
    fontFamily: fonts.headingSemi,
    fontSize: 22,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  quote: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 16,
    color: colors.textPrimary,
    lineHeight: 26,
    marginBottom: spacing.lg,
    paddingLeft: spacing.md,
    borderLeftWidth: 2,
    borderLeftColor: colors.gold,
  },
  prompt: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 15,
    color: colors.liturgical.purple,
    lineHeight: 24,
    marginBottom: spacing.lg,
  },
  label: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.2,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.md,
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textPrimary,
    minHeight: 100,
    textAlignVertical: "top",
    marginBottom: spacing.lg,
  },
  reflectionBox: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.gold,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  reflectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: spacing.sm,
  },
  reflectionHeaderText: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1.5,
    color: colors.gold,
  },
  reflectionText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textPrimary,
    lineHeight: 24,
  },
  primaryBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 14,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
  },
  primaryBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 15,
    letterSpacing: 0.6,
  },
  secondaryBtn: {
    paddingVertical: 12,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  secondaryBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.textSecondary,
    fontSize: 14,
    letterSpacing: 0.4,
  },
  actionsCol: {
    flexDirection: "column",
    gap: spacing.sm,
  },
  error: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: "#b1452e",
    marginBottom: spacing.md,
  },
});

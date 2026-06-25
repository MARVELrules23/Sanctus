import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  TextInput,
  View,
} from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";

import { api, DailyPractice } from "@/src/api";
import { useI18n } from "@/src/i18n";
import { colors, fonts, radius, spacing } from "@/src/theme";

type Props = {
  date: string; // YYYY-MM-DD
};

const INTENSITY_LABEL: Record<string, string> = {
  easy: "Light",
  moderate: "Moderate",
  hard: "Hard",
};

/**
 * Today's spiritual / mortification practice card.
 *
 * - Deterministic per (user, date) on the backend, with last-90-days
 *   exclusion so the same practice is essentially never repeated.
 * - Tap "Mark complete" to record completion (optionally with a note).
 * - "Journal this" deep-links into the journal with a seed.
 */
export default function DailyPracticeCard({ date }: Props) {
  const router = useRouter();
  const { lang } = useI18n();
  const [practice, setPractice] = useState<DailyPractice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [noteOpen, setNoteOpen] = useState(false);
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const p = await api<DailyPractice>(
        `/daily-practice?date=${encodeURIComponent(date)}`,
      );
      setPractice(p);
      setNote(p.note || "");
    } catch (e: any) {
      setError(e?.message || "Couldn't load today's practice");
    } finally {
      setLoading(false);
    }
  }, [date, lang]);

  useEffect(() => {
    void load();
  }, [load]);

  const onComplete = useCallback(async () => {
    if (!practice) return;
    setSubmitting(true);
    try {
      const updated = await api<DailyPractice>(`/daily-practice/complete`, {
        method: "POST",
        body: { date, note: note.trim() || undefined },
      });
      setPractice(updated);
      setNoteOpen(false);
    } catch (e: any) {
      setError(e?.message || "Couldn't save");
    } finally {
      setSubmitting(false);
    }
  }, [practice, date, note]);

  const onUndo = useCallback(async () => {
    setSubmitting(true);
    try {
      const updated = await api<DailyPractice>(
        `/daily-practice/complete?date=${encodeURIComponent(date)}`,
        { method: "DELETE" },
      );
      setPractice(updated);
      setNote("");
    } catch (e: any) {
      setError(e?.message || "Couldn't undo");
    } finally {
      setSubmitting(false);
    }
  }, [date]);

  const onJournal = useCallback(() => {
    if (!practice) return;
    const body =
      `Today's practice: ${practice.title}\n\n` +
      `Virtue: ${practice.virtue}\n` +
      `What it asks: ${practice.body}\n\n` +
      `Why it matters: ${practice.why}\n\n` +
      `Reflection:\n`;
    router.push({
      pathname: "/journal",
      params: {
        date,
        seed_title: `Daily practice — ${practice.title}`,
        seed_body: body,
      },
    });
  }, [practice, date, router]);

  // ---- Render states ----
  if (loading) {
    return (
      <View style={styles.card} testID="daily-practice-card">
        <View style={styles.header}>
          <Ionicons name="sparkles-outline" size={16} color={colors.gold} />
          <Text style={styles.eyebrow}>TODAY&apos;S PRACTICE</Text>
        </View>
        <ActivityIndicator size="small" color={colors.gold} style={{ marginTop: spacing.md }} />
      </View>
    );
  }

  if (error || !practice) {
    return (
      <View style={styles.card} testID="daily-practice-card">
        <View style={styles.header}>
          <Ionicons name="sparkles-outline" size={16} color={colors.gold} />
          <Text style={styles.eyebrow}>TODAY&apos;S PRACTICE</Text>
        </View>
        <Text style={styles.errorText}>{error || "No practice available."}</Text>
        <Pressable
          onPress={load}
          style={({ pressed }) => [styles.linkBtn, pressed && { opacity: 0.7 }]}
        >
          <Text style={styles.linkBtnText}>Try again</Text>
        </Pressable>
      </View>
    );
  }

  const isDone = !!practice.completed_at;

  return (
    <View style={styles.card} testID="daily-practice-card">
      <View style={styles.header}>
        <Ionicons
          name={isDone ? "checkmark-circle" : "sparkles-outline"}
          size={16}
          color={isDone ? colors.liturgical.green : colors.gold}
        />
        <Text style={styles.eyebrow}>TODAY&apos;S PRACTICE</Text>
        <View style={styles.headerBadge}>
          <Text style={styles.headerBadgeText}>{practice.category.toUpperCase()}</Text>
        </View>
      </View>

      <Text style={styles.title} testID="daily-practice-title">
        {practice.title}
      </Text>

      <Text style={styles.body} numberOfLines={expanded ? undefined : 3}>
        {practice.body}
      </Text>

      <View style={styles.metaRow}>
        <View style={styles.metaItem}>
          <Ionicons name="ribbon-outline" size={12} color={colors.gold} />
          <Text style={styles.metaText}>{practice.virtue}</Text>
        </View>
        <View style={styles.metaDot} />
        <View style={styles.metaItem}>
          <Ionicons name="speedometer-outline" size={12} color={colors.gold} />
          <Text style={styles.metaText}>
            {INTENSITY_LABEL[practice.intensity] || practice.intensity}
          </Text>
        </View>
      </View>

      {expanded ? (
        <View style={styles.whyBox}>
          <Text style={styles.whyLabel}>WHY</Text>
          <Text style={styles.whyText}>{practice.why}</Text>
        </View>
      ) : null}

      <Pressable
        onPress={() => setExpanded((e) => !e)}
        style={({ pressed }) => [styles.expandRow, pressed && { opacity: 0.7 }]}
        testID="daily-practice-expand"
      >
        <Text style={styles.expandText}>
          {expanded ? "Show less" : "Show more"}
        </Text>
        <Ionicons
          name={expanded ? "chevron-up" : "chevron-down"}
          size={14}
          color={colors.textSecondary}
        />
      </Pressable>

      {/* Completion / actions */}
      {isDone ? (
        <View style={styles.doneBlock} testID="daily-practice-done">
          <View style={styles.doneRow}>
            <Ionicons name="checkmark-done-outline" size={16} color={colors.liturgical.green} />
            <Text style={styles.doneText}>
              Completed
              {practice.completed_at
                ? ` at ${new Date(practice.completed_at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`
                : ""}
            </Text>
          </View>
          {practice.note ? (
            <Text style={styles.doneNote}>&ldquo;{practice.note}&rdquo;</Text>
          ) : null}
          <View style={styles.actionsRow}>
            <Pressable
              onPress={onJournal}
              style={({ pressed }) => [styles.secondaryBtn, pressed && { opacity: 0.7 }]}
              testID="daily-practice-journal"
            >
              <Ionicons name="create-outline" size={14} color={colors.gold} />
              <Text style={styles.secondaryBtnText}>Journal this</Text>
            </Pressable>
            <Pressable
              onPress={onUndo}
              disabled={submitting}
              style={({ pressed }) => [styles.ghostBtn, pressed && { opacity: 0.7 }]}
              testID="daily-practice-undo"
            >
              <Text style={styles.ghostBtnText}>Undo</Text>
            </Pressable>
          </View>
        </View>
      ) : (
        <View style={styles.actionsBlock}>
          {noteOpen ? (
            <TextInput
              value={note}
              onChangeText={setNote}
              placeholder="Optional note (how did it go?)"
              placeholderTextColor={colors.textMuted}
              style={styles.noteInput}
              multiline
              numberOfLines={2}
              testID="daily-practice-note"
            />
          ) : null}
          <View style={styles.actionsRow}>
            <Pressable
              onPress={onComplete}
              disabled={submitting}
              style={({ pressed }) => [
                styles.primaryBtn,
                pressed && { opacity: 0.85 },
                submitting && { opacity: 0.5 },
              ]}
              testID="daily-practice-complete"
            >
              <Ionicons name="checkmark-circle-outline" size={16} color={colors.gold} />
              <Text style={styles.primaryBtnText}>
                {submitting ? "Saving…" : "Mark complete"}
              </Text>
            </Pressable>
            <Pressable
              onPress={() => setNoteOpen((o) => !o)}
              style={({ pressed }) => [styles.ghostBtn, pressed && { opacity: 0.7 }]}
              testID="daily-practice-add-note"
            >
              <Ionicons
                name={noteOpen ? "remove-outline" : "add-outline"}
                size={14}
                color={colors.textSecondary}
              />
              <Text style={styles.ghostBtnText}>
                {noteOpen ? "Hide note" : "Add note"}
              </Text>
            </Pressable>
          </View>
        </View>
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
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
    marginBottom: spacing.sm,
  },
  eyebrow: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1.8,
    color: colors.gold,
  },
  headerBadge: {
    marginLeft: "auto",
    backgroundColor: "rgba(212,175,55,0.12)",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: "rgba(212,175,55,0.3)",
  },
  headerBadgeText: {
    fontFamily: fonts.uiSemi,
    fontSize: 9,
    letterSpacing: 0.8,
    color: colors.gold,
  },
  title: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  body: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 21,
    marginBottom: spacing.sm,
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  metaItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  metaDot: {
    width: 3,
    height: 3,
    backgroundColor: colors.textMuted,
    borderRadius: 1.5,
    marginHorizontal: 8,
  },
  metaText: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textSecondary,
  },
  whyBox: {
    backgroundColor: "rgba(212,175,55,0.05)",
    borderLeftWidth: 3,
    borderLeftColor: colors.gold,
    paddingLeft: spacing.sm,
    paddingVertical: spacing.xs,
    marginBottom: spacing.sm,
  },
  whyLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 9,
    letterSpacing: 1.6,
    color: colors.gold,
    marginBottom: 2,
  },
  whyText: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 13,
    color: colors.textPrimary,
    lineHeight: 19,
  },
  expandRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingVertical: 2,
    marginBottom: spacing.sm,
  },
  expandText: {
    fontFamily: fonts.uiMedium,
    fontSize: 12,
    color: colors.textSecondary,
  },
  actionsBlock: {
    marginTop: spacing.xs,
  },
  noteInput: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textPrimary,
    backgroundColor: "rgba(0,0,0,0.03)",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.md,
    padding: spacing.sm,
    marginBottom: spacing.sm,
    minHeight: 44,
    textAlignVertical: "top",
  },
  actionsRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  primaryBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: colors.primary,
    paddingVertical: 11,
    borderRadius: radius.round,
  },
  primaryBtnText: {
    fontFamily: fonts.uiSemi,
    fontSize: 13,
    color: colors.gold,
  },
  secondaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingVertical: 9,
    paddingHorizontal: 12,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: "rgba(212,175,55,0.4)",
  },
  secondaryBtnText: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.gold,
  },
  ghostBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingVertical: 9,
    paddingHorizontal: 10,
  },
  ghostBtnText: {
    fontFamily: fonts.uiMedium,
    fontSize: 12,
    color: colors.textSecondary,
  },
  doneBlock: {
    marginTop: spacing.xs,
  },
  doneRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 4,
  },
  doneText: {
    fontFamily: fonts.uiMedium,
    fontSize: 13,
    color: colors.liturgical.green,
  },
  doneNote: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: 4,
    marginBottom: spacing.sm,
  },
  errorText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.liturgical.red,
    marginTop: spacing.sm,
  },
  linkBtn: {
    marginTop: spacing.sm,
    alignSelf: "flex-start",
  },
  linkBtnText: {
    fontFamily: fonts.uiSemi,
    fontSize: 13,
    color: colors.gold,
  },
});

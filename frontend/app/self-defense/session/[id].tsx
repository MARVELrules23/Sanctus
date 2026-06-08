import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";

import { api, SDSession } from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { timeAgo } from "@/src/utils/time-ago";

const INTENSITIES: Array<"low" | "medium" | "high"> = ["low", "medium", "high"];

export default function SDSessionViewerScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ id?: string }>();
  const sessionId = typeof params.id === "string" ? params.id : "";

  const [session, setSession] = useState<SDSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [showReflection, setShowReflection] = useState(true);
  const [showCompleteModal, setShowCompleteModal] = useState(false);
  const [completeNotes, setCompleteNotes] = useState("");
  const [completeIntensity, setCompleteIntensity] = useState<"low" | "medium" | "high" | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    if (!sessionId) return;
    try {
      const r = await api<SDSession>(`/self-defense/sessions/${sessionId}`);
      setSession(r);
      setShowReflection(r.include_patron_reflection);
    } catch (e: any) {
      Alert.alert("Couldn't load session", e?.message || "Please try again.");
      router.back();
    } finally {
      setLoading(false);
    }
  }, [sessionId, router]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  const onComplete = async () => {
    if (!session) return;
    setSubmitting(true);
    try {
      const r = await api<SDSession>(`/self-defense/sessions/${session.session_id}/complete`, {
        method: "POST",
        body: { notes: completeNotes, intensity_actual: completeIntensity },
      });
      setSession(r);
      setShowCompleteModal(false);
      setCompleteNotes("");
      setCompleteIntensity(null);
    } catch (e: any) {
      Alert.alert("Couldn't save", e?.message || "Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const onUncomplete = () => {
    if (!session) return;
    Alert.alert("Mark as not completed?", "This will undo your completion record.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Undo",
        style: "destructive",
        onPress: async () => {
          try {
            const r = await api<SDSession>(`/self-defense/sessions/${session.session_id}/uncomplete`, { method: "POST" });
            setSession(r);
          } catch (e: any) {
            Alert.alert("Couldn't undo", e?.message || "Please try again.");
          }
        },
      },
    ]);
  };

  const onRedo = async () => {
    if (!session) return;
    try {
      const r = await api<SDSession>(`/self-defense/sessions/${session.session_id}/redo`, { method: "POST" });
      router.replace({ pathname: "/self-defense/session/[id]", params: { id: r.session_id } });
    } catch (e: any) {
      Alert.alert("Couldn't redo", e?.message || "Please try again.");
    }
  };

  const onDelete = () => {
    if (!session) return;
    Alert.alert("Delete this session?", "This cannot be undone.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await api(`/self-defense/sessions/${session.session_id}`, { method: "DELETE" });
            router.back();
          } catch (e: any) {
            Alert.alert("Couldn't delete", e?.message || "Please try again.");
          }
        },
      },
    ]);
  };

  if (loading || !session) {
    return (
      <SafeAreaView style={styles.safe}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
        </View>
      </SafeAreaView>
    );
  }

  const { plan, patron } = session;
  const isCompleted = !!session.completed_at;

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="sd-session-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="sd-session-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle} numberOfLines={1}>{session.discipline_name}</Text>
        <Pressable onPress={onDelete} hitSlop={12} testID="sd-session-delete">
          <Ionicons name="trash-outline" size={20} color={colors.textMuted} />
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Title block */}
        <View style={styles.titleBlock}>
          <Text style={styles.focusTag}>{(plan.technique_focus || "").toUpperCase()}</Text>
          <Text style={styles.titleText}>{plan.title}</Text>
          <View style={styles.metaRow}>
            <MetaItem icon="barbell-outline" label={session.level} />
            <MetaItem icon="time-outline" label={`${session.duration_minutes} min`} />
            {plan.intensity ? <MetaItem icon="flame-outline" label={plan.intensity} /> : null}
            {session.source === "redo" ? <MetaItem icon="refresh-outline" label="redo" /> : null}
          </View>
          {isCompleted ? (
            <View style={styles.completedBanner}>
              <Ionicons name="checkmark-circle" size={16} color={colors.gold} />
              <Text style={styles.completedText}>
                Completed {timeAgo(session.completed_at!)}
                {session.intensity_actual ? ` · felt ${session.intensity_actual}` : ""}
              </Text>
            </View>
          ) : null}
          {isCompleted && session.completion_notes ? (
            <Text style={styles.completedNotes}>"{session.completion_notes}"</Text>
          ) : null}
        </View>

        {/* Patron reflection */}
        {patron?.name && (showReflection || !plan.patron_reflection) && plan.patron_reflection ? (
          <View style={styles.reflectionCard} testID="sd-reflection">
            <View style={styles.cardHeader}>
              <Ionicons name={(patron.icon as any) || "ribbon-outline"} size={16} color={colors.gold} />
              <Text style={styles.cardHeaderText}>{patron.name.toUpperCase()}</Text>
              <Pressable onPress={() => setShowReflection((s) => !s)} hitSlop={8} testID="sd-reflection-toggle">
                <Ionicons name={showReflection ? "chevron-up" : "chevron-down"} size={18} color={colors.textMuted} />
              </Pressable>
            </View>
            <Text style={styles.reflectionText}>{plan.patron_reflection}</Text>
            {plan.patron_prayer ? (
              <View style={styles.prayerBox}>
                <Text style={styles.prayerLabel}>PRAYER</Text>
                <Text style={styles.prayerText}>{plan.patron_prayer}</Text>
              </View>
            ) : null}
          </View>
        ) : null}

        {/* Warmup */}
        {plan.warmup && plan.warmup.length > 0 ? (
          <Block title="Warm-up" icon="sunny-outline">
            {plan.warmup.map((w, i) => (
              <Row key={i} index={i + 1} title={w.name}
                meta={w.duration_seconds ? `${w.duration_seconds}s` : undefined}
                notes={w.notes} />
            ))}
          </Block>
        ) : null}

        {/* Drills */}
        {plan.drills && plan.drills.length > 0 ? (
          <Block title="Drills" icon="repeat-outline">
            {plan.drills.map((d, i) => (
              <Row key={i} index={i + 1} title={d.name}
                meta={d.sets} notes={d.notes}
                badge={d.solo_safe === false ? "needs partner" : undefined} />
            ))}
          </Block>
        ) : null}

        {/* Technique focus */}
        {plan.technique_block ? (
          <Block title="Technique focus" icon="aperture-outline">
            <Text style={styles.techniqueName}>{plan.technique_block.name}</Text>
            {plan.technique_block.key_points && plan.technique_block.key_points.length > 0 ? (
              <>
                <Text style={styles.subLabel}>Key points</Text>
                {plan.technique_block.key_points.map((p, i) => (
                  <Text key={i} style={styles.bullet}>· {p}</Text>
                ))}
              </>
            ) : null}
            {plan.technique_block.common_errors && plan.technique_block.common_errors.length > 0 ? (
              <>
                <Text style={[styles.subLabel, { color: colors.liturgical.red }]}>Common errors</Text>
                {plan.technique_block.common_errors.map((p, i) => (
                  <Text key={i} style={styles.bulletErr}>✗ {p}</Text>
                ))}
              </>
            ) : null}
            {plan.technique_block.progression_hint ? (
              <View style={styles.hintBox}>
                <Ionicons name="arrow-forward" size={12} color={colors.primary} />
                <Text style={styles.hintText}>{plan.technique_block.progression_hint}</Text>
              </View>
            ) : null}
          </Block>
        ) : null}

        {/* Live application */}
        {plan.live_application && plan.live_application.length > 0 ? (
          <Block title="Live application" icon="flash-outline">
            {plan.live_application.map((l, i) => (
              <View key={i} style={styles.liveRow}>
                <Text style={styles.liveTitle}>
                  {l.name}
                  {l.requires_partner ? " " : ""}
                  {l.requires_partner ? <Text style={styles.partnerTag}>(partner)</Text> : null}
                </Text>
                <Text style={styles.liveDesc}>{l.description}</Text>
              </View>
            ))}
          </Block>
        ) : null}

        {/* Cooldown */}
        {plan.cooldown && plan.cooldown.length > 0 ? (
          <Block title="Cool-down" icon="moon-outline">
            {plan.cooldown.map((c, i) => (
              <Row key={i} index={i + 1} title={c.name}
                meta={c.duration_seconds ? `${c.duration_seconds}s` : undefined} />
            ))}
          </Block>
        ) : null}

        {/* Coach note */}
        {plan.coach_note ? (
          <View style={styles.coachCard}>
            <Ionicons name="chatbubble-outline" size={14} color={colors.gold} />
            <Text style={styles.coachText}>{plan.coach_note}</Text>
          </View>
        ) : null}

        <View style={{ height: spacing.xxl }} />
      </ScrollView>

      {/* Bottom action bar */}
      <View style={styles.bottomBar}>
        <Pressable
          onPress={onRedo}
          testID="sd-redo"
          style={({ pressed }) => [styles.secondaryBtn, pressed && { opacity: 0.7 }]}
        >
          <Ionicons name="refresh" size={16} color={colors.primary} />
          <Text style={styles.secondaryBtnText}>Redo</Text>
        </Pressable>
        {isCompleted ? (
          <Pressable
            onPress={onUncomplete}
            testID="sd-uncomplete"
            style={({ pressed }) => [styles.primaryBtn, { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft }, pressed && { opacity: 0.7 }]}
          >
            <Ionicons name="checkmark-done" size={16} color={colors.primary} />
            <Text style={[styles.primaryBtnText, { color: colors.primary }]}>Completed</Text>
          </Pressable>
        ) : (
          <Pressable
            onPress={() => setShowCompleteModal(true)}
            testID="sd-complete"
            style={({ pressed }) => [styles.primaryBtn, pressed && { opacity: 0.7 }]}
          >
            <Ionicons name="checkmark-circle" size={16} color={colors.gold} />
            <Text style={styles.primaryBtnText}>Mark complete</Text>
          </Pressable>
        )}
      </View>

      {/* Complete modal */}
      <Modal
        transparent
        visible={showCompleteModal}
        animationType="slide"
        onRequestClose={() => setShowCompleteModal(false)}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={styles.modalScrim}
        >
          <Pressable style={{ flex: 1 }} onPress={() => setShowCompleteModal(false)} />
          <View style={styles.completeSheet}>
            <Text style={styles.completeTitle}>Mark session complete</Text>
            <Text style={styles.completeSub}>How did it actually feel?</Text>
            <View style={styles.chipsRow}>
              {INTENSITIES.map((iv) => (
                <Pressable
                  key={iv}
                  onPress={() => setCompleteIntensity(iv)}
                  testID={`sd-complete-intensity-${iv}`}
                  style={({ pressed }) => [styles.chip, completeIntensity === iv && styles.chipActive, pressed && { opacity: 0.7 }]}
                >
                  <Text style={[styles.chipText, completeIntensity === iv && styles.chipTextActive]}>{iv}</Text>
                </Pressable>
              ))}
            </View>
            <TextInput
              testID="sd-complete-notes"
              value={completeNotes}
              onChangeText={setCompleteNotes}
              placeholder="Optional notes (what clicked, what to revisit)…"
              placeholderTextColor={colors.textMuted}
              style={styles.notesInput}
              multiline
              maxLength={1000}
            />
            <View style={styles.completeActions}>
              <Pressable onPress={() => setShowCompleteModal(false)} style={({ pressed }) => [styles.btnGhost, pressed && { opacity: 0.7 }]}>
                <Text style={styles.btnGhostText}>Cancel</Text>
              </Pressable>
              <Pressable
                onPress={onComplete}
                disabled={submitting}
                testID="sd-complete-submit"
                style={({ pressed }) => [styles.btnPrimary, submitting && { opacity: 0.6 }, pressed && { opacity: 0.7 }]}
              >
                <Text style={styles.btnPrimaryText}>{submitting ? "Saving…" : "Save"}</Text>
              </Pressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

function MetaItem({ icon, label }: { icon: any; label: string }) {
  return (
    <View style={styles.metaItem}>
      <Ionicons name={icon} size={12} color={colors.gold} />
      <Text style={styles.metaItemText}>{label}</Text>
    </View>
  );
}

function Block({ title, icon, children }: { title: string; icon: any; children: React.ReactNode }) {
  return (
    <View style={styles.block}>
      <View style={styles.cardHeader}>
        <Ionicons name={icon} size={16} color={colors.gold} />
        <Text style={styles.cardHeaderText}>{title.toUpperCase()}</Text>
      </View>
      {children}
    </View>
  );
}

function Row({ index, title, meta, notes, badge }:
  { index: number; title: string; meta?: string; notes?: string; badge?: string }) {
  return (
    <View style={styles.itemRow}>
      <View style={styles.itemIndex}>
        <Text style={styles.itemIndexText}>{index}</Text>
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.itemTitle}>{title}</Text>
        {meta ? <Text style={styles.itemMeta}>{meta}</Text> : null}
        {notes ? <Text style={styles.itemNotes}>{notes}</Text> : null}
        {badge ? (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{badge}</Text>
          </View>
        ) : null}
      </View>
    </View>
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
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 17, color: colors.textPrimary, flex: 1, textAlign: "center", marginHorizontal: spacing.sm },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  scroll: { padding: spacing.lg, paddingBottom: 100 },
  titleBlock: { marginBottom: spacing.md },
  focusTag: { fontFamily: fonts.uiSemi, fontSize: 10, letterSpacing: 2, color: colors.gold },
  titleText: { fontFamily: fonts.headingBold, fontSize: 24, color: colors.textPrimary, marginTop: 4 },
  metaRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: spacing.sm },
  metaItem: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.round, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft },
  metaItemText: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textSecondary, textTransform: "capitalize" },
  completedBanner: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: spacing.sm, backgroundColor: colors.primary, borderRadius: radius.round, paddingHorizontal: 12, paddingVertical: 6, alignSelf: "flex-start" },
  completedText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 11 },
  completedNotes: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textSecondary, fontSize: 13, marginTop: 6 },
  reflectionCard: { backgroundColor: colors.surface, borderRadius: radius.md, padding: spacing.md, marginBottom: spacing.md, borderWidth: 1, borderColor: colors.borderSoft, ...shadow.card },
  cardHeader: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: spacing.sm },
  cardHeaderText: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 2, color: colors.gold, flex: 1 },
  reflectionText: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary, lineHeight: 21 },
  prayerBox: { backgroundColor: colors.background, borderRadius: radius.sm, padding: spacing.sm, marginTop: spacing.sm, borderLeftWidth: 3, borderLeftColor: colors.gold },
  prayerLabel: { fontFamily: fonts.uiSemi, fontSize: 9, letterSpacing: 1.6, color: colors.gold },
  prayerText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13, color: colors.textPrimary, lineHeight: 20, marginTop: 4 },
  block: { backgroundColor: colors.surface, borderRadius: radius.md, padding: spacing.md, marginBottom: spacing.md, borderWidth: 1, borderColor: colors.borderSoft, ...shadow.card },
  itemRow: { flexDirection: "row", marginBottom: spacing.sm },
  itemIndex: { width: 26, height: 26, borderRadius: 13, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center", marginRight: spacing.sm },
  itemIndexText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 12 },
  itemTitle: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  itemMeta: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.primary, marginTop: 1 },
  itemNotes: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textSecondary, marginTop: 4, lineHeight: 18 },
  badge: { alignSelf: "flex-start", paddingHorizontal: 6, paddingVertical: 2, borderRadius: radius.round, backgroundColor: "#FCE9E9", marginTop: 4 },
  badgeText: { fontFamily: fonts.uiSemi, fontSize: 10, color: colors.liturgical.red },
  techniqueName: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary, marginBottom: 6 },
  subLabel: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.gold, letterSpacing: 1.5, marginTop: spacing.sm, marginBottom: 4 },
  bullet: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textPrimary, lineHeight: 20, marginLeft: 4 },
  bulletErr: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.liturgical.red, lineHeight: 20, marginLeft: 4 },
  hintBox: { flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: colors.background, borderRadius: radius.sm, padding: spacing.sm, marginTop: spacing.sm },
  hintText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.primary, flex: 1 },
  liveRow: { marginBottom: spacing.sm },
  liveTitle: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  partnerTag: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted },
  liveDesc: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, lineHeight: 19, marginTop: 2 },
  coachCard: { flexDirection: "row", alignItems: "flex-start", gap: 8, backgroundColor: colors.primary, borderRadius: radius.md, padding: spacing.md, marginTop: spacing.sm },
  coachText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 14, color: colors.gold, flex: 1, lineHeight: 21 },
  bottomBar: {
    flexDirection: "row",
    gap: spacing.sm,
    padding: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
    backgroundColor: colors.surface,
  },
  secondaryBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, paddingHorizontal: spacing.lg, paddingVertical: 12, borderRadius: radius.round, borderWidth: 1, borderColor: colors.primary, backgroundColor: colors.background },
  secondaryBtnText: { fontFamily: fonts.uiSemi, color: colors.primary, fontSize: 13 },
  primaryBtn: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, paddingVertical: 12, borderRadius: radius.round, backgroundColor: colors.primary },
  primaryBtnText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 13 },
  modalScrim: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: "flex-end" },
  completeSheet: { backgroundColor: colors.background, borderTopLeftRadius: radius.lg, borderTopRightRadius: radius.lg, padding: spacing.lg, paddingBottom: spacing.xl },
  completeTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  completeSub: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, marginTop: 4, marginBottom: spacing.sm },
  chipsRow: { flexDirection: "row", gap: 6, marginTop: 4, marginBottom: spacing.sm },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surface },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textSecondary, textTransform: "capitalize" },
  chipTextActive: { color: colors.gold, fontFamily: fonts.uiSemi },
  notesInput: { backgroundColor: colors.surface, borderRadius: radius.md, padding: spacing.md, minHeight: 80, fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary, borderWidth: 1, borderColor: colors.borderSoft, textAlignVertical: "top" },
  completeActions: { flexDirection: "row", justifyContent: "flex-end", gap: spacing.sm, marginTop: spacing.md },
  btnGhost: { paddingHorizontal: spacing.lg, paddingVertical: 10 },
  btnGhostText: { fontFamily: fonts.uiSemi, color: colors.textSecondary },
  btnPrimary: { paddingHorizontal: spacing.lg, paddingVertical: 10, borderRadius: radius.round, backgroundColor: colors.primary },
  btnPrimaryText: { fontFamily: fonts.uiSemi, color: colors.gold },
});

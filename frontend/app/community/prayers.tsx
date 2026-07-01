import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  RefreshControl,
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
  PrayerIntention,
  createPrayerIntention,
  deletePrayerIntention,
  listPrayerIntentions,
  togglePrayForIntention,
} from "@/src/api";
import { confirmAction } from "@/src/confirm";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Math.max(0, Date.now() - then);
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}

export default function PrayerJournalScreen() {
  const router = useRouter();
  const [items, setItems] = useState<PrayerIntention[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [body, setBody] = useState("");
  const [anonymous, setAnonymous] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    const res = await listPrayerIntentions();
    setItems(res.items);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await load();
      } catch (e) {
        console.warn("prayers load failed", e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await load();
    } finally {
      setRefreshing(false);
    }
  };

  const submit = async () => {
    const text = body.trim();
    if (!text || submitting) return;
    setSubmitting(true);
    try {
      const created = await createPrayerIntention(text, anonymous);
      setItems((prev) => [created, ...prev]);
      setBody("");
      setAnonymous(false);
    } catch (e) {
      console.warn("create prayer failed", e);
    } finally {
      setSubmitting(false);
    }
  };

  const togglePray = async (p: PrayerIntention) => {
    // optimistic
    setItems((prev) =>
      prev.map((it) =>
        it.prayer_id === p.prayer_id
          ? { ...it, prayed_by_me: !it.prayed_by_me, pray_count: it.pray_count + (it.prayed_by_me ? -1 : 1) }
          : it,
      ),
    );
    try {
      const res = await togglePrayForIntention(p.prayer_id);
      setItems((prev) =>
        prev.map((it) =>
          it.prayer_id === p.prayer_id ? { ...it, prayed_by_me: res.prayed, pray_count: res.pray_count } : it,
        ),
      );
    } catch (e) {
      console.warn("toggle pray failed", e);
      await load();
    }
  };

  const remove = async (p: PrayerIntention) => {
    const ok = await confirmAction("Delete this intention?", "This cannot be undone.");
    if (!ok) return;
    setItems((prev) => prev.filter((it) => it.prayer_id !== p.prayer_id));
    try {
      await deletePrayerIntention(p.prayer_id);
    } catch (e) {
      console.warn("delete prayer failed", e);
      await load();
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="prayer-journal-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="prayer-journal-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Prayer Journal</Text>
        <View style={{ width: 26 }} />
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
        >
          <Text style={styles.intro}>
            Share what weighs on your heart. The parish will lift it up in prayer.
          </Text>

          {/* Composer */}
          <View style={styles.composer}>
            <TextInput
              testID="prayer-input"
              style={styles.input}
              placeholder="Please pray for…"
              placeholderTextColor={colors.textMuted}
              value={body}
              onChangeText={setBody}
              multiline
              maxLength={1500}
            />
            <View style={styles.composerRow}>
              <View style={styles.anonRow}>
                <Switch
                  testID="prayer-anon-toggle"
                  value={anonymous}
                  onValueChange={setAnonymous}
                  trackColor={{ true: colors.gold, false: colors.borderSoft }}
                  thumbColor="#FAF9F6"
                />
                <Text style={styles.anonLabel}>Post anonymously</Text>
              </View>
              <Pressable
                testID="prayer-submit"
                onPress={submit}
                disabled={!body.trim() || submitting}
                style={({ pressed }) => [
                  styles.submitBtn,
                  (!body.trim() || submitting) && styles.submitBtnDisabled,
                  pressed && styles.pressed,
                ]}
              >
                {submitting ? (
                  <ActivityIndicator color={colors.gold} size="small" />
                ) : (
                  <Text style={styles.submitText}>Share</Text>
                )}
              </Pressable>
            </View>
          </View>

          {loading ? (
            <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xxl }} />
          ) : items.length === 0 ? (
            <View style={styles.empty}>
              <Ionicons name="hand-left-outline" size={30} color={colors.gold} />
              <Text style={styles.emptyText}>No intentions yet. Be the first to ask for prayer.</Text>
            </View>
          ) : (
            items.map((p) => (
              <View key={p.prayer_id} style={styles.card} testID={`prayer-item-${p.prayer_id}`}>
                <View style={styles.cardHead}>
                  <Text style={styles.author}>
                    {p.anonymous || !p.author ? "Anonymous" : p.author.name}
                  </Text>
                  <Text style={styles.time}>{timeAgo(p.created_at)}</Text>
                </View>
                <Text style={styles.body}>{p.body}</Text>
                <View style={styles.actions}>
                  <Pressable
                    testID={`prayer-pray-${p.prayer_id}`}
                    onPress={() => togglePray(p)}
                    style={({ pressed }) => [
                      styles.prayBtn,
                      p.prayed_by_me && styles.prayBtnOn,
                      pressed && styles.pressed,
                    ]}
                  >
                    <Ionicons
                      name={p.prayed_by_me ? "hand-left" : "hand-left-outline"}
                      size={16}
                      color={p.prayed_by_me ? colors.primary : colors.gold}
                    />
                    <Text style={[styles.prayText, p.prayed_by_me && styles.prayTextOn]}>
                      {p.prayed_by_me ? "Prayed" : "I prayed"}
                      {p.pray_count > 0 ? ` · ${p.pray_count}` : ""}
                    </Text>
                  </Pressable>
                  {p.is_mine ? (
                    <Pressable
                      testID={`prayer-delete-${p.prayer_id}`}
                      onPress={() => remove(p)}
                      hitSlop={8}
                      style={({ pressed }) => [styles.deleteBtn, pressed && styles.pressed]}
                    >
                      <Ionicons name="trash-outline" size={16} color={colors.textMuted} />
                    </Pressable>
                  ) : null}
                </View>
              </View>
            ))
          )}
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      </KeyboardAvoidingView>
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
  headerTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
    flex: 1,
    textAlign: "center",
    marginHorizontal: spacing.sm,
  },
  scroll: { padding: spacing.lg },
  intro: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 21,
    marginBottom: spacing.md,
  },
  composer: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.md,
    ...shadow.card,
  },
  input: {
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textPrimary,
    minHeight: 60,
    textAlignVertical: "top",
  },
  composerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: spacing.sm,
  },
  anonRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  anonLabel: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textSecondary },
  submitBtn: {
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.lg,
    paddingVertical: 10,
    borderRadius: radius.md,
    minWidth: 76,
    alignItems: "center",
  },
  submitBtnDisabled: { opacity: 0.5 },
  submitText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 14, letterSpacing: 0.5 },
  empty: { alignItems: "center", marginTop: spacing.xxl, gap: spacing.sm },
  emptyText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: "center",
    maxWidth: 260,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.md,
    marginTop: spacing.md,
    ...shadow.card,
  },
  cardHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  author: { fontFamily: fonts.headingSemi, fontSize: 14, color: colors.textPrimary },
  time: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted },
  body: {
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textPrimary,
    lineHeight: 23,
    marginTop: 6,
  },
  actions: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: spacing.sm,
  },
  prayBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.gold,
  },
  prayBtnOn: { backgroundColor: colors.gold, borderColor: colors.gold },
  prayText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold },
  prayTextOn: { color: colors.primary },
  deleteBtn: { padding: 6 },
  pressed: { opacity: 0.7 },
});

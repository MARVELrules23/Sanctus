/**
 * Admin · Liturgical Challenges
 *
 * Lets philipwils13 (and any future admin) review tracks, generate
 * AI-drafted day content, edit each day's title / theme / patron /
 * reflection / prayer items, and publish/unpublish individual days
 * (or the whole track).
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
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
  AdminChallenge,
  ChallengeDay,
  ChallengePrayerItem,
  adminGenerateChallengeDays,
  adminListChallengeDays,
  adminListChallenges,
  adminPatchChallengeDay,
  adminPublishChallenge,
  adminUnpublishChallenge,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { formatLongFromISO } from "@/src/date-utils";

function isoDate(s: string | null | undefined): string {
  if (!s) return "";
  return s.slice(0, 10);
}

export default function AdminChallengesScreen() {
  const router = useRouter();
  const { user, ready } = useAuth();
  const [items, setItems] = useState<AdminChallenge[]>([]);
  const [loading, setLoading] = useState(true);
  const [openSlug, setOpenSlug] = useState<string | null>(null);
  const [days, setDays] = useState<Record<string, ChallengeDay[]>>({});
  const [loadingDays, setLoadingDays] = useState<string | null>(null);
  const [generating, setGenerating] = useState<string | null>(null);
  const [editingDay, setEditingDay] = useState<ChallengeDay | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await adminListChallenges();
      setItems(r.items || []);
    } catch (e: any) {
      Alert.alert("Couldn't load challenges", e?.message || "");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!ready) return;
    if (!user?.is_admin) return;
    void load();
  }, [ready, user, load]);

  const onExpand = async (slug: string) => {
    if (openSlug === slug) {
      setOpenSlug(null);
      return;
    }
    setOpenSlug(slug);
    if (!days[slug]) {
      setLoadingDays(slug);
      try {
        const r = await adminListChallengeDays(slug);
        setDays((prev) => ({ ...prev, [slug]: r.items || [] }));
      } catch (e: any) {
        Alert.alert("Couldn't load days", e?.message || "");
      } finally {
        setLoadingDays(null);
      }
    }
  };

  const onGenerate = async (slug: string, overwrite: boolean) => {
    if (generating) return;
    const conf = await new Promise<boolean>((resolve) => {
      Alert.alert(
        overwrite ? "Regenerate all days?" : "Generate missing days?",
        overwrite
          ? "This overwrites every existing day with fresh AI drafts. Existing edits will be lost."
          : "Draft AI content for any day that doesn't have content yet.",
        [
          { text: "Cancel", style: "cancel", onPress: () => resolve(false) },
          { text: overwrite ? "Regenerate" : "Generate", onPress: () => resolve(true) },
        ],
      );
    });
    if (!conf) return;
    setGenerating(slug);
    try {
      const r = await adminGenerateChallengeDays(slug, { overwrite });
      const okCount = (r.results || []).filter((x) => !x.skipped).length;
      const failCount = (r.failures || []).length;
      Alert.alert(
        "Done",
        `Generated ${okCount} day(s).${failCount ? ` ${failCount} failed.` : ""}`,
      );
      // refresh both list + days
      const d = await adminListChallengeDays(slug);
      setDays((prev) => ({ ...prev, [slug]: d.items || [] }));
      await load();
    } catch (e: any) {
      Alert.alert("Generation failed", e?.message || "");
    } finally {
      setGenerating(null);
    }
  };

  const onTogglePublish = async (c: AdminChallenge) => {
    try {
      if (c.status === "published") {
        await adminUnpublishChallenge(c.slug);
      } else {
        await adminPublishChallenge(c.slug);
      }
      await load();
    } catch (e: any) {
      Alert.alert("Couldn't update status", e?.message || "");
    }
  };

  const onToggleDayPublish = async (slug: string, day: ChallengeDay) => {
    try {
      const next = day.status === "published" ? "draft" : "published";
      const updated = await adminPatchChallengeDay(day.day_id, { status: next });
      setDays((prev) => ({
        ...prev,
        [slug]: (prev[slug] || []).map((d) => (d.day_id === day.day_id ? updated : d)),
      }));
    } catch (e: any) {
      Alert.alert("Couldn't update day", e?.message || "");
    }
  };

  if (!ready) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      </SafeAreaView>
    );
  }

  if (!user?.is_admin) {
    return (
      <SafeAreaView style={styles.safe} edges={["top"]}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <Ionicons name="chevron-back" size={26} color={colors.primary} />
          </Pressable>
          <Text style={styles.headerTitle}>Admin · Challenges</Text>
          <View style={{ width: 26 }} />
        </View>
        <View style={styles.center}>
          <Text style={styles.empty}>Admin access required.</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="admin-challenges-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Admin · Challenges</Text>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          {items.map((c) => {
            const accent = c.color || colors.gold;
            const isOpen = openSlug === c.slug;
            const list = days[c.slug] || [];
            return (
              <View key={c.challenge_id} style={[styles.card, { borderColor: accent }]}>
                <Pressable onPress={() => onExpand(c.slug)}>
                  <View style={styles.cardHead}>
                    <Ionicons
                      name={(c.icon as keyof typeof Ionicons.glyphMap) || "flame-outline"}
                      size={20}
                      color={accent}
                    />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.cardName}>{c.name}</Text>
                      <Text style={styles.cardMeta}>
                        {c.status.toUpperCase()} · {c.published_days}/{c.total_days} published
                      </Text>
                      {c.start_date && c.end_date ? (
                        <Text style={styles.cardDates}>
                          {formatLongFromISO(isoDate(c.start_date))} → {formatLongFromISO(isoDate(c.end_date))}
                        </Text>
                      ) : null}
                    </View>
                    <Ionicons
                      name={isOpen ? "chevron-up" : "chevron-down"}
                      size={20}
                      color={colors.textMuted}
                    />
                  </View>
                </Pressable>

                <View style={styles.actionsRow}>
                  <Pressable
                    testID={`admin-generate-missing-${c.slug}`}
                    disabled={generating === c.slug}
                    onPress={() => onGenerate(c.slug, false)}
                    style={({ pressed }) => [
                      styles.actionBtn,
                      { backgroundColor: accent },
                      (pressed || generating === c.slug) && { opacity: 0.7 },
                    ]}
                  >
                    {generating === c.slug ? (
                      <ActivityIndicator size="small" color={colors.gold} />
                    ) : (
                      <>
                        <Ionicons name="sparkles" size={14} color={colors.gold} />
                        <Text style={styles.actionBtnText}>Generate missing</Text>
                      </>
                    )}
                  </Pressable>
                  <Pressable
                    onPress={() => onGenerate(c.slug, true)}
                    disabled={generating === c.slug}
                    style={({ pressed }) => [
                      styles.actionBtnGhost,
                      pressed && { opacity: 0.7 },
                    ]}
                  >
                    <Ionicons name="refresh" size={14} color={colors.textPrimary} />
                    <Text style={styles.actionBtnGhostText}>Regen all</Text>
                  </Pressable>
                  <Pressable
                    testID={`admin-publish-${c.slug}`}
                    onPress={() => onTogglePublish(c)}
                    style={({ pressed }) => [
                      styles.actionBtnGhost,
                      pressed && { opacity: 0.7 },
                    ]}
                  >
                    <Ionicons
                      name={c.status === "published" ? "eye-off-outline" : "eye-outline"}
                      size={14}
                      color={colors.textPrimary}
                    />
                    <Text style={styles.actionBtnGhostText}>
                      {c.status === "published" ? "Unpublish" : "Publish"}
                    </Text>
                  </Pressable>
                </View>

                {isOpen ? (
                  loadingDays === c.slug ? (
                    <View style={{ paddingVertical: spacing.lg }}>
                      <ActivityIndicator color={accent} />
                    </View>
                  ) : list.length === 0 ? (
                    <Text style={styles.emptyDays}>No days yet. Hit &ldquo;Generate missing&rdquo;.</Text>
                  ) : (
                    <View style={{ marginTop: spacing.sm }}>
                      {list.map((d) => (
                        <View key={d.day_id} style={styles.dayRow}>
                          <View style={[styles.dayBadge, { borderColor: accent }]}>
                            <Text style={[styles.dayBadgeText, { color: accent }]}>{d.day_index}</Text>
                          </View>
                          <Pressable
                            onPress={() => setEditingDay(d)}
                            style={{ flex: 1 }}
                          >
                            <Text style={styles.dayTitle} numberOfLines={1}>
                              {d.title || `Day ${d.day_index}`}
                            </Text>
                            <Text style={styles.dayMeta} numberOfLines={1}>
                              {isoDate(d.date)} · {d.patron_saint || "—"}
                            </Text>
                          </Pressable>
                          <Pressable
                            onPress={() => onToggleDayPublish(c.slug, d)}
                            style={[
                              styles.statusPill,
                              d.status === "published"
                                ? { backgroundColor: accent }
                                : { backgroundColor: colors.borderSoft },
                            ]}
                          >
                            <Text
                              style={[
                                styles.statusPillText,
                                d.status === "published" && { color: colors.gold },
                              ]}
                            >
                              {d.status === "published" ? "LIVE" : "DRAFT"}
                            </Text>
                          </Pressable>
                          <Pressable onPress={() => setEditingDay(d)} hitSlop={8}>
                            <Ionicons name="pencil" size={16} color={colors.textMuted} />
                          </Pressable>
                        </View>
                      ))}
                    </View>
                  )
                ) : null}
              </View>
            );
          })}

          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}

      <DayEditorModal
        day={editingDay}
        onClose={() => setEditingDay(null)}
        onSaved={(updated) => {
          // Patch in-memory days list
          const slug = (items.find((x) => x.challenge_id === updated.challenge_id) || {}).slug;
          if (slug) {
            setDays((prev) => ({
              ...prev,
              [slug]: (prev[slug] || []).map((d) =>
                d.day_id === updated.day_id ? updated : d,
              ),
            }));
          }
          setEditingDay(null);
        }}
      />
    </SafeAreaView>
  );
}

function DayEditorModal({
  day,
  onClose,
  onSaved,
}: {
  day: ChallengeDay | null;
  onClose: () => void;
  onSaved: (d: ChallengeDay) => void;
}) {
  const [title, setTitle] = useState("");
  const [theme, setTheme] = useState("");
  const [patron, setPatron] = useState("");
  const [patronBlurb, setPatronBlurb] = useState("");
  const [reflection, setReflection] = useState("");
  const [itemsJson, setItemsJson] = useState("[]");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!day) return;
    setTitle(day.title || "");
    setTheme(day.theme || "");
    setPatron(day.patron_saint || "");
    setPatronBlurb(day.patron_blurb || "");
    setReflection(day.reflection || "");
    setItemsJson(JSON.stringify(day.prayer_items || [], null, 2));
  }, [day]);

  const onSave = async () => {
    if (!day) return;
    let parsedItems: ChallengePrayerItem[] = [];
    try {
      const arr = JSON.parse(itemsJson);
      if (!Array.isArray(arr)) throw new Error("not an array");
      parsedItems = arr;
    } catch {
      Alert.alert("Items JSON invalid", "Prayer items must be valid JSON array.");
      return;
    }
    setSaving(true);
    try {
      const updated = await adminPatchChallengeDay(day.day_id, {
        title,
        theme,
        patron_saint: patron,
        patron_blurb: patronBlurb,
        reflection,
        prayer_items: parsedItems,
      });
      onSaved(updated);
    } catch (e: any) {
      Alert.alert("Couldn't save", e?.message || "");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal visible={!!day} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
        <View style={styles.header}>
          <Pressable onPress={onClose} hitSlop={12}>
            <Ionicons name="close" size={24} color={colors.primary} />
          </Pressable>
          <Text style={styles.headerTitle}>Edit Day {day?.day_index ?? ""}</Text>
          <Pressable onPress={onSave} disabled={saving} hitSlop={12}>
            {saving ? (
              <ActivityIndicator size="small" color={colors.gold} />
            ) : (
              <Text style={styles.saveBtn}>Save</Text>
            )}
          </Pressable>
        </View>
        <ScrollView contentContainerStyle={{ padding: spacing.lg }}>
          <Field label="Title" value={title} onChange={setTitle} />
          <Field label="Theme" value={theme} onChange={setTheme} />
          <Field label="Patron Saint" value={patron} onChange={setPatron} />
          <Field label="Patron Blurb" value={patronBlurb} onChange={setPatronBlurb} multiline />
          <Field label="Reflection" value={reflection} onChange={setReflection} multiline />
          <Field
            label="Prayer Items (JSON)"
            value={itemsJson}
            onChange={setItemsJson}
            multiline
            mono
          />
          <Text style={styles.helpText}>
            Each prayer item: {"{"} kind, title, detail? {"}"}. Kinds: prayer, fast,
            almsgiving, reading, devotion.
          </Text>
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

function Field({
  label,
  value,
  onChange,
  multiline,
  mono,
}: {
  label: string;
  value: string;
  onChange: (s: string) => void;
  multiline?: boolean;
  mono?: boolean;
}) {
  return (
    <View style={{ marginBottom: spacing.md }}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChange}
        multiline={multiline}
        style={[
          styles.input,
          multiline && { minHeight: 80, textAlignVertical: "top" },
          mono && { fontFamily: "Courier", fontSize: 12 },
        ]}
        placeholderTextColor={colors.textMuted}
      />
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
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  saveBtn: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.gold },
  scroll: { padding: spacing.lg },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl },
  empty: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted },
  emptyDays: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textMuted,
    marginTop: spacing.md,
  },

  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1.5,
    marginBottom: spacing.md,
    ...shadow.card,
  },
  cardHead: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  cardName: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  cardMeta: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1.2,
    color: colors.textMuted,
    marginTop: 2,
  },
  cardDates: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 2,
  },

  actionsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginTop: spacing.md,
  },
  actionBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: radius.round,
  },
  actionBtnText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold },
  actionBtnGhost: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.background,
  },
  actionBtnGhostText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textPrimary },

  dayRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
  },
  dayBadge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 1.5,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.background,
  },
  dayBadgeText: { fontFamily: fonts.uiSemi, fontSize: 11 },
  dayTitle: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textPrimary },
  dayMeta: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  statusPill: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.round,
  },
  statusPillText: {
    fontFamily: fonts.uiSemi,
    fontSize: 9,
    letterSpacing: 1,
    color: colors.textSecondary,
  },

  fieldLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.2,
    color: colors.gold,
    marginBottom: 4,
  },
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textPrimary,
  },
  helpText: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 11,
    color: colors.textMuted,
    marginTop: -spacing.sm,
  },
});

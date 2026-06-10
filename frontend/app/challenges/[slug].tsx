/**
 * Challenge Detail — a single track view (Hallowtide / Advent / Lent).
 *
 * Shows: opening prayer, the (optional) preparation content (e.g., the
 * soul-cake recipe for Hallowtide), and a list of all days with reflection,
 * patron saint, and prayer items. Each day card has a check-in button.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import {
  ChallengeDay,
  ChallengeDetail,
  checkinChallenge,
  enrollChallenge,
  getChallenge,
  unenrollChallenge,
} from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { todayISO, formatLongFromISO } from "@/src/date-utils";

function iso(s: string | null | undefined): string | null {
  if (!s) return null;
  return s.slice(0, 10);
}

export default function ChallengeDetailScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const router = useRouter();
  const [data, setData] = useState<ChallengeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);
  const [busyDay, setBusyDay] = useState<string | null>(null);
  const [doneDays, setDoneDays] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<string | null>(null);
  const today = todayISO();

  const load = useCallback(async () => {
    if (!slug) return;
    try {
      const d = await getChallenge(slug);
      setData(d);
      const done = new Set<string>();
      // We don't have per-day done state from this endpoint, but today's is
      // available; the rest come via separate progress fetch on demand.
      if (d.today_checkin?.completed) {
        const todayDay = (d.days || []).find((x) => iso(x.date) === today);
        if (todayDay) done.add(todayDay.day_id);
      }
      setDoneDays(done);
    } catch (e: any) {
      Alert.alert("Couldn't load", e?.message || "Try again.");
    } finally {
      setLoading(false);
    }
  }, [slug, today]);

  useEffect(() => { void load(); }, [load]);

  // Auto-expand today's day on first load.
  useEffect(() => {
    if (!data || expanded !== null) return;
    const td = (data.days || []).find((d) => iso(d.date) === today);
    if (td) setExpanded(td.day_id);
  }, [data, today, expanded]);

  const enrolled = !!data?.enrolled;
  const accent = data?.color || colors.gold;

  const onToggleEnroll = async (next: boolean) => {
    if (!slug || toggling) return;
    setToggling(true);
    try {
      if (next) await enrollChallenge(slug);
      else await unenrollChallenge(slug);
      await load();
    } catch (e: any) {
      Alert.alert("Couldn't update", e?.message || "Try again.");
    } finally {
      setToggling(false);
    }
  };

  const onCheckIn = async (day: ChallengeDay) => {
    if (!slug || busyDay) return;
    if (!enrolled) {
      Alert.alert("Enroll first", "Turn the toggle on to walk this season — then mark days complete.");
      return;
    }
    const dStr = iso(day.date);
    if (!dStr) return;
    if (dStr > today) {
      Alert.alert("Not yet", "This day hasn't arrived yet.");
      return;
    }
    setBusyDay(day.day_id);
    try {
      await checkinChallenge(slug, {
        date: dStr,
        completed: true,
        items_done: (day.prayer_items || []).map((p) => p.title),
      });
      setDoneDays((prev) => new Set(prev).add(day.day_id));
    } catch (e: any) {
      Alert.alert("Couldn't check in", e?.message || "Try again.");
    } finally {
      setBusyDay(null);
    }
  };

  const visibleDays = useMemo(() => data?.days || [], [data]);
  const prep = data?.preparation_content;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={`challenge-detail-${slug}`}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>{data?.name || "Challenge"}</Text>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      ) : !data ? (
        <View style={styles.center}>
          <Text style={styles.empty}>This challenge isn&apos;t available right now.</Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          {/* Hero */}
          <View style={[styles.hero, { borderColor: accent }]}>
            <View style={styles.heroHead}>
              <Ionicons
                name={(data.icon as keyof typeof Ionicons.glyphMap) || "flame-outline"}
                size={22}
                color={accent}
              />
              <Text style={[styles.heroSeason, { color: accent }]}>
                {data.subtitle || data.season}
              </Text>
            </View>
            {data.start_date && data.end_date ? (
              <Text style={styles.heroDates}>
                {formatLongFromISO(iso(data.start_date)!)} → {formatLongFromISO(iso(data.end_date)!)}
              </Text>
            ) : null}
            {data.patron_saint ? (
              <Text style={styles.heroPatron}>Patron · {data.patron_saint}</Text>
            ) : null}
            {data.blurb ? <Text style={styles.heroBlurb}>{data.blurb}</Text> : null}

            <View style={styles.enrollRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.enrollLabel}>
                  {enrolled ? "Tracking your participation" : "Track my participation"}
                </Text>
                <Text style={styles.enrollSub}>
                  {enrolled
                    ? "Counts streaks and daily check-ins"
                    : "Optional — calendar overlays use the master toggle on the Calendar tab"}
                </Text>
              </View>
              {toggling ? (
                <ActivityIndicator size="small" color={accent} />
              ) : (
                <Switch
                  testID={`challenge-detail-toggle-${slug}`}
                  value={enrolled}
                  onValueChange={onToggleEnroll}
                  trackColor={{ false: colors.borderSoft, true: accent }}
                  thumbColor={colors.gold}
                />
              )}
            </View>

            {enrolled && data.enrollment ? (
              <View style={styles.statRow}>
                <View style={styles.statChip}>
                  <Ionicons name="flame" size={12} color={colors.gold} />
                  <Text style={styles.statText}>
                    {data.enrollment.current_streak}-day streak
                  </Text>
                </View>
                <View style={styles.statChip}>
                  <Ionicons name="checkmark-circle" size={12} color={accent} />
                  <Text style={styles.statText}>
                    {data.enrollment.total_days_completed} / {data.total_days} days
                  </Text>
                </View>
              </View>
            ) : null}
          </View>

          {/* Opening prayer */}
          {data.opening_prayer ? (
            <View style={styles.card}>
              <Text style={styles.sectionLabel}>OPENING PRAYER</Text>
              <Text style={styles.prayer}>{data.opening_prayer}</Text>
            </View>
          ) : null}

          {/* Preparation content (Hallowtide soul cakes etc.) */}
          {prep ? (
            <View style={styles.card} testID="challenge-prep">
              <Text style={styles.sectionLabel}>PREPARATION</Text>
              {prep.title ? <Text style={styles.prepTitle}>{prep.title}</Text> : null}
              {prep.intro ? <Text style={styles.prepIntro}>{prep.intro}</Text> : null}
              {prep.recipe ? (
                <View style={styles.recipe}>
                  {prep.recipe.yield ? (
                    <Text style={styles.recipeYield}>{prep.recipe.yield}</Text>
                  ) : null}
                  {(prep.recipe.ingredients || []).length ? (
                    <>
                      <Text style={styles.recipeHead}>Ingredients</Text>
                      {prep.recipe.ingredients!.map((ing, i) => (
                        <Text key={i} style={styles.recipeItem}>• {ing}</Text>
                      ))}
                    </>
                  ) : null}
                  {(prep.recipe.steps || []).length ? (
                    <>
                      <Text style={styles.recipeHead}>Steps</Text>
                      {prep.recipe.steps!.map((s, i) => (
                        <Text key={i} style={styles.recipeItem}>{i + 1}. {s}</Text>
                      ))}
                    </>
                  ) : null}
                </View>
              ) : null}
              {prep.encouragement ? (
                <Text style={styles.prepEnc}>{prep.encouragement}</Text>
              ) : null}
            </View>
          ) : null}

          {/* Days */}
          <Text style={styles.sectionLabelTop}>DAY BY DAY</Text>
          {visibleDays.length === 0 ? (
            <Text style={styles.empty}>
              Daily content is still being prepared. Check back soon.
            </Text>
          ) : (
            visibleDays.map((d) => {
              const dStr = iso(d.date) || "";
              const isToday = dStr === today;
              const isPast = dStr < today;
              const isOpen = expanded === d.day_id;
              const isDone = doneDays.has(d.day_id);
              return (
                <View
                  key={d.day_id}
                  testID={`challenge-day-${d.day_index}`}
                  style={[
                    styles.dayCard,
                    isToday && { borderColor: accent, borderWidth: 1.5 },
                  ]}
                >
                  <Pressable
                    onPress={() => setExpanded(isOpen ? null : d.day_id)}
                    style={({ pressed }) => [{ opacity: pressed ? 0.85 : 1 }]}
                  >
                    <View style={styles.dayHead}>
                      <View style={[styles.dayBadge, { borderColor: accent }]}>
                        <Text style={[styles.dayBadgeText, { color: accent }]}>
                          {d.day_index}
                        </Text>
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.dayTitle} numberOfLines={2}>
                          {d.title || `Day ${d.day_index}`}
                        </Text>
                        <Text style={styles.dayMeta}>
                          {dStr ? formatLongFromISO(dStr) : "—"}
                          {d.theme ? ` · ${d.theme}` : ""}
                        </Text>
                      </View>
                      {isDone ? (
                        <Ionicons name="checkmark-circle" size={20} color={accent} />
                      ) : isToday ? (
                        <View style={[styles.todayPill, { backgroundColor: accent }]}>
                          <Text style={styles.todayPillText}>TODAY</Text>
                        </View>
                      ) : isPast ? (
                        <Ionicons name="ellipsis-horizontal" size={16} color={colors.textMuted} />
                      ) : (
                        <Ionicons name="lock-closed-outline" size={16} color={colors.textMuted} />
                      )}
                      <Ionicons
                        name={isOpen ? "chevron-up" : "chevron-down"}
                        size={16}
                        color={colors.textMuted}
                        style={{ marginLeft: 4 }}
                      />
                    </View>
                    {d.patron_saint ? (
                      <Text style={styles.dayPatron}>
                        <Ionicons name="sparkles-outline" size={11} color={colors.gold} /> {d.patron_saint}
                      </Text>
                    ) : null}
                  </Pressable>

                  {/* Always render the check-in row (testID stays in the DOM
                      so flows can locate it even when the day card is
                      collapsed). The button is disabled for future days. */}
                  {!isDone ? (
                    <Pressable
                      testID={`challenge-day-checkin-${d.day_index}`}
                      disabled={busyDay === d.day_id || (!isToday && !isPast)}
                      onPress={() => onCheckIn(d)}
                      style={({ pressed }) => [
                        styles.checkBtnSmall,
                        { backgroundColor: !isToday && !isPast ? colors.borderSoft : accent },
                        (pressed || busyDay === d.day_id) && { opacity: 0.7 },
                      ]}
                    >
                      {busyDay === d.day_id ? (
                        <ActivityIndicator color={colors.gold} size="small" />
                      ) : (
                        <>
                          <Ionicons
                            name={
                              !isToday && !isPast
                                ? "lock-closed-outline"
                                : "checkmark-circle-outline"
                            }
                            size={14}
                            color={!isToday && !isPast ? colors.textMuted : colors.gold}
                          />
                          <Text
                            style={[
                              styles.checkBtnSmallText,
                              !isToday && !isPast && { color: colors.textMuted },
                            ]}
                          >
                            {!isToday && !isPast ? "Not yet" : isToday ? "Mark today complete" : "Mark complete"}
                          </Text>
                        </>
                      )}
                    </Pressable>
                  ) : (
                    <View
                      testID={`challenge-day-checkin-${d.day_index}`}
                      style={[styles.checkBtnSmall, { backgroundColor: colors.background, borderWidth: 1, borderColor: accent }]}
                    >
                      <Ionicons name="checkmark-circle" size={14} color={accent} />
                      <Text style={[styles.checkBtnSmallText, { color: accent }]}>Completed</Text>
                    </View>
                  )}

                  {isOpen ? (
                    <View style={styles.dayBody}>
                      {d.patron_blurb ? (
                        <Text style={styles.patronBlurb}>{d.patron_blurb}</Text>
                      ) : null}
                      {d.reflection ? (
                        <Text style={styles.reflection}>{d.reflection}</Text>
                      ) : null}
                      {(d.prayer_items || []).length ? (
                        <View style={styles.itemsWrap}>
                          {d.prayer_items.map((it, i) => (
                            <View key={i} style={styles.itemRow}>
                              <View style={[styles.itemBullet, { backgroundColor: accent }]} />
                              <View style={{ flex: 1 }}>
                                <Text style={styles.itemTitle}>{it.title}</Text>
                                {it.detail ? (
                                  <Text style={styles.itemDetail}>{it.detail}</Text>
                                ) : null}
                              </View>
                            </View>
                          ))}
                        </View>
                      ) : null}
                    </View>
                  ) : null}
                </View>
              );
            })
          )}

          {/* Closing prayer */}
          {data.closing_prayer ? (
            <View style={[styles.card, { marginTop: spacing.lg }]}>
              <Text style={styles.sectionLabel}>CLOSING PRAYER</Text>
              <Text style={styles.prayer}>{data.closing_prayer}</Text>
            </View>
          ) : null}

          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}
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
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl },
  empty: { textAlign: "center", fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted },

  hero: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1.5,
    ...shadow.card,
  },
  heroHead: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  heroSeason: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.6,
  },
  heroDates: {
    fontFamily: fonts.uiMedium,
    fontSize: 12,
    color: colors.textMuted,
    marginTop: 6,
  },
  heroPatron: {
    fontFamily: fonts.uiSemi,
    fontSize: 13,
    color: colors.gold,
    marginTop: 4,
  },
  heroBlurb: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
    marginTop: spacing.sm,
  },
  enrollRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    marginTop: spacing.md,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
  },
  enrollLabel: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  enrollSub: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  statRow: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm, flexWrap: "wrap" },
  statChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.round,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  statText: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.textPrimary },

  card: {
    marginTop: spacing.md,
    padding: spacing.lg,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  sectionLabel: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 2, color: colors.gold },
  sectionLabelTop: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 2,
    color: colors.gold,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  prayer: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 15,
    lineHeight: 24,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },

  prepTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
    marginTop: spacing.sm,
  },
  prepIntro: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    lineHeight: 22,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  recipe: { marginTop: spacing.md },
  recipeYield: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textMuted },
  recipeHead: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    letterSpacing: 1.2,
    color: colors.gold,
    marginTop: spacing.md,
  },
  recipeItem: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    lineHeight: 20,
    color: colors.textPrimary,
    marginTop: 4,
  },
  prepEnc: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: spacing.md,
  },

  dayCard: {
    marginBottom: spacing.sm,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  dayHead: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  dayBadge: {
    width: 34,
    height: 34,
    borderRadius: 17,
    borderWidth: 1.5,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.background,
  },
  dayBadgeText: { fontFamily: fonts.uiSemi, fontSize: 12 },
  dayTitle: { fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary },
  dayMeta: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  dayPatron: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold, marginTop: 6, marginLeft: 42 },
  todayPill: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: radius.round },
  todayPillText: { fontFamily: fonts.uiSemi, fontSize: 9, letterSpacing: 1, color: colors.gold },

  dayBody: {
    marginTop: spacing.sm,
    paddingTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
  },
  patronBlurb: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 13,
    lineHeight: 22,
    color: colors.textSecondary,
    marginTop: 4,
  },
  reflection: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    lineHeight: 22,
    color: colors.textPrimary,
    marginTop: spacing.sm,
  },
  itemsWrap: { marginTop: spacing.md, gap: 8 },
  itemRow: { flexDirection: "row", alignItems: "flex-start", gap: 8 },
  itemBullet: { width: 6, height: 6, borderRadius: 3, marginTop: 7 },
  itemTitle: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textPrimary },
  itemDetail: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
    lineHeight: 18,
  },

  checkBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 10,
    borderRadius: radius.round,
    marginTop: spacing.md,
  },
  checkBtnText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold, letterSpacing: 0.6 },
  checkBtnSmall: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: radius.round,
    marginTop: spacing.sm,
    alignSelf: "flex-start",
    marginLeft: 42,
  },
  checkBtnSmallText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold, letterSpacing: 0.4 },
});

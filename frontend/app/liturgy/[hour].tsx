/**
 * Sanctus — Liturgy of the Hours reader.
 *
 * Renders one Hour (Lauds / Vespers / Compline) for a chosen weekday.
 * A day selector lets the user pick the ferial psalmody (hidden for
 * Compline, whose psalter is fixed). Latin & English render side-by-side
 * on wide screens, stacked on phones. Free for all authenticated users.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import {
  getLiturgyHour,
  getLiturgyDay,
  LiturgyHourDetail,
  LiturgySection,
} from "@/src/api";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type DisplayMode = "both" | "english" | "latin";

const JS_DAY_TO_KEY = [
  "sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
];

export default function LiturgyReaderScreen() {
  const { hour } = useLocalSearchParams<{ hour: string }>();
  const router = useRouter();
  const { width } = useWindowDimensions();

  const [detail, setDetail] = useState<LiturgyHourDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedDay, setSelectedDay] = useState<string>(
    JS_DAY_TO_KEY[new Date().getDay()],
  );
  const [sections, setSections] = useState<LiturgySection[]>([]);
  const [loadingSections, setLoadingSections] = useState(false);
  const [mode, setMode] = useState<DisplayMode>("both");

  const sideBySide = width >= 520;
  const accent = detail?.accent_color || colors.gold;

  const loadDetail = useCallback(async () => {
    if (!hour) return;
    setLoadingDetail(true);
    setError(null);
    try {
      const d = await getLiturgyHour(hour);
      setDetail(d);
    } catch (e: any) {
      setError(e?.message || "Could not load this Hour.");
    } finally {
      setLoadingDetail(false);
    }
  }, [hour]);

  const loadDay = useCallback(async (dayKey: string) => {
    if (!hour) return;
    setLoadingSections(true);
    try {
      const p = await getLiturgyDay(hour, dayKey);
      setSections(p.sections || []);
    } catch {
      setSections([]);
    } finally {
      setLoadingSections(false);
    }
  }, [hour]);

  useEffect(() => { void loadDetail(); }, [loadDetail]);
  useEffect(() => { void loadDay(selectedDay); }, [loadDay, selectedDay]);

  const todayKey = JS_DAY_TO_KEY[new Date().getDay()];
  const showDaySelector = detail?.psalms_vary_by_day ?? true;

  const renderParas = (text: string | null | undefined, baseStyle: any) => {
    if (!text) return null;
    return text.split(/\n{2,}/).map((p, i) => (
      <Text key={i} style={baseStyle}>{p}</Text>
    ));
  };

  const dayChips = useMemo(() => detail?.days || [], [detail]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={`liturgy-reader-${hour}`}>
      <Stack.Screen options={{ headerShown: false }} />

      <View style={styles.header}>
        <Pressable testID="liturgy-reader-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.headerTitle} numberOfLines={1}>
            {detail?.name || "Hour"}
          </Text>
          {detail ? (
            <Text style={styles.headerSub} numberOfLines={1}>{detail.latin_name}</Text>
          ) : null}
        </View>
        <View style={{ width: 26 }} />
      </View>

      {/* Mode toggle */}
      {detail ? (
        <View style={styles.modeRow}>
          {(
            [
              { key: "both", label: "Side by Side", icon: "swap-horizontal" },
              { key: "english", label: "English", icon: "language" },
              { key: "latin", label: "Latin", icon: "book" },
            ] as { key: DisplayMode; label: string; icon: keyof typeof Ionicons.glyphMap }[]
          ).map((opt) => {
            const active = mode === opt.key;
            return (
              <Pressable
                key={opt.key}
                testID={`liturgy-mode-${opt.key}`}
                onPress={() => setMode(opt.key)}
                style={({ pressed }) => [
                  styles.modeChip,
                  active && { backgroundColor: accent, borderColor: accent },
                  pressed && { opacity: 0.85 },
                ]}
              >
                <Ionicons name={opt.icon} size={13} color={active ? colors.gold : colors.textSecondary} />
                <Text style={[styles.modeChipText, active && { color: colors.gold }]}>{opt.label}</Text>
              </Pressable>
            );
          })}
        </View>
      ) : null}

      {/* Day selector */}
      {detail && showDaySelector ? (
        <View style={styles.dayStrip}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.dayScroll}>
            {dayChips.map((d) => {
              const active = d.key === selectedDay;
              const isToday = d.key === todayKey;
              return (
                <Pressable
                  key={d.key}
                  testID={`liturgy-day-${d.key}`}
                  onPress={() => setSelectedDay(d.key)}
                  style={({ pressed }) => [
                    styles.dayChip,
                    active && { backgroundColor: accent, borderColor: accent },
                    pressed && { opacity: 0.85 },
                  ]}
                >
                  <Text style={[styles.dayChipText, active && { color: colors.gold }]}>
                    {d.name.slice(0, 3)}
                  </Text>
                  {isToday ? (
                    <View style={[styles.todayDot, { backgroundColor: active ? colors.gold : accent }]} />
                  ) : null}
                </Pressable>
              );
            })}
          </ScrollView>
        </View>
      ) : null}

      {loadingDetail ? (
        <View style={styles.center}><ActivityIndicator color={accent} /></View>
      ) : error || !detail ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error || "Hour not found."}</Text>
          <Pressable onPress={loadDetail} style={({ pressed }) => [styles.retry, pressed && { opacity: 0.7 }]}>
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          {/* Intro */}
          <View style={[styles.introCard, { borderColor: accent }]}>
            <Ornament />
            <Text style={[styles.introLatin, { color: accent }]}>{detail.latin_name.toUpperCase()}</Text>
            <Text style={styles.introName}>{detail.name}</Text>
            <Text style={styles.introSubtitle}>{detail.subtitle} · {detail.time_of_day}</Text>
            <Text style={styles.introBody}>{detail.intro}</Text>
          </View>

          {loadingSections ? (
            <View style={{ paddingVertical: spacing.xxl }}>
              <ActivityIndicator color={accent} />
            </View>
          ) : (
            sections.map((sec) => {
              const hasLatin = !!sec.latin;
              const renderBoth = mode === "both" && hasLatin;
              const showEnglish = mode !== "latin" || !hasLatin;
              const showLatin = mode !== "english" && hasLatin;

              return (
                <View
                  key={sec.index}
                  testID={`liturgy-section-${sec.index}`}
                  style={[styles.sectionCard, { borderTopColor: accent }]}
                >
                  <View style={styles.sectionHeadRow}>
                    <View style={[styles.sectionBadge, { borderColor: accent }]}>
                      <Text style={[styles.sectionBadgeText, { color: accent }]}>{sec.index + 1}</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.sectionTitle}>{sec.title}</Text>
                      {sec.latin_title ? (
                        <Text style={[styles.sectionLatinTitle, { color: accent }]}>{sec.latin_title}</Text>
                      ) : null}
                    </View>
                  </View>

                  {sec.rubric ? (
                    <View style={[styles.rubricBox, { borderLeftColor: accent }]}>
                      <Ionicons name="information-circle-outline" size={13} color={accent} />
                      <Text style={styles.rubricText}>{sec.rubric}</Text>
                    </View>
                  ) : null}

                  {renderBoth && sideBySide ? (
                    <View style={styles.twoCol}>
                      <View style={[styles.col, { borderRightWidth: StyleSheet.hairlineWidth, borderRightColor: colors.borderSoft, paddingRight: spacing.sm }]}>
                        <Text style={[styles.colLabel, { color: accent }]}>LATIN</Text>
                        {renderParas(sec.latin, styles.latinText)}
                      </View>
                      <View style={[styles.col, { paddingLeft: spacing.sm }]}>
                        <Text style={[styles.colLabel, { color: accent }]}>ENGLISH</Text>
                        {renderParas(sec.english, styles.englishText)}
                      </View>
                    </View>
                  ) : renderBoth ? (
                    <View style={styles.stacked}>
                      <View>
                        <Text style={[styles.colLabel, { color: accent }]}>LATIN</Text>
                        {renderParas(sec.latin, styles.latinText)}
                      </View>
                      <View style={{ borderTopColor: colors.borderSoft, borderTopWidth: StyleSheet.hairlineWidth, paddingTop: spacing.sm, marginTop: spacing.sm }}>
                        <Text style={[styles.colLabel, { color: accent }]}>ENGLISH</Text>
                        {renderParas(sec.english, styles.englishText)}
                      </View>
                    </View>
                  ) : (
                    <View>
                      {showLatin ? (
                        <View style={{ marginBottom: showEnglish ? spacing.md : 0 }}>
                          <Text style={[styles.colLabel, { color: accent }]}>LATIN</Text>
                          {renderParas(sec.latin, styles.latinText)}
                        </View>
                      ) : null}
                      {showEnglish ? (
                        <View>
                          {hasLatin ? (
                            <Text style={[styles.colLabel, { color: accent }]}>ENGLISH</Text>
                          ) : null}
                          {renderParas(sec.english, styles.englishText)}
                        </View>
                      ) : null}
                    </View>
                  )}

                  {sec.note ? <Text style={styles.noteText}>{sec.note}</Text> : null}
                </View>
              );
            })
          )}

          <View style={{ height: spacing.xxl * 2 }} />
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
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
    gap: spacing.md,
  },
  headerTitleWrap: { flex: 1, alignItems: "center" },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 17, color: colors.textPrimary },
  headerSub: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, fontSize: 11, marginTop: 1 },

  modeRow: {
    flexDirection: "row",
    justifyContent: "center",
    gap: spacing.xs,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  modeChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.surface,
  },
  modeChipText: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 0.4, color: colors.textSecondary },

  dayStrip: {
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
    backgroundColor: colors.surface,
    paddingVertical: spacing.sm,
  },
  dayScroll: { paddingHorizontal: spacing.md, gap: 6 },
  dayChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.background,
  },
  dayChipText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary, letterSpacing: 0.3 },
  todayDot: { width: 6, height: 6, borderRadius: 3 },

  scroll: { padding: spacing.lg, paddingBottom: spacing.xxl },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.md },
  errorText: { fontFamily: fonts.bodyRegular, color: colors.textSecondary, textAlign: "center" },
  retry: { paddingHorizontal: spacing.lg, paddingVertical: 10, backgroundColor: colors.primary, borderRadius: radius.round },
  retryText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 13 },

  introCard: {
    alignItems: "center",
    padding: spacing.lg,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    ...shadow.card,
    gap: spacing.xs,
    marginBottom: spacing.lg,
  },
  introLatin: { fontFamily: fonts.uiSemi, fontSize: 10, letterSpacing: 1.6, marginTop: spacing.sm },
  introName: { fontFamily: fonts.headingBold, fontSize: 22, color: colors.textPrimary, textAlign: "center" },
  introSubtitle: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12.5, color: colors.textSecondary, textAlign: "center" },
  introBody: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    lineHeight: 22,
    color: colors.textSecondary,
    textAlign: "center",
    marginTop: spacing.sm,
  },

  sectionCard: {
    marginBottom: spacing.lg,
    padding: spacing.lg,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderTopWidth: 3,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  sectionHeadRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.sm },
  sectionBadge: {
    minWidth: 30,
    height: 30,
    paddingHorizontal: 6,
    borderRadius: 15,
    borderWidth: 1.5,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.background,
  },
  sectionBadgeText: { fontFamily: fonts.uiSemi, fontSize: 11 },
  sectionTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary, lineHeight: 22 },
  sectionLatinTitle: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12, marginTop: 2 },

  rubricBox: {
    flexDirection: "row",
    gap: 6,
    alignItems: "flex-start",
    paddingLeft: spacing.sm,
    paddingVertical: 6,
    borderLeftWidth: 2,
    backgroundColor: colors.background,
    borderRadius: 4,
    marginBottom: spacing.md,
  },
  rubricText: { flex: 1, fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12, lineHeight: 18, color: colors.textMuted },

  twoCol: { flexDirection: "row" },
  col: { flex: 1 },
  stacked: {},
  colLabel: { fontFamily: fonts.uiSemi, fontSize: 10, letterSpacing: 1.6, marginBottom: 6 },
  latinText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 14, lineHeight: 22, color: colors.textPrimary, marginBottom: spacing.sm },
  englishText: { fontFamily: fonts.bodyRegular, fontSize: 14, lineHeight: 22, color: colors.textPrimary, marginBottom: spacing.sm },
  noteText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12, color: colors.textMuted, marginTop: spacing.sm, lineHeight: 18 },
});

/**
 * Sanctus Missal Reader — single missal, all sections in order.
 *
 * Renders the Order of Mass for a single missal. When a section has both
 * Latin and English, they render side-by-side (two flex columns). When
 * only one is present, it spans the full width.
 *
 * Free for all authenticated users.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  LayoutChangeEvent,
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
  getMissal,
  getMissalSection,
  MissalDetail,
  MissalSection,
} from "@/src/api";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type DisplayMode = "both" | "english" | "latin";

export default function MissalReaderScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const router = useRouter();
  const { width } = useWindowDimensions();

  const [detail, setDetail] = useState<MissalDetail | null>(null);
  const [sections, setSections] = useState<Record<number, MissalSection>>({});
  const [loadingDetail, setLoadingDetail] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<DisplayMode>("both");
  const [activeIdx, setActiveIdx] = useState<number>(0);

  const scrollRef = useRef<ScrollView | null>(null);
  const sectionOffsets = useRef<Record<number, number>>({});

  // Side-by-side only when there's room. Below ~520 px we stack vertically.
  const sideBySide = width >= 520;

  const accent = detail?.accent_color || colors.gold;

  const loadDetail = useCallback(async () => {
    if (!slug) return;
    setLoadingDetail(true);
    setError(null);
    try {
      const d = await getMissal(slug);
      setDetail(d);
      // Eagerly load all sections in parallel — total payload is ~50–80 KB,
      // which is fast and avoids per-section spinners while scrolling.
      const results = await Promise.all(
        (d.sections || []).map((s) => getMissalSection(slug, s.index)),
      );
      const map: Record<number, MissalSection> = {};
      for (const r of results) map[r.index] = r;
      setSections(map);
    } catch (e: any) {
      setError(e?.message || "Could not load this missal.");
    } finally {
      setLoadingDetail(false);
    }
  }, [slug]);

  useEffect(() => { void loadDetail(); }, [loadDetail]);

  const sectionList = useMemo(() => detail?.sections || [], [detail]);

  const onSectionLayout = (idx: number) => (e: LayoutChangeEvent) => {
    sectionOffsets.current[idx] = e.nativeEvent.layout.y;
  };

  const scrollToSection = (idx: number) => {
    const y = sectionOffsets.current[idx];
    if (y != null && scrollRef.current) {
      scrollRef.current.scrollTo({ y: Math.max(0, y - 8), animated: true });
      setActiveIdx(idx);
    }
  };

  // Update active section based on scroll position.
  const onScroll = (e: any) => {
    const y = e.nativeEvent.contentOffset.y;
    let active = 0;
    for (const [idxStr, offset] of Object.entries(sectionOffsets.current)) {
      if (offset - 80 <= y) active = Math.max(active, parseInt(idxStr, 10));
    }
    if (active !== activeIdx) setActiveIdx(active);
  };

  const renderParas = (text: string | null | undefined, baseStyle: any) => {
    if (!text) return null;
    return text.split(/\n{2,}/).map((p, i) => (
      <Text key={i} style={baseStyle}>
        {p.replace(/\n/g, "\n")}
      </Text>
    ));
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={`missal-reader-${slug}`}>
      <Stack.Screen options={{ headerShown: false }} />

      <View style={styles.header}>
        <Pressable testID="missal-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.headerTitle} numberOfLines={1}>
            {detail?.name || "Missal"}
          </Text>
          {detail ? (
            <Text style={styles.headerSub} numberOfLines={1}>{detail.subtitle}</Text>
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
              { key: "english", label: detail.vernacular_label, icon: "language" },
              { key: "latin", label: "Latin", icon: "book" },
            ] as { key: DisplayMode; label: string; icon: keyof typeof Ionicons.glyphMap }[]
          ).map((opt) => {
            const active = mode === opt.key;
            return (
              <Pressable
                key={opt.key}
                testID={`missal-mode-${opt.key}`}
                onPress={() => setMode(opt.key)}
                style={({ pressed }) => [
                  styles.modeChip,
                  active && { backgroundColor: accent, borderColor: accent },
                  pressed && { opacity: 0.85 },
                ]}
              >
                <Ionicons
                  name={opt.icon}
                  size={13}
                  color={active ? colors.gold : colors.textSecondary}
                />
                <Text style={[styles.modeChipText, active && { color: colors.gold }]}>
                  {opt.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      ) : null}

      {loadingDetail ? (
        <View style={styles.center}><ActivityIndicator color={accent} /></View>
      ) : error || !detail ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error || "Missal not found."}</Text>
          <Pressable onPress={loadDetail} style={({ pressed }) => [styles.retry, pressed && { opacity: 0.7 }]}>
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      ) : (
        <View style={{ flex: 1 }}>
          <ScrollView
            ref={scrollRef}
            contentContainerStyle={styles.scroll}
            onScroll={onScroll}
            scrollEventThrottle={64}
          >
            {/* Intro */}
            <View style={[styles.introCard, { borderColor: accent }]}>
              <Ornament />
              <Text style={[styles.introTradition, { color: accent }]}>
                {detail.tradition.toUpperCase()}
              </Text>
              <Text style={styles.introName}>{detail.name}</Text>
              <Text style={styles.introSubtitle}>{detail.subtitle}</Text>
              <Text style={styles.introBody}>{detail.intro}</Text>
            </View>

            {/* Sections */}
            {sectionList.map((meta) => {
              const sec = sections[meta.index];
              if (!sec) return null;
              const hasLatin = !!sec.latin;
              const renderBoth = mode === "both" && hasLatin;
              const showEnglish = mode !== "latin" || !hasLatin;
              const showLatin = mode !== "english" && hasLatin;

              return (
                <View
                  key={meta.index}
                  testID={`missal-section-${meta.index}`}
                  onLayout={onSectionLayout(meta.index)}
                  style={[styles.sectionCard, { borderTopColor: accent }]}
                >
                  <View style={styles.sectionHeadRow}>
                    <View style={[styles.sectionBadge, { borderColor: accent }]}>
                      <Text style={[styles.sectionBadgeText, { color: accent }]}>
                        {meta.index + 1}
                      </Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.sectionTitle}>{sec.title}</Text>
                      {sec.latin_title ? (
                        <Text style={[styles.sectionLatinTitle, { color: accent }]}>
                          {sec.latin_title}
                        </Text>
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
                        <Text style={[styles.colLabel, { color: accent }]}>{detail.vernacular_label.toUpperCase()}</Text>
                        {renderParas(sec.english, styles.englishText)}
                      </View>
                    </View>
                  ) : renderBoth ? (
                    // Stacked Latin + English for narrow screens.
                    <View style={styles.stacked}>
                      <View style={styles.stackedBlock}>
                        <Text style={[styles.colLabel, { color: accent }]}>LATIN</Text>
                        {renderParas(sec.latin, styles.latinText)}
                      </View>
                      <View style={[styles.stackedBlock, { borderTopColor: colors.borderSoft, borderTopWidth: StyleSheet.hairlineWidth, paddingTop: spacing.sm, marginTop: spacing.sm }]}>
                        <Text style={[styles.colLabel, { color: accent }]}>{detail.vernacular_label.toUpperCase()}</Text>
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
                            <Text style={[styles.colLabel, { color: accent }]}>{detail.vernacular_label.toUpperCase()}</Text>
                          ) : null}
                          {renderParas(sec.english, styles.englishText)}
                        </View>
                      ) : null}
                    </View>
                  )}

                  {sec.note ? (
                    <Text style={styles.noteText}>{sec.note}</Text>
                  ) : null}
                </View>
              );
            })}

            <View style={{ height: spacing.xxl * 2 }} />
          </ScrollView>

          {/* TOC strip — horizontally scrollable chips */}
          <View style={styles.tocStrip}>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.tocScroll}
            >
              {sectionList.map((meta) => {
                const active = meta.index === activeIdx;
                return (
                  <Pressable
                    key={meta.index}
                    testID={`missal-toc-${meta.index}`}
                    onPress={() => scrollToSection(meta.index)}
                    style={({ pressed }) => [
                      styles.tocChip,
                      active && { backgroundColor: accent, borderColor: accent },
                      pressed && { opacity: 0.85 },
                    ]}
                  >
                    <Text
                      style={[
                        styles.tocChipText,
                        active && { color: colors.gold },
                      ]}
                      numberOfLines={1}
                    >
                      {meta.index + 1}. {meta.title.split(" · ")[0]}
                    </Text>
                  </Pressable>
                );
              })}
            </ScrollView>
          </View>
        </View>
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
  modeChipText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 0.4,
    color: colors.textSecondary,
  },

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
  introTradition: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1.6,
    marginTop: spacing.sm,
  },
  introName: {
    fontFamily: fonts.headingBold,
    fontSize: 22,
    color: colors.textPrimary,
    textAlign: "center",
  },
  introSubtitle: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 13,
    color: colors.textSecondary,
    textAlign: "center",
  },
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
  sectionHeadRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
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
  sectionTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 16,
    color: colors.textPrimary,
    lineHeight: 22,
  },
  sectionLatinTitle: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 12,
    marginTop: 2,
  },

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
  rubricText: {
    flex: 1,
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 12,
    lineHeight: 18,
    color: colors.textMuted,
  },

  twoCol: {
    flexDirection: "row",
    gap: 0,
  },
  col: { flex: 1 },
  stacked: { gap: 0 },
  stackedBlock: {},
  colLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1.6,
    marginBottom: 6,
  },
  latinText: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 14,
    lineHeight: 22,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  englishText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    lineHeight: 22,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  noteText: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 12,
    color: colors.textMuted,
    marginTop: spacing.sm,
    lineHeight: 18,
  },

  tocStrip: {
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
    backgroundColor: colors.surface,
    paddingVertical: spacing.sm,
  },
  tocScroll: { paddingHorizontal: spacing.md, gap: 6 },
  tocChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.background,
    maxWidth: 240,
  },
  tocChipText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.textSecondary,
    letterSpacing: 0.3,
  },
});

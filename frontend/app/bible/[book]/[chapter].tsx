import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { api, BibleBook, BibleChapter, BibleColor } from "@/src/api";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import BookmarkButton from "@/src/components/BookmarkButton";
import { HIGHLIGHT_SWATCHES, highlightHex } from "@/src/bible-colors";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const SECTION_LABEL: Record<BibleBook["section"], string> = {
  ot: "Old Testament",
  deutero: "Deuterocanonical",
  nt: "New Testament",
};

export default function BibleReaderScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ book?: string; chapter?: string }>();
  const bookSlug = typeof params.book === "string" ? params.book : "";
  const chapter = Math.max(1, parseInt((typeof params.chapter === "string" ? params.chapter : "1"), 10) || 1);

  const [book, setBook] = useState<BibleBook | null>(null);
  const [data, setData] = useState<BibleChapter | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingVerse, setPendingVerse] = useState<number | null>(null);
  const [busyVerse, setBusyVerse] = useState<number | null>(null);
  const [translation, setTranslation] = useState<"douayrheims" | "vulgate">("douayrheims");

  const highlightMap = useMemo(() => {
    const m: Record<number, BibleColor> = {};
    for (const h of data?.highlights ?? []) m[h.verse] = h.color;
    return m;
  }, [data]);

  const load = useCallback(async () => {
    if (!bookSlug) return;
    setLoading(true);
    setError(null);
    try {
      // Books list is small; cache it once per session via a quick load.
      // (No HTTP cache layer yet — keep simple; cost is fine.)
      const [meta, ch] = await Promise.all([
        api<{ items: BibleBook[] }>("/bible/books"),
        api<BibleChapter>(`/bible/chapter/${bookSlug}/${chapter}?translation=${translation}`),
      ]);
      const b = meta.items.find((x) => x.slug === bookSlug) || null;
      setBook(b);
      setData(ch);
    } catch (e: any) {
      setError(e?.message || "Could not load the chapter.");
    } finally {
      setLoading(false);
    }
  }, [bookSlug, chapter, translation]);

  useEffect(() => {
    void load();
  }, [load]);

  const setHighlight = async (verseN: number, color: BibleColor | null) => {
    if (!book) return;
    setBusyVerse(verseN);
    try {
      if (color) {
        await api(`/bible/highlight`, {
          method: "POST",
          body: { book: book.slug, chapter, verse: verseN, color },
        });
      } else {
        await api(`/bible/highlight/${book.slug}/${chapter}/${verseN}`, { method: "DELETE" });
      }
      // Mutate local state for instant feedback.
      setData((d) => {
        if (!d) return d;
        const without = d.highlights.filter((h) => h.verse !== verseN);
        return { ...d, highlights: color ? [...without, { verse: verseN, color }] : without };
      });
    } catch (e) {
      console.warn("highlight set failed", e);
    } finally {
      setBusyVerse(null);
      setPendingVerse(null);
    }
  };

  const journalVerse = (verseN: number) => {
    if (!book || !data) return;
    const verse = data.verses.find((v) => v.n === verseN);
    if (!verse) return;
    const ref = `${book.name} ${chapter}:${verseN}`;
    setPendingVerse(null);
    router.push({
      pathname: "/journal",
      params: {
        mode: "free",
        verse_ref: ref,
        verse_text: verse.text,
      },
    });
  };

  const goToChapter = (nextCh: number) => {
    if (!book) return;
    if (nextCh < 1 || nextCh > book.chapters) return;
    router.replace({ pathname: "/bible/[book]/[chapter]", params: { book: book.slug, chapter: String(nextCh) } });
  };

  const renderHeader = () => (
    <View style={styles.header}>
      <Pressable testID="bible-reader-back" onPress={() => router.back()} hitSlop={12}>
        <Ionicons name="chevron-back" size={26} color={colors.primary} />
      </Pressable>
      <View style={styles.headerCenter}>
        <Text style={styles.headerTitle}>
          {book?.name ?? "Chapter"} {data?.chapter ?? chapter}
        </Text>
        {book ? (
          <View style={styles.headerSubRow}>
            <LiturgicalBadge color={colors.gold} label={SECTION_LABEL[book.section]} />
            {book.dr_name !== book.name ? (
              <Text style={styles.drName}>{book.dr_name}</Text>
            ) : null}
          </View>
        ) : null}
      </View>
      {book ? (
        <BookmarkButton
          input={{
            kind: "bible",
            ref_id: `${book.slug}:${data?.chapter ?? chapter}`,
            title: `${book.name} ${data?.chapter ?? chapter}`,
            subtitle: "Bible",
            route: "/bible/[book]/[chapter]",
            params: { book: book.slug, chapter: String(data?.chapter ?? chapter) },
          }}
        />
      ) : null}
      <Pressable
        testID="bible-reader-list"
        onPress={() => router.push("/bible")}
        hitSlop={12}
      >
        <Ionicons name="list-outline" size={22} color={colors.primary} />
      </Pressable>
    </View>
  );

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="bible-reader-screen">
      <Stack.Screen options={{ headerShown: false }} />
      {renderHeader()}

      <View style={styles.transRow}>
        {(["douayrheims", "vulgate"] as const).map((tr) => (
          <Pressable
            key={tr}
            testID={`bible-trans-${tr}`}
            onPress={() => setTranslation(tr)}
            style={[styles.transChip, translation === tr && styles.transChipActive]}
          >
            <Text style={[styles.transChipText, translation === tr && styles.transChipTextActive]}>
              {tr === "douayrheims" ? "Douay-Rheims" : "Latin · Vulgate"}
            </Text>
          </Pressable>
        ))}
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
        </View>
      ) : error ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable testID="bible-reader-retry" onPress={load} style={({ pressed }) => [styles.retry, pressed && styles.pressed]}>
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      ) : data ? (
        <ScrollView contentContainerStyle={styles.scroll}>
          <Text style={styles.chapterLabel}>Chapter {data.chapter}</Text>
          <View style={styles.divider} />
          <View style={styles.verseBlock}>
            {data.verses.map((v) => {
              const color = highlightMap[v.n];
              const bg = highlightHex(color);
              const isBusy = busyVerse === v.n;
              return (
                <Pressable
                  key={v.n}
                  testID={`bible-verse-${v.n}`}
                  onPress={() => setPendingVerse(v.n)}
                  style={({ pressed }) => [
                    styles.versePress,
                    bg ? { backgroundColor: bg } : null,
                    pressed && styles.pressed,
                  ]}
                >
                  <Text style={styles.verseText}>
                    <Text style={styles.verseNum}>{v.n}</Text>
                    <Text>  </Text>
                    {v.text}
                    {isBusy ? "  …" : ""}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          {/* Chapter pager */}
          <View style={styles.pager}>
            <Pressable
              testID="bible-prev-chapter"
              onPress={() => goToChapter(data.chapter - 1)}
              disabled={data.chapter <= 1}
              style={({ pressed }) => [styles.pageBtn, data.chapter <= 1 && styles.pageBtnDisabled, pressed && styles.pressed]}
            >
              <Ionicons name="chevron-back" size={16} color={colors.primary} />
              <Text style={styles.pageText}>Previous</Text>
            </Pressable>
            <Text style={styles.pagerCenter}>
              {data.chapter} / {book?.chapters ?? data.chapters_total}
            </Text>
            <Pressable
              testID="bible-next-chapter"
              onPress={() => goToChapter(data.chapter + 1)}
              disabled={!!book && data.chapter >= (book.chapters)}
              style={({ pressed }) => [
                styles.pageBtn,
                !!book && data.chapter >= book.chapters && styles.pageBtnDisabled,
                pressed && styles.pressed,
              ]}
            >
              <Text style={styles.pageText}>Next</Text>
              <Ionicons name="chevron-forward" size={16} color={colors.primary} />
            </Pressable>
          </View>
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      ) : null}

      {/* Verse action sheet */}
      <Modal
        transparent
        visible={pendingVerse !== null}
        animationType="fade"
        onRequestClose={() => setPendingVerse(null)}
      >
        <Pressable style={styles.modalScrim} onPress={() => setPendingVerse(null)} testID="bible-sheet-scrim">
          <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation?.()}>
            {pendingVerse !== null && data && book ? (
              <>
                <Text style={styles.sheetCitation}>
                  {book.name} {chapter}:{pendingVerse}
                </Text>
                <Text style={styles.sheetVerse} numberOfLines={4}>
                  {data.verses.find((v) => v.n === pendingVerse)?.text}
                </Text>

                <Text style={styles.sheetLabel}>Highlight</Text>
                <View style={styles.swatchRow}>
                  {HIGHLIGHT_SWATCHES.map((s) => {
                    const active = highlightMap[pendingVerse] === s.value;
                    return (
                      <Pressable
                        key={s.value}
                        testID={`bible-swatch-${s.value}`}
                        onPress={() => setHighlight(pendingVerse, s.value)}
                        style={[styles.swatch, { backgroundColor: s.hex, borderColor: active ? s.ring : "transparent" }]}
                        accessibilityLabel={`Highlight ${s.label}`}
                      >
                        {active ? <Ionicons name="checkmark" size={16} color={s.ring} /> : null}
                      </Pressable>
                    );
                  })}
                  {highlightMap[pendingVerse] ? (
                    <Pressable
                      testID="bible-swatch-clear"
                      onPress={() => setHighlight(pendingVerse, null)}
                      style={styles.swatchClear}
                      accessibilityLabel="Remove highlight"
                    >
                      <Ionicons name="trash-outline" size={16} color={colors.textSecondary} />
                    </Pressable>
                  ) : null}
                </View>

                <Pressable
                  testID="bible-sheet-journal"
                  onPress={() => journalVerse(pendingVerse)}
                  style={({ pressed }) => [styles.sheetCta, pressed && styles.pressed]}
                >
                  <Ionicons name="create-outline" size={16} color={colors.gold} />
                  <Text style={styles.sheetCtaText}>Journal this verse</Text>
                </Pressable>

                <Pressable
                  testID="bible-sheet-close"
                  onPress={() => setPendingVerse(null)}
                  style={({ pressed }) => [styles.sheetCancel, pressed && styles.pressed]}
                >
                  <Text style={styles.sheetCancelText}>Close</Text>
                </Pressable>
              </>
            ) : null}
          </Pressable>
        </Pressable>
      </Modal>
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
  headerCenter: { flex: 1, alignItems: "center" },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 18, color: colors.textPrimary },
  headerSubRow: { flexDirection: "row", gap: spacing.sm, alignItems: "center", marginTop: 2 },
  drName: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, fontSize: 11 },
  transRow: { flexDirection: "row", gap: 8, paddingHorizontal: spacing.lg, paddingTop: spacing.sm },
  transChip: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surface },
  transChipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  transChipText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary },
  transChipTextActive: { color: colors.gold },
  scroll: { padding: spacing.lg, paddingTop: spacing.md },
  chapterLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 2.5,
    color: colors.gold,
    textAlign: "center",
    textTransform: "uppercase",
  },
  divider: {
    alignSelf: "center",
    width: 50,
    height: 1,
    backgroundColor: colors.gold,
    opacity: 0.5,
    marginTop: spacing.xs,
    marginBottom: spacing.md,
  },
  verseBlock: { gap: 2 },
  versePress: {
    paddingVertical: 6,
    paddingHorizontal: 8,
    borderRadius: radius.sm,
  },
  verseText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 17,
    lineHeight: 28,
    color: colors.textPrimary,
  },
  verseNum: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.gold,
  },
  pager: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: spacing.xl,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
  },
  pageBtn: { flexDirection: "row", alignItems: "center", gap: 4, padding: 8 },
  pageBtnDisabled: { opacity: 0.3 },
  pageText: { fontFamily: fonts.uiSemi, color: colors.primary, fontSize: 13 },
  pagerCenter: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textMuted },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.lg },
  errorText: { fontFamily: fonts.bodyRegular, color: colors.liturgical.red, fontSize: 14, textAlign: "center", marginBottom: spacing.md },
  retry: { paddingHorizontal: spacing.lg, paddingVertical: 10, borderRadius: radius.round, backgroundColor: colors.primary },
  retryText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 13 },
  modalScrim: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.45)",
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: colors.background,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xl,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    ...shadow.card,
  },
  sheetCitation: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 1.5, color: colors.gold, textTransform: "uppercase" },
  sheetVerse: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 15,
    lineHeight: 22,
    color: colors.textPrimary,
    marginTop: 6,
    marginBottom: spacing.md,
  },
  sheetLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.5,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  swatchRow: { flexDirection: "row", gap: 12, alignItems: "center", marginBottom: spacing.lg },
  swatch: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 3,
    alignItems: "center",
    justifyContent: "center",
  },
  swatchClear: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.borderSoft,
    alignItems: "center",
    justifyContent: "center",
    marginLeft: 4,
  },
  sheetCta: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    paddingVertical: 14,
    borderRadius: radius.md,
    backgroundColor: colors.primary,
  },
  sheetCtaText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 14 },
  sheetCancel: { alignItems: "center", paddingVertical: 12, marginTop: 6 },
  sheetCancelText: { fontFamily: fonts.uiSemi, color: colors.textSecondary, fontSize: 14 },
  pressed: { opacity: 0.7 },
});

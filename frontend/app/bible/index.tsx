import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
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

import { api, BibleBook } from "@/src/api";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const SECTION_TITLES: Record<BibleBook["section"], string> = {
  ot: "Old Testament",
  deutero: "Deuterocanonical",
  nt: "New Testament",
};
const SECTION_ORDER: BibleBook["section"][] = ["ot", "deutero", "nt"];

export default function BibleIndexScreen() {
  const router = useRouter();
  const [books, setBooks] = useState<BibleBook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [openBook, setOpenBook] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const r = await api<{ items: BibleBook[] }>("/bible/books");
      setBooks(r.items || []);
    } catch (e: any) {
      setError(e?.message || "Could not load the Bible. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return books;
    return books.filter(
      (b) =>
        b.name.toLowerCase().includes(q) ||
        b.abbr.toLowerCase().includes(q) ||
        b.dr_name.toLowerCase().includes(q),
    );
  }, [books, query]);

  const grouped = useMemo(() => {
    const map: Record<BibleBook["section"], BibleBook[]> = { ot: [], deutero: [], nt: [] };
    for (const b of filtered) map[b.section].push(b);
    for (const k of Object.keys(map) as BibleBook["section"][]) {
      map[k].sort((a, z) => a.order - z.order);
    }
    return map;
  }, [filtered]);

  const openChapter = (slug: string, chapter: number) => {
    setOpenBook(null);
    router.push({ pathname: "/bible/[book]/[chapter]", params: { book: slug, chapter: String(chapter) } });
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="bible-index-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="bible-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.headerTitle}>Holy Bible</Text>
          <Text style={styles.headerSub}>Douay-Rheims · Challoner</Text>
        </View>
        <View style={{ width: 26 }} />
      </View>

      <View style={styles.searchRow}>
        <Ionicons name="search" size={16} color={colors.textMuted} />
        <TextInput
          testID="bible-search-input"
          value={query}
          onChangeText={setQuery}
          placeholder="Search book…"
          placeholderTextColor={colors.textMuted}
          style={styles.searchInput}
          autoCorrect={false}
          autoCapitalize="words"
          returnKeyType="search"
        />
        {query ? (
          <Pressable onPress={() => setQuery("")} hitSlop={10} testID="bible-search-clear">
            <Ionicons name="close-circle" size={16} color={colors.textMuted} />
          </Pressable>
        ) : null}
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
        </View>
      ) : error ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable testID="bible-retry" onPress={load} style={({ pressed }) => [styles.retry, pressed && styles.pressed]}>
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          {SECTION_ORDER.map((sec) => {
            const list = grouped[sec];
            if (!list.length) return null;
            return (
              <View key={sec} style={styles.sectionBlock}>
                <View style={styles.sectionHead}>
                  <Ornament />
                  <Text style={styles.sectionTitle}>{SECTION_TITLES[sec]}</Text>
                  <Ornament />
                </View>
                <View style={styles.booksGrid}>
                  {list.map((b) => (
                    <Pressable
                      key={b.slug}
                      testID={`bible-book-${b.slug}`}
                      onPress={() => setOpenBook((cur) => (cur === b.slug ? null : b.slug))}
                      style={({ pressed }) => [styles.bookTile, pressed && styles.pressed, openBook === b.slug && styles.bookTileActive]}
                    >
                      <Text style={[styles.bookName, openBook === b.slug && styles.bookNameActive]}>{b.name}</Text>
                      {b.name !== b.dr_name ? (
                        <Text style={[styles.bookDr, openBook === b.slug && styles.bookDrActive]} numberOfLines={1}>
                          {b.dr_name}
                        </Text>
                      ) : null}
                      <Text style={[styles.bookCh, openBook === b.slug && styles.bookChActive]}>{b.chapters} ch</Text>
                    </Pressable>
                  ))}
                </View>
                {openBook && grouped[sec].some((b) => b.slug === openBook) ? (
                  <View style={styles.chapterGrid} testID={`bible-chapter-grid-${openBook}`}>
                    {Array.from(
                      { length: grouped[sec].find((b) => b.slug === openBook)!.chapters },
                      (_, i) => i + 1,
                    ).map((c) => (
                      <Pressable
                        key={c}
                        testID={`bible-chapter-${openBook}-${c}`}
                        onPress={() => openChapter(openBook, c)}
                        style={({ pressed }) => [styles.chapTile, pressed && styles.pressed]}
                      >
                        <Text style={styles.chapText}>{c}</Text>
                      </Pressable>
                    ))}
                  </View>
                ) : null}
              </View>
            );
          })}
          {filtered.length === 0 ? (
            <View style={styles.center}>
              <Text style={styles.emptyText}>No books match “{query}”.</Text>
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
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
    gap: spacing.md,
  },
  headerTitleWrap: { flex: 1, alignItems: "center" },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.textPrimary },
  headerSub: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, fontSize: 11, marginTop: 1 },
  searchRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginHorizontal: spacing.lg,
    marginTop: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    backgroundColor: colors.surface,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  searchInput: {
    flex: 1,
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textPrimary,
    paddingVertical: 0,
  },
  scroll: { padding: spacing.lg },
  center: { alignItems: "center", justifyContent: "center", paddingVertical: spacing.xxl },
  emptyText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, fontSize: 14 },
  errorText: { fontFamily: fonts.bodyRegular, color: colors.liturgical.red, fontSize: 14, textAlign: "center", marginBottom: spacing.md, paddingHorizontal: spacing.lg },
  retry: { paddingHorizontal: spacing.lg, paddingVertical: 10, borderRadius: radius.round, backgroundColor: colors.primary },
  retryText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 13 },
  sectionBlock: { marginBottom: spacing.lg },
  sectionHead: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  sectionTitle: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    letterSpacing: 2,
    color: colors.gold,
    textTransform: "uppercase",
  },
  booksGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  bookTile: {
    width: "31.5%",
    minHeight: 78,
    paddingHorizontal: 10,
    paddingVertical: 10,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    justifyContent: "space-between",
    ...shadow.card,
  },
  bookTileActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  bookName: { fontFamily: fonts.headingSemi, fontSize: 14, color: colors.textPrimary, lineHeight: 18 },
  bookNameActive: { color: colors.gold },
  bookDr: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 10, color: colors.textMuted, marginTop: 2 },
  bookDrActive: { color: "#E8DCB5" },
  bookCh: { fontFamily: fonts.uiMedium, fontSize: 10, color: colors.textMuted, marginTop: 4, letterSpacing: 0.4 },
  bookChActive: { color: "#E8DCB5" },
  chapterGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginTop: spacing.md,
    padding: spacing.md,
    backgroundColor: colors.borderSoft,
    borderRadius: radius.md,
  },
  chapTile: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  chapText: { fontFamily: fonts.uiSemi, color: colors.textPrimary, fontSize: 14 },
  pressed: { opacity: 0.7 },
});

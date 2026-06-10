import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { LibraryBook, listLibraryBooks } from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type Tab = "books" | "radio" | "films";

const TRADITION_LABEL: Record<string, string> = {
  "catholic-classic": "Classic",
  doctor: "Doctor of the Church",
  mystic: "Mystic",
  apologist: "Apologist",
};

export default function LibraryIndexScreen() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("books");
  const [books, setBooks] = useState<LibraryBook[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await listLibraryBooks();
      setBooks(r.items || []);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const grouped = useMemo(() => {
    const inProgress = books.filter((b) => b.progress && (b.progress.chapter_index > 0 || b.progress.scroll_pct > 0.01));
    const embedded = books.filter((b) => b.type === "embedded" && !inProgress.includes(b));
    const external = books.filter((b) => b.type === "external");
    return { inProgress, embedded, external };
  }, [books]);

  const renderCard = (b: LibraryBook) => {
    const accent = b.cover_color || colors.gold;
    const progress = b.progress;
    const hasProgress = !!progress && (progress.chapter_index > 0 || progress.scroll_pct > 0.01);
    const pct = hasProgress
      ? Math.min(1, (progress!.chapter_index + progress!.scroll_pct) / Math.max(1, b.chapter_count))
      : 0;
    return (
      <Pressable
        key={b.book_id}
        testID={`library-book-card-${b.slug}`}
        onPress={() => router.push(`/library/books/${b.slug}`)}
        style={({ pressed }) => [styles.bookCard, pressed && { opacity: 0.85 }]}
      >
        <View style={[styles.cover, { backgroundColor: accent }]}>
          <Ionicons
            name={(b.cover_icon as any) || "book-outline"}
            size={28}
            color={colors.gold}
          />
          {b.type === "external" ? (
            <View style={styles.externalBadge}>
              <Ionicons name="open-outline" size={10} color={colors.surface} />
            </View>
          ) : null}
        </View>
        <View style={styles.bookMeta}>
          <Text style={styles.bookTitle} numberOfLines={2}>{b.title}</Text>
          <Text style={styles.bookAuthor} numberOfLines={1}>
            {b.author}{b.year ? ` · ${b.year}` : ""}
          </Text>
          {b.tradition && TRADITION_LABEL[b.tradition] ? (
            <Text style={[styles.bookTrad, { color: accent }]} numberOfLines={1}>
              {TRADITION_LABEL[b.tradition]}
            </Text>
          ) : null}
          {hasProgress ? (
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${Math.max(6, pct * 100)}%`, backgroundColor: accent }]} />
            </View>
          ) : null}
        </View>
      </Pressable>
    );
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable hitSlop={12} onPress={() => router.back()} testID="library-back">
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
        </Pressable>
        <Text style={styles.headerTitle}>Sanctus Library</Text>
        <View style={{ width: 22 }} />
      </View>

      <View style={styles.segmentRow}>
        {(["books", "radio", "films"] as Tab[]).map((t) => (
          <Pressable
            key={t}
            testID={`library-tab-${t}`}
            onPress={() => setTab(t)}
            style={[styles.segment, tab === t && styles.segmentActive]}
          >
            <Ionicons
              name={t === "books" ? "book-outline" : t === "radio" ? "radio-outline" : "film-outline"}
              size={14}
              color={tab === t ? colors.surface : colors.textSecondary}
            />
            <Text style={[styles.segmentText, tab === t && { color: colors.surface }]}>
              {t === "books" ? "Books" : t === "radio" ? "Radio" : "Films"}
            </Text>
          </Pressable>
        ))}
      </View>

      {tab === "books" ? (
        loading ? (
          <View style={styles.centerFill}>
            <ActivityIndicator color={colors.gold} />
          </View>
        ) : (
          <ScrollView
            contentContainerStyle={styles.scrollBody}
            refreshControl={
              <RefreshControl
                tintColor={colors.gold}
                refreshing={refreshing}
                onRefresh={() => { setRefreshing(true); void load(); }}
              />
            }
          >
            {grouped.inProgress.length > 0 ? (
              <>
                <Text style={styles.section}>Continue Reading</Text>
                {grouped.inProgress.map(renderCard)}
              </>
            ) : null}

            <Text style={styles.section}>In-App Reader</Text>
            <Text style={styles.sectionHint}>
              Public-domain classics with full text inside Sanctus.
            </Text>
            {grouped.embedded.map(renderCard)}

            <Text style={styles.section}>External Library</Text>
            <Text style={styles.sectionHint}>
              Opens the work in a clean in-app browser.
            </Text>
            {grouped.external.map(renderCard)}

            <View style={{ height: spacing.xxl }} />
          </ScrollView>
        )
      ) : (
        <View style={styles.placeholder} testID={`library-${tab}-placeholder`}>
          <Ionicons
            name={tab === "radio" ? "radio-outline" : "film-outline"}
            size={48}
            color={colors.gold}
          />
          <Text style={styles.placeholderTitle}>
            {tab === "radio" ? "Catholic Radio" : "Catholic Films"}
          </Text>
          <Text style={styles.placeholderText}>
            {tab === "radio"
              ? "Live Catholic stations are arriving in the next Sanctus update — EWTN Radio, Relevant Radio, Ave Maria, and more, with background playback."
              : "Curated Catholic films & animated series from YouTube are on the way — Lives of the Saints, doctrine, and animated stories for children."}
          </Text>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: spacing.lg, paddingVertical: spacing.md,
  },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.textPrimary },
  segmentRow: {
    flexDirection: "row", gap: spacing.sm, paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
  },
  segment: {
    flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 6, paddingVertical: 8, borderRadius: radius.round,
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft,
  },
  segmentActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  segmentText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary, letterSpacing: 0.3 },
  scrollBody: { paddingHorizontal: spacing.lg, paddingBottom: spacing.xl },
  centerFill: { flex: 1, alignItems: "center", justifyContent: "center" },
  section: {
    fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary,
    marginTop: spacing.lg, marginBottom: spacing.xs, letterSpacing: 0.2,
  },
  sectionHint: {
    fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textMuted, marginBottom: spacing.md,
  },
  bookCard: {
    flexDirection: "row", gap: spacing.md, padding: spacing.md,
    backgroundColor: colors.surface, borderRadius: radius.lg, marginBottom: spacing.sm,
    borderWidth: 1, borderColor: colors.borderSoft, ...shadow.card,
  },
  cover: {
    width: 64, height: 88, borderRadius: radius.md,
    alignItems: "center", justifyContent: "center", position: "relative",
  },
  externalBadge: {
    position: "absolute", top: 4, right: 4,
    backgroundColor: "rgba(0,0,0,0.35)", borderRadius: radius.round, padding: 3,
  },
  bookMeta: { flex: 1, justifyContent: "center" },
  bookTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary, lineHeight: 20 },
  bookAuthor: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textSecondary, marginTop: 4 },
  bookTrad: { fontFamily: fonts.uiSemi, fontSize: 10, letterSpacing: 1.4, marginTop: 6, textTransform: "uppercase" },
  progressTrack: {
    marginTop: spacing.sm, height: 4, backgroundColor: colors.borderSoft, borderRadius: 2, overflow: "hidden",
  },
  progressFill: { height: 4, borderRadius: 2 },
  placeholder: {
    flex: 1, alignItems: "center", justifyContent: "center",
    paddingHorizontal: spacing.xl, gap: spacing.md,
  },
  placeholderTitle: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.textPrimary },
  placeholderText: {
    fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary,
    textAlign: "center", lineHeight: 20,
  },
});

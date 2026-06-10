import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import * as WebBrowser from "expo-web-browser";

import { getLibraryBook, LibraryBook } from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const TRADITION_LABEL: Record<string, string> = {
  "catholic-classic": "Classic",
  doctor: "Doctor of the Church",
  mystic: "Mystic",
  apologist: "Apologist",
};

export default function BookDetailScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const router = useRouter();
  const [book, setBook] = useState<LibraryBook | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!slug) return;
    try {
      const b = await getLibraryBook(slug);
      setBook(b);
    } catch (e: any) {
      Alert.alert("Couldn't load", e?.message || "Try again.");
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => { void load(); }, [load]);

  if (loading || !book) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.centerFill}>
          <ActivityIndicator color={colors.gold} />
        </View>
      </SafeAreaView>
    );
  }

  const accent = book.cover_color || colors.gold;
  const isExternal = book.type === "external";
  const progress = book.progress;
  const resumeIndex = progress?.chapter_index ?? 0;
  const hasResume = !!progress && (progress.chapter_index > 0 || progress.scroll_pct > 0.01);

  const startReading = (chapterIndex: number) => {
    router.push(`/library/books/${slug}/read?chapter=${chapterIndex}`);
  };

  const openExternal = async () => {
    if (!book.source_url) return;
    try {
      await WebBrowser.openBrowserAsync(book.source_url, {
        toolbarColor: accent,
        controlsColor: colors.gold,
        dismissButtonStyle: "close",
      });
    } catch {
      Alert.alert("Couldn't open", "Please try again.");
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable hitSlop={12} onPress={() => router.back()} testID="book-back">
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
        </Pressable>
        <Text style={styles.headerTitle} numberOfLines={1}>{book.title}</Text>
        <View style={{ width: 22 }} />
      </View>

      <ScrollView contentContainerStyle={styles.body}>
        <View style={[styles.hero, { borderColor: accent }]}>
          <View style={[styles.coverLg, { backgroundColor: accent }]}>
            <Ionicons
              name={(book.cover_icon as any) || "book-outline"}
              size={48}
              color={colors.gold}
            />
          </View>
          <Text style={styles.heroTitle}>{book.title}</Text>
          <Text style={styles.heroAuthor}>
            {book.author}{book.year ? ` · ${book.year}` : ""}
          </Text>
          {book.tradition && TRADITION_LABEL[book.tradition] ? (
            <Text style={[styles.heroTrad, { color: accent }]}>{TRADITION_LABEL[book.tradition]}</Text>
          ) : null}
        </View>

        {book.blurb ? <Text style={styles.blurb}>{book.blurb}</Text> : null}

        {isExternal ? (
          <Pressable
            testID="book-open-external"
            onPress={openExternal}
            style={({ pressed }) => [
              styles.primaryBtn,
              { backgroundColor: accent, opacity: pressed ? 0.85 : 1 },
            ]}
          >
            <Ionicons name="open-outline" size={16} color={colors.gold} />
            <Text style={styles.primaryBtnText}>Open full work</Text>
          </Pressable>
        ) : (
          <>
            {hasResume ? (
              <Pressable
                testID="book-resume"
                onPress={() => startReading(resumeIndex)}
                style={({ pressed }) => [
                  styles.primaryBtn,
                  { backgroundColor: accent, opacity: pressed ? 0.85 : 1 },
                ]}
              >
                <Ionicons name="play" size={14} color={colors.gold} />
                <Text style={styles.primaryBtnText}>Resume Chapter {resumeIndex + 1}</Text>
              </Pressable>
            ) : (
              <Pressable
                testID="book-start"
                onPress={() => startReading(0)}
                style={({ pressed }) => [
                  styles.primaryBtn,
                  { backgroundColor: accent, opacity: pressed ? 0.85 : 1 },
                ]}
              >
                <Ionicons name="book" size={14} color={colors.gold} />
                <Text style={styles.primaryBtnText}>Start Reading</Text>
              </Pressable>
            )}

            <Text style={styles.section}>Chapters</Text>
            {book.chapters.map((c) => (
              <Pressable
                key={c.index}
                testID={`book-chapter-${c.index}`}
                onPress={() => startReading(c.index)}
                style={({ pressed }) => [styles.chapterRow, pressed && { opacity: 0.85 }]}
              >
                <View style={[styles.chapterNum, { backgroundColor: accent }]}>
                  <Text style={styles.chapterNumText}>{c.index + 1}</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.chapterTitle} numberOfLines={2}>{c.title}</Text>
                  <Text style={styles.chapterMeta}>{c.word_count} words</Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
              </Pressable>
            ))}

            {book.source_url ? (
              <Pressable
                testID="book-continue-source"
                onPress={openExternal}
                style={({ pressed }) => [styles.linkBtn, pressed && { opacity: 0.7 }]}
              >
                <Ionicons name="open-outline" size={14} color={accent} />
                <Text style={[styles.linkBtnText, { color: accent }]}>Continue full work at source →</Text>
              </Pressable>
            ) : null}
          </>
        )}

        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: spacing.lg, paddingVertical: spacing.md,
  },
  headerTitle: {
    flex: 1, marginHorizontal: spacing.md, textAlign: "center",
    fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary,
  },
  centerFill: { flex: 1, alignItems: "center", justifyContent: "center" },
  body: { paddingHorizontal: spacing.lg, paddingBottom: spacing.xl },
  hero: {
    alignItems: "center", padding: spacing.lg, borderRadius: radius.lg,
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft,
    ...shadow.card,
  },
  coverLg: {
    width: 110, height: 150, borderRadius: radius.md,
    alignItems: "center", justifyContent: "center", marginBottom: spacing.md,
  },
  heroTitle: {
    fontFamily: fonts.headingBold, fontSize: 22, color: colors.textPrimary,
    textAlign: "center", lineHeight: 26,
  },
  heroAuthor: {
    fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13,
    color: colors.textSecondary, marginTop: 4,
  },
  heroTrad: {
    fontFamily: fonts.uiSemi, fontSize: 10, letterSpacing: 1.4, marginTop: 8, textTransform: "uppercase",
  },
  blurb: {
    fontFamily: fonts.bodyRegular, fontSize: 14, lineHeight: 22,
    color: colors.textSecondary, marginTop: spacing.lg,
  },
  primaryBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 8, paddingVertical: 14, borderRadius: radius.round, marginTop: spacing.lg,
  },
  primaryBtnText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.gold, letterSpacing: 0.6 },
  section: {
    fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary,
    marginTop: spacing.xl, marginBottom: spacing.sm,
  },
  chapterRow: {
    flexDirection: "row", alignItems: "center", gap: spacing.md,
    padding: spacing.md, marginBottom: spacing.xs,
    backgroundColor: colors.surface, borderRadius: radius.md,
    borderWidth: 1, borderColor: colors.borderSoft,
  },
  chapterNum: {
    width: 28, height: 28, borderRadius: 14,
    alignItems: "center", justifyContent: "center",
  },
  chapterNumText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold },
  chapterTitle: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.textPrimary, lineHeight: 18 },
  chapterMeta: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  linkBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6,
    paddingVertical: spacing.md, marginTop: spacing.md,
  },
  linkBtnText: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 0.4 },
});

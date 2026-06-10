import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  NativeScrollEvent,
  NativeSyntheticEvent,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import AsyncStorage from "@react-native-async-storage/async-storage";

import {
  getLibraryChapter,
  LibraryChapterDetail,
  saveLibraryProgress,
} from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type FontSize = "sm" | "md" | "lg" | "xl";
type Mode = "light" | "sepia" | "dark";

const FONT_SCALE: Record<FontSize, number> = { sm: 14, md: 17, lg: 20, xl: 23 };
const LINE_SCALE: Record<FontSize, number> = { sm: 22, md: 27, lg: 32, xl: 37 };

const MODES: Record<
  Mode,
  { bg: string; surface: string; text: string; muted: string; border: string }
> = {
  light: {
    bg: colors.background, surface: colors.surface, text: colors.textPrimary,
    muted: colors.textMuted, border: colors.borderSoft,
  },
  sepia: {
    bg: "#F4ECD8", surface: "#F4ECD8", text: "#3E2C18",
    muted: "#7A6446", border: "#E1D3B0",
  },
  dark: {
    bg: "#0F172A", surface: "#0F172A", text: "#E5E7EB",
    muted: "#9CA3AF", border: "#1E293B",
  },
};

const FS_KEY = "sanctus.library.reader.font_size";
const MODE_KEY = "sanctus.library.reader.mode";

export default function ReaderScreen() {
  const params = useLocalSearchParams<{ slug: string; chapter?: string }>();
  const router = useRouter();
  const slug = params.slug as string;
  const initialChapter = Math.max(0, parseInt(params.chapter || "0", 10) || 0);

  const [chapter, setChapter] = useState<LibraryChapterDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [fontSize, setFontSize] = useState<FontSize>("md");
  const [mode, setMode] = useState<Mode>("light");
  const [showSettings, setShowSettings] = useState(false);
  const scrollRef = useRef<ScrollView>(null);
  const scrollPctRef = useRef(0);
  const lastSaveRef = useRef(0);
  const restoredRef = useRef(false);

  // Load saved preferences once.
  useEffect(() => {
    (async () => {
      try {
        const [fs, md] = await Promise.all([
          AsyncStorage.getItem(FS_KEY),
          AsyncStorage.getItem(MODE_KEY),
        ]);
        if (fs && ["sm", "md", "lg", "xl"].includes(fs)) setFontSize(fs as FontSize);
        if (md && ["light", "sepia", "dark"].includes(md)) setMode(md as Mode);
      } catch {
        /* ignore */
      }
    })();
  }, []);

  const persistPrefs = useCallback(async (fs: FontSize, m: Mode) => {
    try {
      await AsyncStorage.setItem(FS_KEY, fs);
      await AsyncStorage.setItem(MODE_KEY, m);
    } catch {
      /* ignore */
    }
  }, []);

  const loadChapter = useCallback(async (idx: number) => {
    if (!slug) return;
    setLoading(true);
    restoredRef.current = false;
    try {
      const c = await getLibraryChapter(slug, idx);
      setChapter(c);
      scrollPctRef.current = 0;
      // Persist that we're now on this chapter (resume point).
      void saveLibraryProgress(slug, idx, 0);
      // Scroll back to top after the new chapter renders.
      requestAnimationFrame(() => scrollRef.current?.scrollTo({ y: 0, animated: false }));
    } catch (e: any) {
      Alert.alert("Couldn't load chapter", e?.message || "Try again.");
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => { void loadChapter(initialChapter); }, [loadChapter, initialChapter]);

  // Throttled save of scroll progress.
  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const { contentOffset, contentSize, layoutMeasurement } = e.nativeEvent;
    const max = Math.max(1, contentSize.height - layoutMeasurement.height);
    const pct = Math.max(0, Math.min(1, contentOffset.y / max));
    scrollPctRef.current = pct;
    const now = Date.now();
    if (chapter && now - lastSaveRef.current > 3500) {
      lastSaveRef.current = now;
      void saveLibraryProgress(slug, chapter.chapter_index, pct);
    }
  };

  // Final save on unmount.
  useEffect(() => {
    return () => {
      if (chapter) {
        void saveLibraryProgress(slug, chapter.chapter_index, scrollPctRef.current);
      }
    };
  }, [slug, chapter]);

  const theme = MODES[mode];
  const fz = FONT_SCALE[fontSize];
  const lh = LINE_SCALE[fontSize];

  const goPrev = () => {
    if (!chapter || chapter.chapter_index <= 0) return;
    void loadChapter(chapter.chapter_index - 1);
  };
  const goNext = () => {
    if (!chapter || chapter.is_last) return;
    void loadChapter(chapter.chapter_index + 1);
  };

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: theme.bg }]} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={[styles.header, { borderBottomColor: theme.border }]}>
        <Pressable hitSlop={12} onPress={() => router.back()} testID="reader-back">
          <Ionicons name="chevron-back" size={22} color={theme.text} />
        </Pressable>
        <Text style={[styles.headerTitle, { color: theme.text }]} numberOfLines={1}>
          {chapter?.title || "Reading"}
        </Text>
        <Pressable
          hitSlop={12}
          onPress={() => setShowSettings(true)}
          testID="reader-settings"
        >
          <Ionicons name="text" size={20} color={theme.text} />
        </Pressable>
      </View>

      {loading || !chapter ? (
        <View style={styles.centerFill}>
          <ActivityIndicator color={colors.gold} />
        </View>
      ) : (
        <ScrollView
          ref={scrollRef}
          contentContainerStyle={styles.body}
          onScroll={onScroll}
          scrollEventThrottle={120}
          testID="reader-scroll"
        >
          <Text
            style={[styles.chapterTitle, { color: theme.text, fontSize: fz + 4, lineHeight: lh + 4 }]}
            testID="reader-chapter-title"
          >
            {chapter.title}
          </Text>
          <Text
            style={[styles.bodyText, { color: theme.text, fontSize: fz, lineHeight: lh }]}
            testID="reader-chapter-body"
          >
            {chapter.body_md}
          </Text>
          <View style={styles.navRow}>
            <Pressable
              testID="reader-prev"
              onPress={goPrev}
              disabled={chapter.chapter_index <= 0}
              style={[
                styles.navBtn,
                { borderColor: theme.border, opacity: chapter.chapter_index <= 0 ? 0.4 : 1 },
              ]}
            >
              <Ionicons name="chevron-back" size={14} color={theme.text} />
              <Text style={[styles.navText, { color: theme.text }]}>Previous</Text>
            </Pressable>
            <Pressable
              testID="reader-next"
              onPress={goNext}
              disabled={chapter.is_last}
              style={[
                styles.navBtn,
                {
                  backgroundColor: chapter.is_last ? "transparent" : colors.gold,
                  borderColor: chapter.is_last ? theme.border : colors.gold,
                  opacity: chapter.is_last ? 0.4 : 1,
                },
              ]}
            >
              <Text
                style={[
                  styles.navText,
                  { color: chapter.is_last ? theme.text : colors.primary },
                ]}
              >
                {chapter.is_last ? "End of work" : "Next chapter"}
              </Text>
              {!chapter.is_last ? (
                <Ionicons name="chevron-forward" size={14} color={colors.primary} />
              ) : null}
            </Pressable>
          </View>
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}

      <Modal
        visible={showSettings}
        transparent
        animationType="slide"
        onRequestClose={() => setShowSettings(false)}
      >
        <View style={styles.modalBackdrop}>
          <Pressable style={StyleSheet.absoluteFill} onPress={() => setShowSettings(false)} />
          <View style={[styles.modalSheet, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <View style={styles.modalHandle} />
            <Text style={[styles.modalLabel, { color: theme.text }]}>Font Size</Text>
            <View style={styles.fsRow}>
              {(["sm", "md", "lg", "xl"] as FontSize[]).map((s) => (
                <Pressable
                  key={s}
                  testID={`reader-fs-${s}`}
                  onPress={() => { setFontSize(s); void persistPrefs(s, mode); }}
                  style={[
                    styles.fsChip,
                    { borderColor: theme.border },
                    fontSize === s && { backgroundColor: colors.gold, borderColor: colors.gold },
                  ]}
                >
                  <Text
                    style={{
                      fontFamily: fonts.uiSemi,
                      color: fontSize === s ? colors.primary : theme.text,
                      fontSize: FONT_SCALE[s],
                    }}
                  >
                    Aa
                  </Text>
                </Pressable>
              ))}
            </View>
            <Text style={[styles.modalLabel, { color: theme.text }]}>Theme</Text>
            <View style={styles.modeRow}>
              {(["light", "sepia", "dark"] as Mode[]).map((m) => (
                <Pressable
                  key={m}
                  testID={`reader-mode-${m}`}
                  onPress={() => { setMode(m); void persistPrefs(fontSize, m); }}
                  style={[
                    styles.modeChip,
                    { backgroundColor: MODES[m].bg, borderColor: mode === m ? colors.gold : theme.border },
                  ]}
                >
                  <Text style={{ color: MODES[m].text, fontFamily: fonts.uiSemi, fontSize: 12 }}>
                    {m === "light" ? "Light" : m === "sepia" ? "Sepia" : "Dark"}
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: spacing.lg, paddingVertical: spacing.md,
    borderBottomWidth: 1,
  },
  headerTitle: {
    flex: 1, marginHorizontal: spacing.md, textAlign: "center",
    fontFamily: fonts.uiSemi, fontSize: 13,
  },
  centerFill: { flex: 1, alignItems: "center", justifyContent: "center" },
  body: { paddingHorizontal: spacing.lg, paddingVertical: spacing.lg },
  chapterTitle: { fontFamily: fonts.headingBold, marginBottom: spacing.lg },
  bodyText: { fontFamily: fonts.bodyRegular },
  navRow: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    gap: spacing.md, marginTop: spacing.xl,
  },
  navBtn: {
    flexDirection: "row", alignItems: "center", gap: 6,
    paddingVertical: 12, paddingHorizontal: 18, borderRadius: radius.round,
    borderWidth: 1,
  },
  navText: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 0.4 },
  modalBackdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.45)", justifyContent: "flex-end" },
  modalSheet: {
    borderTopLeftRadius: radius.lg, borderTopRightRadius: radius.lg,
    padding: spacing.lg, paddingBottom: spacing.xl, gap: spacing.md,
    borderWidth: 1, ...shadow.card,
  },
  modalHandle: {
    alignSelf: "center", width: 36, height: 4, borderRadius: 2,
    backgroundColor: colors.borderSoft, marginBottom: spacing.sm,
  },
  modalLabel: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 0.4 },
  fsRow: { flexDirection: "row", gap: spacing.sm },
  fsChip: {
    flex: 1, alignItems: "center", justifyContent: "center",
    paddingVertical: 12, borderRadius: radius.md, borderWidth: 1,
  },
  modeRow: { flexDirection: "row", gap: spacing.sm },
  modeChip: {
    flex: 1, alignItems: "center", justifyContent: "center",
    paddingVertical: 14, borderRadius: radius.md, borderWidth: 2,
  },
});

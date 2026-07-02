import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { AutoText as Text } from "@/src/auto-text";

import {
  LibraryBook,
  LibraryFilm,
  LibraryFilmCategory,
  LibraryStation,
  listLibraryBooks,
  listLibraryFilms,
  listLibraryStations,
} from "@/src/api";
import { useRadioPlayer } from "@/src/audio/RadioPlayerContext";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type Tab = "books" | "radio" | "films";

const TRADITION_LABEL: Record<string, string> = {
  "catholic-classic": "Classic",
  doctor: "Doctor of the Church",
  mystic: "Mystic",
  apologist: "Apologist",
  children: "For Children",
  reference: "Reference",
};

const FILM_CATEGORIES: { value: LibraryFilmCategory | "all"; label: string; icon: any }[] = [
  { value: "all", label: "All", icon: "apps-outline" },
  { value: "saints", label: "Saints", icon: "rose-outline" },
  { value: "doctrine", label: "Doctrine", icon: "book-outline" },
  { value: "animated", label: "For Kids", icon: "color-palette-outline" },
  { value: "documentary", label: "Documentary", icon: "videocam-outline" },
];

export default function LibraryIndexScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ tab?: string }>();
  const initialTab: Tab =
    params.tab === "radio" || params.tab === "films" ? params.tab : "books";

  const [tab, setTab] = useState<Tab>(initialTab);
  const [books, setBooks] = useState<LibraryBook[]>([]);
  const [stations, setStations] = useState<LibraryStation[]>([]);
  const [films, setFilms] = useState<LibraryFilm[]>([]);
  const [loading, setLoading] = useState<{ books: boolean; radio: boolean; films: boolean }>({
    books: true,
    radio: true,
    films: true,
  });
  const [refreshing, setRefreshing] = useState(false);
  const [filmCategory, setFilmCategory] = useState<LibraryFilmCategory | "all">("all");
  const [bookFilter, setBookFilter] = useState<"all" | "free">("all");

  const radio = useRadioPlayer();

  // Reactively switch when deep-linked with ?tab=
  useEffect(() => {
    if (params.tab === "radio" || params.tab === "films" || params.tab === "books") {
      setTab(params.tab as Tab);
    }
  }, [params.tab]);

  const loadBooks = useCallback(async () => {
    setLoading((l) => ({ ...l, books: true }));
    try {
      const r = await listLibraryBooks();
      setBooks(r.items || []);
    } catch (_e) {
      setBooks([]);
    } finally {
      setLoading((l) => ({ ...l, books: false }));
    }
  }, []);

  const loadStations = useCallback(async () => {
    setLoading((l) => ({ ...l, radio: true }));
    try {
      const r = await listLibraryStations();
      setStations(r.items || []);
    } catch (_e) {
      setStations([]);
    } finally {
      setLoading((l) => ({ ...l, radio: false }));
    }
  }, []);

  const loadFilms = useCallback(async () => {
    setLoading((l) => ({ ...l, films: true }));
    try {
      const r = await listLibraryFilms();
      setFilms(r.items || []);
    } catch (_e) {
      setFilms([]);
    } finally {
      setLoading((l) => ({ ...l, films: false }));
    }
  }, []);

  useEffect(() => {
    void loadBooks();
    void loadStations();
    void loadFilms();
  }, [loadBooks, loadStations, loadFilms]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    if (tab === "books") await loadBooks();
    else if (tab === "radio") await loadStations();
    else await loadFilms();
    setRefreshing(false);
  }, [tab, loadBooks, loadStations, loadFilms]);

  const grouped = useMemo(() => {
    const base = bookFilter === "free" ? books.filter((b) => !b.is_premium) : books;
    const inProgress = base.filter(
      (b) => b.progress && (b.progress.chapter_index > 0 || b.progress.scroll_pct > 0.01),
    );
    const isEncyclical = (b: LibraryBook) => (b.tradition || "").toLowerCase() === "papal";
    const isChildren = (b: LibraryBook) => (b.tradition || "").toLowerCase() === "children";
    const encyclicals = base.filter((b) => isEncyclical(b) && !inProgress.includes(b));
    const children = base.filter((b) => isChildren(b) && !inProgress.includes(b));
    const authored = base.filter((b) => !isEncyclical(b) && !isChildren(b) && !inProgress.includes(b));
    return { inProgress, encyclicals, children, authored };
  }, [books, bookFilter]);

  const filteredFilms = useMemo(() => {
    if (filmCategory === "all") return films;
    return films.filter((f) => f.category === filmCategory);
  }, [films, filmCategory]);

  const { user } = useAuth();
  /* ------------------------- BOOK CARD --------------------------------- */
  const renderBookCard = (b: LibraryBook) => {
    const accent = b.cover_color || colors.gold;
    const progress = b.progress;
    const hasProgress = !!progress && (progress.chapter_index > 0 || progress.scroll_pct > 0.01);
    const pct = hasProgress
      ? Math.min(1, (progress!.chapter_index + progress!.scroll_pct) / Math.max(1, b.chapter_count))
      : 0;
    const isLocked = !!b.is_premium && !user?.is_premium;
    return (
      <Pressable
        key={b.book_id}
        testID={`library-book-card-${b.slug}`}
        onPress={() => router.push(`/library/books/${b.slug}`)}
        style={({ pressed }) => [styles.bookCard, pressed && { opacity: 0.85 }]}
      >
        <View style={[styles.cover, { backgroundColor: accent }]}>
          <Ionicons name={(b.cover_icon as any) || "book-outline"} size={28} color={colors.gold} />
          {b.type === "external" ? (
            <View style={styles.externalBadge}>
              <Ionicons name="open-outline" size={10} color={colors.surface} />
            </View>
          ) : null}
          {isLocked ? (
            <View style={styles.lockBadge}>
              <Ionicons name="lock-closed" size={10} color={colors.primary} />
            </View>
          ) : null}
        </View>
        <View style={styles.bookMeta}>
          <Text style={styles.bookTitle} numberOfLines={2}>
            {b.title}
          </Text>
          <Text style={styles.bookAuthor} numberOfLines={1}>
            {b.author}
            {b.year ? ` · ${b.year}` : ""}
          </Text>
          {b.tradition && TRADITION_LABEL[b.tradition] ? (
            <Text style={[styles.bookTrad, { color: accent }]} numberOfLines={1}>
              {TRADITION_LABEL[b.tradition]}
            </Text>
          ) : null}
          {!b.is_premium ? (
            <View style={styles.freeTag} testID={`library-free-tag-${b.slug}`}>
              <Ionicons name="gift-outline" size={10} color={colors.liturgical.green} />
              <Text style={styles.freeTagText}>Free to read</Text>
            </View>
          ) : null}
          {hasProgress ? (
            <View style={styles.progressTrack}>
              <View
                style={[
                  styles.progressFill,
                  { width: `${Math.max(6, pct * 100)}%`, backgroundColor: accent },
                ]}
              />
            </View>
          ) : null}
        </View>
      </Pressable>
    );
  };

  /* ------------------------- STATION CARD ------------------------------ */
  const renderStationCard = (s: LibraryStation) => {
    const accent = s.accent_color || colors.gold;
    const isCurrent = radio.current?.station_id === s.station_id;
    const showPause = isCurrent && (radio.isPlaying || radio.isBuffering);

    return (
      <Pressable
        key={s.station_id}
        testID={`library-station-card-${s.slug}`}
        onPress={() => {
          if (isCurrent) {
            radio.toggle();
          } else {
            radio.play(s);
          }
        }}
        style={({ pressed }) => [
          styles.stationCard,
          pressed && { opacity: 0.92 },
          isCurrent && { borderColor: accent, borderWidth: 1.5 },
        ]}
      >
        <View style={[styles.stationIcon, { backgroundColor: accent }]}>
          <Ionicons name={(s.icon as any) || "radio-outline"} size={24} color={colors.gold} />
        </View>
        <View style={{ flex: 1, paddingHorizontal: spacing.md }}>
          <Text style={styles.stationName} numberOfLines={1}>
            {s.name}
          </Text>
          {s.blurb ? (
            <Text style={styles.stationBlurb} numberOfLines={2}>
              {s.blurb}
            </Text>
          ) : null}
          <View style={styles.stationMetaRow}>
            {s.country ? <Text style={styles.stationMetaTag}>{s.country}</Text> : null}
            {s.language ? (
              <Text style={[styles.stationMetaTag, { color: colors.textMuted }]}>{s.language}</Text>
            ) : null}
            {isCurrent ? (
              <View style={[styles.liveDot, { backgroundColor: accent }]} />
            ) : null}
            {isCurrent ? (
              <Text style={[styles.stationMetaTag, { color: accent, fontFamily: fonts.uiSemi }]}>
                {radio.isBuffering ? "BUFFERING" : radio.isPlaying ? "ON AIR" : "PAUSED"}
              </Text>
            ) : null}
          </View>
        </View>
        <View style={[styles.playBtn, { backgroundColor: accent }]}>
          {radio.isBuffering && isCurrent ? (
            <ActivityIndicator size="small" color={colors.gold} />
          ) : (
            <Ionicons
              name={showPause ? "pause" : "play"}
              size={20}
              color={colors.gold}
            />
          )}
        </View>
      </Pressable>
    );
  };

  /* ------------------------- FILM CARD --------------------------------- */
  const FilmThumb: React.FC<{ youtubeId: string }> = ({ youtubeId }) => {
    const [src, setSrc] = useState(`https://i.ytimg.com/vi/${youtubeId}/hqdefault.jpg`);
    return (
      <Image
        source={{ uri: src }}
        style={styles.filmThumb}
        resizeMode="cover"
        onError={() => {
          // YouTube hqdefault is missing for some videos — fall back to
          // the lower-res mqdefault, then to the catch-all 0.jpg.
          if (src.includes("hqdefault")) {
            setSrc(`https://i.ytimg.com/vi/${youtubeId}/mqdefault.jpg`);
          } else if (src.includes("mqdefault")) {
            setSrc(`https://i.ytimg.com/vi/${youtubeId}/0.jpg`);
          }
        }}
      />
    );
  };

  const renderFilmCard = (f: LibraryFilm) => {
    const accent = f.accent_color || colors.gold;
    return (
      <Pressable
        key={f.film_id}
        testID={`library-film-card-${f.slug}`}
        onPress={() => router.push(`/library/films/${f.slug}`)}
        style={({ pressed }) => [styles.filmCard, pressed && { opacity: 0.92 }]}
      >
        <View style={styles.filmThumbWrap}>
          <FilmThumb youtubeId={f.youtube_id} />
          <View style={[styles.filmCategoryPill, { backgroundColor: accent }]}>
            <Text style={styles.filmCategoryText}>{f.category.toUpperCase()}</Text>
          </View>
          <View style={styles.filmPlayOverlay}>
            <Ionicons name="play-circle" size={48} color={"rgba(255,255,255,0.92)"} />
          </View>
          {f.duration_label ? (
            <View style={styles.filmDuration}>
              <Text style={styles.filmDurationText}>{f.duration_label}</Text>
            </View>
          ) : null}
        </View>
        <View style={{ padding: spacing.md }}>
          <Text style={styles.filmTitle} numberOfLines={2}>
            {f.title}
          </Text>
          {f.blurb ? (
            <Text style={styles.filmBlurb} numberOfLines={2}>
              {f.blurb}
            </Text>
          ) : null}
        </View>
      </Pressable>
    );
  };

  /* ------------------------- RENDER ------------------------------------ */
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

      <ScrollView
        contentContainerStyle={styles.scrollBody}
        refreshControl={
          <RefreshControl
            tintColor={colors.gold}
            refreshing={refreshing}
            onRefresh={onRefresh}
          />
        }
      >
        {tab === "books" ? (
          loading.books ? (
            <View style={styles.centerPad}>
              <ActivityIndicator color={colors.gold} />
            </View>
          ) : (
            <>
              <View style={styles.bookFilterRow}>
                {(["all", "free"] as const).map((f) => {
                  const active = bookFilter === f;
                  return (
                    <Pressable
                      key={f}
                      testID={`library-book-filter-${f}`}
                      onPress={() => setBookFilter(f)}
                      style={[styles.bookFilterChip, active && styles.bookFilterChipActive]}
                    >
                      {f === "free" ? (
                        <Ionicons
                          name="gift-outline"
                          size={12}
                          color={active ? colors.surface : colors.liturgical.green}
                        />
                      ) : null}
                      <Text
                        style={[styles.bookFilterChipText, active && { color: colors.surface }]}
                      >
                        {f === "all" ? "All books" : "Free to read"}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
              {grouped.inProgress.length > 0 ? (
                <>
                  <Text style={styles.section}>Continue Reading</Text>
                  {grouped.inProgress.map(renderBookCard)}
                </>
              ) : null}
              <Text style={styles.section}>Books</Text>
              <Text style={styles.sectionHint}>
                Spiritual classics & guides — including a discernment library. Reading included with Sanctus Premium.
              </Text>
              {grouped.authored.map(renderBookCard)}

              {grouped.children.length > 0 ? (
                <>
                  <Text style={styles.section} testID="library-section-children">For Children</Text>
                  <Text style={styles.sectionHint}>
                    Full storybooks written for little ones — free to read together as a family.
                  </Text>
                  {grouped.children.map(renderBookCard)}
                </>
              ) : null}

              <Text style={styles.section}>Encyclicals</Text>
              <Text style={styles.sectionHint}>
                Papal letters & exhortations — always free. Several are practical guides to spiritual discernment.
              </Text>
              {grouped.encyclicals.map(renderBookCard)}
            </>
          )
        ) : null}

        {tab === "radio" ? (
          loading.radio ? (
            <View style={styles.centerPad}>
              <ActivityIndicator color={colors.gold} />
            </View>
          ) : (
            <>
              <Text style={styles.section}>Catholic Stations</Text>
              <Text style={styles.sectionHint}>
                Tap a station to start streaming. Use the mini-player to pause or close.
              </Text>
              {radio.error ? (
                <View style={styles.errorBox} testID="library-radio-warning">
                  <Ionicons name="information-circle-outline" size={16} color={colors.textSecondary} />
                  <Text style={styles.errorText}>{radio.error}</Text>
                </View>
              ) : null}
              {stations.map(renderStationCard)}
              <View style={styles.nativeNote}>
                <Ionicons name="phone-portrait-outline" size={14} color={colors.textMuted} />
                <Text style={styles.nativeNoteText}>
                  Background playback (locked screen) is enabled on the iOS/Android build.
                </Text>
              </View>
            </>
          )
        ) : null}

        {tab === "films" ? (
          loading.films ? (
            <View style={styles.centerPad}>
              <ActivityIndicator color={colors.gold} />
            </View>
          ) : (
            <>
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.filmCatRow}
              >
                {FILM_CATEGORIES.map((c) => {
                  const active = filmCategory === c.value;
                  return (
                    <Pressable
                      key={c.value}
                      testID={`library-film-cat-${c.value}`}
                      onPress={() => setFilmCategory(c.value)}
                      style={[styles.filmCatChip, active && styles.filmCatChipActive]}
                    >
                      <Ionicons
                        name={c.icon}
                        size={13}
                        color={active ? colors.surface : colors.textSecondary}
                      />
                      <Text style={[styles.filmCatChipText, active && { color: colors.surface }]}>
                        {c.label}
                      </Text>
                    </Pressable>
                  );
                })}
              </ScrollView>
              {filteredFilms.length === 0 ? (
                <Text style={styles.empty}>No films in this category yet.</Text>
              ) : null}
              {filteredFilms.map(renderFilmCard)}
            </>
          )
        ) : null}

        <View style={{ height: 120 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.textPrimary },
  segmentRow: {
    flexDirection: "row",
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
  },
  segment: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 8,
    borderRadius: radius.round,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  segmentActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  segmentText: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.textSecondary,
    letterSpacing: 0.3,
  },
  scrollBody: { paddingHorizontal: spacing.lg, paddingBottom: spacing.xl },
  centerPad: { paddingVertical: spacing.xl, alignItems: "center" },
  section: {
    fontFamily: fonts.headingSemi,
    fontSize: 16,
    color: colors.textPrimary,
    marginTop: spacing.lg,
    marginBottom: spacing.xs,
    letterSpacing: 0.2,
  },
  sectionHint: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textMuted,
    marginBottom: spacing.md,
  },
  empty: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textMuted,
    textAlign: "center",
    marginVertical: spacing.xl,
  },
  // Books
  bookCard: {
    flexDirection: "row",
    gap: spacing.md,
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  cover: {
    width: 64,
    height: 88,
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
  },
  externalBadge: {
    position: "absolute",
    top: 4,
    right: 4,
    backgroundColor: "rgba(0,0,0,0.35)",
    borderRadius: radius.round,
    padding: 3,
  },
  lockBadge: {
    position: "absolute",
    bottom: 4,
    right: 4,
    backgroundColor: colors.gold,
    borderRadius: radius.round,
    width: 18, height: 18,
    alignItems: "center", justifyContent: "center",
  },
  bookMeta: { flex: 1, justifyContent: "center" },
  bookTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary, lineHeight: 20 },
  bookAuthor: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textSecondary, marginTop: 4 },
  bookTrad: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1.4,
    marginTop: 6,
    textTransform: "uppercase",
  },
  progressTrack: {
    marginTop: spacing.sm,
    height: 4,
    backgroundColor: colors.borderSoft,
    borderRadius: 2,
    overflow: "hidden",
  },
  progressFill: { height: 4, borderRadius: 2 },
  // Radio
  stationCard: {
    flexDirection: "row",
    alignItems: "center",
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  stationIcon: {
    width: 52,
    height: 52,
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
  },
  stationName: { fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary },
  stationBlurb: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 4,
    lineHeight: 16,
  },
  stationMetaRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
  stationMetaTag: {
    fontFamily: fonts.uiMedium,
    fontSize: 10,
    color: colors.textSecondary,
    letterSpacing: 0.8,
  },
  liveDot: { width: 6, height: 6, borderRadius: 3 },
  playBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: "center",
    justifyContent: "center",
  },
  errorBox: {
    flexDirection: "row",
    gap: spacing.sm,
    padding: spacing.md,
    backgroundColor: "rgba(184, 134, 11, 0.08)",
    borderRadius: radius.md,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: "rgba(184, 134, 11, 0.25)",
  },
  errorText: {
    flex: 1,
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textSecondary,
    lineHeight: 16,
  },
  nativeNote: {
    flexDirection: "row",
    gap: spacing.sm,
    alignItems: "center",
    marginTop: spacing.lg,
    paddingHorizontal: spacing.sm,
  },
  nativeNoteText: {
    flex: 1,
    fontFamily: fonts.bodyRegular,
    fontSize: 11,
    color: colors.textMuted,
    fontStyle: "italic",
  },
  // Films
  filmCatRow: {
    flexDirection: "row",
    gap: spacing.sm,
    paddingVertical: spacing.md,
  },
  filmCatChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderRadius: radius.round,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  filmCatChipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  bookFilterRow: {
    flexDirection: "row",
    gap: spacing.sm,
    paddingBottom: spacing.sm,
  },
  bookFilterChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderRadius: radius.round,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  bookFilterChipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  bookFilterChipText: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.textSecondary,
    letterSpacing: 0.3,
  },
  freeTag: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    gap: 3,
    marginTop: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: radius.round,
    backgroundColor: colors.liturgical.green + "1A",
  },
  freeTagText: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    color: colors.liturgical.green,
    letterSpacing: 0.3,
  },
  filmCatChipText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.textSecondary,
    letterSpacing: 0.3,
  },
  filmCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    overflow: "hidden",
    ...shadow.card,
  },
  filmThumbWrap: { width: "100%", aspectRatio: 16 / 9, position: "relative" },
  filmThumb: { width: "100%", height: "100%", backgroundColor: colors.borderSoft },
  filmCategoryPill: {
    position: "absolute",
    top: 10,
    left: 10,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.round,
  },
  filmCategoryText: {
    fontFamily: fonts.uiSemi,
    fontSize: 9,
    color: colors.gold,
    letterSpacing: 1.2,
  },
  filmDuration: {
    position: "absolute",
    bottom: 10,
    right: 10,
    backgroundColor: "rgba(0,0,0,0.7)",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.sm,
  },
  filmDurationText: { fontFamily: fonts.uiSemi, fontSize: 10, color: "#FFF" },
  filmPlayOverlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: "center",
    justifyContent: "center",
  },
  filmTitle: { fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary },
  filmBlurb: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 4,
    lineHeight: 16,
  },
});

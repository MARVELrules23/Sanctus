import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import YouTubeEmbed from "@/src/components/YouTubeEmbed";
import { LibraryFilm, getLibraryFilm } from "@/src/api";
import { useRadioPlayer } from "@/src/audio/RadioPlayerContext";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const CATEGORY_LABEL: Record<string, string> = {
  saints: "Saints",
  doctrine: "Doctrine",
  animated: "For Kids",
  documentary: "Documentary",
};

export default function FilmDetailScreen() {
  const router = useRouter();
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const radio = useRadioPlayer();

  const [film, setFilm] = useState<LibraryFilm | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!slug) return;
    let mounted = true;
    (async () => {
      try {
        const f = await getLibraryFilm(slug);
        if (mounted) setFilm(f);
      } catch (e: any) {
        if (mounted) setError(e?.message || "Couldn't load this film.");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [slug]);

  // Pause radio when the user starts watching a film — they almost
  // certainly don't want both playing at once.
  useEffect(() => {
    if (playing && radio.isPlaying) {
      radio.pause();
    }
  }, [playing, radio]);

  const openYouTube = () => {
    if (!film) return;
    const url = `https://www.youtube.com/watch?v=${film.youtube_id}`;
    Linking.openURL(url).catch(() => {});
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safe}>
        <Stack.Screen options={{ headerShown: false }} />
        <Header onBack={() => router.back()} title="Film" />
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
        </View>
      </SafeAreaView>
    );
  }

  if (error || !film) {
    return (
      <SafeAreaView style={styles.safe}>
        <Stack.Screen options={{ headerShown: false }} />
        <Header onBack={() => router.back()} title="Film" />
        <View style={styles.center}>
          <Ionicons name="alert-circle-outline" size={36} color={colors.textMuted} />
          <Text style={styles.errorText}>{error || "Film not found."}</Text>
        </View>
      </SafeAreaView>
    );
  }

  const accent = film.accent_color || colors.gold;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <Header onBack={() => router.back()} title="Film" />

      <ScrollView contentContainerStyle={styles.body}>
        <View style={styles.playerWrap} testID={`film-player-${film.slug}`}>
          <YouTubeEmbed
            videoId={film.youtube_id}
            playing={playing}
            onPlayingChange={setPlaying}
            height={210}
          />
        </View>

        <View style={styles.metaRow}>
          <View style={[styles.categoryPill, { backgroundColor: accent }]}>
            <Text style={styles.categoryText}>
              {CATEGORY_LABEL[film.category] || film.category}
            </Text>
          </View>
          {film.duration_label ? (
            <View style={styles.durationPill}>
              <Ionicons name="time-outline" size={12} color={colors.textSecondary} />
              <Text style={styles.durationText}>{film.duration_label}</Text>
            </View>
          ) : null}
        </View>

        <Text style={styles.title}>{film.title}</Text>
        {film.blurb ? <Text style={styles.blurb}>{film.blurb}</Text> : null}

        <View style={styles.btnRow}>
          <Pressable
            testID="film-toggle-play"
            onPress={() => setPlaying((p) => !p)}
            style={[styles.primaryBtn, { backgroundColor: accent }]}
          >
            <Ionicons name={playing ? "pause" : "play"} size={18} color={colors.gold} />
            <Text style={styles.primaryBtnText}>{playing ? "Pause" : "Watch now"}</Text>
          </Pressable>
          <Pressable testID="film-open-youtube" onPress={openYouTube} style={styles.secondaryBtn}>
            <Ionicons name="logo-youtube" size={18} color={colors.textPrimary} />
            <Text style={styles.secondaryBtnText}>Open on YouTube</Text>
          </Pressable>
        </View>

        <View style={styles.attribution}>
          <Ionicons name="information-circle-outline" size={14} color={colors.textMuted} />
          <Text style={styles.attributionText}>
            Hosted by the original creator on YouTube. Sanctus links to publicly available videos for
            devotional and catechetical use.
          </Text>
        </View>

        <View style={{ height: 120 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function Header({ onBack, title }: { onBack: () => void; title: string }) {
  return (
    <View style={styles.header}>
      <Pressable hitSlop={12} onPress={onBack} testID="film-back">
        <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
      </Pressable>
      <Text style={styles.headerTitle}>{title}</Text>
      <View style={{ width: 22 }} />
    </View>
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
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.md },
  errorText: { fontFamily: fonts.bodyRegular, color: colors.textSecondary, fontSize: 14 },
  body: { paddingHorizontal: spacing.lg, paddingBottom: spacing.xl },
  playerWrap: {
    marginTop: spacing.md,
    borderRadius: radius.lg,
    overflow: "hidden",
    ...shadow.card,
    backgroundColor: "#000",
  },
  metaRow: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.lg, alignItems: "center" },
  categoryPill: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.round },
  categoryText: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    color: colors.gold,
    letterSpacing: 1.2,
  },
  durationPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    backgroundColor: colors.borderSoft,
    borderRadius: radius.round,
  },
  durationText: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textSecondary },
  title: {
    fontFamily: fonts.headingBold,
    fontSize: 22,
    color: colors.textPrimary,
    marginTop: spacing.sm,
    lineHeight: 28,
  },
  blurb: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: spacing.sm,
    lineHeight: 20,
  },
  btnRow: { flexDirection: "row", gap: spacing.md, marginTop: spacing.lg },
  primaryBtn: {
    flex: 1,
    flexDirection: "row",
    gap: 8,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 14,
    borderRadius: radius.round,
  },
  primaryBtnText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold, letterSpacing: 0.5 },
  secondaryBtn: {
    flex: 1,
    flexDirection: "row",
    gap: 8,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 14,
    borderRadius: radius.round,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  secondaryBtnText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textPrimary, letterSpacing: 0.5 },
  attribution: {
    flexDirection: "row",
    gap: spacing.sm,
    marginTop: spacing.lg,
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  attributionText: {
    flex: 1,
    fontFamily: fonts.bodyRegular,
    fontSize: 11,
    color: colors.textMuted,
    lineHeight: 15,
  },
});

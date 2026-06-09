import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useKeepAwake } from "@/src/utils/keep-awake";

import BreathingGuide from "@/src/components/BreathingGuide";
import RotatingQuote from "@/src/components/RotatingQuote";
import SanctuaryAudio from "@/src/components/SanctuaryAudio";
import {
  MEDITATION_TRACKS,
  SanctuaryTrack,
  TrackKind,
} from "@/src/utils/sanctuary-tracks";
import { colors, fonts, radius, spacing } from "@/src/theme";

const TIMER_OPTIONS: { label: string; minutes: number }[] = [
  { label: "5 min", minutes: 5 },
  { label: "10 min", minutes: 10 },
  { label: "15 min", minutes: 15 },
  { label: "20 min", minutes: 20 },
  { label: "30 min", minutes: 30 },
];

const FILTER_KINDS: { label: string; kind: TrackKind | "all" }[] = [
  { label: "All", kind: "all" },
  { label: "Piano", kind: "piano" },
  { label: "Harp / Organ", kind: "harp" },
  { label: "Chant", kind: "chant" },
];

function fmt(secs: number): string {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function MeditationScreen() {
  useKeepAwake();

  const [filter, setFilter] = useState<TrackKind | "all">("all");
  const tracks = useMemo<SanctuaryTrack[]>(
    () => (filter === "all" ? MEDITATION_TRACKS : MEDITATION_TRACKS.filter((t) => t.kind === filter)),
    [filter],
  );
  const [activeTrack, setActiveTrack] = useState<SanctuaryTrack | null>(MEDITATION_TRACKS[0]);
  const [playing, setPlaying] = useState(false);
  const [timerMin, setTimerMin] = useState<number | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [showCompletion, setShowCompletion] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Drive the countdown when playing.
  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (playing && secondsLeft > 0) {
      intervalRef.current = setInterval(() => {
        setSecondsLeft((s) => {
          if (s <= 1) {
            // Time's up
            if (intervalRef.current) clearInterval(intervalRef.current);
            setPlaying(false);
            setShowCompletion(true);
            return 0;
          }
          return s - 1;
        });
      }, 1000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [playing, secondsLeft]);

  const startWithTimer = (minutes: number) => {
    setTimerMin(minutes);
    setSecondsLeft(minutes * 60);
    setPlaying(true);
  };

  const clearTimer = () => {
    setTimerMin(null);
    setSecondsLeft(0);
  };

  const pickTrack = (t: SanctuaryTrack) => {
    if (t.id === activeTrack?.id) return;
    setActiveTrack(t);
    // Keep playing state — the audio component will pick up the new track and start.
  };

  /**
   * Toggle play/pause from the breathing-orb tap. If the user hasn't picked
   * a timer yet we deliberately leave the timer untouched — they can run an
   * open-ended sit and tap again to pause. Hitting play with a timer that's
   * already counted down to zero resets it to the previously-chosen length
   * so the orb behaves like a real play/pause control.
   */
  const toggleOrb = () => {
    if (playing) {
      setPlaying(false);
      return;
    }
    if (timerMin != null && secondsLeft <= 0) {
      setSecondsLeft(timerMin * 60);
    }
    setPlaying(true);
  };

  return (
    <SafeAreaView style={styles.screen} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      {/* Header */}
      <View style={styles.headerRow}>
        <Pressable
          onPress={() => router.back()}
          hitSlop={16}
          style={({ pressed }) => [styles.headerBtn, pressed && styles.pressed]}
          testID="meditation-back"
        >
          <Ionicons name="chevron-back" size={22} color={colors.gold} />
        </Pressable>
        <View style={{ flex: 1 }}>
          <Text style={styles.headerEyebrow}>SANCTUARY</Text>
          <Text style={styles.headerTitle}>Meditation</Text>
        </View>
        {timerMin != null && secondsLeft > 0 ? (
          <View style={styles.timerPill} testID="meditation-timer-pill">
            <Ionicons name="time-outline" size={14} color={colors.gold} />
            <Text style={styles.timerPillText}>{fmt(secondsLeft)}</Text>
          </View>
        ) : null}
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        {/* Breathing orb */}
        <BreathingGuide active={playing} onTogglePlay={toggleOrb} />

        {/* Rotating scripture / saint quote */}
        <RotatingQuote active={playing} />

        {/* Filter chips */}
        <View style={styles.filterRow}>
          {FILTER_KINDS.map((f) => (
            <Pressable
              key={f.kind}
              onPress={() => setFilter(f.kind)}
              testID={`meditation-filter-${f.kind}`}
              style={({ pressed }) => [
                styles.filterChip,
                filter === f.kind && styles.filterChipActive,
                pressed && styles.pressed,
              ]}
            >
              <Text
                style={[
                  styles.filterChipText,
                  filter === f.kind && styles.filterChipTextActive,
                ]}
              >
                {f.label}
              </Text>
            </Pressable>
          ))}
        </View>

        {/* Track list */}
        <View style={styles.trackList}>
          {tracks.map((t) => {
            const isActive = t.id === activeTrack?.id;
            return (
              <Pressable
                key={t.id}
                onPress={() => pickTrack(t)}
                testID={`meditation-track-${t.id}`}
                style={({ pressed }) => [
                  styles.trackRow,
                  isActive && styles.trackRowActive,
                  pressed && styles.pressed,
                ]}
              >
                <Ionicons
                  name={isActive ? "ellipse" : "ellipse-outline"}
                  size={14}
                  color={isActive ? colors.gold : colors.textMuted}
                />
                <View style={{ flex: 1 }}>
                  <Text style={styles.trackTitle}>{t.title}</Text>
                  <Text style={styles.trackArtist} numberOfLines={1}>
                    {t.artist} {t.durationLabel ? `\u00b7 ${t.durationLabel}` : ""}
                  </Text>
                </View>
              </Pressable>
            );
          })}
        </View>

        {/* Player */}
        <View style={styles.playerWrap}>
          <SanctuaryAudio
            track={activeTrack}
            playing={playing}
            onPlayPauseChange={setPlaying}
          />
        </View>

        {/* Timer selector */}
        <Text style={styles.sectionLabel}>SET A SOFT TIMER</Text>
        <View style={styles.timerRow}>
          {TIMER_OPTIONS.map((opt) => {
            const isActive = timerMin === opt.minutes && secondsLeft > 0;
            return (
              <Pressable
                key={opt.minutes}
                onPress={() => startWithTimer(opt.minutes)}
                testID={`meditation-timer-${opt.minutes}`}
                style={({ pressed }) => [
                  styles.timerChip,
                  isActive && styles.timerChipActive,
                  pressed && styles.pressed,
                ]}
              >
                <Text
                  style={[
                    styles.timerChipText,
                    isActive && styles.timerChipTextActive,
                  ]}
                >
                  {opt.label}
                </Text>
              </Pressable>
            );
          })}
          {timerMin != null ? (
            <Pressable
              onPress={clearTimer}
              testID="meditation-timer-clear"
              style={({ pressed }) => [styles.timerClearBtn, pressed && styles.pressed]}
            >
              <Ionicons name="close" size={14} color={colors.textMuted} />
              <Text style={styles.timerClearText}>Clear</Text>
            </Pressable>
          ) : null}
        </View>
        <Text style={styles.timerHint}>
          When the timer rings out, the music stops and a gentle prompt invites you back.
        </Text>

        <View style={{ height: spacing.xxl }} />
      </ScrollView>

      {/* Completion overlay */}
      <Modal visible={showCompletion} transparent animationType="fade">
        <View style={styles.completionBackdrop}>
          <View style={styles.completionCard} testID="meditation-completion">
            <Ionicons name="leaf-outline" size={36} color={colors.gold} />
            <Text style={styles.completionTitle}>Time to return.</Text>
            <Text style={styles.completionBody}>
              May the peace of Christ go with you wherever you walk next.
            </Text>
            <Pressable
              onPress={() => {
                setShowCompletion(false);
                clearTimer();
              }}
              testID="meditation-completion-close"
              style={({ pressed }) => [styles.completionBtn, pressed && styles.pressed]}
            >
              <Text style={styles.completionBtnText}>Amen</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    gap: spacing.md,
  },
  headerBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  headerEyebrow: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    color: colors.gold,
    letterSpacing: 2,
  },
  headerTitle: {
    fontFamily: fonts.headingBold,
    fontSize: 22,
    color: colors.textPrimary,
  },
  timerPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: spacing.sm,
    paddingVertical: 6,
    backgroundColor: colors.primary,
    borderRadius: radius.round,
  },
  timerPillText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 13,
    letterSpacing: 0.5,
  },
  scroll: { paddingHorizontal: spacing.lg, paddingBottom: spacing.xxl },
  filterRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  filterChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  filterChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  filterChipText: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.textPrimary,
    letterSpacing: 0.3,
  },
  filterChipTextActive: { color: colors.gold },
  trackList: {
    marginTop: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    overflow: "hidden",
  },
  trackRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  trackRowActive: {
    backgroundColor: "#FBF6E8",
  },
  trackTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 15,
    color: colors.textPrimary,
  },
  trackArtist: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  playerWrap: { marginTop: spacing.lg },
  sectionLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.gold,
    letterSpacing: 1.5,
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
  },
  timerRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  timerChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  timerChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  timerChipText: {
    fontFamily: fonts.uiSemi,
    color: colors.textPrimary,
    fontSize: 13,
    letterSpacing: 0.3,
  },
  timerChipTextActive: { color: colors.gold },
  timerClearBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
  },
  timerClearText: {
    fontFamily: fonts.uiMedium,
    fontSize: 12,
    color: colors.textMuted,
  },
  timerHint: {
    fontFamily: fonts.bodyItalic,
    fontSize: 12,
    color: colors.textMuted,
    marginTop: spacing.sm,
    lineHeight: 17,
  },
  completionBackdrop: {
    flex: 1,
    backgroundColor: "rgba(20, 26, 42, 0.85)",
    alignItems: "center",
    justifyContent: "center",
    padding: spacing.lg,
  },
  completionCard: {
    width: "100%",
    maxWidth: 360,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.xl,
    alignItems: "center",
    gap: spacing.md,
  },
  completionTitle: {
    fontFamily: fonts.headingBold,
    fontSize: 24,
    color: colors.textPrimary,
    textAlign: "center",
  },
  completionBody: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: "center",
    lineHeight: 21,
  },
  completionBtn: {
    marginTop: spacing.sm,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.sm + 4,
    borderRadius: radius.md,
    backgroundColor: colors.primary,
  },
  completionBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 14,
    letterSpacing: 1,
  },
  pressed: { opacity: 0.75 },
});

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

import SanctuaryAudio from "@/src/components/SanctuaryAudio";
import {
  STUDY_TRACKS,
  SanctuaryTrack,
  TrackKind,
} from "@/src/utils/sanctuary-tracks";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const FOCUS_MIN = 25;
const SHORT_BREAK_MIN = 5;
const LONG_BREAK_MIN = 15;
const POMODOROS_BEFORE_LONG_BREAK = 4;

type Phase = "focus" | "short-break" | "long-break" | "idle";

const FILTER_KINDS: { label: string; kind: TrackKind | "all" }[] = [
  { label: "All", kind: "all" },
  { label: "Catholic Lofi", kind: "lofi" },
  { label: "Piano", kind: "piano" },
];

function fmt(secs: number): string {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function StudyScreen() {
  useKeepAwake();

  const [filter, setFilter] = useState<TrackKind | "all">("all");
  const tracks = useMemo<SanctuaryTrack[]>(
    () => (filter === "all" ? STUDY_TRACKS : STUDY_TRACKS.filter((t) => t.kind === filter)),
    [filter],
  );

  const [activeTrack, setActiveTrack] = useState<SanctuaryTrack | null>(STUDY_TRACKS[0]);
  const [playing, setPlaying] = useState(false);

  // Pomodoro state
  const [phase, setPhase] = useState<Phase>("idle");
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [cyclesDone, setCyclesDone] = useState(0);
  const [phaseDoneOverlay, setPhaseDoneOverlay] = useState<Phase | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const phaseLabel = (p: Phase): string => {
    switch (p) {
      case "focus":       return "Focus";
      case "short-break": return "Short break";
      case "long-break":  return "Long break";
      default:            return "Ready";
    }
  };

  const phaseColor = (p: Phase): string => {
    switch (p) {
      case "focus":       return colors.gold;
      case "short-break": return colors.liturgical.green;
      case "long-break":  return colors.liturgical.green;
      default:            return colors.textMuted;
    }
  };

  // Tick down each second when the timer is running
  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (phase !== "idle" && secondsLeft > 0) {
      intervalRef.current = setInterval(() => {
        setSecondsLeft((s) => {
          if (s <= 1) {
            // Phase ended — surface a gentle overlay and advance.
            if (intervalRef.current) clearInterval(intervalRef.current);
            setPhaseDoneOverlay(phase);
            return 0;
          }
          return s - 1;
        });
      }, 1000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [phase, secondsLeft]);

  const startFocus = () => {
    setPhase("focus");
    setSecondsLeft(FOCUS_MIN * 60);
    setPlaying(true);
  };

  const advanceAfterFocus = () => {
    const nextCycles = cyclesDone + 1;
    setCyclesDone(nextCycles);
    if (nextCycles % POMODOROS_BEFORE_LONG_BREAK === 0) {
      setPhase("long-break");
      setSecondsLeft(LONG_BREAK_MIN * 60);
    } else {
      setPhase("short-break");
      setSecondsLeft(SHORT_BREAK_MIN * 60);
    }
    setPlaying(false);  // music pauses during breaks
  };

  const advanceAfterBreak = () => {
    // Auto-start the next focus block
    startFocus();
  };

  const handlePhaseDoneClose = () => {
    const finishedPhase = phaseDoneOverlay;
    setPhaseDoneOverlay(null);
    if (finishedPhase === "focus") {
      advanceAfterFocus();
    } else if (finishedPhase === "short-break" || finishedPhase === "long-break") {
      advanceAfterBreak();
    }
  };

  const stopAll = () => {
    setPhase("idle");
    setSecondsLeft(0);
    setPlaying(false);
    setCyclesDone(0);
    setPhaseDoneOverlay(null);
  };

  const skipPhase = () => {
    // End the current phase early — same flow as if the timer hit 0.
    if (phase !== "idle") {
      setPhaseDoneOverlay(phase);
      setSecondsLeft(0);
    }
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
          testID="study-back"
        >
          <Ionicons name="chevron-back" size={22} color={colors.gold} />
        </Pressable>
        <View style={{ flex: 1 }}>
          <Text style={styles.headerEyebrow}>SANCTUARY</Text>
          <Text style={styles.headerTitle}>Study</Text>
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        {/* Pomodoro clock */}
        <View style={styles.clockCard}>
          <View style={styles.clockTopRow}>
            <Text style={[styles.phaseLabel, { color: phaseColor(phase) }]}>
              {phaseLabel(phase).toUpperCase()}
            </Text>
            <Text style={styles.cycleText} testID="study-cycle">
              Pomodoro {cyclesDone + (phase === "focus" ? 1 : 0)} / {POMODOROS_BEFORE_LONG_BREAK}
            </Text>
          </View>
          <Text style={styles.clockTime} testID="study-clock">
            {phase === "idle" ? fmt(FOCUS_MIN * 60) : fmt(secondsLeft)}
          </Text>
          <View style={styles.clockBtnRow}>
            {phase === "idle" ? (
              <Pressable
                testID="study-start-focus"
                onPress={startFocus}
                style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
              >
                <Ionicons name="play" size={16} color={colors.gold} />
                <Text style={styles.primaryBtnText}>Start a 25-min focus</Text>
              </Pressable>
            ) : (
              <>
                <Pressable
                  testID="study-skip-phase"
                  onPress={skipPhase}
                  style={({ pressed }) => [styles.secondaryBtn, pressed && styles.pressed]}
                >
                  <Ionicons name="play-skip-forward-outline" size={14} color={colors.primary} />
                  <Text style={styles.secondaryBtnText}>End phase</Text>
                </Pressable>
                <Pressable
                  testID="study-stop"
                  onPress={stopAll}
                  style={({ pressed }) => [styles.secondaryBtn, pressed && styles.pressed]}
                >
                  <Ionicons name="stop-outline" size={14} color={colors.primary} />
                  <Text style={styles.secondaryBtnText}>Stop</Text>
                </Pressable>
              </>
            )}
          </View>
          <Text style={styles.clockHint}>
            25 min focus &middot; 5 min break &middot; long break after 4 cycles
          </Text>
        </View>

        {/* Filter chips */}
        <View style={styles.filterRow}>
          {FILTER_KINDS.map((f) => (
            <Pressable
              key={f.kind}
              onPress={() => setFilter(f.kind)}
              testID={`study-filter-${f.kind}`}
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
                onPress={() => setActiveTrack(t)}
                testID={`study-track-${t.id}`}
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

        {/* Audio player */}
        <View style={styles.playerWrap}>
          <SanctuaryAudio
            track={activeTrack}
            playing={playing}
            onPlayPauseChange={setPlaying}
          />
        </View>

        <Text style={styles.tip}>
          Tip: keep the volume low &mdash; lofi works best when it&apos;s under your thoughts, not over them.
        </Text>

        <View style={{ height: spacing.xxl }} />
      </ScrollView>

      <Modal visible={!!phaseDoneOverlay} transparent animationType="fade">
        <View style={styles.completionBackdrop}>
          <View style={styles.completionCard} testID="study-phase-done">
            <Ionicons
              name={phaseDoneOverlay === "focus" ? "cafe-outline" : "book-outline"}
              size={36}
              color={colors.gold}
            />
            <Text style={styles.completionTitle}>
              {phaseDoneOverlay === "focus"
                ? "Step away for 5 minutes."
                : phaseDoneOverlay === "long-break"
                  ? "Long break complete."
                  : "Break over."}
            </Text>
            <Text style={styles.completionBody}>
              {phaseDoneOverlay === "focus"
                ? "Stand, drink water, stretch. The lofi will return when you start the next focus block."
                : "Ready to begin the next focus block?"}
            </Text>
            <Pressable
              onPress={handlePhaseDoneClose}
              testID="study-phase-done-close"
              style={({ pressed }) => [styles.completionBtn, pressed && styles.pressed]}
            >
              <Text style={styles.completionBtnText}>
                {phaseDoneOverlay === "focus" ? "Begin break" : "Start focus"}
              </Text>
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
  scroll: { paddingHorizontal: spacing.lg, paddingBottom: spacing.xxl },
  clockCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    alignItems: "center",
    marginTop: spacing.md,
    ...shadow.card,
  },
  clockTopRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    alignSelf: "stretch",
  },
  phaseLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 2,
  },
  cycleText: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textMuted,
    letterSpacing: 1,
  },
  clockTime: {
    fontFamily: fonts.headingBold,
    fontSize: 64,
    color: colors.textPrimary,
    marginVertical: spacing.md,
    letterSpacing: 1,
  },
  clockBtnRow: {
    flexDirection: "row",
    gap: spacing.sm,
    flexWrap: "wrap",
    justifyContent: "center",
  },
  primaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.sm + 4,
    borderRadius: radius.md,
  },
  primaryBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 14,
    letterSpacing: 0.4,
  },
  secondaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  secondaryBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.primary,
    fontSize: 13,
  },
  clockHint: {
    fontFamily: fonts.bodyItalic,
    fontSize: 11,
    color: colors.textMuted,
    marginTop: spacing.md,
    textAlign: "center",
  },
  filterRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginTop: spacing.lg,
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
  tip: {
    fontFamily: fonts.bodyItalic,
    fontSize: 12,
    color: colors.textMuted,
    marginTop: spacing.lg,
    textAlign: "center",
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
    fontSize: 22,
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
    letterSpacing: 0.6,
  },
  pressed: { opacity: 0.75 },
});

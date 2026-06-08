import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  AppState,
  AppStateStatus,
  Platform,
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";

import { api, SDSession } from "@/src/api";
import SilhouetteAnimation from "@/src/components/SilhouetteAnimation";
import { colors, fonts, radius, spacing } from "@/src/theme";
import {
  buildPlayerSteps,
  PlayerStep,
  totalDurationSec,
} from "@/src/utils/sd-player";
import {
  loadVoiceEnabled,
  saveVoiceEnabled,
  speak,
  stopSpeaking,
} from "@/src/utils/voice";

function pad2(n: number) {
  return n < 10 ? `0${n}` : `${n}`;
}

function fmtTime(sec: number) {
  const m = Math.floor(sec / 60);
  const s = Math.max(0, sec % 60);
  return `${pad2(m)}:${pad2(s)}`;
}

function sectionColor(tag: PlayerStep["sectionTag"]): string {
  switch (tag) {
    case "WARM-UP":
      return "#A57F2C";
    case "DRILL":
      return colors.gold;
    case "TECHNIQUE":
      return "#8B5A2B";
    case "LIVE":
      return colors.liturgical.red;
    case "COOL-DOWN":
      return "#5F7A8A";
    case "REST":
      return colors.textMuted;
    default:
      return colors.gold;
  }
}

export default function SelfDefensePlayerScreen() {
  const params = useLocalSearchParams<{ id: string; start?: string }>();
  const router = useRouter();
  const sessionId = String(params.id || "");
  const startIndex = Math.max(0, parseInt(String(params.start || "0"), 10) || 0);

  const [session, setSession] = useState<SDSession | null>(null);
  const [steps, setSteps] = useState<PlayerStep[]>([]);
  const [index, setIndex] = useState<number>(startIndex);
  const [secondsLeft, setSecondsLeft] = useState<number>(0);
  const [running, setRunning] = useState<boolean>(false);
  const [completedAll, setCompletedAll] = useState<boolean>(false);
  const [voiceOn, setVoiceOn] = useState<boolean>(true);
  const [loading, setLoading] = useState(true);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastSpokenRef = useRef<string>("");
  const lastBeepRef = useRef<number>(-1);

  // Load session + steps
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        const s = await api<SDSession>(`/self-defense/sessions/${sessionId}`);
        if (cancelled) return;
        const built = buildPlayerSteps(s);
        if (built.length === 0) {
          Alert.alert("Nothing to play", "This session has no exercises.");
          router.back();
          return;
        }
        setSession(s);
        setSteps(built);
        const initial = Math.min(startIndex, built.length - 1);
        setIndex(initial);
        setSecondsLeft(built[initial].durationSec);
        setLoading(false);
      } catch (e: any) {
        if (cancelled) return;
        Alert.alert("Couldn't load", e?.message || "Please try again.");
        router.back();
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [sessionId, startIndex, router]);

  // Load voice preference
  useEffect(() => {
    void loadVoiceEnabled().then((v) => setVoiceOn(v));
    return () => stopSpeaking();
  }, []);

  // Pause when app backgrounded
  useEffect(() => {
    const sub = AppState.addEventListener("change", (next: AppStateStatus) => {
      if (next !== "active") {
        setRunning(false);
        stopSpeaking();
      }
    });
    return () => sub.remove();
  }, []);

  const goToIndex = useCallback(
    (i: number, autostart: boolean) => {
      stopSpeaking();
      lastBeepRef.current = -1;
      if (i < 0) i = 0;
      if (i >= steps.length) {
        setCompletedAll(true);
        setRunning(false);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
        return;
      }
      setIndex(i);
      setSecondsLeft(steps[i].durationSec);
      setRunning(autostart);
    },
    [steps],
  );

  // Tick
  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (!running || completedAll) return;
    intervalRef.current = setInterval(() => {
      setSecondsLeft((sec) => {
        if (sec <= 1) {
          // Auto-advance handled by effect below; clamp here
          return 0;
        }
        // beeps & "3,2,1" cue for last 3 seconds (haptic only — no audio beep)
        if (sec <= 4 && sec >= 2) {
          if (lastBeepRef.current !== sec) {
            lastBeepRef.current = sec;
            Haptics.selectionAsync().catch(() => {});
          }
        }
        return sec - 1;
      });
    }, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [running, completedAll]);

  // Speak step intro when index changes & running
  useEffect(() => {
    if (loading || steps.length === 0) return;
    const step = steps[index];
    if (!step) return;
    const key = `${index}-${step.id}`;
    if (lastSpokenRef.current === key) return;
    lastSpokenRef.current = key;
    if (running && voiceOn) {
      void speak(step.voiceIntro, true);
    }
  }, [index, running, voiceOn, steps, loading]);

  // Auto-advance when timer hits 0
  useEffect(() => {
    if (!running || completedAll) return;
    if (secondsLeft === 0) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      goToIndex(index + 1, true);
    }
  }, [secondsLeft, running, index, goToIndex, completedAll]);

  const playPause = useCallback(() => {
    if (completedAll) {
      // Restart
      setCompletedAll(false);
      goToIndex(0, true);
      return;
    }
    setRunning((r) => {
      const next = !r;
      if (!next) stopSpeaking();
      Haptics.selectionAsync().catch(() => {});
      return next;
    });
  }, [completedAll, goToIndex]);

  const toggleVoice = useCallback(() => {
    setVoiceOn((v) => {
      const next = !v;
      void saveVoiceEnabled(next);
      if (!next) stopSpeaking();
      else if (running && steps[index]) {
        void speak(steps[index].voiceIntro, true);
      }
      return next;
    });
  }, [running, steps, index]);

  const onMarkComplete = useCallback(async () => {
    if (!session) return;
    try {
      await api(`/self-defense/sessions/${session.session_id}/complete`, {
        method: "POST",
        body: { notes: "Completed via guided player", intensity_actual: null },
      });
      router.replace({ pathname: "/self-defense/session/[id]", params: { id: session.session_id } });
    } catch (e: any) {
      Alert.alert("Couldn't save", e?.message || "Please try again.");
    }
  }, [session, router]);

  const handleExit = useCallback(() => {
    if (completedAll || !running) {
      stopSpeaking();
      router.back();
      return;
    }
    Alert.alert("Exit session?", "Your progress on this guided run will not be saved.", [
      { text: "Keep training", style: "cancel" },
      {
        text: "Exit",
        style: "destructive",
        onPress: () => {
          stopSpeaking();
          router.back();
        },
      },
    ]);
  }, [completedAll, running, router]);

  const totalSec = useMemo(() => totalDurationSec(steps), [steps]);
  const elapsedBeforeThis = useMemo(() => {
    let acc = 0;
    for (let i = 0; i < index && i < steps.length; i++) acc += steps[i].durationSec;
    return acc;
  }, [steps, index]);
  const overallElapsed = elapsedBeforeThis + (steps[index]?.durationSec || 0) - secondsLeft;
  const overallPct = totalSec === 0 ? 0 : Math.min(100, Math.max(0, (overallElapsed / totalSec) * 100));

  if (loading || !session || steps.length === 0) {
    return (
      <SafeAreaView style={styles.safe}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
        </View>
      </SafeAreaView>
    );
  }

  const step = steps[index];
  const stepPct = step.durationSec === 0 ? 0 : ((step.durationSec - secondsLeft) / step.durationSec) * 100;
  const tagColor = sectionColor(step.sectionTag);

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="sd-player-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <StatusBar barStyle="dark-content" />

      {/* Top bar */}
      <View style={styles.topBar}>
        <Pressable onPress={handleExit} hitSlop={12} testID="sd-player-close">
          <Ionicons name="close" size={26} color={colors.primary} />
        </Pressable>
        <View style={styles.topCenter}>
          <Text style={styles.topTitle} numberOfLines={1}>
            {session.discipline_name}
          </Text>
          <Text style={styles.topSub} numberOfLines={1}>
            {session.plan.title}
          </Text>
        </View>
        <Pressable onPress={toggleVoice} hitSlop={12} testID="sd-player-voice-toggle">
          <Ionicons
            name={voiceOn ? "volume-high" : "volume-mute"}
            size={22}
            color={voiceOn ? colors.primary : colors.textMuted}
          />
        </Pressable>
      </View>

      {/* Overall progress */}
      <View style={styles.overallBar}>
        <View style={[styles.overallFill, { width: `${overallPct}%` }]} />
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
        bounces={false}
      >
        {/* Section tag */}
        <View style={styles.tagRow}>
          <View style={[styles.tagPill, { backgroundColor: tagColor }]}>
            <Text style={styles.tagText}>{step.sectionTag}</Text>
          </View>
          <Text style={styles.sectionText}>{step.section}</Text>
        </View>

        {/* Animated silhouette */}
        <View style={styles.silhouetteWrap}>
          <SilhouetteAnimation mode={step.motion} paused={!running} size={260} />
        </View>

        {/* Title + detail */}
        <Text style={styles.stepTitle} testID="sd-player-step-title">
          {step.title}
        </Text>
        {step.detail ? <Text style={styles.stepDetail}>{step.detail}</Text> : null}
        {step.requiresPartner ? (
          <View style={styles.partnerTag}>
            <Ionicons name="people" size={11} color={colors.liturgical.red} />
            <Text style={styles.partnerTagText}>Partner required</Text>
          </View>
        ) : null}
        {step.notes ? <Text style={styles.stepNotes}>{step.notes}</Text> : null}
        {step.bullets && step.bullets.length > 0 ? (
          <View style={styles.bulletsBox}>
            {step.bullets.map((b, i) => (
              <Text key={i} style={styles.bulletText}>
                · {b}
              </Text>
            ))}
          </View>
        ) : null}

        {/* Step progress bar */}
        <View style={styles.stepBar}>
          <View style={[styles.stepFill, { width: `${stepPct}%` }]} />
        </View>

        {/* Big timer */}
        <Text style={styles.timer} testID="sd-player-timer">
          {fmtTime(secondsLeft)}
        </Text>
        <Text style={styles.timerSub}>
          Step {index + 1} of {steps.length}
        </Text>

        <View style={{ height: spacing.lg }} />
      </ScrollView>

      {/* Bottom controls */}
      <View style={styles.controls}>
        <Pressable
          testID="sd-player-prev"
          onPress={() => goToIndex(index - 1, running)}
          style={({ pressed }) => [styles.controlBtn, pressed && styles.pressed]}
          hitSlop={8}
        >
          <Ionicons name="play-skip-back" size={22} color={colors.primary} />
        </Pressable>
        <Pressable
          testID="sd-player-playpause"
          onPress={playPause}
          style={({ pressed }) => [styles.playBtn, pressed && styles.pressed]}
        >
          <Ionicons
            name={completedAll ? "refresh" : running ? "pause" : "play"}
            size={34}
            color={colors.gold}
          />
        </Pressable>
        <Pressable
          testID="sd-player-next"
          onPress={() => goToIndex(index + 1, running)}
          style={({ pressed }) => [styles.controlBtn, pressed && styles.pressed]}
          hitSlop={8}
        >
          <Ionicons name="play-skip-forward" size={22} color={colors.primary} />
        </Pressable>
      </View>

      {/* Completion overlay */}
      {completedAll ? (
        <View style={styles.completeOverlay} pointerEvents="box-none">
          <View style={styles.completeCard} testID="sd-player-complete">
            <Ionicons name="trophy-outline" size={36} color={colors.gold} />
            <Text style={styles.completeTitle}>Session complete</Text>
            <Text style={styles.completeSub}>
              Well done. The body has been ordered toward virtue.
            </Text>
            <Pressable
              testID="sd-player-mark-complete"
              onPress={onMarkComplete}
              style={({ pressed }) => [styles.completePrimary, pressed && styles.pressed]}
            >
              <Ionicons name="checkmark-circle" size={16} color={colors.gold} />
              <Text style={styles.completePrimaryText}>Mark complete & save</Text>
            </Pressable>
            <Pressable
              testID="sd-player-restart"
              onPress={() => {
                setCompletedAll(false);
                goToIndex(0, true);
              }}
              style={({ pressed }) => [styles.completeSecondary, pressed && styles.pressed]}
            >
              <Text style={styles.completeSecondaryText}>Restart</Text>
            </Pressable>
            <Pressable
              testID="sd-player-back-to-session"
              onPress={() => router.back()}
              style={({ pressed }) => [styles.completeSecondary, pressed && styles.pressed]}
            >
              <Text style={styles.completeSecondaryText}>Back to session</Text>
            </Pressable>
          </View>
        </View>
      ) : null}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingTop: Platform.OS === "android" ? spacing.sm : 0,
    paddingBottom: spacing.sm,
  },
  topCenter: { flex: 1, alignItems: "center", paddingHorizontal: spacing.sm },
  topTitle: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textPrimary },
  topSub: { fontFamily: fonts.bodyRegular, fontSize: 11, color: colors.textSecondary, marginTop: 2 },
  overallBar: {
    height: 3,
    marginHorizontal: spacing.md,
    backgroundColor: colors.borderSoft,
    borderRadius: 2,
    overflow: "hidden",
  },
  overallFill: { height: "100%", backgroundColor: colors.gold },
  scroll: {
    alignItems: "center",
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  tagRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: spacing.sm,
    alignSelf: "stretch",
    justifyContent: "center",
  },
  tagPill: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.round,
  },
  tagText: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    color: "#fff",
    letterSpacing: 1.6,
  },
  sectionText: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textSecondary },
  silhouetteWrap: {
    backgroundColor: "rgba(212,175,55,0.06)",
    borderRadius: radius.lg,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginVertical: spacing.sm,
  },
  stepTitle: {
    fontFamily: fonts.headingBold,
    fontSize: 24,
    color: colors.textPrimary,
    textAlign: "center",
    marginTop: spacing.sm,
  },
  stepDetail: {
    fontFamily: fonts.uiMedium,
    fontSize: 12,
    color: colors.gold,
    marginTop: 4,
    letterSpacing: 1,
  },
  partnerTag: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 6,
    backgroundColor: "rgba(178,34,52,0.08)",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.round,
  },
  partnerTagText: {
    fontFamily: fonts.uiMedium,
    fontSize: 10,
    color: colors.liturgical.red,
    letterSpacing: 1,
  },
  stepNotes: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 13,
    color: colors.textSecondary,
    textAlign: "center",
    marginTop: spacing.sm,
    lineHeight: 20,
    paddingHorizontal: spacing.sm,
  },
  bulletsBox: {
    alignSelf: "stretch",
    marginTop: spacing.sm,
    paddingHorizontal: spacing.sm,
  },
  bulletText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textPrimary,
    lineHeight: 20,
  },
  stepBar: {
    alignSelf: "stretch",
    height: 6,
    backgroundColor: colors.borderSoft,
    borderRadius: 4,
    overflow: "hidden",
    marginTop: spacing.md,
  },
  stepFill: { height: "100%", backgroundColor: colors.gold },
  timer: {
    fontFamily: fonts.headingBold,
    fontSize: 60,
    color: colors.textPrimary,
    marginTop: spacing.sm,
    fontVariant: ["tabular-nums"],
  },
  timerSub: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textSecondary,
    letterSpacing: 1.5,
  },
  controls: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    gap: spacing.lg,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
  },
  controlBtn: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  playBtn: {
    width: 80,
    height: 80,
    borderRadius: 40,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.primary,
  },
  pressed: { opacity: 0.7 },
  completeOverlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(28,40,65,0.78)",
    padding: spacing.lg,
  },
  completeCard: {
    width: "100%",
    maxWidth: 420,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    paddingVertical: spacing.lg,
    paddingHorizontal: spacing.lg,
    alignItems: "center",
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.gold,
  },
  completeTitle: {
    fontFamily: fonts.headingBold,
    fontSize: 22,
    color: colors.textPrimary,
    marginTop: 4,
  },
  completeSub: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 13,
    color: colors.textSecondary,
    textAlign: "center",
    marginBottom: spacing.sm,
  },
  completePrimary: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: colors.primary,
    paddingVertical: 14,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.round,
    alignSelf: "stretch",
  },
  completePrimaryText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 14 },
  completeSecondary: {
    paddingVertical: 10,
    alignItems: "center",
    alignSelf: "stretch",
  },
  completeSecondaryText: {
    fontFamily: fonts.uiMedium,
    fontSize: 13,
    color: colors.textSecondary,
  },
});

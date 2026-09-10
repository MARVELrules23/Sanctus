/**
 * St. Joseph's Workshop — an immersive lo-fi study prompt.
 *
 * A full-screen, calm scene of St. Joseph quietly working wood at his bench
 * (AI-generated, cached on the backend) with a slow Ken-Burns drift, paired
 * with an extra-soft, auto-looping Gregorian chant. A gentle focus timer sits
 * over the scene so the room itself becomes the study cue.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";
import { useAudioPlayer, useAudioPlayerStatus } from "expo-audio";

import { getSanctuaryStudyImage } from "@/src/api";
import LofiSaintBackground from "@/src/components/LofiSaintBackground";
import { useKeepAwake } from "@/src/utils/keep-awake";
import { fonts, spacing } from "@/src/theme";

// Public-domain Gregorian chant (Internet Archive) — extra-soft looping ambiance.
const CHANT_URL = "https://archive.org/download/GregorianChantMass/02Track2.mp3";

const FOCUS_MIN = 25;

function fmt(secs: number): string {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function WorkshopScreen() {
  useKeepAwake();
  const router = useRouter();

  const [image, setImage] = useState<string | null>(null);

  // Extra-soft looping Gregorian chant — auto-tries on open, stops on leave.
  const player = useAudioPlayer(CHANT_URL);
  const audioStatus = useAudioPlayerStatus(player);
  const chantOn = !!audioStatus?.playing;

  useEffect(() => {
    try {
      player.loop = true;
      player.volume = 0.22; // extra soft, sits under your thoughts
    } catch {/* ignore */}
    const t = setTimeout(() => { try { player.play(); } catch {/* autoplay may be blocked on web */} }, 700);
    return () => {
      clearTimeout(t);
      try { player.pause(); } catch {/* ignore */}
    };
  }, [player]);

  const toggleChant = useCallback(() => {
    try {
      if (chantOn) player.pause();
      else player.play();
    } catch {/* ignore */}
  }, [player, chantOn]);

  // Poll for the (lazily generated) illustration until it's ready.
  useEffect(() => {
    let alive = true;
    let tries = 0;
    const fetchImg = async () => {
      if (!alive) return;
      try {
        const r = await getSanctuaryStudyImage();
        if (alive && r.image) { setImage(r.image); return; }
      } catch {/* ignore */}
      tries += 1;
      if (alive && tries < 10) setTimeout(fetchImg, 3000);
    };
    fetchImg();
    return () => { alive = false; };
  }, []);

  // Gentle focus timer
  const [running, setRunning] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(FOCUS_MIN * 60);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
    if (running && secondsLeft > 0) {
      intervalRef.current = setInterval(() => {
        setSecondsLeft((s) => {
          if (s <= 1) {
            if (intervalRef.current) clearInterval(intervalRef.current);
            setRunning(false);
            return 0;
          }
          return s - 1;
        });
      }, 1000);
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [running, secondsLeft]);

  const toggleTimer = () => {
    if (secondsLeft === 0) setSecondsLeft(FOCUS_MIN * 60);
    setRunning((r) => !r);
  };
  const resetTimer = () => { setRunning(false); setSecondsLeft(FOCUS_MIN * 60); };

  return (
    <View style={styles.root} testID="workshop-screen">
      <Stack.Screen options={{ headerShown: false }} />

      <LofiSaintBackground image={image} variant="workshop" />

      <SafeAreaView edges={["top", "bottom"]} style={styles.safe}>
        {/* Top controls */}
        <View style={styles.topRow}>
          <Pressable testID="workshop-back" onPress={() => router.back()} hitSlop={12} style={styles.iconBtn}>
            <Ionicons name="chevron-back" size={26} color="#FFF8EA" />
          </Pressable>
          <Pressable testID="workshop-chant-toggle" onPress={toggleChant} hitSlop={12} style={styles.iconBtn}>
            <Ionicons
              name={chantOn ? "musical-notes" : "musical-notes-outline"}
              size={20}
              color={chantOn ? "#FFE6A8" : "#FFF8EA"}
            />
          </Pressable>
        </View>

        <View style={styles.titleWrap}>
          <Text style={styles.eyebrow}>STUDY WITH</Text>
          <Text style={styles.title}>St. Joseph&apos;s Workshop</Text>
          <Text style={styles.subtitle}>
            Work as he worked — quietly, faithfully, one plank at a time. Soft chant fills the room.
          </Text>
          {!image ? (
            <View style={styles.imgLoading}>
              <ActivityIndicator size="small" color="#FFE6A8" />
              <Text style={styles.imgLoadingText}>Lighting the workshop…</Text>
            </View>
          ) : null}
        </View>

        <View style={{ flex: 1 }} />

        {/* Gentle focus timer */}
        <View style={styles.timerCard}>
          <Text style={styles.timerLabel}>{running ? "FOCUS" : "READY"}</Text>
          <Text style={styles.timerTime} testID="workshop-clock">{fmt(secondsLeft)}</Text>
          <View style={styles.timerBtnRow}>
            <Pressable testID="workshop-timer-toggle" onPress={toggleTimer} hitSlop={10} style={styles.primaryBtn}>
              <Ionicons name={running ? "pause" : "play"} size={16} color="#1A1326" />
              <Text style={styles.primaryBtnText}>{running ? "Pause" : secondsLeft === 0 ? "Begin again" : "Begin 25 min"}</Text>
            </Pressable>
            <Pressable testID="workshop-timer-reset" onPress={resetTimer} hitSlop={10} style={styles.secondaryBtn}>
              <Ionicons name="refresh" size={16} color="#FFF8EA" />
            </Pressable>
          </View>
          <Text style={styles.hint}>
            &ldquo;Go to Joseph.&rdquo; &middot; offer this work for someone you love
          </Text>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#15101F" },
  safe: { flex: 1, paddingHorizontal: spacing.lg },
  topRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingTop: spacing.xs,
  },
  iconBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(20,16,30,0.35)",
  },
  titleWrap: { marginTop: spacing.lg, alignItems: "center" },
  eyebrow: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: "#FFE6A8",
    letterSpacing: 2.5,
  },
  title: {
    fontFamily: fonts.headingBold,
    fontSize: 30,
    color: "#FFF8EA",
    textAlign: "center",
    marginTop: 6,
  },
  subtitle: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: "#E8E0D0",
    textAlign: "center",
    lineHeight: 21,
    marginTop: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  imgLoading: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: spacing.md },
  imgLoadingText: { fontFamily: fonts.bodyItalic, fontSize: 12, color: "#FFE6A8" },
  timerCard: {
    alignItems: "center",
    backgroundColor: "rgba(20,16,30,0.55)",
    borderRadius: 24,
    paddingVertical: spacing.lg,
    paddingHorizontal: spacing.xl,
    marginBottom: spacing.lg,
  },
  timerLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 2,
    color: "#FFE6A8",
  },
  timerTime: {
    fontFamily: fonts.headingBold,
    fontSize: 60,
    color: "#FFF8EA",
    marginVertical: spacing.xs,
    letterSpacing: 1,
  },
  timerBtnRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: spacing.xs },
  primaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "#FFE6A8",
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.sm + 4,
    borderRadius: 999,
  },
  primaryBtnText: { fontFamily: fonts.uiSemi, fontSize: 14, color: "#1A1326", letterSpacing: 0.3 },
  secondaryBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "rgba(255,248,234,0.4)",
  },
  hint: {
    fontFamily: fonts.bodyItalic,
    fontSize: 12,
    color: "#D8CFC0",
    marginTop: spacing.md,
    textAlign: "center",
  },
});

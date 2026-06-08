import React, { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import Animated, {
  Easing,
  cancelAnimation,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";

import { colors, fonts } from "@/src/theme";

/**
 * 4-7-8 breathing pattern — inhale 4s, hold 7s, exhale 8s.
 * The orb scales up during inhale, holds, then contracts during exhale.
 * Designed to lull, not to distract — animations are slow and steady.
 */

type Phase = "inhale" | "hold" | "exhale";

const PHASES: { name: Phase; label: string; duration: number; scale: number }[] = [
  { name: "inhale", label: "Breathe in",  duration: 4000, scale: 1.6 },
  { name: "hold",   label: "Hold",         duration: 7000, scale: 1.6 },
  { name: "exhale", label: "Breathe out",  duration: 8000, scale: 1.0 },
];

export interface BreathingGuideProps {
  active: boolean;          // when false, the orb stays at rest
  size?: number;            // diameter at rest, default 140
}

export default function BreathingGuide({ active, size = 140 }: BreathingGuideProps) {
  const scale = useSharedValue(1);
  const [phaseIdx, setPhaseIdx] = useState(0);
  const phaseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Drive a continuous loop of phases while `active`.
  useEffect(() => {
    const clear = () => {
      if (phaseTimerRef.current) {
        clearTimeout(phaseTimerRef.current);
        phaseTimerRef.current = null;
      }
    };
    if (!active) {
      clear();
      cancelAnimation(scale);
      scale.value = withTiming(1, { duration: 600, easing: Easing.inOut(Easing.ease) });
      setPhaseIdx(0);
      return clear;
    }
    let idx = 0;
    const step = () => {
      const phase = PHASES[idx];
      setPhaseIdx(idx);
      scale.value = withTiming(phase.scale, {
        duration: phase.duration,
        easing: Easing.inOut(Easing.ease),
      });
      phaseTimerRef.current = setTimeout(() => {
        idx = (idx + 1) % PHASES.length;
        step();
      }, phase.duration);
    };
    step();
    return clear;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  const orbStyle = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  const phase = PHASES[phaseIdx];

  return (
    <View style={styles.wrap} testID="breathing-guide">
      <View
        style={[
          styles.outerRing,
          { width: size * 1.8, height: size * 1.8, borderRadius: (size * 1.8) / 2 },
        ]}
      />
      <Animated.View
        style={[
          orbStyle,
          styles.orb,
          { width: size, height: size, borderRadius: size / 2 },
        ]}
      />
      <View style={styles.labelWrap} pointerEvents="none">
        <Text style={styles.label}>{active ? phase.label : "Tap play to begin"}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: "center",
    justifyContent: "center",
    height: 320,
    width: "100%",
  },
  outerRing: {
    position: "absolute",
    borderWidth: 1,
    borderColor: colors.gold,
    opacity: 0.25,
  },
  orb: {
    backgroundColor: colors.primary,
    opacity: 0.85,
    shadowColor: colors.gold,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.4,
    shadowRadius: 24,
    elevation: 8,
  },
  labelWrap: {
    position: "absolute",
    alignItems: "center",
    justifyContent: "center",
  },
  label: {
    fontFamily: fonts.headingSemi,
    fontSize: 20,
    color: colors.gold,
    letterSpacing: 1.2,
    textAlign: "center",
  },
});

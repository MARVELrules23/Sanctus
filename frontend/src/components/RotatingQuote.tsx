import React, { useEffect, useMemo, useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";

import { colors, fonts, spacing } from "@/src/theme";
import { SANCTUARY_QUOTES, SanctuaryQuote } from "@/src/utils/sanctuary-quotes";

/**
 * Cross-fades between scripture verses and saint quotes every ~25 s.
 * When `active` is false the rotation stops on the current line.
 */

const ROTATE_MS = 25_000;
const FADE_MS = 1200;

function shuffled<T>(arr: T[]): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

export interface RotatingQuoteProps {
  active: boolean;
}

export default function RotatingQuote({ active }: RotatingQuoteProps) {
  const order = useMemo<SanctuaryQuote[]>(() => shuffled(SANCTUARY_QUOTES), []);
  const [index, setIndex] = useState(0);
  const opacity = useSharedValue(1);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const clear = () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
    if (!active) {
      clear();
      return clear;
    }
    const tick = () => {
      // Fade out → swap → fade in
      opacity.value = withTiming(0, { duration: FADE_MS, easing: Easing.inOut(Easing.ease) });
      timerRef.current = setTimeout(() => {
        setIndex((i) => (i + 1) % order.length);
        opacity.value = withTiming(1, { duration: FADE_MS, easing: Easing.inOut(Easing.ease) });
        timerRef.current = setTimeout(tick, ROTATE_MS);
      }, FADE_MS);
    };
    timerRef.current = setTimeout(tick, ROTATE_MS);
    return clear;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, order.length]);

  const animStyle = useAnimatedStyle(() => ({ opacity: opacity.value }));
  const q = order[index];

  return (
    <Animated.View style={[styles.wrap, animStyle]} testID="rotating-quote">
      <Text style={styles.text}>&ldquo;{q.text}&rdquo;</Text>
      <Text style={styles.source}>— {q.source}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    alignItems: "center",
  },
  text: {
    fontFamily: fonts.bodyItalic,
    fontSize: 17,
    color: colors.textPrimary,
    lineHeight: 26,
    textAlign: "center",
  },
  source: {
    fontFamily: fonts.uiMedium,
    fontSize: 12,
    color: colors.textMuted,
    letterSpacing: 1,
    marginTop: spacing.sm,
    textTransform: "uppercase",
  },
});

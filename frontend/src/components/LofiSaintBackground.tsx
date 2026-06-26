/**
 * LofiSaintBackground — a calm, lo-fi animated backdrop for a companion saint.
 *
 * Shows the (AI-generated) saint illustration with a slow "Ken Burns" drift, a
 * gently pulsing golden halo glow, and drifting light motes — giving a living,
 * contemplative feel without heavy assets. Falls back to a soft gradient while
 * the image is still being generated.
 */
import React, { useEffect } from "react";
import { StyleSheet, View } from "react-native";
import { Image } from "expo-image";
import { LinearGradient } from "expo-linear-gradient";
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from "react-native-reanimated";

const AImage = Animated.createAnimatedComponent(Image);

function Mote({ delay, left, size }: { delay: number; left: string; size: number }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withRepeat(withTiming(1, { duration: 9000, easing: Easing.inOut(Easing.ease) }), -1, true);
  }, [t]);
  const style = useAnimatedStyle(() => ({
    opacity: 0.15 + t.value * 0.45,
    transform: [{ translateY: -t.value * 60 }, { scale: 0.8 + t.value * 0.6 }],
  }));
  return (
    <Animated.View
      pointerEvents="none"
      style={[
        styles.mote,
        { left: left as any, width: size, height: size, borderRadius: size / 2, animationDelay: `${delay}ms` } as any,
        style,
      ]}
    />
  );
}

export default function LofiSaintBackground({ image }: { image: string | null }) {
  const drift = useSharedValue(0);
  const glow = useSharedValue(0);

  useEffect(() => {
    drift.value = withRepeat(withTiming(1, { duration: 16000, easing: Easing.inOut(Easing.ease) }), -1, true);
    glow.value = withRepeat(withTiming(1, { duration: 4500, easing: Easing.inOut(Easing.ease) }), -1, true);
  }, [drift, glow]);

  const imgStyle = useAnimatedStyle(() => ({
    transform: [
      { scale: 1.08 + drift.value * 0.07 },
      { translateY: -drift.value * 14 },
      { translateX: (drift.value - 0.5) * 10 },
    ],
  }));
  const glowStyle = useAnimatedStyle(() => ({ opacity: 0.25 + glow.value * 0.4 }));

  return (
    <View style={styles.fill} pointerEvents="none">
      {image ? (
        <AImage source={{ uri: image }} style={[styles.fill, imgStyle]} contentFit="cover" transition={400} />
      ) : (
        <LinearGradient colors={["#2B2440", "#4A3A6B", "#6B5A8A"]} style={styles.fill} />
      )}

      {/* Soft golden halo glow that gently pulses */}
      <Animated.View style={[styles.glowWrap, glowStyle]}>
        <LinearGradient
          colors={["rgba(255,224,150,0.0)", "rgba(255,221,140,0.55)", "rgba(255,224,150,0.0)"]}
          start={{ x: 0.5, y: 0 }}
          end={{ x: 0.5, y: 1 }}
          style={styles.glow}
        />
      </Animated.View>

      {/* Drifting light motes */}
      <Mote delay={0} left="18%" size={6} />
      <Mote delay={2500} left="42%" size={4} />
      <Mote delay={1200} left="68%" size={7} />
      <Mote delay={3800} left="83%" size={5} />

      {/* Bottom-to-top scrim so text stays readable */}
      <LinearGradient
        colors={["rgba(20,16,30,0.15)", "rgba(20,16,30,0.55)", "rgba(20,16,30,0.92)"]}
        locations={[0, 0.45, 1]}
        style={styles.fill}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { ...StyleSheet.absoluteFillObject },
  glowWrap: { ...StyleSheet.absoluteFillObject, alignItems: "center", justifyContent: "flex-start" },
  glow: { position: "absolute", top: 30, width: 280, height: 280, borderRadius: 140 },
  mote: { position: "absolute", bottom: 40, backgroundColor: "rgba(255,236,180,0.9)" },
});

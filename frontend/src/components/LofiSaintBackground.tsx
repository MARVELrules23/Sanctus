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

function Mote({ delay, left, size, color }: { delay: number; left: string; size: number; color?: string }) {
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
        { left: left as any, width: size, height: size, borderRadius: size / 2, backgroundColor: color ?? "rgba(255,236,180,0.9)", animationDelay: `${delay}ms` } as any,
        style,
      ]}
    />
  );
}

/**
 * Sawdust drifting down through the workshop lamplight. Slow fall + slight
 * sideways sway, fading as it descends — like fine wood dust catching light.
 */
function Sawdust({ delay, left, size, duration }: { delay: number; left: string; size: number; duration: number }) {
  const t = useSharedValue(0);
  useEffect(() => {
    const id = setTimeout(() => {
      t.value = withRepeat(withTiming(1, { duration, easing: Easing.linear }), -1, false);
    }, delay);
    return () => clearTimeout(id);
  }, [t, duration, delay]);
  const style = useAnimatedStyle(() => ({
    opacity: 0.55 * Math.sin(Math.PI * t.value),
    transform: [
      { translateY: t.value * 220 },
      { translateX: Math.sin(t.value * Math.PI * 2) * 12 },
    ],
  }));
  return (
    <Animated.View
      pointerEvents="none"
      style={[
        styles.sawdust,
        { left: left as any, width: size, height: size, borderRadius: size / 2 } as any,
        style,
      ]}
    />
  );
}

type Variant = "saint" | "workshop";

export default function LofiSaintBackground({ image, variant = "saint" }: { image: string | null; variant?: Variant }) {
  const isWorkshop = variant === "workshop";
  const drift = useSharedValue(0);
  const glow = useSharedValue(0);
  const flicker = useSharedValue(0);

  useEffect(() => {
    drift.value = withRepeat(withTiming(1, { duration: 16000, easing: Easing.inOut(Easing.ease) }), -1, true);
    glow.value = withRepeat(withTiming(1, { duration: 4500, easing: Easing.inOut(Easing.ease) }), -1, true);
    // Fast, irregular flame flicker for the workshop lamp.
    flicker.value = withRepeat(withTiming(1, { duration: 140, easing: Easing.inOut(Easing.ease) }), -1, true);
  }, [drift, glow, flicker]);

  const imgStyle = useAnimatedStyle(() => ({
    transform: [
      { scale: 1.08 + drift.value * (isWorkshop ? 0.1 : 0.07) },
      { translateY: -drift.value * (isWorkshop ? 18 : 14) },
      { translateX: (drift.value - 0.5) * (isWorkshop ? 16 : 10) },
    ],
  }));
  // Workshop: warm lamp with a fast flame flicker layered on the slow pulse.
  const glowStyle = useAnimatedStyle(() =>
    isWorkshop
      ? { opacity: 0.3 + glow.value * 0.3 + flicker.value * 0.18 }
      : { opacity: 0.25 + glow.value * 0.4 }
  );

  return (
    <View style={styles.fill} pointerEvents="none">
      {image ? (
        <AImage source={{ uri: image }} style={[styles.fill, imgStyle]} contentFit="cover" transition={400} />
      ) : (
        <LinearGradient colors={isWorkshop ? ["#2A1E14", "#4A3320", "#6B4A2A"] : ["#2B2440", "#4A3A6B", "#6B5A8A"]} style={styles.fill} />
      )}

      {/* Warm candle/lamp glow (workshop) or golden halo (saint) that gently pulses */}
      <Animated.View style={[isWorkshop ? styles.lampWrap : styles.glowWrap, glowStyle]}>
        <LinearGradient
          colors={
            isWorkshop
              ? ["rgba(255,178,84,0.0)", "rgba(255,168,72,0.6)", "rgba(255,140,50,0.0)"]
              : ["rgba(255,224,150,0.0)", "rgba(255,221,140,0.55)", "rgba(255,224,150,0.0)"]
          }
          start={{ x: 0.5, y: 0 }}
          end={{ x: 0.5, y: 1 }}
          style={isWorkshop ? styles.lamp : styles.glow}
        />
      </Animated.View>

      {isWorkshop ? (
        <>
          {/* Fine sawdust drifting down through the lamplight */}
          <Sawdust delay={0} left="22%" size={3} duration={7000} />
          <Sawdust delay={1500} left="38%" size={2} duration={9000} />
          <Sawdust delay={3200} left="55%" size={3} duration={6500} />
          <Sawdust delay={800} left="70%" size={2} duration={8200} />
          <Sawdust delay={4200} left="84%" size={3} duration={7600} />
          <Sawdust delay={2400} left="12%" size={2} duration={9500} />
          {/* A couple of warm embers rising from the work */}
          <Mote delay={0} left="30%" size={5} color="rgba(255,170,90,0.9)" />
          <Mote delay={2600} left="63%" size={4} color="rgba(255,150,70,0.9)" />
        </>
      ) : (
        <>
          {/* Drifting light motes */}
          <Mote delay={0} left="18%" size={6} />
          <Mote delay={2500} left="42%" size={4} />
          <Mote delay={1200} left="68%" size={7} />
          <Mote delay={3800} left="83%" size={5} />
        </>
      )}

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
  lampWrap: { ...StyleSheet.absoluteFillObject, alignItems: "center", justifyContent: "center" },
  lamp: { position: "absolute", top: 90, width: 340, height: 340, borderRadius: 170 },
  mote: { position: "absolute", bottom: 40, backgroundColor: "rgba(255,236,180,0.9)" },
  sawdust: { position: "absolute", top: 60, backgroundColor: "rgba(255,214,150,0.95)" },
});

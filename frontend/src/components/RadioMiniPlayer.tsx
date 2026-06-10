/**
 * RadioMiniPlayer — persistent mini-player overlay.
 *
 * Renders absolutely positioned at the bottom of the screen whenever a
 * station is loaded in the global RadioPlayerContext. Anchors itself just
 * above the bottom tab bar on tab routes (so it never covers the tabs) and
 * sits right above the home-indicator safe-area inset on non-tab routes.
 *
 * Single-tap toggles play/pause. Right-side close button stops + clears.
 * Tap on the body deep-links to /library?tab=radio so the user can pick a
 * different station.
 */
import React from "react";
import { ActivityIndicator, Platform, Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter, useSegments } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useRadioPlayer } from "@/src/audio/RadioPlayerContext";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const TAB_BAR_BASE_HEIGHT = 64; // matches (tabs)/_layout.tsx → tabBarStyle.height base
const BOTTOM_GAP = 8; // breathing room above tabs / safe area

export default function RadioMiniPlayer() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const segments = useSegments();
  const { current, isPlaying, isBuffering, toggle, stop } = useRadioPlayer();

  if (!current) return null;

  // Detect: are we inside the bottom-tab navigator? expo-router exposes
  // segment groups in parentheses, so the first segment is "(tabs)" on tab
  // routes (vs. e.g. "library", "challenges", etc. on stack routes).
  const inTabs = segments[0] === "(tabs)";
  const bottomOffset =
    (inTabs ? TAB_BAR_BASE_HEIGHT + insets.bottom : insets.bottom) + BOTTOM_GAP;

  const accent = current.accent_color || colors.gold;

  return (
    <View
      pointerEvents="box-none"
      style={[styles.wrap, { bottom: bottomOffset }]}
      testID="radio-mini-player"
    >
      <Pressable
        onPress={() => router.push("/library?tab=radio")}
        style={({ pressed }) => [styles.card, pressed && { opacity: 0.92 }]}
        testID="radio-mini-open"
      >
        <View style={[styles.iconWrap, { backgroundColor: accent }]}>
          <Ionicons
            name={(current.icon as any) || "radio-outline"}
            size={18}
            color={colors.gold}
          />
        </View>
        <View style={{ flex: 1, paddingHorizontal: spacing.sm }}>
          <Text style={styles.title} numberOfLines={1}>
            {current.name}
          </Text>
          <Text style={styles.subtitle} numberOfLines={1}>
            {isBuffering
              ? "Buffering…"
              : isPlaying
                ? "Live · On air"
                : "Paused"}
          </Text>
        </View>
        <Pressable
          onPress={(e) => {
            e.stopPropagation();
            toggle();
          }}
          hitSlop={10}
          style={styles.iconBtn}
          testID="radio-mini-playpause"
        >
          {isBuffering ? (
            <ActivityIndicator size="small" color={colors.gold} />
          ) : (
            <Ionicons
              name={isPlaying ? "pause" : "play"}
              size={20}
              color={colors.gold}
            />
          )}
        </Pressable>
        <Pressable
          onPress={(e) => {
            e.stopPropagation();
            stop();
          }}
          hitSlop={10}
          style={styles.iconBtn}
          testID="radio-mini-close"
        >
          <Ionicons name="close" size={18} color={colors.textSecondary} />
        </Pressable>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: "absolute",
    left: spacing.md,
    right: spacing.md,
    zIndex: 1000,
    elevation: Platform.OS === "android" ? 12 : 0,
  },
  card: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    paddingVertical: 10,
    paddingHorizontal: 10,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  iconWrap: {
    width: 38,
    height: 38,
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
  },
  title: { fontFamily: fonts.bodyBold, fontSize: 13, color: colors.textPrimary },
  subtitle: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 2,
    letterSpacing: 0.3,
  },
  iconBtn: {
    width: 36,
    height: 36,
    alignItems: "center",
    justifyContent: "center",
    marginLeft: 4,
  },
});

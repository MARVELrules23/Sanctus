import React from "react";
import { Image, StyleSheet, Text, View } from "react-native";
import { colors, fonts } from "@/src/theme";

export function Avatar({
  name,
  picture,
  size = 40,
  testID,
}: {
  name?: string | null;
  picture?: string | null;
  size?: number;
  testID?: string;
}) {
  const initials = (name || "?")
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() || "")
    .join("") || "?";
  if (picture) {
    return (
      <Image
        testID={testID}
        source={{ uri: picture }}
        style={[styles.img, { width: size, height: size, borderRadius: size / 2 }]}
      />
    );
  }
  return (
    <View
      testID={testID}
      style={[
        styles.fallback,
        { width: size, height: size, borderRadius: size / 2 },
      ]}
    >
      <Text style={[styles.initials, { fontSize: Math.max(11, size * 0.4) }]}>{initials}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  img: { backgroundColor: colors.borderSoft },
  fallback: {
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  initials: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    letterSpacing: 0.5,
  },
});

export default Avatar;

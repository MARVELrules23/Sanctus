/**
 * LiturgicalBadge — pill showing season/feast color and label.
 */
import React from "react";
import { StyleSheet, View } from "react-native";

import { AutoText } from "@/src/auto-text";
import { colorForLiturgical, colors, fonts, radius, spacing } from "@/src/theme";

export function LiturgicalBadge({
  color,
  label,
  testID,
}: {
  color?: string;
  label: string;
  testID?: string;
}) {
  const c = colorForLiturgical(color);
  return (
    <View
      testID={testID}
      style={[
        styles.badge,
        { borderColor: c, backgroundColor: c + "14" },
      ]}
    >
      <View style={[styles.dot, { backgroundColor: c }]} />
      <AutoText style={[styles.label, { color: c }]}>{label.toUpperCase()}</AutoText>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: radius.round,
    borderWidth: 1,
    alignSelf: "flex-start",
    gap: spacing.xs + 2,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  label: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.1,
  },
});

export default LiturgicalBadge;

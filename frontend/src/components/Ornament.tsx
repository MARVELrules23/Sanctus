/**
 * Ornament — small gold flourish divider with central cross.
 */
import React from "react";
import { StyleSheet, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { colors, spacing } from "@/src/theme";

export function Ornament({ size = 14 }: { size?: number }) {
  return (
    <View style={styles.row}>
      <View style={styles.line} />
      <Ionicons name="diamond-outline" size={size} color={colors.gold} style={styles.icon} />
      <View style={styles.line} />
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: spacing.sm,
  },
  line: {
    flex: 1,
    height: 1,
    backgroundColor: colors.gold + "55",
  },
  icon: {
    marginHorizontal: spacing.md,
  },
});

export default Ornament;

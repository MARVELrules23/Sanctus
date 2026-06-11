/**
 * Tiny gold "unread count" badge used by the Inbox icon (and anywhere
 * else a glanceable count is needed). Renders nothing when count <= 0.
 *
 * Numbers above 99 collapse to "99+" to keep the pill compact.
 */
import React from "react";
import { StyleSheet, Text, View, ViewStyle } from "react-native";

import { colors, fonts } from "@/src/theme";

type Props = {
  count: number;
  /** Optional positioning override. Caller should make the parent
   *  view `position: "relative"` to receive an absolute badge. */
  style?: ViewStyle;
  testID?: string;
};

export function NotificationBadge({ count, style, testID }: Props) {
  if (!count || count <= 0) return null;
  const label = count > 99 ? "99+" : String(count);
  const isCompact = label.length === 1;
  return (
    <View
      pointerEvents="none"
      testID={testID || "notification-badge"}
      style={[
        styles.badge,
        isCompact ? styles.compact : styles.wide,
        style,
      ]}
    >
      <Text style={styles.text} numberOfLines={1}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    position: "absolute",
    top: -4,
    right: -6,
    backgroundColor: colors.gold,
    borderRadius: 999,
    minWidth: 18,
    height: 18,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 4,
    // Stand out against gold parent surfaces too.
    borderWidth: 1.5,
    borderColor: colors.surface,
  },
  compact: { width: 18, paddingHorizontal: 0 },
  wide: { minWidth: 22 },
  text: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    lineHeight: 12,
    color: colors.primary,
    letterSpacing: 0.2,
    textAlign: "center",
  },
});

import React from "react";
import { Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { BookmarkInput } from "@/src/api";
import { useBookmarks } from "@/src/bookmarks-context";
import { colors } from "@/src/theme";

/**
 * Reusable bookmark toggle. Reads/writes through BookmarksProvider so state
 * stays consistent across screens and the Profile "Saved" section.
 */
export default function BookmarkButton({
  input,
  size = 22,
  testID,
  activeColor = colors.gold,
  inactiveColor = colors.primary,
}: {
  input: BookmarkInput;
  size?: number;
  testID?: string;
  activeColor?: string;
  inactiveColor?: string;
}) {
  const { isBookmarked, toggle } = useBookmarks();
  const active = isBookmarked(input.kind, input.ref_id);
  return (
    <Pressable
      testID={testID ?? `bookmark-${input.kind}-${input.ref_id}`}
      onPress={() => toggle(input)}
      hitSlop={10}
      style={({ pressed }) => [styles.btn, pressed && styles.pressed]}
      accessibilityLabel={active ? "Remove bookmark" : "Add bookmark"}
    >
      <Ionicons
        name={active ? "bookmark" : "bookmark-outline"}
        size={size}
        color={active ? activeColor : inactiveColor}
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  btn: { padding: 4 },
  pressed: { opacity: 0.6 },
});

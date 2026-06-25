import React from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { colors, fonts, radius, spacing } from "@/src/theme";
import type { GoalMode } from "@/src/api";

type Props = {
  value: GoalMode;
  onChange: (m: GoalMode) => void;
  testID?: string;
  goalsDisabled?: boolean; // shown but if pressed will hint user to set wellness profile
  onGoalsDisabledPress?: () => void;
};

export default function GoalModeToggle({ value, onChange, testID, goalsDisabled, onGoalsDisabledPress }: Props) {
  const tap = (mode: GoalMode) => {
    if (mode === "goals" && goalsDisabled) {
      onGoalsDisabledPress?.();
      return;
    }
    onChange(mode);
  };
  return (
    <View style={styles.row} testID={testID}>
      <Pressable
        testID={`${testID}-liturgical`}
        onPress={() => tap("liturgical")}
        style={[styles.pill, value === "liturgical" && styles.pillActive]}
        accessibilityRole="button"
        accessibilityState={{ selected: value === "liturgical" }}
      >
        <Ionicons
          name="flower-outline"
          size={13}
          color={value === "liturgical" ? colors.gold : colors.textMuted}
        />
        <Text style={[styles.pillText, value === "liturgical" && styles.pillTextActive]}>
          Liturgical season
        </Text>
      </Pressable>
      <Pressable
        testID={`${testID}-goals`}
        onPress={() => tap("goals")}
        style={[
          styles.pill,
          value === "goals" && styles.pillActive,
          goalsDisabled && styles.pillDisabled,
        ]}
        accessibilityRole="button"
        accessibilityState={{ selected: value === "goals", disabled: !!goalsDisabled }}
      >
        <Ionicons
          name="trending-up-outline"
          size={13}
          color={
            value === "goals"
              ? colors.gold
              : goalsDisabled
              ? colors.border
              : colors.textMuted
          }
        />
        <Text
          style={[
            styles.pillText,
            value === "goals" && styles.pillTextActive,
            goalsDisabled && styles.pillTextDisabled,
          ]}
        >
          My goals
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignSelf: "center",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.round,
    padding: 3,
    gap: 2,
  },
  pill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderRadius: radius.round,
  },
  pillActive: { backgroundColor: colors.primary },
  pillDisabled: { opacity: 0.5 },
  pillText: {
    fontFamily: fonts.uiMedium,
    fontSize: 12,
    color: colors.textMuted,
    letterSpacing: 0.2,
  },
  pillTextActive: { color: colors.gold },
  pillTextDisabled: { color: colors.textMuted },
});

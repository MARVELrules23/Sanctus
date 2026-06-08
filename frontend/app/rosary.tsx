import React, { useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { fullRosary, mysteryForDate, MYSTERY_SETS, MysterySet } from "@/src/rosary";
import { parseISO, todayISO } from "@/src/date-utils";

export default function RosaryScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ date?: string; season?: string }>();
  const initialDate = params.date && typeof params.date === "string" ? params.date : todayISO();
  const initialSeason = typeof params.season === "string" ? params.season : undefined;

  const initialSet = useMemo(() => mysteryForDate(parseISO(initialDate), initialSeason), [initialDate, initialSeason]);
  const [setKey, setSetKey] = useState<MysterySet["key"]>(initialSet.key);
  const set = MYSTERY_SETS[setKey];
  const steps = useMemo(() => fullRosary(set), [set]);
  const [idx, setIdx] = useState(0);

  const step = steps[idx];
  const isLast = idx === steps.length - 1;
  const progress = ((idx + 1) / steps.length) * 100;

  // Count Hail Marys completed in current decade (visible bead row).
  const hailMaryCountInDecade = useMemo(() => {
    const decadeStart = (() => {
      // Find last bead that starts with "1. " or "2. " etc. (mystery announcement)
      let j = idx;
      while (j >= 0 && !/^[1-5]\. /.test(steps[j].label)) j--;
      return j;
    })();
    if (decadeStart < 0) return null;
    let count = 0;
    for (let i = decadeStart; i <= idx; i++) {
      if (steps[i].label.startsWith("Hail Mary")) count++;
    }
    const inDecade = idx > decadeStart && idx < decadeStart + 13;
    return inDecade ? count : null;
  }, [idx, steps]);

  return (
    <View style={styles.root} testID="rosary-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        {/* Header */}
        <View style={styles.headerRow}>
          <Pressable testID="rosary-close" onPress={() => router.back()} hitSlop={12} style={({ pressed }) => pressed && styles.pressed}>
            <Ionicons name="close" size={26} color={colors.gold} />
          </Pressable>
          <Text style={styles.headerTitle}>Holy Rosary</Text>
          <View style={{ width: 26 }} />
        </View>

        {/* Mystery selector */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.mysteryRow}
        >
          {(Object.keys(MYSTERY_SETS) as MysterySet["key"][]).map((k) => {
            const s = MYSTERY_SETS[k];
            const sel = k === setKey;
            return (
              <Pressable
                key={k}
                testID={`rosary-set-${k}`}
                onPress={() => {
                  setSetKey(k);
                  setIdx(0);
                }}
                style={[styles.mysteryChip, sel && { backgroundColor: s.color, borderColor: s.color }]}
              >
                <Text style={[styles.mysteryChipText, sel && styles.mysteryChipTextSel]}>{s.title.split(" ")[0]}</Text>
              </Pressable>
            );
          })}
        </ScrollView>

        {/* Progress bar */}
        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${progress}%`, backgroundColor: set.color }]} />
        </View>
        <Text style={styles.progressText}>
          Bead {idx + 1} of {steps.length}
        </Text>

        {/* Current step */}
        <View style={styles.stepCard} testID="rosary-step">
          <View style={[styles.beadIndicator, { backgroundColor: set.color + "22", borderColor: set.color }]}>
            <Ionicons name="ellipse" size={14} color={set.color} />
          </View>
          <Text style={styles.stepLabel}>{step.label}</Text>
          <ScrollView style={styles.stepScroll} contentContainerStyle={{ paddingBottom: spacing.md }}>
            <Text style={styles.stepText}>{step.prayer}</Text>
          </ScrollView>
          {hailMaryCountInDecade !== null && (
            <View style={styles.beadCounter}>
              {Array.from({ length: 10 }).map((_, i) => (
                <View
                  key={i}
                  style={[
                    styles.bead,
                    i < hailMaryCountInDecade && { backgroundColor: set.color, borderColor: set.color },
                  ]}
                />
              ))}
            </View>
          )}
        </View>

        {/* Controls */}
        <View style={styles.controls}>
          <Pressable
            testID="rosary-prev"
            onPress={() => setIdx(Math.max(0, idx - 1))}
            disabled={idx === 0}
            style={({ pressed }) => [styles.controlBtn, pressed && styles.pressed, idx === 0 && styles.controlDisabled]}
          >
            <Ionicons name="chevron-back" size={22} color={colors.primary} />
            <Text style={styles.controlText}>Prev</Text>
          </Pressable>
          <Pressable
            testID="rosary-next"
            onPress={() => {
              if (isLast) router.back();
              else setIdx(idx + 1);
            }}
            style={({ pressed }) => [styles.controlBtnPrimary, pressed && styles.pressed]}
          >
            <Text style={styles.controlBtnPrimaryText}>{isLast ? "Amen — Finish" : "Next Bead"}</Text>
            <Ionicons name={isLast ? "checkmark" : "chevron-forward"} size={20} color={colors.gold} />
          </Pressable>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.primary },
  safe: { flex: 1, paddingHorizontal: spacing.lg },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: spacing.md },
  headerTitle: { fontFamily: fonts.headingBold, color: colors.gold, fontSize: 22, letterSpacing: 1 },
  mysteryRow: { gap: spacing.sm, paddingVertical: spacing.sm, paddingRight: spacing.md },
  mysteryChip: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: "#3A4A6A",
    backgroundColor: "rgba(255,255,255,0.04)",
    flexShrink: 0,
    height: 36,
    justifyContent: "center",
  },
  mysteryChipText: { fontFamily: fonts.uiSemi, color: "#D8D2C0", fontSize: 12, letterSpacing: 0.8 },
  mysteryChipTextSel: { color: "#FAF9F6" },
  progressBar: { height: 3, backgroundColor: "rgba(255,255,255,0.1)", borderRadius: 2, marginTop: spacing.sm },
  progressFill: { height: 3, borderRadius: 2 },
  progressText: { fontFamily: fonts.uiMedium, color: "#D8D2C0", fontSize: 12, marginTop: spacing.xs, textAlign: "center" },
  stepCard: {
    flex: 1,
    backgroundColor: "#FAF9F6",
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginTop: spacing.md,
    ...shadow.card,
    alignItems: "center",
  },
  beadIndicator: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 1.5,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.md,
  },
  stepLabel: {
    fontFamily: fonts.headingBold,
    fontSize: 26,
    color: colors.textPrimary,
    textAlign: "center",
    marginBottom: spacing.md,
    lineHeight: 32,
  },
  stepScroll: { flex: 1, width: "100%" },
  stepText: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textSecondary,
    fontSize: 17,
    lineHeight: 28,
    textAlign: "center",
  },
  beadCounter: {
    flexDirection: "row",
    gap: 6,
    marginTop: spacing.md,
  },
  bead: {
    width: 16,
    height: 16,
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: "#D4D0C4",
    backgroundColor: "transparent",
  },
  controls: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.md, paddingBottom: spacing.sm },
  controlBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
    paddingVertical: 14,
    paddingHorizontal: 18,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: "#D4D0C4",
    backgroundColor: "#FAF9F6",
  },
  controlText: { fontFamily: fonts.uiSemi, color: colors.primary, fontSize: 14 },
  controlBtnPrimary: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    paddingVertical: 14,
    borderRadius: radius.md,
    backgroundColor: colors.primary,
    borderWidth: 1,
    borderColor: colors.gold,
  },
  controlBtnPrimaryText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 15, letterSpacing: 0.5 },
  controlDisabled: { opacity: 0.5 },
  pressed: { opacity: 0.7 },
});

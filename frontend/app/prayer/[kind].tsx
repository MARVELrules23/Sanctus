import React, { useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { BeadStep, fullRosary, mysteryForDate, MYSTERY_SETS, MysterySet } from "@/src/rosary";
import { CHAPLETS, ChapletKey } from "@/src/prayers/chaplets";
import { parseISO, todayISO } from "@/src/date-utils";
import { useI18n } from "@/src/i18n";
import { useTranslator } from "@/src/translate";

type PrayerMeta = {
  title: string;
  color: string;
  steps: BeadStep[];
  good_work: string;
  motto: string;
  note?: string;
  mysterySwitcher?: {
    current: MysterySet["key"];
    setCurrent: (k: MysterySet["key"]) => void;
  };
};

export default function PrayerRunnerScreen() {
  const router = useRouter();
  const { lang } = useI18n();
  const es = lang === "es";
  const it = lang === "it";
  const params = useLocalSearchParams<{ kind?: string; date?: string; season?: string }>();
  const kind = String(params.kind || "rosary");
  const initialDate = params.date && typeof params.date === "string" ? params.date : todayISO();
  const initialSeason = typeof params.season === "string" ? params.season : undefined;

  const initialSet = useMemo(
    () => mysteryForDate(parseISO(initialDate), initialSeason),
    [initialDate, initialSeason],
  );
  const [rosarySetKey, setRosarySetKey] = useState<MysterySet["key"]>(initialSet.key);

  const meta: PrayerMeta = useMemo(() => {
    if (kind === "rosary") {
      const set = MYSTERY_SETS[rosarySetKey];
      return {
        title: "Holy Rosary",
        color: set.color,
        steps: fullRosary(set),
        good_work: set.good_work_for_today,
        motto: set.daily_motto,
        mysterySwitcher: { current: rosarySetKey, setCurrent: setRosarySetKey },
      };
    }
    const ch = CHAPLETS[kind as ChapletKey];
    if (!ch) {
      return { title: "Prayer not found", color: colors.gold, steps: [], good_work: "", motto: "" };
    }
    return {
      title: ch.title,
      color: ch.color,
      steps: ch.steps,
      good_work: ch.good_work_for_today,
      motto: ch.daily_motto,
      note: ch.note,
    };
  }, [kind, rosarySetKey]);

  // Collect every user-visible prayer string for batch translation (es only).
  const allStrings = useMemo(() => {
    const arr = [meta.title, meta.good_work, meta.motto];
    if (meta.note) arr.push(meta.note);
    meta.steps.forEach((s) => { arr.push(s.label, s.prayer); });
    Object.values(MYSTERY_SETS).forEach((s) => arr.push(s.title));
    return arr;
  }, [meta]);
  const { tr } = useTranslator(allStrings);

  const ui = {
    goodWork: es ? "Buena obra para hoy" : it ? "Buona opera per oggi" : "Good work for today",
    goodWorkUpper: es ? "BUENA OBRA PARA HOY" : it ? "BUONA OPERA PER OGGI" : "GOOD WORK FOR TODAY",
    bead: (i: number, t: number) =>
      es ? `Cuenta ${i} de ${t}` : it ? `Grano ${i} di ${t}` : `Bead ${i} of ${t}`,
    prev: es ? "Atrás" : it ? "Indietro" : "Prev",
    nextBead: es ? "Siguiente" : it ? "Avanti" : "Next Bead",
    amenContinue: es ? "Amén — Continuar" : it ? "Amen — Continua" : "Amen — Continue",
    journalThis: es ? "Anotar en el diario" : it ? "Annota nel diario" : "Journal this",
    amenDone: es ? "Amén — Hecho" : it ? "Amen — Fatto" : "Amen — Done",
  };

  const [idx, setIdx] = useState(0);
  const total = meta.steps.length;
  const onClosing = idx >= total;
  const step = onClosing ? null : meta.steps[idx];
  const progressPct = total === 0 ? 100 : Math.min(100, ((idx + 1) / (total + 1)) * 100);

  const hailMaryCountInDecade = useMemo(() => {
    if (kind !== "rosary" || onClosing) return null;
    const stepsArr = meta.steps;
    let j = idx;
    while (j >= 0 && !/^[1-5]\. /.test(stepsArr[j].label)) j--;
    if (j < 0) return null;
    let count = 0;
    for (let i = j; i <= idx; i++) {
      if (stepsArr[i].label.startsWith("Hail Mary")) count++;
    }
    const inDecade = idx > j && idx < j + 13;
    return inDecade ? count : null;
  }, [idx, meta.steps, kind, onClosing]);

  const isLast = idx === total - 1;

  return (
    <View style={styles.root} testID="prayer-runner-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <View style={styles.headerRow}>
          <Pressable testID="prayer-close" onPress={() => router.back()} hitSlop={12} style={({ pressed }) => pressed && styles.pressed}>
            <Ionicons name="close" size={26} color={colors.gold} />
          </Pressable>
          <Text style={styles.headerTitle} numberOfLines={1}>{tr(meta.title)}</Text>
          <View style={{ width: 26 }} />
        </View>

        {meta.note && idx === 0 && !onClosing ? (
          <View style={[styles.noteCallout, { borderLeftColor: meta.color, backgroundColor: meta.color + "12" }]} testID="prayer-note">
            <Ionicons name="information-circle" size={16} color={meta.color} style={{ marginTop: 1 }} />
            <Text style={styles.noteText}>{tr(meta.note)}</Text>
          </View>
        ) : null}

        {meta.mysterySwitcher ? (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.mysteryRow}>
            {(Object.keys(MYSTERY_SETS) as MysterySet["key"][]).map((k) => {
              const s = MYSTERY_SETS[k];
              const sel = k === meta.mysterySwitcher!.current;
              const chipLabel = es
                ? (tr(s.title).split(" ").slice(1).join(" ") || tr(s.title))
                : s.title.split(" ")[0];
              return (
                <Pressable
                  key={k}
                  testID={`prayer-rosary-set-${k}`}
                  onPress={() => { meta.mysterySwitcher!.setCurrent(k); setIdx(0); }}
                  style={[styles.mysteryChip, sel && { backgroundColor: s.color, borderColor: s.color }]}
                >
                  <Text style={[styles.mysteryChipText, sel && styles.mysteryChipTextSel]}>{chipLabel}</Text>
                </Pressable>
              );
            })}
          </ScrollView>
        ) : null}

        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${progressPct}%`, backgroundColor: meta.color }]} />
        </View>
        <Text style={styles.progressText}>
          {onClosing ? ui.goodWork : ui.bead(idx + 1, total)}
        </Text>

        {onClosing ? (
          <View style={styles.stepCard} testID="prayer-good-work">
            <View style={[styles.beadIndicator, { backgroundColor: meta.color + "22", borderColor: meta.color }]}>
              <Ionicons name="sparkles" size={16} color={meta.color} />
            </View>
            <Text style={styles.eyebrow}>{ui.goodWorkUpper}</Text>
            <ScrollView style={styles.stepScroll} contentContainerStyle={{ paddingBottom: spacing.md }}>
              <Text style={styles.goodWorkText}>{tr(meta.good_work)}</Text>
              {meta.motto ? (
                <View style={styles.mottoBox}>
                  <Ionicons name="bookmark" size={12} color={meta.color} />
                  <Text style={styles.mottoText}>{tr(meta.motto)}</Text>
                </View>
              ) : null}
            </ScrollView>
          </View>
        ) : step ? (
          <View style={styles.stepCard} testID="prayer-step">
            <View style={[styles.beadIndicator, { backgroundColor: meta.color + "22", borderColor: meta.color }]}>
              <Ionicons name="ellipse" size={14} color={meta.color} />
            </View>
            <Text style={styles.stepLabel}>{tr(step.label)}</Text>
            <ScrollView style={styles.stepScroll} contentContainerStyle={{ paddingBottom: spacing.md }}>
              <Text style={styles.stepText}>{tr(step.prayer)}</Text>
            </ScrollView>
            {hailMaryCountInDecade !== null && (
              <View style={styles.beadCounter}>
                {Array.from({ length: 10 }).map((_, i) => (
                  <View key={i} style={[styles.bead, i < hailMaryCountInDecade && { backgroundColor: meta.color, borderColor: meta.color }]} />
                ))}
              </View>
            )}
          </View>
        ) : null}

        <View style={styles.controls}>
          {onClosing ? (
            <>
              <Pressable
                testID="prayer-journal"
                onPress={() =>
                  router.replace({
                    pathname: "/journal",
                    params: {
                      date: todayISO(),
                      mode: "free",
                      seed_title: tr(meta.title),
                      seed_body: `${tr(meta.title)} — ${es ? "completado hoy" : "completed today"}.\n\n${ui.goodWork}: ${tr(meta.good_work)}\n\n${es ? "Reflexión" : "Reflection"}:\n`,
                    },
                  })
                }
                style={({ pressed }) => [styles.controlBtn, pressed && styles.pressed, { flex: 1 }]}
              >
                <Ionicons name="create-outline" size={18} color={colors.primary} />
                <Text style={styles.controlText}>{ui.journalThis}</Text>
              </Pressable>
              <Pressable testID="prayer-done" onPress={() => router.back()} style={({ pressed }) => [styles.controlBtnPrimary, pressed && styles.pressed]}>
                <Text style={styles.controlBtnPrimaryText}>{ui.amenDone}</Text>
                <Ionicons name="checkmark" size={20} color={colors.gold} />
              </Pressable>
            </>
          ) : (
            <>
              <Pressable
                testID="prayer-prev"
                onPress={() => setIdx(Math.max(0, idx - 1))}
                disabled={idx === 0}
                style={({ pressed }) => [styles.controlBtn, pressed && styles.pressed, idx === 0 && styles.controlDisabled]}
              >
                <Ionicons name="chevron-back" size={22} color={colors.primary} />
                <Text style={styles.controlText}>{ui.prev}</Text>
              </Pressable>
              <Pressable
                testID="prayer-next"
                onPress={() => { if (isLast) setIdx(total); else setIdx(idx + 1); }}
                style={({ pressed }) => [styles.controlBtnPrimary, pressed && styles.pressed]}
              >
                <Text style={styles.controlBtnPrimaryText}>{isLast ? ui.amenContinue : ui.nextBead}</Text>
                <Ionicons name={isLast ? "sparkles" : "chevron-forward"} size={20} color={colors.gold} />
              </Pressable>
            </>
          )}
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.primary },
  safe: { flex: 1, paddingHorizontal: spacing.lg },
  headerRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: spacing.md, gap: spacing.sm },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingBold, color: colors.gold, fontSize: 18, letterSpacing: 0.5 },
  mysteryRow: { gap: spacing.sm, paddingVertical: spacing.sm, paddingRight: spacing.md },
  mysteryChip: {
    paddingVertical: 8, paddingHorizontal: 14, borderRadius: radius.round, borderWidth: 1,
    borderColor: "#3A4A6A", backgroundColor: "rgba(255,255,255,0.04)", flexShrink: 0, height: 36, justifyContent: "center",
  },
  mysteryChipText: { fontFamily: fonts.uiSemi, color: "#D8D2C0", fontSize: 12, letterSpacing: 0.8 },
  mysteryChipTextSel: { color: "#FAF9F6" },
  progressBar: { height: 3, backgroundColor: "rgba(255,255,255,0.1)", borderRadius: 2, marginTop: spacing.sm },
  progressFill: { height: 3, borderRadius: 2 },
  progressText: { fontFamily: fonts.uiMedium, color: "#D8D2C0", fontSize: 12, marginTop: spacing.xs, textAlign: "center" },
  stepCard: { flex: 1, backgroundColor: "#FAF9F6", borderRadius: radius.lg, padding: spacing.lg, marginTop: spacing.md, ...shadow.card, alignItems: "center" },
  beadIndicator: { width: 40, height: 40, borderRadius: 20, borderWidth: 1.5, alignItems: "center", justifyContent: "center", marginBottom: spacing.md },
  eyebrow: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.gold, letterSpacing: 2, marginBottom: spacing.sm },
  stepLabel: { fontFamily: fonts.headingBold, fontSize: 24, color: colors.textPrimary, textAlign: "center", marginBottom: spacing.md, lineHeight: 30 },
  stepScroll: { flex: 1, width: "100%" },
  stepText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textSecondary, fontSize: 17, lineHeight: 28, textAlign: "center" },
  goodWorkText: { fontFamily: fonts.bodyRegular, color: colors.textPrimary, fontSize: 18, lineHeight: 30, textAlign: "center" },
  mottoBox: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, marginTop: spacing.lg, paddingTop: spacing.md, borderTopWidth: 1, borderTopColor: "#EAE5D6" },
  mottoText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 14, color: colors.textSecondary, textAlign: "center" },
  noteCallout: { flexDirection: "row", alignItems: "flex-start", gap: 8, marginHorizontal: spacing.lg, marginBottom: spacing.sm, paddingVertical: spacing.sm, paddingHorizontal: spacing.md, borderRadius: 12, borderLeftWidth: 3 },
  noteText: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 13, lineHeight: 19, color: colors.textSecondary },
  beadCounter: { flexDirection: "row", gap: 6, marginTop: spacing.md },
  bead: { width: 16, height: 16, borderRadius: 8, borderWidth: 1.5, borderColor: "#D4D0C4", backgroundColor: "transparent" },
  controls: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.md, paddingBottom: spacing.sm },
  controlBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 4, paddingVertical: 14, paddingHorizontal: 18, borderRadius: radius.md, borderWidth: 1, borderColor: "#D4D0C4", backgroundColor: "#FAF9F6" },
  controlText: { fontFamily: fonts.uiSemi, color: colors.primary, fontSize: 14 },
  controlBtnPrimary: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, paddingVertical: 14, borderRadius: radius.md, backgroundColor: colors.primary, borderWidth: 1, borderColor: colors.gold },
  controlBtnPrimaryText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 15, letterSpacing: 0.5 },
  controlDisabled: { opacity: 0.5 },
  pressed: { opacity: 0.7 },
});

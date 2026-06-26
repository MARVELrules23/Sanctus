import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import {
  getConsecration, startConsecration, stopConsecration, completeConsecrationDay,
  getConsecrationDay, ConsecrationOverview, ConsecrationActive, ConsecrationDayContent,
} from "@/src/api";
import { todayISO } from "@/src/date-utils";
import { colors, fonts, radius, spacing } from "@/src/theme";

export default function ConsecrationScreen() {
  const router = useRouter();
  const [ov, setOv] = useState<ConsecrationOverview | null>(null);
  const [active, setActive] = useState<ConsecrationActive>(null);
  const [day, setDay] = useState<ConsecrationDayContent | null>(null);
  const [viewDay, setViewDay] = useState(1);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const o = await getConsecration();
      setOv(o);
      setActive(o.active);
      setViewDay(o.active?.current_day || 1);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const loadDay = useCallback(async (d: number) => {
    try { setDay(await getConsecrationDay(d)); } catch {/* ignore */}
  }, []);
  useEffect(() => { if (active) loadDay(viewDay); }, [active, viewDay, loadDay]);

  const begin = async () => {
    setBusy(true);
    try {
      const r = await startConsecration(todayISO());
      setActive(r.active);
      setViewDay(1);
    } finally { setBusy(false); }
  };

  const markDone = async () => {
    if (!active) return;
    setBusy(true);
    try {
      const r = await completeConsecrationDay(viewDay);
      if (r.status === "completed") { await load(); }
      else { setActive(r.active); if (viewDay < (r.active?.total_days || 33)) setViewDay(viewDay + 1); }
    } finally { setBusy(false); }
  };

  const reset = async () => { setBusy(true); try { await stopConsecration(); setActive(null); setDay(null); } finally { setBusy(false); } };

  const completed = active?.completed_days || [];
  const dayDone = completed.includes(viewDay);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="consecration-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="consec-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle} numberOfLines={1}>St. Joseph Consecration</Text>
        <View style={{ width: 26 }} />
      </View>

      {loading || !ov ? (
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      ) : !active ? (
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <Text style={styles.bigTitle}>{ov.title}</Text>
          <Text style={styles.intro}>{ov.intro}</Text>

          <Pressable testID="consec-begin" onPress={begin} disabled={busy}
            style={({ pressed }) => [styles.beginBtn, pressed && { opacity: 0.9 }]}>
            {busy ? <ActivityIndicator color="#FFF8EA" /> : (
              <>
                <Ionicons name="play-circle-outline" size={20} color="#FFF8EA" />
                <Text style={styles.beginBtnText}>Begin today ({ov.total_days} days)</Text>
              </>
            )}
          </Pressable>

          <View style={styles.cardHead}><Ionicons name="calendar-outline" size={16} color={colors.gold} />
            <Text style={styles.cardHeadText}>Traditional start dates</Text></View>
          <Text style={styles.note}>Begin on a set date so the final day lands on a feast of St. Joseph — or simply start today.</Text>
          {ov.set_times.map((s, i) => (
            <View key={i} style={styles.setRow}>
              <Ionicons name="ellipse" size={8} color={colors.gold} />
              <Text style={styles.setText}>Start {s.start.replace("-", "/")} → {s.feast}</Text>
            </View>
          ))}

          <View style={styles.cardHead}><Ionicons name="list-outline" size={16} color={colors.gold} />
            <Text style={styles.cardHeadText}>The 33 days</Text></View>
          {ov.days.map((d) => (
            <View key={d.day} style={styles.dayRow}>
              <Text style={styles.dayNum}>{d.day}</Text>
              <View style={{ flex: 1 }}>
                <Text style={styles.dayTitle}>{d.title}</Text>
                <Text style={styles.dayTheme}>{d.theme}</Text>
              </View>
            </View>
          ))}
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          {/* Progress */}
          <View style={styles.progressCard}>
            <Text style={styles.progressText}>Day {viewDay} of {active.total_days}</Text>
            <Text style={styles.progressSub}>{completed.length} days completed · started {active.start_date}</Text>
            <View style={styles.dayNav}>
              <Pressable disabled={viewDay <= 1} onPress={() => setViewDay(viewDay - 1)} style={styles.navBtn}>
                <Ionicons name="chevron-back" size={18} color={viewDay <= 1 ? colors.textMuted : colors.primary} />
              </Pressable>
              <Pressable disabled={viewDay >= active.total_days} onPress={() => setViewDay(viewDay + 1)} style={styles.navBtn}>
                <Ionicons name="chevron-forward" size={18} color={viewDay >= active.total_days ? colors.textMuted : colors.primary} />
              </Pressable>
            </View>
          </View>

          {day ? (
            <>
              <Text style={styles.bigTitle}>{day.title}</Text>
              <Text style={styles.theme}>{day.theme}</Text>
              <Text style={styles.meditation}>{day.meditation}</Text>

              <View style={styles.cardHead}><Ionicons name="book-outline" size={16} color={colors.gold} />
                <Text style={styles.cardHeadText}>Daily prayer</Text></View>
              <Text style={styles.prayer}>{day.daily_prayer}</Text>

              {day.act_of_consecration ? (
                <View style={styles.actBox}>
                  <View style={styles.cardHead}><Ionicons name="ribbon-outline" size={16} color={colors.gold} />
                    <Text style={styles.cardHeadText}>Act of Consecration</Text></View>
                  <Text style={styles.prayer}>{day.act_of_consecration}</Text>
                </View>
              ) : null}

              <Pressable testID="consec-complete" onPress={markDone} disabled={busy || dayDone}
                style={({ pressed }) => [styles.beginBtn, dayDone && styles.doneBtn, pressed && { opacity: 0.9 }]}>
                {busy ? <ActivityIndicator color="#FFF8EA" /> : (
                  <>
                    <Ionicons name={dayDone ? "checkmark-circle" : "checkmark-circle-outline"} size={20} color="#FFF8EA" />
                    <Text style={styles.beginBtnText}>{dayDone ? "Day completed" : "Mark day complete"}</Text>
                  </>
                )}
              </Pressable>
            </>
          ) : <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />}

          <Pressable onPress={reset} disabled={busy} style={styles.resetBtn}>
            <Text style={styles.resetText}>Restart / stop consecration</Text>
          </Pressable>
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingSemi, fontSize: 18, color: colors.primary, marginHorizontal: spacing.sm },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  scroll: { padding: spacing.lg },
  bigTitle: { fontFamily: fonts.headingBold, fontSize: 24, color: colors.primary, marginBottom: 6 },
  intro: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textSecondary, lineHeight: 23 },
  theme: { fontFamily: fonts.bodyItalic, fontSize: 14, color: colors.goldDark, marginBottom: spacing.sm },
  meditation: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textSecondary, lineHeight: 24 },
  beginBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, backgroundColor: colors.primary, borderRadius: radius.md, padding: spacing.md, marginTop: spacing.lg },
  doneBtn: { backgroundColor: "#5B8A5B" },
  beginBtnText: { fontFamily: fonts.uiSemi, fontSize: 15, color: "#FFF8EA" },
  cardHead: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: spacing.lg, marginBottom: spacing.sm },
  cardHeadText: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 0.6, textTransform: "uppercase", color: colors.gold },
  note: { fontFamily: fonts.bodyItalic, fontSize: 13, color: colors.textMuted, marginBottom: spacing.sm, lineHeight: 19 },
  setRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 6 },
  setText: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, flex: 1 },
  dayRow: { flexDirection: "row", gap: 10, alignItems: "flex-start", marginBottom: spacing.sm },
  dayNum: { fontFamily: fonts.headingBold, fontSize: 14, color: colors.gold, width: 22 },
  dayTitle: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.primary },
  dayTheme: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textSecondary, marginTop: 1 },
  progressCard: { backgroundColor: colors.surfaceDark, borderRadius: radius.lg, padding: spacing.md, flexDirection: "row", alignItems: "center" },
  progressText: { fontFamily: fonts.headingSemi, fontSize: 17, color: "#FBF6E9" },
  progressSub: { fontFamily: fonts.bodyRegular, fontSize: 12, color: "#D8CFBC", marginTop: 2, flex: 1 },
  dayNav: { flexDirection: "row", gap: 6 },
  navBtn: { width: 34, height: 34, borderRadius: 17, backgroundColor: "rgba(255,255,255,0.12)", alignItems: "center", justifyContent: "center" },
  prayer: { fontFamily: fonts.bodyRegular, fontSize: 14.5, color: colors.textSecondary, lineHeight: 23, fontStyle: "italic" },
  actBox: { backgroundColor: "#FBF4DF", borderWidth: 1, borderColor: "#EBDDB4", borderRadius: radius.md, padding: spacing.md, marginTop: spacing.md },
  resetBtn: { alignItems: "center", marginTop: spacing.lg },
  resetText: { fontFamily: fonts.uiMedium, fontSize: 13, color: colors.textMuted },
});

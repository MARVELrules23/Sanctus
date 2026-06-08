import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";

import { api, LiturgicalDay } from "@/src/api";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import { colorForLiturgical, colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { monthName, todayISO } from "@/src/date-utils";

const DOW_HEAD = ["S", "M", "T", "W", "T", "F", "S"];

export default function CalendarScreen() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [days, setDays] = useState<LiturgicalDay[]>([]);
  const [selected, setSelected] = useState<string>(todayISO());
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const res = await api<{ days: LiturgicalDay[] }>(`/liturgical/month?year=${year}&month=${month}`);
    setDays(res.days);
  }, [year, month]);

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    (async () => {
      try {
        await load();
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => {
      cancel = true;
    };
  }, [load]);

  const grid = useMemo(() => {
    if (!days.length) return [];
    const firstDay = new Date(year, month - 1, 1);
    const padBefore = firstDay.getDay(); // Sunday=0
    const cells: (LiturgicalDay | null)[] = [];
    for (let i = 0; i < padBefore; i++) cells.push(null);
    cells.push(...days);
    while (cells.length % 7 !== 0) cells.push(null);
    return cells;
  }, [days, year, month]);

  const sel = days.find((d) => d.date === selected);

  const prev = () => {
    if (month === 1) {
      setYear(year - 1);
      setMonth(12);
    } else setMonth(month - 1);
  };
  const next = () => {
    if (month === 12) {
      setYear(year + 1);
      setMonth(1);
    } else setMonth(month + 1);
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="calendar-screen">
      <View style={styles.header}>
        <Text style={styles.title}>Liturgical Calendar</Text>
        <View style={styles.monthRow}>
          <Pressable testID="cal-prev" onPress={prev} hitSlop={12}>
            <Ionicons name="chevron-back" size={22} color={colors.primary} />
          </Pressable>
          <Text style={styles.monthLabel}>
            {monthName(month)} {year}
          </Text>
          <Pressable testID="cal-next" onPress={next} hitSlop={12}>
            <Ionicons name="chevron-forward" size={22} color={colors.primary} />
          </Pressable>
        </View>
        <View style={styles.dowRow}>
          {DOW_HEAD.map((d, i) => (
            <Text key={i} style={styles.dowText}>
              {d}
            </Text>
          ))}
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {loading ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
        ) : (
          <>
            <View style={styles.grid}>
              {grid.map((cell, idx) => {
                if (!cell) return <View key={idx} style={styles.cellEmpty} />;
                const isSel = cell.date === selected;
                const isToday = cell.date === todayISO();
                const c = colorForLiturgical(cell.color);
                return (
                  <Pressable
                    key={cell.date}
                    testID={`cal-cell-${cell.date}`}
                    onPress={() => setSelected(cell.date)}
                    style={[styles.cell, isSel && styles.cellSel]}
                  >
                    <View style={[styles.cellTop, { backgroundColor: c }]} />
                    <Text style={[styles.cellNum, isSel && styles.cellNumSel]}>
                      {Number(cell.date.split("-")[2])}
                    </Text>
                    {isToday && <View style={styles.todayDot} />}
                    {cell.feast && cell.rank === "solemnity" && (
                      <Ionicons name="star" size={8} color={colors.gold} style={styles.cellStar} />
                    )}
                  </Pressable>
                );
              })}
            </View>

            {sel ? (
              <View style={styles.detail} testID="cal-detail-card">
                <View style={styles.detailHeader}>
                  <View style={[styles.colorRing, { borderColor: colorForLiturgical(sel.color) }]}>
                    <View style={[styles.colorDot, { backgroundColor: colorForLiturgical(sel.color) }]} />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.detailDate}>
                      {new Date(sel.date).toLocaleDateString(undefined, {
                        weekday: "long",
                        month: "long",
                        day: "numeric",
                      })}
                    </Text>
                    <Text style={styles.detailSeason}>{sel.season}</Text>
                  </View>
                </View>
                {sel.feast ? <Text style={styles.detailFeast}>{sel.feast}</Text> : null}
                <View style={styles.detailBadges}>
                  {sel.is_abstinence && <LiturgicalBadge color="red" label="Abstinence" />}
                  {sel.is_fast && <LiturgicalBadge color="purple" label="Fast" />}
                  {sel.is_sunday && <LiturgicalBadge color="gold" label="Lord's Day" />}
                  {sel.rank && sel.rank !== "feria" && (
                    <LiturgicalBadge color={sel.color} label={sel.rank} />
                  )}
                </View>
                {sel.is_abstinence ? (
                  <Text style={styles.detailNote}>
                    No meat is observed. Meals will be planned around fish, vegetables, and grains.
                  </Text>
                ) : sel.is_sunday ? (
                  <Text style={styles.detailNote}>
                    The Lord&apos;s Day. Workouts on Sundays are gentle — a walk, stretching, and prayer.
                  </Text>
                ) : sel.rank === "solemnity" ? (
                  <Text style={styles.detailNote}>
                    A solemnity — meals will be festive and joyful in the spirit of the Church&apos;s tradition.
                  </Text>
                ) : (
                  <Text style={styles.detailNote}>
                    A weekday in {sel.season}. Plans flow with the rhythm of the season.
                  </Text>
                )}
              </View>
            ) : null}
            <View style={{ height: spacing.xxl }} />
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const CELL_BORDER = "#F0EBE1";

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  title: { fontFamily: fonts.headingBold, fontSize: 28, color: colors.textPrimary },
  monthRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: spacing.md },
  monthLabel: { fontFamily: fonts.headingSemi, fontSize: 20, color: colors.primary },
  dowRow: { flexDirection: "row", marginTop: spacing.sm },
  dowText: {
    flex: 1,
    textAlign: "center",
    fontFamily: fonts.uiSemi,
    color: colors.textMuted,
    fontSize: 12,
    letterSpacing: 1,
  },
  scroll: { paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  grid: { flexDirection: "row", flexWrap: "wrap" },
  cell: {
    width: `${100 / 7}%`,
    aspectRatio: 1,
    padding: 2,
    borderWidth: 1,
    borderColor: CELL_BORDER,
    alignItems: "center",
    justifyContent: "flex-start",
    backgroundColor: colors.surface,
  },
  cellEmpty: { width: `${100 / 7}%`, aspectRatio: 1 },
  cellSel: { backgroundColor: "#FFF7E0", borderColor: colors.gold },
  cellTop: { width: "60%", height: 3, borderRadius: 2, marginTop: 4 },
  cellNum: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary, marginTop: 4 },
  cellNumSel: { color: colors.primary },
  cellStar: { position: "absolute", top: 4, right: 4 },
  todayDot: { width: 4, height: 4, borderRadius: 2, backgroundColor: colors.primary, marginTop: 2 },
  detail: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginTop: spacing.lg,
    ...shadow.card,
  },
  detailHeader: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  colorRing: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 2,
    alignItems: "center",
    justifyContent: "center",
  },
  colorDot: { width: 18, height: 18, borderRadius: 9 },
  detailDate: { fontFamily: fonts.headingBold, fontSize: 18, color: colors.textPrimary },
  detailSeason: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textSecondary, fontSize: 14 },
  detailFeast: { fontFamily: fonts.headingSemi, fontSize: 20, color: colors.liturgical.red, marginTop: spacing.md },
  detailBadges: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.md },
  detailNote: {
    fontFamily: fonts.bodyRegular,
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 22,
    marginTop: spacing.md,
  },
});

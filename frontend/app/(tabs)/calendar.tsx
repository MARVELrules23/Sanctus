import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";

import { api, ChallengeSummary, JournalEntry, LiturgicalDay, listChallenges } from "@/src/api";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import { colorForLiturgical, colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { formatLongFromISO, monthName, todayISO } from "@/src/date-utils";

const DOW_HEAD = ["S", "M", "T", "W", "T", "F", "S"];

export default function CalendarScreen() {
  const router = useRouter();
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [days, setDays] = useState<LiturgicalDay[]>([]);
  const [selected, setSelected] = useState<string>(todayISO());
  const [loading, setLoading] = useState(true);
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [entriesLoading, setEntriesLoading] = useState(false);
  const [entryDates, setEntryDates] = useState<Set<string>>(new Set());
  const [challenges, setChallenges] = useState<ChallengeSummary[]>([]);

  // Pull enrolled challenges so we can decorate calendar cells (and the
  // selected-day detail card) — only enrolled tracks count toward overlays,
  // per the toggle-driven contract.
  const loadChallenges = useCallback(async () => {
    try {
      const r = await listChallenges();
      setChallenges((r.items || []).filter((c) => c.enrolled));
    } catch {
      setChallenges([]);
    }
  }, []);

  const load = useCallback(async () => {
    const res = await api<{ days: LiturgicalDay[] }>(`/liturgical/month?year=${year}&month=${month}`);
    setDays(res.days);
  }, [year, month]);

  // Load journal entries from a window around the visible month so we can show dots.
  const loadEntryDates = useCallback(async () => {
    try {
      const res = await api<{ items: JournalEntry[] }>(`/journal?limit=200`);
      const inMonth = (res.items || [])
        .map((j) => j.date)
        .filter((d) => {
          const [y, m] = d.split("-");
          return Number(y) === year && Number(m) === month;
        });
      setEntryDates(new Set(inMonth));
    } catch (e) {
      console.warn("entries window failed", e);
    }
  }, [year, month]);

  // Load entries for the selected day specifically.
  const loadEntriesFor = useCallback(async (d: string) => {
    setEntriesLoading(true);
    try {
      const res = await api<{ items: JournalEntry[] }>(`/journal?date=${d}`);
      setEntries(res.items || []);
    } catch (e) {
      console.warn("entries failed", e);
      setEntries([]);
    } finally {
      setEntriesLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    (async () => {
      try {
        await Promise.all([load(), loadEntryDates(), loadChallenges()]);
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => {
      cancel = true;
    };
  }, [load, loadEntryDates, loadChallenges]);

  useEffect(() => {
    void loadEntriesFor(selected);
  }, [selected, loadEntriesFor]);

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

  // Lookup: which enrolled challenge does this date belong to (if any)?
  const challengeFor = useCallback(
    (dStr: string): ChallengeSummary | null => {
      for (const c of challenges) {
        const s = (c.start_date || "").slice(0, 10);
        const e = (c.end_date || "").slice(0, 10);
        if (!s || !e) continue;
        if (s <= dStr && dStr <= e) return c;
      }
      return null;
    },
    [challenges],
  );

  const selChallenge = sel ? challengeFor(sel.date) : null;
  const selDayIndex = useMemo(() => {
    if (!sel || !selChallenge) return null;
    const start = (selChallenge.start_date || "").slice(0, 10);
    if (!start) return null;
    const sD = new Date(`${start}T00:00:00`);
    const dD = new Date(`${sel.date}T00:00:00`);
    const raw = Math.floor((dD.getTime() - sD.getTime()) / 86_400_000) + 1;
    const total = selChallenge.total_days || 0;
    if (!total) return Math.max(1, raw);
    return Math.max(1, Math.min(raw, total));
  }, [sel, selChallenge]);

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

  const newEntry = () =>
    router.push({ pathname: "/journal", params: { date: selected } });
  const openEntry = (id: string) =>
    router.push({ pathname: "/journal", params: { entry: id } });

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
                const cellChallenge = challengeFor(cell.date);
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
                    {entryDates.has(cell.date) && (
                      <View style={styles.entryDot} testID={`entry-dot-${cell.date}`} />
                    )}
                    {cellChallenge ? (
                      <View
                        style={[
                          styles.cellChallengeBar,
                          { backgroundColor: cellChallenge.color || colors.gold },
                        ]}
                        testID={`cal-challenge-${cell.date}`}
                      />
                    ) : null}
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
                      {formatLongFromISO(sel.date)}
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

                {selChallenge ? (
                  <Pressable
                    testID={`cal-challenge-tile-${selChallenge.slug}`}
                    onPress={() =>
                      router.push({
                        pathname: "/challenges/[slug]",
                        params: { slug: selChallenge.slug },
                      })
                    }
                    style={({ pressed }) => [
                      styles.challengeTile,
                      { borderColor: selChallenge.color || colors.gold },
                      pressed && styles.pressed,
                    ]}
                  >
                    <Ionicons
                      name={(selChallenge.icon as keyof typeof Ionicons.glyphMap) || "flame-outline"}
                      size={18}
                      color={selChallenge.color || colors.gold}
                    />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.challengeTileTitle}>
                        {selChallenge.name}
                      </Text>
                      <Text style={styles.challengeTileMeta}>
                        Day {selDayIndex} of {selChallenge.total_days}
                        {selChallenge.patron_saint ? ` · ${selChallenge.patron_saint}` : ""}
                      </Text>
                    </View>
                    <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
                  </Pressable>
                ) : null}
              </View>
            ) : null}

            {/* Journal entries for selected day */}
            <View style={styles.journalSection} testID="cal-journal-section">
              <View style={styles.journalHead}>
                <Text style={styles.journalTitle}>Journal &amp; notes</Text>
                <Pressable
                  testID="cal-add-note"
                  onPress={newEntry}
                  style={({ pressed }) => [styles.addBtn, pressed && styles.pressed]}
                >
                  <Ionicons name="add" size={16} color={colors.gold} />
                  <Text style={styles.addBtnText}>Add note</Text>
                </Pressable>
              </View>
              {entriesLoading ? (
                <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.sm }} />
              ) : entries.length === 0 ? (
                <Text style={styles.journalEmpty}>
                  No notes yet for this day. Tap Add note to write a reflection.
                </Text>
              ) : (
                entries.map((e) => (
                  <Pressable
                    key={e.entry_id}
                    testID={`cal-entry-${e.entry_id}`}
                    onPress={() => openEntry(e.entry_id)}
                    style={({ pressed }) => [styles.entryRow, pressed && styles.pressed]}
                  >
                    <Ionicons
                      name={
                        e.kind === "examen"
                          ? "sunny-outline"
                          : e.kind === "examination"
                            ? "leaf-outline"
                            : "create-outline"
                      }
                      size={18}
                      color={colors.gold}
                    />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.entryTitle} numberOfLines={1}>
                        {e.title || "Untitled entry"}
                      </Text>
                      <Text style={styles.entryPreview} numberOfLines={2}>
                        {e.body}
                      </Text>
                    </View>
                    <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
                  </Pressable>
                ))
              )}
            </View>
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
  entryDot: {
    position: "absolute",
    bottom: 4,
    right: 6,
    width: 5,
    height: 5,
    borderRadius: 3,
    backgroundColor: colors.gold,
  },
  cellChallengeBar: {
    position: "absolute",
    bottom: 0,
    left: 6,
    right: 6,
    height: 3,
    borderRadius: 2,
  },
  challengeTile: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginTop: spacing.md,
    padding: spacing.sm + 2,
    borderRadius: radius.md,
    borderWidth: 1.5,
    backgroundColor: colors.background,
  },
  challengeTileTitle: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textPrimary },
  challengeTileMeta: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 2,
  },
  journalSection: {
    marginTop: spacing.lg,
    paddingTop: spacing.lg,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
  },
  journalHead: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.sm,
  },
  journalTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  addBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
  },
  addBtnText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 12 },
  journalEmpty: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textSecondary,
    fontSize: 13,
    marginTop: spacing.sm,
  },
  entryRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  entryTitle: { fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary },
  entryPreview: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textMuted,
    lineHeight: 18,
    marginTop: 2,
  },
  pressed: { opacity: 0.7 },
});

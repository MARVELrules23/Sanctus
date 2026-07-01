import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  View,
} from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect, useRouter } from "expo-router";

import { api, ChallengeWindow, JournalEntry, LiturgicalDay, listAttendingEvents, listChallengeWindows, listSchedule, ParishEvent, ScheduleItem } from "@/src/api";
import { useChallengeMasterPref } from "@/src/use-challenge-pref";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import { colorForLiturgical, colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { formatLongFromISO, monthName, todayISO } from "@/src/date-utils";
import { dowOf, format12 } from "@/src/schedule-utils";

const DOW_HEAD = ["S", "M", "T", "W", "T", "F", "S"];

export default function CalendarScreen() {
  const router = useRouter();
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [days, setDays] = useState<LiturgicalDay[]>([]);
  const [selected, setSelected] = useState<string>(todayISO());
  const [loading, setLoading] = useState(true);
  const [rite, setRite] = useState<"roman" | "tridentine" | "eastern">("roman");
  const [eastCal, setEastCal] = useState<"new" | "old">("new");
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [entriesLoading, setEntriesLoading] = useState(false);
  const [entryDates, setEntryDates] = useState<Set<string>>(new Set());
  const [challenges, setChallenges] = useState<ChallengeWindow[]>([]);
  const [novenaWin, setNovenaWin] = useState<ChallengeWindow | null>(null);
  const [scheduleItems, setScheduleItems] = useState<ScheduleItem[]>([]);
  const [attending, setAttending] = useState<ParishEvent[]>([]);
  const { enabled: challengeMasterOn, setEnabled: setChallengeMasterOn } = useChallengeMasterPref();

  const loadAttending = useCallback(async () => {
    try {
      const r = await listAttendingEvents(180);
      setAttending(r.items || []);
    } catch {
      setAttending([]);
    }
  }, []);

  // Pull every liturgical challenge's window computed for the year currently
  // being viewed — so all tracks (Hallowtide, Advent, Lent, and the
  // Consecrations) overlay the calendar in whatever year the user browses.
  const loadChallenges = useCallback(async () => {
    try {
      const r = await listChallengeWindows(year);
      setChallenges(r.items || []);
    } catch {
      setChallenges([]);
    }
    // The user's active novena (if any) overlays the calendar like a challenge,
    // but independent of the challenge master toggle.
    try {
      const nr = await api<{ active: any }>("/novenas/active");
      const a = nr?.active;
      if (a && a.novena) {
        setNovenaWin({
          challenge_id: `novena-${a.slug}`,
          slug: a.slug,
          name: a.novena.name,
          subtitle: a.novena.patron,
          color: a.novena.color,
          icon: a.novena.icon,
          start_date: a.start_date,
          end_date: a.end_date,
          total_days: a.total_days || 9,
          status: "active",
        } as ChallengeWindow);
      } else {
        setNovenaWin(null);
      }
    } catch {
      setNovenaWin(null);
    }
  }, [year]);

  const load = useCallback(async () => {
    const url =
      rite === "eastern"
        ? `/eastern/month?year=${year}&month=${month}&calendar=${eastCal}`
        : rite === "tridentine"
        ? `/tridentine/month?year=${year}&month=${month}`
        : `/liturgical/month?year=${year}&month=${month}`;
    const res = await api<{ days: LiturgicalDay[] }>(url);
    setDays(res.days);
  }, [year, month, rite, eastCal]);

  const loadSchedule = useCallback(async () => {
    try {
      const r = await listSchedule();
      setScheduleItems(r.items || []);
    } catch {
      setScheduleItems([]);
    }
  }, []);

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
        await Promise.all([load(), loadEntryDates(), loadChallenges(), loadSchedule(), loadAttending()]);
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => {
      cancel = true;
    };
  }, [load, loadEntryDates, loadChallenges, loadSchedule, loadAttending]);

  // Refresh the schedule whenever the screen regains focus (e.g. after adding).
  useFocusEffect(useCallback(() => { void loadSchedule(); void loadAttending(); }, [loadSchedule, loadAttending]));

  // Group the events the user is attending by their LOCAL calendar date.
  const eventsByDate = useMemo(() => {
    const m = new Map<string, ParishEvent[]>();
    for (const ev of attending) {
      const d = new Date(ev.start_at);
      if (isNaN(d.getTime())) continue;
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
      const arr = m.get(key) || [];
      arr.push(ev);
      m.set(key, arr);
    }
    return m;
  }, [attending]);

  const eventsForSel = useMemo(() => {
    const list = (eventsByDate.get(selected) || []).slice();
    return list.sort((a, b) => (a.start_at || "").localeCompare(b.start_at || ""));
  }, [eventsByDate, selected]);

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

  // Does a given date have any schedule items? (weekly by weekday, or one-off).
  const hasSchedule = useCallback(
    (dStr: string): boolean => {
      const dw = dowOf(dStr);
      return scheduleItems.some((it) =>
        it.recurrence === "once" ? it.date === dStr : (it.days_of_week || []).includes(dw),
      );
    },
    [scheduleItems],
  );

  // Schedule items that fall on the selected day, timed first.
  const scheduleForSel = useMemo(() => {
    const dw = dowOf(selected);
    return scheduleItems
      .filter((it) => (it.recurrence === "once" ? it.date === selected : (it.days_of_week || []).includes(dw)))
      .sort((a, b) => (a.time || "99:99").localeCompare(b.time || "99:99"));
  }, [scheduleItems, selected]);

  // Lookup: which published challenges cover this date (there can be more than
  // one — e.g. St. Joseph overlaps Lent, Sacred Heart overlaps Marian). Sorted
  // shortest-window-first so the most specific track is listed first. Returns
  // an empty array whenever the master "Liturgical Challenges" toggle is off.
  const challengesForDate = useCallback(
    (dStr: string): ChallengeWindow[] => {
      const list = challengeMasterOn
        ? challenges.filter((c) => {
            const s = (c.start_date || "").slice(0, 10);
            const e = (c.end_date || "").slice(0, 10);
            return !!s && !!e && s <= dStr && dStr <= e;
          })
        : [];
      // Active novena always overlays (not gated by the challenge toggle).
      if (novenaWin) {
        const s = (novenaWin.start_date || "").slice(0, 10);
        const e = (novenaWin.end_date || "").slice(0, 10);
        if (s && e && s <= dStr && dStr <= e) list.push(novenaWin);
      }
      return list.sort((a, b) => (a.total_days || 0) - (b.total_days || 0));
    },
    [challenges, challengeMasterOn, novenaWin],
  );

  const dayIndexFor = useCallback((c: ChallengeWindow, dStr: string): number => {
    const start = (c.start_date || "").slice(0, 10);
    if (!start) return 1;
    // Parse as UTC midnight so the day count is never thrown off by a DST
    // transition inside the window (e.g. the St. Joseph track crosses the
    // March spring-forward, which previously duplicated a day and dropped 33).
    const sD = new Date(`${start}T00:00:00Z`);
    const dD = new Date(`${dStr}T00:00:00Z`);
    const raw = Math.round((dD.getTime() - sD.getTime()) / 86_400_000) + 1;
    const total = c.total_days || 0;
    return total ? Math.max(1, Math.min(raw, total)) : Math.max(1, raw);
  }, []);

  const selChallenges = useMemo(
    () => (sel ? challengesForDate(sel.date) : []),
    [sel, challengesForDate],
  );

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
        <View style={styles.riteRow}>
          {(["roman", "tridentine", "eastern"] as const).map((r) => (
            <Pressable
              key={r}
              testID={`cal-rite-${r}`}
              onPress={() => setRite(r)}
              style={[styles.riteChip, rite === r && styles.riteChipActive]}
            >
              <Text
                numberOfLines={2}
                style={[styles.riteChipText, rite === r && styles.riteChipTextActive]}
              >
                {r === "roman"
                  ? "Roman (Latin)"
                  : r === "tridentine"
                  ? "Traditional (1962)"
                  : "Eastern (Byzantine)"}
              </Text>
            </Pressable>
          ))}
        </View>
        {rite === "eastern" ? (
          <View style={styles.calRow}>
            {(["new", "old"] as const).map((c) => (
              <Pressable
                key={c}
                testID={`cal-eastcal-${c}`}
                onPress={() => setEastCal(c)}
                style={[styles.calChip, eastCal === c && styles.calChipActive]}
              >
                <Text style={[styles.calChipText, eastCal === c && styles.calChipTextActive]}>
                  {c === "new" ? "New (Gregorian)" : "Old (Julian)"}
                </Text>
              </Pressable>
            ))}
          </View>
        ) : null}
        <View style={styles.monthRow}>
          <Pressable testID="cal-prev" onPress={prev} hitSlop={12}>
            <Ionicons name="chevron-back" size={22} color={colors.primary} />
          </Pressable>
          <Text style={styles.monthLabel}>
            <Text>{monthName(month)}</Text> {year}
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
                const cellChallenges = challengesForDate(cell.date);
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
                    {cell.feast && (cell.rank === "solemnity" || cell.rank === "I class") && (
                      <Ionicons name="star" size={8} color={colors.gold} style={styles.cellStar} />
                    )}
                    {cell.is_holy_day && (
                      <View style={styles.holyDayDot} testID={`holyday-dot-${cell.date}`} />
                    )}
                    {cell.observance && (
                      <View style={styles.observanceDot} testID={`observance-dot-${cell.date}`} />
                    )}
                    {entryDates.has(cell.date) && (
                      <View style={styles.entryDot} testID={`entry-dot-${cell.date}`} />
                    )}
                    {hasSchedule(cell.date) && (
                      <View style={styles.scheduleDot} testID={`schedule-dot-${cell.date}`} />
                    )}
                    {eventsByDate.has(cell.date) && (
                      <View style={styles.eventDot} testID={`event-dot-${cell.date}`} />
                    )}
                    {cellChallenges.length > 0 ? (
                      <View style={styles.cellChallengeBarRow} testID={`cal-challenge-${cell.date}`}>
                        {cellChallenges.slice(0, 3).map((cc) => (
                          <View
                            key={cc.slug}
                            style={[
                              styles.cellChallengeBar,
                              { backgroundColor: cc.color || colors.gold },
                            ]}
                            testID={`cal-challenge-${cell.date}-${cc.slug}`}
                          />
                        ))}
                      </View>
                    ) : null}
                  </Pressable>
                );
              })}
            </View>

            {/* Master toggle — when ON, every published Liturgical Challenge
                is laid over the calendar on its specific dates. Persisted per
                device (AsyncStorage). */}
            {challenges.length > 0 ? (
              <View style={styles.challengeToggleCard} testID="cal-challenge-master-card">
                <Ionicons
                  name="flame-outline"
                  size={18}
                  color={challengeMasterOn ? colors.gold : colors.textMuted}
                />
                <View style={{ flex: 1 }}>
                  <Text style={styles.challengeToggleTitle}>Liturgical Challenges</Text>
                  <Text style={styles.challengeToggleSub}>
                    {challengeMasterOn
                      ? "Showing on the calendar on each track's dates."
                      : "Turn on to see all liturgical challenges on the calendar."}
                  </Text>
                </View>
                <Switch
                  testID="cal-challenge-master-toggle"
                  value={challengeMasterOn}
                  onValueChange={(v) => { void setChallengeMasterOn(v); }}
                  trackColor={{ false: colors.borderSoft, true: colors.gold }}
                  thumbColor={colors.surface}
                />
              </View>
            ) : null}

            {/* Full list of liturgical challenges — tap any to open it and
                choose whether to begin today, tomorrow, or on its feast day. */}
            {challenges.length > 0 ? (
              <View style={styles.scheduleSection} testID="cal-all-challenges-section">
                <View style={styles.journalHead}>
                  <Text style={styles.journalTitle}>All Liturgical Challenges</Text>
                </View>
                <Text style={styles.scheduleEmpty}>
                  Tap any challenge to read it and choose when to begin. Consecration challenges are
                  timed to a feast — start on the feast day to fulfil the consecration if you wish.
                </Text>
                {challenges.map((ch) => (
                  <Pressable
                    key={ch.slug}
                    testID={`cal-all-challenge-${ch.slug}`}
                    onPress={() => router.push({ pathname: "/challenges/[slug]", params: { slug: ch.slug } })}
                    style={({ pressed }) => [
                      styles.challengeTile,
                      { borderColor: ch.color || colors.gold, marginTop: spacing.sm },
                      pressed && styles.pressed,
                    ]}
                  >
                    <Ionicons
                      name={(ch.icon as keyof typeof Ionicons.glyphMap) || "flame-outline"}
                      size={18}
                      color={ch.color || colors.gold}
                    />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.challengeTileTitle}>{ch.name}</Text>
                      <Text style={styles.challengeTileMeta}>
                        {ch.total_days}-day walk · begins {formatLongFromISO(ch.start_date)}
                        {ch.patron_saint ? ` · ${ch.patron_saint}` : ""}
                      </Text>
                    </View>
                    <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
                  </Pressable>
                ))}
              </View>
            ) : null}

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
                {sel.observance ? (
                  <Text style={styles.detailObservance} testID="cal-observance">{sel.observance}</Text>
                ) : null}
                <View style={styles.detailBadges}>
                  {sel.is_holy_day && <LiturgicalBadge color="gold" label="Holy Day of Obligation" />}
                  {sel.is_abstinence && (
                    <LiturgicalBadge
                      color="red"
                      label={sel.abstinence_type === "partial" ? "Partial Abstinence" : "Abstinence"}
                    />
                  )}
                  {sel.is_fast && <LiturgicalBadge color="purple" label="Fast" />}
                  {sel.is_sunday && <LiturgicalBadge color="gold" label="Lord's Day" />}
                  {sel.rank && sel.rank !== "feria" && (
                    <LiturgicalBadge color={sel.color} label={sel.rank} />
                  )}
                </View>
                {sel.holy_day_note ? (
                  <Text style={styles.detailNote} testID="cal-holyday-note">{sel.holy_day_note} — assist at Mass.</Text>
                ) : null}
                {sel.is_abstinence ? (
                  <Text style={styles.detailNote}>
                    {sel.abstinence_type === "partial"
                      ? "Partial abstinence — meat only at the principal meal. Meals will lean on fish, vegetables, and grains."
                      : "No meat is observed. Meals will be planned around fish, vegetables, and grains."}
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

                {selChallenges.map((ch) => (
                  <Pressable
                    key={ch.slug}
                    testID={`cal-challenge-tile-${ch.slug}`}
                    onPress={() =>
                      router.push(
                        ch.challenge_id?.startsWith("novena-")
                          ? { pathname: "/novenas/[slug]", params: { slug: ch.slug } }
                          : { pathname: "/challenges/[slug]", params: { slug: ch.slug } }
                      )
                    }
                    style={({ pressed }) => [
                      styles.challengeTile,
                      { borderColor: ch.color || colors.gold },
                      pressed && styles.pressed,
                    ]}
                  >
                    <Ionicons
                      name={(ch.icon as keyof typeof Ionicons.glyphMap) || "flame-outline"}
                      size={18}
                      color={ch.color || colors.gold}
                    />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.challengeTileTitle}>
                        {ch.name}
                      </Text>
                      <Text style={styles.challengeTileMeta}>
                        Day {dayIndexFor(ch, sel.date)} of {ch.total_days}
                        {ch.patron_saint ? ` · ${ch.patron_saint}` : ""}
                      </Text>
                    </View>
                    <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
                  </Pressable>
                ))}
              </View>
            ) : null}

            {/* Schedule for selected day */}
            <View style={styles.scheduleSection} testID="cal-schedule-section">
              <View style={styles.journalHead}>
                <Text style={styles.journalTitle}>Schedule</Text>
                <Pressable
                  testID="cal-schedule-add"
                  onPress={() =>
                    router.push({
                      pathname: "/schedule/edit",
                      params: { date: selected, dow: String(dowOf(selected)), rec: "once" },
                    })
                  }
                  style={({ pressed }) => [styles.addBtn, pressed && styles.pressed]}
                >
                  <Ionicons name="add" size={16} color={colors.gold} />
                  <Text style={styles.addBtnText}>Add</Text>
                </Pressable>
              </View>
              {scheduleForSel.length === 0 ? (
                <Text style={styles.scheduleEmpty}>Nothing scheduled for this day.</Text>
              ) : (
                scheduleForSel.map((it) => (
                  <Pressable
                    key={it.id}
                    testID={`cal-schedule-item-${it.id}`}
                    onPress={() => router.push({ pathname: "/schedule/edit", params: { id: it.id } })}
                    style={({ pressed }) => [styles.schedRow, { borderLeftColor: it.color || colors.gold }, pressed && styles.pressed]}
                  >
                    <Ionicons name={(it.icon as keyof typeof Ionicons.glyphMap) || "ellipse-outline"} size={16} color={it.color || colors.gold} />
                    <Text style={styles.schedTime}>{format12(it.time)}</Text>
                    <Text style={styles.schedTitle} numberOfLines={1}>{it.title}</Text>
                    {it.notify ? <Ionicons name="notifications" size={13} color={colors.gold} /> : null}
                  </Pressable>
                ))
              )}
              <Pressable
                testID="cal-schedule-open"
                onPress={() => router.push("/schedule")}
                style={({ pressed }) => [styles.schedOpen, pressed && styles.pressed]}
              >
                <Text style={styles.schedOpenText}>Open full schedule</Text>
                <Ionicons name="chevron-forward" size={15} color={colors.gold} />
              </Pressable>
            </View>

            {/* Parish events the user is attending on the selected day */}
            <View style={styles.scheduleSection} testID="cal-events-section">
              <View style={styles.journalHead}>
                <Text style={styles.journalTitle}>Events you&apos;re attending</Text>
                <Pressable
                  testID="cal-events-browse"
                  onPress={() => router.push("/parish-events")}
                  style={({ pressed }) => [styles.addBtn, pressed && styles.pressed]}
                >
                  <Ionicons name="search" size={14} color={colors.gold} />
                  <Text style={styles.addBtnText}>Browse</Text>
                </Pressable>
              </View>
              {eventsForSel.length === 0 ? (
                <Text style={styles.scheduleEmpty}>
                  No events marked for this day. Tap &ldquo;I&apos;m going&rdquo; on a parish event and it will appear here.
                </Text>
              ) : (
                eventsForSel.map((ev) => {
                  const t = new Date(ev.start_at).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
                  return (
                    <Pressable
                      key={ev.occurrence_key || ev.id}
                      testID={`cal-event-item-${ev.id}`}
                      onPress={() => router.push("/parish-events")}
                      style={({ pressed }) => [styles.schedRow, { borderLeftColor: colors.gold }, pressed && styles.pressed]}
                    >
                      <Ionicons name="people-outline" size={16} color={colors.gold} />
                      <Text style={styles.schedTime}>{t}</Text>
                      <Text style={styles.schedTitle} numberOfLines={1}>{ev.title}</Text>
                      {ev.recurrence && ev.recurrence !== "once" ? (
                        <Ionicons name="repeat" size={13} color={colors.textMuted} />
                      ) : null}
                    </Pressable>
                  );
                })
              )}
            </View>

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
  riteRow: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm },
  riteChip: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    alignItems: "center",
  },
  riteChipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  riteChipText: { fontFamily: fonts.uiSemi, fontSize: 12.5, color: colors.textSecondary },
  riteChipTextActive: { color: colors.gold },
  calRow: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm },
  calChip: {
    flex: 1,
    paddingVertical: 6,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.gold,
    alignItems: "center",
  },
  calChipActive: { backgroundColor: colors.gold },
  calChipText: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.gold },
  calChipTextActive: { color: colors.primary },
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
  detailObservance: {
    fontFamily: fonts.uiSemi,
    fontSize: 13,
    color: colors.liturgical.purple,
    marginTop: spacing.xs,
  },
  holyDayDot: {
    position: "absolute",
    top: 4,
    left: 4,
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.gold,
  },
  observanceDot: {
    position: "absolute",
    top: 4,
    left: 12,
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.liturgical.purple,
  },
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
  cellChallengeBarRow: {
    position: "absolute",
    bottom: 0,
    left: 6,
    right: 6,
    height: 3,
    flexDirection: "row",
    gap: 2,
  },
  cellChallengeBar: {
    flex: 1,
    height: 3,
    borderRadius: 2,
  },
  challengeToggleCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginTop: spacing.md,
    padding: spacing.md,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.surface,
  },
  challengeToggleTitle: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  challengeToggleSub: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textMuted,
    marginTop: 2,
    lineHeight: 16,
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
  scheduleDot: {
    position: "absolute",
    bottom: 4,
    left: 6,
    width: 5,
    height: 5,
    borderRadius: 3,
    backgroundColor: colors.primary,
  },
  eventDot: {
    position: "absolute",
    bottom: 4,
    left: 14,
    width: 5,
    height: 5,
    borderRadius: 3,
    backgroundColor: colors.gold,
  },
  scheduleSection: {
    marginTop: spacing.lg,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.md,
    ...shadow.card,
  },
  scheduleEmpty: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 13,
    color: colors.textMuted,
    paddingVertical: spacing.sm,
  },
  schedRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingVertical: 9,
    paddingHorizontal: spacing.sm,
    borderLeftWidth: 3,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.borderSoft,
  },
  schedTime: { fontFamily: fonts.uiSemi, fontSize: 11.5, color: colors.textMuted, minWidth: 62 },
  schedTitle: { flex: 1, fontFamily: fonts.headingSemi, fontSize: 14, color: colors.textPrimary },
  schedOpen: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
    marginTop: spacing.sm,
    paddingVertical: 8,
  },
  schedOpenText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold, letterSpacing: 0.3 },
});

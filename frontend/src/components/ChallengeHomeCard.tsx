/**
 * ChallengeHomeCard — surfaces the user's currently-active enrolled
 * Liturgical Challenge on the Home tab.
 *
 * Per design: the card is ONLY visible when the user is enrolled in a
 * challenge AND today is inside that challenge's date window. If the user
 * is not enrolled (toggle off) or the window has not started / has ended,
 * the card renders nothing — keeping the Home tab calm.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";

import {
  ChallengeDay,
  ChallengeDetail,
  ChallengeSummary,
  checkinChallenge,
  getChallenge,
  listChallenges,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

function iso(s: string | null | undefined): string | null {
  if (!s) return null;
  return s.slice(0, 10);
}

function isActiveToday(c: ChallengeSummary, today: string): boolean {
  const start = iso(c.start_date);
  const end = iso(c.end_date);
  if (!start || !end) return false;
  return start <= today && today <= end;
}

export default function ChallengeHomeCard({ date }: { date: string }) {
  const router = useRouter();
  const { user } = useAuth();
  const [summary, setSummary] = useState<ChallengeSummary | null>(null);
  const [detail, setDetail] = useState<ChallengeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!user) {
      setSummary(null);
      setDetail(null);
      setLoading(false);
      return;
    }
    try {
      const r = await listChallenges();
      // Find the user's enrolled + currently-active challenge.
      const active = (r.items || []).find(
        (c) => c.enrolled && isActiveToday(c, date),
      );
      if (!active) {
        setSummary(null);
        setDetail(null);
        return;
      }
      setSummary(active);
      try {
        const d = await getChallenge(active.slug);
        setDetail(d);
      } catch {
        setDetail(null);
      }
    } catch {
      setSummary(null);
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, [user, date]);

  useEffect(() => { void load(); }, [load]);

  const today: ChallengeDay | null = useMemo(() => {
    if (!detail?.days) return null;
    return detail.days.find((d) => iso(d.date) === date) || null;
  }, [detail, date]);

  // Clamp the day index so it never exceeds the total days available.
  const displayDayIndex = useMemo(() => {
    if (today?.day_index) return today.day_index;
    if (!summary?.start_date) return null;
    const start = iso(summary.start_date);
    if (!start) return null;
    const s = new Date(`${start}T00:00:00`);
    const t = new Date(`${date}T00:00:00`);
    const diff = Math.floor((t.getTime() - s.getTime()) / 86_400_000) + 1;
    if (!summary.total_days) return diff > 0 ? diff : null;
    return Math.max(1, Math.min(diff, summary.total_days));
  }, [today, summary, date]);

  const completedToday = !!detail?.today_checkin?.completed;

  const onMarkDone = async () => {
    if (!summary || busy) return;
    setBusy(true);
    try {
      await checkinChallenge(summary.slug, {
        date,
        completed: true,
        items_done: (today?.prayer_items || []).map((p) => p.title),
      });
      await load();
    } catch {
      // silent — keep card on screen
    } finally {
      setBusy(false);
    }
  };

  if (loading) return null;
  if (!summary) return null;

  const totalDays = summary.total_days || 0;
  const accent = summary.color || colors.gold;

  return (
    <View testID="challenge-home-card" style={[styles.card, { borderColor: accent }]}>
      <View style={styles.headerRow}>
        <Ionicons
          name={(summary.icon as keyof typeof Ionicons.glyphMap) || "flame-outline"}
          size={16}
          color={accent}
        />
        <Text style={[styles.headerLabel, { color: accent }]}>
          {summary.name.toUpperCase()} · DAY {displayDayIndex ?? "—"}{totalDays ? ` OF ${totalDays}` : ""}
        </Text>
        <View style={{ flex: 1 }} />
        {summary.streak ? (
          <View style={styles.streakPill}>
            <Ionicons name="flame" size={11} color={colors.gold} />
            <Text style={styles.streakText}>{summary.streak}-day</Text>
          </View>
        ) : null}
      </View>

      <Pressable
        testID="challenge-home-open"
        onPress={() => router.push({ pathname: "/challenges/[slug]", params: { slug: summary.slug } })}
        style={({ pressed }) => [styles.body, pressed && styles.pressed]}
      >
        <Text style={styles.title} numberOfLines={2}>
          {today?.title || summary.subtitle || summary.name}
        </Text>
        {today?.patron_saint ? (
          <Text style={styles.patron} numberOfLines={1}>
            <Ionicons name="sparkles-outline" size={12} color={colors.gold} /> {today.patron_saint}
          </Text>
        ) : null}
        {today?.reflection ? (
          <Text style={styles.reflection} numberOfLines={3}>{today.reflection}</Text>
        ) : (
          <Text style={styles.reflection} numberOfLines={3}>{summary.blurb}</Text>
        )}

        {today?.prayer_items?.length ? (
          <View style={styles.itemsWrap}>
            {today.prayer_items.slice(0, 3).map((it, i) => (
              <View key={i} style={styles.itemRow}>
                <View style={[styles.itemBullet, { backgroundColor: accent }]} />
                <Text style={styles.itemTitle} numberOfLines={2}>{it.title}</Text>
              </View>
            ))}
          </View>
        ) : null}
      </Pressable>

      <View style={styles.footerRow}>
        <Pressable
          testID="challenge-home-checkin"
          disabled={busy || completedToday}
          onPress={onMarkDone}
          style={({ pressed }) => [
            styles.checkBtn,
            { backgroundColor: completedToday ? colors.background : accent },
            (pressed || busy) && { opacity: 0.7 },
          ]}
        >
          {busy ? (
            <ActivityIndicator size="small" color={completedToday ? accent : colors.gold} />
          ) : (
            <>
              <Ionicons
                name={completedToday ? "checkmark-circle" : "checkmark-circle-outline"}
                size={16}
                color={completedToday ? accent : colors.gold}
              />
              <Text
                style={[
                  styles.checkBtnText,
                  { color: completedToday ? accent : colors.gold },
                ]}
              >
                {completedToday ? "Marked for today" : "Mark today complete"}
              </Text>
            </>
          )}
        </Pressable>
        <Pressable
          testID="challenge-home-detail"
          onPress={() => router.push({ pathname: "/challenges/[slug]", params: { slug: summary.slug } })}
          hitSlop={8}
          style={({ pressed }) => [styles.linkBtn, pressed && styles.pressed]}
        >
          <Text style={[styles.linkBtnText, { color: accent }]}>Open</Text>
          <Ionicons name="chevron-forward" size={14} color={accent} />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    marginTop: spacing.md,
    padding: spacing.lg,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    ...shadow.card,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  headerLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.6,
  },
  streakPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
  },
  streakText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 11 },
  body: { marginTop: spacing.sm },
  title: {
    fontFamily: fonts.headingSemi,
    fontSize: 20,
    color: colors.textPrimary,
    lineHeight: 26,
  },
  patron: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.gold,
    marginTop: 4,
    letterSpacing: 0.5,
  },
  reflection: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
    marginTop: spacing.sm,
  },
  itemsWrap: { marginTop: spacing.sm, gap: 4 },
  itemRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  itemBullet: { width: 6, height: 6, borderRadius: 3 },
  itemTitle: {
    flex: 1,
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textPrimary,
  },
  footerRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  checkBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 10,
    borderRadius: radius.round,
  },
  checkBtnText: { fontFamily: fonts.uiSemi, fontSize: 13, letterSpacing: 0.6 },
  linkBtn: { flexDirection: "row", alignItems: "center", gap: 2, paddingHorizontal: 6 },
  linkBtnText: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 0.6 },
  pressed: { opacity: 0.7 },
});

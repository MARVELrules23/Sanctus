/**
 * Schedule — weekly + one-off personal plan layered on the liturgical calendar.
 *
 * Pick a day of the week to see what's scheduled, browse upcoming one-off
 * items, and add/edit entries. Reminders fire on a built app (see banner).
 */
import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";

import { listSchedule, ScheduleItem } from "@/src/api";
import { notificationsSupported } from "@/src/notifications";
import { useI18n } from "@/src/i18n";
import { DOW_SHORT, daysLabel, format12 } from "@/src/schedule-utils";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { formatLongFromISO, todayISO } from "@/src/date-utils";

export default function ScheduleScreen() {
  const router = useRouter();
  const { t } = useI18n();
  const params = useLocalSearchParams<{ dow?: string }>();
  const todayDow = new Date().getDay();
  const [selectedDow, setSelectedDow] = useState<number>(
    params.dow != null ? Number(params.dow) : todayDow,
  );
  const [items, setItems] = useState<ScheduleItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const r = await listSchedule();
      setItems(r.items || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  const today = todayISO();
  const weeklyForDay = useMemo(
    () =>
      items
        .filter((i) => i.recurrence === "weekly" && (i.days_of_week || []).includes(selectedDow))
        .sort((a, b) => (a.time || "99:99").localeCompare(b.time || "99:99")),
    [items, selectedDow],
  );
  const oneOffs = useMemo(
    () =>
      items
        .filter((i) => i.recurrence === "once" && (i.date || "") >= today)
        .sort((a, b) => (a.date || "").localeCompare(b.date || "") || (a.time || "99:99").localeCompare(b.time || "99:99")),
    [items, today],
  );
  const anyNotify = useMemo(() => items.some((i) => i.notify), [items]);

  const goAdd = () =>
    router.push({ pathname: "/schedule/edit", params: { dow: String(selectedDow) } } as any);
  const goEdit = (id: string) =>
    router.push({ pathname: "/schedule/edit", params: { id } } as any);

  const ItemCard = ({ item }: { item: ScheduleItem }) => (
    <Pressable
      testID={`schedule-item-${item.id}`}
      onPress={() => goEdit(item.id)}
      style={({ pressed }) => [styles.itemCard, { borderLeftColor: item.color || colors.gold }, pressed && { opacity: 0.85 }]}
    >
      <View style={[styles.itemIcon, { backgroundColor: (item.color || colors.gold) + "22" }]}>
        <Ionicons name={(item.icon as keyof typeof Ionicons.glyphMap) || "ellipse-outline"} size={18} color={item.color || colors.gold} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.itemTitle} numberOfLines={1}>{item.title}</Text>
        <View style={styles.itemMetaRow}>
          <Ionicons name="time-outline" size={12} color={colors.textMuted} />
          <Text style={styles.itemMeta}>{format12(item.time)}</Text>
          <Text style={styles.itemDot}>·</Text>
          <Text style={styles.itemMeta}>
            {item.recurrence === "once" ? (item.date ? formatLongFromISO(item.date) : "Once") : daysLabel(item.days_of_week)}
          </Text>
        </View>
      </View>
      {item.notify ? <Ionicons name="notifications" size={15} color={colors.gold} /> : null}
      <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
    </Pressable>
  );

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="schedule-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="schedule-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.headerTitle}>{t("schedule.title")}</Text>
          <Text style={styles.headerSub}>{t("schedule.subtitle")}</Text>
        </View>
        <Pressable testID="schedule-add" onPress={goAdd} hitSlop={10}>
          <Ionicons name="add-circle" size={28} color={colors.gold} />
        </Pressable>
      </View>

      {/* Day-of-week selector */}
      <View style={styles.dowStrip}>
        {DOW_SHORT.map((label, i) => {
          const on = i === selectedDow;
          const isToday = i === todayDow;
          return (
            <Pressable
              key={i}
              testID={`schedule-dow-${i}`}
              onPress={() => setSelectedDow(i)}
              style={({ pressed }) => [styles.dowChip, on && styles.dowChipOn, pressed && { opacity: 0.85 }]}
            >
              <Text style={[styles.dowChipText, on && styles.dowChipTextOn]}>{label}</Text>
              {isToday ? <View style={[styles.dowToday, on && { backgroundColor: colors.gold }]} /> : null}
            </Pressable>
          );
        })}
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          {notificationsSupported && anyNotify ? null : anyNotify ? (
            <View style={styles.banner}>
              <Ionicons name="information-circle-outline" size={16} color={colors.primary} />
              <Text style={styles.bannerText}>
                {t("schedule.remindersNote")}
              </Text>
            </View>
          ) : null}

          <Text style={styles.sectionLabel}>{t("schedule.every", { day: DOW_SHORT[selectedDow].toUpperCase() })}</Text>
          {weeklyForDay.length === 0 ? (
            <Text style={styles.empty}>{t("schedule.nothing")}</Text>
          ) : (
            weeklyForDay.map((it) => <ItemCard key={it.id} item={it} />)
          )}

          {oneOffs.length > 0 ? (
            <>
              <Text style={[styles.sectionLabel, { marginTop: spacing.lg }]}>UPCOMING ONE-OFF</Text>
              {oneOffs.map((it) => <ItemCard key={it.id} item={it} />)}
            </>
          ) : null}

          <Pressable
            testID="schedule-add-cta"
            onPress={goAdd}
            style={({ pressed }) => [styles.addCta, pressed && { opacity: 0.85 }]}
          >
            <Ionicons name="add" size={18} color={colors.gold} />
            <Text style={styles.addCtaText}>{t("schedule.addToSchedule")}</Text>
          </Pressable>
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row", alignItems: "center",
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
    borderBottomWidth: 1, borderBottomColor: colors.borderSoft, gap: spacing.md,
  },
  headerTitleWrap: { flex: 1, alignItems: "center" },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.textPrimary },
  headerSub: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, fontSize: 11, marginTop: 1 },
  dowStrip: {
    flexDirection: "row", justifyContent: "space-between",
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
    borderBottomWidth: 1, borderBottomColor: colors.borderSoft, backgroundColor: colors.surface,
  },
  dowChip: { flex: 1, alignItems: "center", paddingVertical: 8, marginHorizontal: 2, borderRadius: radius.md },
  dowChipOn: { backgroundColor: colors.primary },
  dowChipText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary },
  dowChipTextOn: { color: colors.gold },
  dowToday: { width: 5, height: 5, borderRadius: 3, backgroundColor: colors.primary, marginTop: 3 },
  scroll: { padding: spacing.lg, gap: spacing.sm },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl },
  banner: {
    flexDirection: "row", alignItems: "center", gap: 8, padding: spacing.sm + 2,
    borderRadius: radius.md, backgroundColor: "#EEF1F6", marginBottom: spacing.sm,
  },
  bannerText: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 12, lineHeight: 17, color: colors.textSecondary },
  sectionLabel: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 1.4, color: colors.textMuted, marginBottom: 2 },
  empty: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13, color: colors.textMuted, paddingVertical: spacing.sm },
  itemCard: {
    flexDirection: "row", alignItems: "center", gap: spacing.sm,
    padding: spacing.md, borderRadius: radius.lg, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: colors.borderSoft, borderLeftWidth: 4, ...shadow.card,
  },
  itemIcon: { width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center" },
  itemTitle: { fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary },
  itemMetaRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 3 },
  itemMeta: { fontFamily: fonts.uiMedium, fontSize: 11.5, color: colors.textMuted },
  itemDot: { color: colors.textMuted, fontSize: 11 },
  addCta: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    marginTop: spacing.lg, paddingVertical: 13, borderRadius: radius.round, backgroundColor: colors.primary,
  },
  addCtaText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.gold, letterSpacing: 0.4 },
});

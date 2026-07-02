import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Stack, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import {
  checkinCustomChallenge,
  CUSTOM_CHALLENGE_CATEGORIES,
  CustomChallenge,
  deleteCustomChallenge,
  getCustomChallenge,
} from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}
function dateForDay(startIso: string, day: number): string {
  const d = new Date(`${startIso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + (day - 1));
  return d.toISOString().slice(0, 10);
}
function shortDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

export default function CustomChallengeDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [data, setData] = useState<CustomChallenge | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const d = await getCustomChallenge(id);
      setData(d);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const toggle = async (day: number, idx: number, done: boolean) => {
    if (!id) return;
    const key = `${day}:${idx}`;
    setBusy(key);
    try {
      const d = await checkinCustomChallenge(id, day, idx, done);
      setData(d);
    } catch {
      /* ignore */
    } finally {
      setBusy(null);
    }
  };

  const remove = () => {
    if (!id) return;
    const doDelete = async () => {
      await deleteCustomChallenge(id);
      router.back();
    };
    Alert.alert("Delete challenge?", "This cannot be undone.", [
      { text: "Cancel", style: "cancel" },
      { text: "Delete", style: "destructive", onPress: doDelete },
    ]);
  };

  const catIcon = (key: string) =>
    (CUSTOM_CHALLENGE_CATEGORIES.find((c) => c.key === key)?.icon ||
      "ellipse-outline") as keyof typeof Ionicons.glyphMap;

  const today = todayIso();
  const color = data?.color || colors.gold;

  return (
    <View style={{ flex: 1, backgroundColor: colors.background, paddingTop: insets.top }}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="ccd-back" onPress={() => router.back()} hitSlop={12} style={styles.iconBtn}>
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
        </Pressable>
        <Text style={styles.headerTitle} numberOfLines={1}>
          {data?.title || "Challenge"}
        </Text>
        <Pressable testID="ccd-delete" onPress={remove} hitSlop={12} style={styles.iconBtn}>
          <Ionicons name="trash-outline" size={20} color={colors.textMuted} />
        </Pressable>
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={colors.gold} />
      ) : !data ? (
        <Text style={styles.empty}>Challenge not found.</Text>
      ) : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: 60 }}>
          <View style={[styles.banner, { borderColor: color }]}>
            <Ionicons name="create-outline" size={20} color={color} />
            <Text style={styles.bannerText}>
              {data.length_days}-day challenge · {shortDate(data.start_date)} – {shortDate(data.end_date)}
            </Text>
          </View>

          {data.days.map((d) => {
            const dIso = dateForDay(data.start_date, d.day);
            const isToday = dIso === today;
            if (d.items.length === 0) return null;
            return (
              <View
                key={d.day}
                testID={`ccd-day-${d.day}`}
                style={[styles.dayCard, isToday && { borderColor: color, borderWidth: 2 }]}
              >
                <View style={styles.dayHead}>
                  <Text style={styles.dayTitle}>Day {d.day}</Text>
                  <Text style={[styles.daySub, isToday && { color, fontFamily: fonts.uiSemi }]}>
                    {isToday ? "Today" : shortDate(dIso)}
                  </Text>
                </View>
                {d.items.map((it, idx) => {
                  const key = `${d.day}:${idx}`;
                  const done = !!data.completed[key];
                  return (
                    <Pressable
                      key={idx}
                      testID={`ccd-item-${d.day}-${idx}`}
                      onPress={() => toggle(d.day, idx, !done)}
                      style={styles.itemRow}
                    >
                      <Ionicons
                        name={done ? "checkmark-circle" : "ellipse-outline"}
                        size={22}
                        color={done ? color : colors.textMuted}
                      />
                      <Ionicons name={catIcon(it.category)} size={15} color={colors.gold} />
                      <Text style={[styles.itemText, done && styles.itemDone]}>{it.text}</Text>
                      {busy === key ? <ActivityIndicator size="small" color={color} /> : null}
                    </Pressable>
                  );
                })}
              </View>
            );
          })}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  iconBtn: { padding: 4 },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingSemi, fontSize: 17, color: colors.textPrimary },
  empty: { textAlign: "center", marginTop: 40, fontFamily: fonts.bodyRegular, color: colors.textSecondary },
  banner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.lg,
    backgroundColor: colors.surface,
  },
  bannerText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary, flex: 1 },
  dayCard: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  dayHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.sm },
  dayTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  daySub: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary },
  itemRow: { flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 8 },
  itemText: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary },
  itemDone: { textDecorationLine: "line-through", color: colors.textMuted },
});

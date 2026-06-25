import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useFocusEffect, useRouter } from "expo-router";

import { api, JournalEntry } from "@/src/api";
import { moodFor } from "@/src/journal-mood";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { parseISO, todayISO } from "@/src/date-utils";

export default function JournalListScreen() {
  const router = useRouter();
  const [items, setItems] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<"all" | "free" | "examen" | "catechism">("all");

  const load = useCallback(async () => {
    const qs = filter === "all" ? "" : `&kind=${filter}`;
    const res = await api<{ items: JournalEntry[] }>(`/journal?limit=100${qs}`);
    setItems(res.items || []);
  }, [filter]);

  useFocusEffect(
    useCallback(() => {
      let c = false;
      (async () => {
        try {
          await load();
        } finally {
          if (!c) setLoading(false);
        }
      })();
      return () => {
        c = true;
      };
    }, [load]),
  );

  useEffect(() => {
    /* initial load handled by useFocusEffect */
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await load();
    } finally {
      setRefreshing(false);
    }
  };

  const confirmDelete = (id: string) => {
    Alert.alert(
      "Delete this entry?",
      "This cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            try {
              await api<{ ok: boolean }>(`/journal/${id}`, { method: "DELETE" });
              setItems((prev) => prev.filter((i) => i.entry_id !== id));
            } catch (e) {
              console.warn("delete failed", e);
            }
          },
        },
      ],
      { cancelable: true },
    );
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="journal-list-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.headerRow}>
        <Pressable testID="journal-list-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Journal</Text>
        <Pressable
          testID="journal-list-new"
          onPress={() => router.push({ pathname: "/journal", params: { date: todayISO() } })}
          hitSlop={12}
        >
          <Ionicons name="add" size={28} color={colors.gold} />
        </Pressable>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
      >
        {/* Folder filter chips */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.chipsRow}
        >
          {[
            { key: "all", label: "All", icon: "book-outline" as const },
            { key: "free", label: "Reflections", icon: "create-outline" as const },
            { key: "examen", label: "Examen", icon: "sunny-outline" as const },
            { key: "catechism", label: "CCC Reflection", icon: "library-outline" as const },
          ].map((f) => {
            const active = filter === f.key;
            return (
              <Pressable
                key={f.key}
                testID={`journal-filter-${f.key}`}
                onPress={() => setFilter(f.key as typeof filter)}
                style={({ pressed }) => [
                  styles.chip,
                  active && styles.chipActive,
                  pressed && styles.pressed,
                ]}
              >
                <Ionicons
                  name={f.icon}
                  size={14}
                  color={active ? colors.gold : colors.textSecondary}
                />
                <Text style={[styles.chipText, active && styles.chipTextActive]}>{f.label}</Text>
              </Pressable>
            );
          })}
        </ScrollView>

        {loading ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xxl }} />
        ) : items.length === 0 ? (
          <View style={styles.empty}>
            <Ionicons name="book-outline" size={36} color={colors.gold} />
            <Text style={styles.emptyTitle}>No entries yet</Text>
            <Text style={styles.emptyText}>
              Write your first reflection. Even a single sentence is a gift.
            </Text>
            <Pressable
              testID="journal-list-empty-add"
              onPress={() => router.push({ pathname: "/journal", params: { date: todayISO() } })}
              style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
            >
              <Ionicons name="add" size={16} color={colors.gold} />
              <Text style={styles.primaryBtnText}>New Entry</Text>
            </Pressable>
          </View>
        ) : (
          items.map((it) => {
            const m = moodFor(it.mood);
            const date = parseISO(it.date);
            return (
              <Pressable
                key={it.entry_id}
                testID={`journal-row-${it.entry_id}`}
                onPress={() => router.push({ pathname: "/journal", params: { entry: it.entry_id } })}
                onLongPress={() => confirmDelete(it.entry_id)}
                style={({ pressed }) => [styles.row, pressed && styles.pressed]}
              >
                <View style={styles.rowHeader}>
                  <Text style={styles.rowDate}>
                    {date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}
                  </Text>
                  {m ? (
                    <View style={[styles.moodPill, { backgroundColor: m.color }]}>
                      <Ionicons name={m.icon as React.ComponentProps<typeof Ionicons>["name"]} size={11} color="#fff" />
                      <Text style={styles.moodText}>{m.label}</Text>
                    </View>
                  ) : null}
                </View>
                {it.title ? <Text style={styles.rowTitle}>{it.title}</Text> : null}
                <Text style={styles.rowBody} numberOfLines={3}>
                  {it.body}
                </Text>
                <View style={styles.rowFooter}>
                  {it.liturgical?.feast ? (
                    <Text style={styles.rowFeast}>{it.liturgical.feast}</Text>
                  ) : null}
                  {it.kind === "catechism" ? (
                    <View style={styles.kindPill} testID={`journal-kind-ccc-${it.entry_id}`}>
                      <Ionicons name="library" size={11} color={colors.gold} />
                      <Text style={styles.kindPillText}>CCC</Text>
                    </View>
                  ) : it.kind === "examen" ? (
                    <View style={[styles.kindPill, { borderColor: colors.liturgical.purple }]}>
                      <Ionicons name="sunny" size={11} color={colors.liturgical.purple} />
                      <Text style={[styles.kindPillText, { color: colors.liturgical.purple }]}>
                        Examen
                      </Text>
                    </View>
                  ) : null}
                </View>
              </Pressable>
            );
          })
        )}
        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 22, color: colors.textPrimary },
  scroll: { padding: spacing.lg },
  empty: { alignItems: "center", padding: spacing.xl, gap: spacing.sm },
  emptyTitle: { fontFamily: fonts.headingSemi, fontSize: 20, color: colors.textPrimary },
  emptyText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: "center",
    lineHeight: 22,
  },
  primaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.primary,
    paddingVertical: 12,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    marginTop: spacing.md,
  },
  primaryBtnText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 14 },
  row: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginBottom: spacing.md,
    ...shadow.card,
  },
  rowHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  rowDate: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 1.2, color: colors.textMuted },
  moodPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.round,
  },
  moodText: { fontFamily: fonts.uiSemi, fontSize: 10, color: "#fff", letterSpacing: 0.4 },
  rowTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary, marginTop: 4 },
  rowBody: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, lineHeight: 22, marginTop: 4 },
  rowFeast: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12, color: colors.liturgical.red, marginTop: 6 },
  pressed: { opacity: 0.7 },
});

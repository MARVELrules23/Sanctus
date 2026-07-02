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
import { Stack, useFocusEffect, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import {
  deleteMyDevotion,
  deleteMyPrayer,
  listMyDevotions,
  listMyPrayers,
  MyDevotion,
  MyPrayer,
} from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

export default function MyDevotionsHub() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [prayers, setPrayers] = useState<MyPrayer[]>([]);
  const [devotions, setDevotions] = useState<MyDevotion[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [p, d] = await Promise.all([listMyPrayers(), listMyDevotions()]);
      setPrayers(p.items || []);
      setDevotions(d.items || []);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const removePrayer = (id: string) =>
    Alert.alert("Delete prayer?", "This cannot be undone.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          await deleteMyPrayer(id);
          load();
        },
      },
    ]);

  const removeDevotion = (id: string) =>
    Alert.alert("Delete devotional?", "This cannot be undone.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          await deleteMyDevotion(id);
          load();
        },
      },
    ]);

  return (
    <View style={{ flex: 1, backgroundColor: colors.background, paddingTop: insets.top }}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="md-back" onPress={() => router.back()} hitSlop={12} style={styles.iconBtn}>
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
        </Pressable>
        <Text style={styles.headerTitle}>My Prayers & Devotionals</Text>
        <View style={{ width: 30 }} />
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={colors.gold} />
      ) : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: 60 }}>
          {/* Prayers */}
          <View style={styles.sectionHead}>
            <Text style={styles.sectionTitle}>My Prayers</Text>
            <Pressable
              testID="md-new-prayer"
              onPress={() => router.push("/my-devotions/new-prayer")}
              style={styles.newBtn}
            >
              <Ionicons name="add" size={16} color={colors.gold} />
              <Text style={styles.newText}>Prayer</Text>
            </Pressable>
          </View>
          {prayers.length === 0 ? (
            <Text style={styles.empty}>Write your own prayers and keep them close at hand.</Text>
          ) : (
            prayers.map((p) => {
              const open = expanded === p.prayer_id;
              return (
                <Pressable
                  key={p.prayer_id}
                  testID={`md-prayer-${p.prayer_id}`}
                  onPress={() => setExpanded(open ? null : p.prayer_id)}
                  style={styles.card}
                >
                  <View style={styles.cardTop}>
                    <Ionicons name="create-outline" size={18} color={colors.gold} />
                    <Text style={styles.cardTitle}>{p.title}</Text>
                    <Pressable onPress={() => removePrayer(p.prayer_id)} hitSlop={8}>
                      <Ionicons name="trash-outline" size={17} color={colors.textMuted} />
                    </Pressable>
                  </View>
                  {open ? <Text style={styles.prayerBody}>{p.body}</Text> : null}
                </Pressable>
              );
            })
          )}

          {/* Devotionals */}
          <View style={[styles.sectionHead, { marginTop: spacing.xl }]}>
            <Text style={styles.sectionTitle}>My Devotionals</Text>
            <Pressable
              testID="md-new-devotion"
              onPress={() => router.push("/my-devotions/new-devotional")}
              style={styles.newBtn}
            >
              <Ionicons name="add" size={16} color={colors.gold} />
              <Text style={styles.newText}>Devotional</Text>
            </Pressable>
          </View>
          {devotions.length === 0 ? (
            <Text style={styles.empty}>
              Create a devotional to a saint or angel and write your own practices.
            </Text>
          ) : (
            devotions.map((d) => (
              <Pressable
                key={d.devotion_id}
                testID={`md-devotion-${d.devotion_id}`}
                onPress={() => router.push({ pathname: "/my-devotions/[id]", params: { id: d.devotion_id } })}
                style={styles.card}
              >
                <View style={styles.cardTop}>
                  <Ionicons name="rose-outline" size={18} color={colors.gold} />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.cardTitle}>{d.title}</Text>
                    <Text style={styles.cardSub}>To {d.saint_name} · {d.practices.length} practices</Text>
                  </View>
                  <Pressable onPress={() => removeDevotion(d.devotion_id)} hitSlop={8}>
                    <Ionicons name="trash-outline" size={17} color={colors.textMuted} />
                  </Pressable>
                </View>
              </Pressable>
            ))
          )}
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
  sectionHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: spacing.sm },
  sectionTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  newBtn: { flexDirection: "row", alignItems: "center", gap: 3, paddingHorizontal: 12, paddingVertical: 6, borderRadius: radius.round, borderWidth: 1, borderColor: colors.gold },
  newText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold },
  empty: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, lineHeight: 20 },
  card: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft, borderRadius: radius.lg, padding: spacing.md, marginBottom: spacing.sm },
  cardTop: { flexDirection: "row", alignItems: "center", gap: 8 },
  cardTitle: { flex: 1, fontFamily: fonts.uiSemi, fontSize: 15, color: colors.textPrimary },
  cardSub: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textSecondary, marginTop: 2 },
  prayerBody: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary, lineHeight: 24, marginTop: spacing.sm },
});

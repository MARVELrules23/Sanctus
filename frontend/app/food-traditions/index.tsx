import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { Stack, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";

import { getFoodTraditions, FoodTradition } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

export default function FoodTraditionsScreen() {
  const router = useRouter();
  const [items, setItems] = useState<FoodTradition[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await getFoodTraditions();
      setItems(r.items || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="food-traditions-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="food-traditions-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Feast-day Food</Text>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={colors.gold} />
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          <Text style={styles.intro}>
            Recipes to celebrate the Church's feasts and seasons at your own table.
          </Text>
          {items.map((t) => (
            <Pressable
              key={t.slug}
              testID={`food-tradition-${t.slug}`}
              onPress={() => router.push(`/food-traditions/${t.slug}` as any)}
              style={({ pressed }) => [styles.card, pressed && { opacity: 0.85 }]}
            >
              <View style={[styles.iconWrap, { backgroundColor: t.color || colors.primary }]}>
                <Ionicons name={(t.icon as any) || "restaurant-outline"} size={20} color="#FBF6E9" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.cardTitle}>{t.title}</Text>
                <Text style={styles.cardOccasion}>{t.occasion} · {t.origin}</Text>
                <Text style={styles.cardDesc} numberOfLines={2}>{t.description}</Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
            </Pressable>
          ))}
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  scroll: { padding: spacing.lg, gap: spacing.md },
  intro: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, lineHeight: 21, marginBottom: spacing.xs },
  card: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.borderSoft, padding: spacing.md },
  iconWrap: { width: 42, height: 42, borderRadius: 21, alignItems: "center", justifyContent: "center" },
  cardTitle: { fontFamily: fonts.headingSemi, fontSize: 15.5, color: colors.textPrimary },
  cardOccasion: { fontFamily: fonts.uiSemi, fontSize: 11.5, color: colors.gold, marginTop: 1 },
  cardDesc: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textSecondary, lineHeight: 18, marginTop: 3 },
});

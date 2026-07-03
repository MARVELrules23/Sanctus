import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { Stack, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";

import { getColoringPages, ColoringPage } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

export default function ColoringListScreen() {
  const router = useRouter();
  const [items, setItems] = useState<ColoringPage[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await getColoringPages();
      setItems(r.items || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="coloring-list-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="coloring-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Coloring Book</Text>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={colors.gold} />
      ) : items.length === 0 ? (
        <Text style={styles.empty}>Coloring pages are on their way. Check back soon!</Text>
      ) : (
        <ScrollView contentContainerStyle={styles.grid}>
          <Text style={styles.intro}>Pick a picture and color it in with your finger.</Text>
          <View style={styles.gridRow}>
            {items.map((p) => (
              <Pressable
                key={p.slug}
                testID={`coloring-page-${p.slug}`}
                onPress={() => router.push(`/coloring/${p.slug}` as any)}
                style={({ pressed }) => [styles.tile, pressed && { opacity: 0.85 }]}
              >
                <Image source={{ uri: p.image }} style={styles.thumb} resizeMode="contain" />
                <Text style={styles.tileLabel} numberOfLines={1}>{p.title}</Text>
              </Pressable>
            ))}
          </View>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  empty: { textAlign: "center", marginTop: 40, fontFamily: fonts.bodyRegular, color: colors.textSecondary, paddingHorizontal: spacing.lg },
  intro: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, marginBottom: spacing.md },
  grid: { padding: spacing.lg },
  gridRow: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", gap: spacing.md },
  tile: { width: "47%", backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.borderSoft, padding: spacing.sm, marginBottom: spacing.md },
  thumb: { width: "100%", aspectRatio: 1, borderRadius: radius.md, backgroundColor: "#FFFFFF" },
  tileLabel: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textPrimary, marginTop: 8, textAlign: "center" },
});

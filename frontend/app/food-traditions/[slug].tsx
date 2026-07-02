import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";

import { getFoodTradition, FoodTradition } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

export default function FoodTraditionDetail() {
  const router = useRouter();
  const params = useLocalSearchParams<{ slug?: string }>();
  const slug = typeof params.slug === "string" ? params.slug : "";
  const [t, setT] = useState<FoodTradition | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setT(await getFoodTradition(slug));
    } catch {
      setT(null);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => { void load(); }, [load]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="food-tradition-detail">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Ionicons name="chevron-back" size={26} color={colors.primary} onPress={() => router.back()} />
        <Text style={styles.headerTitle} numberOfLines={1}>{t?.title || "Recipe"}</Text>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={colors.gold} />
      ) : !t ? (
        <Text style={styles.empty}>Recipe not found.</Text>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={[styles.hero, { backgroundColor: t.color || colors.primary }]}>
            <Ionicons name={(t.icon as any) || "restaurant-outline"} size={30} color="#FBF6E9" />
            <Text style={styles.heroOccasion}>{t.occasion}</Text>
            <Text style={styles.heroTitle}>{t.title}</Text>
            <Text style={styles.heroOrigin}>{t.origin}</Text>
          </View>

          <Text style={styles.desc}>{t.description}</Text>

          <Text style={styles.sectionLabel}>Ingredients</Text>
          {(t.ingredients || []).map((ing, i) => (
            <View key={i} style={styles.row}>
              <Ionicons name="ellipse" size={6} color={colors.gold} style={{ marginTop: 8 }} />
              <Text style={styles.rowText}>{ing}</Text>
            </View>
          ))}

          <Text style={styles.sectionLabel}>How to make it</Text>
          {(t.steps || []).map((s, i) => (
            <View key={i} style={styles.row}>
              <View style={styles.stepNum}><Text style={styles.stepNumText}>{i + 1}</Text></View>
              <Text style={styles.rowText}>{s}</Text>
            </View>
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
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary, marginHorizontal: spacing.sm },
  empty: { textAlign: "center", marginTop: 40, fontFamily: fonts.bodyRegular, color: colors.textSecondary },
  scroll: { padding: spacing.lg },
  hero: { borderRadius: radius.lg, padding: spacing.lg, alignItems: "center", marginBottom: spacing.md },
  heroOccasion: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 1, color: "#F3E9C9", textTransform: "uppercase", marginTop: 8 },
  heroTitle: { fontFamily: fonts.headingBold, fontSize: 22, color: "#FBF6E9", textAlign: "center", marginTop: 2 },
  heroOrigin: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13, color: "#F3E9C9", marginTop: 4 },
  desc: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary, lineHeight: 23, marginBottom: spacing.md },
  sectionLabel: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 1.5, color: colors.gold, textTransform: "uppercase", marginTop: spacing.md, marginBottom: spacing.sm },
  row: { flexDirection: "row", gap: spacing.sm, alignItems: "flex-start", marginBottom: spacing.sm },
  rowText: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary, lineHeight: 23 },
  stepNum: { width: 22, height: 22, borderRadius: 11, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center", marginTop: 1 },
  stepNumText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold },
});

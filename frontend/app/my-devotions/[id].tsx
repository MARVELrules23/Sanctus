import React, { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Stack, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { getMyDevotion, MyDevotion } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

export default function MyDevotionDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [data, setData] = useState<MyDevotion | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setData(await getMyDevotion(id));
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

  return (
    <View style={{ flex: 1, backgroundColor: colors.background, paddingTop: insets.top }}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="mdd-back" onPress={() => router.back()} hitSlop={12} style={styles.iconBtn}>
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
        </Pressable>
        <Text style={styles.headerTitle} numberOfLines={1}>{data?.title || "Devotional"}</Text>
        <View style={{ width: 30 }} />
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={colors.gold} />
      ) : !data ? (
        <Text style={styles.empty}>Devotional not found.</Text>
      ) : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: 60 }}>
          <View style={styles.saintBanner}>
            <Ionicons name="rose" size={20} color={colors.gold} />
            <Text style={styles.saintName}>To {data.saint_name}</Text>
          </View>
          {data.intro ? <Text style={styles.intro}>{data.intro}</Text> : null}
          <Text style={styles.sectionTitle}>My practices</Text>
          {data.practices.map((p, i) => (
            <View key={i} style={styles.practiceRow}>
              <Ionicons name="flower-outline" size={16} color={colors.goldDark} style={{ marginTop: 2 }} />
              <Text style={styles.practiceText}>{p}</Text>
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  iconBtn: { padding: 4 },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingSemi, fontSize: 17, color: colors.textPrimary },
  empty: { textAlign: "center", marginTop: 40, fontFamily: fonts.bodyRegular, color: colors.textSecondary },
  saintBanner: { flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: "#FBF6E8", borderWidth: 1, borderColor: "#EADfBE", borderRadius: radius.md, padding: spacing.md },
  saintName: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  intro: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary, lineHeight: 24, marginTop: spacing.md },
  sectionTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary, marginTop: spacing.lg, marginBottom: spacing.sm },
  practiceRow: { flexDirection: "row", gap: 8, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft, borderRadius: radius.md, padding: spacing.md, marginBottom: spacing.sm },
  practiceText: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary, lineHeight: 23 },
});

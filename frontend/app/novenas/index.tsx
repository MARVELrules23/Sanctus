import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter, useFocusEffect } from "expo-router";

import { api } from "@/src/api";
import { useI18n } from "@/src/i18n";
import { AutoText as Text } from "@/src/auto-text";
import { colors, fonts, radius, spacing } from "@/src/theme";

type Novena = {
  slug: string; name: string; patron: string; feast: string;
  theme: string; color: string; icon: string; days: number;
};
type Active = { slug: string; start_date: string; end_date: string; completed_days: number[]; total_days: number };

export default function NovenasListScreen() {
  const router = useRouter();
  const { lang } = useI18n();
  const [items, setItems] = useState<Novena[] | null>(null);
  const [active, setActive] = useState<Active | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await api<{ items: Novena[]; active: Active | null }>("/novenas");
      setItems(res.items || []);
      setActive(res.active || null);
    } catch {
      setItems([]);
    }
  }, [lang]);

  useEffect(() => { load(); }, [load]);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const activeNovena = active ? items?.find((n) => n.slug === active.slug) : null;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="novenas-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}><Ionicons name="chevron-back" size={26} color={colors.primary} /></Pressable>
        <Text style={styles.headerTitle}>Novenas</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: spacing.xxl }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false); }} tintColor={colors.gold} />}>
        <Text style={styles.intro}>
          Nine days of prayer, beginning on a date you choose. Pray a little each day; after each day
          a reflection helps you carry the grace forward.
        </Text>

        {active && activeNovena ? (
          <Pressable testID="novena-active-banner" onPress={() => router.push(`/novenas/${active.slug}`)}
            style={({ pressed }) => [styles.activeCard, pressed && styles.pressed]}>
            <View style={[styles.iconWrap, { backgroundColor: activeNovena.color }]}>
              <Ionicons name={activeNovena.icon as any} size={20} color="#FAF9F6" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.activeLabel}>IN PROGRESS</Text>
              <Text style={styles.activeName}>{activeNovena.name}</Text>
              <Text style={styles.activeProg}>{`${active.completed_days.length} of ${active.total_days} days complete`}</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          </Pressable>
        ) : null}

        {items === null ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
        ) : (
          items.map((n) => (
            <Pressable key={n.slug} testID={`novena-card-${n.slug}`} onPress={() => router.push(`/novenas/${n.slug}`)}
              style={({ pressed }) => [styles.card, pressed && styles.pressed]}>
              <View style={[styles.iconWrap, { backgroundColor: n.color }]}>
                <Ionicons name={n.icon as any} size={22} color="#FAF9F6" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.cardTitle}>{n.name}</Text>
                <Text style={styles.cardSub}>{n.theme}</Text>
                <Text style={styles.cardMeta}>FEAST · {n.feast}</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
            </Pressable>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary, flex: 1, textAlign: "center" },
  intro: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, lineHeight: 21, marginBottom: spacing.lg },
  activeCard: { flexDirection: "row", alignItems: "center", gap: spacing.sm, backgroundColor: colors.surface, borderRadius: radius.lg, padding: spacing.md, marginBottom: spacing.lg, borderWidth: 1.5, borderColor: colors.gold },
  activeLabel: { fontFamily: fonts.uiSemi, fontSize: 9, letterSpacing: 1.4, color: colors.gold },
  activeName: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.primary, marginTop: 1 },
  activeProg: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textMuted, marginTop: 2 },
  card: { flexDirection: "row", alignItems: "center", gap: spacing.sm, backgroundColor: colors.surface, borderRadius: radius.lg, padding: spacing.md, marginBottom: spacing.md, borderWidth: 1, borderColor: colors.borderSoft },
  iconWrap: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center" },
  cardTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  cardSub: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12.5, color: colors.textSecondary, marginTop: 2 },
  cardMeta: { fontFamily: fonts.uiMedium, fontSize: 10, color: colors.gold, marginTop: 4, letterSpacing: 1 },
  pressed: { opacity: 0.7 },
});

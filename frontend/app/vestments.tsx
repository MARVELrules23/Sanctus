import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Stack, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { getVestments, VestmentRite } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

export default function VestmentsScreen() {
  const router = useRouter();
  const [rites, setRites] = useState<VestmentRite[]>([]);
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const r = await getVestments();
      setRites(r.rites || []);
    } catch {
      setRites([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const rite = rites[active];

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="vestments-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="vestments-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Vestments</Text>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={colors.gold} />
      ) : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: 60 }}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: spacing.md }}>
            <View style={{ flexDirection: "row", gap: 8 }}>
              {rites.map((r, i) => {
                const sel = active === i;
                return (
                  <Pressable
                    key={r.key}
                    testID={`vestments-rite-${r.key}`}
                    onPress={() => setActive(i)}
                    style={[styles.riteChip, sel && styles.riteChipSel]}
                  >
                    <Text style={[styles.riteChipText, sel && { color: colors.surface }]}>{r.label}</Text>
                  </Pressable>
                );
              })}
            </View>
          </ScrollView>

          {rite ? (
            <>
              <Text style={styles.blurb}>{rite.blurb}</Text>
              {rite.vestments.map((v, i) => (
                <View key={i} style={styles.card} testID={`vestment-${rite.key}-${i}`}>
                  {v.image ? (
                    <Image source={{ uri: v.image }} style={styles.image} resizeMode="cover" />
                  ) : (
                    <View style={[styles.image, styles.imagePlaceholder]}>
                      <Ionicons name="shirt-outline" size={40} color={colors.textMuted} />
                    </View>
                  )}
                  <View style={styles.cardBody}>
                    <Text style={styles.vName}>{v.name}</Text>
                    <Text style={styles.vMeaning}>{v.meaning}</Text>
                  </View>
                </View>
              ))}
              <Text style={styles.credit}>Photos: Wikimedia / Wikipedia (Creative Commons).</Text>
            </>
          ) : null}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  riteChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surface },
  riteChipSel: { backgroundColor: colors.primary, borderColor: colors.primary },
  riteChipText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textSecondary },
  blurb: { fontFamily: fonts.bodyRegular, fontSize: 14.5, color: colors.textSecondary, lineHeight: 22, marginBottom: spacing.md },
  card: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft, borderRadius: radius.lg, overflow: "hidden", marginBottom: spacing.md },
  image: { width: "100%", height: 200, backgroundColor: colors.background },
  imagePlaceholder: { alignItems: "center", justifyContent: "center" },
  cardBody: { padding: spacing.md },
  vName: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary, marginBottom: 6 },
  vMeaning: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary, lineHeight: 23 },
  credit: { fontFamily: fonts.bodyRegular, fontSize: 11.5, color: colors.textMuted, marginTop: spacing.sm, textAlign: "center" },
});

import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Stack, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { getByzantineReadings, ByzantineReadings } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

function isoOf(d: Date): string {
  return d.toISOString().slice(0, 10);
}
function longDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export default function ByzantineReadingsScreen() {
  const router = useRouter();
  const [iso, setIso] = useState(isoOf(new Date()));
  const [data, setData] = useState<ByzantineReadings | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await getByzantineReadings(iso));
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [iso]);

  useEffect(() => {
    load();
  }, [load]);

  const shift = (delta: number) => {
    const d = new Date(`${iso}T00:00:00Z`);
    d.setUTCDate(d.getUTCDate() + delta);
    setIso(isoOf(d));
  };

  const Part = ({ label, part }: { label: string; part?: ByzantineReadings["epistle"] }) => {
    if (!part) return null;
    let lastCh: number | undefined;
    return (
      <View style={styles.partCard}>
        <Text style={styles.partLabel}>{label}</Text>
        <Text style={styles.citation}>{part.citation}</Text>
        {part.verses.map((v, i) => {
          const showCh = v.ch !== undefined && v.ch !== lastCh && i > 0;
          lastCh = v.ch;
          return (
            <React.Fragment key={`${v.ch}-${v.n}`}>
              {showCh ? <Text style={styles.chapterDivider}>Chapter {v.ch}</Text> : null}
              <Text style={styles.verse}>
                <Text style={styles.verseNum}>{v.n} </Text>
                {v.text}
              </Text>
            </React.Fragment>
          );
        })}
        {part.verses.length === 0 ? <Text style={styles.verse}>Text unavailable offline.</Text> : null}
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="byzantine-readings-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="byzantine-readings-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Byzantine Readings</Text>
        <View style={{ width: 26 }} />
      </View>

      <View style={styles.dateRow}>
        <Pressable testID="byz-prev" onPress={() => shift(-1)} style={styles.dateBtn}>
          <Ionicons name="chevron-back" size={18} color={colors.gold} />
        </Pressable>
        <Text style={styles.dateText}>{longDate(iso)}</Text>
        <Pressable testID="byz-next" onPress={() => shift(1)} style={styles.dateBtn}>
          <Ionicons name="chevron-forward" size={18} color={colors.gold} />
        </Pressable>
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={colors.gold} />
      ) : !data || !data.available ? (
        <Text style={styles.empty}>Readings for this day are not available yet.</Text>
      ) : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: 60 }}>
          <Text style={styles.subhead}>Byzantine Divine Liturgy · Paschal cycle (Douay-Rheims)</Text>
          {data.feria_fallback ? (
            <Text style={styles.feriaNote}>
              A weekday — the readings of the most recent Sunday are shown.
            </Text>
          ) : null}
          <Part label="Epistle" part={data.epistle} />
          <Part label="Gospel" part={data.gospel} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  dateRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.lg, paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  dateBtn: { padding: 8 },
  dateText: { flex: 1, textAlign: "center", fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  empty: { textAlign: "center", marginTop: 40, fontFamily: fonts.bodyRegular, color: colors.textSecondary, paddingHorizontal: spacing.lg },
  subhead: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold, marginBottom: spacing.sm, textAlign: "center" },
  feriaNote: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, fontStyle: "italic", marginBottom: spacing.md, textAlign: "center" },
  partCard: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft, borderRadius: radius.lg, padding: spacing.md, marginBottom: spacing.md },
  partLabel: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.liturgical.red },
  citation: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textSecondary, marginBottom: spacing.sm },
  chapterDivider: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 1.2, color: colors.gold, marginTop: spacing.sm, marginBottom: 4 },
  verse: { fontFamily: fonts.bodyRegular, fontSize: 16, color: colors.textPrimary, lineHeight: 26, marginBottom: 4 },
  verseNum: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.gold },
});

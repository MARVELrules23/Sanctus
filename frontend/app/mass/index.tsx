import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { api, LiturgicalDay, Readings } from "@/src/api";
import { useI18n } from "@/src/i18n";
import { AutoText } from "@/src/auto-text";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { todayISO } from "@/src/date-utils";

export default function MassHubScreen() {
  const router = useRouter();
  const { lang } = useI18n();
  const [date] = useState(() => todayISO());
  const [readings, setReadings] = useState<Readings | null>(null);
  const [lit, setLit] = useState<LiturgicalDay | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    api<LiturgicalDay>(`/liturgical/day?date=${date}`).then(setLit).catch(() => undefined);
    const r = await api<Readings>(`/readings?date=${date}`);
    setReadings(r);
  }, [date]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await load();
      } catch (e) {
        console.warn("mass hub load failed", e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [load]);

  const title =
    lang === "es" ? "Misa" : lang === "it" ? "Messa" : "Mass";
  const intro =
    lang === "es"
      ? "El corazón de la vida católica. Lee las lecturas de hoy, reza con el Misal y encuentra una Misa cerca de ti."
      : lang === "it"
        ? "Il cuore della vita cattolica. Leggi le letture di oggi, prega con il Messale e trova una Messa vicino a te."
        : "The source and summit of the Christian life. Read today's Mass, pray the Order of Mass, and find a Mass near you.";

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="mass-hub-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="mass-hub-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>{title}</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.intro}>
          <Text style={styles.eyebrow}>SANCTA MISSA</Text>
          <AutoText style={styles.introBody}>{intro}</AutoText>
        </View>

        <Ornament />

        {/* Today's Mass Readings — full, changing daily */}
        <Pressable
          testID="mass-readings-card"
          onPress={() => router.push({ pathname: "/readings", params: { date } })}
          style={({ pressed }) => [styles.card, styles.featured, pressed && styles.pressed]}
        >
          <View style={styles.cardHeader}>
            <View style={[styles.iconWrap, { backgroundColor: colors.liturgical.red }]}>
              <Ionicons name="bookmark-outline" size={20} color="#FAF9F6" />
            </View>
            <View style={{ flex: 1 }}>
              <AutoText style={styles.cardTitle}>
                {lang === "es" ? "Lecturas de hoy" : lang === "it" ? "Letture di oggi" : "Today's Mass Readings"}
              </AutoText>
              <AutoText style={styles.cardSub}>
                {readings?.liturgical_title || lit?.feast || lit?.season || "Read the full readings"}
              </AutoText>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          </View>
          {loading ? (
            <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.sm }} />
          ) : readings ? (
            <View style={styles.readingRows}>
              {readings.gospel ? (
                <View style={styles.readingRow}>
                  <AutoText style={styles.readingLabel}>Gospel</AutoText>
                  <Text style={styles.readingCite}>{readings.gospel}</Text>
                </View>
              ) : null}
              {readings.first_reading ? (
                <View style={styles.readingRow}>
                  <AutoText style={styles.readingLabel}>1st</AutoText>
                  <Text style={styles.readingCite}>{readings.first_reading}</Text>
                </View>
              ) : null}
              {readings.psalm ? (
                <View style={styles.readingRow}>
                  <AutoText style={styles.readingLabel}>Psalm</AutoText>
                  <Text style={styles.readingCite}>{readings.psalm}</Text>
                </View>
              ) : null}
              <Text style={styles.readMore}>
                {lang === "es" ? "Toca para leer el texto completo →" : lang === "it" ? "Tocca per leggere il testo completo →" : "Tap to read the full text →"}
              </Text>
            </View>
          ) : null}
        </Pressable>

        {/* Traditional Latin Mass Readings (1962) */}
        <Pressable
          testID="mass-tlm-readings-card"
          onPress={() => router.push("/tlm-readings" as any)}
          style={({ pressed }) => [styles.card, pressed && styles.pressed]}
        >
          <View style={styles.cardHeader}>
            <View style={[styles.iconWrap, { backgroundColor: "#8A1C1C" }]}>
              <Ionicons name="rose-outline" size={20} color="#FAF9F6" />
            </View>
            <View style={{ flex: 1 }}>
              <AutoText style={styles.cardTitle}>
                {lang === "es" ? "Lecturas de la Misa Tradicional (1962)" : lang === "it" ? "Letture della Messa Tradizionale (1962)" : "Traditional Latin Mass Readings"}
              </AutoText>
              <AutoText style={styles.cardSub}>
                {lang === "es"
                  ? "Epístola y Evangelio · Misal de 1962 (Douay-Rheims)"
                  : lang === "it"
                    ? "Epistola e Vangelo · Messale del 1962 (Douay-Rheims)"
                    : "Epistle & Gospel · 1962 Missal (Douay-Rheims)"}
              </AutoText>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          </View>
        </Pressable>

        {/* Byzantine Divine Liturgy Readings */}
        <Pressable
          testID="mass-byzantine-readings-card"
          onPress={() => router.push("/byzantine-readings" as any)}
          style={({ pressed }) => [styles.card, pressed && styles.pressed]}
        >
          <View style={styles.cardHeader}>
            <View style={[styles.iconWrap, { backgroundColor: "#1E4E79" }]}>
              <Ionicons name="flower-outline" size={20} color="#FAF9F6" />
            </View>
            <View style={{ flex: 1 }}>
              <AutoText style={styles.cardTitle}>
                {lang === "es" ? "Lecturas de la Divina Liturgia" : lang === "it" ? "Letture della Divina Liturgia" : "Byzantine Divine Liturgy Readings"}
              </AutoText>
              <AutoText style={styles.cardSub}>
                {lang === "es"
                  ? "Epístola y Evangelio · Ciclo Pascual bizantino"
                  : lang === "it"
                    ? "Epistola e Vangelo · Ciclo pasquale bizantino"
                    : "Epistle & Gospel · Byzantine Paschal cycle"}
              </AutoText>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          </View>
        </Pressable>

        {/* Mass Missals */}
        <Pressable
          testID="mass-missals-card"
          onPress={() => router.push("/missals" as any)}
          style={({ pressed }) => [styles.card, pressed && styles.pressed]}
        >
          <View style={styles.cardHeader}>
            <View style={[styles.iconWrap, { backgroundColor: "#7A5C00" }]}>
              <Ionicons name="book" size={20} color="#FAF9F6" />
            </View>
            <View style={{ flex: 1 }}>
              <AutoText style={styles.cardTitle}>
                {lang === "es" ? "Misales de la Misa" : lang === "it" ? "Messali" : "Mass Missals"}
              </AutoText>
              <AutoText style={styles.cardSub}>
                {lang === "es"
                  ? "Novus Ordo · Latín Tradicional · Ritos Orientales"
                  : lang === "it"
                    ? "Novus Ordo · Latino Tradizionale · Riti Orientali"
                    : "Novus Ordo · Traditional Latin · Eastern Rites"}
              </AutoText>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          </View>
        </Pressable>

        {/* Vestments reference */}
        <Pressable
          testID="mass-vestments-card"
          onPress={() => router.push("/vestments" as any)}
          style={({ pressed }) => [styles.card, pressed && styles.pressed]}
        >
          <View style={styles.cardHeader}>
            <View style={[styles.iconWrap, { backgroundColor: "#6B2D5C" }]}>
              <Ionicons name="shirt-outline" size={20} color="#FAF9F6" />
            </View>
            <View style={{ flex: 1 }}>
              <AutoText style={styles.cardTitle}>
                {lang === "es" ? "Vestiduras litúrgicas" : lang === "it" ? "Paramenti liturgici" : "Vestments"}
              </AutoText>
              <AutoText style={styles.cardSub}>
                {lang === "es"
                  ? "Las vestiduras del sacerdote por rito y su significado"
                  : lang === "it"
                    ? "I paramenti del sacerdote per rito e il loro significato"
                    : "The priest's vestments by rite & their meaning"}
              </AutoText>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          </View>
        </Pressable>

        {/* Find nearby Mass */}
        <Pressable
          testID="mass-nearby-card"
          onPress={() => router.push("/churches" as any)}
          style={({ pressed }) => [styles.card, pressed && styles.pressed]}
        >
          <View style={styles.cardHeader}>
            <View style={[styles.iconWrap, { backgroundColor: "#1E5631" }]}>
              <Ionicons name="location-outline" size={20} color="#FAF9F6" />
            </View>
            <View style={{ flex: 1 }}>
              <AutoText style={styles.cardTitle}>
                {lang === "es" ? "Encontrar Misa cercana" : lang === "it" ? "Trova Messa vicina" : "Find a Mass Near You"}
              </AutoText>
              <AutoText style={styles.cardSub}>
                {lang === "es"
                  ? "Iglesias católicas cercanas y direcciones"
                  : lang === "it"
                    ? "Chiese cattoliche vicine e indirizzi"
                    : "Nearby Catholic churches & directions"}
              </AutoText>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          </View>
        </Pressable>

        <View style={{ height: spacing.xxl }} />
      </ScrollView>
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
  headerTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
    flex: 1,
    textAlign: "center",
    marginHorizontal: spacing.sm,
  },
  scroll: { padding: spacing.lg },
  intro: { marginBottom: spacing.md },
  eyebrow: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 2.5,
    color: colors.gold,
  },
  introBody: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
    marginTop: spacing.sm,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginTop: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  featured: { borderColor: colors.gold, borderWidth: 1.5 },
  cardHeader: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  cardTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  cardSub: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  readingRows: { marginTop: spacing.sm },
  readingRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: 6 },
  readingLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1.2,
    color: colors.textMuted,
    width: 46,
  },
  readingCite: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary, flex: 1 },
  readMore: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold, marginTop: spacing.sm },
  pressed: { opacity: 0.7 },
});

import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import { useAudioPlayer, useAudioPlayerStatus } from "expo-audio";

import { getCompanion, getCompanionImage, CompanionDetail } from "@/src/api";
import LofiSaintBackground from "@/src/components/LofiSaintBackground";
import { colors, fonts, radius, spacing } from "@/src/theme";

// Public-domain Gregorian chant (Internet Archive) — soft looping ambiance.
const CHANT_URL = "https://archive.org/download/GregorianChantMass/02Track2.mp3";

export default function CompanionScreen() {
  const router = useRouter();
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const [data, setData] = useState<CompanionDetail | null>(null);
  const [image, setImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Soft looping Gregorian chant ambiance — auto-tries on open, stops on leave.
  const player = useAudioPlayer(CHANT_URL);
  const audioStatus = useAudioPlayerStatus(player);
  const chantOn = !!audioStatus?.playing;

  useEffect(() => {
    try {
      player.loop = true;
      player.volume = 0.32;
    } catch {/* ignore */}
    const t = setTimeout(() => { try { player.play(); } catch {/* autoplay may be blocked on web */} }, 700);
    return () => {
      clearTimeout(t);
      try { player.pause(); } catch {/* ignore */}
    };
  }, [player]);

  const toggleChant = useCallback(() => {
    try { chantOn ? player.pause() : player.play(); } catch {/* ignore */}
  }, [player, chantOn]);

  const load = useCallback(async () => {
    if (!slug) return;
    try {
      const d = await getCompanion(slug);
      setData(d);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  // Poll for the (lazily generated) illustration until it's ready.
  useEffect(() => {
    let alive = true;
    let tries = 0;
    const fetchImg = async () => {
      if (!slug || !alive) return;
      try {
        const r = await getCompanionImage(slug);
        if (alive && r.image) { setImage(r.image); return; }
      } catch {/* ignore */}
      tries += 1;
      if (alive && tries < 8) setTimeout(fetchImg, 3000);
    };
    fetchImg();
    return () => { alive = false; };
  }, [slug]);

  useEffect(() => { load(); }, [load]);

  return (
    <View style={styles.root} testID="companion-screen">
      <Stack.Screen options={{ headerShown: false }} />

      {/* Animated lo-fi hero */}
      <View style={styles.hero}>
        <LofiSaintBackground image={image} />
        <SafeAreaView edges={["top"]} style={styles.heroSafe}>
          <View style={styles.topRow}>
            <Pressable testID="companion-back" onPress={() => router.back()} hitSlop={12} style={styles.iconBtn}>
              <Ionicons name="chevron-back" size={26} color="#FFF8EA" />
            </Pressable>
            <Pressable testID="companion-chant-toggle" onPress={toggleChant} hitSlop={12} style={styles.iconBtn}>
              <Ionicons name={chantOn ? "musical-notes" : "musical-notes-outline"} size={20} color={chantOn ? "#FFE6A8" : "#FFF8EA"} />
            </Pressable>
          </View>
          <View style={{ flex: 1 }} />
          {data ? (
            <View style={styles.heroText}>
              <Text style={styles.heroEyebrow}>WALKING WITH</Text>
              <Text style={styles.heroName}>{data.name}</Text>
              {data.feast ? <Text style={styles.heroFeast}>Feast · {data.feast}</Text> : null}
              {!image ? (
                <View style={styles.imgLoading}>
                  <ActivityIndicator size="small" color="#FFE6A8" />
                  <Text style={styles.imgLoadingText}>Painting a lo-fi icon…</Text>
                </View>
              ) : null}
            </View>
          ) : null}
        </SafeAreaView>
      </View>

      {loading || !data ? (
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      ) : (
        <ScrollView style={styles.body} contentContainerStyle={styles.bodyContent} showsVerticalScrollIndicator={false}>
          {/* Why this saint matters */}
          <View style={styles.cardHead}>
            <Ionicons name="sparkles-outline" size={16} color={colors.gold} />
            <Text style={styles.cardHeadText}>Why walk with {data.name}</Text>
          </View>
          <Text style={styles.importance}>{data.importance}</Text>

          {/* Daily act */}
          <View style={styles.actCard} testID="companion-daily-act">
            <View style={styles.cardHead}>
              <Ionicons name="leaf-outline" size={16} color={colors.gold} />
              <Text style={styles.cardHeadText}>Today's act to draw closer</Text>
            </View>
            <Text style={styles.actText}>{data.daily_act.text}</Text>
            <Text style={styles.actMeta}>A different act each day · {data.daily_act.total} in the cycle</Text>
          </View>

          {/* Virtues to imitate */}
          <View style={styles.cardHead}>
            <Ionicons name="ribbon-outline" size={16} color={colors.gold} />
            <Text style={styles.cardHeadText}>Virtues to imitate</Text>
          </View>
          {data.virtues.map((v, i) => (
            <View key={i} style={styles.virtue}>
              <Ionicons name="flower-outline" size={15} color={colors.goldDark} style={{ marginTop: 2 }} />
              <View style={{ flex: 1 }}>
                <Text style={styles.virtueName}>{v.name}</Text>
                <Text style={styles.virtueHow}>{v.how}</Text>
              </View>
            </View>
          ))}
          <Pressable
            testID="companion-virtus-link"
            onPress={() => router.push("/virtus" as any)}
            style={({ pressed }) => [styles.softBtn, pressed && { opacity: 0.85 }]}
          >
            <Ionicons name="barbell-outline" size={16} color={colors.primary} />
            <Text style={styles.softBtnText}>Practice these in Virtus</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
          </Pressable>

          {/* Prayer actions */}
          <View style={styles.cardHead}>
            <Ionicons name="book-outline" size={16} color={colors.gold} />
            <Text style={styles.cardHeadText}>Pray with {data.name}</Text>
          </View>
          {data.novena_slug ? (
            <Pressable
              testID="companion-novena-btn"
              onPress={() => router.push(`/novenas/${data.novena_slug}` as any)}
              style={({ pressed }) => [styles.primaryBtn, pressed && { opacity: 0.9 }]}
            >
              <Ionicons name="calendar-outline" size={18} color="#FFF8EA" />
              <Text style={styles.primaryBtnText}>Pray the Novena to {data.name}</Text>
            </Pressable>
          ) : null}
          {data.has_consecration ? (
            <Pressable
              testID="companion-consecration-btn"
              onPress={() => router.push("/consecration" as any)}
              style={({ pressed }) => [styles.consecBtn, pressed && { opacity: 0.9 }]}
            >
              <Ionicons name="shield-half-outline" size={18} color="#3A2E12" />
              <View style={{ flex: 1 }}>
                <Text style={styles.consecBtnText}>33-Day Consecration to St. Joseph</Text>
                <Text style={styles.consecBtnSub}>Begin any day — give yourself to Jesus through St. Joseph</Text>
              </View>
            </Pressable>
          ) : null}

          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.background },
  hero: { height: 320, backgroundColor: "#2B2440", overflow: "hidden" },
  heroSafe: { flex: 1, paddingHorizontal: spacing.md, paddingBottom: spacing.md },
  topRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: spacing.sm },
  iconBtn: { width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center", backgroundColor: "rgba(0,0,0,0.25)" },
  heroText: { gap: 2 },
  heroEyebrow: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 2, color: "#FFE6A8" },
  heroName: { fontFamily: fonts.headingBold, fontSize: 30, color: "#FFF8EA", lineHeight: 36 },
  heroFeast: { fontFamily: fonts.bodyRegular, fontSize: 13, color: "#E9DDC4", marginTop: 2 },
  imgLoading: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 8 },
  imgLoadingText: { fontFamily: fonts.bodyItalic, fontSize: 12, color: "#E9DDC4" },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  body: { flex: 1 },
  bodyContent: { padding: spacing.lg },
  cardHead: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: spacing.lg, marginBottom: spacing.sm },
  cardHeadText: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 0.6, textTransform: "uppercase", color: colors.gold },
  importance: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textSecondary, lineHeight: 23 },
  actCard: { backgroundColor: "#FBF4DF", borderWidth: 1, borderColor: "#EBDDB4", borderRadius: radius.lg, padding: spacing.md, marginTop: spacing.lg },
  actText: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.primary, lineHeight: 23 },
  actMeta: { fontFamily: fonts.bodyItalic, fontSize: 12, color: colors.textMuted, marginTop: 6 },
  virtue: { flexDirection: "row", gap: 8, alignItems: "flex-start", marginBottom: spacing.sm },
  virtueName: { fontFamily: fonts.uiSemi, fontSize: 14.5, color: colors.primary },
  virtueHow: { fontFamily: fonts.bodyRegular, fontSize: 13.5, color: colors.textSecondary, lineHeight: 20, marginTop: 1 },
  softBtn: { flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft, borderRadius: radius.md, padding: spacing.md, marginTop: spacing.xs },
  softBtnText: { flex: 1, fontFamily: fonts.uiSemi, fontSize: 14, color: colors.primary },
  primaryBtn: { flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: colors.primary, borderRadius: radius.md, padding: spacing.md, marginBottom: spacing.sm },
  primaryBtnText: { flex: 1, fontFamily: fonts.uiSemi, fontSize: 15, color: "#FFF8EA" },
  consecBtn: { flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: colors.gold, borderRadius: radius.md, padding: spacing.md },
  consecBtnText: { fontFamily: fonts.uiSemi, fontSize: 15, color: "#3A2E12" },
  consecBtnSub: { fontFamily: fonts.bodyRegular, fontSize: 12, color: "#5A4A1E", marginTop: 2, lineHeight: 16 },
});

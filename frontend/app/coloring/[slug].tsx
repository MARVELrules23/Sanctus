import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, Alert, Image, PanResponder, Platform, Pressable, StyleSheet, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import AsyncStorage from "@react-native-async-storage/async-storage";
import Svg, { Path } from "react-native-svg";
import { captureRef } from "react-native-view-shot";
import * as Sharing from "expo-sharing";

import { getColoringPages, ColoringPage } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

const PALETTE = ["#E23B3B", "#F5A623", "#F8E71C", "#5BB543", "#3E8ED0", "#8E44AD", "#8B5A2B", "#F49AC2", "#2C3E50", "#FFFFFF"];
type Stroke = { d: string; color: string };

export default function ColoringCanvas() {
  const router = useRouter();
  const params = useLocalSearchParams<{ slug?: string }>();
  const slug = typeof params.slug === "string" ? params.slug : "";
  const [page, setPage] = useState<ColoringPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const [current, setCurrent] = useState<string>("");
  const [color, setColor] = useState<string>(PALETTE[0]);
  const [sharing, setSharing] = useState(false);
  const colorRef = useRef(color);
  colorRef.current = color;
  const currentRef = useRef("");
  const captureRefView = useRef<View>(null);

  const storageKey = `coloring_progress_${slug}`;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await getColoringPages();
      setPage((r.items || []).find((p) => p.slug === slug) || null);
      const saved = await AsyncStorage.getItem(storageKey);
      if (saved) setStrokes(JSON.parse(saved));
    } catch {
      setPage(null);
    } finally {
      setLoading(false);
    }
  }, [slug, storageKey]);

  useEffect(() => { void load(); }, [load]);

  const persist = useCallback((next: Stroke[]) => {
    AsyncStorage.setItem(storageKey, JSON.stringify(next)).catch(() => {});
  }, [storageKey]);

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => true,
        onMoveShouldSetPanResponder: () => true,
        onPanResponderGrant: (e) => {
          const { locationX, locationY } = e.nativeEvent;
          currentRef.current = `M ${locationX.toFixed(1)} ${locationY.toFixed(1)}`;
          setCurrent(currentRef.current);
        },
        onPanResponderMove: (e) => {
          const { locationX, locationY } = e.nativeEvent;
          currentRef.current += ` L ${locationX.toFixed(1)} ${locationY.toFixed(1)}`;
          setCurrent(currentRef.current);
        },
        onPanResponderRelease: () => {
          const d = currentRef.current;
          currentRef.current = "";
          setCurrent("");
          if (d.includes("L")) {
            setStrokes((prev) => {
              const next = [...prev, { d, color: colorRef.current }];
              persist(next);
              return next;
            });
          }
        },
      }),
    [persist],
  );

  const undo = () => setStrokes((prev) => { const next = prev.slice(0, -1); persist(next); return next; });
  const clear = () => { setStrokes([]); persist([]); };

  const onShare = async () => {
    if (Platform.OS === "web") {
      Alert.alert("Saving pictures", "Saving and sharing your picture works on the Sanctus app (iOS/Android), not the web preview.");
      return;
    }
    setSharing(true);
    try {
      const uri = await captureRef(captureRefView, { format: "png", quality: 1 });
      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(uri, { mimeType: "image/png", dialogTitle: page?.title || "My coloring page" });
      } else {
        Alert.alert("Saved", "Your picture was saved.");
      }
    } catch {
      Alert.alert("Couldn't save", "Something went wrong saving your picture. Please try again.");
    } finally {
      setSharing(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="coloring-canvas-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="coloring-canvas-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle} numberOfLines={1}>{page?.title || "Color"}</Text>
        <View style={{ flexDirection: "row", gap: spacing.md }}>
          <Pressable testID="coloring-undo" onPress={undo} hitSlop={10}><Ionicons name="arrow-undo" size={22} color={colors.primary} /></Pressable>
          <Pressable testID="coloring-clear" onPress={clear} hitSlop={10}><Ionicons name="trash-outline" size={22} color={colors.liturgical?.red || "#8A1C1C"} /></Pressable>
          <Pressable testID="coloring-share" onPress={onShare} hitSlop={10} disabled={sharing}>
            {sharing ? <ActivityIndicator size="small" color={colors.gold} /> : <Ionicons name="share-outline" size={22} color={colors.gold} />}
          </Pressable>
        </View>
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={colors.gold} />
      ) : !page ? (
        <Text style={styles.empty}>Page not found.</Text>
      ) : (
        <View style={{ flex: 1 }}>
          <View ref={captureRefView} collapsable={false} style={styles.canvasWrap} {...panResponder.panHandlers} testID="coloring-canvas">
            <Image source={{ uri: page.image }} style={styles.lineArt} resizeMode="contain" />
            <Svg style={styles.overlay}>
              {strokes.map((s, i) => (
                <Path key={i} d={s.d} stroke={s.color} strokeWidth={22} strokeLinecap="round" strokeLinejoin="round" fill="none" opacity={0.55} />
              ))}
              {current ? (
                <Path d={current} stroke={color} strokeWidth={22} strokeLinecap="round" strokeLinejoin="round" fill="none" opacity={0.55} />
              ) : null}
            </Svg>
          </View>

          <View style={styles.palette}>
            {PALETTE.map((c) => (
              <Pressable
                key={c}
                testID={`coloring-color-${c}`}
                onPress={() => setColor(c)}
                style={[styles.swatch, { backgroundColor: c }, color === c && styles.swatchActive]}
              />
            ))}
          </View>
          <Text style={styles.hint}>Pick a color and draw with your finger. Colors are see-through so the picture shows.</Text>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary, marginHorizontal: spacing.sm },
  empty: { textAlign: "center", marginTop: 40, fontFamily: fonts.bodyRegular, color: colors.textSecondary },
  canvasWrap: { flex: 1, margin: spacing.md, borderRadius: radius.lg, overflow: "hidden", backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: colors.borderSoft },
  lineArt: { ...StyleSheet.absoluteFillObject, width: "100%", height: "100%", pointerEvents: "none" },
  overlay: { ...StyleSheet.absoluteFillObject, pointerEvents: "none" },
  palette: { flexDirection: "row", flexWrap: "wrap", justifyContent: "center", gap: spacing.sm, paddingHorizontal: spacing.md },
  swatch: { width: 34, height: 34, borderRadius: 17, borderWidth: 1, borderColor: colors.borderSoft },
  swatchActive: { borderWidth: 3, borderColor: colors.primary, transform: [{ scale: 1.15 }] },
  hint: { fontFamily: fonts.bodyRegular, fontSize: 11.5, color: colors.textMuted, textAlign: "center", paddingHorizontal: spacing.lg, paddingVertical: spacing.sm },
});

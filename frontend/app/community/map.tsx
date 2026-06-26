import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { listCatholicSites, CatholicSite } from "@/src/api";
import CatholicMapView from "@/src/components/catholic-map/CatholicMapView";
import { colors, fonts, radius, spacing } from "@/src/theme";

const TYPE_COLORS: Record<string, string> = {
  basilica: "#D4AF37",
  cathedral: "#9C6B3F",
  shrine: "#7A86C4",
  apparition: "#3F7AC4",
  monastery: "#5B8A5B",
  church: "#B05A7A",
};

const TYPE_LABELS: Record<string, string> = {
  basilica: "Basilica",
  cathedral: "Cathedral",
  shrine: "Shrine",
  apparition: "Apparition",
  monastery: "Monastery",
  church: "Church",
};

function DetailSection({ icon, title, items }: { icon: any; title: string; items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <View style={styles.section}>
      <View style={styles.sectionHead}>
        <Ionicons name={icon} size={15} color={colors.gold} />
        <Text style={styles.sectionTitle}>{title}</Text>
      </View>
      {items.map((it, i) => (
        <View key={i} style={styles.bulletRow}>
          <Text style={styles.bulletDot}>•</Text>
          <Text style={styles.bulletText}>{it}</Text>
        </View>
      ))}
    </View>
  );
}

export default function CatholicMapScreen() {
  const router = useRouter();
  const [sites, setSites] = useState<CatholicSite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<CatholicSite | null>(null);
  const [showList, setShowList] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await listCatholicSites();
      setSites(res.items);
    } catch (e: any) {
      setError(e?.message || "Could not load the map.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const markers = useMemo(
    () => sites.map((s) => ({ id: s.site_id, name: s.name, type: s.type, lat: s.lat, lng: s.lng })),
    [sites],
  );

  const onSelectId = useCallback(
    (id: string) => {
      const s = sites.find((x) => x.site_id === id);
      if (s) setSelected(s);
    },
    [sites],
  );

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="catholic-map-screen">
      <Stack.Screen options={{ headerShown: false }} />

      <View style={styles.header}>
        <Pressable testID="map-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.headerTitle}>Catholic World Map</Text>
        </View>
        <Pressable testID="map-toggle-list" onPress={() => setShowList((v) => !v)} hitSlop={10}>
          <Ionicons name={showList ? "map-outline" : "list-outline"} size={22} color={colors.primary} />
        </Pressable>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
        </View>
      ) : error ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable onPress={load} style={({ pressed }) => [styles.retry, pressed && { opacity: 0.7 }]}>
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      ) : showList ? (
        <ScrollView contentContainerStyle={styles.listScroll}>
          <Text style={styles.intro}>Explore {sites.length} significant Catholic places across the world.</Text>
          {sites.map((s) => (
            <Pressable
              key={s.site_id}
              testID={`map-list-${s.slug}`}
              onPress={() => setSelected(s)}
              style={({ pressed }) => [styles.listRow, pressed && { opacity: 0.85 }]}
            >
              <View style={[styles.dot, { backgroundColor: TYPE_COLORS[s.type] || colors.gold }]} />
              <View style={{ flex: 1 }}>
                <Text style={styles.listTitle} numberOfLines={1}>{s.name}</Text>
                <Text style={styles.listSub} numberOfLines={1}>{s.city}, {s.country}</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
            </Pressable>
          ))}
        </ScrollView>
      ) : (
        <View style={styles.mapWrap}>
          <CatholicMapView markers={markers} onSelect={onSelectId} />
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.legend}
            contentContainerStyle={styles.legendContent}
          >
            {Object.keys(TYPE_LABELS).map((t) => (
              <View key={t} style={styles.legendItem}>
                <View style={[styles.dot, { backgroundColor: TYPE_COLORS[t] }]} />
                <Text style={styles.legendText}>{TYPE_LABELS[t]}</Text>
              </View>
            ))}
          </ScrollView>
        </View>
      )}

      {/* Detail sheet */}
      <Modal visible={!!selected} animationType="slide" transparent onRequestClose={() => setSelected(null)}>
        <View style={styles.modalBackdrop}>
          <Pressable style={styles.backdropFill} onPress={() => setSelected(null)} />
          <View style={styles.sheet}>
            {selected ? (
              <ScrollView contentContainerStyle={styles.sheetScroll} showsVerticalScrollIndicator={false}>
                <View style={styles.sheetHandle} />
                <View style={styles.typeBadge}>
                  <View style={[styles.dot, { backgroundColor: TYPE_COLORS[selected.type] || colors.gold }]} />
                  <Text style={styles.typeBadgeText}>{TYPE_LABELS[selected.type] || "Place"}</Text>
                </View>
                <Text style={styles.sheetTitle}>{selected.name}</Text>
                <View style={styles.locRow}>
                  <Ionicons name="location-outline" size={14} color={colors.textMuted} />
                  <Text style={styles.sheetLoc}>
                    {selected.city}, {selected.country}
                    {selected.founded ? `  ·  ${selected.founded}` : ""}
                  </Text>
                </View>

                {selected.history ? <Text style={styles.history}>{selected.history}</Text> : null}

                <DetailSection icon="diamond-outline" title="Relics" items={selected.relics} />
                <DetailSection icon="person-outline" title="Saints" items={selected.saints} />
                <DetailSection icon="sparkles-outline" title="Miracles & Apparitions" items={selected.miracles} />

                {selected.source_url ? (
                  <Pressable
                    testID="map-source-link"
                    onPress={() => Linking.openURL(selected.source_url!)}
                    style={({ pressed }) => [styles.sourceBtn, pressed && { opacity: 0.8 }]}
                  >
                    <Ionicons name="open-outline" size={15} color={colors.primary} />
                    <Text style={styles.sourceText}>Learn more</Text>
                  </Pressable>
                ) : null}

                <Pressable
                  testID="map-close"
                  onPress={() => setSelected(null)}
                  style={({ pressed }) => [styles.closeBtn, pressed && { opacity: 0.85 }]}
                >
                  <Text style={styles.closeText}>Close</Text>
                </Pressable>
              </ScrollView>
            ) : null}
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  headerTitleWrap: { flex: 1, alignItems: "center" },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.primary },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.lg, gap: spacing.md },
  errorText: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, textAlign: "center" },
  retry: { backgroundColor: colors.primary, paddingHorizontal: spacing.lg, paddingVertical: spacing.sm, borderRadius: radius.md },
  retryText: { fontFamily: fonts.uiSemi, color: "#fff" },
  mapWrap: { flex: 1 },
  legend: {
    position: "absolute",
    bottom: spacing.md,
    left: 0,
    right: 0,
    maxHeight: 40,
  },
  legendContent: { paddingHorizontal: spacing.md, gap: spacing.sm, alignItems: "center" },
  legendItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.round,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  legendText: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textSecondary },
  dot: { width: 11, height: 11, borderRadius: 6 },
  listScroll: { padding: spacing.md, gap: spacing.sm },
  intro: { fontFamily: fonts.bodyItalic, fontSize: 13.5, color: colors.textSecondary, marginBottom: spacing.sm },
  listRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  listTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.primary },
  listSub: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textMuted, marginTop: 1 },
  modalBackdrop: { flex: 1, justifyContent: "flex-end", backgroundColor: "rgba(0,0,0,0.35)" },
  backdropFill: { ...StyleSheet.absoluteFillObject },
  sheet: {
    backgroundColor: colors.background,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: "85%",
  },
  sheetScroll: { padding: spacing.lg, paddingBottom: spacing.xl ?? 32 },
  sheetHandle: { alignSelf: "center", width: 40, height: 4, borderRadius: 2, backgroundColor: colors.borderSoft, marginBottom: spacing.md },
  typeBadge: { flexDirection: "row", alignItems: "center", gap: 6, alignSelf: "flex-start", marginBottom: 6 },
  typeBadgeText: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 0.5, textTransform: "uppercase", color: colors.textSecondary },
  sheetTitle: { fontFamily: fonts.headingBold, fontSize: 24, color: colors.primary, lineHeight: 28 },
  locRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 4, marginBottom: spacing.md },
  sheetLoc: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textMuted },
  history: { fontFamily: fonts.bodyRegular, fontSize: 14.5, color: colors.textSecondary, lineHeight: 22 },
  section: { marginTop: spacing.lg },
  sectionHead: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 6 },
  sectionTitle: { fontFamily: fonts.uiSemi, fontSize: 13, letterSpacing: 0.5, textTransform: "uppercase", color: colors.primary },
  bulletRow: { flexDirection: "row", gap: 8, marginBottom: 4 },
  bulletDot: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.gold, lineHeight: 21 },
  bulletText: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, lineHeight: 21 },
  sourceBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    alignSelf: "flex-start",
    marginTop: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.round,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  sourceText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.primary },
  closeBtn: {
    marginTop: spacing.lg,
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    paddingVertical: 13,
    alignItems: "center",
  },
  closeText: { fontFamily: fonts.uiSemi, fontSize: 15, color: "#fff" },
});

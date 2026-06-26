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

import { listCatholicSites, nearbyCatholicSites, createScheduleItem, CatholicSite } from "@/src/api";
import * as Location from "expo-location";
import CatholicMapView from "@/src/components/catholic-map/CatholicMapView";
import { colors, fonts, radius, spacing } from "@/src/theme";

// Upcoming weekend dates for a "mini pilgrimage" — simple, dependency-free picker.
function pilgrimageDateOptions(): { label: string; date: string }[] {
  const out: { label: string; date: string }[] = [];
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  const today = new Date();
  const add = (n: number) => { const d = new Date(today); d.setDate(d.getDate() + n); return d; };
  const nextDow = (dow: number) => { const d = new Date(today); const diff = (dow - d.getDay() + 7) % 7 || 7; d.setDate(d.getDate() + diff); return d; };
  out.push({ label: "Today", date: fmt(today) });
  out.push({ label: "Tomorrow", date: fmt(add(1)) });
  const sat = nextDow(6); out.push({ label: "This Saturday", date: fmt(sat) });
  const sun = nextDow(0); out.push({ label: "This Sunday", date: fmt(sun) });
  const nextSat = new Date(sat); nextSat.setDate(nextSat.getDate() + 7); out.push({ label: "Next Saturday", date: fmt(nextSat) });
  // Drop any option whose date duplicates an earlier one (e.g. Tomorrow == This Saturday).
  const seen = new Set<string>();
  return out.filter((o) => (seen.has(o.date) ? false : (seen.add(o.date), true)));
}

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
  const [featured, setFeatured] = useState<CatholicSite | null>(null);
  const [planFor, setPlanFor] = useState<CatholicSite | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [usingLocation, setUsingLocation] = useState(false);
  const [nearCity, setNearCity] = useState<string>("");
  const [nearbyChurches, setNearbyChurches] = useState<CatholicSite[]>([]);

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

  // Resolve the user's GPS location and load the truly nearest holy place.
  // `prompt` = ask for permission (used by the "locate" button & first mount).
  const locateAndLoad = useCallback(async (prompt: boolean) => {
    try {
      const perm = prompt
        ? await Location.requestForegroundPermissionsAsync()
        : await Location.getForegroundPermissionsAsync();
      if (perm.granted) {
        const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        const { latitude, longitude } = pos.coords;
        const res = await nearbyCatholicSites(latitude, longitude);
        setFeatured(res.featured || res.items?.[0] || null);
        setNearbyChurches(res.nearby_churches || []);
        setUsingLocation(true);
        try {
          const geo = await Location.reverseGeocodeAsync({ latitude, longitude });
          const g = geo?.[0];
          setNearCity([g?.city || g?.subregion || g?.region, g?.country].filter(Boolean).join(", "));
        } catch {
          setNearCity("");
        }
        return true;
      }
    } catch {
      /* fall through to daily pick */
    }
    // Fallback: no location — show a place to explore (not "near you").
    try {
      const res = await nearbyCatholicSites();
      setFeatured(res.items?.[0] || null);
    } catch {
      setFeatured(null);
    }
    setUsingLocation(false);
    return false;
  }, []);

  const useMyLocation = useCallback(async () => {
    const ok = await locateAndLoad(true);
    setToast(ok ? "Found the nearest holy place to you." : "Location unavailable — enable location to find nearby places.");
    setTimeout(() => setToast(null), 3000);
  }, [locateAndLoad]);

  const planPilgrimage = useCallback(async (site: CatholicSite, date: string, label: string) => {
    try {
      await createScheduleItem({
        kind: "pilgrimage",
        title: `Pilgrimage: ${site.name}`,
        note: `${site.city}, ${site.country}`,
        recurrence: "once",
        date,
        ref_slug: site.slug,
        icon: "footsteps-outline",
        color: "#7A5CB0",
      });
      setPlanFor(null);
      setToast(`Added to your calendar for ${label}.`);
      setTimeout(() => setToast(null), 2800);
    } catch (e: any) {
      setToast(e?.message || "Couldn't add to calendar.");
      setTimeout(() => setToast(null), 2800);
    }
  }, []);

  const openInMaps = useCallback((s: CatholicSite) => {
    const label = encodeURIComponent(s.name);
    const url = `https://www.google.com/maps/search/?api=1&query=${s.lat},${s.lng}(${label})`;
    Linking.openURL(url).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    locateAndLoad(true);
  }, [load, locateAndLoad]);

  const markers = useMemo(
    () => sites.map((s) => ({ id: s.site_id, name: s.name, type: s.type, lat: s.lat, lng: s.lng, persecuted: s.persecuted })),
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

      {/* Saint of the place near you */}
      {featured ? (
        <View style={styles.featCard} testID="saint-near-you">
          <Pressable style={{ flex: 1 }} onPress={() => setSelected(featured)}>
            <View style={styles.featTop}>
              <Ionicons name="navigate-circle-outline" size={14} color={colors.gold} />
              <Text style={styles.featLabel}>{usingLocation ? (nearCity ? `Near ${nearCity}` : "Saint of the place near you") : "A holy place to explore"}</Text>
            </View>
            <Text style={styles.featName} numberOfLines={1}>{featured.name}</Text>
            <Text style={styles.featSub} numberOfLines={1}>
              {featured.city}, {featured.country}
              {featured.distance_km != null ? ` · ${featured.distance_km} km away` : ""}
            </Text>
            {featured.relics && featured.relics.length > 0 ? (
              <View style={styles.featRelic}>
                <Ionicons name="sparkles-outline" size={11} color={colors.gold} />
                <Text style={styles.featRelicText} numberOfLines={1}>Relics to venerate here</Text>
              </View>
            ) : null}
          </Pressable>
          <View style={styles.featActions}>
            <Pressable testID="saint-near-locate" onPress={useMyLocation} hitSlop={8} style={styles.featIconBtn}>
              <Ionicons name="locate-outline" size={18} color={colors.primary} />
            </Pressable>
            <Pressable testID="saint-near-plan" onPress={() => setPlanFor(featured)} style={({ pressed }) => [styles.featPlan, pressed && { opacity: 0.85 }]}>
              <Ionicons name="footsteps-outline" size={14} color="#fff" />
              <Text style={styles.featPlanText}>Plan</Text>
            </Pressable>
          </View>
        </View>
      ) : null}

      {toast ? (
        <View style={styles.toast} testID="map-toast"><Text style={styles.toastText}>{toast}</Text></View>
      ) : null}

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
          {usingLocation && nearbyChurches.length > 0 ? (
            <View style={styles.nearbyBlock}>
              <Text style={styles.nearbyHead}>
                Catholic churches near you{nearCity ? ` · ${nearCity}` : ""}
              </Text>
              {nearbyChurches.map((c) => (
                <Pressable
                  key={c.site_id}
                  testID={`map-nearby-${c.site_id}`}
                  onPress={() => openInMaps(c)}
                  style={({ pressed }) => [styles.listRow, pressed && { opacity: 0.85 }]}
                >
                  <View style={[styles.dot, { backgroundColor: TYPE_COLORS.church }]} />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.listTitle} numberOfLines={1}>{c.name}</Text>
                    <Text style={styles.listSub} numberOfLines={1}>
                      {[c.city, c.distance_km != null ? `${c.distance_km} km away` : ""].filter(Boolean).join(" · ")}
                    </Text>
                  </View>
                  <Ionicons name="navigate-outline" size={16} color={colors.primary} />
                </Pressable>
              ))}
              <Text style={styles.nearbyNote}>Live from OpenStreetMap · tap to open in Maps</Text>
            </View>
          ) : null}
          <Text style={styles.intro}>Explore {sites.length} significant Catholic places across the world.</Text>
          {sites.filter((s) => !s.osm).map((s) => (
            <Pressable
              key={s.site_id}
              testID={`map-list-${s.slug}`}
              onPress={() => setSelected(s)}
              style={({ pressed }) => [styles.listRow, pressed && { opacity: 0.85 }]}
            >
              <View style={[styles.dot, { backgroundColor: s.persecuted ? "#B3261E" : TYPE_COLORS[s.type] || colors.gold }]} />
              <View style={{ flex: 1 }}>
                <Text style={styles.listTitle} numberOfLines={1}>{s.name}</Text>
                <Text style={styles.listSub} numberOfLines={1}>{s.city}, {s.country}</Text>
              </View>
              {s.persecuted ? <Ionicons name="alert-circle" size={16} color="#B3261E" style={{ marginRight: 4 }} /> : null}
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
            <View style={styles.legendItem}>
              <View style={[styles.dot, styles.dotPersecuted]} />
              <Text style={styles.legendText}>Under persecution</Text>
            </View>
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

                {selected.persecuted ? (
                  <View style={styles.persBanner} testID="map-persecution-banner">
                    <Ionicons name="alert-circle" size={18} color="#B3261E" />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.persTitle}>Church under persecution</Text>
                      {selected.persecution_note ? <Text style={styles.persNote}>{selected.persecution_note}</Text> : null}
                    </View>
                  </View>
                ) : null}

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
                  testID="map-plan-pilgrimage"
                  onPress={() => { const s = selected; setSelected(null); setPlanFor(s); }}
                  style={({ pressed }) => [styles.planBtn, pressed && { opacity: 0.85 }]}
                >
                  <Ionicons name="footsteps-outline" size={16} color="#fff" />
                  <Text style={styles.planBtnText}>Plan a mini pilgrimage</Text>
                </Pressable>

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

      {/* Mini pilgrimage date picker */}
      <Modal visible={!!planFor} animationType="fade" transparent onRequestClose={() => setPlanFor(null)}>
        <View style={styles.planBackdrop}>
          <Pressable style={styles.backdropFill} onPress={() => setPlanFor(null)} />
          <View style={styles.planSheet} testID="pilgrimage-picker">
            <Ionicons name="footsteps" size={26} color="#7A5CB0" style={{ alignSelf: "center" }} />
            <Text style={styles.planTitle}>Plan a mini pilgrimage</Text>
            {planFor ? <Text style={styles.planSite}>{planFor.name}</Text> : null}
            <Text style={styles.planHint}>Pick a day to add it to your calendar.</Text>
            {pilgrimageDateOptions().map((opt) => (
              <Pressable
                key={opt.label}
                testID={`pilgrimage-date-${opt.label.replace(/\s+/g, "-").toLowerCase()}`}
                onPress={() => planFor && planPilgrimage(planFor, opt.date, opt.label)}
                style={({ pressed }) => [styles.planOption, pressed && { opacity: 0.85 }]}
              >
                <Ionicons name="calendar-outline" size={16} color={colors.primary} />
                <Text style={styles.planOptionText}>{opt.label}</Text>
                <View style={{ flex: 1 }} />
                <Text style={styles.planOptionDate}>{opt.date.slice(5)}</Text>
              </Pressable>
            ))}
            <Pressable onPress={() => setPlanFor(null)} style={styles.planCancel}>
              <Text style={styles.planCancelText}>Cancel</Text>
            </Pressable>
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
  dotPersecuted: { backgroundColor: "#B3261E", borderWidth: 1.5, borderColor: "#F4C7C3" },
  persBanner: {
    flexDirection: "row",
    gap: 8,
    alignItems: "flex-start",
    backgroundColor: "#FCEDEC",
    borderWidth: 1,
    borderColor: "#F2C5C1",
    borderRadius: radius.md,
    padding: spacing.md,
    marginTop: spacing.sm,
  },
  persTitle: { fontFamily: fonts.uiSemi, fontSize: 13.5, color: "#B3261E" },
  persNote: { fontFamily: fonts.bodyRegular, fontSize: 13, color: "#7A2520", lineHeight: 19, marginTop: 2 },
  featCard: {
    flexDirection: "row", alignItems: "center", gap: spacing.sm,
    marginHorizontal: spacing.md, marginTop: spacing.sm,
    backgroundColor: "#F3EFFB", borderWidth: 1, borderColor: "#DDD2F2",
    borderRadius: radius.md, padding: spacing.md,
  },
  featTop: { flexDirection: "row", alignItems: "center", gap: 5, marginBottom: 2 },
  featLabel: { fontFamily: fonts.uiSemi, fontSize: 10.5, letterSpacing: 0.4, textTransform: "uppercase", color: "#7A5CB0" },
  featName: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.primary },
  featSub: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textMuted, marginTop: 1 },
  featRelic: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 3 },
  featRelicText: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.gold },
  featActions: { flexDirection: "row", alignItems: "center", gap: 8 },
  featIconBtn: { padding: 4 },
  featPlan: { flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: "#7A5CB0", borderRadius: radius.round, paddingHorizontal: 12, paddingVertical: 8 },
  featPlanText: { fontFamily: fonts.uiSemi, fontSize: 13, color: "#fff" },
  toast: { position: "absolute", bottom: 24, left: spacing.lg, right: spacing.lg, backgroundColor: colors.surfaceDark, borderRadius: radius.md, padding: spacing.md, zIndex: 50 },
  toastText: { fontFamily: fonts.uiMedium, fontSize: 13.5, color: "#FBF6E9", textAlign: "center" },
  planBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, marginTop: spacing.lg, backgroundColor: "#7A5CB0", borderRadius: radius.md, paddingVertical: 13 },
  planBtnText: { fontFamily: fonts.uiSemi, fontSize: 15, color: "#fff" },
  planBackdrop: { flex: 1, justifyContent: "center", backgroundColor: "rgba(0,0,0,0.4)", padding: spacing.lg },
  planSheet: { backgroundColor: colors.background, borderRadius: 20, padding: spacing.lg, gap: 8 },
  planTitle: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.primary, textAlign: "center", marginTop: 4 },
  planSite: { fontFamily: fonts.headingSemi, fontSize: 15, color: "#7A5CB0", textAlign: "center" },
  planHint: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, textAlign: "center", marginBottom: 6 },
  planOption: { flexDirection: "row", alignItems: "center", gap: 8, borderWidth: 1, borderColor: colors.borderSoft, borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 13, marginBottom: 4 },
  planOptionText: { fontFamily: fonts.uiSemi, fontSize: 15, color: colors.primary },
  planOptionDate: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textMuted },
  planCancel: { paddingVertical: 12, alignItems: "center", marginTop: 2 },
  planCancelText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textMuted },
  listScroll: { padding: spacing.md, gap: spacing.sm },
  intro: { fontFamily: fonts.bodyItalic, fontSize: 13.5, color: colors.textSecondary, marginBottom: spacing.sm },
  nearbyBlock: { marginBottom: spacing.md, gap: spacing.sm },
  nearbyHead: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.primary },
  nearbyNote: { fontFamily: fonts.bodyItalic, fontSize: 11.5, color: colors.textMuted, marginTop: 2 },
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

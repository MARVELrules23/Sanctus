import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";
import * as Location from "expo-location";

import { api, ChurchItem } from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type Tab = "nearby" | "saved";

type PermStatus = "undetermined" | "granted" | "denied" | "blocked";

export default function ChurchesScreen() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("nearby");
  const [permStatus, setPermStatus] = useState<PermStatus>("undetermined");
  const [locating, setLocating] = useState(false);
  const [loadingNearby, setLoadingNearby] = useState(false);
  const [loadingSaved, setLoadingSaved] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [nearby, setNearby] = useState<ChurchItem[]>([]);
  const [saved, setSaved] = useState<ChurchItem[]>([]);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Search state
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<ChurchItem[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const searchSeq = useRef(0);

  const loadSaved = useCallback(async () => {
    setLoadingSaved(true);
    try {
      const res = await api<{ items: ChurchItem[] }>("/churches/saved");
      setSaved(res.items || []);
    } catch (e) {
      console.warn("saved churches failed", e);
    } finally {
      setLoadingSaved(false);
    }
  }, []);

  useEffect(() => {
    void loadSaved();
    // Pre-check permission status
    (async () => {
      try {
        const cur = await Location.getForegroundPermissionsAsync();
        if (cur.status === "granted") setPermStatus("granted");
        else if (cur.status === "denied" && !cur.canAskAgain) setPermStatus("blocked");
        else if (cur.status === "denied") setPermStatus("denied");
        else setPermStatus("undetermined");
      } catch {
        // ignore
      }
    })();
  }, [loadSaved]);

  const fetchNearbyAt = useCallback(
    async (lat: number, lng: number) => {
      setLoadingNearby(true);
      try {
        const res = await api<{ items: ChurchItem[]; count: number }>(
          `/churches/nearby?lat=${lat}&lng=${lng}&radius_m=12000&enrich=true`,
        );
        setNearby(res.items || []);
        setErrorMsg(null);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "";
        setErrorMsg(msg || "Could not load churches");
        setNearby([]);
      } finally {
        setLoadingNearby(false);
      }
    },
    [],
  );

  const requestLocationAndLoad = useCallback(async () => {
    setErrorMsg(null);
    setLocating(true);
    try {
      let cur = await Location.getForegroundPermissionsAsync();
      if (cur.status !== "granted") {
        if (!cur.canAskAgain) {
          setPermStatus("blocked");
          return;
        }
        const req = await Location.requestForegroundPermissionsAsync();
        cur = req;
        if (req.status !== "granted") {
          setPermStatus(req.canAskAgain ? "denied" : "blocked");
          return;
        }
      }
      setPermStatus("granted");
      const pos = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      const { latitude, longitude } = pos.coords;
      setCoords({ lat: latitude, lng: longitude });
      await fetchNearbyAt(latitude, longitude);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "";
      setErrorMsg(msg || "Could not determine your location");
    } finally {
      setLocating(false);
    }
  }, [fetchNearbyAt]);

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      if (tab === "saved") {
        await loadSaved();
      } else if (coords) {
        await fetchNearbyAt(coords.lat, coords.lng);
      }
    } finally {
      setRefreshing(false);
    }
  };

  const toggleStar = async (c: ChurchItem) => {
    if (c.is_starred) {
      try {
        await api(`/churches/saved/${encodeURIComponent(c.church_id)}`, { method: "DELETE" });
      } catch (e) {
        console.warn("unsave failed", e);
      }
      setNearby((arr) => arr.map((x) => (x.church_id === c.church_id ? { ...x, is_starred: false } : x)));
      setSaved((arr) => arr.filter((x) => x.church_id !== c.church_id));
    } else {
      try {
        const payload = {
          church_id: c.church_id,
          name: c.name,
          lat: c.lat,
          lng: c.lng,
          address: c.address || "",
          website: c.website || "",
          phone: c.phone || "",
          mass_times: c.mass_times || [],
          confession_times: c.confession_times || [],
        };
        const saved = await api<ChurchItem>("/churches/save", { method: "POST", body: payload });
        setNearby((arr) =>
          arr.map((x) => (x.church_id === c.church_id ? { ...x, is_starred: true } : x)),
        );
        setSaved((arr) => [saved, ...arr.filter((x) => x.church_id !== saved.church_id)]);
      } catch (e) {
        console.warn("save failed", e);
      }
    }
  };

  const openMaps = (c: ChurchItem) => {
    const url = Platform.select({
      ios: `http://maps.apple.com/?q=${encodeURIComponent(c.name)}&ll=${c.lat},${c.lng}`,
      default: `https://www.google.com/maps/search/?api=1&query=${c.lat},${c.lng}`,
    });
    if (url) void Linking.openURL(url);
  };

  const openWebsite = (url?: string) => {
    if (!url) return;
    const full = url.startsWith("http") ? url : `https://${url}`;
    void Linking.openURL(full).catch(() => undefined);
  };

  const dial = (phone?: string) => {
    if (!phone) return;
    void Linking.openURL(`tel:${phone}`).catch(() => undefined);
  };

  const openSettings = () => {
    void Linking.openSettings().catch(() => Alert.alert("Unable to open settings"));
  };

  const runSearch = useCallback(
    async (text: string) => {
      const q = text.trim();
      if (!q) {
        setSearchResults(null);
        setSearchError(null);
        return;
      }
      const seq = ++searchSeq.current;
      setSearching(true);
      setSearchError(null);
      try {
        const params = new URLSearchParams({ q });
        if (coords) {
          params.set("lat", String(coords.lat));
          params.set("lng", String(coords.lng));
        }
        const res = await api<{ items: ChurchItem[]; count: number }>(
          `/churches/search?${params.toString()}`,
        );
        if (seq !== searchSeq.current) return;
        // Annotate is_starred from current saved list as a fallback (backend
        // already does this, but saved tab may have churches not in this list).
        const savedIds = new Set(saved.map((s) => s.church_id));
        const items = (res.items || []).map((c) => ({
          ...c,
          is_starred: c.is_starred || savedIds.has(c.church_id),
        }));
        setSearchResults(items);
      } catch (e: unknown) {
        if (seq !== searchSeq.current) return;
        const msg = e instanceof Error ? e.message : "";
        setSearchError(msg || "Search failed. Try a different name.");
        setSearchResults([]);
      } finally {
        if (seq === searchSeq.current) setSearching(false);
      }
    },
    [coords, saved],
  );

  // Debounce live search as the user types.
  useEffect(() => {
    if (tab !== "nearby") return;
    const text = query.trim();
    if (!text) {
      setSearchResults(null);
      return;
    }
    if (text.length < 3) return;
    const t = setTimeout(() => {
      void runSearch(text);
    }, 450);
    return () => clearTimeout(t);
  }, [query, tab, runSearch]);

  const clearSearch = () => {
    setQuery("");
    setSearchResults(null);
    setSearchError(null);
    searchSeq.current += 1;
    setSearching(false);
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="churches-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.headerRow}>
        <Pressable testID="churches-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Catholic Churches</Text>
        <View style={{ width: 26 }} />
      </View>

      <View style={styles.segmentRow}>
        <Pressable
          testID="churches-tab-nearby"
          onPress={() => setTab("nearby")}
          style={[styles.segment, tab === "nearby" && styles.segmentActive]}
        >
          <Text style={[styles.segmentText, tab === "nearby" && styles.segmentTextActive]}>
            Nearby
          </Text>
        </Pressable>
        <Pressable
          testID="churches-tab-saved"
          onPress={() => setTab("saved")}
          style={[styles.segment, tab === "saved" && styles.segmentActive]}
        >
          <Text style={[styles.segmentText, tab === "saved" && styles.segmentTextActive]}>
            Saved {saved.length > 0 ? `(${saved.length})` : ""}
          </Text>
        </Pressable>
      </View>

      {tab === "nearby" && (
        <View style={styles.searchRow} testID="churches-search-row">
          <Ionicons name="search-outline" size={18} color={colors.textMuted} />
          <TextInput
            testID="churches-search-input"
            value={query}
            onChangeText={setQuery}
            placeholder="Search by parish name…"
            placeholderTextColor={colors.textMuted}
            returnKeyType="search"
            autoCorrect={false}
            autoCapitalize="words"
            onSubmitEditing={() => runSearch(query)}
            style={styles.searchInput}
          />
          {searching ? (
            <ActivityIndicator color={colors.gold} />
          ) : query.length > 0 ? (
            <Pressable
              testID="churches-search-clear"
              onPress={clearSearch}
              hitSlop={10}
            >
              <Ionicons name="close-circle" size={18} color={colors.textMuted} />
            </Pressable>
          ) : null}
        </View>
      )}

      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />
        }
      >
        {tab === "nearby" ? (
          searchResults !== null ? (
            // SEARCH MODE
            <>
              <View style={styles.searchHeader}>
                <Text style={styles.searchHeaderText}>
                  {searchResults.length > 0
                    ? `${searchResults.length} result${searchResults.length === 1 ? "" : "s"} for "${query}"`
                    : `No results for "${query}"`}
                </Text>
              </View>
              {searchError ? <Text style={styles.errorText}>{searchError}</Text> : null}
              {searchResults.length === 0 && !searching ? (
                <Text style={styles.empty}>
                  Try a shorter name, the patron saint, or a nearby town.
                </Text>
              ) : (
                searchResults.map((c) => (
                  <ChurchCard
                    key={c.church_id}
                    c={c}
                    onStar={() => toggleStar(c)}
                    onMaps={() => openMaps(c)}
                    onWeb={() => openWebsite(c.website)}
                    onCall={() => dial(c.phone)}
                  />
                ))
              )}
            </>
          ) : permStatus !== "granted" ? (
            <View style={styles.card} testID="churches-permission-card">
              <Ionicons name="navigate-circle-outline" size={36} color={colors.gold} />
              <Text style={styles.cardTitle}>Find churches near you</Text>
              <Text style={styles.cardBody}>
                Sanctus uses your device location once — only when you ask — to find Catholic
                churches in your area along with Mass and Confession times. Your location is never stored.
              </Text>
              {permStatus === "blocked" ? (
                <>
                  <Text style={styles.errorText}>
                    Location is blocked for Sanctus. Open Settings to allow it, then return here.
                  </Text>
                  <Pressable
                    testID="churches-open-settings"
                    onPress={openSettings}
                    style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
                  >
                    <Ionicons name="settings-outline" size={16} color={colors.gold} />
                    <Text style={styles.primaryBtnText}>Open Settings</Text>
                  </Pressable>
                </>
              ) : (
                <Pressable
                  testID="churches-grant"
                  onPress={requestLocationAndLoad}
                  disabled={locating}
                  style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
                >
                  {locating ? (
                    <ActivityIndicator color={colors.gold} />
                  ) : (
                    <>
                      <Ionicons name="location-outline" size={16} color={colors.gold} />
                      <Text style={styles.primaryBtnText}>Use my location</Text>
                    </>
                  )}
                </Pressable>
              )}
            </View>
          ) : (
            <>
              <Pressable
                testID="churches-refresh"
                onPress={requestLocationAndLoad}
                disabled={locating || loadingNearby}
                style={({ pressed }) => [styles.refreshLocBtn, pressed && styles.pressed]}
              >
                <Ionicons name="locate-outline" size={16} color={colors.primary} />
                <Text style={styles.refreshLocText}>
                  {locating || loadingNearby ? "Locating…" : "Refresh from my location"}
                </Text>
              </Pressable>
              {errorMsg ? <Text style={styles.errorText}>{errorMsg}</Text> : null}
              {loadingNearby ? (
                <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
              ) : nearby.length === 0 ? (
                <>
                  <Text style={styles.empty}>
                    No Catholic churches found in the search radius. Try refreshing from a different
                    spot.
                  </Text>
                  <Pressable
                    testID="churches-add-cta-empty"
                    onPress={() => router.push("/add-church")}
                    style={({ pressed }) => [styles.addCta, pressed && styles.pressed]}
                  >
                    <Ionicons name="add-circle-outline" size={18} color={colors.gold} />
                    <Text style={styles.addCtaText}>Add a parish manually</Text>
                  </Pressable>
                </>
              ) : (
                nearby.map((c) => (
                  <ChurchCard
                    key={c.church_id}
                    c={c}
                    onStar={() => toggleStar(c)}
                    onMaps={() => openMaps(c)}
                    onWeb={() => openWebsite(c.website)}
                    onCall={() => dial(c.phone)}
                  />
                ))
              )}
              {!loadingNearby && nearby.length > 0 ? (
                <Pressable
                  testID="churches-add-cta"
                  onPress={() => router.push("/add-church")}
                  style={({ pressed }) => [styles.addCta, pressed && styles.pressed]}
                >
                  <Ionicons name="add-circle-outline" size={18} color={colors.gold} />
                  <Text style={styles.addCtaText}>
                    Don&apos;t see your parish? Add it here.
                  </Text>
                </Pressable>
              ) : null}
            </>
          )
        ) : loadingSaved ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
        ) : saved.length === 0 ? (
          <Text style={styles.empty}>
            No saved churches yet. Star one from the Nearby tab to keep its Mass and Confession
            times handy.
          </Text>
        ) : (
          saved.map((c) => (
            <ChurchCard
              key={c.church_id}
              c={c}
              onStar={() => toggleStar(c)}
              onMaps={() => openMaps(c)}
              onWeb={() => openWebsite(c.website)}
              onCall={() => dial(c.phone)}
            />
          ))
        )}
        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function ChurchCard({
  c,
  onStar,
  onMaps,
  onWeb,
  onCall,
}: {
  c: ChurchItem;
  onStar: () => void;
  onMaps: () => void;
  onWeb: () => void;
  onCall: () => void;
}) {
  const router = useRouter();
  return (
    <View style={styles.card} testID={`church-${c.church_id}`}>
      <View style={styles.churchHeader}>
        <View style={{ flex: 1 }}>
          <Text style={styles.churchName}>{c.name}</Text>
          {c.distance_km != null ? (
            <Text style={styles.churchMeta}>{c.distance_km.toFixed(1)} km away</Text>
          ) : null}
          {c.address ? <Text style={styles.churchAddr}>{c.address}</Text> : null}
          {c.source === "community" ? (
            <View style={styles.communityBadge} testID={`church-community-${c.church_id}`}>
              <Ionicons name="people-outline" size={11} color={colors.liturgical.purple} />
              <Text style={styles.communityBadgeText}>
                Added by {c.submitted_by_name || "a Sanctus user"}
              </Text>
            </View>
          ) : null}
          {c.editor_count && c.editor_count > 0 ? (
            <View style={styles.communityBadge} testID={`church-editors-${c.church_id}`}>
              <Ionicons name="create-outline" size={11} color={colors.gold} />
              <Text style={styles.communityBadgeText}>
                {c.contributors && c.contributors.length > 0
                  ? `Edited by ${c.contributors.slice(0, 2).join(", ")}${
                      c.editor_count > c.contributors.length
                        ? ` + ${c.editor_count - c.contributors.length} more`
                        : ""
                    }`
                  : `Edited by ${c.editor_count} ${c.editor_count === 1 ? "person" : "people"}`}
              </Text>
            </View>
          ) : null}
        </View>
        <Pressable testID={`church-star-${c.church_id}`} onPress={onStar} hitSlop={10}>
          <Ionicons
            name={c.is_starred ? "star" : "star-outline"}
            size={24}
            color={c.is_starred ? colors.gold : colors.textMuted}
          />
        </Pressable>
      </View>

      {c.mass_times && c.mass_times.length > 0 ? (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Mass times</Text>
          {c.mass_times.map((m, i) => (
            <Text key={i} style={styles.timeLine}>
              {m}
            </Text>
          ))}
        </View>
      ) : null}
      {c.confession_times && c.confession_times.length > 0 ? (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Confession</Text>
          {c.confession_times.map((m, i) => (
            <Text key={i} style={styles.timeLine}>
              {m}
            </Text>
          ))}
        </View>
      ) : null}
      {(!c.mass_times || c.mass_times.length === 0) && (!c.confession_times || c.confession_times.length === 0) ? (
        <Text style={styles.hint}>Times not listed publicly — check the parish website or call.</Text>
      ) : null}

      <View style={styles.actionsRow}>
        <Pressable
          testID={`church-events-${c.church_id}`}
          onPress={() =>
            router.push({
              pathname: "/parish-events",
              params: {
                church_id: c.church_id,
                church_name: c.name,
                lat: String(c.lat),
                lng: String(c.lng),
              },
            })
          }
          style={({ pressed }) => [styles.actionBtn, pressed && styles.pressed]}
        >
          <Ionicons name="calendar-outline" size={16} color={colors.primary} />
          <Text style={styles.actionText}>Events</Text>
        </Pressable>
        <Pressable testID={`church-map-${c.church_id}`} onPress={onMaps} style={({ pressed }) => [styles.actionBtn, pressed && styles.pressed]}>
          <Ionicons name="map-outline" size={16} color={colors.primary} />
          <Text style={styles.actionText}>Map</Text>
        </Pressable>
        {c.website ? (
          <Pressable testID={`church-web-${c.church_id}`} onPress={onWeb} style={({ pressed }) => [styles.actionBtn, pressed && styles.pressed]}>
            <Ionicons name="globe-outline" size={16} color={colors.primary} />
            <Text style={styles.actionText}>Website</Text>
          </Pressable>
        ) : null}
        {c.phone ? (
          <Pressable testID={`church-call-${c.church_id}`} onPress={onCall} style={({ pressed }) => [styles.actionBtn, pressed && styles.pressed]}>
            <Ionicons name="call-outline" size={16} color={colors.primary} />
            <Text style={styles.actionText}>Call</Text>
          </Pressable>
        ) : null}
        <Pressable
          testID={`church-edit-${c.church_id}`}
          onPress={() =>
            router.push({
              pathname: "/edit-church",
              params: {
                church_id: c.church_id,
                church_name: c.name,
                address: c.address || "",
                existing_mass: JSON.stringify(c.mass_times || []),
                existing_conf: JSON.stringify(c.confession_times || []),
                existing_website: c.website || "",
                existing_phone: c.phone || "",
                existing_notes: c.notes || "",
              },
            })
          }
          style={({ pressed }) => [styles.actionBtn, styles.actionBtnEdit, pressed && styles.pressed]}
        >
          <Ionicons name="create-outline" size={16} color={colors.gold} />
          <Text style={[styles.actionText, styles.actionTextEdit]}>Edit</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 22, color: colors.textPrimary },
  segmentRow: {
    flexDirection: "row",
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    gap: spacing.sm,
  },
  segment: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    backgroundColor: colors.surface,
  },
  segmentActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  segmentText: { fontFamily: fonts.uiSemi, color: colors.textSecondary, fontSize: 14 },
  segmentTextActive: { color: colors.gold },
  searchRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginHorizontal: spacing.lg,
    marginTop: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: Platform.OS === "ios" ? 10 : 6,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.round,
  },
  searchInput: {
    flex: 1,
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textPrimary,
    paddingVertical: 0,
  },
  searchHeader: {
    paddingBottom: spacing.sm,
  },
  searchHeaderText: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.textMuted,
    letterSpacing: 0.6,
  },
  scroll: { padding: spacing.lg },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginBottom: spacing.md,
    ...shadow.card,
  },
  cardTitle: {
    fontFamily: fonts.headingBold,
    fontSize: 22,
    color: colors.textPrimary,
    marginTop: spacing.sm,
  },
  cardBody: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
    marginTop: spacing.sm,
  },
  churchHeader: { flexDirection: "row", alignItems: "flex-start", gap: spacing.sm },
  churchName: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  churchMeta: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold, marginTop: 2 },
  churchAddr: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, marginTop: 2, lineHeight: 18 },
  section: { marginTop: spacing.md },
  sectionLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1.2,
    color: colors.textMuted,
    marginBottom: 4,
  },
  timeLine: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textPrimary, lineHeight: 20 },
  hint: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12, color: colors.textMuted, marginTop: spacing.sm },
  actionsRow: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.md, flexWrap: "wrap" },
  actionBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.background,
  },
  actionText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.primary },
  actionBtnEdit: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  actionTextEdit: { color: colors.gold },
  primaryBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 14,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  primaryBtnText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 15, letterSpacing: 0.6 },
  refreshLocBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 10,
    paddingHorizontal: spacing.md,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    alignSelf: "flex-start",
    marginBottom: spacing.md,
  },
  refreshLocText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.primary },
  errorText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.liturgical.red,
    marginTop: spacing.sm,
    lineHeight: 20,
  },
  empty: {
    fontFamily: fonts.bodyRegular,
    fontStyle: "italic",
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
    marginTop: spacing.lg,
    textAlign: "center",
    paddingHorizontal: spacing.lg,
  },
  addCta: {
    marginTop: spacing.lg,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.gold,
    borderStyle: "dashed",
    backgroundColor: colors.surface,
  },
  addCtaText: {
    fontFamily: fonts.uiSemi,
    fontSize: 13,
    color: colors.gold,
    letterSpacing: 0.3,
  },
  communityBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    alignSelf: "flex-start",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.round,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.liturgical.purple,
    marginTop: 6,
  },
  communityBadgeText: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    color: colors.liturgical.purple,
    letterSpacing: 0.4,
  },
  pressed: { opacity: 0.7 },
});

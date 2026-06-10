import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Image,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import {
  Charity,
  CharityCategoryLabel,
  getCharityCategories,
  listCharities,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

export default function CharitiesIndex() {
  const router = useRouter();
  const { user } = useAuth();
  const [items, setItems] = useState<Charity[]>([]);
  const [categories, setCategories] = useState<CharityCategoryLabel[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [state, setStateFilter] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const load = useCallback(async () => {
    if (!user) return;
    try {
      const r = await listCharities({
        q: search.trim() || undefined,
        category: category || undefined,
        state: state.trim() || undefined,
      });
      setItems(r.items);
    } catch (e) {
      console.warn("load charities failed", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [user, search, category, state]);

  useEffect(() => {
    getCharityCategories().then((r) => setCategories(r.categories)).catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  const renderItem = ({ item }: { item: Charity }) => (
    <Pressable
      onPress={() => router.push(`/charities/${item.charity_id}`)}
      style={({ pressed }) => [styles.card, pressed && { opacity: 0.85 }]}
    >
      <View style={styles.cardRow}>
        {item.logo_url ? (
          <Image source={{ uri: item.logo_url }} style={styles.logo} resizeMode="cover" />
        ) : (
          <View style={[styles.logo, styles.logoPh]}>
            <Ionicons name="heart-circle-outline" size={28} color={colors.gold} />
          </View>
        )}
        <View style={{ flex: 1 }}>
          <Text style={styles.name} numberOfLines={2}>{item.name}</Text>
          {item.city || item.state ? (
            <Text style={styles.loc} numberOfLines={1}>
              {[item.city, item.state].filter(Boolean).join(", ")}
            </Text>
          ) : null}
          <Text style={styles.mission} numberOfLines={3}>{item.mission}</Text>
        </View>
      </View>
      <View style={styles.tagsRow}>
        <View style={styles.tag}>
          <Text style={styles.tagText}>{labelFor(categories, item.category)}</Text>
        </View>
        {item.claimed_by ? (
          <View style={[styles.tag, { backgroundColor: colors.liturgical.green + "22", borderColor: colors.liturgical.green }]}>
            <Ionicons name="checkmark-circle" size={11} color={colors.liturgical.green} />
            <Text style={[styles.tagText, { color: colors.liturgical.green }]}>Claimed</Text>
          </View>
        ) : null}
      </View>
    </Pressable>
  );

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.headerBtn}>
          <Ionicons name="chevron-back" size={24} color={colors.primary} />
        </Pressable>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>Catholic Charities</Text>
          <Text style={styles.headerSub}>Volunteer your time · corporal works of mercy</Text>
        </View>
        <Pressable onPress={() => router.push("/charities/submit")} hitSlop={10} style={styles.headerBtn} testID="submit-charity">
          <Ionicons name="add-circle" size={26} color={colors.primary} />
        </Pressable>
      </View>

      <View style={styles.searchRow}>
        <View style={styles.searchBox}>
          <Ionicons name="search" size={16} color={colors.textMuted} />
          <TextInput
            value={search}
            onChangeText={setSearch}
            placeholder="Search by name, mission, or city"
            placeholderTextColor={colors.textMuted}
            style={styles.searchInput}
            returnKeyType="search"
            onSubmitEditing={load}
          />
          {search ? (
            <Pressable onPress={() => setSearch("")} hitSlop={6}>
              <Ionicons name="close-circle" size={16} color={colors.textMuted} />
            </Pressable>
          ) : null}
        </View>
        <Pressable onPress={() => setShowFilters(!showFilters)} style={({ pressed }) => [styles.filterBtn, (category || state) && styles.filterBtnActive, pressed && { opacity: 0.7 }]}>
          <Ionicons name="options-outline" size={18} color={(category || state) ? "#fff" : colors.primary} />
        </Pressable>
      </View>

      {showFilters ? (
        <View style={styles.filtersWrap}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipsRow}>
            <Pressable onPress={() => setCategory(null)} style={[styles.chip, !category && styles.chipActive]}>
              <Text style={[styles.chipText, !category && styles.chipTextActive]}>All</Text>
            </Pressable>
            {categories.map((c) => (
              <Pressable key={c.key} onPress={() => setCategory(c.key)} style={[styles.chip, category === c.key && styles.chipActive]}>
                <Text style={[styles.chipText, category === c.key && styles.chipTextActive]}>{c.label}</Text>
              </Pressable>
            ))}
          </ScrollView>
          <View style={styles.stateRow}>
            <Ionicons name="location-outline" size={14} color={colors.textMuted} />
            <TextInput
              value={state}
              onChangeText={setStateFilter}
              placeholder="State (e.g. CA)"
              placeholderTextColor={colors.textMuted}
              style={styles.stateInput}
              autoCapitalize="characters"
              maxLength={20}
            />
            {state ? (
              <Pressable onPress={() => setStateFilter("")} hitSlop={6}>
                <Ionicons name="close-circle" size={16} color={colors.textMuted} />
              </Pressable>
            ) : null}
          </View>
        </View>
      ) : null}

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.primary} /></View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(c) => c.charity_id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor={colors.primary} />}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="heart-outline" size={48} color={colors.textMuted} />
              <Text style={styles.emptyTitle}>No charities listed yet</Text>
              <Text style={styles.emptyHint}>Be the first to add one your parish supports.</Text>
              <Pressable onPress={() => router.push("/charities/submit")} style={({ pressed }) => [styles.emptyBtn, pressed && { opacity: 0.8 }]}>
                <Text style={styles.emptyBtnText}>Add a charity</Text>
              </Pressable>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

function labelFor(cats: CharityCategoryLabel[], key: string): string {
  return cats.find((c) => c.key === key)?.label || key.replace(/_/g, " ");
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, backgroundColor: colors.surface },
  headerBtn: { padding: spacing.xs, minWidth: 40, alignItems: "center" },
  headerCenter: { flex: 1, alignItems: "center" },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 19, color: colors.primary },
  headerSub: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  searchRow: { flexDirection: "row", alignItems: "center", gap: 8, padding: spacing.md, paddingTop: spacing.sm },
  searchBox: { flex: 1, flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 10, paddingVertical: 8, backgroundColor: colors.surface, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft },
  searchInput: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary, paddingVertical: 0 },
  filterBtn: { padding: 10, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.surface },
  filterBtnActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  filtersWrap: { paddingBottom: spacing.sm, gap: spacing.sm, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  chipsRow: { paddingHorizontal: spacing.md, gap: 6 },
  chip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: radius.round, backgroundColor: colors.background, borderWidth: 1, borderColor: colors.borderSoft },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textSecondary },
  chipTextActive: { color: "#fff" },
  stateRow: { flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: spacing.md, paddingVertical: 4 },
  stateInput: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textPrimary, paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  list: { padding: spacing.md, paddingBottom: spacing.xl, gap: spacing.sm },
  card: { padding: spacing.md, backgroundColor: colors.surface, borderRadius: radius.lg, ...shadow.card, marginBottom: spacing.sm, gap: spacing.sm },
  cardRow: { flexDirection: "row", gap: spacing.sm },
  logo: { width: 56, height: 56, borderRadius: radius.md, backgroundColor: colors.background },
  logoPh: { alignItems: "center", justifyContent: "center" },
  name: { fontFamily: fonts.headingBold, fontSize: 16, color: colors.primary },
  loc: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textMuted, marginTop: 2 },
  mission: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, marginTop: 4, lineHeight: 18 },
  tagsRow: { flexDirection: "row", gap: 6, flexWrap: "wrap" },
  tag: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.round, backgroundColor: colors.gold + "22", borderWidth: 1, borderColor: colors.gold + "66" },
  tagText: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.gold },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  empty: { alignItems: "center", padding: spacing.xl, gap: spacing.sm, marginTop: spacing.xl },
  emptyTitle: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.primary },
  emptyHint: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, textAlign: "center" },
  emptyBtn: { marginTop: spacing.md, paddingHorizontal: spacing.lg, paddingVertical: 10, borderRadius: radius.round, backgroundColor: colors.primary },
  emptyBtnText: { fontFamily: fonts.uiSemi, fontSize: 13, color: "#fff" },
});

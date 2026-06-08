import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { api, CommunityUserPublic } from "@/src/api";
import Avatar from "@/src/components/Avatar";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

export default function PeopleSearchScreen() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CommunityUserPublic[]>([]);
  const [recommended, setRecommended] = useState<CommunityUserPublic[]>([]);
  const [searching, setSearching] = useState(false);
  const [loadingRec, setLoadingRec] = useState(true);

  const loadRec = useCallback(async () => {
    try {
      const r = await api<{ items: CommunityUserPublic[] }>("/community/users/recommended");
      setRecommended(r.items || []);
    } catch {
      // ignore
    } finally {
      setLoadingRec(false);
    }
  }, []);

  useEffect(() => {
    void loadRec();
  }, [loadRec]);

  // Debounced search
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    setSearching(true);
    const t = setTimeout(async () => {
      try {
        const r = await api<{ items: CommunityUserPublic[] }>(
          `/community/users/search?q=${encodeURIComponent(query.trim())}`,
        );
        setResults(r.items || []);
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  const openUser = (u: CommunityUserPublic) => {
    router.push({ pathname: "/community/user/[id]", params: { id: u.user_id } });
  };
  const startDM = (u: CommunityUserPublic) => {
    router.push({ pathname: "/community/dm/[thread_id]", params: { thread_id: "new", other_id: u.user_id } });
  };

  const showRecommended = !query.trim();

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="community-people-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="people-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Find people</Text>
        <View style={{ width: 26 }} />
      </View>

      <View style={styles.searchRow}>
        <Ionicons name="search" size={16} color={colors.textMuted} />
        <TextInput
          testID="people-search-input"
          value={query}
          onChangeText={setQuery}
          placeholder="Search by name or email…"
          placeholderTextColor={colors.textMuted}
          style={styles.searchInput}
          autoCorrect={false}
          autoCapitalize="none"
          returnKeyType="search"
        />
        {query ? (
          <Pressable onPress={() => setQuery("")} hitSlop={10} testID="people-search-clear">
            <Ionicons name="close-circle" size={16} color={colors.textMuted} />
          </Pressable>
        ) : null}
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {showRecommended ? (
          <>
            <Text style={styles.sectionTitle}>Recommended</Text>
            {loadingRec ? (
              <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.lg }} />
            ) : recommended.length === 0 ? (
              <Text style={styles.empty}>No suggestions yet — invite a friend to Sanctus!</Text>
            ) : (
              recommended.map((u) => (
                <UserRow key={u.user_id} user={u} onPress={() => openUser(u)} onDM={() => startDM(u)} />
              ))
            )}
          </>
        ) : (
          <>
            <Text style={styles.sectionTitle}>Results</Text>
            {searching ? (
              <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.lg }} />
            ) : results.length === 0 ? (
              <Text style={styles.empty}>No one matched &ldquo;{query.trim()}&rdquo;.</Text>
            ) : (
              results.map((u) => (
                <UserRow key={u.user_id} user={u} onPress={() => openUser(u)} onDM={() => startDM(u)} />
              ))
            )}
          </>
        )}
        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function UserRow({ user, onPress, onDM }: { user: CommunityUserPublic; onPress: () => void; onDM: () => void }) {
  return (
    <View style={styles.row}>
      <Pressable
        onPress={onPress}
        hitSlop={6}
        style={({ pressed }) => [styles.rowMain, pressed && { opacity: 0.7 }]}
        testID={`people-user-${user.user_id}`}
      >
        <Avatar name={user.name} picture={user.picture ?? null} size={42} />
        <View style={{ marginLeft: spacing.sm, flex: 1 }}>
          <Text style={styles.name} numberOfLines={1}>{user.name}</Text>
          <Text style={styles.subtle}>View profile</Text>
        </View>
      </Pressable>
      <Pressable
        onPress={onDM}
        hitSlop={8}
        style={({ pressed }) => [styles.dmBtn, pressed && { opacity: 0.7 }]}
        testID={`people-dm-${user.user_id}`}
      >
        <Ionicons name="paper-plane-outline" size={16} color={colors.gold} />
        <Text style={styles.dmBtnText}>Message</Text>
      </Pressable>
    </View>
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
  searchRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginHorizontal: spacing.lg,
    marginTop: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    backgroundColor: colors.surface,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  searchInput: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary, paddingVertical: 0 },
  scroll: { padding: spacing.lg, paddingTop: spacing.md },
  sectionTitle: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 2.5,
    color: colors.gold,
    textTransform: "uppercase",
    marginBottom: spacing.sm,
  },
  empty: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, textAlign: "center", paddingVertical: spacing.lg },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginBottom: spacing.sm,
    ...shadow.card,
  },
  rowMain: { flex: 1, flexDirection: "row", alignItems: "center" },
  name: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  subtle: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 1 },
  dmBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
  },
  dmBtnText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold },
});

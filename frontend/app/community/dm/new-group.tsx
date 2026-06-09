import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
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

import {
  CommunityUserPublic,
  Friendship,
  dmCreateGroup,
  friendList,
} from "@/src/api";
import Avatar from "@/src/components/Avatar";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

// Backend cap (mirrors community.MAX_GROUP_MEMBERS). Subtract 1 for the
// creator who is auto-added on the server.
const MAX_OTHERS = 49;

export default function NewGroupDMScreen() {
  const router = useRouter();
  const [friends, setFriends] = useState<CommunityUserPublic[]>([]);
  const [loadingFriends, setLoadingFriends] = useState(true);
  const [selected, setSelected] = useState<Record<string, CommunityUserPublic>>({});
  const [query, setQuery] = useState("");
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoadingFriends(true);
    try {
      const r = await friendList("accepted");
      const list: CommunityUserPublic[] = (r.items || [])
        .map((f: Friendship) => f.user)
        .filter((u): u is CommunityUserPublic => !!u)
        // Stable alpha sort so the picker doesn't shuffle on each load.
        .sort((a, b) => a.name.localeCompare(b.name));
      setFriends(list);
    } catch {
      setFriends([]);
    } finally {
      setLoadingFriends(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return friends;
    return friends.filter((u) => u.name.toLowerCase().includes(q));
  }, [friends, query]);

  const selectedList = useMemo(() => Object.values(selected), [selected]);
  const canCreate = selectedList.length >= 2 && !creating;

  const toggle = (u: CommunityUserPublic) => {
    setSelected((prev) => {
      const next = { ...prev };
      if (next[u.user_id]) {
        delete next[u.user_id];
        return next;
      }
      if (Object.keys(next).length >= MAX_OTHERS) {
        Alert.alert(
          "Group is full",
          `You can include up to ${MAX_OTHERS} friends in a group.`,
        );
        return prev;
      }
      next[u.user_id] = u;
      return next;
    });
  };

  const create = async () => {
    if (!canCreate) return;
    setCreating(true);
    try {
      const thread = await dmCreateGroup(
        selectedList.map((u) => u.user_id),
        name.trim() ? name.trim() : null,
      );
      // Replace this screen with the newly-created thread so the back
      // button returns to the Inbox, not the picker.
      router.replace({
        pathname: "/community/dm/[thread_id]",
        params: { thread_id: thread.thread_id },
      });
    } catch (e: any) {
      Alert.alert("Couldn't create group", e?.message || "Please try again.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="dm-new-group-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="new-group-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>New group</Text>
        <Pressable
          onPress={create}
          disabled={!canCreate}
          hitSlop={10}
          testID="new-group-create"
          style={({ pressed }) => [styles.createBtn, !canCreate && { opacity: 0.4 }, pressed && { opacity: 0.7 }]}
        >
          {creating ? (
            <ActivityIndicator color={colors.gold} size="small" />
          ) : (
            <Text style={styles.createBtnText}>Create</Text>
          )}
        </Pressable>
      </View>

      {/* Optional group name */}
      <View style={styles.nameWrap}>
        <Text style={styles.label}>Group name (optional)</Text>
        <TextInput
          testID="new-group-name-input"
          value={name}
          onChangeText={setName}
          placeholder="e.g. Tuesday Holy Hour"
          placeholderTextColor={colors.textMuted}
          style={styles.nameInput}
          maxLength={60}
        />
      </View>

      {/* Selected chip rail */}
      {selectedList.length > 0 ? (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.chipRow}
        >
          {selectedList.map((u) => (
            <Pressable
              key={u.user_id}
              onPress={() => toggle(u)}
              style={styles.chip}
              testID={`new-group-chip-${u.user_id}`}
              hitSlop={4}
            >
              <Avatar name={u.name} picture={u.picture ?? null} size={22} />
              <Text style={styles.chipText} numberOfLines={1}>{u.name}</Text>
              <Ionicons name="close" size={14} color={colors.textMuted} />
            </Pressable>
          ))}
        </ScrollView>
      ) : null}

      {/* Search */}
      <View style={styles.searchRow}>
        <Ionicons name="search" size={16} color={colors.textMuted} />
        <TextInput
          testID="new-group-search"
          value={query}
          onChangeText={setQuery}
          placeholder="Search your friends…"
          placeholderTextColor={colors.textMuted}
          style={styles.searchInput}
          autoCorrect={false}
          autoCapitalize="none"
        />
        {query ? (
          <Pressable onPress={() => setQuery("")} hitSlop={10}>
            <Ionicons name="close-circle" size={16} color={colors.textMuted} />
          </Pressable>
        ) : null}
      </View>

      <View style={styles.counterRow}>
        <Text style={styles.counterText}>
          {selectedList.length === 0
            ? "Select at least 2 friends"
            : `${selectedList.length} selected · ${MAX_OTHERS - selectedList.length} more allowed`}
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        {loadingFriends ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.gold} />
          </View>
        ) : friends.length === 0 ? (
          <View style={styles.empty}>
            <Ionicons name="people-outline" size={32} color={colors.gold} />
            <Text style={styles.emptyTitle}>No friends yet</Text>
            <Text style={styles.emptyText}>
              Add friends from their profiles to start a group conversation.
            </Text>
            <Pressable
              onPress={() => router.replace("/community/people")}
              style={({ pressed }) => [styles.cta, pressed && { opacity: 0.7 }]}
              testID="new-group-find-people"
            >
              <Ionicons name="person-add-outline" size={16} color={colors.gold} />
              <Text style={styles.ctaText}>Find people</Text>
            </Pressable>
          </View>
        ) : filtered.length === 0 ? (
          <Text style={styles.emptyInline}>No friends match &ldquo;{query.trim()}&rdquo;.</Text>
        ) : (
          filtered.map((u) => {
            const isSelected = !!selected[u.user_id];
            return (
              <Pressable
                key={u.user_id}
                onPress={() => toggle(u)}
                testID={`new-group-row-${u.user_id}`}
                style={({ pressed }) => [
                  styles.row,
                  isSelected && styles.rowSelected,
                  pressed && { opacity: 0.85 },
                ]}
              >
                <Avatar name={u.name} picture={u.picture ?? null} size={42} />
                <View style={{ flex: 1, marginLeft: spacing.sm }}>
                  <Text style={styles.name} numberOfLines={1}>{u.name}</Text>
                  <Text style={styles.subtle}>Friend</Text>
                </View>
                <View style={[styles.checkbox, isSelected && styles.checkboxOn]}>
                  {isSelected ? (
                    <Ionicons name="checkmark" size={16} color={colors.gold} />
                  ) : null}
                </View>
              </Pressable>
            );
          })
        )}
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
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  createBtn: {
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
    minWidth: 72,
    alignItems: "center",
  },
  createBtnText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 13 },
  nameWrap: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
  },
  label: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.4,
    color: colors.gold,
    textTransform: "uppercase",
    marginBottom: 6,
  },
  nameInput: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textPrimary,
  },
  chipRow: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
    flexDirection: "row",
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.primary,
    backgroundColor: colors.surface,
    maxWidth: 180,
  },
  chipText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textPrimary, maxWidth: 110 },
  searchRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginHorizontal: spacing.lg,
    marginTop: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    backgroundColor: colors.surface,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  searchInput: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary, paddingVertical: 0 },
  counterRow: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  counterText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, fontSize: 12 },
  scroll: { padding: spacing.lg, paddingTop: spacing.sm },
  center: { paddingVertical: spacing.xxl, alignItems: "center" },
  empty: { alignItems: "center", padding: spacing.lg, gap: spacing.sm },
  emptyTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary, marginTop: spacing.sm },
  emptyText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, textAlign: "center" },
  emptyInline: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, textAlign: "center", paddingVertical: spacing.lg },
  cta: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: spacing.lg,
    paddingVertical: 10,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
    marginTop: spacing.sm,
  },
  ctaText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold },
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
  rowSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.background,
  },
  name: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  subtle: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 1 },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: colors.borderSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxOn: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
});

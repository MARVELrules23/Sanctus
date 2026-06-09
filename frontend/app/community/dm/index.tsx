import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useFocusEffect, useRouter } from "expo-router";

import { api, CommunityDMThread } from "@/src/api";
import Avatar from "@/src/components/Avatar";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { timeAgo } from "@/src/utils/time-ago";

export default function DMInboxScreen() {
  const router = useRouter();
  const [threads, setThreads] = useState<CommunityDMThread[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await api<{ items: CommunityDMThread[] }>("/community/dm/threads");
      setThreads(r.items || []);
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="community-dm-inbox">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="dm-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Messages</Text>
        <View style={{ flexDirection: "row", gap: spacing.md }}>
          <Pressable
            onPress={() => router.push("/community/dm/new-group")}
            hitSlop={12}
            testID="dm-new-group"
          >
            <Ionicons name="people-outline" size={22} color={colors.primary} />
          </Pressable>
          <Pressable
            onPress={() => router.push("/community/people")}
            hitSlop={12}
            testID="dm-new"
          >
            <Ionicons name="create-outline" size={22} color={colors.primary} />
          </Pressable>
        </View>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
        </View>
      ) : threads.length === 0 ? (
        <View style={styles.empty}>
          <Ionicons name="chatbubbles-outline" size={32} color={colors.gold} />
          <Text style={styles.emptyTitle}>No conversations yet</Text>
          <Text style={styles.emptyText}>
            Find a brother or sister in faith and begin a charitable conversation.
          </Text>
          <Pressable
            onPress={() => router.push("/community/people")}
            style={({ pressed }) => [styles.cta, pressed && { opacity: 0.7 }]}
            testID="dm-empty-find-people"
          >
            <Ionicons name="person-add-outline" size={16} color={colors.gold} />
            <Text style={styles.ctaText}>Find people</Text>
          </Pressable>
        </View>
      ) : (
        <ScrollView
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor={colors.gold} />}
          contentContainerStyle={styles.scroll}
        >
          {threads.map((t) => {
            const displayName = t.is_group
              ? (t.name || t.auto_name || "Group chat")
              : (t.other?.name || "Unknown");
            return (
              <Pressable
                key={t.thread_id}
                testID={`dm-thread-${t.thread_id}`}
                onPress={() => router.push({ pathname: "/community/dm/[thread_id]", params: { thread_id: t.thread_id } })}
                style={({ pressed }) => [styles.row, pressed && { opacity: 0.7 }]}
              >
                {t.is_group ? (
                  <View style={styles.groupAvatar}>
                    <Ionicons name="people" size={22} color={colors.gold} />
                  </View>
                ) : (
                  <Avatar name={t.other?.name} picture={t.other?.picture ?? null} size={48} />
                )}
                <View style={styles.middle}>
                  <View style={styles.topLine}>
                    <Text style={styles.name} numberOfLines={1}>
                      {t.is_group ? `👥  ${displayName}` : displayName}
                    </Text>
                    {t.last_message_at ? <Text style={styles.time}>{timeAgo(t.last_message_at)}</Text> : null}
                  </View>
                  <View style={styles.bottomLine}>
                    <Text style={[styles.preview, t.unread > 0 && styles.previewUnread]} numberOfLines={1}>
                      {t.last_message || (t.is_group ? `${t.members?.length || 0} members` : "Say hello")}
                    </Text>
                    {t.unread > 0 ? (
                      <View style={styles.unreadDot}><Text style={styles.unreadText}>{t.unread}</Text></View>
                    ) : null}
                  </View>
                </View>
              </Pressable>
            );
          })}
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}
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
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  empty: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.lg, gap: spacing.sm },
  emptyTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary, marginTop: spacing.sm },
  emptyText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, textAlign: "center" },
  cta: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: spacing.lg,
    paddingVertical: 10,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
    marginTop: spacing.md,
  },
  ctaText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold },
  scroll: { padding: spacing.lg, paddingTop: spacing.md },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginBottom: spacing.sm,
    ...shadow.card,
  },
  middle: { flex: 1, marginLeft: spacing.sm },
  topLine: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  bottomLine: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: 4 },
  name: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  time: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted },
  preview: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, flex: 1, marginRight: spacing.sm },
  previewUnread: { fontFamily: fonts.bodyBold, color: colors.textPrimary },
  unreadDot: {
    minWidth: 20,
    height: 20,
    paddingHorizontal: 6,
    borderRadius: 10,
    backgroundColor: colors.gold,
    alignItems: "center",
    justifyContent: "center",
  },
  unreadText: { fontFamily: fonts.uiSemi, color: colors.primary, fontSize: 11 },
  groupAvatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
});

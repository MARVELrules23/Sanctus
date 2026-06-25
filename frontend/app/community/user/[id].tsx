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
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { api, CommunityPost, CommunityUserPublic, friendAccept, friendDecline, friendRemove, friendRequest, friendStatus, FriendStatus } from "@/src/api";
import Avatar from "@/src/components/Avatar";
import { PostCard } from "@/app/(tabs)/community";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type ProfileResponse = {
  user: CommunityUserPublic;
  posts: CommunityPost[];
  is_self: boolean;
};

type FriendState = { status: FriendStatus; requested_by: string | null };

export default function CommunityUserProfileScreen() {
  const router = useRouter();
  const { user: me } = useAuth();
  const params = useLocalSearchParams<{ id?: string }>();
  const userId = typeof params.id === "string" ? params.id : "";

  const [data, setData] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [friend, setFriend] = useState<FriendState>({ status: "none", requested_by: null });
  const [friendBusy, setFriendBusy] = useState(false);

  const load = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const r = await api<ProfileResponse>(`/community/users/${userId}`);
      setData(r);
      if (!r.is_self) {
        try {
          const fs = await friendStatus(userId);
          setFriend(fs);
        } catch {
          /* ignore */
        }
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { void load(); }, [load]);

  // Drive the right button copy / action based on the friendship state.
  // We treat "self" the same as having no button.
  const onFriendAction = async () => {
    if (!userId || friendBusy || !me) return;
    setFriendBusy(true);
    try {
      if (friend.status === "none") {
        await friendRequest(userId);
        setFriend({ status: "pending", requested_by: me.user_id });
      } else if (friend.status === "pending" && friend.requested_by === me.user_id) {
        // I sent it — clicking again cancels.
        await friendDecline(userId);
        setFriend({ status: "none", requested_by: null });
      } else if (friend.status === "pending" && friend.requested_by !== me.user_id) {
        await friendAccept(userId);
        setFriend({ status: "accepted", requested_by: friend.requested_by });
      } else if (friend.status === "accepted") {
        await friendRemove(userId);
        setFriend({ status: "none", requested_by: null });
      }
    } catch (e) {
      console.warn("friend action failed", e);
    } finally {
      setFriendBusy(false);
    }
  };

  // Compute button label/icon/color from state — kept inline so it's
  // obvious at a glance which copy maps to which state.
  const friendUi = (() => {
    if (friend.status === "accepted")
      return { label: "Friends", icon: "checkmark-circle" as const, accent: true };
    if (friend.status === "pending" && friend.requested_by === me?.user_id)
      return { label: "Cancel request", icon: "time-outline" as const, accent: false };
    if (friend.status === "pending")
      return { label: "Accept request", icon: "person-add" as const, accent: true };
    return { label: "Add friend", icon: "person-add-outline" as const, accent: true };
  })();

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="community-user-profile">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="profile-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Profile</Text>
        <View style={{ width: 26 }} />
      </View>

      {loading || !data ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.identity}>
            <Avatar name={data.user.name} picture={data.user.picture ?? null} size={88} />
            <Text style={styles.name}>{data.user.name}</Text>
            {(() => {
              const cap = (s?: string | null) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : "");
              const parts = [
                cap(data.user.denomination),
                cap(data.user.tradition_path),
                data.user.age ? `${data.user.age}` : "",
              ].filter(Boolean);
              return parts.length ? <Text style={styles.bio}>{parts.join("  ·  ")}</Text> : null;
            })()}
            {!data.is_self ? (
              <View style={styles.actionRow}>
                <Pressable
                  onPress={onFriendAction}
                  disabled={friendBusy}
                  style={({ pressed }) => [
                    styles.cta,
                    !friendUi.accent && styles.ctaSecondary,
                    (pressed || friendBusy) && { opacity: 0.7 },
                  ]}
                  testID="profile-friend-button"
                >
                  <Ionicons
                    name={friendUi.icon}
                    size={16}
                    color={friendUi.accent ? colors.gold : colors.primary}
                  />
                  <Text style={[styles.ctaText, !friendUi.accent && styles.ctaTextSecondary]}>
                    {friendUi.label}
                  </Text>
                </Pressable>
                <Pressable
                  onPress={() => router.push({ pathname: "/community/dm/[thread_id]", params: { thread_id: "new", other_id: data.user.user_id } })}
                  style={({ pressed }) => [styles.cta, styles.ctaSecondary, pressed && { opacity: 0.7 }]}
                  testID="profile-dm"
                >
                  <Ionicons name="paper-plane-outline" size={16} color={colors.primary} />
                  <Text style={[styles.ctaText, styles.ctaTextSecondary]}>Message</Text>
                </Pressable>
              </View>
            ) : null}
          </View>

          <Text style={styles.sectionTitle}>Recent posts</Text>
          {data.posts.length === 0 ? (
            <Text style={styles.empty}>No posts yet.</Text>
          ) : (
            data.posts.map((p) => (
              <PostCard
                key={p.post_id}
                post={p}
                currentUser={me}
                onPress={() => router.push({ pathname: "/community/post/[id]", params: { id: p.post_id } })}
                onLike={async () => {
                  try {
                    const r = await api<{ liked: boolean; like_count: number }>(`/community/posts/${p.post_id}/like`, { method: "POST" });
                    setData((d) => d ? {
                      ...d,
                      posts: d.posts.map((x) => x.post_id === p.post_id
                        ? { ...x, liked_by_me: r.liked, like_count: r.like_count }
                        : x),
                    } : d);
                  } catch { /* ignore */ }
                }}
                onAuthor={() => {}}
                onDM={() => router.push({ pathname: "/community/dm/[thread_id]", params: { thread_id: "new", other_id: data.user.user_id } })}
                compact
              />
            ))
          )}
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
  scroll: { padding: spacing.lg },
  identity: { alignItems: "center", paddingVertical: spacing.lg, gap: spacing.sm },
  name: { fontFamily: fonts.headingBold, fontSize: 22, color: colors.textPrimary, marginTop: spacing.sm },
  bio: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold, marginTop: 4, letterSpacing: 0.3 },
  cta: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: spacing.lg,
    paddingVertical: 10,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
    marginTop: spacing.sm,
    ...shadow.card,
  },
  ctaText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold },
  actionRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  ctaSecondary: {
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.primary,
  },
  ctaTextSecondary: { color: colors.primary },
  sectionTitle: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 2.5,
    color: colors.gold,
    textTransform: "uppercase",
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  empty: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, textAlign: "center", paddingVertical: spacing.lg },
});

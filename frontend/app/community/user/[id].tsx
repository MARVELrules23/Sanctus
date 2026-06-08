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

import { api, CommunityPost, CommunityUserPublic } from "@/src/api";
import Avatar from "@/src/components/Avatar";
import { PostCard } from "@/app/(tabs)/community";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type ProfileResponse = {
  user: CommunityUserPublic;
  posts: CommunityPost[];
  is_self: boolean;
};

export default function CommunityUserProfileScreen() {
  const router = useRouter();
  const { user: me } = useAuth();
  const params = useLocalSearchParams<{ id?: string }>();
  const userId = typeof params.id === "string" ? params.id : "";

  const [data, setData] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const r = await api<ProfileResponse>(`/community/users/${userId}`);
      setData(r);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { void load(); }, [load]);

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
            {!data.is_self ? (
              <Pressable
                onPress={() => router.push({ pathname: "/community/dm/[thread_id]", params: { thread_id: "new", other_id: data.user.user_id } })}
                style={({ pressed }) => [styles.cta, pressed && { opacity: 0.7 }]}
                testID="profile-dm"
              >
                <Ionicons name="paper-plane-outline" size={16} color={colors.gold} />
                <Text style={styles.ctaText}>Message</Text>
              </Pressable>
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

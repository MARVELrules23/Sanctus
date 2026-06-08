import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { api, CommunityPost, CommunityReply } from "@/src/api";
import Avatar from "@/src/components/Avatar";
import { useAuth } from "@/src/auth-context";
import { colorForLiturgical, colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { timeAgo } from "@/src/utils/time-ago";

export default function PostDetailScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const params = useLocalSearchParams<{ id?: string }>();
  const postId = typeof params.id === "string" ? params.id : "";

  const [post, setPost] = useState<CommunityPost | null>(null);
  const [replies, setReplies] = useState<CommunityReply[]>([]);
  const [loading, setLoading] = useState(true);
  const [replyText, setReplyText] = useState("");
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    if (!postId) return;
    setLoading(true);
    try {
      const [p, r] = await Promise.all([
        api<CommunityPost>(`/community/posts/${postId}`),
        api<{ items: CommunityReply[] }>(`/community/posts/${postId}/replies`),
      ]);
      setPost(p);
      setReplies(r.items || []);
    } catch (e: any) {
      Alert.alert("Couldn't load post", e?.message || "Please try again.");
      router.back();
    } finally {
      setLoading(false);
    }
  }, [postId, router]);

  useEffect(() => {
    void load();
  }, [load]);

  const toggleLike = async () => {
    if (!post) return;
    const optimistic = { ...post, liked_by_me: !post.liked_by_me, like_count: Math.max(0, post.like_count + (post.liked_by_me ? -1 : 1)) };
    setPost(optimistic);
    try {
      const r = await api<{ liked: boolean; like_count: number }>(`/community/posts/${post.post_id}/like`, { method: "POST" });
      setPost((prev) => prev ? { ...prev, liked_by_me: r.liked, like_count: r.like_count } : prev);
    } catch {
      setPost(post);
    }
  };

  const submitReply = async () => {
    const body = replyText.trim();
    if (!body || !post) return;
    setSending(true);
    try {
      const r = await api<CommunityReply>(`/community/posts/${post.post_id}/replies`, {
        method: "POST",
        body: { body },
      });
      setReplies((prev) => [...prev, r]);
      setPost((prev) => prev ? { ...prev, reply_count: prev.reply_count + 1 } : prev);
      setReplyText("");
    } catch (e: any) {
      Alert.alert("Couldn't reply", e?.message || "Please try again.");
    } finally {
      setSending(false);
    }
  };

  const deleteReply = (reply: CommunityReply) => {
    Alert.alert("Delete reply?", "This cannot be undone.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await api(`/community/replies/${reply.reply_id}`, { method: "DELETE" });
            setReplies((prev) => prev.filter((r) => r.reply_id !== reply.reply_id));
            setPost((p) => p ? { ...p, reply_count: Math.max(0, p.reply_count - 1) } : p);
          } catch (e: any) {
            Alert.alert("Couldn't delete", e?.message || "Please try again.");
          }
        },
      },
    ]);
  };

  const litColor = post?.liturgical_color ? colorForLiturgical(post.liturgical_color) : null;

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="post-detail-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="post-detail-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Post</Text>
        <View style={{ width: 26 }} />
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={20}>
        {loading || !post ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.gold} />
          </View>
        ) : (
          <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
            <View style={styles.card}>
              {litColor ? <View style={[styles.litRail, { backgroundColor: litColor }]} /> : null}
              <View style={{ flex: 1 }}>
                <Pressable
                  onPress={() => router.push({ pathname: "/community/user/[id]", params: { id: post.author.user_id } })}
                  style={styles.authorRow}
                  hitSlop={6}
                >
                  <Avatar name={post.author.name} picture={post.author.picture ?? null} size={40} />
                  <View style={{ marginLeft: spacing.sm }}>
                    <Text style={styles.authorName}>{post.author.name}</Text>
                    <Text style={styles.authorMeta}>{timeAgo(post.created_at)}{post.topic ? ` · ${pretty(post.topic)}` : ""}</Text>
                  </View>
                </Pressable>
                <Text style={styles.body}>{post.body}</Text>
                <View style={styles.footerRow}>
                  <Pressable onPress={toggleLike} hitSlop={8} style={styles.footerBtn} testID="post-detail-like">
                    <Ionicons
                      name={post.liked_by_me ? "heart" : "heart-outline"}
                      size={20}
                      color={post.liked_by_me ? colors.liturgical.red : colors.textSecondary}
                    />
                    <Text style={styles.footerCount}>{post.like_count}</Text>
                  </Pressable>
                  <View style={styles.footerBtn}>
                    <Ionicons name="chatbubble-outline" size={18} color={colors.textSecondary} />
                    <Text style={styles.footerCount}>{post.reply_count}</Text>
                  </View>
                  {post.author.user_id !== user?.user_id ? (
                    <Pressable
                      onPress={() => router.push({ pathname: "/community/dm/[thread_id]", params: { thread_id: "new", other_id: post.author.user_id } })}
                      hitSlop={8}
                      style={styles.footerBtn}
                      testID="post-detail-dm"
                    >
                      <Ionicons name="paper-plane-outline" size={18} color={colors.textSecondary} />
                      <Text style={styles.footerCount}>Message</Text>
                    </Pressable>
                  ) : null}
                </View>
              </View>
            </View>

            {/* Replies */}
            <Text style={styles.repliesHeader}>
              {replies.length === 0 ? "No replies yet" : `${replies.length} reply${replies.length === 1 ? "" : "s"}`}
            </Text>
            {replies.map((r) => {
              const mine = user?.user_id === r.author.user_id;
              return (
                <View key={r.reply_id} style={styles.replyRow} testID={`community-reply-${r.reply_id}`}>
                  <Avatar name={r.author.name} picture={r.author.picture ?? null} size={32} />
                  <View style={{ flex: 1, marginLeft: spacing.sm }}>
                    <View style={styles.replyBubble}>
                      <Text style={styles.replyAuthor}>{r.author.name}</Text>
                      <Text style={styles.replyText}>{r.body}</Text>
                    </View>
                    <View style={styles.replyFooter}>
                      <Text style={styles.replyMeta}>{timeAgo(r.created_at)}</Text>
                      {mine ? (
                        <Pressable
                          onPress={() => deleteReply(r)}
                          hitSlop={6}
                          testID={`community-reply-delete-${r.reply_id}`}
                        >
                          <Text style={styles.replyDelete}>Delete</Text>
                        </Pressable>
                      ) : null}
                    </View>
                  </View>
                </View>
              );
            })}
            <View style={{ height: 24 }} />
          </ScrollView>
        )}

        {/* Reply composer */}
        {post ? (
          <View style={styles.replyComposer}>
            <TextInput
              testID="post-detail-reply-input"
              value={replyText}
              onChangeText={setReplyText}
              placeholder="Write a charitable reply…"
              placeholderTextColor={colors.textMuted}
              style={styles.replyInput}
              multiline
              maxLength={800}
            />
            <Pressable
              testID="post-detail-reply-submit"
              onPress={submitReply}
              disabled={!replyText.trim() || sending}
              style={({ pressed }) => [
                styles.replySend,
                (!replyText.trim() || sending) && { opacity: 0.4 },
                pressed && { opacity: 0.7 },
              ]}
            >
              <Ionicons name={sending ? "hourglass-outline" : "send"} size={18} color={colors.gold} />
            </Pressable>
          </View>
        ) : null}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function pretty(slug: string): string {
  return slug.split("-").map((s) => s[0]?.toUpperCase() + s.slice(1)).join(" ");
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
  scroll: { padding: spacing.lg },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  card: {
    flexDirection: "row",
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  litRail: { width: 3, borderRadius: 2, marginRight: spacing.sm, alignSelf: "stretch", opacity: 0.7 },
  authorRow: { flexDirection: "row", alignItems: "center" },
  authorName: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  authorMeta: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 1 },
  body: { fontFamily: fonts.bodyRegular, fontSize: 16, lineHeight: 24, color: colors.textPrimary, marginTop: spacing.sm },
  footerRow: { flexDirection: "row", gap: spacing.lg, marginTop: spacing.md },
  footerBtn: { flexDirection: "row", alignItems: "center", gap: 4 },
  footerCount: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textSecondary },
  repliesHeader: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 2, color: colors.gold, textTransform: "uppercase", marginTop: spacing.lg, marginBottom: spacing.sm },
  replyRow: { flexDirection: "row", marginBottom: spacing.md },
  replyBubble: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  replyAuthor: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textPrimary, marginBottom: 2 },
  replyText: { fontFamily: fonts.bodyRegular, fontSize: 14, lineHeight: 20, color: colors.textPrimary },
  replyFooter: { flexDirection: "row", gap: spacing.md, marginTop: 4, marginLeft: 4 },
  replyMeta: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted },
  replyDelete: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.liturgical.red },
  replyComposer: {
    flexDirection: "row",
    alignItems: "flex-end",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
    gap: spacing.sm,
  },
  replyInput: {
    flex: 1,
    minHeight: 40,
    maxHeight: 120,
    backgroundColor: colors.background,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textPrimary,
    textAlignVertical: "center",
  },
  replySend: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
});

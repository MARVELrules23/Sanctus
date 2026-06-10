import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
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
import { useFocusEffect, useRouter } from "expo-router";

import {
  api,
  CommunityFeed,
  CommunityPost,
  CommunityTopic,
  REPORT_REASONS_FALLBACK,
  User,
} from "@/src/api";
import Avatar from "@/src/components/Avatar";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import { useAuth } from "@/src/auth-context";
import { colorForLiturgical, colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { timeAgo } from "@/src/utils/time-ago";

const DEFAULT_TOPICS: CommunityTopic[] = [
  { slug: null, label: "Parish", icon: "people-outline" },
];

export default function CommunityScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [topics, setTopics] = useState<CommunityTopic[]>(DEFAULT_TOPICS);
  const [reportReasons, setReportReasons] = useState<string[]>(REPORT_REASONS_FALLBACK);
  const [activeTopic, setActiveTopic] = useState<string | null>(null);
  const [feed, setFeed] = useState<CommunityFeed | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  // Composer
  const [showCompose, setShowCompose] = useState(false);
  const [composerBody, setComposerBody] = useState("");
  const [composerTopic, setComposerTopic] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Report
  const [reportTarget, setReportTarget] = useState<CommunityPost | null>(null);
  const [reportReason, setReportReason] = useState<string | null>(null);
  const [reportDetail, setReportDetail] = useState("");
  const [reporting, setReporting] = useState(false);

  const loadTopics = useCallback(async () => {
    try {
      const r = await api<{ items: CommunityTopic[]; report_reasons: string[] }>("/community/topics");
      if (r.items?.length) setTopics(r.items);
      if (r.report_reasons?.length) setReportReasons(r.report_reasons);
    } catch (e) {
      // silent
    }
  }, []);

  const loadFeed = useCallback(async (topic: string | null) => {
    setLoading(true);
    try {
      const path = topic ? `/community/feed?topic=${encodeURIComponent(topic)}` : "/community/feed";
      const r = await api<CommunityFeed>(path);
      setFeed(r);
    } catch (e: any) {
      console.warn("feed load failed", e);
      Alert.alert("Couldn't load feed", e?.message || "Please try again.");
      setFeed({ items: [], next_cursor: null, topic });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTopics();
  }, [loadTopics]);

  useFocusEffect(
    useCallback(() => {
      void loadFeed(activeTopic);
    }, [loadFeed, activeTopic]),
  );

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const path = activeTopic ? `/community/feed?topic=${encodeURIComponent(activeTopic)}` : "/community/feed";
      const r = await api<CommunityFeed>(path);
      setFeed(r);
    } catch (e) {
      // ignore
    } finally {
      setRefreshing(false);
    }
  }, [activeTopic]);

  const loadMore = useCallback(async () => {
    if (!feed?.next_cursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const params = new URLSearchParams();
      if (activeTopic) params.set("topic", activeTopic);
      params.set("before", feed.next_cursor);
      const r = await api<CommunityFeed>(`/community/feed?${params.toString()}`);
      setFeed((f) => (f ? { ...r, items: [...f.items, ...r.items] } : r));
    } catch {
      // ignore
    } finally {
      setLoadingMore(false);
    }
  }, [activeTopic, feed, loadingMore]);

  const openCompose = () => {
    setComposerBody("");
    setComposerTopic(activeTopic);
    setShowCompose(true);
  };

  const submitPost = async () => {
    const body = composerBody.trim();
    if (!body) return;
    setSubmitting(true);
    try {
      const created = await api<CommunityPost>("/community/posts", {
        method: "POST",
        body: { body, topic: composerTopic },
      });
      // Show in feed if it matches current filter
      if (activeTopic === null || activeTopic === created.topic) {
        setFeed((f) => f ? { ...f, items: [created, ...f.items] } : { items: [created], next_cursor: null, topic: activeTopic });
      } else {
        // Switch to the topic the user posted to
        setActiveTopic(created.topic);
      }
      setShowCompose(false);
      setComposerBody("");
    } catch (e: any) {
      Alert.alert("Couldn't post", e?.message || "Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const toggleLike = async (post: CommunityPost) => {
    // optimistic
    setFeed((f) => f ? {
      ...f,
      items: f.items.map((p) => p.post_id === post.post_id
        ? { ...p, liked_by_me: !p.liked_by_me, like_count: Math.max(0, p.like_count + (p.liked_by_me ? -1 : 1)) }
        : p),
    } : f);
    try {
      const r = await api<{ liked: boolean; like_count: number }>(`/community/posts/${post.post_id}/like`, { method: "POST" });
      setFeed((f) => f ? {
        ...f,
        items: f.items.map((p) => p.post_id === post.post_id
          ? { ...p, liked_by_me: r.liked, like_count: r.like_count }
          : p),
      } : f);
    } catch {
      // rollback
      setFeed((f) => f ? {
        ...f,
        items: f.items.map((p) => p.post_id === post.post_id ? post : p),
      } : f);
    }
  };

  const deletePost = (post: CommunityPost) => {
    Alert.alert("Delete post?", "This cannot be undone.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await api(`/community/posts/${post.post_id}`, { method: "DELETE" });
            setFeed((f) => f ? { ...f, items: f.items.filter((p) => p.post_id !== post.post_id) } : f);
          } catch (e: any) {
            Alert.alert("Couldn't delete", e?.message || "Please try again.");
          }
        },
      },
    ]);
  };

  const openReport = (post: CommunityPost) => {
    setReportTarget(post);
    setReportReason(null);
    setReportDetail("");
  };
  const submitReport = async () => {
    if (!reportTarget || !reportReason) return;
    setReporting(true);
    try {
      await api("/community/report", {
        method: "POST",
        body: { target_type: "post", target_id: reportTarget.post_id, reason: reportReason, detail: reportDetail },
      });
      setReportTarget(null);
      Alert.alert("Thank you", "Your report has been received. We review reports carefully.");
    } catch (e: any) {
      Alert.alert("Couldn't send report", e?.message || "Please try again.");
    } finally {
      setReporting(false);
    }
  };

  const activeTopicLabel = useMemo(() => {
    const t = topics.find((x) => (x.slug ?? null) === activeTopic);
    return t?.label || "Parish";
  }, [topics, activeTopic]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="community-screen">
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Community</Text>
          <Text style={styles.headerSub}>The parish gathers — speak in charity.</Text>
        </View>
        <View style={styles.headerActions}>
          <Pressable
            testID="community-library-btn"
            onPress={() => router.push("/library")}
            hitSlop={8}
            style={({ pressed }) => [styles.iconBtn, pressed && styles.pressed]}
          >
            <Ionicons name="library-outline" size={20} color={colors.primary} />
          </Pressable>
          <Pressable
            testID="community-charities-btn"
            onPress={() => router.push("/charities")}
            hitSlop={8}
            style={({ pressed }) => [styles.iconBtn, pressed && styles.pressed]}
          >
            <Ionicons name="heart-circle-outline" size={20} color={colors.primary} />
          </Pressable>
          <Pressable
            testID="community-people-btn"
            onPress={() => router.push("/community/people")}
            hitSlop={8}
            style={({ pressed }) => [styles.iconBtn, pressed && styles.pressed]}
          >
            <Ionicons name="person-add-outline" size={20} color={colors.primary} />
          </Pressable>
          <Pressable
            testID="community-dm-btn"
            onPress={() => router.push("/community/dm")}
            hitSlop={8}
            style={({ pressed }) => [styles.iconBtn, pressed && styles.pressed]}
          >
            <Ionicons name="chatbubbles-outline" size={20} color={colors.primary} />
          </Pressable>
        </View>
      </View>

      {/* Topic chips */}
      <View style={styles.chipsWrap}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipsRow}>
          {topics.map((t) => {
            const active = (t.slug ?? null) === activeTopic;
            return (
              <Pressable
                key={t.slug ?? "__all"}
                testID={`community-topic-${t.slug ?? "all"}`}
                onPress={() => setActiveTopic(t.slug ?? null)}
                style={({ pressed }) => [styles.chip, active && styles.chipActive, pressed && styles.pressed]}
              >
                <Ionicons name={t.icon as any} size={14} color={active ? colors.gold : colors.textSecondary} />
                <Text style={[styles.chipText, active && styles.chipTextActive]}>{t.label}</Text>
              </Pressable>
            );
          })}
        </ScrollView>
      </View>

      {loading && !feed ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
        </View>
      ) : (
        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={styles.scrollContent}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />}
          onScroll={(e) => {
            const layout = e.nativeEvent.layoutMeasurement.height;
            const offsetY = e.nativeEvent.contentOffset.y;
            const contentH = e.nativeEvent.contentSize.height;
            if (offsetY + layout >= contentH - 120) {
              void loadMore();
            }
          }}
          scrollEventThrottle={250}
        >
          {!feed?.items.length ? (
            <View style={styles.empty}>
              <Ionicons name="leaf-outline" size={32} color={colors.gold} />
              <Text style={styles.emptyTitle}>No posts yet</Text>
              <Text style={styles.emptyText}>Be the first to share something edifying in {activeTopicLabel}.</Text>
              <Pressable
                onPress={openCompose}
                style={({ pressed }) => [styles.emptyCta, pressed && styles.pressed]}
                testID="community-empty-compose"
              >
                <Ionicons name="create-outline" size={16} color={colors.gold} />
                <Text style={styles.emptyCtaText}>Write the first post</Text>
              </Pressable>
            </View>
          ) : (
            <>
              {feed.items.map((p) => (
                <PostCard
                  key={p.post_id}
                  post={p}
                  currentUser={user}
                  onPress={() => router.push({ pathname: "/community/post/[id]", params: { id: p.post_id } })}
                  onLike={() => toggleLike(p)}
                  onAuthor={() => router.push({ pathname: "/community/user/[id]", params: { id: p.author.user_id } })}
                  onDelete={() => deletePost(p)}
                  onReport={() => openReport(p)}
                  onDM={() => router.push({ pathname: "/community/dm/[thread_id]", params: { thread_id: "new", other_id: p.author.user_id } })}
                />
              ))}
              {loadingMore ? (
                <View style={{ paddingVertical: spacing.md }}>
                  <ActivityIndicator color={colors.gold} />
                </View>
              ) : null}
            </>
          )}
          <View style={{ height: 100 }} />
        </ScrollView>
      )}

      {/* FAB */}
      <Pressable
        testID="community-fab-compose"
        onPress={openCompose}
        style={({ pressed }) => [styles.fab, pressed && styles.pressed]}
      >
        <Ionicons name="create" size={22} color={colors.gold} />
      </Pressable>

      {/* Composer modal */}
      <Modal
        transparent
        visible={showCompose}
        animationType="slide"
        onRequestClose={() => setShowCompose(false)}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={styles.modalScrim}
        >
          <Pressable style={{ flex: 1 }} onPress={() => setShowCompose(false)} testID="community-compose-scrim" />
          <View style={styles.composerSheet}>
            <View style={styles.composerHeader}>
              <Pressable onPress={() => setShowCompose(false)} testID="community-compose-cancel">
                <Text style={styles.composerCancel}>Cancel</Text>
              </Pressable>
              <Text style={styles.composerTitle}>New post</Text>
              <Pressable
                onPress={submitPost}
                disabled={!composerBody.trim() || submitting}
                testID="community-compose-submit"
              >
                <Text style={[styles.composerSubmit, (!composerBody.trim() || submitting) && styles.composerSubmitDisabled]}>
                  {submitting ? "Posting…" : "Post"}
                </Text>
              </Pressable>
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.composerTopics}>
              {topics.map((t) => {
                const active = (t.slug ?? null) === composerTopic;
                return (
                  <Pressable
                    key={t.slug ?? "__all"}
                    testID={`community-compose-topic-${t.slug ?? "all"}`}
                    onPress={() => setComposerTopic(t.slug ?? null)}
                    style={({ pressed }) => [styles.composerTopic, active && styles.composerTopicActive, pressed && styles.pressed]}
                  >
                    <Text style={[styles.composerTopicText, active && styles.composerTopicTextActive]}>{t.label}</Text>
                  </Pressable>
                );
              })}
            </ScrollView>
            <TextInput
              testID="community-compose-input"
              value={composerBody}
              onChangeText={setComposerBody}
              placeholder="Share a reflection, an intention, a question…"
              placeholderTextColor={colors.textMuted}
              style={styles.composerInput}
              multiline
              autoFocus
              maxLength={1500}
            />
            <Text style={styles.composerHint}>{composerBody.length}/1500 — be charitable; this is a public parish.</Text>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* Report modal */}
      <Modal
        transparent
        visible={!!reportTarget}
        animationType="fade"
        onRequestClose={() => setReportTarget(null)}
      >
        <Pressable style={styles.modalScrim} onPress={() => setReportTarget(null)} testID="community-report-scrim">
          <Pressable style={styles.reportSheet} onPress={(e) => e.stopPropagation?.()}>
            <Text style={styles.reportTitle}>Report post</Text>
            <Text style={styles.reportSub}>Reports are reviewed by stewards. Please choose a reason:</Text>
            {reportReasons.map((reason) => {
              const active = reportReason === reason;
              return (
                <Pressable
                  key={reason}
                  testID={`community-report-reason-${reason}`}
                  onPress={() => setReportReason(reason)}
                  style={({ pressed }) => [styles.reasonRow, active && styles.reasonRowActive, pressed && styles.pressed]}
                >
                  <Ionicons
                    name={active ? "radio-button-on" : "radio-button-off"}
                    size={18}
                    color={active ? colors.primary : colors.textMuted}
                  />
                  <Text style={styles.reasonText}>{reason}</Text>
                </Pressable>
              );
            })}
            <TextInput
              testID="community-report-detail"
              value={reportDetail}
              onChangeText={setReportDetail}
              placeholder="Optional detail (max 500 chars)"
              placeholderTextColor={colors.textMuted}
              style={styles.reportDetail}
              multiline
              maxLength={500}
            />
            <View style={styles.reportActions}>
              <Pressable
                onPress={() => setReportTarget(null)}
                style={({ pressed }) => [styles.reportCancel, pressed && styles.pressed]}
              >
                <Text style={styles.reportCancelText}>Cancel</Text>
              </Pressable>
              <Pressable
                testID="community-report-submit"
                disabled={!reportReason || reporting}
                onPress={submitReport}
                style={({ pressed }) => [styles.reportSubmit, (!reportReason || reporting) && { opacity: 0.4 }, pressed && styles.pressed]}
              >
                <Text style={styles.reportSubmitText}>{reporting ? "Sending…" : "Send report"}</Text>
              </Pressable>
            </View>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

export function PostCard({
  post,
  currentUser,
  onPress,
  onLike,
  onAuthor,
  onDelete,
  onReport,
  onDM,
  compact = false,
}: {
  post: CommunityPost;
  currentUser: User | null;
  onPress?: () => void;
  onLike?: () => void;
  onAuthor?: () => void;
  onDelete?: () => void;
  onReport?: () => void;
  onDM?: () => void;
  compact?: boolean;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const isMine = !!currentUser && post.author.user_id === currentUser.user_id;
  const litColor = post.liturgical_color ? colorForLiturgical(post.liturgical_color) : null;
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.postCard, pressed && onPress && styles.pressed]}
      testID={`community-post-${post.post_id}`}
    >
      {litColor ? <View style={[styles.litRail, { backgroundColor: litColor }]} /> : null}
      <View style={{ flex: 1 }}>
        <View style={styles.postHeader}>
          <Pressable onPress={onAuthor} hitSlop={6} testID={`community-author-${post.author.user_id}`}>
            <Avatar name={post.author.name} picture={post.author.picture ?? null} size={36} />
          </Pressable>
          <Pressable onPress={onAuthor} style={{ flex: 1, marginLeft: spacing.sm }} hitSlop={4}>
            <Text style={styles.authorName} numberOfLines={1}>{post.author.name}</Text>
            <Text style={styles.postMeta}>{timeAgo(post.created_at)}{post.topic ? ` · ${prettyTopic(post.topic)}` : ""}</Text>
          </Pressable>
          <Pressable
            onPress={(e) => { e.stopPropagation?.(); setMenuOpen(true); }}
            hitSlop={10}
            testID={`community-post-menu-${post.post_id}`}
          >
            <Ionicons name="ellipsis-horizontal" size={20} color={colors.textMuted} />
          </Pressable>
        </View>

        <Text style={styles.postBody} numberOfLines={compact ? 4 : undefined}>
          {post.body}
        </Text>

        {post.challenge && post.challenge.slug ? (
          <View
            style={styles.challengeChip}
            testID={`community-post-challenge-${post.post_id}`}
          >
            <Ionicons name="flame-outline" size={11} color={colors.gold} />
            <Text style={styles.challengeChipText}>
              {post.challenge.name || "Challenge"}
              {post.challenge.day_index ? ` · Day ${post.challenge.day_index}` : ""}
            </Text>
          </View>
        ) : null}

        <View style={styles.postFooter}>
          <Pressable
            onPress={(e) => { e.stopPropagation?.(); onLike?.(); }}
            hitSlop={8}
            style={({ pressed }) => [styles.footerBtn, pressed && styles.pressed]}
            testID={`community-like-${post.post_id}`}
          >
            <Ionicons
              name={post.liked_by_me ? "heart" : "heart-outline"}
              size={18}
              color={post.liked_by_me ? colors.liturgical.red : colors.textSecondary}
            />
            <Text style={styles.footerCount}>{post.like_count}</Text>
          </Pressable>
          <Pressable
            onPress={(e) => { e.stopPropagation?.(); onPress?.(); }}
            hitSlop={8}
            style={({ pressed }) => [styles.footerBtn, pressed && styles.pressed]}
            testID={`community-replies-${post.post_id}`}
          >
            <Ionicons name="chatbubble-outline" size={17} color={colors.textSecondary} />
            <Text style={styles.footerCount}>{post.reply_count}</Text>
          </Pressable>
          {!isMine ? (
            <Pressable
              onPress={(e) => { e.stopPropagation?.(); onDM?.(); }}
              hitSlop={8}
              style={({ pressed }) => [styles.footerBtn, pressed && styles.pressed]}
              testID={`community-dm-author-${post.author.user_id}`}
            >
              <Ionicons name="paper-plane-outline" size={16} color={colors.textSecondary} />
              <Text style={styles.footerCount}>Message</Text>
            </Pressable>
          ) : null}
          {post.liturgical_season ? (
            <View style={{ marginLeft: "auto" }}>
              <LiturgicalBadge color={post.liturgical_color || "green"} label={post.liturgical_season} />
            </View>
          ) : null}
        </View>
      </View>

      {/* Action menu */}
      <Modal transparent visible={menuOpen} animationType="fade" onRequestClose={() => setMenuOpen(false)}>
        <Pressable style={styles.modalScrim} onPress={() => setMenuOpen(false)}>
          <Pressable style={styles.menuSheet} onPress={(e) => e.stopPropagation?.()}>
            {isMine ? (
              <Pressable
                testID={`community-menu-delete-${post.post_id}`}
                onPress={() => { setMenuOpen(false); onDelete?.(); }}
                style={({ pressed }) => [styles.menuItem, pressed && styles.pressed]}
              >
                <Ionicons name="trash-outline" size={18} color={colors.liturgical.red} />
                <Text style={[styles.menuItemText, { color: colors.liturgical.red }]}>Delete post</Text>
              </Pressable>
            ) : (
              <>
                <Pressable
                  testID={`community-menu-report-${post.post_id}`}
                  onPress={() => { setMenuOpen(false); onReport?.(); }}
                  style={({ pressed }) => [styles.menuItem, pressed && styles.pressed]}
                >
                  <Ionicons name="flag-outline" size={18} color={colors.liturgical.red} />
                  <Text style={[styles.menuItemText, { color: colors.liturgical.red }]}>Report</Text>
                </Pressable>
                <Pressable
                  testID={`community-menu-dm-${post.post_id}`}
                  onPress={() => { setMenuOpen(false); onDM?.(); }}
                  style={({ pressed }) => [styles.menuItem, pressed && styles.pressed]}
                >
                  <Ionicons name="paper-plane-outline" size={18} color={colors.primary} />
                  <Text style={styles.menuItemText}>Message author</Text>
                </Pressable>
              </>
            )}
            <Pressable
              onPress={() => setMenuOpen(false)}
              style={({ pressed }) => [styles.menuCancel, pressed && styles.pressed]}
            >
              <Text style={styles.menuCancelText}>Cancel</Text>
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>
    </Pressable>
  );
}

function prettyTopic(slug: string): string {
  return slug
    .split("-")
    .map((s) => s[0]?.toUpperCase() + s.slice(1))
    .join(" ");
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
    paddingBottom: spacing.sm,
    gap: spacing.md,
  },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 26, color: colors.textPrimary },
  headerSub: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12, color: colors.textMuted, marginTop: 2 },
  headerActions: { marginLeft: "auto", flexDirection: "row", gap: spacing.sm },
  iconBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  chipsWrap: { borderBottomWidth: 1, borderBottomColor: colors.borderSoft, paddingBottom: spacing.sm },
  chipsRow: { paddingHorizontal: spacing.lg, gap: 8 },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.surface,
  },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary },
  chipTextActive: { color: colors.gold },
  scrollContent: { paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  empty: { alignItems: "center", paddingVertical: spacing.xxl, gap: spacing.sm },
  emptyTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary, marginTop: spacing.sm },
  emptyText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, textAlign: "center", paddingHorizontal: spacing.lg },
  emptyCta: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.lg,
    paddingVertical: 12,
    borderRadius: radius.round,
    marginTop: spacing.md,
  },
  emptyCtaText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold },
  postCard: {
    flexDirection: "row",
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
    overflow: "hidden",
  },
  litRail: {
    width: 3,
    borderRadius: 2,
    marginRight: spacing.sm,
    alignSelf: "stretch",
    opacity: 0.7,
  },
  postHeader: { flexDirection: "row", alignItems: "center" },
  authorName: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  postMeta: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 1 },
  postBody: { fontFamily: fonts.bodyRegular, fontSize: 15, lineHeight: 22, color: colors.textPrimary, marginTop: spacing.sm },
  challengeChip: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: radius.round,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.gold,
    marginTop: spacing.sm,
  },
  challengeChipText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.gold,
    letterSpacing: 0.4,
  },
  postFooter: { flexDirection: "row", alignItems: "center", gap: spacing.lg, marginTop: spacing.md },
  footerBtn: { flexDirection: "row", alignItems: "center", gap: 4 },
  footerCount: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textSecondary },
  fab: {
    position: "absolute",
    right: spacing.lg,
    bottom: spacing.lg + 70,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    ...shadow.card,
    shadowOpacity: 0.2,
    elevation: 6,
  },
  modalScrim: { flex: 1, backgroundColor: "rgba(0,0,0,0.45)", justifyContent: "flex-end" },
  composerSheet: {
    backgroundColor: colors.background,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.xl,
    maxHeight: "85%",
  },
  composerHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: spacing.sm },
  composerCancel: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textSecondary },
  composerTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  composerSubmit: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.primary },
  composerSubmitDisabled: { color: colors.textMuted },
  composerTopics: { gap: 8, paddingVertical: spacing.sm },
  composerTopic: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.surface,
  },
  composerTopicActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  composerTopicText: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textSecondary },
  composerTopicTextActive: { color: colors.gold },
  composerInput: {
    minHeight: 140,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.md,
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textPrimary,
    textAlignVertical: "top",
    marginTop: spacing.sm,
  },
  composerHint: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 11, color: colors.textMuted, marginTop: spacing.sm },
  reportSheet: {
    backgroundColor: colors.background,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xl,
  },
  reportTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  reportSub: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, marginTop: 4, marginBottom: spacing.md },
  reasonRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: 10,
    paddingHorizontal: spacing.sm,
    borderRadius: radius.md,
  },
  reasonRowActive: { backgroundColor: colors.borderSoft },
  reasonText: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary },
  reportDetail: {
    minHeight: 80,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.md,
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textPrimary,
    textAlignVertical: "top",
    marginTop: spacing.sm,
  },
  reportActions: { flexDirection: "row", justifyContent: "flex-end", gap: spacing.sm, marginTop: spacing.md },
  reportCancel: { paddingHorizontal: spacing.lg, paddingVertical: 10 },
  reportCancelText: { fontFamily: fonts.uiSemi, color: colors.textSecondary, fontSize: 13 },
  reportSubmit: { paddingHorizontal: spacing.lg, paddingVertical: 10, borderRadius: radius.round, backgroundColor: colors.liturgical.red },
  reportSubmitText: { fontFamily: fonts.uiSemi, color: "#fff", fontSize: 13 },
  menuSheet: {
    backgroundColor: colors.background,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    paddingTop: spacing.sm,
    paddingBottom: spacing.lg,
  },
  menuItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: 14,
  },
  menuItemText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  menuCancel: { paddingVertical: 14, alignItems: "center", borderTopWidth: 1, borderTopColor: colors.borderSoft, marginTop: spacing.sm },
  menuCancelText: { fontFamily: fonts.uiSemi, color: colors.textSecondary, fontSize: 14 },
  pressed: { opacity: 0.7 },
});

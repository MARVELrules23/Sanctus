import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
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

import { api, CommunityDMMessage, CommunityDMThread, dmRenameGroup, dmRemoveGroupMember } from "@/src/api";
import Avatar from "@/src/components/Avatar";
import { useAuth } from "@/src/auth-context";
import { useNotifications } from "@/src/notifications-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { timeOfDay } from "@/src/utils/time-ago";

export default function DMThreadScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const { markThreadRead, refresh: refreshNotifications } = useNotifications();
  const params = useLocalSearchParams<{ thread_id?: string; other_id?: string }>();
  const incomingThread = typeof params.thread_id === "string" ? params.thread_id : "";
  const incomingOther = typeof params.other_id === "string" ? params.other_id : "";

  const [thread, setThread] = useState<CommunityDMThread | null>(null);
  const [messages, setMessages] = useState<CommunityDMMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<ScrollView | null>(null);
  // Group threads need a tiny in-memory cache of "user_id -> name" so we can
  // label each bubble. Built from the thread.members payload.
  const [showMembers, setShowMembers] = useState(false);

  const bootstrap = useCallback(async () => {
    setLoading(true);
    try {
      let tid = incomingThread;
      if (tid === "new" && incomingOther) {
        const t = await api<CommunityDMThread>("/community/dm/threads", {
          method: "POST",
          body: { user_id: incomingOther },
        });
        tid = t.thread_id;
        setThread(t);
      }
      if (tid && tid !== "new") {
        const r = await api<{ thread: CommunityDMThread; messages: CommunityDMMessage[] }>(
          `/community/dm/threads/${tid}/messages`,
        );
        setThread(r.thread);
        setMessages(r.messages || []);
        // Backend just marked this thread read for us; drop the badge instantly.
        markThreadRead(tid);
      }
    } catch (e: any) {
      Alert.alert("Couldn't open conversation", e?.message || "Please try again.");
      router.back();
    } finally {
      setLoading(false);
    }
  }, [incomingThread, incomingOther, router, markThreadRead]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  // Lightweight poll while screen is open
  useEffect(() => {
    if (!thread) return;
    const id = setInterval(async () => {
      try {
        const r = await api<{ thread: CommunityDMThread; messages: CommunityDMMessage[] }>(
          `/community/dm/threads/${thread.thread_id}/messages`,
        );
        setMessages(r.messages || []);
      } catch {
        // ignore
      }
    }, 5000);
    return () => clearInterval(id);
  }, [thread]);

  useEffect(() => {
    // Scroll to bottom whenever messages change
    if (scrollRef.current) {
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 50);
    }
  }, [messages.length]);

  const send = async () => {
    const text = body.trim();
    if (!text || !thread) return;
    setSending(true);
    const optimistic: CommunityDMMessage = {
      message_id: `tmp_${Date.now()}`,
      thread_id: thread.thread_id,
      sender_id: user?.user_id || "me",
      body: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);
    setBody("");
    try {
      const real = await api<CommunityDMMessage>(`/community/dm/threads/${thread.thread_id}/messages`, {
        method: "POST",
        body: { body: text },
      });
      setMessages((prev) => prev.map((m) => (m.message_id === optimistic.message_id ? real : m)));
    } catch (e: any) {
      Alert.alert("Couldn't send", e?.message || "Please try again.");
      setMessages((prev) => prev.filter((m) => m.message_id !== optimistic.message_id));
      setBody(text);
    } finally {
      setSending(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="dm-thread-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="dm-thread-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        {thread?.is_group ? (
          <Pressable
            onPress={() => setShowMembers(true)}
            style={styles.headerMid}
            hitSlop={6}
            testID="dm-thread-group-info"
          >
            <View style={styles.headerGroupIcon}>
              <Ionicons name="people" size={18} color={colors.gold} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.headerTitle} numberOfLines={1}>
                {thread.name || thread.auto_name || "Group chat"}
              </Text>
              <Text style={styles.headerSub} numberOfLines={1}>
                {thread.members?.length ?? 0} members · tap to manage
              </Text>
            </View>
          </Pressable>
        ) : (
          <Pressable
            onPress={() => thread?.other && router.push({ pathname: "/community/user/[id]", params: { id: thread.other.user_id } })}
            style={styles.headerMid}
            hitSlop={6}
          >
            <Avatar name={thread?.other?.name} picture={thread?.other?.picture ?? null} size={32} />
            <Text style={styles.headerTitle} numberOfLines={1}>{thread?.other?.name || "Conversation"}</Text>
          </Pressable>
        )}
        <View style={{ width: 26 }} />
      </View>

      {/* Group members modal — tap to leave / rename / see who's here */}
      {thread?.is_group && showMembers ? (
        <GroupMembersSheet
          thread={thread}
          meId={user?.user_id || ""}
          onClose={() => setShowMembers(false)}
          onRenamed={(t) => setThread(t)}
          onLeft={() => {
            setShowMembers(false);
            router.back();
          }}
        />
      ) : null}

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={20}>
        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.gold} />
          </View>
        ) : (
          <ScrollView
            ref={scrollRef}
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
          >
            {messages.length === 0 ? (
              <View style={styles.empty}>
                <Text style={styles.emptyText}>
                  Begin a charitable conversation. Pax tecum.
                </Text>
              </View>
            ) : (
              messages.map((m, idx) => {
                const mine = m.sender_id === user?.user_id;
                const prev = messages[idx - 1];
                const showTime = !prev || (new Date(m.created_at).getTime() - new Date(prev.created_at).getTime() > 1000 * 60 * 10);
                // In group threads, show the sender's name above their bubble
                // when the previous message was from someone else (so we
                // don't repeat the label for back-to-back bubbles).
                const showSender = !!thread?.is_group && !mine && (!prev || prev.sender_id !== m.sender_id);
                const senderName = (thread?.members || []).find((u) => u.user_id === m.sender_id)?.name
                  || "Someone";
                return (
                  <View key={m.message_id}>
                    {showTime ? (
                      <Text style={styles.timeStamp}>{timeOfDay(m.created_at)}</Text>
                    ) : null}
                    {showSender ? (
                      <Text style={styles.senderLabel}>{senderName}</Text>
                    ) : null}
                    <View style={[styles.bubbleWrap, mine ? styles.bubbleWrapMine : styles.bubbleWrapOther]}>
                      <View style={[styles.bubble, mine ? styles.bubbleMine : styles.bubbleOther]}>
                        <Text style={[styles.bubbleText, mine && styles.bubbleTextMine]}>{m.body}</Text>
                      </View>
                    </View>
                  </View>
                );
              })
            )}
          </ScrollView>
        )}

        <View style={styles.composer}>
          <TextInput
            testID="dm-thread-input"
            value={body}
            onChangeText={setBody}
            placeholder="Type a message…"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
            multiline
            maxLength={1500}
          />
          <Pressable
            testID="dm-thread-send"
            onPress={send}
            disabled={!body.trim() || sending}
            style={({ pressed }) => [
              styles.sendBtn,
              (!body.trim() || sending) && { opacity: 0.4 },
              pressed && { opacity: 0.7 },
            ]}
          >
            <Ionicons name="send" size={18} color={colors.gold} />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
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
    gap: spacing.sm,
  },
  headerMid: { flexDirection: "row", alignItems: "center", gap: spacing.sm, flex: 1, justifyContent: "center" },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary, maxWidth: 220 },
  headerSub: { fontFamily: fonts.bodyRegular, fontSize: 11, color: colors.textMuted },
  headerGroupIcon: {
    width: 32, height: 32, borderRadius: 16, backgroundColor: colors.primary,
    alignItems: "center", justifyContent: "center",
  },
  senderLabel: {
    fontFamily: fonts.uiSemi, fontSize: 11, color: colors.textMuted,
    marginLeft: spacing.md, marginBottom: 2,
  },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  scroll: { padding: spacing.lg, paddingBottom: spacing.md },
  empty: { paddingTop: spacing.xxl, alignItems: "center" },
  emptyText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, textAlign: "center" },
  timeStamp: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, textAlign: "center", marginVertical: spacing.sm },
  bubbleWrap: { flexDirection: "row", marginBottom: 4 },
  bubbleWrapMine: { justifyContent: "flex-end" },
  bubbleWrapOther: { justifyContent: "flex-start" },
  bubble: {
    maxWidth: "78%",
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    borderRadius: 18,
    ...shadow.card,
  },
  bubbleMine: { backgroundColor: colors.primary, borderBottomRightRadius: 4 },
  bubbleOther: { backgroundColor: colors.surface, borderBottomLeftRadius: 4, borderWidth: 1, borderColor: colors.borderSoft },
  bubbleText: { fontFamily: fonts.bodyRegular, fontSize: 15, lineHeight: 21, color: colors.textPrimary },
  bubbleTextMine: { color: "#F9F6E9" },
  composer: {
    flexDirection: "row",
    alignItems: "flex-end",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
    gap: spacing.sm,
  },
  input: {
    flex: 1,
    minHeight: 42,
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
  sendBtn: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  sheetBackdrop: {
    flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: colors.background,
    borderTopLeftRadius: 20, borderTopRightRadius: 20,
    padding: spacing.lg,
    maxHeight: "80%",
  },
  sheetTitle: {
    fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary,
    marginBottom: spacing.md,
  },
  renameLabel: {
    fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 1.2, color: colors.textMuted,
    marginTop: 4, marginBottom: 6, textTransform: "uppercase",
  },
  renameInput: {
    backgroundColor: colors.surface,
    borderRadius: radius.md, borderWidth: 1, borderColor: colors.borderSoft,
    paddingHorizontal: spacing.md, paddingVertical: 10,
    fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary,
  },
  renameBtn: {
    alignSelf: "flex-end", marginTop: 6, paddingHorizontal: 14, paddingVertical: 8,
    backgroundColor: colors.primary, borderRadius: radius.round,
  },
  renameBtnText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 12 },
  memberRow: {
    flexDirection: "row", alignItems: "center", gap: spacing.sm,
    paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.borderSoft,
  },
  memberName: { flex: 1, fontFamily: fonts.uiSemi, color: colors.textPrimary, fontSize: 14 },
  memberYou: { fontFamily: fonts.bodyRegular, fontSize: 11, color: colors.gold },
  leaveBtn: {
    marginTop: spacing.lg, paddingVertical: 12, borderRadius: radius.md,
    backgroundColor: colors.background, borderWidth: 1, borderColor: colors.liturgical.red,
    alignItems: "center",
  },
  leaveBtnText: { fontFamily: fonts.uiSemi, color: colors.liturgical.red },
  closeSheet: {
    marginTop: spacing.sm, alignSelf: "center", padding: 8,
  },
  closeSheetText: { fontFamily: fonts.uiMedium, color: colors.textMuted, fontSize: 12 },
});

// --------------------------------------------------------------------------
// Group members sheet — only mounted when viewing a group thread. Lets the
// caller rename, kick (creator only), or leave the group. We keep the
// network calls scoped here so the parent screen stays compact.
function GroupMembersSheet({
  thread, meId, onClose, onRenamed, onLeft,
}: {
  thread: CommunityDMThread;
  meId: string;
  onClose: () => void;
  onRenamed: (t: CommunityDMThread) => void;
  onLeft: () => void;
}) {
  const [name, setName] = useState<string>(thread.name || "");
  const [busy, setBusy] = useState(false);
  const isCreator = thread.created_by === meId;

  const rename = async () => {
    setBusy(true);
    try {
      const fresh = await dmRenameGroup(thread.thread_id, name.trim() || null);
      onRenamed(fresh);
    } catch (e: any) {
      Alert.alert("Couldn't rename", e?.message || "Try again later.");
    } finally {
      setBusy(false);
    }
  };

  const leave = () => {
    Alert.alert(
      "Leave group?",
      "You'll need to be re-added by a member to rejoin.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Leave", style: "destructive", onPress: async () => {
            try {
              await dmRemoveGroupMember(thread.thread_id, meId);
              onLeft();
            } catch (e: any) {
              Alert.alert("Couldn't leave", e?.message || "Try again later.");
            }
          },
        },
      ],
    );
  };

  const kick = (uid: string, displayName: string) => {
    Alert.alert(
      `Remove ${displayName}?`,
      "They will no longer see this conversation.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Remove", style: "destructive", onPress: async () => {
            try {
              await dmRemoveGroupMember(thread.thread_id, uid);
              const fresh = await api<{ thread: CommunityDMThread }>(
                `/community/dm/threads/${thread.thread_id}/messages`);
              onRenamed(fresh.thread);
            } catch (e: any) {
              Alert.alert("Couldn't remove", e?.message || "Try again later.");
            }
          },
        },
      ],
    );
  };

  return (
    <Modal animationType="slide" transparent visible onRequestClose={onClose}>
      <Pressable style={styles.sheetBackdrop} onPress={onClose} testID="dm-group-sheet-backdrop">
        <Pressable style={styles.sheet} onPress={() => { /* swallow */ }}>
          <Text style={styles.sheetTitle}>Group info</Text>

          <Text style={styles.renameLabel}>Name</Text>
          <TextInput
            testID="dm-group-rename-input"
            value={name}
            onChangeText={setName}
            placeholder={thread.auto_name || "Group chat"}
            placeholderTextColor={colors.textMuted}
            style={styles.renameInput}
            maxLength={60}
          />
          <Pressable
            testID="dm-group-rename-save"
            onPress={rename}
            disabled={busy}
            style={({ pressed }) => [styles.renameBtn, (busy || pressed) && { opacity: 0.7 }]}
          >
            <Text style={styles.renameBtnText}>Save name</Text>
          </Pressable>

          <Text style={[styles.renameLabel, { marginTop: spacing.md }]}>
            Members ({thread.members?.length ?? 0})
          </Text>
          <ScrollView style={{ maxHeight: 260 }}>
            {(thread.members || []).map((u) => (
              <View key={u.user_id} style={styles.memberRow}>
                <Avatar name={u.name} picture={u.picture ?? null} size={32} />
                <Text style={styles.memberName} numberOfLines={1}>{u.name}</Text>
                {u.user_id === meId ? (
                  <Text style={styles.memberYou}>You</Text>
                ) : isCreator ? (
                  <Pressable
                    testID={`dm-group-kick-${u.user_id}`}
                    onPress={() => kick(u.user_id, u.name)}
                    hitSlop={8}
                  >
                    <Ionicons name="remove-circle-outline" size={20} color={colors.liturgical.red} />
                  </Pressable>
                ) : null}
              </View>
            ))}
          </ScrollView>

          <Pressable
            testID="dm-group-leave"
            onPress={leave}
            style={({ pressed }) => [styles.leaveBtn, pressed && { opacity: 0.7 }]}
          >
            <Text style={styles.leaveBtnText}>Leave group</Text>
          </Pressable>

          <Pressable onPress={onClose} style={styles.closeSheet} testID="dm-group-close">
            <Text style={styles.closeSheetText}>Close</Text>
          </Pressable>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

import React, { useCallback, useEffect, useRef, useState } from "react";
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

import { api, CommunityDMMessage, CommunityDMThread } from "@/src/api";
import Avatar from "@/src/components/Avatar";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { timeOfDay } from "@/src/utils/time-ago";

export default function DMThreadScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const params = useLocalSearchParams<{ thread_id?: string; other_id?: string }>();
  const incomingThread = typeof params.thread_id === "string" ? params.thread_id : "";
  const incomingOther = typeof params.other_id === "string" ? params.other_id : "";

  const [thread, setThread] = useState<CommunityDMThread | null>(null);
  const [messages, setMessages] = useState<CommunityDMMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<ScrollView | null>(null);

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
      }
    } catch (e: any) {
      Alert.alert("Couldn't open conversation", e?.message || "Please try again.");
      router.back();
    } finally {
      setLoading(false);
    }
  }, [incomingThread, incomingOther, router]);

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
        <Pressable
          onPress={() => thread?.other && router.push({ pathname: "/community/user/[id]", params: { id: thread.other.user_id } })}
          style={styles.headerMid}
          hitSlop={6}
        >
          <Avatar name={thread?.other?.name} picture={thread?.other?.picture ?? null} size={32} />
          <Text style={styles.headerTitle} numberOfLines={1}>{thread?.other?.name || "Conversation"}</Text>
        </Pressable>
        <View style={{ width: 26 }} />
      </View>

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
                return (
                  <View key={m.message_id}>
                    {showTime ? (
                      <Text style={styles.timeStamp}>{timeOfDay(m.created_at)}</Text>
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
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary, maxWidth: 180 },
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
});

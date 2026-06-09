import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Linking,
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
import { Stack, useRouter } from "expo-router";

import {
  FAQItem,
  SupportInfoResponse,
  getSupportInfo,
  submitSupportTicket,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const PUBLIC_SUPPORT_URL = `${process.env.EXPO_PUBLIC_BACKEND_URL ?? ""}/api/legal/support`;

// Mirrors the SupportContactRequest.category enum on the backend (free-form
// but we present a fixed picker so tickets get triaged predictably).
const CATEGORIES: { id: string; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { id: "bug", label: "Bug", icon: "bug-outline" },
  { id: "account", label: "Account", icon: "person-circle-outline" },
  { id: "suggestion", label: "Suggestion", icon: "bulb-outline" },
  { id: "other", label: "Other", icon: "help-circle-outline" },
];

export default function SupportScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [info, setInfo] = useState<SupportInfoResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Contact form state
  const [category, setCategory] = useState<string>("bug");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState(user?.email ?? "");
  const [sending, setSending] = useState(false);
  const [sentMsg, setSentMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await getSupportInfo();
      setInfo(r);
    } catch {
      // ignore — we still show the form with the hardcoded fallback email.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const supportEmail = info?.support_email ?? "philipwils13@gmail.com";

  const canSend = useMemo(
    () => subject.trim().length >= 2 && message.trim().length >= 4 && !sending,
    [subject, message, sending],
  );

  const openMail = () => {
    Linking.openURL(`mailto:${supportEmail}?subject=Sanctus%20support`).catch(() => {
      Alert.alert("No mail app", `Please email ${supportEmail} from your preferred mail client.`);
    });
  };

  const send = async () => {
    if (!canSend) return;
    setSending(true);
    setSentMsg(null);
    try {
      const r = await submitSupportTicket({
        subject: subject.trim(),
        message: message.trim(),
        category,
        email: email.trim() || undefined,
      });
      setSentMsg(r.message);
      setSubject("");
      setMessage("");
    } catch (e: any) {
      Alert.alert("Couldn't send", e?.message || "Please try again, or email directly.");
    } finally {
      setSending(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="support-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="support-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Help &amp; Support</Text>
        <Pressable
          onPress={() => Linking.openURL(PUBLIC_SUPPORT_URL).catch(() => {})}
          hitSlop={10}
          testID="support-open-web"
          accessibilityLabel="Open support page on the web"
        >
          <Ionicons name="open-outline" size={22} color={colors.primary} />
        </Pressable>
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={20}
      >
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <Text style={styles.brand}>SANCTUS</Text>
          <Text style={styles.title}>How can we help?</Text>
          <Text style={styles.subtitle}>
            Email us directly, or fill in the form below — we usually reply within 48 hours.
          </Text>

          <Pressable
            onPress={openMail}
            style={({ pressed }) => [styles.emailCta, pressed && { opacity: 0.7 }]}
            testID="support-email-button"
          >
            <Ionicons name="mail-outline" size={18} color={colors.gold} />
            <Text style={styles.emailCtaText} numberOfLines={1}>
              {supportEmail}
            </Text>
          </Pressable>

          {/* Contact form */}
          <View style={styles.formCard}>
            <Text style={styles.formTitle}>Send us a message</Text>

            <Text style={styles.label}>Category</Text>
            <View style={styles.categoryRow}>
              {CATEGORIES.map((c) => {
                const active = c.id === category;
                return (
                  <Pressable
                    key={c.id}
                    onPress={() => setCategory(c.id)}
                    testID={`support-category-${c.id}`}
                    style={({ pressed }) => [
                      styles.categoryChip,
                      active && styles.categoryChipOn,
                      pressed && { opacity: 0.8 },
                    ]}
                  >
                    <Ionicons
                      name={c.icon}
                      size={14}
                      color={active ? colors.gold : colors.primary}
                    />
                    <Text
                      style={[
                        styles.categoryText,
                        active && styles.categoryTextOn,
                      ]}
                    >
                      {c.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            <Text style={styles.label}>Email (so we can reply)</Text>
            <TextInput
              testID="support-email-input"
              value={email}
              onChangeText={setEmail}
              placeholder="you@example.com"
              placeholderTextColor={colors.textMuted}
              style={styles.input}
              keyboardType="email-address"
              autoCorrect={false}
              autoCapitalize="none"
            />

            <Text style={styles.label}>Subject</Text>
            <TextInput
              testID="support-subject-input"
              value={subject}
              onChangeText={setSubject}
              placeholder="Short summary"
              placeholderTextColor={colors.textMuted}
              style={styles.input}
              maxLength={140}
            />

            <Text style={styles.label}>Message</Text>
            <TextInput
              testID="support-message-input"
              value={message}
              onChangeText={setMessage}
              placeholder="Tell us what's going on…"
              placeholderTextColor={colors.textMuted}
              style={[styles.input, styles.inputMultiline]}
              multiline
              maxLength={4000}
              textAlignVertical="top"
            />

            <Pressable
              onPress={send}
              disabled={!canSend}
              testID="support-send"
              style={({ pressed }) => [
                styles.sendBtn,
                !canSend && { opacity: 0.4 },
                pressed && { opacity: 0.7 },
              ]}
            >
              {sending ? (
                <ActivityIndicator size="small" color={colors.gold} />
              ) : (
                <>
                  <Ionicons name="send" size={16} color={colors.gold} />
                  <Text style={styles.sendText}>Send</Text>
                </>
              )}
            </Pressable>

            {sentMsg ? (
              <View style={styles.sentBox} testID="support-sent-confirm">
                <Ionicons name="checkmark-circle" size={18} color={colors.liturgical.green} />
                <Text style={styles.sentText}>{sentMsg}</Text>
              </View>
            ) : null}
          </View>

          {/* FAQ */}
          {loading ? (
            <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.lg }} />
          ) : info ? (
            <>
              <Text style={styles.section}>Frequently asked</Text>
              {info.faq.map((item: FAQItem, i: number) => (
                <View key={i} style={styles.faqCard} testID={`support-faq-${i}`}>
                  <Text style={styles.faqQ}>{item.q}</Text>
                  <Text style={styles.faqA}>{item.a}</Text>
                </View>
              ))}
            </>
          ) : null}

          <Text style={styles.footer}>Ad maiorem Dei gloriam.</Text>
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
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
  },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  scroll: { padding: spacing.lg },
  brand: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 3.5,
    color: colors.gold,
    textAlign: "center",
    marginTop: spacing.md,
  },
  title: {
    fontFamily: fonts.headingBold,
    fontSize: 26,
    color: colors.textPrimary,
    textAlign: "center",
    marginTop: spacing.xs,
  },
  subtitle: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textMuted,
    textAlign: "center",
    marginTop: spacing.xs,
    marginBottom: spacing.lg,
  },
  emailCta: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: spacing.lg,
    paddingVertical: 14,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
    marginBottom: spacing.lg,
    ...shadow.card,
  },
  emailCtaText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.gold },
  formCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.lg,
    ...shadow.card,
  },
  formTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  label: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.4,
    color: colors.gold,
    textTransform: "uppercase",
    marginTop: spacing.md,
    marginBottom: 6,
  },
  categoryRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.xs,
  },
  categoryChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: 8,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.background,
  },
  categoryChipOn: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  categoryText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.primary },
  categoryTextOn: { color: colors.gold },
  input: {
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textPrimary,
  },
  inputMultiline: { minHeight: 120, paddingTop: 12 },
  sendBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    marginTop: spacing.lg,
    paddingVertical: 12,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
  },
  sendText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold },
  sentBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: colors.background,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.liturgical.green,
    padding: spacing.sm,
    marginTop: spacing.md,
  },
  sentText: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textPrimary },
  section: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 2.5,
    color: colors.gold,
    textTransform: "uppercase",
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
  },
  faqCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.md,
    marginBottom: spacing.sm,
    ...shadow.card,
  },
  faqQ: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary, marginBottom: 4 },
  faqA: { fontFamily: fonts.bodyRegular, fontSize: 13, lineHeight: 20, color: colors.textSecondary },
  footer: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textMuted,
    textAlign: "center",
    marginTop: spacing.lg,
  },
});

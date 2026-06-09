import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { getPrivacyPolicy, PrivacyPolicyResponse } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";

// The public web version of this page lives at /api/legal/privacy — both
// surfaces are sourced from the same backend payload so they stay in sync.
const PUBLIC_PRIVACY_URL = `${process.env.EXPO_PUBLIC_BACKEND_URL ?? ""}/api/legal/privacy`;

export default function PrivacyScreen() {
  const router = useRouter();
  const [data, setData] = useState<PrivacyPolicyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await getPrivacyPolicy();
      setData(r);
    } catch (e: any) {
      setError(e?.message || "Couldn't load the privacy policy.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="privacy-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="privacy-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Privacy</Text>
        <Pressable
          onPress={() => Linking.openURL(PUBLIC_PRIVACY_URL).catch(() => {})}
          hitSlop={10}
          testID="privacy-open-web"
          accessibilityLabel="Open privacy policy on the web"
        >
          <Ionicons name="open-outline" size={22} color={colors.primary} />
        </Pressable>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
        </View>
      ) : error ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable
            onPress={load}
            style={({ pressed }) => [styles.retry, pressed && { opacity: 0.7 }]}
            testID="privacy-retry"
          >
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      ) : data ? (
        <ScrollView contentContainerStyle={styles.scroll}>
          <Text style={styles.brand}>SANCTUS</Text>
          <Text style={styles.title}>Privacy Policy</Text>
          <Text style={styles.updated} testID="privacy-updated">Last updated {data.last_updated}</Text>
          {data.sections.map((s, i) => (
            <View key={`${i}-${s.title}`} style={styles.section} testID={`privacy-section-${i}`}>
              <Text style={styles.sectionTitle}>{s.title}</Text>
              <Text style={styles.sectionBody}>{s.body}</Text>
            </View>
          ))}
          <Pressable
            onPress={() => Linking.openURL(`mailto:${data.support_email}`).catch(() => {})}
            style={({ pressed }) => [styles.cta, pressed && { opacity: 0.7 }]}
            testID="privacy-email-link"
          >
            <Ionicons name="mail-outline" size={16} color={colors.gold} />
            <Text style={styles.ctaText}>Email {data.support_email}</Text>
          </Pressable>
          <Text style={styles.footer}>Ad maiorem Dei gloriam.</Text>
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      ) : null}
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
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.lg, gap: spacing.md },
  errorText: { fontFamily: fonts.bodyRegular, color: colors.textSecondary, textAlign: "center" },
  retry: {
    paddingHorizontal: spacing.lg,
    paddingVertical: 10,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
  },
  retryText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 13 },
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
    fontSize: 28,
    color: colors.textPrimary,
    textAlign: "center",
    marginTop: spacing.xs,
  },
  updated: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textMuted,
    textAlign: "center",
    marginTop: spacing.xs,
    marginBottom: spacing.lg,
  },
  section: { marginBottom: spacing.lg },
  sectionTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  sectionBody: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    lineHeight: 22,
    color: colors.textSecondary,
  },
  cta: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: spacing.lg,
    paddingVertical: 12,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
    marginTop: spacing.md,
  },
  ctaText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold },
  footer: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textMuted,
    textAlign: "center",
    marginTop: spacing.lg,
  },
});

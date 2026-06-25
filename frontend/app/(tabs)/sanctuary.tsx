import React from "react";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

export default function SanctuaryHub() {
  return (
    <SafeAreaView style={styles.screen} edges={["top"]}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.eyebrow}>SANCTUARY</Text>
          <Text style={styles.title}>A quiet place to dwell.</Text>
          <Ornament />
          <Text style={styles.subtitle}>
            Step away from the noise. Pray, breathe, or study with sacred music in the background.
          </Text>
        </View>

        <Pressable
          testID="sanctuary-meditation-card"
          onPress={() => router.push("/sanctuary/meditation")}
          style={({ pressed }) => [styles.card, styles.meditationCard, pressed && styles.pressed]}
        >
          <View style={styles.cardHeader}>
            <Ionicons name="flower-outline" size={28} color={colors.gold} />
            <View style={styles.tag}>
              <Text style={styles.tagText}>PIANO · HARP · CHANT</Text>
            </View>
          </View>
          <Text style={styles.cardTitle}>Meditation</Text>
          <Text style={styles.cardBody}>
            Soothing piano and harp, Gregorian chant, and 4&ndash;7&ndash;8 breathing. A timer rings
            you back gently when it&apos;s over.
          </Text>
          <View style={styles.cardFooter}>
            <Text style={styles.cardFooterText}>Enter the silence</Text>
            <Ionicons name="arrow-forward" size={16} color={colors.gold} />
          </View>
        </Pressable>

        <Pressable
          testID="sanctuary-study-card"
          onPress={() => router.push("/sanctuary/study")}
          style={({ pressed }) => [styles.card, styles.studyCard, pressed && styles.pressed]}
        >
          <View style={styles.cardHeader}>
            <Ionicons name="book-outline" size={28} color={colors.gold} />
            <View style={styles.tag}>
              <Text style={styles.tagText}>CATHOLIC LOFI</Text>
            </View>
          </View>
          <Text style={styles.cardTitle}>Study</Text>
          <Text style={styles.cardBody}>
            Soft Catholic lofi while you read, write, or work. A Pomodoro timer keeps you focused
            without burning you out.
          </Text>
          <View style={styles.cardFooter}>
            <Text style={styles.cardFooterText}>Begin a session</Text>
            <Ionicons name="arrow-forward" size={16} color={colors.gold} />
          </View>
        </Pressable>

        <View style={styles.footer}>
          <Ionicons name="musical-notes-outline" size={14} color={colors.textMuted} />
          <Text style={styles.footerText}>
            Music is streamed from public-domain archives and creators&apos; channels — please
            support them when you can.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  scroll: { padding: spacing.lg, paddingBottom: spacing.xxl },
  header: { alignItems: "center", marginBottom: spacing.xl },
  eyebrow: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.gold,
    letterSpacing: 2.5,
  },
  title: {
    fontFamily: fonts.headingBold,
    fontSize: 28,
    color: colors.textPrimary,
    textAlign: "center",
    marginTop: 8,
  },
  subtitle: {
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textSecondary,
    textAlign: "center",
    lineHeight: 22,
    marginTop: spacing.md,
    paddingHorizontal: spacing.md,
  },
  card: {
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.lg,
    ...shadow.card,
  },
  meditationCard: {
    backgroundColor: "#2B2A4A",
  },
  studyCard: {
    backgroundColor: "#1F3A52",
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.md,
  },
  tag: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.gold,
  },
  tagText: {
    fontFamily: fonts.uiSemi,
    fontSize: 9,
    color: colors.gold,
    letterSpacing: 1.5,
  },
  cardTitle: {
    fontFamily: fonts.headingBold,
    fontSize: 32,
    color: colors.gold,
    marginBottom: spacing.sm,
  },
  cardBody: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: "#E8E4D8",
    lineHeight: 22,
  },
  cardFooter: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginTop: spacing.lg,
  },
  cardFooterText: {
    fontFamily: fonts.uiSemi,
    fontSize: 13,
    color: colors.gold,
    letterSpacing: 0.5,
  },
  footer: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 6,
    marginTop: spacing.md,
    paddingHorizontal: spacing.sm,
  },
  footerText: {
    flex: 1,
    fontFamily: fonts.bodyRegular,
    fontSize: 11,
    color: colors.textMuted,
    lineHeight: 16,
  },
  pressed: { opacity: 0.85 },
});

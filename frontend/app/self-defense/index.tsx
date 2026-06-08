import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useFocusEffect, useRouter } from "expo-router";

import { api, SDDiscipline, SDPatron, SDProgress } from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type DisciplineWithPatron = SDDiscipline & { patron: SDPatron };

type DisciplineListResponse = {
  items: DisciplineWithPatron[];
  disclaimer: string;
};

type DisclaimerResponse = {
  text: string;
  acknowledged: boolean;
  acknowledged_at?: string | null;
};

type ProgressListResponse = {
  items: Array<{
    discipline_id: string;
    discipline_name: string;
    icon: string;
    progress: SDProgress;
    patron_name: string | null;
  }>;
};

export default function SelfDefenseIndexScreen() {
  const router = useRouter();
  const [disciplines, setDisciplines] = useState<DisciplineWithPatron[]>([]);
  const [disclaimerText, setDisclaimerText] = useState("");
  const [progressMap, setProgressMap] = useState<Record<string, SDProgress>>({});
  const [loading, setLoading] = useState(true);
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const [ackInFlight, setAckInFlight] = useState(false);
  const [pendingNav, setPendingNav] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [list, disc, prog] = await Promise.all([
        api<DisciplineListResponse>("/self-defense/disciplines"),
        api<DisclaimerResponse>("/self-defense/disclaimer"),
        api<ProgressListResponse>("/self-defense/progress"),
      ]);
      setDisciplines(list.items || []);
      setDisclaimerText(list.disclaimer || disc.text || "");
      const map: Record<string, SDProgress> = {};
      for (const item of prog.items || []) {
        map[item.discipline_id] = item.progress;
      }
      setProgressMap(map);
      // Show disclaimer modal if not yet acknowledged
      if (!disc.acknowledged) {
        setShowDisclaimer(true);
      }
    } catch (e: any) {
      Alert.alert("Couldn't load self-defense", e?.message || "Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  const acknowledge = async () => {
    setAckInFlight(true);
    try {
      await api("/self-defense/disclaimer/acknowledge", { method: "POST" });
      setShowDisclaimer(false);
      if (pendingNav) {
        const target = pendingNav;
        setPendingNav(null);
        router.push({ pathname: "/self-defense/[discipline]", params: { discipline: target } });
      }
    } catch (e: any) {
      Alert.alert("Couldn't acknowledge", e?.message || "Please try again.");
    } finally {
      setAckInFlight(false);
    }
  };

  const openDiscipline = (id: string) => {
    if (showDisclaimer) {
      setPendingNav(id);
      return;
    }
    router.push({ pathname: "/self-defense/[discipline]", params: { discipline: id } });
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safe}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="sd-index-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="sd-index-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Self-Defense</Text>
        <Pressable onPress={() => setShowDisclaimer(true)} hitSlop={12} testID="sd-index-disclaimer">
          <Ionicons name="shield-outline" size={22} color={colors.primary} />
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.intro}>
          <Text style={styles.eyebrow}>MILES CHRISTI</Text>
          <Text style={styles.introTitle}>Train the body. Order the soul.</Text>
          <Text style={styles.introBody}>
            Six combat disciplines, each entrusted to a Catholic patron — from St. Sebastian for boxing
            to Bl. Justo Takayama Ukon for the way of the sword. Choose one to begin.
          </Text>
        </View>

        {disciplines.map((d) => {
          const prog = progressMap[d.id];
          const completed = prog?.sessions_completed ?? 0;
          const level = prog?.current_level ?? "beginner";
          return (
            <Pressable
              key={d.id}
              testID={`sd-card-${d.id}`}
              onPress={() => openDiscipline(d.id)}
              style={({ pressed }) => [styles.card, pressed && styles.pressed]}
            >
              <View style={styles.cardTop}>
                <View style={styles.iconWrap}>
                  <Ionicons name={(d.icon as any) || "ribbon-outline"} size={22} color={colors.gold} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.tradition}>{d.tradition.toUpperCase()}</Text>
                  <Text style={styles.name}>{d.name}</Text>
                  <Text style={styles.tagline}>{d.tagline}</Text>
                </View>
                <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
              </View>

              {d.patron ? (
                <View style={styles.patronRow}>
                  <Ionicons name={(d.patron.icon as any) || "ribbon-outline"} size={13} color={colors.gold} />
                  <Text style={styles.patronLabel}>PATRON</Text>
                  <Text style={styles.patronName} numberOfLines={1}>
                    {d.patron.name}
                  </Text>
                </View>
              ) : null}

              <View style={styles.statsRow}>
                <View style={styles.levelBadge}>
                  <Text style={styles.levelBadgeText}>{level.toUpperCase()}</Text>
                </View>
                <Text style={styles.statsText}>
                  <Text style={styles.statsNum}>{completed}</Text>
                  <Text style={styles.statsLabel}> completed</Text>
                </Text>
              </View>
            </Pressable>
          );
        })}

        <Pressable
          testID="sd-show-disclaimer"
          onPress={() => setShowDisclaimer(true)}
          style={({ pressed }) => [styles.disclaimerLink, pressed && styles.pressed]}
        >
          <Ionicons name="information-circle-outline" size={14} color={colors.primary} />
          <Text style={styles.disclaimerLinkText}>Review safety disclaimer</Text>
        </Pressable>

        <View style={{ height: spacing.xxl }} />
      </ScrollView>

      {/* Disclaimer modal */}
      <Modal
        visible={showDisclaimer}
        animationType="fade"
        transparent
        onRequestClose={() => {
          // Only allow dismissing without acknowledging if already acknowledged before
          if (pendingNav === null) setShowDisclaimer(false);
        }}
      >
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard} testID="sd-disclaimer-modal">
            <View style={styles.modalIconRow}>
              <Ionicons name="shield-checkmark-outline" size={28} color={colors.gold} />
            </View>
            <Text style={styles.modalTitle}>Safety Acknowledgment</Text>
            <ScrollView style={styles.modalBodyScroll} contentContainerStyle={{ paddingBottom: 4 }}>
              <Text style={styles.modalBody}>{disclaimerText}</Text>
            </ScrollView>
            <Pressable
              testID="sd-disclaimer-ack"
              onPress={acknowledge}
              disabled={ackInFlight}
              style={({ pressed }) => [styles.modalPrimary, ackInFlight && { opacity: 0.6 }, pressed && styles.pressed]}
            >
              {ackInFlight ? (
                <ActivityIndicator color={colors.gold} />
              ) : (
                <>
                  <Ionicons name="checkmark" size={16} color={colors.gold} />
                  <Text style={styles.modalPrimaryText}>I acknowledge & proceed</Text>
                </>
              )}
            </Pressable>
            <Pressable
              testID="sd-disclaimer-cancel"
              onPress={() => {
                setShowDisclaimer(false);
                setPendingNav(null);
                if (!disclaimerText || disciplines.length === 0) {
                  router.back();
                }
              }}
              style={({ pressed }) => [styles.modalSecondary, pressed && styles.pressed]}
            >
              <Text style={styles.modalSecondaryText}>Not now</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  headerTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
    flex: 1,
    textAlign: "center",
    marginHorizontal: spacing.sm,
  },
  scroll: { padding: spacing.lg },
  intro: { marginBottom: spacing.lg },
  eyebrow: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 2.5,
    color: colors.gold,
  },
  introTitle: {
    fontFamily: fonts.headingBold,
    fontSize: 26,
    color: colors.textPrimary,
    marginTop: 6,
  },
  introBody: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
    marginTop: spacing.sm,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  cardTop: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  tradition: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 2,
    color: colors.gold,
  },
  name: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
    marginTop: 2,
  },
  tagline: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  patronRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginTop: spacing.sm,
    paddingTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.borderSoft,
  },
  patronLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 9,
    letterSpacing: 1.8,
    color: colors.gold,
  },
  patronName: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.textPrimary,
    flex: 1,
  },
  statsRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  levelBadge: {
    backgroundColor: colors.primary,
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: radius.round,
  },
  levelBadgeText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 10,
    letterSpacing: 1.4,
  },
  statsText: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textPrimary },
  statsNum: { fontFamily: fonts.headingBold, fontSize: 16, color: colors.textPrimary },
  statsLabel: { color: colors.textSecondary },
  disclaimerLink: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: spacing.md,
  },
  disclaimerLinkText: {
    fontFamily: fonts.uiMedium,
    fontSize: 12,
    color: colors.primary,
    textDecorationLine: "underline",
  },
  pressed: { opacity: 0.7 },
  // Modal
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(28,40,65,0.65)",
    alignItems: "center",
    justifyContent: "center",
    padding: spacing.lg,
  },
  modalCard: {
    width: "100%",
    maxWidth: 480,
    maxHeight: "85%",
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.gold,
    ...shadow.card,
  },
  modalIconRow: { alignItems: "center", marginBottom: spacing.sm },
  modalTitle: {
    fontFamily: fonts.headingBold,
    fontSize: 20,
    color: colors.textPrimary,
    textAlign: "center",
    marginBottom: spacing.md,
  },
  modalBodyScroll: { maxHeight: 280, marginBottom: spacing.md },
  modalBody: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textPrimary,
    lineHeight: 22,
  },
  modalPrimary: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: colors.primary,
    paddingVertical: 14,
    borderRadius: radius.round,
    marginTop: spacing.sm,
  },
  modalPrimaryText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 14 },
  modalSecondary: {
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 12,
    marginTop: 4,
  },
  modalSecondaryText: {
    fontFamily: fonts.uiMedium,
    fontSize: 13,
    color: colors.textSecondary,
  },
});

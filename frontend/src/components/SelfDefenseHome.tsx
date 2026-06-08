import React, { useCallback, useEffect, useState } from "react";
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
import { useFocusEffect, useRouter } from "expo-router";

import { api, SDDiscipline, SDSession } from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { timeAgo } from "@/src/utils/time-ago";

type DisciplinesResponse = { items: SDDiscipline[]; disclaimer: string };
type DisclaimerResponse = { text: string; acknowledged: boolean; acknowledged_at?: string };
type ProgressResponse = {
  items: Array<{
    discipline_id: string;
    discipline_name: string;
    icon: string;
    patron_name?: string;
    progress: {
      current_level: "beginner" | "intermediate" | "advanced";
      sessions_completed: number;
      sessions_generated?: number;
      last_session_at?: string | null;
    };
  }>;
};

export default function SelfDefenseHome() {
  const router = useRouter();
  const [disciplines, setDisciplines] = useState<SDDiscipline[]>([]);
  const [progressMap, setProgressMap] = useState<Record<string, ProgressResponse["items"][number]["progress"]>>({});
  const [recent, setRecent] = useState<SDSession[]>([]);
  const [disclaimer, setDisclaimer] = useState<DisclaimerResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const [acking, setAcking] = useState(false);

  const load = useCallback(async () => {
    try {
      const [d, p, r, dis] = await Promise.all([
        api<DisciplinesResponse>("/self-defense/disciplines"),
        api<ProgressResponse>("/self-defense/progress"),
        api<{ items: SDSession[] }>("/self-defense/sessions?limit=10"),
        api<DisclaimerResponse>("/self-defense/disclaimer"),
      ]);
      setDisciplines(d.items || []);
      const map: Record<string, any> = {};
      for (const it of p.items || []) map[it.discipline_id] = it.progress;
      setProgressMap(map);
      setRecent(r.items || []);
      setDisclaimer(dis);
      if (!dis.acknowledged) setShowDisclaimer(true);
    } catch (e) {
      console.warn("self-defense load failed", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  const acknowledge = async () => {
    setAcking(true);
    try {
      await api("/self-defense/disclaimer/acknowledge", { method: "POST" });
      setDisclaimer((d) => d ? { ...d, acknowledged: true } : d);
      setShowDisclaimer(false);
    } catch (e: any) {
      Alert.alert("Couldn't save acknowledgement", e?.message || "Please try again.");
    } finally {
      setAcking(false);
    }
  };

  const openDiscipline = (id: string) => {
    if (!disclaimer?.acknowledged) {
      setShowDisclaimer(true);
      return;
    }
    router.push({ pathname: "/self-defense/[discipline]", params: { discipline: id } });
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.gold} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1 }}>
      <ScrollView contentContainerStyle={styles.scroll} testID="self-defense-home">
        <View style={styles.intro}>
          <Ionicons name="shield-half-outline" size={18} color={colors.gold} />
          <Text style={styles.introText}>
            Train protection of self, family, and neighbor — under the patronage of the saints.
          </Text>
        </View>

        {!disclaimer?.acknowledged ? (
          <Pressable
            onPress={() => setShowDisclaimer(true)}
            testID="sd-disclaimer-banner"
            style={({ pressed }) => [styles.disclaimerBanner, pressed && styles.pressed]}
          >
            <Ionicons name="alert-circle-outline" size={18} color={colors.liturgical.red} />
            <Text style={styles.disclaimerBannerText}>Review the safety disclaimer to begin</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.liturgical.red} />
          </Pressable>
        ) : null}

        <Text style={styles.sectionTitle}>Disciplines</Text>
        <View style={styles.grid}>
          {disciplines.map((d) => {
            const prog = progressMap[d.id];
            return (
              <Pressable
                key={d.id}
                onPress={() => openDiscipline(d.id)}
                testID={`sd-discipline-${d.id}`}
                style={({ pressed }) => [styles.card, pressed && styles.pressed]}
              >
                <View style={styles.cardHead}>
                  <Ionicons name={d.icon as any} size={22} color={colors.gold} />
                  <View style={styles.levelPill}>
                    <Text style={styles.levelPillText}>
                      {(prog?.current_level || "beginner").toUpperCase()}
                    </Text>
                  </View>
                </View>
                <Text style={styles.cardTitle}>{d.name}</Text>
                <Text style={styles.cardTradition}>{d.tradition}</Text>
                <Text style={styles.cardTagline} numberOfLines={2}>{d.tagline}</Text>
                <View style={styles.cardFooter}>
                  <View style={styles.patronRow}>
                    <Ionicons name={d.patron?.icon as any || "ribbon-outline"} size={12} color={colors.primary} />
                    <Text style={styles.patronText} numberOfLines={1}>
                      {d.patron?.name || "—"}
                    </Text>
                  </View>
                  <Text style={styles.progressText}>
                    {prog?.sessions_completed ?? 0} done
                  </Text>
                </View>
              </Pressable>
            );
          })}
        </View>

        {recent.length > 0 ? (
          <>
            <Text style={styles.sectionTitle}>Recent sessions</Text>
            {recent.slice(0, 6).map((s) => (
              <Pressable
                key={s.session_id}
                onPress={() => router.push({ pathname: "/self-defense/session/[id]", params: { id: s.session_id } })}
                testID={`sd-recent-${s.session_id}`}
                style={({ pressed }) => [styles.recentRow, pressed && styles.pressed]}
              >
                <View style={{ flex: 1 }}>
                  <Text style={styles.recentTitle} numberOfLines={1}>{s.plan?.title || "Session"}</Text>
                  <Text style={styles.recentMeta}>
                    {s.discipline_name} · {timeAgo(s.generated_at)}
                    {s.completed_at ? " · ✓ completed" : ""}
                    {s.source === "redo" ? " · redo" : ""}
                  </Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
              </Pressable>
            ))}
          </>
        ) : null}

        <View style={{ height: spacing.xxl }} />
      </ScrollView>

      {/* Disclaimer modal */}
      <Modal
        transparent
        visible={showDisclaimer}
        animationType="fade"
        onRequestClose={() => disclaimer?.acknowledged && setShowDisclaimer(false)}
      >
        <View style={styles.modalScrim}>
          <View style={styles.disclaimerSheet}>
            <View style={styles.disclaimerHeader}>
              <Ionicons name="alert-circle" size={22} color={colors.liturgical.red} />
              <Text style={styles.disclaimerTitle}>Safety first</Text>
            </View>
            <ScrollView style={{ maxHeight: 320 }} contentContainerStyle={{ paddingBottom: spacing.md }}>
              <Text style={styles.disclaimerBody}>{disclaimer?.text}</Text>
            </ScrollView>
            <View style={styles.disclaimerActions}>
              {disclaimer?.acknowledged ? (
                <Pressable
                  onPress={() => setShowDisclaimer(false)}
                  style={({ pressed }) => [styles.ackBtn, pressed && styles.pressed]}
                >
                  <Text style={styles.ackBtnText}>Close</Text>
                </Pressable>
              ) : (
                <Pressable
                  onPress={acknowledge}
                  disabled={acking}
                  testID="sd-disclaimer-acknowledge"
                  style={({ pressed }) => [styles.ackBtn, pressed && styles.pressed, acking && { opacity: 0.6 }]}
                >
                  <Text style={styles.ackBtnText}>{acking ? "Saving…" : "I understand & accept"}</Text>
                </Pressable>
              )}
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl },
  scroll: { paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  intro: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  introText: {
    flex: 1,
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 19,
  },
  disclaimerBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: "#FCE9E9",
    borderRadius: radius.md,
    padding: spacing.md,
    marginTop: spacing.md,
    borderWidth: 1,
    borderColor: "#F2C9C9",
  },
  disclaimerBannerText: { flex: 1, fontFamily: fonts.uiSemi, fontSize: 13, color: colors.liturgical.red },
  sectionTitle: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 2.5,
    color: colors.gold,
    textTransform: "uppercase",
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  grid: { gap: spacing.sm },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  cardHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  levelPill: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
  },
  levelPillText: { fontFamily: fonts.uiSemi, fontSize: 9, color: colors.gold, letterSpacing: 1.2 },
  cardTitle: { fontFamily: fonts.headingSemi, fontSize: 17, color: colors.textPrimary, marginTop: spacing.sm },
  cardTradition: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2, letterSpacing: 0.6 },
  cardTagline: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13, color: colors.textSecondary, marginTop: 6, lineHeight: 19 },
  cardFooter: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: spacing.sm },
  patronRow: { flexDirection: "row", alignItems: "center", gap: 4, flex: 1 },
  patronText: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.primary, flexShrink: 1 },
  progressText: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted },
  recentRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginBottom: spacing.sm,
  },
  recentTitle: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  recentMeta: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  modalScrim: { flex: 1, backgroundColor: "rgba(0,0,0,0.55)", justifyContent: "center", padding: spacing.lg },
  disclaimerSheet: {
    backgroundColor: colors.background,
    borderRadius: radius.lg,
    padding: spacing.lg,
    ...shadow.card,
  },
  disclaimerHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: spacing.sm },
  disclaimerTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary },
  disclaimerBody: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary, lineHeight: 21 },
  disclaimerActions: { flexDirection: "row", justifyContent: "flex-end", marginTop: spacing.md },
  ackBtn: { paddingHorizontal: spacing.lg, paddingVertical: 12, borderRadius: radius.round, backgroundColor: colors.primary },
  ackBtnText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 14 },
  pressed: { opacity: 0.7 },
});

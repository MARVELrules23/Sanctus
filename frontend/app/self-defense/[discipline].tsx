import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";

import { api, SDDiscipline, SDPatron, SDProgress, SDSession } from "@/src/api";
import MartialArtsMediaList from "@/src/components/MartialArtsMediaList";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { timeAgo } from "@/src/utils/time-ago";

type DetailResponse = { discipline: SDDiscipline; patron: SDPatron; progress: SDProgress };

const DURATIONS = [20, 30, 45, 60, 90];
const LEVELS: Array<"beginner" | "intermediate" | "advanced"> = ["beginner", "intermediate", "advanced"];

const PARTNER_EQUIPMENT = ["partner", "mats", "pads", "mitts", "gi", "no_gi"];

export default function DisciplineDetailScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ discipline?: string }>();
  const disciplineId = typeof params.discipline === "string" ? params.discipline : "";

  const [detail, setDetail] = useState<DetailResponse | null>(null);
  const [sessions, setSessions] = useState<SDSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  // Generator controls
  const [duration, setDuration] = useState(45);
  const [hasPartner, setHasPartner] = useState(false);
  const [equipment, setEquipment] = useState<string[]>([]);
  const [overrideLevel, setOverrideLevel] = useState<null | "beginner" | "intermediate" | "advanced">(null);
  const [includeReflection, setIncludeReflection] = useState(true);

  const load = useCallback(async () => {
    if (!disciplineId) return;
    try {
      const [d, s] = await Promise.all([
        api<DetailResponse>(`/self-defense/disciplines/${disciplineId}`),
        api<{ items: SDSession[] }>(`/self-defense/sessions?discipline_id=${disciplineId}&limit=50`),
      ]);
      setDetail(d);
      setSessions(s.items || []);
    } catch (e: any) {
      Alert.alert("Couldn't load discipline", e?.message || "Please try again.");
      router.back();
    } finally {
      setLoading(false);
    }
  }, [disciplineId, router]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  // Auto-clear partner-only equipment when going solo
  useEffect(() => {
    if (!hasPartner) {
      setEquipment((eq) => eq.filter((e) => !PARTNER_EQUIPMENT.includes(e) || e === "mats"));
    }
  }, [hasPartner]);

  const equipmentOptions = useMemo(() => {
    return detail?.discipline.equipment_options.filter((e) => e !== "solo" && e !== "partner") || [];
  }, [detail]);

  const generate = async () => {
    if (!detail) return;
    setGenerating(true);
    try {
      const eq = [...equipment];
      if (hasPartner && !eq.includes("partner")) eq.push("partner");
      if (!hasPartner && !eq.includes("solo")) eq.push("solo");
      const r = await api<SDSession>("/self-defense/generate", {
        method: "POST",
        body: {
          discipline_id: disciplineId,
          duration_minutes: duration,
          equipment: eq,
          has_partner: hasPartner,
          override_level: overrideLevel,
          include_patron_reflection: includeReflection,
        },
      });
      router.push({ pathname: "/self-defense/session/[id]", params: { id: r.session_id } });
    } catch (e: any) {
      Alert.alert("Couldn't generate session", e?.message || "Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  const toggleEquipment = (key: string) => {
    setEquipment((eq) => (eq.includes(key) ? eq.filter((x) => x !== key) : [...eq, key]));
  };

  if (loading || !detail) {
    return (
      <SafeAreaView style={styles.safe}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
        </View>
      </SafeAreaView>
    );
  }

  const { discipline, patron, progress } = detail;
  const effectiveLevel = overrideLevel || progress.current_level;
  const nextThreshold = progress.current_level === "beginner" ? 12 : progress.current_level === "intermediate" ? 30 : null;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="sd-discipline-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12} testID="sd-discipline-back">
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle} numberOfLines={1}>{discipline.name}</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Hero */}
        <View style={styles.hero}>
          <Ionicons name={discipline.icon as any} size={28} color={colors.gold} />
          <Text style={styles.heroTradition}>{discipline.tradition.toUpperCase()}</Text>
          <Text style={styles.heroTitle}>{discipline.name}</Text>
          <Text style={styles.heroTagline}>{discipline.tagline}</Text>
          <Text style={styles.heroDescription}>{discipline.description}</Text>
        </View>

        {/* Patron card */}
        <View style={styles.patronCard} testID="sd-patron-card">
          <View style={styles.patronHeader}>
            <Ionicons name={(patron.icon as any) || "ribbon-outline"} size={18} color={colors.gold} />
            <Text style={styles.patronLabel}>PATRON</Text>
            {patron.feast_day && patron.feast_day !== "—" ? (
              <Text style={styles.patronFeast}>· Feast {patron.feast_day}</Text>
            ) : null}
          </View>
          <Text style={styles.patronName}>{patron.name}</Text>
          {patron.title ? <Text style={styles.patronTitle}>{patron.title}</Text> : null}
          {patron.why_aligned ? <Text style={styles.patronBody}>{patron.why_aligned}</Text> : null}
          {patron.scripture ? <Text style={styles.patronScripture}>— {patron.scripture}</Text> : null}
        </View>

        {/* Films & anime where the discipline is central */}
        <MartialArtsMediaList
          disciplineId={discipline.id}
          disciplineName={discipline.name}
          initiallyCollapsed
        />

        {/* Progress */}
        <View style={styles.progressCard} testID="sd-progress-card">
          <View style={styles.progressRow}>
            <View style={styles.levelBadge}>
              <Text style={styles.levelBadgeText}>{progress.current_level.toUpperCase()}</Text>
            </View>
            <Text style={styles.progressMain}>
              <Text style={styles.progressNum}>{progress.sessions_completed}</Text>
              <Text style={styles.progressLabel}> sessions completed</Text>
            </Text>
          </View>
          {nextThreshold ? (
            <View style={styles.progressBarTrack}>
              <View
                style={[
                  styles.progressBarFill,
                  { width: `${Math.min(100, (progress.sessions_completed / nextThreshold) * 100)}%` },
                ]}
              />
            </View>
          ) : (
            <Text style={styles.progressMax}>You&apos;re at the highest tier — keep refining.</Text>
          )}
          {nextThreshold ? (
            <Text style={styles.progressHint}>
              {Math.max(0, nextThreshold - progress.sessions_completed)} more to {progress.current_level === "beginner" ? "intermediate" : "advanced"}
            </Text>
          ) : null}
          {progress.recent_focus && progress.recent_focus.length > 0 ? (
            <Text style={styles.recentFocusText} numberOfLines={2}>
              Recent focus: {progress.recent_focus.slice(-3).join(" → ")}
            </Text>
          ) : null}
        </View>

        {/* Generator */}
        <Text style={styles.sectionTitle}>Next session</Text>
        <View style={styles.generator}>
          {/* Duration */}
          <Text style={styles.fieldLabel}>Duration</Text>
          <View style={styles.chipsRow}>
            {DURATIONS.map((m) => (
              <Pressable
                key={m}
                onPress={() => setDuration(m)}
                testID={`sd-duration-${m}`}
                style={({ pressed }) => [styles.chip, duration === m && styles.chipActive, pressed && styles.pressed]}
              >
                <Text style={[styles.chipText, duration === m && styles.chipTextActive]}>{m} min</Text>
              </Pressable>
            ))}
          </View>

          {/* Partner toggle */}
          <View style={styles.rowBetween}>
            <View style={{ flex: 1, marginRight: spacing.md }}>
              <Text style={styles.fieldLabel}>Training with a partner?</Text>
              <Text style={styles.fieldHint}>
                {discipline.id === "kendo" ? "Solo includes Iaido form work." : "Solo skips partner-only drills."}
              </Text>
            </View>
            <Switch
              testID="sd-partner-toggle"
              value={hasPartner}
              onValueChange={setHasPartner}
              trackColor={{ true: colors.primary, false: colors.borderSoft }}
              thumbColor={colors.gold}
            />
          </View>

          {/* Equipment chips */}
          {equipmentOptions.length > 0 ? (
            <>
              <Text style={styles.fieldLabel}>Equipment</Text>
              <View style={styles.chipsRow}>
                {equipmentOptions.map((eq) => {
                  const disabled = !hasPartner && PARTNER_EQUIPMENT.includes(eq) && eq !== "mats";
                  const active = equipment.includes(eq);
                  return (
                    <Pressable
                      key={eq}
                      onPress={() => !disabled && toggleEquipment(eq)}
                      testID={`sd-equipment-${eq}`}
                      disabled={disabled}
                      style={({ pressed }) => [
                        styles.chip,
                        active && styles.chipActive,
                        disabled && styles.chipDisabled,
                        pressed && !disabled && styles.pressed,
                      ]}
                    >
                      <Text style={[styles.chipText, active && styles.chipTextActive, disabled && styles.chipTextDisabled]}>
                        {prettyLabel(eq)}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            </>
          ) : null}

          {/* Level override */}
          <Text style={styles.fieldLabel}>Level (auto: {progress.current_level})</Text>
          <View style={styles.chipsRow}>
            <Pressable
              onPress={() => setOverrideLevel(null)}
              testID="sd-level-auto"
              style={({ pressed }) => [styles.chip, overrideLevel === null && styles.chipActive, pressed && styles.pressed]}
            >
              <Text style={[styles.chipText, overrideLevel === null && styles.chipTextActive]}>Auto</Text>
            </Pressable>
            {LEVELS.map((lvl) => (
              <Pressable
                key={lvl}
                onPress={() => setOverrideLevel(lvl)}
                testID={`sd-level-${lvl}`}
                style={({ pressed }) => [styles.chip, overrideLevel === lvl && styles.chipActive, pressed && styles.pressed]}
              >
                <Text style={[styles.chipText, overrideLevel === lvl && styles.chipTextActive]}>
                  {lvl[0].toUpperCase() + lvl.slice(1)}
                </Text>
              </Pressable>
            ))}
          </View>

          {/* Patron reflection */}
          <View style={styles.rowBetween}>
            <View style={{ flex: 1, marginRight: spacing.md }}>
              <Text style={styles.fieldLabel}>Patron-saint reflection</Text>
              <Text style={styles.fieldHint}>Open & close with {patron.name}.</Text>
            </View>
            <Switch
              testID="sd-reflection-toggle"
              value={includeReflection}
              onValueChange={setIncludeReflection}
              trackColor={{ true: colors.primary, false: colors.borderSoft }}
              thumbColor={colors.gold}
            />
          </View>

          {/* Generate */}
          <Pressable
            onPress={generate}
            disabled={generating}
            testID="sd-generate-button"
            style={({ pressed }) => [styles.generateBtn, generating && { opacity: 0.6 }, pressed && styles.pressed]}
          >
            {generating ? (
              <ActivityIndicator color={colors.gold} />
            ) : (
              <>
                <Ionicons name="sparkles" size={16} color={colors.gold} />
                <Text style={styles.generateBtnText}>
                  Generate {effectiveLevel} session
                </Text>
              </>
            )}
          </Pressable>
          <Text style={styles.generatorHint}>
            The AI reads your past sessions in this discipline and progresses you forward.
          </Text>
        </View>

        {/* History */}
        <Text style={styles.sectionTitle}>Past sessions</Text>
        {sessions.length === 0 ? (
          <Text style={styles.empty}>No sessions yet — generate your first.</Text>
        ) : (
          sessions.map((s) => (
            <Pressable
              key={s.session_id}
              onPress={() => router.push({ pathname: "/self-defense/session/[id]", params: { id: s.session_id } })}
              testID={`sd-history-${s.session_id}`}
              style={({ pressed }) => [styles.histRow, pressed && styles.pressed]}
            >
              <View style={[styles.histDot, { backgroundColor: s.completed_at ? colors.gold : colors.borderSoft }]} />
              <View style={{ flex: 1 }}>
                <Text style={styles.histTitle} numberOfLines={1}>{s.plan?.title || "Session"}</Text>
                <Text style={styles.histMeta}>
                  {s.level} · {s.duration_minutes}m · {s.plan?.technique_focus || "—"} · {timeAgo(s.generated_at)}
                  {s.source === "redo" ? " · redo" : ""}
                </Text>
              </View>
              {s.completed_at ? (
                <Ionicons name="checkmark-circle" size={20} color={colors.gold} />
              ) : (
                <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
              )}
            </Pressable>
          ))
        )}
        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function prettyLabel(key: string): string {
  return key.split("_").map((s) => s[0]?.toUpperCase() + s.slice(1)).join(" ");
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
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.textPrimary, flex: 1, textAlign: "center", marginHorizontal: spacing.sm },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  scroll: { padding: spacing.lg },
  hero: {
    backgroundColor: colors.primary,
    borderRadius: radius.lg,
    padding: spacing.lg,
    ...shadow.card,
  },
  heroTradition: { fontFamily: fonts.uiSemi, fontSize: 10, color: colors.gold, letterSpacing: 2.5, marginTop: spacing.sm },
  heroTitle: { fontFamily: fonts.headingBold, fontSize: 24, color: "#F9F6E9", marginTop: 4 },
  heroTagline: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 14, color: colors.gold, marginTop: 6 },
  heroDescription: { fontFamily: fonts.bodyRegular, fontSize: 14, color: "#E4DDC2", marginTop: spacing.sm, lineHeight: 21 },
  patronCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    marginTop: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  patronHeader: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 6 },
  patronLabel: { fontFamily: fonts.uiSemi, fontSize: 10, letterSpacing: 2, color: colors.gold },
  patronFeast: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted },
  patronName: { fontFamily: fonts.headingSemi, fontSize: 17, color: colors.textPrimary },
  patronTitle: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12, color: colors.textMuted, marginTop: 2 },
  patronBody: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textPrimary, lineHeight: 20, marginTop: spacing.sm },
  patronScripture: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.primary, marginTop: 6 },
  progressCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    marginTop: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  progressRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.sm },
  levelBadge: { backgroundColor: colors.primary, paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.round },
  levelBadgeText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 11, letterSpacing: 1.4 },
  progressMain: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary },
  progressNum: { fontFamily: fonts.headingBold, fontSize: 22, color: colors.textPrimary },
  progressLabel: { color: colors.textSecondary },
  progressBarTrack: { height: 6, borderRadius: 3, backgroundColor: colors.borderSoft, marginTop: 4, overflow: "hidden" },
  progressBarFill: { height: 6, backgroundColor: colors.gold },
  progressMax: { fontFamily: fonts.uiSemi, color: colors.gold, marginTop: 4 },
  progressHint: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 4 },
  recentFocusText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12, color: colors.textSecondary, marginTop: 6 },
  sectionTitle: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 2.5,
    color: colors.gold,
    textTransform: "uppercase",
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  generator: { backgroundColor: colors.surface, borderRadius: radius.md, padding: spacing.md, borderWidth: 1, borderColor: colors.borderSoft, ...shadow.card },
  fieldLabel: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textPrimary, marginTop: spacing.sm },
  fieldHint: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  chipsRow: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 6 },
  chip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.background },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipDisabled: { opacity: 0.35 },
  chipText: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textSecondary },
  chipTextActive: { color: colors.gold, fontFamily: fonts.uiSemi },
  chipTextDisabled: { color: colors.textMuted },
  rowBetween: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: spacing.md },
  generateBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: colors.primary,
    paddingVertical: 14,
    borderRadius: radius.round,
    marginTop: spacing.md,
  },
  generateBtnText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 14 },
  generatorHint: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 11, color: colors.textMuted, marginTop: spacing.sm, textAlign: "center" },
  histRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginBottom: spacing.sm,
  },
  histDot: { width: 10, height: 10, borderRadius: 5 },
  histTitle: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  histMeta: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  empty: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, textAlign: "center", paddingVertical: spacing.lg },
  pressed: { opacity: 0.7 },
});

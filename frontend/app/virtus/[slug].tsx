/**
 * Virtus — virtue detail.
 *
 * Renders a single virtue/topic's subsections (what it is, living it across
 * the seasons of life, overcoming the opposing vice, saints of the virtue),
 * plus a Premium-gated Resources section. For the "Saints of Virtue" topic it
 * renders saints grouped by virtue. Admins see an Edit button.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import {
  getVirtue,
  getVirtueResources,
  listVirtues,
  VirtueContent,
  VirtueResource,
} from "@/src/api";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

function Paragraphs({ text, style }: { text?: string; style: any }) {
  if (!text) return null;
  return (
    <>
      {text.split(/\n{2,}/).map((p, i) => (
        <Text key={i} style={style}>{p}</Text>
      ))}
    </>
  );
}

function Saint({ s, accent }: { s: { name: string; years?: string; why?: string; prayer?: string }; accent: string }) {
  return (
    <View style={styles.saintCard}>
      <View style={styles.saintHead}>
        <Ionicons name="ribbon-outline" size={15} color={accent} />
        <Text style={styles.saintName}>{s.name}</Text>
        {s.years ? <Text style={styles.saintYears}>{s.years}</Text> : null}
      </View>
      {s.why ? <Text style={styles.saintWhy}>{s.why}</Text> : null}
      {s.prayer ? (
        <View style={[styles.prayerBox, { borderLeftColor: accent }]}>
          <Text style={styles.prayerText}>{s.prayer}</Text>
        </View>
      ) : null}
    </View>
  );
}

export default function VirtueDetailScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const router = useRouter();

  const [data, setData] = useState<VirtueContent | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<Record<string, boolean>>({ what_is: true });

  const [resources, setResources] = useState<VirtueResource[] | null>(null);
  const [resLoading, setResLoading] = useState(false);

  const load = useCallback(async () => {
    if (!slug) return;
    setLoading(true);
    setError(null);
    try {
      const [d, list] = await Promise.all([getVirtue(slug), listVirtues().catch(() => null)]);
      setData(d);
      if (list) setIsAdmin(!!list.is_admin);
    } catch (e: any) {
      setError(e?.message || "Could not load this virtue.");
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => { void load(); }, [load]);

  const accent = data?.accent_color || colors.gold;
  const toggle = (k: string) => setOpen((p) => ({ ...p, [k]: !p[k] }));

  const loadResources = async () => {
    if (!slug || !data) return;
    if (!data.user_is_premium) {
      router.push("/premium" as any);
      return;
    }
    if (!open.resources) toggle("resources");
    if (resources) return;
    setResLoading(true);
    try {
      const r = await getVirtueResources(slug);
      setResources(r.resources || []);
    } catch (e: any) {
      if (e?.status === 402) router.push("/premium" as any);
    } finally {
      setResLoading(false);
    }
  };

  const Section = ({
    id, title, icon, children, onExpand,
  }: { id: string; title: string; icon: keyof typeof Ionicons.glyphMap; children?: React.ReactNode; onExpand?: () => void }) => {
    const isOpen = !!open[id];
    return (
      <View style={[styles.sectionCard, { borderTopColor: accent }]} testID={`virtus-section-${id}`}>
        <Pressable
          onPress={() => { onExpand ? onExpand() : toggle(id); }}
          style={({ pressed }) => [styles.sectionHead, pressed && { opacity: 0.8 }]}
          testID={`virtus-section-toggle-${id}`}
        >
          <Ionicons name={icon} size={18} color={accent} />
          <Text style={styles.sectionTitle}>{title}</Text>
          <View style={{ flex: 1 }} />
          <Ionicons name={isOpen ? "chevron-up" : "chevron-down"} size={18} color={colors.textMuted} />
        </Pressable>
        {isOpen ? <View style={styles.sectionBody}>{children}</View> : null}
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID={`virtus-detail-${slug}`}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable testID="virtus-detail-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.headerTitle} numberOfLines={1}>{data?.name || "Virtue"}</Text>
        </View>
        {isAdmin ? (
          <Pressable
            testID="virtus-edit-btn"
            onPress={() => router.push({ pathname: "/virtus/edit/[slug]", params: { slug: slug! } } as any)}
            hitSlop={10}
          >
            <Ionicons name="create-outline" size={22} color={colors.gold} />
          </Pressable>
        ) : (
          <View style={{ width: 26 }} />
        )}
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={accent} />
          <Text style={styles.loadingHint}>Preparing this virtue…</Text>
        </View>
      ) : error || !data ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error || "Not found."}</Text>
          <Pressable onPress={load} style={({ pressed }) => [styles.retry, pressed && { opacity: 0.7 }]}>
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          {/* Hero */}
          <View style={[styles.hero, { borderColor: accent }]}>
            <View style={[styles.heroIcon, { backgroundColor: accent + "22", borderColor: accent }]}>
              <Ionicons name={(data.icon as keyof typeof Ionicons.glyphMap) || "ellipse-outline"} size={30} color={accent} />
            </View>
            <Text style={styles.heroName}>{data.name}</Text>
            <Text style={styles.heroTagline}>{data.tagline}</Text>
            {data.opposite_vice ? (
              <View style={[styles.vicePill, { borderColor: accent }]}>
                <Ionicons name="warning-outline" size={12} color={accent} />
                <Text style={[styles.vicePillText, { color: accent }]}>Opposed to {data.opposite_vice}</Text>
              </View>
            ) : null}
          </View>

          {data.kind === "saints" ? (
            <>
              {data.intro ? (
                <View style={styles.introCard}>
                  <Ornament />
                  <Paragraphs text={data.intro} style={styles.bodyText} />
                </View>
              ) : null}
              {(data.saints_by_virtue || []).map((g, gi) => (
                <View key={gi} style={[styles.sectionCard, { borderTopColor: accent }]}>
                  <Text style={[styles.sectionTitle, { marginBottom: spacing.sm }]}>{g.virtue}</Text>
                  {g.saints.map((s, si) => <Saint key={si} s={s} accent={accent} />)}
                </View>
              ))}
            </>
          ) : (
            <>
              <Section id="what_is" title={`What is ${data.name}?`} icon="book-outline">
                <Paragraphs text={data.what_is} style={styles.bodyText} />
              </Section>

              <Section id="life_stages" title="Through the seasons of life" icon="trail-sign-outline">
                {(["singleness", "dating", "marriage"] as const).map((k) => (
                  <View key={k} style={styles.stageBlock}>
                    <Text style={[styles.stageLabel, { color: accent }]}>{k.toUpperCase()}</Text>
                    <Paragraphs text={data.life_stages?.[k]} style={styles.bodyText} />
                  </View>
                ))}
              </Section>

              <Section id="overcoming" title={`Overcoming ${data.opposite_vice || "the vice"}`} icon="flame-outline">
                <Paragraphs text={data.overcoming_vice} style={styles.bodyText} />
              </Section>

              {(data.saints || []).length > 0 ? (
                <Section id="saints" title="Saints of this virtue" icon="people-outline">
                  {(data.saints || []).map((s, si) => <Saint key={si} s={s} accent={accent} />)}
                </Section>
              ) : null}
            </>
          )}

          {/* Resources — Premium */}
          <View style={[styles.sectionCard, { borderTopColor: colors.gold }]} testID="virtus-section-resources">
            <Pressable
              onPress={loadResources}
              style={({ pressed }) => [styles.sectionHead, pressed && { opacity: 0.8 }]}
              testID="virtus-resources-toggle"
            >
              <Ionicons name="library-outline" size={18} color={colors.gold} />
              <Text style={styles.sectionTitle}>Resources to go deeper</Text>
              <View style={{ flex: 1 }} />
              {data.user_is_premium ? (
                <Ionicons name={open.resources ? "chevron-up" : "chevron-down"} size={18} color={colors.textMuted} />
              ) : (
                <Ionicons name="lock-closed" size={16} color={colors.gold} />
              )}
            </Pressable>

            {!data.user_is_premium ? (
              <View style={styles.lockBody}>
                <Text style={styles.lockText}>
                  Curated books, prayers, and practices to grow in {data.name} are
                  part of Sanctus Premium.
                </Text>
                <Pressable
                  testID="virtus-resources-unlock"
                  onPress={() => router.push("/premium" as any)}
                  style={({ pressed }) => [styles.unlockBtn, pressed && { opacity: 0.85 }]}
                >
                  <Ionicons name="sparkles" size={14} color={colors.gold} />
                  <Text style={styles.unlockText}>Unlock with Premium</Text>
                </Pressable>
              </View>
            ) : open.resources ? (
              <View style={styles.sectionBody}>
                {resLoading ? (
                  <ActivityIndicator color={colors.gold} />
                ) : (resources || []).length === 0 ? (
                  <Text style={styles.bodyText}>No resources yet.</Text>
                ) : (
                  (resources || []).map((r, ri) => (
                    <View key={ri} style={styles.resourceRow} testID={`virtus-resource-${ri}`}>
                      <View style={[styles.resourceKind, { borderColor: colors.gold }]}>
                        <Text style={styles.resourceKindText}>{(r.kind || "item").toUpperCase()}</Text>
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.resourceTitle}>{r.title}</Text>
                        {r.author ? <Text style={styles.resourceAuthor}>{r.author}</Text> : null}
                        {r.description ? <Text style={styles.resourceDesc}>{r.description}</Text> : null}
                      </View>
                    </View>
                  ))
                )}
              </View>
            ) : null}
          </View>

          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
    gap: spacing.md,
  },
  headerTitleWrap: { flex: 1, alignItems: "center" },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 18, color: colors.textPrimary },
  scroll: { padding: spacing.lg, gap: spacing.md },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.md },
  loadingHint: { fontFamily: fonts.bodyItalic, fontStyle: "italic", color: colors.textMuted, fontSize: 13 },
  errorText: { fontFamily: fonts.bodyRegular, color: colors.textSecondary, textAlign: "center" },
  retry: { paddingHorizontal: spacing.lg, paddingVertical: 10, backgroundColor: colors.primary, borderRadius: radius.round },
  retryText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 13 },

  hero: {
    alignItems: "center",
    padding: spacing.lg,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    ...shadow.card,
    gap: 6,
  },
  heroIcon: { width: 60, height: 60, borderRadius: 30, alignItems: "center", justifyContent: "center", borderWidth: 1.5, marginBottom: 4 },
  heroName: { fontFamily: fonts.headingBold, fontSize: 24, color: colors.textPrimary },
  heroTagline: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13, color: colors.textSecondary, textAlign: "center" },
  vicePill: {
    flexDirection: "row", alignItems: "center", gap: 4,
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: radius.round, borderWidth: 1, marginTop: 6,
  },
  vicePillText: { fontFamily: fonts.uiSemi, fontSize: 10.5, letterSpacing: 0.4 },

  introCard: {
    padding: spacing.lg, borderRadius: radius.lg, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: colors.borderSoft, ...shadow.card, alignItems: "center", gap: spacing.sm,
  },

  sectionCard: {
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderTopWidth: 3,
    ...shadow.card,
    overflow: "hidden",
  },
  sectionHead: { flexDirection: "row", alignItems: "center", gap: spacing.sm, padding: spacing.md },
  sectionTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  sectionBody: { paddingHorizontal: spacing.md, paddingBottom: spacing.md, gap: spacing.sm },
  bodyText: { fontFamily: fonts.bodyRegular, fontSize: 14, lineHeight: 22, color: colors.textPrimary, marginBottom: spacing.sm },

  stageBlock: { marginBottom: spacing.md },
  stageLabel: { fontFamily: fonts.uiSemi, fontSize: 10.5, letterSpacing: 1.4, marginBottom: 5 },

  saintCard: {
    padding: spacing.md, borderRadius: radius.md, backgroundColor: colors.background,
    borderWidth: 1, borderColor: colors.borderSoft, marginBottom: spacing.sm, gap: 6,
  },
  saintHead: { flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" },
  saintName: { fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary },
  saintYears: { fontFamily: fonts.bodyRegular, fontSize: 11, color: colors.textMuted },
  saintWhy: { fontFamily: fonts.bodyRegular, fontSize: 13, lineHeight: 20, color: colors.textSecondary },
  prayerBox: { paddingLeft: spacing.sm, paddingVertical: 4, borderLeftWidth: 2 },
  prayerText: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13, lineHeight: 20, color: colors.textPrimary },

  lockBody: { paddingHorizontal: spacing.md, paddingBottom: spacing.md, gap: spacing.sm },
  lockText: { fontFamily: fonts.bodyRegular, fontSize: 13, lineHeight: 20, color: colors.textSecondary },
  unlockBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6,
    paddingVertical: 11, borderRadius: radius.round, backgroundColor: colors.primary,
  },
  unlockText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold, letterSpacing: 0.4 },

  resourceRow: { flexDirection: "row", gap: spacing.sm, alignItems: "flex-start", marginBottom: spacing.sm },
  resourceKind: { paddingHorizontal: 7, paddingVertical: 3, borderRadius: radius.round, borderWidth: 1 },
  resourceKindText: { fontFamily: fonts.uiSemi, fontSize: 8.5, letterSpacing: 0.6, color: colors.gold },
  resourceTitle: { fontFamily: fonts.headingSemi, fontSize: 14, color: colors.textPrimary },
  resourceAuthor: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 12, color: colors.textMuted, marginTop: 1 },
  resourceDesc: { fontFamily: fonts.bodyRegular, fontSize: 12.5, lineHeight: 18, color: colors.textSecondary, marginTop: 3 },
});

import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, Linking, Platform, Pressable, ScrollView, StyleSheet, TextInput, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";

import {
  getFamilyToday, FamilyToday, FamilyPrayer,
  getFamilyMembers, addFamilyMember, deleteFamilyMember, getCompanionOptions,
  FamilyMember, CompanionOption,
} from "@/src/api";
import { areRemindersEnabled, enableFamilyReminders } from "@/src/family-notifications";
import { colors, fonts, radius, spacing } from "@/src/theme";

const CHILDREN_BOOKS = [
  { slug: "bible-stories-for-little-souls", title: "Bible Stories for Little Souls", sub: "God's great story, told for children", icon: "book-outline", color: "#3E6B8A" },
  { slug: "little-saints-for-little-hearts", title: "Little Saints for Little Hearts", sub: "Heroes of holiness for young readers", icon: "sparkles-outline", color: "#8A6A2E" },
  { slug: "the-holy-mass-for-little-ones", title: "The Holy Mass for Little Ones", sub: "Understanding the Mass, step by step", icon: "flower-outline", color: "#5B3E7A" },
];

const PARENT_GUIDES = [
  { slug: "parents-guide-to-the-mass", title: "A Parent's Guide to the Mass", icon: "book-outline", color: "#8A2E2E" },
  { slug: "parents-guide-to-confession", title: "A Parent's Guide to Confession", icon: "heart-outline", color: "#5B3E7A" },
  { slug: "teaching-your-child-the-faith", title: "Teaching Your Child the Faith", icon: "school-outline", color: "#3E6B5B" },
  { slug: "humanae-vitae", title: "Humanae Vitae (on married love)", icon: "ribbon-outline", color: "#7A5C2E" },
];

function PrayerCard({ prayer, icon }: { prayer: FamilyPrayer; icon: string }) {
  return (
    <View style={styles.card}>
      <View style={styles.cardHead}>
        <Ionicons name={icon as any} size={18} color={colors.gold} />
        <Text style={styles.cardHeadText}>{prayer.title}</Text>
      </View>
      {prayer.lines.map((ln, i) => (
        <View key={i} style={styles.prayerLine}>
          <Text style={styles.prayerWho}>{ln.who}</Text>
          <Text style={styles.prayerText}>{ln.text}</Text>
        </View>
      ))}
    </View>
  );
}

function ResourceTile({ title, sub, icon, color, onPress, testID }: { title: string; sub?: string; icon: string; color: string; onPress: () => void; testID?: string }) {
  return (
    <Pressable testID={testID} onPress={onPress} style={({ pressed }) => [styles.tile, pressed && { opacity: 0.85 }]}>
      <View style={[styles.tileIcon, { backgroundColor: color }]}><Ionicons name={icon as any} size={20} color="#FBF6E9" /></View>
      <View style={{ flex: 1 }}>
        <Text style={styles.tileTitle}>{title}</Text>
        {sub ? <Text style={styles.tileSub}>{sub}</Text> : null}
      </View>
      <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
    </Pressable>
  );
}

function FamilyCompanions() {
  const router = useRouter();
  const [members, setMembers] = useState<FamilyMember[]>([]);
  const [options, setOptions] = useState<CompanionOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [m, o] = await Promise.all([getFamilyMembers(), getCompanionOptions()]);
      setMembers(m.items || []);
      setOptions(o || []);
    } catch {
      setMembers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const onAdd = async () => {
    const nm = name.trim();
    if (!nm) { Alert.alert("Add a name", "Please enter a name for the family member."); return; }
    setSaving(true);
    try {
      const created = await addFamilyMember(nm, slug);
      setMembers((prev) => [...prev, created]);
      setName(""); setSlug(null); setAdding(false);
    } catch {
      Alert.alert("Couldn't add", "Something went wrong. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const onDelete = (m: FamilyMember) => {
    Alert.alert("Remove", `Remove ${m.name} from your family companions?`, [
      { text: "Cancel", style: "cancel" },
      { text: "Remove", style: "destructive", onPress: async () => {
        setMembers((prev) => prev.filter((x) => x.id !== m.id));
        try { await deleteFamilyMember(m.id); } catch {}
      } },
    ]);
  };

  return (
    <View style={styles.card} testID="family-companions">
      <View style={styles.cardHead}>
        <Ionicons name="people-outline" size={18} color={colors.gold} />
        <Text style={styles.cardHeadText}>My family companions</Text>
      </View>
      <Text style={styles.sectionHint}>Give each person a patron saint to walk with them.</Text>

      {loading ? (
        <ActivityIndicator style={{ marginVertical: 16 }} color={colors.gold} />
      ) : (
        <>
          {members.map((m) => (
            <View key={m.id} style={styles.memberRow} testID={`family-member-${m.id}`}>
              <View style={{ flex: 1 }}>
                <Text style={styles.memberName}>{m.name}</Text>
                {m.companion_name ? (
                  <Pressable onPress={() => m.companion_slug && router.push(`/companions/${m.companion_slug}` as any)}>
                    <Text style={styles.memberPatron}>Patron: {m.companion_name}</Text>
                  </Pressable>
                ) : <Text style={styles.memberNoPatron}>No patron chosen</Text>}
              </View>
              <Pressable testID={`family-member-delete-${m.id}`} onPress={() => onDelete(m)} hitSlop={10}>
                <Ionicons name="close-circle-outline" size={22} color={colors.textMuted} />
              </Pressable>
            </View>
          ))}
          {members.length === 0 ? <Text style={styles.memberEmpty}>No family members yet.</Text> : null}

          {adding ? (
            <View style={styles.addBox}>
              <TextInput
                testID="family-member-name-input"
                value={name}
                onChangeText={setName}
                placeholder="Name (e.g. Maria)"
                placeholderTextColor={colors.textMuted}
                style={styles.input}
              />
              <Text style={styles.pickLabel}>Choose a patron saint (optional)</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, paddingVertical: 4 }}>
                {options.map((o) => (
                  <Pressable
                    key={o.slug}
                    testID={`family-patron-${o.slug}`}
                    onPress={() => setSlug((s) => (s === o.slug ? null : o.slug))}
                    style={[styles.chip, slug === o.slug && styles.chipActive]}
                  >
                    <Text style={[styles.chipText, slug === o.slug && styles.chipTextActive]}>{o.name}</Text>
                  </Pressable>
                ))}
              </ScrollView>
              <View style={styles.addActions}>
                <Pressable testID="family-member-cancel" onPress={() => { setAdding(false); setName(""); setSlug(null); }} style={styles.btnGhost}>
                  <Text style={styles.btnGhostText}>Cancel</Text>
                </Pressable>
                <Pressable testID="family-member-save" onPress={onAdd} disabled={saving} style={styles.btnPrimary}>
                  {saving ? <ActivityIndicator size="small" color="#FBF6E9" /> : <Text style={styles.btnPrimaryText}>Add</Text>}
                </Pressable>
              </View>
            </View>
          ) : (
            <Pressable testID="family-member-add" onPress={() => setAdding(true)} style={({ pressed }) => [styles.addBtn, pressed && { opacity: 0.85 }]}>
              <Ionicons name="add-circle-outline" size={20} color={colors.gold} />
              <Text style={styles.addBtnText}>Add a family member</Text>
            </Pressable>
          )}
        </>
      )}
    </View>
  );
}

export default function FamilyScreen() {
  const router = useRouter();
  const [data, setData] = useState<FamilyToday | null>(null);
  const [loading, setLoading] = useState(true);
  const [reminders, setReminders] = useState(false);
  const [saintOpen, setSaintOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await getFamilyToday());
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    areRemindersEnabled().then(setReminders);
  }, [load]);

  const onEnableReminders = async () => {
    const status = await enableFamilyReminders();
    if (status === "granted") {
      setReminders(true);
      Alert.alert("Reminders on", "You'll be gently reminded to pray together at 6:00 AM and 7:00 PM your time.");
    } else if (status === "unsupported") {
      Alert.alert("Not available here", "Prayer reminders work on the installed app (iOS/Android), not the web preview.");
    } else if (status === "blocked") {
      Alert.alert(
        "Notifications are off",
        "Please enable notifications for Sanctus in your device Settings to receive prayer reminders.",
        [{ text: "Cancel", style: "cancel" }, { text: "Open Settings", onPress: () => Linking.openSettings() }],
      );
    } else {
      Alert.alert("Reminders not enabled", "You can turn these on anytime.");
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="family-screen">
      <View style={styles.header}>
        <Text style={styles.title}>Family</Text>
        <Text style={styles.subtitle}>A little domestic church, gathered in love.</Text>
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={colors.gold} />
      ) : !data ? (
        <Text style={styles.empty}>Could not load today's family prayers.</Text>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          {/* Reminders */}
          <Pressable testID="family-enable-reminders" onPress={onEnableReminders} style={({ pressed }) => [styles.reminderCard, pressed && { opacity: 0.9 }]}>
            <Ionicons name={reminders ? "notifications" : "notifications-outline"} size={20} color={colors.gold} />
            <View style={{ flex: 1 }}>
              <Text style={styles.reminderTitle}>{reminders ? "Prayer reminders are on" : "Turn on prayer reminders"}</Text>
              <Text style={styles.reminderSub}>
                {Platform.OS === "web"
                  ? "Available on the installed app: 6:00 AM & 7:00 PM (your time)."
                  : "6:00 AM morning prayer · 7:00 PM night prayer, in your timezone."}
              </Text>
            </View>
            {!reminders ? <Ionicons name="chevron-forward" size={18} color={colors.textMuted} /> : <Ionicons name="checkmark-circle" size={20} color="#5BB543" />}
          </Pressable>

          {/* Saint Spotlight */}
          <Pressable testID="family-saint-spotlight" onPress={() => setSaintOpen((v) => !v)} style={({ pressed }) => [styles.saintCard, { borderColor: data.saint.color || colors.gold }, pressed && { opacity: 0.92 }]}>
            <View style={styles.cardHead}>
              <Ionicons name={(data.saint.icon as any) || "sparkles-outline"} size={18} color={data.saint.color || colors.gold} />
              <Text style={styles.cardHeadText}>Saint Spotlight</Text>
              <View style={{ flex: 1 }} />
              <Ionicons name={saintOpen ? "chevron-up" : "chevron-down"} size={18} color={colors.textMuted} />
            </View>
            <Text style={styles.saintName}>{data.saint.name}</Text>
            <Text style={styles.saintMeta}>Feast: {data.saint.feast} · Patron of {data.saint.patronage}</Text>
            {saintOpen ? <Text style={styles.saintBio}>{data.saint.bio}</Text> : <Text style={styles.tapMore}>Tap to learn about today's saint →</Text>}
          </Pressable>

          {/* Devotional suggestion */}
          <Pressable
            testID="family-devotional"
            disabled={!data.devotional.route}
            onPress={() => data.devotional.route && router.push(data.devotional.route as any)}
            style={({ pressed }) => [styles.card, pressed && data.devotional.route && { opacity: 0.85 }]}
          >
            <View style={styles.cardHead}>
              <Ionicons name="rose-outline" size={18} color={colors.gold} />
              <Text style={styles.cardHeadText}>Today's devotion</Text>
              {data.devotional.route ? <><View style={{ flex: 1 }} /><Ionicons name="arrow-forward-circle" size={20} color={colors.gold} /></> : null}
            </View>
            <Text style={styles.devTitle}>{data.devotional.title}</Text>
            <Text style={styles.devBody}>{data.devotional.body}</Text>
          </Pressable>

          {/* Question of the day */}
          <View style={styles.questionCard} testID="family-question">
            <View style={styles.cardHead}>
              <Ionicons name="chatbubble-ellipses-outline" size={18} color={colors.gold} />
              <Text style={styles.cardHeadText}>Ask your child today</Text>
            </View>
            <Text style={styles.questionText}>{data.question}</Text>
          </View>

          {/* Prayers */}
          <PrayerCard prayer={data.morning_prayer} icon="sunny-outline" />
          <PrayerCard prayer={data.night_prayer} icon="moon-outline" />

          {/* Coloring book */}
          <Pressable testID="family-coloring" onPress={() => router.push("/coloring" as any)} style={({ pressed }) => [styles.coloringCard, pressed && { opacity: 0.9 }]}>
            <View style={styles.coloringIcon}><Ionicons name="color-palette-outline" size={22} color="#FBF6E9" /></View>
            <View style={{ flex: 1 }}>
              <Text style={styles.coloringTitle}>Catholic Coloring Book</Text>
              <Text style={styles.coloringSub}>Color in holy pictures together</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
          </Pressable>

          {/* My family companions */}
          <FamilyCompanions />

          {/* For Children books */}
          <View style={styles.sectionHeadRow}>
            <Text style={styles.sectionHead}>For Children</Text>
            <Pressable testID="family-children-all" onPress={() => router.push("/library" as any)} hitSlop={8}>
              <Text style={styles.sectionLink}>Library →</Text>
            </Pressable>
          </View>
          {CHILDREN_BOOKS.map((b) => (
            <ResourceTile
              key={b.slug}
              testID={`family-childbook-${b.slug}`}
              title={b.title}
              sub={b.sub}
              icon={b.icon}
              color={b.color}
              onPress={() => router.push(`/library/books/${b.slug}` as any)}
            />
          ))}

          {/* For Parents */}
          <View style={styles.sectionHeadRow}>
            <Text style={styles.sectionHead}>For Parents</Text>
          </View>
          {PARENT_GUIDES.map((g) => (
            <ResourceTile
              key={g.slug}
              testID={`family-guide-${g.slug}`}
              title={g.title}
              icon={g.icon}
              color={g.color}
              onPress={() => router.push(`/library/books/${g.slug}` as any)}
            />
          ))}

          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { paddingHorizontal: spacing.lg, paddingTop: spacing.sm, paddingBottom: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  title: { fontFamily: fonts.headingBold, fontSize: 26, color: colors.textPrimary },
  subtitle: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13, color: colors.textSecondary, marginTop: 2 },
  empty: { textAlign: "center", marginTop: 40, fontFamily: fonts.bodyRegular, color: colors.textSecondary },
  scroll: { padding: spacing.lg, gap: spacing.md },
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.borderSoft, padding: spacing.md },
  cardHead: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: spacing.xs },
  cardHeadText: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 1.2, color: colors.textMuted, textTransform: "uppercase" },
  reminderCard: { flexDirection: "row", alignItems: "center", gap: spacing.sm, backgroundColor: colors.surfaceDark, borderRadius: radius.lg, padding: spacing.md },
  reminderTitle: { fontFamily: fonts.headingSemi, fontSize: 15, color: "#FBF6E9" },
  reminderSub: { fontFamily: fonts.bodyRegular, fontSize: 12, color: "#E9E2D0", marginTop: 2 },
  saintCard: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1.5, padding: spacing.md },
  saintName: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.primary },
  saintMeta: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold, marginTop: 2 },
  saintBio: { fontFamily: fonts.bodyRegular, fontSize: 14.5, color: colors.textPrimary, lineHeight: 22, marginTop: spacing.sm },
  tapMore: { fontFamily: fonts.uiSemi, fontSize: 12.5, color: colors.gold, marginTop: spacing.sm },
  devTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  devBody: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, lineHeight: 21, marginTop: 2 },
  questionCard: { backgroundColor: "#FBF3E0", borderRadius: radius.lg, borderWidth: 1, borderColor: "#EED9A8", padding: spacing.md },
  questionText: { fontFamily: fonts.headingSemi, fontSize: 17, color: "#6B4E1E", lineHeight: 25, marginTop: 2 },
  prayerLine: { marginTop: spacing.sm },
  prayerWho: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 0.5, textTransform: "uppercase", color: colors.gold },
  prayerText: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary, lineHeight: 22, marginTop: 1 },
  coloringCard: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.borderSoft, padding: spacing.md },
  coloringIcon: { width: 44, height: 44, borderRadius: 22, backgroundColor: "#8E44AD", alignItems: "center", justifyContent: "center" },
  coloringTitle: { fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary },
  coloringSub: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textSecondary, marginTop: 2 },
  sectionHeadRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: spacing.sm },
  sectionHead: { fontFamily: fonts.headingBold, fontSize: 18, color: colors.textPrimary },
  sectionLink: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold },
  sectionHint: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, marginBottom: spacing.sm },
  tile: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.borderSoft, padding: spacing.md },
  tileIcon: { width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center" },
  tileTitle: { fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary },
  tileSub: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textSecondary, marginTop: 2 },
  memberRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingVertical: spacing.sm, borderTopWidth: 1, borderTopColor: colors.borderSoft },
  memberName: { fontFamily: fonts.headingSemi, fontSize: 15.5, color: colors.textPrimary },
  memberPatron: { fontFamily: fonts.uiSemi, fontSize: 12.5, color: colors.gold, marginTop: 1 },
  memberNoPatron: { fontFamily: fonts.bodyRegular, fontSize: 12.5, color: colors.textMuted, marginTop: 1 },
  memberEmpty: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textMuted, paddingVertical: spacing.sm },
  addBtn: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: spacing.sm, paddingVertical: spacing.sm },
  addBtnText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.gold },
  addBox: { marginTop: spacing.sm, gap: spacing.xs },
  input: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textPrimary, backgroundColor: colors.background, borderRadius: radius.md, borderWidth: 1, borderColor: colors.borderSoft, paddingHorizontal: spacing.md, paddingVertical: 10 },
  pickLabel: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textMuted, marginTop: spacing.xs },
  chip: { paddingHorizontal: spacing.md, paddingVertical: 8, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.background },
  chipActive: { backgroundColor: colors.gold, borderColor: colors.gold },
  chipText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textPrimary },
  chipTextActive: { color: "#FFFFFF" },
  addActions: { flexDirection: "row", justifyContent: "flex-end", gap: spacing.sm, marginTop: spacing.xs },
  btnGhost: { paddingHorizontal: spacing.lg, paddingVertical: 10, borderRadius: radius.md },
  btnGhostText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textSecondary },
  btnPrimary: { paddingHorizontal: spacing.lg, paddingVertical: 10, borderRadius: radius.md, backgroundColor: colors.primary, minWidth: 64, alignItems: "center" },
  btnPrimaryText: { fontFamily: fonts.uiSemi, fontSize: 14, color: "#FBF6E9" },
});

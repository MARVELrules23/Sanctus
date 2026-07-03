import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, Linking, Platform, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";

import { getFamilyToday, FamilyToday, FamilyPrayer } from "@/src/api";
import { areRemindersEnabled, enableFamilyReminders } from "@/src/family-notifications";
import { colors, fonts, radius, spacing } from "@/src/theme";

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
});

import React from "react";
import { ScrollView, StyleSheet, View } from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";

import { colors, fonts, radius, spacing } from "@/src/theme";

/**
 * Family hub. Content is added incrementally — this is a real, welcoming
 * landing space (not a "coming soon" wall) so the tab feels alive today.
 */
export default function FamilyScreen() {
  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="family-screen">
      <View style={styles.header}>
        <Text style={styles.title}>Family</Text>
        <Text style={styles.subtitle}>A little domestic church, gathered in love.</Text>
      </View>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.hero}>
          <View style={styles.iconWrap}>
            <Ionicons name="home-outline" size={30} color={colors.gold} />
          </View>
          <Text style={styles.heroTitle}>Your family space</Text>
          <Text style={styles.heroBody}>
            This is where prayers, traditions and moments for parents and children will live.
            More is on the way — tend this little garden of faith at home.
          </Text>
        </View>

        <View style={styles.verseCard}>
          <Text style={styles.verseText}>
            “As for me and my house, we will serve the Lord.”
          </Text>
          <Text style={styles.verseRef}>— Joshua 24:15</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { paddingHorizontal: spacing.lg, paddingTop: spacing.sm, paddingBottom: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  title: { fontFamily: fonts.headingBold, fontSize: 26, color: colors.textPrimary },
  subtitle: { fontFamily: fonts.bodyItalic, fontStyle: "italic", fontSize: 13, color: colors.textSecondary, marginTop: 2 },
  scroll: { padding: spacing.lg, gap: spacing.md },
  hero: { backgroundColor: colors.surface, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.borderSoft, padding: spacing.lg, alignItems: "center" },
  iconWrap: { width: 60, height: 60, borderRadius: 30, backgroundColor: colors.surfaceDark, alignItems: "center", justifyContent: "center", marginBottom: spacing.sm },
  heroTitle: { fontFamily: fonts.headingSemi, fontSize: 18, color: colors.primary, marginBottom: 6 },
  heroBody: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, lineHeight: 21, textAlign: "center" },
  verseCard: { backgroundColor: colors.surfaceDark, borderRadius: radius.md, padding: spacing.md, borderLeftWidth: 3, borderLeftColor: colors.gold },
  verseText: { fontFamily: fonts.bodyItalic, fontSize: 15, color: "#FBF6E9", lineHeight: 23 },
  verseRef: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold, marginTop: 6, textAlign: "right" },
});

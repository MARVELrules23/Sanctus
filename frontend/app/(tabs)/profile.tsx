import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";

import { api, User } from "@/src/api";
import { useAuth } from "@/src/auth-context";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type Prefs = {
  dietary: string;
  allergies: string;
  fitness_level: string;
  fitness_goal: string;
  devotion_focus: string;
};

const DIETARY_OPTIONS = ["balanced", "vegetarian", "pescetarian", "low-carb", "mediterranean"];
const LEVEL_OPTIONS = ["beginner", "intermediate", "advanced"];

export default function ProfileScreen() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [prefs, setPrefs] = useState<Prefs | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedFlash, setSavedFlash] = useState(false);

  const load = useCallback(async () => {
    const p = await api<Prefs>("/preferences");
    setPrefs(p);
  }, []);

  useEffect(() => {
    let c = false;
    (async () => {
      try {
        await load();
      } finally {
        if (!c) setLoading(false);
      }
    })();
    return () => {
      c = true;
    };
  }, [load]);

  const save = async (next: Prefs) => {
    setSaving(true);
    try {
      await api<Prefs>("/preferences", { method: "PUT", body: next });
      setSavedFlash(true);
      setTimeout(() => setSavedFlash(false), 1500);
    } catch (e) {
      console.warn("save prefs failed", e);
    } finally {
      setSaving(false);
    }
  };

  const update = (patch: Partial<Prefs>) => {
    if (!prefs) return;
    const next = { ...prefs, ...patch };
    setPrefs(next);
    save(next);
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="profile-screen">
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>Profile</Text>
        <View style={styles.userCard} testID="user-card">
          {user?.picture ? (
            <Image source={{ uri: user.picture }} style={styles.avatar} />
          ) : (
            <View style={[styles.avatar, styles.avatarFallback]}>
              <Text style={styles.avatarInitial}>{user?.name?.[0]?.toUpperCase() ?? "?"}</Text>
            </View>
          )}
          <View style={{ flex: 1 }}>
            <Text style={styles.userName}>{user?.name ?? "Faithful soul"}</Text>
            <Text style={styles.userEmail}>{user?.email}</Text>
            <FaithBioChips user={user} />
          </View>
          <Pressable
            testID="profile-edit-button"
            onPress={() => router.push("/edit-profile")}
            hitSlop={10}
            style={({ pressed }) => [styles.editBtn, pressed && styles.pressed]}
            accessibilityLabel="Edit profile"
          >
            <Ionicons name="pencil" size={16} color={colors.primary} />
          </Pressable>
        </View>

        {/* Quick links — entry points to user-scoped lists */}
        <View style={styles.quickLinksRow}>
          <Pressable
            testID="profile-my-events"
            onPress={() => router.push("/my-events")}
            style={({ pressed }) => [styles.quickLink, pressed && styles.pressed]}
          >
            <Ionicons name="calendar-outline" size={18} color={colors.gold} />
            <Text style={styles.quickLinkText}>My Events</Text>
            <Ionicons name="chevron-forward" size={14} color={colors.textMuted} />
          </Pressable>
          <Pressable
            testID="profile-my-journal"
            onPress={() => router.push("/journal")}
            style={({ pressed }) => [styles.quickLink, pressed && styles.pressed]}
          >
            <Ionicons name="book-outline" size={18} color={colors.gold} />
            <Text style={styles.quickLinkText}>Journal</Text>
            <Ionicons name="chevron-forward" size={14} color={colors.textMuted} />
          </Pressable>
        </View>

        <Ornament />

        {loading || !prefs ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
        ) : (
          <>
            <Text style={styles.section}>Nourishment</Text>
            <Text style={styles.label}>Dietary pattern</Text>
            <View style={styles.optionRow}>
              {DIETARY_OPTIONS.map((opt) => (
                <Pressable
                  key={opt}
                  testID={`pref-dietary-${opt}`}
                  onPress={() => update({ dietary: opt })}
                  style={[styles.optionChip, prefs.dietary === opt && styles.optionChipSel]}
                >
                  <Text style={[styles.optionText, prefs.dietary === opt && styles.optionTextSel]}>{opt}</Text>
                </Pressable>
              ))}
            </View>

            <Text style={styles.label}>Allergies / things to avoid</Text>
            <TextInput
              testID="pref-allergies-input"
              style={styles.input}
              placeholder="e.g. nuts, shellfish"
              placeholderTextColor={colors.textMuted}
              value={prefs.allergies}
              onChangeText={(t) => setPrefs({ ...prefs, allergies: t })}
              onEndEditing={() => save(prefs)}
              returnKeyType="done"
            />

            <Text style={styles.section}>Discipline</Text>
            <Text style={styles.label}>Fitness level</Text>
            <View style={styles.optionRow}>
              {LEVEL_OPTIONS.map((opt) => (
                <Pressable
                  key={opt}
                  testID={`pref-level-${opt}`}
                  onPress={() => update({ fitness_level: opt })}
                  style={[styles.optionChip, prefs.fitness_level === opt && styles.optionChipSel]}
                >
                  <Text style={[styles.optionText, prefs.fitness_level === opt && styles.optionTextSel]}>
                    {opt}
                  </Text>
                </Pressable>
              ))}
            </View>

            <Text style={styles.label}>Goal</Text>
            <TextInput
              testID="pref-goal-input"
              style={styles.input}
              placeholder="e.g. build endurance, lose weight"
              placeholderTextColor={colors.textMuted}
              value={prefs.fitness_goal}
              onChangeText={(t) => setPrefs({ ...prefs, fitness_goal: t })}
              onEndEditing={() => save(prefs)}
              returnKeyType="done"
            />

            <Text style={styles.section}>Devotion</Text>
            <Text style={styles.label}>Focus</Text>
            <TextInput
              testID="pref-devotion-input"
              style={styles.input}
              placeholder="e.g. daily Mass, rosary, Liturgy of the Hours"
              placeholderTextColor={colors.textMuted}
              value={prefs.devotion_focus}
              onChangeText={(t) => setPrefs({ ...prefs, devotion_focus: t })}
              onEndEditing={() => save(prefs)}
              returnKeyType="done"
            />

            <View style={styles.saveStatus}>
              {saving ? (
                <ActivityIndicator size="small" color={colors.gold} />
              ) : savedFlash ? (
                <>
                  <Ionicons name="checkmark-circle" size={16} color={colors.liturgical.green} />
                  <Text style={styles.savedText}>Saved</Text>
                </>
              ) : null}
            </View>
          </>
        )}

        <Text style={styles.section}>About</Text>
        <View style={styles.linkRow} testID="profile-about-links">
          <Pressable
            testID="profile-premium-link"
            onPress={() => router.push("/premium")}
            style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
          >
            <Ionicons name="ribbon-outline" size={18} color={colors.gold} />
            <Text style={styles.linkLabel}>
              {user?.is_premium ? "Sanctus Premium · Manage" : "Sanctus Premium"}
            </Text>
            <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
          </Pressable>
          <Pressable
            testID="profile-shop-link"
            onPress={() => router.push("/shop")}
            style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
          >
            <Ionicons name="basket-outline" size={18} color={colors.primary} />
            <Text style={styles.linkLabel}>Sanctus Shop</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
          </Pressable>
          <Pressable
            testID="profile-orders-link"
            onPress={() => router.push("/orders")}
            style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
          >
            <Ionicons name="receipt-outline" size={18} color={colors.primary} />
            <Text style={styles.linkLabel}>My Orders</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
          </Pressable>
          <Pressable
            testID="profile-support-link"
            onPress={() => router.push("/support")}
            style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
          >
            <Ionicons name="help-buoy-outline" size={18} color={colors.primary} />
            <Text style={styles.linkLabel}>Help &amp; Support</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
          </Pressable>
          <Pressable
            testID="profile-privacy-link"
            onPress={() => router.push("/privacy")}
            style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
          >
            <Ionicons name="lock-closed-outline" size={18} color={colors.primary} />
            <Text style={styles.linkLabel}>Privacy Policy</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
          </Pressable>
        </View>

        {user?.is_admin ? (
          <>
            <Text style={styles.section}>Admin</Text>
            <View style={styles.linkRow} testID="profile-admin-links">
              <Pressable
                testID="profile-admin-saints-link"
                onPress={() => router.push("/admin/saints")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="sparkles-outline" size={18} color={colors.gold} />
                <Text style={styles.linkLabel}>Saints · Review</Text>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </Pressable>
              <Pressable
                testID="profile-admin-shop-link"
                onPress={() => router.push("/admin/shop")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="storefront-outline" size={18} color={colors.gold} />
                <Text style={styles.linkLabel}>Shop · Admin</Text>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </Pressable>
              <Pressable
                testID="profile-admin-charities-link"
                onPress={() => router.push("/admin/charities")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="heart-circle-outline" size={18} color={colors.gold} />
                <Text style={styles.linkLabel}>Charities · Review</Text>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </Pressable>
              <Pressable
                testID="profile-admin-challenges-link"
                onPress={() => router.push("/admin/challenges")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="flame-outline" size={18} color={colors.gold} />
                <Text style={styles.linkLabel}>Challenges · Review</Text>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </Pressable>
              <Pressable
                testID="profile-admin-library-link"
                onPress={() => router.push("/admin/library")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="library-outline" size={18} color={colors.gold} />
                <Text style={styles.linkLabel}>Library · Books</Text>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </Pressable>
              <Pressable
                testID="profile-admin-library-radio-link"
                onPress={() => router.push("/admin/library-radio")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="radio-outline" size={18} color={colors.gold} />
                <Text style={styles.linkLabel}>Library · Radio</Text>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </Pressable>
              <Pressable
                testID="profile-admin-library-films-link"
                onPress={() => router.push("/admin/library-films")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="film-outline" size={18} color={colors.gold} />
                <Text style={styles.linkLabel}>Library · Films</Text>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </Pressable>
            </View>
          </>
        ) : null}

        <Pressable
          testID="sign-out-button"
          onPress={signOut}
          style={({ pressed }) => [styles.signOutBtn, pressed && styles.pressed]}
        >
          <Ionicons name="log-out-outline" size={18} color={colors.liturgical.red} />
          <Text style={styles.signOutText}>Sign out</Text>
        </Pressable>

        <Text style={styles.footer}>Ad maiorem Dei gloriam — for the greater glory of God.</Text>
        <View style={{ height: spacing.xl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

// Faith bio chips — a tiny row showing the user's tradition, path, and age.
// We only render chips for the bits the user actually filled in (everything
// is optional and defaults to null). The motivation: give people a sense of
// who they're chatting with in Community, without forcing a long bio form.
function FaithBioChips({ user }: { user: User | null | undefined }) {
  if (!user) return null;
  const labelFor = (key: string, val?: string | null): string | null => {
    if (!val) return null;
    if (key === "denomination") {
      if (val === "catholic") return "Catholic";
      if (val === "protestant") return "Protestant";
      if (val === "orthodox") return "Orthodox";
    }
    if (key === "path") {
      if (val === "convert") return "Convert";
      if (val === "revert") return "Revert";
      if (val === "cradle") return "Cradle";
    }
    return val;
  };
  const denom = labelFor("denomination", user.denomination ?? null);
  const path = labelFor("path", user.tradition_path ?? null);
  const age = user.age && user.age > 0 ? `Age ${user.age}` : null;
  const items: string[] = [denom, path, age].filter(Boolean) as string[];
  if (items.length === 0) return null;
  return (
    <View style={styles.bioChipRow} testID="profile-bio-chips">
      {items.map((label) => (
        <View key={label} style={styles.bioChip}>
          <Text style={styles.bioChipText}>{label}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  scroll: { padding: spacing.lg },
  title: { fontFamily: fonts.headingBold, fontSize: 30, color: colors.textPrimary },
  userCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginTop: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  avatar: { width: 56, height: 56, borderRadius: 28, backgroundColor: colors.borderSoft },
  avatarFallback: { alignItems: "center", justifyContent: "center", backgroundColor: colors.primary },
  avatarInitial: { fontFamily: fonts.headingBold, color: colors.gold, fontSize: 24 },
  userName: { fontFamily: fonts.headingSemi, fontSize: 20, color: colors.textPrimary },
  userEmail: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, marginTop: 2 },
  editBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.borderSoft,
  },
  section: {
    fontFamily: fonts.headingBold,
    fontSize: 22,
    color: colors.textPrimary,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  label: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 1, color: colors.textMuted, marginTop: spacing.md, marginBottom: spacing.xs },
  optionRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  optionChip: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  optionChipSel: { backgroundColor: colors.primary, borderColor: colors.primary },
  optionText: { fontFamily: fonts.uiMedium, color: colors.textPrimary, fontSize: 13 },
  optionTextSel: { color: colors.gold },
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textPrimary,
  },
  saveStatus: { flexDirection: "row", alignItems: "center", gap: spacing.xs, marginTop: spacing.md, minHeight: 20 },
  savedText: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.liturgical.green },
  signOutBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    paddingVertical: 14,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.liturgical.red,
    marginTop: spacing.xl,
  },
  signOutText: { fontFamily: fonts.uiSemi, color: colors.liturgical.red, fontSize: 15 },
  footer: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    textAlign: "center",
    color: colors.textMuted,
    fontSize: 13,
    marginTop: spacing.xl,
  },
  pressed: { opacity: 0.7 },
  linkRow: {
    flexDirection: "column",
    gap: spacing.xs,
    marginTop: spacing.sm,
  },
  linkCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: 14,
    paddingHorizontal: spacing.md,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.surface,
  },
  linkLabel: {
    flex: 1,
    fontFamily: fonts.uiSemi,
    fontSize: 14,
    color: colors.textPrimary,
  },
  quickLinksRow: {
    flexDirection: "row",
    gap: spacing.sm,
    marginTop: spacing.sm,
    marginBottom: spacing.sm,
  },
  quickLink: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: 12,
    paddingHorizontal: spacing.md,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.surface,
  },
  quickLinkText: {
    fontFamily: fonts.uiSemi,
    fontSize: 13,
    color: colors.textPrimary,
    flex: 1,
  },
  bioChipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginTop: 8,
  },
  bioChip: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.round,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.gold,
  },
  bioChipText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.primary,
    letterSpacing: 0.3,
  },
});

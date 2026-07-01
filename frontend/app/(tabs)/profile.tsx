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

import { api, User, Friendship, friendList } from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { useI18n } from "@/src/i18n";
import { AutoText } from "@/src/auto-text";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type Prefs = {
  dietary: string;
  allergies: string;
  fitness_level: string;
  fitness_goal: string;
  devotion_focus: string;
  marital_status: string;
  vocation: string;
  vocation_state: string;
};

const DIETARY_OPTIONS = ["balanced", "vegetarian", "pescetarian", "low-carb", "mediterranean"];
const LEVEL_OPTIONS = ["beginner", "intermediate", "advanced"];
const MARITAL_OPTIONS = ["single", "married"];
const VOCATION_OPTIONS = ["singleness", "religious life", "marriage"];
const VOCATION_STATE_OPTIONS = ["discerning", "living"];

export default function ProfileScreen() {
  const { user, signOut } = useAuth();
  const { t, lang, setLang } = useI18n();
  const router = useRouter();
  const [prefs, setPrefs] = useState<Prefs | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedFlash, setSavedFlash] = useState(false);
  const [friends, setFriends] = useState<Friendship[]>([]);
  const [incomingCount, setIncomingCount] = useState(0);

  const loadFriends = useCallback(async () => {
    try {
      const [acc, inc] = await Promise.all([
        friendList("accepted"),
        friendList("incoming"),
      ]);
      setFriends(acc.items);
      setIncomingCount(inc.count);
    } catch (e) {
      console.warn("load friends failed", e);
    }
  }, []);

  useEffect(() => {
    loadFriends();
  }, [loadFriends]);

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
        <Text style={styles.title}>{t("profile.title")}</Text>
        <View style={styles.userCard} testID="user-card">
          {user?.picture ? (
            <Image source={{ uri: user.picture }} style={styles.avatar} />
          ) : (
            <View style={[styles.avatar, styles.avatarFallback]}>
              <Text style={styles.avatarInitial}>{user?.name?.[0]?.toUpperCase() ?? "?"}</Text>
            </View>
          )}
          <View style={{ flex: 1 }}>
            <Text style={styles.userName}>{user?.name ?? t("profile.defaultName")}</Text>
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
            <Text style={styles.quickLinkText}>{t("profile.myEvents")}</Text>
            <Ionicons name="chevron-forward" size={14} color={colors.textMuted} />
          </Pressable>
          <Pressable
            testID="profile-my-journal"
            onPress={() => router.push("/journal")}
            style={({ pressed }) => [styles.quickLink, pressed && styles.pressed]}
          >
            <Ionicons name="book-outline" size={18} color={colors.gold} />
            <Text style={styles.quickLinkText}>{t("profile.journal")}</Text>
            <Ionicons name="chevron-forward" size={14} color={colors.textMuted} />
          </Pressable>
        </View>

        <Ornament />

        {/* Friends */}
        <View style={styles.friendsHeaderRow}>
          <Text style={styles.section}>Friends</Text>
          <Pressable
            testID="profile-friends-manage"
            onPress={() => router.push("/community/people")}
            hitSlop={8}
            style={({ pressed }) => [styles.manageBtn, pressed && styles.pressed]}
          >
            <Text style={styles.manageText}>
              {incomingCount > 0 ? `${incomingCount} request${incomingCount > 1 ? "s" : ""}` : "Find friends"}
            </Text>
            <Ionicons name="chevron-forward" size={14} color={colors.gold} />
          </Pressable>
        </View>
        {friends.length === 0 ? (
          <Text style={styles.friendsEmpty} testID="profile-friends-empty">
            No friends yet. Tap “Find friends” to connect with fellow faithful.
          </Text>
        ) : (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.friendsRow}
            testID="profile-friends-list"
          >
            {friends.map((f) =>
              f.user ? (
                <Pressable
                  key={f.friendship_id}
                  testID={`profile-friend-${f.user.user_id}`}
                  onPress={() =>
                    router.push({ pathname: "/community/user/[id]", params: { id: f.user!.user_id } })
                  }
                  style={({ pressed }) => [styles.friendChip, pressed && styles.pressed]}
                >
                  {f.user.picture ? (
                    <Image source={{ uri: f.user.picture }} style={styles.friendAvatar} />
                  ) : (
                    <View style={[styles.friendAvatar, styles.avatarFallback]}>
                      <Text style={styles.avatarInitial}>{f.user.name?.[0]?.toUpperCase() ?? "?"}</Text>
                    </View>
                  )}
                  <Text style={styles.friendName} numberOfLines={1}>
                    {f.user.name}
                  </Text>
                </Pressable>
              ) : null,
            )}
          </ScrollView>
        )}

        {loading || !prefs ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
        ) : (
          <>
            <Text style={styles.section}>{t("profile.nourishment")}</Text>
            <Text style={styles.label}>{t("profile.dietary")}</Text>
            <View style={styles.optionRow}>
              {DIETARY_OPTIONS.map((opt) => (
                <Pressable
                  key={opt}
                  testID={`pref-dietary-${opt}`}
                  onPress={() => update({ dietary: opt })}
                  style={[styles.optionChip, prefs.dietary === opt && styles.optionChipSel]}
                >
                  <AutoText style={[styles.optionText, prefs.dietary === opt && styles.optionTextSel]}>{opt}</AutoText>
                </Pressable>
              ))}
            </View>

            <Text style={styles.label}>{t("profile.allergies")}</Text>
            <TextInput
              testID="pref-allergies-input"
              style={styles.input}
              placeholder={t("profile.allergiesPh")}
              placeholderTextColor={colors.textMuted}
              value={prefs.allergies}
              onChangeText={(t) => setPrefs({ ...prefs, allergies: t })}
              onEndEditing={() => save(prefs)}
              returnKeyType="done"
            />

            <AutoText style={styles.section}>Your Walk with Christ</AutoText>
            <View style={{ flexDirection: "row", gap: 6, alignItems: "flex-start", backgroundColor: colors.borderSoft, borderRadius: radius.md, padding: spacing.sm, marginBottom: spacing.sm }}>
              <Ionicons name="lock-closed" size={13} color={colors.textMuted} />
              <AutoText style={{ flex: 1, fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textSecondary, lineHeight: 17 }}>
                Private — only you can see this. We use it to tailor better habits and ideas for your personal walk with Christ.
              </AutoText>
            </View>
            <AutoText style={styles.label}>Marital status</AutoText>
            <View style={styles.optionRow}>
              {MARITAL_OPTIONS.map((opt) => (
                <Pressable
                  key={opt}
                  testID={`pref-marital-${opt}`}
                  onPress={() => update({ marital_status: opt })}
                  style={[styles.optionChip, prefs.marital_status === opt && styles.optionChipSel]}
                >
                  <AutoText style={[styles.optionText, prefs.marital_status === opt && styles.optionTextSel]}>{opt}</AutoText>
                </Pressable>
              ))}
            </View>
            <AutoText style={styles.label}>Vocation</AutoText>
            <View style={styles.optionRow}>
              {VOCATION_OPTIONS.map((opt) => (
                <Pressable
                  key={opt}
                  testID={`pref-vocation-${opt.replace(/\s+/g, "-")}`}
                  onPress={() => update({ vocation: opt })}
                  style={[styles.optionChip, prefs.vocation === opt && styles.optionChipSel]}
                >
                  <AutoText style={[styles.optionText, prefs.vocation === opt && styles.optionTextSel]}>{opt}</AutoText>
                </Pressable>
              ))}
            </View>
            {prefs.vocation ? (
              <>
                <AutoText style={styles.label}>Are you discerning or living this?</AutoText>
                <View style={styles.optionRow}>
                  {VOCATION_STATE_OPTIONS.map((opt) => (
                    <Pressable
                      key={opt}
                      testID={`pref-vstate-${opt}`}
                      onPress={() => update({ vocation_state: opt })}
                      style={[styles.optionChip, (prefs.vocation_state || "living") === opt && styles.optionChipSel]}
                    >
                      <AutoText style={[styles.optionText, (prefs.vocation_state || "living") === opt && styles.optionTextSel]}>{opt}</AutoText>
                    </Pressable>
                  ))}
                </View>
              </>
            ) : null}

            <Text style={styles.section}>{t("profile.discipline")}</Text>
            <Text style={styles.label}>{t("profile.fitnessLevel")}</Text>
            <View style={styles.optionRow}>
              {LEVEL_OPTIONS.map((opt) => (
                <Pressable
                  key={opt}
                  testID={`pref-level-${opt}`}
                  onPress={() => update({ fitness_level: opt })}
                  style={[styles.optionChip, prefs.fitness_level === opt && styles.optionChipSel]}
                >
                  <AutoText style={[styles.optionText, prefs.fitness_level === opt && styles.optionTextSel]}>
                    {opt}
                  </AutoText>
                </Pressable>
              ))}
            </View>

            <Text style={styles.label}>{t("profile.goal")}</Text>
            <TextInput
              testID="pref-goal-input"
              style={styles.input}
              placeholder={t("profile.goalPh")}
              placeholderTextColor={colors.textMuted}
              value={prefs.fitness_goal}
              onChangeText={(t) => setPrefs({ ...prefs, fitness_goal: t })}
              onEndEditing={() => save(prefs)}
              returnKeyType="done"
            />

            <Text style={styles.section}>{t("profile.devotion")}</Text>
            <Text style={styles.label}>{t("profile.focus")}</Text>
            <TextInput
              testID="pref-devotion-input"
              style={styles.input}
              placeholder={t("profile.focusPh")}
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
                  <Text style={styles.savedText}>{t("profile.saved")}</Text>
                </>
              ) : null}
            </View>
          </>
        )}

        <Text style={styles.section}>{t("settings.language")}</Text>
        <Text style={styles.label}>{t("settings.languageHint")}</Text>
        <View style={styles.optionRow} testID="profile-language">
          {(["en", "es"] as const).map((l) => (
            <Pressable
              key={l}
              testID={`lang-${l}`}
              onPress={() => setLang(l)}
              style={[styles.optionChip, lang === l && styles.optionChipSel]}
            >
              <Text style={[styles.optionText, lang === l && styles.optionTextSel]}>
                {l === "en" ? "English" : "Español"}
              </Text>
            </Pressable>
          ))}
        </View>

        <Text style={styles.section}>{t("profile.about")}</Text>
        <View style={styles.linkRow} testID="profile-about-links">
          <Pressable
            testID="profile-premium-link"
            onPress={() => router.push("/premium")}
            style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
          >
            <Ionicons name="ribbon-outline" size={18} color={colors.gold} />
            <Text style={styles.linkLabel}>
              {user?.is_premium ? t("profile.premiumManage") : t("profile.premium")}
            </Text>
            <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
          </Pressable>
          <Pressable
            testID="profile-shop-link"
            onPress={() => router.push("/shop")}
            style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
          >
            <Ionicons name="basket-outline" size={18} color={colors.primary} />
            <Text style={styles.linkLabel}>{t("profile.shop")}</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
          </Pressable>
          <Pressable
            testID="profile-orders-link"
            onPress={() => router.push("/orders")}
            style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
          >
            <Ionicons name="receipt-outline" size={18} color={colors.primary} />
            <Text style={styles.linkLabel}>{t("profile.orders")}</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
          </Pressable>
          <Pressable
            testID="profile-support-link"
            onPress={() => router.push("/support")}
            style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
          >
            <Ionicons name="help-buoy-outline" size={18} color={colors.primary} />
            <Text style={styles.linkLabel}>{t("profile.support")}</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
          </Pressable>
          <Pressable
            testID="profile-privacy-link"
            onPress={() => router.push("/privacy")}
            style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
          >
            <Ionicons name="lock-closed-outline" size={18} color={colors.primary} />
            <Text style={styles.linkLabel}>{t("profile.privacy")}</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
          </Pressable>
        </View>

        {user?.is_admin ? (
          <>
            <AutoText style={styles.section}>Admin</AutoText>
            <View style={styles.linkRow} testID="profile-admin-links">
              <Pressable
                testID="profile-admin-saints-link"
                onPress={() => router.push("/admin/saints")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="sparkles-outline" size={18} color={colors.gold} />
                <AutoText style={styles.linkLabel}>Saints · Review</AutoText>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </Pressable>
              <Pressable
                testID="profile-admin-shop-link"
                onPress={() => router.push("/admin/shop")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="storefront-outline" size={18} color={colors.gold} />
                <AutoText style={styles.linkLabel}>Shop · Admin</AutoText>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </Pressable>
              <Pressable
                testID="profile-admin-charities-link"
                onPress={() => router.push("/admin/charities")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="heart-circle-outline" size={18} color={colors.gold} />
                <AutoText style={styles.linkLabel}>Charities · Review</AutoText>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </Pressable>
              <Pressable
                testID="profile-admin-challenges-link"
                onPress={() => router.push("/admin/challenges")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="flame-outline" size={18} color={colors.gold} />
                <AutoText style={styles.linkLabel}>Challenges · Review</AutoText>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </Pressable>
              <Pressable
                testID="profile-admin-library-link"
                onPress={() => router.push("/admin/library")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="library-outline" size={18} color={colors.gold} />
                <AutoText style={styles.linkLabel}>Library · Books</AutoText>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </Pressable>
              <Pressable
                testID="profile-admin-library-radio-link"
                onPress={() => router.push("/admin/library-radio")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="radio-outline" size={18} color={colors.gold} />
                <AutoText style={styles.linkLabel}>Library · Radio</AutoText>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </Pressable>
              <Pressable
                testID="profile-admin-library-films-link"
                onPress={() => router.push("/admin/library-films")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="film-outline" size={18} color={colors.gold} />
                <AutoText style={styles.linkLabel}>Library · Films</AutoText>
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </Pressable>
              <Pressable
                testID="profile-admin-miracles-link"
                onPress={() => router.push("/admin/miracles")}
                style={({ pressed }) => [styles.linkCard, pressed && styles.pressed]}
              >
                <Ionicons name="sparkles-outline" size={18} color={colors.gold} />
                <AutoText style={styles.linkLabel}>Miracles · Review</AutoText>
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
          <Text style={styles.signOutText}>{t("profile.signOut")}</Text>
        </Pressable>

        <Text style={styles.footer}>{t("profile.footer")}</Text>
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
  friendsHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  manageBtn: { flexDirection: "row", alignItems: "center", gap: 2 },
  manageText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold },
  friendsEmpty: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 20,
    marginBottom: spacing.sm,
  },
  friendsRow: { gap: spacing.md, paddingVertical: spacing.xs, paddingRight: spacing.lg },
  friendChip: { alignItems: "center", width: 68 },
  friendAvatar: { width: 56, height: 56, borderRadius: 28, backgroundColor: colors.surface },
  friendName: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textPrimary,
    marginTop: 4,
    textAlign: "center",
    width: 68,
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

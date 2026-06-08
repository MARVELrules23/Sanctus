import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  KeyboardAvoidingView,
  Linking,
  Platform,
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
import * as ImagePicker from "expo-image-picker";

import { updateMe } from "@/src/api";
import { useAuth } from "@/src/auth-context";
import Ornament from "@/src/components/Ornament";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

export default function EditProfileScreen() {
  const router = useRouter();
  const { user, setUser } = useAuth();
  const [name, setName] = useState<string>(user?.name ?? "");
  const [picture, setPicture] = useState<string | null>(user?.picture ?? null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pickingPic, setPickingPic] = useState(false);

  useEffect(() => {
    if (user) {
      setName(user.name ?? "");
      setPicture(user.picture ?? null);
    }
  }, [user]);

  const trimmedName = name.trim();
  const isValid = trimmedName.length >= 1 && trimmedName.length <= 60;

  const onPickImage = async () => {
    if (pickingPic) return;
    setPickingPic(true);
    try {
      // Pre-permission explanation: explicit contextual ask.
      const perm = await ImagePicker.getMediaLibraryPermissionsAsync();
      let status = perm.status;
      let canAskAgain = perm.canAskAgain;
      if (status !== "granted") {
        if (canAskAgain) {
          const req = await ImagePicker.requestMediaLibraryPermissionsAsync();
          status = req.status;
          canAskAgain = req.canAskAgain;
        }
      }
      if (status !== "granted") {
        if (!canAskAgain) {
          Alert.alert(
            "Photos permission needed",
            "Sanctus needs access to your photos to set a profile picture.",
            [
              { text: "Cancel", style: "cancel" },
              { text: "Open Settings", onPress: () => Linking.openSettings() },
            ],
          );
        }
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.7,
        base64: true,
      });
      if (result.canceled || !result.assets?.length) return;
      const asset = result.assets[0];
      let uri = asset.uri;
      if (asset.base64) {
        const mime = asset.mimeType || "image/jpeg";
        uri = `data:${mime};base64,${asset.base64}`;
      }
      // Hard guard: 2MB cap (server caps too).
      if (uri.startsWith("data:") && uri.length > 2_800_000) {
        Alert.alert("Image too large", "Please pick a smaller photo (max ~2 MB).");
        return;
      }
      setPicture(uri);
      setDirty(true);
    } catch (e) {
      console.warn("image pick failed", e);
      Alert.alert("Could not load that photo", "Please try a different one.");
    } finally {
      setPickingPic(false);
    }
  };

  const onRemovePic = () => {
    setPicture(null);
    setDirty(true);
  };

  const onSave = async () => {
    if (!isValid || saving) return;
    setSaving(true);
    try {
      const updated = await updateMe({ name: trimmedName, picture });
      setUser(updated);
      router.back();
    } catch (e: any) {
      console.warn("save profile failed", e);
      Alert.alert("Couldn't save", e?.message || "Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const onCancel = () => router.back();

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="edit-profile-screen">
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={{ flex: 1 }}
      >
        <View style={styles.header}>
          <Pressable
            testID="edit-profile-cancel"
            onPress={onCancel}
            hitSlop={12}
            style={({ pressed }) => pressed && styles.pressed}
          >
            <Ionicons name="chevron-back" size={26} color={colors.primary} />
          </Pressable>
          <Text style={styles.headerTitle}>Edit Profile</Text>
          <Pressable
            testID="edit-profile-save"
            onPress={onSave}
            disabled={!isValid || !dirty || saving}
            hitSlop={12}
            style={({ pressed }) => [
              styles.saveTopBtn,
              (!isValid || !dirty) && styles.saveTopBtnDisabled,
              pressed && styles.pressed,
            ]}
          >
            {saving ? (
              <ActivityIndicator color={colors.gold} />
            ) : (
              <Text
                style={[
                  styles.saveTopText,
                  (!isValid || !dirty) && styles.saveTopTextDisabled,
                ]}
              >
                Save
              </Text>
            )}
          </Pressable>
        </View>

        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={styles.avatarWrap}>
            <Pressable
              testID="edit-profile-avatar"
              onPress={onPickImage}
              style={({ pressed }) => [styles.avatarPress, pressed && styles.pressed]}
              accessibilityLabel="Change profile picture"
            >
              {picture ? (
                <Image source={{ uri: picture }} style={styles.avatar} />
              ) : (
                <View style={[styles.avatar, styles.avatarFallback]}>
                  <Text style={styles.avatarInitial}>
                    {trimmedName?.[0]?.toUpperCase() ?? "?"}
                  </Text>
                </View>
              )}
              <View style={styles.avatarBadge}>
                {pickingPic ? (
                  <ActivityIndicator size="small" color={colors.gold} />
                ) : (
                  <Ionicons name="camera" size={16} color={colors.gold} />
                )}
              </View>
            </Pressable>
            <Pressable
              testID="edit-profile-change-photo"
              onPress={onPickImage}
              disabled={pickingPic}
              style={({ pressed }) => [styles.linkBtn, pressed && styles.pressed]}
            >
              <Text style={styles.linkText}>
                {picture ? "Change photo" : "Add a photo"}
              </Text>
            </Pressable>
            {picture ? (
              <Pressable
                testID="edit-profile-remove-photo"
                onPress={onRemovePic}
                style={({ pressed }) => [styles.linkBtn, pressed && styles.pressed]}
              >
                <Text style={[styles.linkText, styles.removeLink]}>Remove photo</Text>
              </Pressable>
            ) : null}
          </View>

          <Ornament />

          <Text style={styles.label}>Display name</Text>
          <TextInput
            testID="edit-profile-name-input"
            style={styles.input}
            value={name}
            onChangeText={(t) => {
              setName(t);
              setDirty(true);
            }}
            placeholder="Your name"
            placeholderTextColor={colors.textMuted}
            maxLength={60}
            autoCapitalize="words"
            returnKeyType="done"
          />
          <Text style={styles.help}>
            {trimmedName.length === 0
              ? "Required"
              : `${trimmedName.length}/60`}
          </Text>

          <Text style={styles.label}>Email</Text>
          <View style={[styles.input, styles.inputDisabled]}>
            <Text style={styles.inputDisabledText}>{user?.email ?? ""}</Text>
          </View>
          <Text style={styles.help}>Linked to your Google sign-in.</Text>

          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      </KeyboardAvoidingView>
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
    backgroundColor: colors.background,
    gap: spacing.md,
  },
  headerTitle: {
    flex: 1,
    fontFamily: fonts.headingSemi,
    fontSize: 20,
    color: colors.textPrimary,
    textAlign: "center",
    marginRight: spacing.lg, // visually center vs back chevron width
  },
  saveTopBtn: {
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
    minWidth: 64,
    alignItems: "center",
  },
  saveTopBtnDisabled: { backgroundColor: colors.border },
  saveTopText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 14 },
  saveTopTextDisabled: { color: colors.textMuted },
  scroll: { padding: spacing.lg },
  avatarWrap: { alignItems: "center", marginBottom: spacing.lg },
  avatarPress: { position: "relative" },
  avatar: { width: 112, height: 112, borderRadius: 56, backgroundColor: colors.borderSoft },
  avatarFallback: { alignItems: "center", justifyContent: "center", backgroundColor: colors.primary },
  avatarInitial: { fontFamily: fonts.headingBold, color: colors.gold, fontSize: 44 },
  avatarBadge: {
    position: "absolute",
    bottom: 2,
    right: 2,
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    borderColor: colors.background,
  },
  linkBtn: { marginTop: spacing.sm, paddingVertical: 4 },
  linkText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.primary },
  removeLink: { color: colors.liturgical.red },
  label: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    letterSpacing: 1,
    color: colors.textMuted,
    marginTop: spacing.lg,
    marginBottom: spacing.xs,
  },
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.md,
    paddingVertical: 14,
    fontFamily: fonts.bodyRegular,
    fontSize: 16,
    color: colors.textPrimary,
    ...shadow.card,
  },
  inputDisabled: { backgroundColor: colors.borderSoft, borderColor: colors.borderSoft },
  inputDisabledText: { fontFamily: fonts.bodyRegular, fontSize: 16, color: colors.textSecondary },
  help: { fontFamily: fonts.bodyRegular, fontSize: 12, color: colors.textMuted, marginTop: 6 },
  pressed: { opacity: 0.7 },
});

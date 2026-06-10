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
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { CharityCategoryLabel, getCharityCategories, submitCharity } from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

export default function SubmitCharity() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [mission, setMission] = useState("");
  const [categories, setCategories] = useState<CharityCategoryLabel[]>([]);
  const [category, setCategory] = useState<string>("general");
  const [city, setCity] = useState("");
  const [state, setStateFld] = useState("");
  const [country, setCountry] = useState("US");
  const [website, setWebsite] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [picking, setPicking] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getCharityCategories().then((r) => setCategories(r.categories)).catch(() => {});
  }, []);

  const pickLogo = async () => {
    if (picking) return;
    setPicking(true);
    try {
      const perm = await ImagePicker.getMediaLibraryPermissionsAsync();
      let status = perm.status; let canAskAgain = perm.canAskAgain;
      if (status !== "granted") {
        if (canAskAgain) {
          const r = await ImagePicker.requestMediaLibraryPermissionsAsync();
          status = r.status; canAskAgain = r.canAskAgain;
        }
      }
      if (status !== "granted") {
        if (!canAskAgain) {
          Alert.alert("Photos permission needed", "Allow photo access to attach a logo.", [
            { text: "Cancel", style: "cancel" },
            { text: "Open Settings", onPress: () => Linking.openSettings() },
          ]);
        }
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, allowsEditing: true, aspect: [1, 1], quality: 0.7, base64: true });
      if (result.canceled || !result.assets?.length) return;
      const a = result.assets[0];
      let uri = a.uri;
      if (a.base64) uri = `data:${a.mimeType || "image/jpeg"};base64,${a.base64}`;
      if (uri.startsWith("data:") && uri.length > 2_800_000) { Alert.alert("Image too large", "Pick a smaller logo (max ~2 MB)."); return; }
      setLogoUrl(uri);
    } catch (e) { console.warn("pick logo failed", e); }
    finally { setPicking(false); }
  };

  const onSubmit = async () => {
    if (name.trim().length < 2) { Alert.alert("Name required", "Please enter the charity name."); return; }
    if (mission.trim().length < 10) { Alert.alert("Mission required", "Briefly describe what this charity does."); return; }
    setSubmitting(true);
    try {
      const created = await submitCharity({
        name: name.trim(),
        mission: mission.trim(),
        category,
        city: city.trim(),
        state: state.trim(),
        country: country.trim().toUpperCase() || "US",
        website: website.trim() || null,
        email: email.trim() || null,
        phone: phone.trim() || null,
        logo_url: logoUrl,
      });
      // Navigate first so the redirect works on all platforms (the Alert OK
      // callback does not fire on react-native-web — we can't rely on it).
      router.replace("/charities");
      Alert.alert(
        created.status === "approved" ? "Published" : "Submitted",
        created.status === "approved"
          ? "Live in the charity hub now."
          : "Thanks! Once an admin approves it, it will appear in the charity hub.",
      );
    } catch (e: any) {
      Alert.alert("Couldn't submit", e?.message || "Try again.");
    } finally { setSubmitting(false); }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.headerBtn}><Ionicons name="chevron-back" size={24} color={colors.primary} /></Pressable>
        <Text style={styles.headerTitle}>Add a charity</Text>
        <Pressable onPress={onSubmit} disabled={submitting} hitSlop={10} style={styles.headerBtn}>
          {submitting ? <ActivityIndicator color={colors.primary} /> : <Text style={styles.saveText}>Submit</Text>}
        </Pressable>
      </View>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.scroll}>
          <Text style={styles.hint}>Help fellow Catholics find places to volunteer. Your submission will be reviewed before it appears publicly.</Text>

          <Text style={styles.label}>Charity name *</Text>
          <TextInput value={name} onChangeText={setName} style={styles.input} placeholder="St. Vincent de Paul Society" placeholderTextColor={colors.textMuted} />

          <Text style={styles.label}>Mission *</Text>
          <TextInput value={mission} onChangeText={setMission} style={[styles.input, { minHeight: 100 }]} multiline placeholder="What does this charity do? Who do they serve?" placeholderTextColor={colors.textMuted} />

          <Text style={styles.label}>Category</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipsRow}>
            {categories.map((c) => (
              <Pressable key={c.key} onPress={() => setCategory(c.key)} style={[styles.chip, category === c.key && styles.chipActive]}>
                <Text style={[styles.chipText, category === c.key && styles.chipTextActive]}>{c.label}</Text>
              </Pressable>
            ))}
          </ScrollView>

          <Text style={styles.label}>Logo (optional)</Text>
          {logoUrl ? (
            <View style={styles.logoWrap}>
              <Image source={{ uri: logoUrl }} style={styles.logoPreview} resizeMode="cover" />
              <Pressable onPress={() => setLogoUrl(null)} style={styles.logoClear}><Ionicons name="close" size={16} color="#fff" /></Pressable>
            </View>
          ) : null}
          <Pressable onPress={pickLogo} disabled={picking} style={({ pressed }) => [styles.pickerBtn, pressed && { opacity: 0.8 }]}>
            {picking ? <ActivityIndicator size="small" color={colors.primary} /> : <Ionicons name="image-outline" size={16} color={colors.primary} />}
            <Text style={styles.pickerBtnText}>{logoUrl ? "Replace from library" : "Upload from library"}</Text>
          </Pressable>

          <View style={styles.row2}>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>City</Text>
              <TextInput value={city} onChangeText={setCity} style={styles.input} placeholder="San Francisco" placeholderTextColor={colors.textMuted} />
            </View>
            <View style={{ width: 110 }}>
              <Text style={styles.label}>State</Text>
              <TextInput value={state} onChangeText={setStateFld} style={styles.input} placeholder="CA" placeholderTextColor={colors.textMuted} autoCapitalize="characters" />
            </View>
          </View>

          <Text style={styles.label}>Country</Text>
          <TextInput value={country} onChangeText={(v) => setCountry(v.toUpperCase().slice(0, 4))} style={styles.input} placeholder="US" placeholderTextColor={colors.textMuted} autoCapitalize="characters" />

          <Text style={styles.label}>Website</Text>
          <TextInput value={website} onChangeText={setWebsite} style={styles.input} placeholder="https://..." placeholderTextColor={colors.textMuted} autoCapitalize="none" keyboardType="url" />

          <Text style={styles.label}>Contact email</Text>
          <TextInput value={email} onChangeText={setEmail} style={styles.input} placeholder="info@charity.org" placeholderTextColor={colors.textMuted} autoCapitalize="none" keyboardType="email-address" />

          <Text style={styles.label}>Phone</Text>
          <TextInput value={phone} onChangeText={setPhone} style={styles.input} placeholder="(415) 555-0123" placeholderTextColor={colors.textMuted} keyboardType="phone-pad" />

          <Pressable onPress={onSubmit} disabled={submitting} style={({ pressed }) => [styles.submitBtn, pressed && { opacity: 0.85 }, submitting && { opacity: 0.6 }]}>
            {submitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.submitText}>Submit for review</Text>}
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, backgroundColor: colors.surface },
  headerBtn: { padding: spacing.xs, width: 60, alignItems: "center" },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingBold, fontSize: 18, color: colors.primary },
  saveText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.primary },
  scroll: { padding: spacing.md, gap: spacing.sm, paddingBottom: spacing.xxl },
  hint: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary, lineHeight: 19, marginBottom: spacing.sm },
  label: { marginTop: spacing.sm, fontFamily: fonts.uiSemi, fontSize: 11, color: colors.textMuted, textTransform: "uppercase" },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, padding: 12, fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary, backgroundColor: colors.surface, textAlignVertical: "top" },
  row2: { flexDirection: "row", gap: 8, alignItems: "flex-start" },
  chipsRow: { paddingVertical: 4, gap: 6 },
  chip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: radius.round, backgroundColor: colors.background, borderWidth: 1, borderColor: colors.borderSoft },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textSecondary },
  chipTextActive: { color: "#fff" },
  logoWrap: { position: "relative", marginTop: 4 },
  logoPreview: { width: 120, height: 120, borderRadius: radius.lg, backgroundColor: colors.surface },
  logoClear: { position: "absolute", top: 6, right: 6, width: 26, height: 26, borderRadius: 13, backgroundColor: "rgba(0,0,0,0.55)", alignItems: "center", justifyContent: "center" },
  pickerBtn: { flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 14, paddingVertical: 10, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.background, alignSelf: "flex-start", marginTop: 6 },
  pickerBtnText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.primary },
  submitBtn: { marginTop: spacing.lg, paddingVertical: 14, borderRadius: radius.round, backgroundColor: colors.primary, alignItems: "center" },
  submitText: { fontFamily: fonts.uiSemi, fontSize: 14, color: "#fff" },
});

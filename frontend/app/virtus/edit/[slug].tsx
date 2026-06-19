/**
 * Virtus — admin content editor.
 *
 * Admin-only. Loads the full virtue content (incl. resources) and lets the
 * founder edit the prose fields, plus the saints/resources lists as JSON.
 * Also offers an AI "Regenerate" action.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
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
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import {
  adminEditVirtue,
  adminGetVirtue,
  adminRegenerateVirtue,
  VirtueContent,
} from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

function Field({ label, value, onChange, lines = 6 }: { label: string; value: string; onChange: (s: string) => void; lines?: number }) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChange}
        style={[styles.input, { minHeight: lines * 20 }]}
        multiline
        placeholderTextColor={colors.textMuted}
      />
    </View>
  );
}

export default function VirtueEditScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const router = useRouter();
  const [data, setData] = useState<VirtueContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [regenning, setRegenning] = useState(false);

  // editable fields
  const [whatIs, setWhatIs] = useState("");
  const [single, setSingle] = useState("");
  const [dating, setDating] = useState("");
  const [marriage, setMarriage] = useState("");
  const [overcoming, setOvercoming] = useState("");
  const [intro, setIntro] = useState("");
  const [saintsJson, setSaintsJson] = useState("");
  const [saintsByVirtueJson, setSaintsByVirtueJson] = useState("");
  const [resourcesJson, setResourcesJson] = useState("");

  const hydrate = (d: VirtueContent) => {
    setData(d);
    setWhatIs(d.what_is || "");
    setSingle(d.life_stages?.singleness || "");
    setDating(d.life_stages?.dating || "");
    setMarriage(d.life_stages?.marriage || "");
    setOvercoming(d.overcoming_vice || "");
    setIntro(d.intro || "");
    setSaintsJson(JSON.stringify(d.saints || [], null, 2));
    setSaintsByVirtueJson(JSON.stringify(d.saints_by_virtue || [], null, 2));
    setResourcesJson(JSON.stringify(d.resources || [], null, 2));
  };

  const load = useCallback(async () => {
    if (!slug) return;
    setLoading(true);
    setError(null);
    try {
      hydrate(await adminGetVirtue(slug));
    } catch (e: any) {
      setError(e?.status === 403 ? "Admins only." : (e?.message || "Could not load."));
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => { void load(); }, [load]);

  const save = async () => {
    if (!slug || saving || !data) return;
    setSaving(true);
    try {
      const body: any = {};
      if (data.kind === "saints") {
        body.intro = intro;
        try { body.saints_by_virtue = JSON.parse(saintsByVirtueJson); } catch { Alert.alert("Invalid JSON", "Saints-by-virtue is not valid JSON."); setSaving(false); return; }
      } else {
        body.what_is = whatIs;
        body.life_stages = { singleness: single, dating: dating, marriage: marriage };
        body.overcoming_vice = overcoming;
        try { body.saints = JSON.parse(saintsJson); } catch { Alert.alert("Invalid JSON", "Saints is not valid JSON."); setSaving(false); return; }
      }
      try { body.resources = JSON.parse(resourcesJson); } catch { Alert.alert("Invalid JSON", "Resources is not valid JSON."); setSaving(false); return; }
      const updated = await adminEditVirtue(slug, body);
      hydrate(updated);
      Alert.alert("Saved", "Your changes are live.");
    } catch (e: any) {
      Alert.alert("Save failed", e?.message || "Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const regenerate = () => {
    Alert.alert("Regenerate with AI?", "This replaces the current content with a fresh AI draft.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Regenerate",
        onPress: async () => {
          if (!slug) return;
          setRegenning(true);
          try {
            hydrate(await adminRegenerateVirtue(slug));
            Alert.alert("Done", "Fresh draft generated. Review and Save.");
          } catch (e: any) {
            Alert.alert("Failed", e?.message || "Please try again.");
          } finally {
            setRegenning(false);
          }
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="virtus-edit-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.headerTitle} numberOfLines={1}>Edit · {data?.name || slug}</Text>
        </View>
        <Pressable testID="virtus-edit-regenerate" onPress={regenerate} hitSlop={10} disabled={regenning}>
          {regenning ? <ActivityIndicator size="small" color={colors.gold} /> : <Ionicons name="refresh" size={20} color={colors.gold} />}
        </Pressable>
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.gold} /></View>
      ) : error ? (
        <View style={styles.center}><Text style={styles.errorText}>{error}</Text></View>
      ) : (
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
          <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
            {data?.kind === "saints" ? (
              <>
                <Field label="Intro" value={intro} onChange={setIntro} lines={5} />
                <Field label="Saints by virtue (JSON)" value={saintsByVirtueJson} onChange={setSaintsByVirtueJson} lines={14} />
              </>
            ) : (
              <>
                <Field label="What is it?" value={whatIs} onChange={setWhatIs} lines={8} />
                <Field label="Singleness" value={single} onChange={setSingle} lines={5} />
                <Field label="Dating" value={dating} onChange={setDating} lines={5} />
                <Field label="Marriage" value={marriage} onChange={setMarriage} lines={5} />
                <Field label="Overcoming the vice" value={overcoming} onChange={setOvercoming} lines={7} />
                <Field label="Saints (JSON)" value={saintsJson} onChange={setSaintsJson} lines={10} />
              </>
            )}
            <Field label="Resources — Premium (JSON)" value={resourcesJson} onChange={setResourcesJson} lines={10} />

            <Pressable
              testID="virtus-edit-save"
              onPress={save}
              disabled={saving}
              style={({ pressed }) => [styles.saveBtn, saving && { opacity: 0.6 }, pressed && { opacity: 0.85 }]}
            >
              {saving ? <ActivityIndicator size="small" color={colors.gold} /> : (
                <>
                  <Ionicons name="save-outline" size={16} color={colors.gold} />
                  <Text style={styles.saveText}>Save changes</Text>
                </>
              )}
            </Pressable>
            <View style={{ height: spacing.xxl }} />
          </ScrollView>
        </KeyboardAvoidingView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row", alignItems: "center",
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
    borderBottomWidth: 1, borderBottomColor: colors.borderSoft, gap: spacing.md,
  },
  headerTitleWrap: { flex: 1, alignItems: "center" },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 17, color: colors.textPrimary },
  scroll: { padding: spacing.lg, gap: spacing.md },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl },
  errorText: { fontFamily: fonts.bodyRegular, color: colors.textSecondary, textAlign: "center" },

  field: { gap: 6 },
  fieldLabel: { fontFamily: fonts.uiSemi, fontSize: 11, letterSpacing: 0.8, color: colors.textMuted },
  input: {
    borderWidth: 1, borderColor: colors.borderSoft, borderRadius: radius.md,
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
    fontFamily: fonts.bodyRegular, fontSize: 13, lineHeight: 19,
    color: colors.textPrimary, backgroundColor: colors.surface, textAlignVertical: "top",
  },
  saveBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
    marginTop: spacing.md, paddingVertical: 13, borderRadius: radius.round, backgroundColor: colors.primary,
    ...shadow.card,
  },
  saveText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.gold, letterSpacing: 0.4 },
});

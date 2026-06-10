import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import {
  LibraryStation,
  LibraryStationCreate,
  adminCreateLibraryStation,
  adminDeleteLibraryStation,
  adminListLibraryStations,
  adminPatchLibraryStation,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const BLANK: LibraryStationCreate = {
  slug: "",
  name: "",
  blurb: "",
  country: "",
  language: "English",
  stream_url: "",
  website_url: "",
  accent_color: "#B8860B",
  icon: "radio-outline",
  status: "published",
};

export default function AdminLibraryRadioScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [items, setItems] = useState<LibraryStation[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<LibraryStation | null>(null);
  const [draft, setDraft] = useState<LibraryStationCreate>(BLANK);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!user?.is_admin) return;
    setLoading(true);
    try {
      const r = await adminListLibraryStations();
      setItems(r.items || []);
    } catch (e: any) {
      Alert.alert("Couldn't load stations", e?.message || "Try again.");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!user?.is_admin) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.center}>
          <Text style={styles.title}>Admin Only</Text>
        </View>
      </SafeAreaView>
    );
  }

  const openCreate = () => {
    setEditing(null);
    setDraft(BLANK);
    setOpen(true);
  };

  const openEdit = (s: LibraryStation) => {
    setEditing(s);
    setDraft({
      slug: s.slug,
      name: s.name,
      blurb: s.blurb || "",
      country: s.country || "",
      language: s.language || "English",
      stream_url: s.stream_url,
      website_url: s.website_url || "",
      accent_color: s.accent_color || "#B8860B",
      icon: s.icon || "radio-outline",
      status: (s.status as any) || "published",
    });
    setOpen(true);
  };

  const save = async () => {
    if (!draft.name.trim() || !draft.slug.trim() || !draft.stream_url.trim()) {
      Alert.alert("Missing fields", "Slug, name, and stream URL are required.");
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        await adminPatchLibraryStation(editing.slug, {
          name: draft.name.trim(),
          blurb: (draft.blurb || "").trim() || null,
          country: (draft.country || "").trim() || null,
          language: (draft.language || "").trim() || null,
          stream_url: draft.stream_url.trim(),
          website_url: (draft.website_url || "").trim() || null,
          accent_color: draft.accent_color || null,
          icon: draft.icon || null,
          status: draft.status,
        });
      } else {
        await adminCreateLibraryStation({
          ...draft,
          slug: draft.slug.trim(),
          name: draft.name.trim(),
          blurb: (draft.blurb || "").trim() || null,
          country: (draft.country || "").trim() || null,
          language: (draft.language || "").trim() || null,
          stream_url: draft.stream_url.trim(),
          website_url: (draft.website_url || "").trim() || null,
        });
      }
      setOpen(false);
      setEditing(null);
      await load();
    } catch (e: any) {
      Alert.alert("Save failed", e?.message || "Try again.");
    } finally {
      setSaving(false);
    }
  };

  const remove = (s: LibraryStation) => {
    Alert.alert("Remove station?", `"${s.name}" will be removed permanently.`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await adminDeleteLibraryStation(s.slug);
            await load();
          } catch (e: any) {
            Alert.alert("Delete failed", e?.message || "Try again.");
          }
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable hitSlop={12} onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={22} color={colors.textPrimary} />
        </Pressable>
        <Text style={styles.headerTitle}>Radio — Admin</Text>
        <Pressable hitSlop={12} onPress={openCreate} testID="admin-radio-add">
          <Ionicons name="add-circle" size={24} color={colors.gold} />
        </Pressable>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.body}>
          {items.length === 0 ? (
            <Text style={styles.empty}>No stations yet. Tap + to add one.</Text>
          ) : null}
          {items.map((s) => (
            <View key={s.station_id} style={styles.row}>
              <View style={[styles.icon, { backgroundColor: s.accent_color || colors.gold }]}>
                <Ionicons
                  name={(s.icon as any) || "radio-outline"}
                  size={18}
                  color={colors.gold}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.rowTitle} numberOfLines={1}>
                  {s.name}
                </Text>
                <Text style={styles.rowMeta} numberOfLines={1}>
                  {s.country || "—"} · {s.language || "—"} · {s.status}
                </Text>
              </View>
              <Pressable
                hitSlop={10}
                onPress={() => openEdit(s)}
                testID={`admin-radio-edit-${s.slug}`}
              >
                <Ionicons name="pencil" size={18} color={colors.textSecondary} />
              </Pressable>
              <Pressable
                hitSlop={10}
                onPress={() => remove(s)}
                testID={`admin-radio-delete-${s.slug}`}
              >
                <Ionicons name="trash-outline" size={18} color="#9E1B1B" />
              </Pressable>
            </View>
          ))}
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}

      <Modal visible={open} animationType="slide" onRequestClose={() => !saving && setOpen(false)}>
        <SafeAreaView style={styles.safe}>
          <View style={styles.header}>
            <Pressable hitSlop={12} onPress={() => !saving && setOpen(false)}>
              <Ionicons name="close" size={22} color={colors.textPrimary} />
            </Pressable>
            <Text style={styles.headerTitle}>{editing ? "Edit Station" : "New Station"}</Text>
            <Pressable
              hitSlop={12}
              onPress={save}
              disabled={saving}
              testID="admin-radio-save"
            >
              {saving ? (
                <ActivityIndicator color={colors.gold} />
              ) : (
                <Text style={styles.saveTxt}>Save</Text>
              )}
            </Pressable>
          </View>
          <ScrollView contentContainerStyle={styles.body}>
            <Field
              label="Slug (URL)"
              value={draft.slug}
              editable={!editing}
              onChange={(v) =>
                setDraft({ ...draft, slug: v.toLowerCase().replace(/[^a-z0-9-]/g, "-") })
              }
            />
            <Field label="Name" value={draft.name} onChange={(v) => setDraft({ ...draft, name: v })} />
            <Field
              label="Blurb"
              multiline
              value={draft.blurb || ""}
              onChange={(v) => setDraft({ ...draft, blurb: v })}
            />
            <Field
              label="Country"
              value={draft.country || ""}
              onChange={(v) => setDraft({ ...draft, country: v })}
            />
            <Field
              label="Language"
              value={draft.language || ""}
              onChange={(v) => setDraft({ ...draft, language: v })}
            />
            <Field
              label="Stream URL (mp3 / m3u8 / aac)"
              value={draft.stream_url}
              onChange={(v) => setDraft({ ...draft, stream_url: v.trim() })}
            />
            <Field
              label="Website URL"
              value={draft.website_url || ""}
              onChange={(v) => setDraft({ ...draft, website_url: v.trim() })}
            />
            <Field
              label="Accent color (#hex)"
              value={draft.accent_color || ""}
              onChange={(v) => setDraft({ ...draft, accent_color: v })}
            />
            <Field
              label="Icon (Ionicons name)"
              value={draft.icon || ""}
              onChange={(v) => setDraft({ ...draft, icon: v })}
            />
            <View style={styles.statusRow}>
              <Text style={styles.label}>Published</Text>
              <Switch
                value={draft.status === "published"}
                onValueChange={(v) =>
                  setDraft({ ...draft, status: v ? "published" : "draft" })
                }
              />
            </View>
            <View style={{ height: spacing.xxl }} />
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}

function Field({
  label,
  value,
  onChange,
  multiline,
  editable = true,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  multiline?: boolean;
  editable?: boolean;
}) {
  return (
    <View style={{ marginBottom: spacing.md }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[
          styles.input,
          multiline && { minHeight: 70, textAlignVertical: "top" },
          !editable && { backgroundColor: colors.borderSoft, color: colors.textMuted },
        ]}
        value={value}
        onChangeText={onChange}
        multiline={multiline}
        editable={editable}
        placeholderTextColor={colors.textMuted}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
    backgroundColor: colors.surface,
  },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  title: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.textPrimary },
  saveTxt: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 14 },
  body: { paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  empty: {
    fontFamily: fonts.bodyRegular,
    color: colors.textMuted,
    textAlign: "center",
    marginTop: spacing.xl,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    padding: spacing.md,
    marginBottom: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  icon: {
    width: 38,
    height: 38,
    borderRadius: radius.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  rowTitle: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.textPrimary },
  rowMeta: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  label: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.textSecondary,
    marginBottom: 6,
    letterSpacing: 0.3,
  },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: radius.md,
    padding: spacing.md,
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textPrimary,
  },
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.md,
  },
});

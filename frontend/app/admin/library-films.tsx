import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
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
  LibraryFilm,
  LibraryFilmCategory,
  LibraryFilmCreate,
  adminCreateLibraryFilm,
  adminDeleteLibraryFilm,
  adminListLibraryFilms,
  adminPatchLibraryFilm,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const CATEGORIES: LibraryFilmCategory[] = ["saints", "doctrine", "animated", "documentary"];

const BLANK: LibraryFilmCreate = {
  slug: "",
  title: "",
  blurb: "",
  youtube_id: "",
  duration_label: "",
  category: "saints",
  accent_color: "#B8860B",
  status: "published",
};

/** Parse any of: raw ID (11+ char), youtu.be/<id>, ?v=<id>, /embed/<id> */
function extractYouTubeId(input: string): string {
  const s = (input || "").trim();
  if (!s) return "";
  if (/^[A-Za-z0-9_-]{8,15}$/.test(s) && !s.includes("/")) return s;
  const patterns = [
    /[?&]v=([A-Za-z0-9_-]{8,15})/,
    /youtu\.be\/([A-Za-z0-9_-]{8,15})/,
    /\/embed\/([A-Za-z0-9_-]{8,15})/,
    /\/shorts\/([A-Za-z0-9_-]{8,15})/,
  ];
  for (const p of patterns) {
    const m = s.match(p);
    if (m) return m[1];
  }
  return s;
}

export default function AdminLibraryFilmsScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [items, setItems] = useState<LibraryFilm[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<LibraryFilm | null>(null);
  const [draft, setDraft] = useState<LibraryFilmCreate>(BLANK);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!user?.is_admin) return;
    setLoading(true);
    try {
      const r = await adminListLibraryFilms();
      setItems(r.items || []);
    } catch (e: any) {
      Alert.alert("Couldn't load films", e?.message || "Try again.");
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

  const openEdit = (f: LibraryFilm) => {
    setEditing(f);
    setDraft({
      slug: f.slug,
      title: f.title,
      blurb: f.blurb || "",
      youtube_id: f.youtube_id,
      duration_label: f.duration_label || "",
      category: f.category,
      accent_color: f.accent_color || "#B8860B",
      status: (f.status as any) || "published",
    });
    setOpen(true);
  };

  const save = async () => {
    const ytId = extractYouTubeId(draft.youtube_id);
    if (!draft.title.trim() || !draft.slug.trim() || !ytId) {
      Alert.alert("Missing fields", "Slug, title, and YouTube ID/URL are required.");
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        await adminPatchLibraryFilm(editing.slug, {
          title: draft.title.trim(),
          blurb: (draft.blurb || "").trim() || null,
          youtube_id: ytId,
          duration_label: (draft.duration_label || "").trim() || null,
          category: draft.category,
          accent_color: draft.accent_color || null,
          status: draft.status,
        });
      } else {
        await adminCreateLibraryFilm({
          ...draft,
          slug: draft.slug.trim(),
          title: draft.title.trim(),
          blurb: (draft.blurb || "").trim() || null,
          youtube_id: ytId,
          duration_label: (draft.duration_label || "").trim() || null,
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

  const remove = (f: LibraryFilm) => {
    Alert.alert("Remove film?", `"${f.title}" will be removed permanently.`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await adminDeleteLibraryFilm(f.slug);
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
        <Text style={styles.headerTitle}>Films — Admin</Text>
        <Pressable hitSlop={12} onPress={openCreate} testID="admin-films-add">
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
            <Text style={styles.empty}>No films yet. Tap + to add one.</Text>
          ) : null}
          {items.map((f) => (
            <View key={f.film_id} style={styles.row}>
              <Image
                source={{ uri: `https://i.ytimg.com/vi/${f.youtube_id}/default.jpg` }}
                style={styles.thumb}
              />
              <View style={{ flex: 1 }}>
                <Text style={styles.rowTitle} numberOfLines={1}>
                  {f.title}
                </Text>
                <Text style={styles.rowMeta} numberOfLines={1}>
                  {f.category} · {f.duration_label || "—"} · {f.status}
                </Text>
              </View>
              <Pressable
                hitSlop={10}
                onPress={() => openEdit(f)}
                testID={`admin-film-edit-${f.slug}`}
              >
                <Ionicons name="pencil" size={18} color={colors.textSecondary} />
              </Pressable>
              <Pressable
                hitSlop={10}
                onPress={() => remove(f)}
                testID={`admin-film-delete-${f.slug}`}
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
            <Text style={styles.headerTitle}>{editing ? "Edit Film" : "New Film"}</Text>
            <Pressable
              hitSlop={12}
              onPress={save}
              disabled={saving}
              testID="admin-film-save"
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
            <Field
              label="Title"
              value={draft.title}
              onChange={(v) => setDraft({ ...draft, title: v })}
            />
            <Field
              label="Blurb"
              multiline
              value={draft.blurb || ""}
              onChange={(v) => setDraft({ ...draft, blurb: v })}
            />
            <Field
              label="YouTube ID or URL"
              value={draft.youtube_id}
              onChange={(v) => setDraft({ ...draft, youtube_id: v })}
            />
            <Field
              label="Duration label (e.g. '1h 28m')"
              value={draft.duration_label || ""}
              onChange={(v) => setDraft({ ...draft, duration_label: v })}
            />

            <Text style={styles.label}>Category</Text>
            <View style={styles.toggleRow}>
              {CATEGORIES.map((c) => (
                <Pressable
                  key={c}
                  onPress={() => setDraft({ ...draft, category: c })}
                  style={[styles.toggleChip, draft.category === c && styles.toggleChipActive]}
                >
                  <Text
                    style={[
                      styles.toggleText,
                      draft.category === c && { color: colors.surface },
                    ]}
                  >
                    {c}
                  </Text>
                </Pressable>
              ))}
            </View>

            <Field
              label="Accent color (#hex)"
              value={draft.accent_color || ""}
              onChange={(v) => setDraft({ ...draft, accent_color: v })}
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
    padding: spacing.sm,
    marginBottom: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  thumb: {
    width: 64,
    height: 48,
    borderRadius: radius.sm,
    backgroundColor: colors.borderSoft,
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
  toggleRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md, flexWrap: "wrap" },
  toggleChip: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: radius.round,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    alignItems: "center",
  },
  toggleChipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  toggleText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary },
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.md,
  },
});

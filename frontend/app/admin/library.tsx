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
  LibraryBook,
  LibraryBookCreate,
  adminCreateLibraryBook,
  adminDeleteLibraryBook,
  adminDeleteLibraryChapter,
  adminListLibraryBooks,
  adminPatchLibraryBook,
  adminUpsertLibraryChapter,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type Tab = "all" | "embedded" | "external" | "draft";

const BLANK: LibraryBookCreate = {
  slug: "",
  title: "",
  author: "",
  year: undefined,
  blurb: "",
  tradition: "catholic-classic",
  cover_color: "#7C3AED",
  cover_icon: "book-outline",
  type: "external",
  source_url: "",
  chapters: [],
  status: "published",
};

export default function AdminLibraryScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("all");
  const [items, setItems] = useState<LibraryBook[]>([]);
  const [loading, setLoading] = useState(true);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<LibraryBook | null>(null); // null = create new
  const [draft, setDraft] = useState<LibraryBookCreate>(BLANK);
  const [saving, setSaving] = useState(false);
  const [chapterDraft, setChapterDraft] = useState<{ title: string; body_md: string }>({
    title: "", body_md: "",
  });
  const [chapterEditIndex, setChapterEditIndex] = useState<number | null>(null);

  const load = useCallback(async () => {
    if (!user?.is_admin) return;
    setLoading(true);
    try {
      const r = await adminListLibraryBooks();
      setItems(r.items || []);
    } catch (e: any) {
      Alert.alert("Couldn't load", e?.message || "Try again.");
    } finally { setLoading(false); }
  }, [user]);

  useEffect(() => { void load(); }, [load]);

  if (!user?.is_admin) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.centerFill}>
          <Text style={styles.title}>Admin Only</Text>
        </View>
      </SafeAreaView>
    );
  }

  const filtered = items.filter((b) => {
    if (tab === "all") return true;
    if (tab === "draft") return b.status === "draft";
    return b.type === tab;
  });

  const openCreate = () => {
    setEditing(null);
    setDraft(BLANK);
    setChapterDraft({ title: "", body_md: "" });
    setChapterEditIndex(null);
    setEditorOpen(true);
  };

  const openEdit = (b: LibraryBook) => {
    setEditing(b);
    setDraft({
      slug: b.slug,
      title: b.title,
      author: b.author,
      year: b.year ?? undefined,
      blurb: b.blurb ?? "",
      tradition: b.tradition,
      cover_color: b.cover_color ?? "#7C3AED",
      cover_icon: b.cover_icon ?? "book-outline",
      type: b.type,
      source_url: b.source_url ?? "",
      chapters: b.chapters.map((c) => ({ title: c.title, body_md: c.body_md || "" })),
      status: b.status as any,
    });
    setChapterDraft({ title: "", body_md: "" });
    setChapterEditIndex(null);
    setEditorOpen(true);
  };

  const closeEditor = () => {
    if (saving) return;
    setEditorOpen(false);
    setEditing(null);
  };

  const saveBook = async () => {
    if (!draft.title.trim() || !draft.author.trim() || !draft.slug.trim()) {
      Alert.alert("Missing fields", "Slug, title, and author are required.");
      return;
    }
    setSaving(true);
    try {
      if (editing) {
        await adminPatchLibraryBook(editing.slug, {
          title: draft.title.trim(),
          author: draft.author.trim(),
          year: draft.year || null,
          blurb: (draft.blurb || "").trim() || null,
          tradition: draft.tradition,
          cover_color: draft.cover_color || null,
          cover_icon: draft.cover_icon || null,
          type: draft.type,
          source_url: (draft.source_url || "").trim() || null,
          status: draft.status,
        });
      } else {
        await adminCreateLibraryBook({
          ...draft,
          slug: draft.slug.trim(),
          title: draft.title.trim(),
          author: draft.author.trim(),
          blurb: (draft.blurb || "").trim() || null,
          source_url: (draft.source_url || "").trim() || null,
          year: draft.year || null,
          chapters: draft.chapters || [],
        });
      }
      setEditorOpen(false);
      setEditing(null);
      await load();
    } catch (e: any) {
      Alert.alert("Save failed", e?.message || "Try again.");
    } finally { setSaving(false); }
  };

  const deleteBook = (b: LibraryBook) => {
    Alert.alert("Delete book?", `\"${b.title}\" will be removed permanently.`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete", style: "destructive",
        onPress: async () => {
          try {
            await adminDeleteLibraryBook(b.slug);
            await load();
          } catch (e: any) {
            Alert.alert("Delete failed", e?.message || "Try again.");
          }
        },
      },
    ]);
  };

  const saveChapter = async () => {
    if (!editing) {
      Alert.alert("Save book first", "Create the book before adding chapters.");
      return;
    }
    if (!chapterDraft.title.trim() || !chapterDraft.body_md.trim()) {
      Alert.alert("Missing fields", "Chapter title and body are required.");
      return;
    }
    try {
      await adminUpsertLibraryChapter(editing.slug, {
        index: chapterEditIndex,
        title: chapterDraft.title.trim(),
        body_md: chapterDraft.body_md.trim(),
      });
      setChapterDraft({ title: "", body_md: "" });
      setChapterEditIndex(null);
      await load();
      const fresh = (await adminListLibraryBooks()).items.find((b) => b.slug === editing.slug);
      if (fresh) openEdit(fresh);
    } catch (e: any) {
      Alert.alert("Save chapter failed", e?.message || "Try again.");
    }
  };

  const deleteChapter = (idx: number) => {
    if (!editing) return;
    Alert.alert("Remove chapter?", "This action is permanent.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Remove", style: "destructive",
        onPress: async () => {
          try {
            await adminDeleteLibraryChapter(editing.slug, idx);
            const fresh = (await adminListLibraryBooks()).items.find((b) => b.slug === editing.slug);
            if (fresh) openEdit(fresh);
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
        <Text style={styles.headerTitle}>Library — Admin</Text>
        <Pressable hitSlop={12} onPress={openCreate} testID="admin-library-add">
          <Ionicons name="add-circle" size={24} color={colors.gold} />
        </Pressable>
      </View>

      <View style={styles.segmentRow}>
        {(["all", "embedded", "external", "draft"] as Tab[]).map((t) => (
          <Pressable
            key={t}
            testID={`admin-library-tab-${t}`}
            onPress={() => setTab(t)}
            style={[styles.segment, tab === t && styles.segmentActive]}
          >
            <Text style={[styles.segmentText, tab === t && { color: colors.surface }]}>
              {t === "all" ? "All" : t === "embedded" ? "In-app" : t === "external" ? "External" : "Drafts"}
            </Text>
          </Pressable>
        ))}
      </View>

      {loading ? (
        <View style={styles.centerFill}><ActivityIndicator color={colors.gold} /></View>
      ) : (
        <ScrollView contentContainerStyle={styles.body}>
          {filtered.length === 0 ? (
            <Text style={styles.emptyText}>No books match this filter.</Text>
          ) : null}
          {filtered.map((b) => (
            <View key={b.book_id} style={styles.bookRow}>
              <View style={[styles.cover, { backgroundColor: b.cover_color || colors.gold }]}>
                <Ionicons name={(b.cover_icon as any) || "book-outline"} size={20} color={colors.gold} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.bookTitle} numberOfLines={1}>{b.title}</Text>
                <Text style={styles.bookMeta} numberOfLines={1}>
                  {b.author} · {b.type === "embedded" ? `${b.chapter_count} chapters` : "external"} · {b.status}
                </Text>
              </View>
              <Pressable hitSlop={10} onPress={() => openEdit(b)} testID={`admin-library-edit-${b.slug}`}>
                <Ionicons name="pencil" size={18} color={colors.textSecondary} />
              </Pressable>
              <Pressable hitSlop={10} onPress={() => deleteBook(b)} testID={`admin-library-delete-${b.slug}`}>
                <Ionicons name="trash-outline" size={18} color="#9E1B1B" />
              </Pressable>
            </View>
          ))}
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}

      {/* Editor */}
      <Modal visible={editorOpen} animationType="slide" onRequestClose={closeEditor}>
        <SafeAreaView style={styles.safe}>
          <View style={styles.header}>
            <Pressable hitSlop={12} onPress={closeEditor}>
              <Ionicons name="close" size={22} color={colors.textPrimary} />
            </Pressable>
            <Text style={styles.headerTitle}>{editing ? "Edit Book" : "New Book"}</Text>
            <Pressable
              hitSlop={12}
              onPress={saveBook}
              disabled={saving}
              testID="admin-library-save"
            >
              {saving ? <ActivityIndicator color={colors.gold} /> : <Text style={styles.saveTxt}>Save</Text>}
            </Pressable>
          </View>
          <ScrollView contentContainerStyle={styles.body}>
            <Field label="Slug (URL)" value={draft.slug}
              editable={!editing}
              onChange={(v) => setDraft({ ...draft, slug: v.toLowerCase().replace(/[^a-z0-9-]/g, "-") })} />
            <Field label="Title" value={draft.title} onChange={(v) => setDraft({ ...draft, title: v })} />
            <Field label="Author" value={draft.author} onChange={(v) => setDraft({ ...draft, author: v })} />
            <Field label="Year" value={draft.year ? String(draft.year) : ""}
              keyboardType="number-pad"
              onChange={(v) => setDraft({ ...draft, year: v ? parseInt(v, 10) || undefined : undefined })} />
            <Field label="Blurb" multiline value={draft.blurb || ""}
              onChange={(v) => setDraft({ ...draft, blurb: v })} />

            <Text style={styles.label}>Type</Text>
            <View style={styles.toggleRow}>
              {(["embedded", "external"] as const).map((t) => (
                <Pressable key={t}
                  onPress={() => setDraft({ ...draft, type: t })}
                  style={[styles.toggleChip, draft.type === t && styles.toggleChipActive]}>
                  <Text style={[styles.toggleText, draft.type === t && { color: colors.surface }]}>
                    {t === "embedded" ? "In-app reader" : "External link"}
                  </Text>
                </Pressable>
              ))}
            </View>

            <Field label={draft.type === "external" ? "Source URL (required)" : "Source URL (for 'continue at source' link)"}
              value={draft.source_url || ""} onChange={(v) => setDraft({ ...draft, source_url: v })} />

            <Field label="Cover color (#hex)" value={draft.cover_color || ""}
              onChange={(v) => setDraft({ ...draft, cover_color: v })} />
            <Field label="Cover icon (Ionicons name)" value={draft.cover_icon || ""}
              onChange={(v) => setDraft({ ...draft, cover_icon: v })} />
            <Field label="Tradition (catholic-classic | doctor | mystic | apologist)"
              value={draft.tradition || ""} onChange={(v) => setDraft({ ...draft, tradition: v })} />

            <View style={styles.statusRow}>
              <Text style={styles.label}>Published</Text>
              <Switch
                value={draft.status === "published"}
                onValueChange={(v) => setDraft({ ...draft, status: v ? "published" : "draft" })}
              />
            </View>

            {editing && draft.type === "embedded" ? (
              <>
                <Text style={styles.section}>Chapters</Text>
                {(editing.chapters || []).map((c, idx) => (
                  <View key={idx} style={styles.chapterRow}>
                    <Text style={styles.chapterIdx}>{idx + 1}</Text>
                    <Text style={styles.chapterTitle} numberOfLines={2}>{c.title}</Text>
                    <Pressable
                      hitSlop={8}
                      onPress={() => {
                        setChapterEditIndex(idx);
                        setChapterDraft({ title: c.title, body_md: c.body_md || "" });
                      }}
                    >
                      <Ionicons name="pencil" size={16} color={colors.textSecondary} />
                    </Pressable>
                    <Pressable hitSlop={8} onPress={() => deleteChapter(idx)}>
                      <Ionicons name="trash-outline" size={16} color="#9E1B1B" />
                    </Pressable>
                  </View>
                ))}

                <Text style={styles.section}>
                  {chapterEditIndex !== null ? `Edit chapter ${chapterEditIndex + 1}` : "Add chapter"}
                </Text>
                <Field label="Chapter title" value={chapterDraft.title}
                  onChange={(v) => setChapterDraft({ ...chapterDraft, title: v })} />
                <Field label="Body (markdown)" multiline tall value={chapterDraft.body_md}
                  onChange={(v) => setChapterDraft({ ...chapterDraft, body_md: v })} />
                <Pressable testID="admin-library-save-chapter" onPress={saveChapter} style={styles.primaryBtn}>
                  <Text style={styles.primaryBtnText}>
                    {chapterEditIndex !== null ? "Save chapter" : "Append chapter"}
                  </Text>
                </Pressable>
                {chapterEditIndex !== null ? (
                  <Pressable
                    onPress={() => { setChapterEditIndex(null); setChapterDraft({ title: "", body_md: "" }); }}
                    style={styles.linkBtn}
                  >
                    <Text style={styles.linkText}>Cancel edit</Text>
                  </Pressable>
                ) : null}
              </>
            ) : null}

            <View style={{ height: spacing.xxl }} />
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}

function Field({
  label, value, onChange, multiline, tall, keyboardType, editable = true,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  multiline?: boolean;
  tall?: boolean;
  keyboardType?: "default" | "number-pad";
  editable?: boolean;
}) {
  return (
    <View style={{ marginBottom: spacing.md }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[
          styles.input,
          multiline && { minHeight: tall ? 180 : 80, textAlignVertical: "top" },
          !editable && { backgroundColor: colors.borderSoft, color: colors.textMuted },
        ]}
        value={value}
        onChangeText={onChange}
        multiline={multiline}
        editable={editable}
        keyboardType={keyboardType || "default"}
        placeholderTextColor={colors.textMuted}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  centerFill: { flex: 1, alignItems: "center", justifyContent: "center" },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: spacing.lg, paddingVertical: spacing.md,
    borderBottomWidth: 1, borderBottomColor: colors.borderSoft, backgroundColor: colors.surface,
  },
  headerTitle: { fontFamily: fonts.headingSemi, fontSize: 16, color: colors.textPrimary },
  title: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.textPrimary },
  saveTxt: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 14 },
  segmentRow: {
    flexDirection: "row", gap: spacing.sm, paddingHorizontal: spacing.lg, paddingVertical: spacing.md,
  },
  segment: {
    flex: 1, paddingVertical: 8, borderRadius: radius.round,
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft,
    alignItems: "center",
  },
  segmentActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  segmentText: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.textSecondary, letterSpacing: 0.3 },
  body: { paddingHorizontal: spacing.lg, paddingBottom: spacing.xl },
  emptyText: { fontFamily: fonts.bodyRegular, color: colors.textMuted, textAlign: "center", marginTop: spacing.xl },
  bookRow: {
    flexDirection: "row", alignItems: "center", gap: spacing.md,
    padding: spacing.md, marginBottom: spacing.sm,
    backgroundColor: colors.surface, borderRadius: radius.md,
    borderWidth: 1, borderColor: colors.borderSoft, ...shadow.card,
  },
  cover: { width: 40, height: 56, borderRadius: radius.sm, alignItems: "center", justifyContent: "center" },
  bookTitle: { fontFamily: fonts.bodyBold, fontSize: 14, color: colors.textPrimary },
  bookMeta: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  label: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary, marginBottom: 6, letterSpacing: 0.3 },
  input: {
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft,
    borderRadius: radius.md, padding: spacing.md,
    fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary,
  },
  toggleRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
  toggleChip: {
    flex: 1, paddingVertical: 10, borderRadius: radius.round,
    backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft,
    alignItems: "center",
  },
  toggleChipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  toggleText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary },
  statusRow: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    marginBottom: spacing.md,
  },
  section: {
    fontFamily: fonts.headingSemi, fontSize: 15, color: colors.textPrimary,
    marginTop: spacing.xl, marginBottom: spacing.sm,
  },
  chapterRow: {
    flexDirection: "row", alignItems: "center", gap: spacing.sm,
    padding: spacing.sm, marginBottom: spacing.xs,
    backgroundColor: colors.surface, borderRadius: radius.sm,
    borderWidth: 1, borderColor: colors.borderSoft,
  },
  chapterIdx: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold, width: 22 },
  chapterTitle: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textPrimary },
  primaryBtn: {
    backgroundColor: colors.primary, paddingVertical: 14, borderRadius: radius.round,
    alignItems: "center", marginTop: spacing.md,
  },
  primaryBtnText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 14, letterSpacing: 0.6 },
  linkBtn: { paddingVertical: spacing.sm, alignItems: "center" },
  linkText: { fontFamily: fonts.uiMedium, color: colors.textSecondary, fontSize: 12 },
});

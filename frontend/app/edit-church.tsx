/**
 * Edit Church Details — adds Mass / Confession times, website and phone to an
 * OSM-sourced church (or amends a community-submitted one). All edits live in
 * the `church_overlays` collection on the backend and get merged into every
 * read endpoint, so a single user's contribution becomes visible to everyone
 * in the area immediately.
 *
 * Design choices:
 *   • Mass / confession times are *additive* — we show the existing list as
 *     a non-removable display (those entries come from OSM or earlier
 *     overlays), and offer an "Add Mass time" chip-input below it. We don't
 *     want one user accidentally wiping schedules another user already
 *     entered. A future "report incorrect schedule" flag will let users
 *     surface issues without destructive deletes.
 *   • Website / phone / notes are scalars; we pre-fill with the current
 *     value and let the user replace it (last-write-wins).
 *   • Once submitted, we navigate back so the caller (ChurchCard) re-fetches
 *     `/churches/nearby` and shows the merged result.
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
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { api, ChurchOverlay } from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

export default function EditChurchScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const params = useLocalSearchParams<{
    church_id?: string;
    church_name?: string;
    address?: string;
    existing_mass?: string;
    existing_conf?: string;
    existing_website?: string;
    existing_phone?: string;
    existing_notes?: string;
  }>();

  const churchId = typeof params.church_id === "string" ? params.church_id : "";
  const churchName = typeof params.church_name === "string" ? params.church_name : "";
  const churchAddress = typeof params.address === "string" ? params.address : "";

  const parseList = (raw: unknown): string[] => {
    if (typeof raw !== "string" || !raw) return [];
    try {
      const v = JSON.parse(raw);
      return Array.isArray(v) ? v.filter((x) => typeof x === "string") : [];
    } catch {
      return [];
    }
  };
  const existingMass = parseList(params.existing_mass);
  const existingConf = parseList(params.existing_conf);

  // ---- editable state ----
  const [newMass, setNewMass] = useState<string[]>([]);
  const [newConf, setNewConf] = useState<string[]>([]);
  const [massInput, setMassInput] = useState("");
  const [confInput, setConfInput] = useState("");
  const [website, setWebsite] = useState<string>(
    typeof params.existing_website === "string" ? params.existing_website : ""
  );
  const [phone, setPhone] = useState<string>(
    typeof params.existing_phone === "string" ? params.existing_phone : ""
  );
  const [notes, setNotes] = useState<string>(
    typeof params.existing_notes === "string" ? params.existing_notes : ""
  );

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editorCount, setEditorCount] = useState<number | null>(null);
  const [contributors, setContributors] = useState<string[]>([]);
  // Attribution is opt-in per edit; default to the user's saved preference.
  const [showName, setShowName] = useState<boolean>(!!user?.show_attribution);

  // Fetch overlay once to surface "Edited by N people" attribution.
  useEffect(() => {
    if (!churchId) return;
    (async () => {
      try {
        const ov = await api<ChurchOverlay>(
          `/churches/${encodeURIComponent(churchId)}/overlay`
        );
        if (ov && typeof ov.editor_count === "number") {
          setEditorCount(ov.editor_count);
          setContributors(ov.contributors || []);
        }
      } catch {
        /* non-fatal — header just won't show attribution */
      }
    })();
  }, [churchId]);

  const addItem = useCallback(
    (raw: string, list: string[], setList: (l: string[]) => void, setInput: (s: string) => void) => {
      const s = raw.trim();
      if (!s) return;
      if (s.length > 80) {
        Alert.alert("Too long", "Each time slot should be 80 characters or less.");
        return;
      }
      if (list.some((x) => x.toLowerCase() === s.toLowerCase())) {
        setInput("");
        return;
      }
      // Also dedupe against existing OSM-side entries.
      if (
        list === newMass &&
        existingMass.some((x) => x.toLowerCase() === s.toLowerCase())
      ) {
        Alert.alert("Already listed", `"${s}" is already in the Mass schedule.`);
        return;
      }
      if (
        list === newConf &&
        existingConf.some((x) => x.toLowerCase() === s.toLowerCase())
      ) {
        Alert.alert("Already listed", `"${s}" is already in the Confession schedule.`);
        return;
      }
      if (list.length >= 24) {
        Alert.alert("Limit reached", "You can add up to 24 time slots per submission.");
        return;
      }
      setList([...list, s]);
      setInput("");
    },
    [newMass, newConf, existingMass, existingConf]
  );

  const removeAt = (idx: number, list: string[], setList: (l: string[]) => void) => {
    setList(list.filter((_, i) => i !== idx));
  };

  const hasChanges = (): boolean => {
    if (newMass.length || newConf.length) return true;
    const w = (website || "").trim();
    const p = (phone || "").trim();
    const n = (notes || "").trim();
    const origW = (typeof params.existing_website === "string" ? params.existing_website : "").trim();
    const origP = (typeof params.existing_phone === "string" ? params.existing_phone : "").trim();
    const origN = (typeof params.existing_notes === "string" ? params.existing_notes : "").trim();
    return w !== origW || p !== origP || n !== origN;
  };

  const submit = async () => {
    setError(null);
    if (!hasChanges()) {
      Alert.alert("No changes", "Add a Mass/Confession time or edit a field to save.");
      return;
    }
    if (!churchId) {
      setError("Missing church id.");
      return;
    }
    setSubmitting(true);
    try {
      const body: Record<string, unknown> = {};
      if (newMass.length) body.mass_times = newMass;
      if (newConf.length) body.confession_times = newConf;
      // Only send scalars that actually changed.
      const w = (website || "").trim();
      const p = (phone || "").trim();
      const n = (notes || "").trim();
      const origW = (typeof params.existing_website === "string" ? params.existing_website : "").trim();
      const origP = (typeof params.existing_phone === "string" ? params.existing_phone : "").trim();
      const origN = (typeof params.existing_notes === "string" ? params.existing_notes : "").trim();
      if (w !== origW) body.website = w;
      if (p !== origP) body.phone = p;
      if (n !== origN) body.notes = n;
      // Carry the per-edit attribution choice — opt-in.
      body.show_name = showName;

      await api<ChurchOverlay>(`/churches/${encodeURIComponent(churchId)}/overlay`, {
        method: "PUT",
        body,
      });
      Alert.alert(
        "Thank you",
        `Your edits to “${churchName || "this parish"}” are now visible to everyone nearby.`,
        [{ text: "OK", onPress: () => router.back() }]
      );
    } catch (e) {
      setError((e as Error).message || "Could not save. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="edit-church-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.headerRow}>
        <Pressable
          testID="edit-church-back"
          onPress={() => router.back()}
          hitSlop={12}
          style={({ pressed }) => [styles.iconBtn, pressed && styles.pressed]}
        >
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle} numberOfLines={1}>
          Edit Details
        </Text>
        <View style={{ width: 40 }} />
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
        >
          {/* Subject line */}
          <View style={styles.subjectCard}>
            <Ionicons name="business-outline" size={18} color={colors.gold} />
            <View style={{ flex: 1, marginLeft: spacing.sm }}>
              <Text style={styles.subjectName} numberOfLines={2}>
                {churchName || "This church"}
              </Text>
              {churchAddress ? (
                <Text style={styles.subjectAddr} numberOfLines={2}>
                  {churchAddress}
                </Text>
              ) : null}
              {editorCount && editorCount > 0 ? (
                <Text style={styles.attribution}>
                  <Ionicons name="people-outline" size={11} color={colors.liturgical.purple} />{" "}
                  Edited by {editorCount} {editorCount === 1 ? "person" : "people"} so far
                </Text>
              ) : null}
            </View>
          </View>

          <Text style={styles.intro}>
            Anything you add here gets shared with everyone in the area. Mass and
            Confession times are <Text style={styles.bold}>added</Text> to whatever&apos;s
            already listed — you can&apos;t accidentally erase another contributor&apos;s work.
          </Text>

          {/* Mass times */}
          <Section label="Mass schedule">
            {existingMass.length > 0 ? (
              <View style={{ marginBottom: spacing.sm }}>
                <Text style={styles.subLabel}>Already listed</Text>
                <View style={styles.chipList}>
                  {existingMass.map((t, i) => (
                    <View key={`em-${i}`} style={[styles.chip, styles.chipReadOnly]}>
                      <Text style={styles.chipText}>{t}</Text>
                    </View>
                  ))}
                </View>
              </View>
            ) : null}
            <Text style={styles.subLabel}>Add Mass times</Text>
            <ChipList
              testIdPrefix="edit-church-mass"
              items={newMass}
              onRemove={(i) => removeAt(i, newMass, setNewMass)}
            />
            <View style={styles.addRow}>
              <TextInput
                testID="edit-church-mass-input"
                style={[styles.input, { flex: 1, marginRight: spacing.sm }]}
                value={massInput}
                onChangeText={setMassInput}
                placeholder='e.g. "Sun 9:00 AM"'
                placeholderTextColor={colors.textMuted}
                returnKeyType="done"
                onSubmitEditing={() =>
                  addItem(massInput, newMass, setNewMass, setMassInput)
                }
                maxLength={80}
              />
              <Pressable
                testID="edit-church-mass-add"
                onPress={() => addItem(massInput, newMass, setNewMass, setMassInput)}
                style={({ pressed }) => [styles.addBtn, pressed && styles.pressed]}
              >
                <Ionicons name="add" size={20} color={colors.gold} />
              </Pressable>
            </View>
          </Section>

          {/* Confession times */}
          <Section label="Confession schedule">
            {existingConf.length > 0 ? (
              <View style={{ marginBottom: spacing.sm }}>
                <Text style={styles.subLabel}>Already listed</Text>
                <View style={styles.chipList}>
                  {existingConf.map((t, i) => (
                    <View key={`ec-${i}`} style={[styles.chip, styles.chipReadOnly]}>
                      <Text style={styles.chipText}>{t}</Text>
                    </View>
                  ))}
                </View>
              </View>
            ) : null}
            <Text style={styles.subLabel}>Add Confession times</Text>
            <ChipList
              testIdPrefix="edit-church-conf"
              items={newConf}
              onRemove={(i) => removeAt(i, newConf, setNewConf)}
            />
            <View style={styles.addRow}>
              <TextInput
                testID="edit-church-conf-input"
                style={[styles.input, { flex: 1, marginRight: spacing.sm }]}
                value={confInput}
                onChangeText={setConfInput}
                placeholder='e.g. "Sat 3:30–4:30 PM"'
                placeholderTextColor={colors.textMuted}
                returnKeyType="done"
                onSubmitEditing={() =>
                  addItem(confInput, newConf, setNewConf, setConfInput)
                }
                maxLength={80}
              />
              <Pressable
                testID="edit-church-conf-add"
                onPress={() => addItem(confInput, newConf, setNewConf, setConfInput)}
                style={({ pressed }) => [styles.addBtn, pressed && styles.pressed]}
              >
                <Ionicons name="add" size={20} color={colors.gold} />
              </Pressable>
            </View>
          </Section>

          {/* Website */}
          <Section label="Website">
            <TextInput
              testID="edit-church-website"
              style={styles.input}
              value={website}
              onChangeText={setWebsite}
              placeholder="https://parish.example.org"
              placeholderTextColor={colors.textMuted}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
              maxLength={300}
            />
          </Section>

          {/* Phone */}
          <Section label="Phone">
            <TextInput
              testID="edit-church-phone"
              style={styles.input}
              value={phone}
              onChangeText={setPhone}
              placeholder="(555) 123-4567"
              placeholderTextColor={colors.textMuted}
              keyboardType="phone-pad"
              maxLength={60}
            />
          </Section>

          {/* Notes */}
          <Section label="Notes">
            <TextInput
              testID="edit-church-notes"
              style={[styles.input, styles.textarea]}
              value={notes}
              onChangeText={setNotes}
              placeholder="Anything helpful — Latin Mass, holy hours, side chapel access, parking..."
              placeholderTextColor={colors.textMuted}
              multiline
              maxLength={600}
            />
          </Section>

          {/* Attribution opt-in */}
          <View style={styles.attribCard} testID="edit-church-attribution-card">
            <View style={{ flex: 1 }}>
              <Text style={styles.attribTitle}>Credit me as a contributor</Text>
              <Text style={styles.attribBody}>
                {showName
                  ? `“${user?.name || "your name"}” will appear in this parish's contributor list.`
                  : "Off by default — your edits are anonymous unless you opt in."}
              </Text>
              {contributors.length > 0 ? (
                <Text style={styles.contributorList}>
                  Currently visible:{" "}
                  {contributors.slice(0, 3).join(", ")}
                  {contributors.length > 3 ? ` + ${contributors.length - 3} more` : ""}
                </Text>
              ) : null}
            </View>
            <Switch
              testID="edit-church-show-name"
              value={showName}
              onValueChange={setShowName}
              trackColor={{ false: colors.borderSoft, true: colors.gold }}
              thumbColor={Platform.OS === "android" ? colors.surface : undefined}
            />
          </View>

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Pressable
            testID="edit-church-submit"
            onPress={submit}
            disabled={submitting}
            style={({ pressed }) => [
              styles.submitBtn,
              (submitting || pressed) && styles.pressed,
            ]}
          >
            {submitting ? (
              <ActivityIndicator color={colors.gold} />
            ) : (
              <>
                <Ionicons name="checkmark-circle-outline" size={18} color={colors.gold} />
                <Text style={styles.submitBtnText}>Save Edits</Text>
              </>
            )}
          </Pressable>

          <Text style={styles.disclaimer}>
            Your edits are visible to everyone nearby. Please only contribute
            accurate, up-to-date information.
          </Text>
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ---- Sub-components ----

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionLabel}>{label}</Text>
      {children}
    </View>
  );
}

function ChipList({
  items,
  onRemove,
  testIdPrefix,
}: {
  items: string[];
  onRemove: (idx: number) => void;
  testIdPrefix: string;
}) {
  if (items.length === 0) return null;
  return (
    <View style={styles.chipList}>
      {items.map((it, i) => (
        <View key={i} style={styles.chip} testID={`${testIdPrefix}-chip-${i}`}>
          <Text style={styles.chipText}>{it}</Text>
          <Pressable
            testID={`${testIdPrefix}-remove-${i}`}
            onPress={() => onRemove(i)}
            hitSlop={8}
          >
            <Ionicons name="close" size={14} color={colors.textSecondary} />
          </Pressable>
        </View>
      ))}
    </View>
  );
}

// ---- styles ----

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  iconBtn: { width: 40, alignItems: "flex-start" },
  headerTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
  },
  scroll: { padding: spacing.lg, paddingBottom: spacing.xl },
  subjectCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.gold,
    padding: spacing.md,
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: spacing.lg,
    ...shadow.card,
  },
  subjectName: {
    fontFamily: fonts.headingSemi,
    fontSize: 16,
    color: colors.textPrimary,
  },
  subjectAddr: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textMuted,
    marginTop: 2,
  },
  attribution: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.liturgical.purple,
    marginTop: 6,
  },
  intro: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
    marginBottom: spacing.lg,
  },
  bold: { fontFamily: fonts.uiSemi },
  section: { marginBottom: spacing.lg },
  sectionLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    letterSpacing: 1.2,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  subLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.textMuted,
    marginBottom: 6,
  },
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textPrimary,
  },
  textarea: {
    minHeight: 90,
    textAlignVertical: "top",
  },
  addRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  addBtn: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  chipList: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginBottom: spacing.sm,
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.gold,
    backgroundColor: colors.background,
  },
  chipReadOnly: {
    borderColor: colors.borderSoft,
    backgroundColor: colors.surface,
  },
  chipText: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.textPrimary,
  },
  attribCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  attribTitle: {
    fontFamily: fonts.uiSemi,
    fontSize: 14,
    color: colors.textPrimary,
    marginBottom: 4,
  },
  attribBody: {
    fontFamily: fonts.bodyRegular,
    fontSize: 12,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  contributorList: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 6,
  },
  error: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: "#b1452e",
    marginBottom: spacing.md,
  },
  submitBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 14,
    borderRadius: radius.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    ...shadow.card,
  },
  submitBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 15,
    letterSpacing: 0.6,
  },
  disclaimer: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 12,
    color: colors.textMuted,
    textAlign: "center",
    marginTop: spacing.md,
    lineHeight: 18,
  },
  pressed: { opacity: 0.7 },
});

/**
 * Add Church — manual submission of a Catholic parish not present in OSM.
 *
 * Why this exists: OpenStreetMap coverage of small chapels, missions and
 * non-parochial Catholic communities (e.g. campus Newman centers, mission
 * outposts, oratories) is spotty. Users in those communities should still be
 * able to surface their parish to others nearby — so we let any signed-in
 * user post a name + coordinates + the basic schedule. The submission goes
 * into a *shared* `community_churches` collection so other users in the area
 * see it immediately (see `submit_community_church` in server.py).
 *
 * Design choices:
 *   • The user can either tap "Use my current location" (preferred — fastest,
 *     least error-prone) OR paste lat/lng manually. We never ask them to type
 *     coordinates from scratch because that's a UX disaster.
 *   • Mass / confession times are kept as free-form short strings ("Sun 9am",
 *     "Wed 7pm Latin Mass"). Real parishes use wildly inconsistent labels and
 *     a structured rrule editor is overkill for a v1.
 *   • Server enforces dedupe (~150m + same lowercased name) and per-user rate
 *     limit (5/day), so the UI can be optimistic — show a single submit toast
 *     and trust the backend to keep things sane.
 */
import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
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
import { Stack, useRouter } from "expo-router";
import * as Location from "expo-location";

import { api, ChurchItem } from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type PermStatus = "undetermined" | "granted" | "denied" | "blocked";

export default function AddChurchScreen() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [website, setWebsite] = useState("");
  const [phone, setPhone] = useState("");
  const [notes, setNotes] = useState("");
  const [lat, setLat] = useState<string>("");
  const [lng, setLng] = useState<string>("");

  const [massTimes, setMassTimes] = useState<string[]>([]);
  const [confessionTimes, setConfessionTimes] = useState<string[]>([]);
  const [massInput, setMassInput] = useState("");
  const [confInput, setConfInput] = useState("");

  const [locating, setLocating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [permStatus, setPermStatus] = useState<PermStatus>("undetermined");

  // --- helpers ----------------------------------------------------------
  const useMyLocation = useCallback(async () => {
    setError(null);
    setLocating(true);
    try {
      const current = await Location.getForegroundPermissionsAsync();
      let status: PermStatus = current.status as PermStatus;
      if (status !== "granted") {
        if (current.canAskAgain === false) {
          setPermStatus("blocked");
          setError(
            "Location is blocked for Sanctus. Open Settings to allow it, then try again."
          );
          return;
        }
        const req = await Location.requestForegroundPermissionsAsync();
        status = req.status as PermStatus;
        if (status !== "granted") {
          setPermStatus(req.canAskAgain === false ? "blocked" : "denied");
          setError("Location permission was not granted.");
          return;
        }
      }
      setPermStatus("granted");
      const pos = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      setLat(pos.coords.latitude.toFixed(6));
      setLng(pos.coords.longitude.toFixed(6));
    } catch (e) {
      setError((e as Error).message || "Could not get your location.");
    } finally {
      setLocating(false);
    }
  }, []);

  const addItem = (
    raw: string,
    list: string[],
    setList: (l: string[]) => void,
    setInput: (s: string) => void
  ) => {
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
    if (list.length >= 24) {
      Alert.alert("Limit reached", "You can add up to 24 time slots.");
      return;
    }
    setList([...list, s]);
    setInput("");
  };

  const removeAt = (idx: number, list: string[], setList: (l: string[]) => void) => {
    setList(list.filter((_, i) => i !== idx));
  };

  const submit = async () => {
    setError(null);
    if (name.trim().length < 2) {
      setError("Please enter the parish name.");
      return;
    }
    const lt = parseFloat(lat);
    const lg = parseFloat(lng);
    if (
      Number.isNaN(lt) ||
      Number.isNaN(lg) ||
      lt < -90 ||
      lt > 90 ||
      lg < -180 ||
      lg > 180
    ) {
      setError(
        "We need the church's location. Tap “Use my current location” while at the parish, or paste a valid lat/lng."
      );
      return;
    }
    setSubmitting(true);
    try {
      const created = await api<ChurchItem>("/churches/manual", {
        method: "POST",
        body: {
          name: name.trim(),
          lat: lt,
          lng: lg,
          address: address.trim() || undefined,
          website: website.trim() || undefined,
          phone: phone.trim() || undefined,
          notes: notes.trim() || undefined,
          mass_times: massTimes,
          confession_times: confessionTimes,
        },
      });
      Alert.alert(
        "Thank you",
        `“${created.name}” has been added to the community church directory.`,
        [
          {
            text: "OK",
            onPress: () => router.back(),
          },
        ]
      );
    } catch (e) {
      const msg = (e as Error).message || "Could not submit. Please try again.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  // --- render -----------------------------------------------------------
  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="add-church-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.headerRow}>
        <Pressable
          testID="add-church-back"
          onPress={() => router.back()}
          hitSlop={12}
          style={({ pressed }) => [styles.iconBtn, pressed && styles.pressed]}
        >
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Add a Church</Text>
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
          <Text style={styles.intro}>
            Catholic parishes, oratories, chapels and Newman centers that aren&apos;t
            showing up nearby. Once submitted, it&apos;s shared with everyone in the
            area — a small act of service for the next person looking for Mass.
          </Text>

          {/* Name */}
          <Section label="Parish name *">
            <TextInput
              testID="add-church-name"
              style={styles.input}
              value={name}
              onChangeText={setName}
              placeholder="St. Joseph Catholic Church"
              placeholderTextColor={colors.textMuted}
              maxLength={160}
              autoCapitalize="words"
            />
          </Section>

          {/* Address */}
          <Section label="Address (optional)">
            <TextInput
              testID="add-church-address"
              style={styles.input}
              value={address}
              onChangeText={setAddress}
              placeholder="123 Main St, Springfield, IL"
              placeholderTextColor={colors.textMuted}
              maxLength={240}
            />
          </Section>

          {/* Location */}
          <Section label="Location *">
            <Pressable
              testID="add-church-use-location"
              onPress={useMyLocation}
              disabled={locating}
              style={({ pressed }) => [
                styles.locBtn,
                pressed && styles.pressed,
                locating && { opacity: 0.6 },
              ]}
            >
              {locating ? (
                <ActivityIndicator color={colors.gold} />
              ) : (
                <>
                  <Ionicons name="locate-outline" size={16} color={colors.gold} />
                  <Text style={styles.locBtnText}>
                    {lat && lng ? "Update from my location" : "Use my current location"}
                  </Text>
                </>
              )}
            </Pressable>
            {permStatus === "blocked" ? (
              <Pressable
                onPress={() => Linking.openSettings()}
                style={({ pressed }) => [styles.linkBtn, pressed && styles.pressed]}
              >
                <Text style={styles.linkBtnText}>Open Settings to allow location</Text>
              </Pressable>
            ) : null}
            <View style={styles.coordRow}>
              <View style={[styles.coordCol, { marginRight: spacing.sm }]}>
                <Text style={styles.label}>Lat</Text>
                <TextInput
                  testID="add-church-lat"
                  style={styles.input}
                  value={lat}
                  onChangeText={setLat}
                  placeholder="40.7128"
                  placeholderTextColor={colors.textMuted}
                  keyboardType="numbers-and-punctuation"
                  inputMode="decimal"
                />
              </View>
              <View style={styles.coordCol}>
                <Text style={styles.label}>Lng</Text>
                <TextInput
                  testID="add-church-lng"
                  style={styles.input}
                  value={lng}
                  onChangeText={setLng}
                  placeholder="-74.0060"
                  placeholderTextColor={colors.textMuted}
                  keyboardType="numbers-and-punctuation"
                  inputMode="decimal"
                />
              </View>
            </View>
          </Section>

          {/* Mass times */}
          <Section label="Mass times (optional)">
            <ChipList
              testIdPrefix="add-church-mass"
              items={massTimes}
              onRemove={(i) => removeAt(i, massTimes, setMassTimes)}
            />
            <View style={styles.addRow}>
              <TextInput
                testID="add-church-mass-input"
                style={[styles.input, { flex: 1, marginRight: spacing.sm }]}
                value={massInput}
                onChangeText={setMassInput}
                placeholder='e.g. "Sun 9:00 AM" or "Daily 7 AM"'
                placeholderTextColor={colors.textMuted}
                returnKeyType="done"
                onSubmitEditing={() =>
                  addItem(massInput, massTimes, setMassTimes, setMassInput)
                }
                maxLength={80}
              />
              <Pressable
                testID="add-church-mass-add"
                onPress={() => addItem(massInput, massTimes, setMassTimes, setMassInput)}
                style={({ pressed }) => [styles.addBtn, pressed && styles.pressed]}
              >
                <Ionicons name="add" size={20} color={colors.gold} />
              </Pressable>
            </View>
          </Section>

          {/* Confession times */}
          <Section label="Confession times (optional)">
            <ChipList
              testIdPrefix="add-church-conf"
              items={confessionTimes}
              onRemove={(i) => removeAt(i, confessionTimes, setConfessionTimes)}
            />
            <View style={styles.addRow}>
              <TextInput
                testID="add-church-conf-input"
                style={[styles.input, { flex: 1, marginRight: spacing.sm }]}
                value={confInput}
                onChangeText={setConfInput}
                placeholder='e.g. "Sat 3:30–4:30 PM" or "By appointment"'
                placeholderTextColor={colors.textMuted}
                returnKeyType="done"
                onSubmitEditing={() =>
                  addItem(confInput, confessionTimes, setConfessionTimes, setConfInput)
                }
                maxLength={80}
              />
              <Pressable
                testID="add-church-conf-add"
                onPress={() =>
                  addItem(confInput, confessionTimes, setConfessionTimes, setConfInput)
                }
                style={({ pressed }) => [styles.addBtn, pressed && styles.pressed]}
              >
                <Ionicons name="add" size={20} color={colors.gold} />
              </Pressable>
            </View>
          </Section>

          {/* Website / phone */}
          <Section label="Website (optional)">
            <TextInput
              testID="add-church-website"
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

          <Section label="Phone (optional)">
            <TextInput
              testID="add-church-phone"
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
          <Section label="Notes (optional)">
            <TextInput
              testID="add-church-notes"
              style={[styles.input, styles.textarea]}
              value={notes}
              onChangeText={setNotes}
              placeholder="Anything helpful — Latin Mass, side chapel, holy hours, etc."
              placeholderTextColor={colors.textMuted}
              multiline
              maxLength={600}
            />
          </Section>

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Pressable
            testID="add-church-submit"
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
                <Text style={styles.submitBtnText}>Submit Parish</Text>
              </>
            )}
          </Pressable>

          <Text style={styles.disclaimer}>
            Submissions are visible to anyone nearby. Please only add real,
            currently-active Catholic places of worship.
          </Text>
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// --------------------------------------------------------------------------
// Sub-components
// --------------------------------------------------------------------------

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

// --------------------------------------------------------------------------
// Styles
// --------------------------------------------------------------------------
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
  intro: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
    marginBottom: spacing.lg,
  },
  section: {
    marginBottom: spacing.lg,
  },
  sectionLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    letterSpacing: 1.2,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  label: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.textMuted,
    marginBottom: 4,
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
  coordRow: {
    flexDirection: "row",
    marginTop: spacing.sm,
  },
  coordCol: { flex: 1 },
  locBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 12,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
  },
  locBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 14,
    letterSpacing: 0.4,
  },
  linkBtn: { marginTop: spacing.sm, alignSelf: "flex-start" },
  linkBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 13,
    textDecorationLine: "underline",
  },
  addRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: spacing.sm,
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
  chipText: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.textPrimary,
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

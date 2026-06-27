/**
 * Parish Events — list & create community-submitted Catholic events.
 *
 * Two entry points:
 *   1. From a specific church (`?church_id=…&church_name=…`) — shows only
 *      events for that parish.
 *   2. Standalone (no params) — shows nearby events using the user's location.
 *
 * Each event card supports:
 *   • Add to Calendar  →  expo-calendar (asks permission, creates a calendar
 *     in the local provider's default source, writes a single event with
 *     alarm at -30m). On iOS we use the default calendar; on Android we
 *     create or reuse a "Sanctus" calendar in the primary account.
 *   • Flag  →  POST /parish-events/{id}/flag. Three unique flags auto-hide
 *     the event server-side. We surface flag counts inline so things stay
 *     transparent.
 *   • Delete (owner only)  →  immediate hard delete.
 *
 * Create flow: bottom-sheet form with type picker, title, description, start
 * date + time, optional end time, optional address. We avoid a heavy native
 * date/time picker for v1 — quick chips ("Tonight 7pm", "Tomorrow 9am") plus
 * raw inputs cover most events.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Linking,
  Modal,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import * as Calendar from "expo-calendar";
import * as Location from "expo-location";

import { api, ParishEvent, ParishEventType, rsvpEvent } from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const EVENT_TYPES: { value: ParishEventType; label: string; icon: string }[] = [
  { value: "mass", label: "Mass", icon: "wine-outline" },
  { value: "confession", label: "Confession", icon: "git-pull-request-outline" },
  { value: "adoration", label: "Adoration", icon: "sunny-outline" },
  { value: "rosary", label: "Rosary", icon: "flower-outline" },
  { value: "talk", label: "Talk / Speaker", icon: "mic-outline" },
  { value: "retreat", label: "Retreat", icon: "leaf-outline" },
  { value: "service", label: "Service", icon: "hand-left-outline" },
  { value: "young_adult", label: "Young Adults", icon: "people-outline" },
  { value: "social", label: "Parish Social", icon: "fast-food-outline" },
  { value: "other", label: "Other", icon: "ellipsis-horizontal-outline" },
];

const TYPE_BY_VALUE = Object.fromEntries(EVENT_TYPES.map((t) => [t.value, t]));

const RECURRENCE_OPTIONS: { value: ParishEvent["recurrence"]; label: string }[] = [
  { value: "once", label: "Once" },
  { value: "weekly", label: "Weekly" },
  { value: "biweekly", label: "Bi-weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "annually", label: "Annually" },
];

export default function ParishEventsScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    church_id?: string;
    church_name?: string;
    lat?: string;
    lng?: string;
  }>();

  const churchId = typeof params.church_id === "string" ? params.church_id : undefined;
  const churchName = typeof params.church_name === "string" ? params.church_name : undefined;
  const paramLat = typeof params.lat === "string" ? parseFloat(params.lat) : NaN;
  const paramLng = typeof params.lng === "string" ? parseFloat(params.lng) : NaN;

  const [events, setEvents] = useState<ParishEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<ParishEventType | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [origin, setOrigin] = useState<{ lat: number; lng: number } | null>(
    !Number.isNaN(paramLat) && !Number.isNaN(paramLng) ? { lat: paramLat, lng: paramLng } : null
  );

  // Resolve a location if we don't already have one (standalone entry point).
  useEffect(() => {
    if (origin || churchId) return;
    (async () => {
      try {
        const perm = await Location.getForegroundPermissionsAsync();
        if (perm.status !== "granted") {
          if (perm.canAskAgain === false) return;
          const req = await Location.requestForegroundPermissionsAsync();
          if (req.status !== "granted") return;
        }
        const pos = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });
        setOrigin({ lat: pos.coords.latitude, lng: pos.coords.longitude });
      } catch {
        /* swallow — we'll just show an empty state */
      }
    })();
  }, [origin, churchId]);

  const load = useCallback(async () => {
    setError(null);
    try {
      const qs = new URLSearchParams();
      qs.set("days", "60");
      if (churchId) qs.set("church_id", churchId);
      else if (origin) {
        qs.set("lat", String(origin.lat));
        qs.set("lng", String(origin.lng));
        qs.set("radius_m", "40000");
      }
      if (filterType) qs.set("event_type", filterType);
      const res = await api<{ items: ParishEvent[] }>(`/parish-events?${qs.toString()}`);
      setEvents(res.items || []);
    } catch (e) {
      setError((e as Error).message || "Could not load events.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [churchId, origin, filterType]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  const onRefresh = () => {
    setRefreshing(true);
    load();
  };

  const flag = async (ev: ParishEvent) => {
    if (ev.is_owner) {
      Alert.alert("That's your event", "You can't flag your own submission.");
      return;
    }
    if (ev.has_flagged) {
      Alert.alert("Already reported", "Thanks — we've already received your report on this event.");
      return;
    }
    Alert.alert(
      "Report this event?",
      "Flag it for review if it's inaccurate, spam, or not a real Catholic event. Three unique flags auto-hide it.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Report",
          style: "destructive",
          onPress: async () => {
            try {
              await api(`/parish-events/${ev.id}/flag`, { method: "POST", body: {} });
              setEvents((prev) =>
                prev.map((e) =>
                  e.id === ev.id ? { ...e, has_flagged: true, flag_count: (e.flag_count || 0) + 1 } : e
                )
              );
            } catch (e) {
              Alert.alert("Could not report", (e as Error).message);
            }
          },
        },
      ]
    );
  };

  const remove = async (ev: ParishEvent) => {
    if (!ev.is_owner) return;
    Alert.alert("Delete this event?", "This cannot be undone.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await api(`/parish-events/${ev.id}`, { method: "DELETE" });
            setEvents((prev) => prev.filter((e) => e.id !== ev.id));
          } catch (e) {
            Alert.alert("Could not delete", (e as Error).message);
          }
        },
      },
    ]);
  };

  const goingToggle = async (ev: ParishEvent) => {
    try {
      const r = await rsvpEvent(ev.id);
      setEvents((prev) =>
        prev.map((e) => (e.id === ev.id ? { ...e, going: r.going, going_count: r.going_count } : e))
      );
    } catch (e) {
      Alert.alert("Could not update", (e as Error).message);
    }
  };

  const addToCalendar = async (ev: ParishEvent) => {
    try {
      const perm = await Calendar.getCalendarPermissionsAsync();
      let status = perm.status;
      if (status !== "granted") {
        if (perm.canAskAgain === false) {
          Alert.alert(
            "Calendar access blocked",
            "Open Settings to allow Sanctus to add events to your calendar.",
            [
              { text: "Cancel", style: "cancel" },
              { text: "Open Settings", onPress: () => Linking.openSettings() },
            ]
          );
          return;
        }
        const req = await Calendar.requestCalendarPermissionsAsync();
        status = req.status;
        if (status !== "granted") {
          Alert.alert("Permission denied", "We can't add the event without calendar access.");
          return;
        }
      }

      // Pick a writable calendar — default on iOS, "Sanctus" on Android.
      const calendars = await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT);
      let calId: string | undefined;
      if (Platform.OS === "ios") {
        // iOS exposes a `defaultCalendar` via getDefaultCalendarAsync.
        const def = await Calendar.getDefaultCalendarAsync().catch(() => null);
        calId = def?.id || calendars.find((c) => c.allowsModifications)?.id;
      } else {
        // Android — find a primary writable calendar, or create one.
        const writable = calendars.filter(
          (c) => c.allowsModifications && c.accessLevel === Calendar.CalendarAccessLevel.OWNER
        );
        const existing = writable.find((c) => c.title === "Sanctus") || writable[0];
        if (existing) {
          calId = existing.id;
        } else {
          const sources = calendars
            .map((c) => c.source)
            .filter((s) => s && (s.type === "com.google" || s.isLocalAccount));
          const src = sources[0];
          if (!src) {
            Alert.alert("No calendar account", "Add a Google or local calendar account first.");
            return;
          }
          calId = await Calendar.createCalendarAsync({
            title: "Sanctus",
            color: "#7E5BEF",
            entityType: Calendar.EntityTypes.EVENT,
            sourceId: src.id,
            source: src,
            name: "Sanctus parish events",
            ownerAccount: src.name || "personal",
            accessLevel: Calendar.CalendarAccessLevel.OWNER,
          });
        }
      }

      if (!calId) {
        Alert.alert("No calendar found", "Could not find a writable calendar on this device.");
        return;
      }

      const start = new Date(ev.start_at);
      const end = ev.end_at ? new Date(ev.end_at) : new Date(start.getTime() + 60 * 60 * 1000);
      await Calendar.createEventAsync(calId, {
        title: ev.title,
        startDate: start,
        endDate: end,
        notes: [ev.description, ev.church_name ? `Parish: ${ev.church_name}` : null]
          .filter(Boolean)
          .join("\n\n"),
        location: ev.address || ev.church_name || undefined,
        alarms: [{ relativeOffset: -30 }],
      });
      Alert.alert("Added to calendar", `“${ev.title}” saved with a 30-minute reminder.`);
    } catch (e) {
      Alert.alert("Could not add", (e as Error).message);
    }
  };

  const visibleTitle = churchName || "Parish Events";

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="parish-events-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.headerRow}>
        <Pressable
          testID="parish-events-back"
          onPress={() => router.back()}
          hitSlop={12}
          style={({ pressed }) => [styles.iconBtn, pressed && styles.pressed]}
        >
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle} numberOfLines={1}>
          {visibleTitle}
        </Text>
        <Pressable
          testID="parish-events-create-fab"
          onPress={() => setShowCreate(true)}
          hitSlop={12}
          style={({ pressed }) => [styles.iconBtn, pressed && styles.pressed]}
        >
          <Ionicons name="add" size={28} color={colors.primary} />
        </Pressable>
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.chipsRow}
      >
        <FilterChip
          label="All"
          active={filterType === null}
          onPress={() => setFilterType(null)}
        />
        {EVENT_TYPES.map((t) => (
          <FilterChip
            key={t.value}
            label={t.label}
            icon={t.icon}
            active={filterType === t.value}
            onPress={() => setFilterType(filterType === t.value ? null : t.value)}
          />
        ))}
      </ScrollView>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.gold} />
        }
      >
        {loading ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
        ) : error ? (
          <Text style={styles.error}>{error}</Text>
        ) : events.length === 0 ? (
          <View style={styles.emptyBox}>
            <Ionicons
              name="calendar-clear-outline"
              size={36}
              color={colors.textMuted}
              style={{ marginBottom: spacing.sm }}
            />
            <Text style={styles.empty}>
              No upcoming events {churchName ? `at ${churchName}` : "nearby"} yet.
            </Text>
            <Text style={styles.emptyHint}>
              Be the first to share one — tap the + above.
            </Text>
          </View>
        ) : (
          events.map((ev) => (
            <EventCard
              key={ev.occurrence_key || ev.id}
              ev={ev}
              onAddToCalendar={() => addToCalendar(ev)}
              onFlag={() => flag(ev)}
              onDelete={() => remove(ev)}
              onGoing={() => goingToggle(ev)}
            />
          ))
        )}
        <View style={{ height: spacing.xl }} />
      </ScrollView>

      <CreateEventModal
        visible={showCreate}
        defaultChurch={
          churchId
            ? {
                church_id: churchId,
                church_name: churchName || "",
                lat: paramLat,
                lng: paramLng,
              }
            : null
        }
        fallbackOrigin={origin}
        onClose={() => setShowCreate(false)}
        onCreated={() => {
          setShowCreate(false);
          setLoading(true);
          load();
        }}
      />
    </SafeAreaView>
  );
}

// -------------------- Sub-components --------------------

function FilterChip({
  label,
  icon,
  active,
  onPress,
}: {
  label: string;
  icon?: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.chip,
        active && styles.chipActive,
        pressed && styles.pressed,
      ]}
    >
      {icon ? (
        <Ionicons
          name={icon as any}
          size={13}
          color={active ? colors.gold : colors.textSecondary}
        />
      ) : null}
      <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
    </Pressable>
  );
}

function EventCard({
  ev,
  onAddToCalendar,
  onFlag,
  onDelete,
  onGoing,
}: {
  ev: ParishEvent;
  onAddToCalendar: () => void;
  onFlag: () => void;
  onDelete: () => void;
  onGoing: () => void;
}) {
  const t = TYPE_BY_VALUE[ev.type] || EVENT_TYPES[EVENT_TYPES.length - 1];
  const start = new Date(ev.start_at);
  const dateStr = start.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  const timeStr = start.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
  return (
    <View style={styles.card} testID={`event-${ev.id}`}>
      <View style={styles.cardTop}>
        <View style={styles.typeBadge}>
          <Ionicons name={t.icon as any} size={14} color={colors.gold} />
          <Text style={styles.typeBadgeText}>{ev.type_label}</Text>
        </View>
        <Text style={styles.dateText}>
          {dateStr} · {timeStr}
        </Text>
      </View>
      <Text style={styles.title}>{ev.title}</Text>
      {ev.recurrence && ev.recurrence !== "once" ? (
        <View style={styles.recurBadge}>
          <Ionicons name="repeat" size={12} color={colors.gold} />
          <Text style={styles.recurBadgeText}>{ev.recurrence_label || "Repeats"}</Text>
        </View>
      ) : null}
      {ev.church_name ? <Text style={styles.churchLine}>{ev.church_name}</Text> : null}
      {ev.address ? <Text style={styles.addressLine}>{ev.address}</Text> : null}
      {ev.description ? (
        <Text style={styles.descLine} numberOfLines={4}>
          {ev.description}
        </Text>
      ) : null}
      <View style={styles.metaRow}>
        <Text style={styles.metaText}>
          submitted by {ev.organizer_name || "a Sanctus user"}
        </Text>
        {ev.flag_count > 0 ? (
          <Text style={styles.flagCount}>{ev.flag_count} flag{ev.flag_count > 1 ? "s" : ""}</Text>
        ) : null}
      </View>
      <View style={styles.actionsRow}>
        <Pressable
          testID={`event-going-${ev.id}`}
          onPress={onGoing}
          style={({ pressed }) => [
            styles.primaryBtn,
            ev.going && styles.goingBtnActive,
            pressed && styles.pressed,
          ]}
        >
          <Ionicons
            name={ev.going ? "checkmark-circle" : "checkmark-circle-outline"}
            size={16}
            color={ev.going ? colors.surface : colors.gold}
          />
          <Text style={[styles.primaryBtnText, ev.going && styles.goingBtnTextActive]}>
            {ev.going ? `Going${ev.going_count ? ` · ${ev.going_count}` : ""}` : "I'm going"}
          </Text>
        </Pressable>
        <Pressable
          testID={`event-calendar-${ev.id}`}
          onPress={onAddToCalendar}
          style={({ pressed }) => [styles.secondaryBtn, pressed && styles.pressed]}
        >
          <Ionicons name="calendar-outline" size={16} color={colors.primary} />
        </Pressable>
        {ev.is_owner ? (
          <Pressable
            testID={`event-delete-${ev.id}`}
            onPress={onDelete}
            style={({ pressed }) => [styles.secondaryBtn, pressed && styles.pressed]}
          >
            <Ionicons name="trash-outline" size={16} color={colors.liturgical.red} />
          </Pressable>
        ) : (
          <Pressable
            testID={`event-flag-${ev.id}`}
            onPress={onFlag}
            style={({ pressed }) => [styles.secondaryBtn, pressed && styles.pressed]}
          >
            <Ionicons
              name={ev.has_flagged ? "flag" : "flag-outline"}
              size={16}
              color={ev.has_flagged ? colors.liturgical.red : colors.textSecondary}
            />
          </Pressable>
        )}
      </View>
    </View>
  );
}

// -------------------- Create modal --------------------

function CreateEventModal({
  visible,
  defaultChurch,
  fallbackOrigin,
  onClose,
  onCreated,
}: {
  visible: boolean;
  defaultChurch: {
    church_id: string;
    church_name: string;
    lat: number;
    lng: number;
  } | null;
  fallbackOrigin: { lat: number; lng: number } | null;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [type, setType] = useState<ParishEventType>("mass");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [address, setAddress] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [recurrence, setRecurrence] = useState<ParishEvent["recurrence"]>("once");
  const [activeQuick, setActiveQuick] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (visible) {
      setType("mass");
      setTitle("");
      setDescription("");
      setAddress("");
      // Default to tomorrow at 7 PM (a common parish event slot).
      const t = new Date();
      t.setDate(t.getDate() + 1);
      setDate(
        `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(
          t.getDate()
        ).padStart(2, "0")}`
      );
      setTime("19:00");
      setEndTime("");
      setRecurrence("once");
      setActiveQuick(null);
      setSubmitting(false);
      setErr(null);
    }
  }, [visible]);

  const quickSet = (label: string) => {
    setActiveQuick(label);
    const now = new Date();
    if (label === "tonight") {
      now.setHours(19, 0, 0, 0);
    } else if (label === "tomorrow") {
      now.setDate(now.getDate() + 1);
      now.setHours(9, 0, 0, 0);
    } else if (label === "sunday") {
      const dow = now.getDay();
      const add = dow === 0 ? 7 : 7 - dow;
      now.setDate(now.getDate() + add);
      now.setHours(10, 0, 0, 0);
    }
    setDate(
      `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(
        now.getDate()
      ).padStart(2, "0")}`
    );
    setTime(
      `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`
    );
  };

  const submit = async () => {
    setErr(null);
    if (title.trim().length < 3) {
      setErr("Please give the event a clear title (3+ characters).");
      return;
    }
    const dt = parseLocalDateTime(date, time);
    if (!dt) {
      setErr("Please enter a valid date (YYYY-MM-DD) and time (HH:MM, 24h).");
      return;
    }
    let endIso: string | undefined;
    if (endTime.trim()) {
      const endDt = parseLocalDateTime(date, endTime);
      if (!endDt || endDt <= dt) {
        setErr("End time must be after the start time.");
        return;
      }
      endIso = endDt.toISOString();
    }
    const origin =
      defaultChurch && !Number.isNaN(defaultChurch.lat) && !Number.isNaN(defaultChurch.lng)
        ? { lat: defaultChurch.lat, lng: defaultChurch.lng }
        : fallbackOrigin;
    if (!origin) {
      setErr("We need a location for this event. Open from a church card or enable location.");
      return;
    }
    setSubmitting(true);
    try {
      await api<ParishEvent>("/parish-events", {
        method: "POST",
        body: {
          type,
          title: title.trim(),
          description: description.trim() || undefined,
          start_at: dt.toISOString(),
          end_at: endIso,
          church_id: defaultChurch?.church_id,
          church_name: defaultChurch?.church_name || undefined,
          address: address.trim() || undefined,
          lat: origin.lat,
          lng: origin.lng,
          recurrence,
        },
      });
      onCreated();
    } catch (e) {
      setErr((e as Error).message || "Could not create event.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView
        style={modalStyles.safe}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View style={modalStyles.header}>
          <Pressable
            testID="event-modal-close"
            onPress={onClose}
            hitSlop={12}
            style={({ pressed }) => [styles.iconBtn, pressed && styles.pressed]}
          >
            <Ionicons name="close" size={26} color={colors.textPrimary} />
          </Pressable>
          <Text style={modalStyles.headerTitle}>New Event</Text>
          <View style={{ width: 40 }} />
        </View>

        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={modalStyles.scroll}
          keyboardShouldPersistTaps="handled"
        >
          {defaultChurch ? (
            <Text style={modalStyles.churchLine}>
              <Ionicons name="business-outline" size={14} color={colors.textMuted} />{" "}
              {defaultChurch.church_name}
            </Text>
          ) : null}

          <Text style={modalStyles.label}>Type</Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.chipsRow}
          >
            {EVENT_TYPES.map((t) => (
              <FilterChip
                key={t.value}
                label={t.label}
                icon={t.icon}
                active={type === t.value}
                onPress={() => setType(t.value)}
              />
            ))}
          </ScrollView>

          <Text style={modalStyles.label}>Title *</Text>
          <TextInput
            testID="event-title-input"
            style={styles.input}
            value={title}
            onChangeText={setTitle}
            placeholder='e.g. "Healing Mass" or "First Friday Adoration"'
            placeholderTextColor={colors.textMuted}
            maxLength={120}
          />

          <Text style={modalStyles.label}>When *</Text>
          <View style={modalStyles.quickRow}>
            <Pressable
              testID="event-quick-tonight"
              onPress={() => quickSet("tonight")}
              style={({ pressed }) => [styles.chip, activeQuick === "tonight" && styles.chipActive, pressed && styles.pressed]}
            >
              <Text style={[styles.chipText, activeQuick === "tonight" && styles.chipTextActive]}>Tonight 7pm</Text>
            </Pressable>
            <Pressable
              testID="event-quick-tomorrow"
              onPress={() => quickSet("tomorrow")}
              style={({ pressed }) => [styles.chip, activeQuick === "tomorrow" && styles.chipActive, pressed && styles.pressed]}
            >
              <Text style={[styles.chipText, activeQuick === "tomorrow" && styles.chipTextActive]}>Tomorrow 9am</Text>
            </Pressable>
            <Pressable
              testID="event-quick-sunday"
              onPress={() => quickSet("sunday")}
              style={({ pressed }) => [styles.chip, activeQuick === "sunday" && styles.chipActive, pressed && styles.pressed]}
            >
              <Text style={[styles.chipText, activeQuick === "sunday" && styles.chipTextActive]}>Next Sunday 10am</Text>
            </Pressable>
          </View>
          <View style={modalStyles.dateRow}>
            <View style={{ flex: 1, marginRight: spacing.sm }}>
              <Text style={modalStyles.subLabel}>Date</Text>
              <TextInput
                testID="event-date-input"
                style={styles.input}
                value={date}
                onChangeText={setDate}
                placeholder="2026-06-15"
                placeholderTextColor={colors.textMuted}
                autoCapitalize="none"
                keyboardType="numbers-and-punctuation"
              />
            </View>
            <View style={{ flex: 1, marginRight: spacing.sm }}>
              <Text style={modalStyles.subLabel}>Start (24h)</Text>
              <TextInput
                testID="event-time-input"
                style={styles.input}
                value={time}
                onChangeText={setTime}
                placeholder="19:00"
                placeholderTextColor={colors.textMuted}
                keyboardType="numbers-and-punctuation"
              />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={modalStyles.subLabel}>End (opt)</Text>
              <TextInput
                testID="event-endtime-input"
                style={styles.input}
                value={endTime}
                onChangeText={setEndTime}
                placeholder="20:30"
                placeholderTextColor={colors.textMuted}
                keyboardType="numbers-and-punctuation"
              />
            </View>
          </View>

          <Text style={modalStyles.label}>Repeats</Text>
          <View style={modalStyles.quickRow}>
            {RECURRENCE_OPTIONS.map((r) => (
              <Pressable
                key={r.value}
                testID={`event-recurrence-${r.value}`}
                onPress={() => setRecurrence(r.value)}
                style={({ pressed }) => [styles.chip, recurrence === r.value && styles.chipActive, pressed && styles.pressed]}
              >
                <Text style={[styles.chipText, recurrence === r.value && styles.chipTextActive]}>{r.label}</Text>
              </Pressable>
            ))}
          </View>
          {recurrence !== "once" ? (
            <Text style={modalStyles.recurHint}>
              Repeats {RECURRENCE_OPTIONS.find((r) => r.value === recurrence)?.label.toLowerCase()} from the start date you chose.
            </Text>
          ) : null}

          <Text style={modalStyles.label}>Address (optional)</Text>
          <TextInput
            testID="event-address-input"
            style={styles.input}
            value={address}
            onChangeText={setAddress}
            placeholder={defaultChurch?.church_name || "Where it's happening"}
            placeholderTextColor={colors.textMuted}
            maxLength={240}
          />

          <Text style={modalStyles.label}>Description (optional)</Text>
          <TextInput
            testID="event-description-input"
            style={[styles.input, { minHeight: 100, textAlignVertical: "top" }]}
            value={description}
            onChangeText={setDescription}
            placeholder="What is it? Anyone welcome? Bring a dish?"
            placeholderTextColor={colors.textMuted}
            multiline
            maxLength={2000}
          />

          {err ? <Text style={styles.error}>{err}</Text> : null}

          <Pressable
            testID="event-submit"
            onPress={submit}
            disabled={submitting}
            style={({ pressed }) => [
              modalStyles.submit,
              (submitting || pressed) && styles.pressed,
            ]}
          >
            {submitting ? (
              <ActivityIndicator color={colors.gold} />
            ) : (
              <>
                <Ionicons name="checkmark-circle-outline" size={18} color={colors.gold} />
                <Text style={styles.primaryBtnText}>Post Event</Text>
              </>
            )}
          </Pressable>
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </Modal>
  );
}

// -------------------- helpers --------------------

function parseLocalDateTime(date: string, time: string): Date | null {
  // Build a Date in the user's local timezone from "YYYY-MM-DD" + "HH:MM".
  const dMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date.trim());
  const tMatch = /^(\d{1,2}):(\d{2})$/.exec(time.trim());
  if (!dMatch || !tMatch) return null;
  const y = parseInt(dMatch[1], 10);
  const mo = parseInt(dMatch[2], 10) - 1;
  const d = parseInt(dMatch[3], 10);
  const h = parseInt(tMatch[1], 10);
  const mi = parseInt(tMatch[2], 10);
  if (h < 0 || h > 23 || mi < 0 || mi > 59 || mo < 0 || mo > 11 || d < 1 || d > 31) return null;
  const dt = new Date(y, mo, d, h, mi, 0, 0);
  if (Number.isNaN(dt.getTime())) return null;
  return dt;
}

// -------------------- styles --------------------

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
  iconBtn: { width: 40, alignItems: "center" },
  headerTitle: {
    flex: 1,
    textAlign: "center",
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
  },
  chipsRow: {
    flexDirection: "row",
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    backgroundColor: colors.surface,
  },
  chipActive: {
    borderColor: colors.gold,
    backgroundColor: colors.primary,
  },
  chipText: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.textSecondary,
    letterSpacing: 0.4,
  },
  chipTextActive: {
    color: colors.gold,
  },
  scroll: { padding: spacing.lg, paddingTop: 0 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    ...shadow.card,
  },
  cardTop: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.sm,
  },
  typeBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.gold,
    backgroundColor: colors.background,
  },
  typeBadgeText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.gold,
    letterSpacing: 0.4,
  },
  dateText: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.textSecondary,
  },
  title: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
    marginBottom: 4,
  },
  churchLine: {
    fontFamily: fonts.uiSemi,
    fontSize: 13,
    color: colors.textSecondary,
    marginBottom: 2,
  },
  addressLine: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  descLine: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 22,
    marginBottom: spacing.sm,
  },
  metaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: spacing.sm,
  },
  metaText: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 11,
    color: colors.textMuted,
  },
  flagCount: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.liturgical.red,
  },
  actionsRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  primaryBtn: {
    flex: 1,
    backgroundColor: colors.primary,
    paddingVertical: 12,
    borderRadius: radius.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
  },
  primaryBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 13,
    letterSpacing: 0.4,
  },
  secondaryBtn: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
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
    marginBottom: spacing.md,
  },
  error: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: "#b1452e",
    marginBottom: spacing.md,
  },
  emptyBox: {
    alignItems: "center",
    paddingVertical: spacing.xl,
  },
  empty: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: "center",
    marginBottom: 4,
  },
  emptyHint: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.gold,
    letterSpacing: 0.4,
  },
  recurBadge: { flexDirection: "row", alignItems: "center", gap: 4, alignSelf: "flex-start", paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.round, backgroundColor: colors.primary, marginBottom: spacing.sm },
  recurBadgeText: { fontFamily: fonts.uiSemi, fontSize: 10, color: colors.gold, letterSpacing: 0.3 },
  goingBtnActive: { backgroundColor: "#1E5631", borderColor: "#1E5631" },
  goingBtnTextActive: { color: colors.surface },
  pressed: { opacity: 0.7 },
});

const modalStyles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  headerTitle: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
  },
  scroll: { padding: spacing.lg },
  label: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    letterSpacing: 1.2,
    color: colors.textMuted,
    marginBottom: spacing.sm,
    marginTop: spacing.sm,
  },
  subLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.textMuted,
    marginBottom: 4,
  },
  churchLine: {
    fontFamily: fonts.uiSemi,
    fontSize: 13,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  quickRow: {
    flexDirection: "row",
    gap: spacing.sm,
    marginBottom: spacing.sm,
    flexWrap: "wrap",
  },
  recurHint: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 12,
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  dateRow: {
    flexDirection: "row",
  },
  submit: {
    backgroundColor: colors.primary,
    paddingVertical: 14,
    borderRadius: radius.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
});

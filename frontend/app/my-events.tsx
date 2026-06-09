/**
 * My Events — list and manage events the current user has created.
 *
 * Why this exists: the user asked for a "My Events" entry on the Profile tab.
 * Without it, organizers had no way to revisit or cancel the events they had
 * posted to their parishes.
 *
 * Design choices:
 *   • One screen, one fetch (`GET /parish-events/me/list`). The backend
 *     filters by organizer_user_id and excludes removed events.
 *   • Each row shows title, type, when, and the church it's tied to. Tap to
 *     navigate into the Parish Events screen scoped to that church (since
 *     that's where event editing/flagging lives).
 *   • Owner-only delete: we already get `is_owner=true` from the backend on
 *     every row, but we also do a client-side confirmation because deletes
 *     are destructive.
 *   • Empty state nudges the user to create an event from a saved church.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { api, ParishEvent } from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const TYPE_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  mass: "wine-outline",
  confession: "shield-checkmark-outline",
  adoration: "sparkles-outline",
  talk: "mic-outline",
  retreat: "leaf-outline",
  service: "hand-left-outline",
  young_adult: "people-outline",
  social: "cafe-outline",
  rosary: "ellipsis-horizontal-circle-outline",
  other: "calendar-outline",
};

function formatWhen(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function MyEventsScreen() {
  const router = useRouter();
  const [items, setItems] = useState<ParishEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await api<{ items: ParishEvent[] }>("/parish-events/me/list");
      setItems(res.items || []);
    } catch (e) {
      setError((e as Error).message || "Could not load your events.");
    }
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

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await load();
    } finally {
      setRefreshing(false);
    }
  };

  const cancel = (ev: ParishEvent) => {
    Alert.alert(
      "Cancel this event?",
      `"${ev.title}" will be removed for everyone. This can't be undone.`,
      [
        { text: "Keep it", style: "cancel" },
        {
          text: "Cancel event",
          style: "destructive",
          onPress: async () => {
            try {
              await api(`/parish-events/${encodeURIComponent(ev.id)}`, {
                method: "DELETE",
              });
              setItems((arr) => arr.filter((x) => x.id !== ev.id));
            } catch (e) {
              Alert.alert("Could not cancel", (e as Error).message || "Try again later.");
            }
          },
        },
      ],
    );
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="my-events-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.headerRow}>
        <Pressable
          testID="my-events-back"
          onPress={() => router.back()}
          hitSlop={12}
          style={({ pressed }) => [styles.iconBtn, pressed && styles.pressed]}
        >
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>My Events</Text>
        <View style={{ width: 40 }} />
      </View>

      {loading ? (
        <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xxl }} />
      ) : (
        <ScrollView
          contentContainerStyle={styles.scroll}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={colors.gold}
            />
          }
        >
          {error ? <Text style={styles.error}>{error}</Text> : null}
          {items.length === 0 ? (
            <View style={styles.emptyCard}>
              <Ionicons name="calendar-outline" size={36} color={colors.gold} />
              <Text style={styles.emptyTitle}>No events yet</Text>
              <Text style={styles.emptyBody}>
                When you post a Mass time, holy hour, or parish gathering, it will
                show up here so you can update or cancel it.
              </Text>
              <Pressable
                testID="my-events-go-churches"
                onPress={() => router.push("/churches")}
                style={({ pressed }) => [styles.primaryBtn, pressed && styles.pressed]}
              >
                <Ionicons name="business-outline" size={16} color={colors.gold} />
                <Text style={styles.primaryBtnText}>Browse my parishes</Text>
              </Pressable>
            </View>
          ) : (
            items.map((ev) => (
              <View key={ev.id} style={styles.card} testID={`my-event-${ev.id}`}>
                <View style={styles.cardHeader}>
                  <View style={styles.typeBadge}>
                    <Ionicons
                      name={TYPE_ICONS[ev.type] || "calendar-outline"}
                      size={14}
                      color={colors.gold}
                    />
                    <Text style={styles.typeBadgeText}>{ev.type_label}</Text>
                  </View>
                  <Pressable
                    testID={`my-event-cancel-${ev.id}`}
                    onPress={() => cancel(ev)}
                    hitSlop={8}
                    style={({ pressed }) => [styles.cancelBtn, pressed && styles.pressed]}
                  >
                    <Ionicons name="trash-outline" size={16} color={colors.liturgical.red} />
                  </Pressable>
                </View>
                <Text style={styles.title}>{ev.title}</Text>
                <View style={styles.metaRow}>
                  <Ionicons name="time-outline" size={14} color={colors.textMuted} />
                  <Text style={styles.metaText}>{formatWhen(ev.start_at)}</Text>
                </View>
                {ev.church_name ? (
                  <View style={styles.metaRow}>
                    <Ionicons name="business-outline" size={14} color={colors.textMuted} />
                    <Text style={styles.metaText} numberOfLines={1}>
                      {ev.church_name}
                    </Text>
                  </View>
                ) : null}
                {ev.description ? (
                  <Text style={styles.body} numberOfLines={3}>
                    {ev.description}
                  </Text>
                ) : null}
                {ev.flag_count > 0 ? (
                  <Text style={styles.flagMeta}>
                    {ev.flag_count} flag{ev.flag_count === 1 ? "" : "s"}
                  </Text>
                ) : null}
                <Pressable
                  testID={`my-event-open-${ev.id}`}
                  onPress={() =>
                    router.push({
                      pathname: "/parish-events",
                      params: {
                        church_id: ev.church_id || "",
                        church_name: ev.church_name || "",
                        lat: String(ev.lat),
                        lng: String(ev.lng),
                      },
                    })
                  }
                  style={({ pressed }) => [styles.openBtn, pressed && styles.pressed]}
                >
                  <Ionicons name="open-outline" size={14} color={colors.primary} />
                  <Text style={styles.openBtnText}>Open at parish</Text>
                </Pressable>
              </View>
            ))
          )}
          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

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
    fontFamily: fonts.headingBold,
    fontSize: 22,
    color: colors.textPrimary,
  },
  scroll: { padding: spacing.lg },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginBottom: spacing.md,
    ...shadow.card,
  },
  cardHeader: {
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
    backgroundColor: colors.primary,
    borderRadius: radius.round,
  },
  typeBadgeText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.gold,
    letterSpacing: 0.4,
  },
  cancelBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.liturgical.red,
  },
  title: {
    fontFamily: fonts.headingSemi,
    fontSize: 18,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 4,
  },
  metaText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textSecondary,
    flex: 1,
  },
  body: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textPrimary,
    lineHeight: 20,
    marginTop: 6,
  },
  flagMeta: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    fontSize: 11,
    color: colors.liturgical.red,
    marginTop: 4,
  },
  openBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    marginTop: spacing.md,
    paddingVertical: 8,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.background,
  },
  openBtnText: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.primary,
  },
  emptyCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.xl,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    alignItems: "center",
    marginTop: spacing.xl,
    ...shadow.card,
  },
  emptyTitle: {
    fontFamily: fonts.headingBold,
    fontSize: 20,
    color: colors.textPrimary,
    marginTop: spacing.sm,
  },
  emptyBody: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 20,
    textAlign: "center",
    marginTop: spacing.sm,
    marginBottom: spacing.md,
  },
  primaryBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 12,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  primaryBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 14,
    letterSpacing: 0.4,
  },
  error: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.liturgical.red,
    marginBottom: spacing.md,
    textAlign: "center",
  },
  pressed: { opacity: 0.7 },
});

import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Image,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { ShopOrder, listMyOrders } from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

function formatPrice(cents?: number): string {
  if (cents == null) return "";
  return `$${(cents / 100).toFixed(2)}`;
}

function statusBadge(status: ShopOrder["status"]) {
  switch (status) {
    case "paid":
      return { label: "Paid", color: colors.liturgical.green };
    case "pending":
      return { label: "Pending", color: colors.gold };
    case "cancelled":
      return { label: "Cancelled", color: colors.textMuted };
    case "failed":
      return { label: "Failed", color: colors.liturgical.red };
    default:
      return { label: status, color: colors.textMuted };
  }
}

export default function MyOrdersScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [orders, setOrders] = useState<ShopOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    if (!user) return;
    try {
      const r = await listMyOrders();
      setOrders(r.orders);
    } catch (e) {
      console.warn("orders load failed", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [user]);

  useEffect(() => { load(); }, [load]);

  const renderItem = ({ item }: { item: ShopOrder }) => {
    const badge = statusBadge(item.status);
    return (
      <View style={styles.card}>
        {item.product_image_url ? (
          <Image source={{ uri: item.product_image_url }} style={styles.thumb} resizeMode="cover" />
        ) : (
          <View style={[styles.thumb, styles.thumbPlaceholder]}>
            <Ionicons name="cube-outline" size={22} color={colors.textMuted} />
          </View>
        )}
        <View style={{ flex: 1 }}>
          <Text style={styles.name} numberOfLines={1}>{item.product_name || item.product_id}</Text>
          <Text style={styles.meta}>Qty {item.quantity} · {formatPrice(item.total_cents)}</Text>
          {item.tracking_number ? (
            <Text style={styles.tracking}>Tracking: {item.tracking_number}</Text>
          ) : null}
          <Text style={styles.dateLine}>{item.created_at ? new Date(item.created_at).toLocaleDateString() : ""}</Text>
        </View>
        <View style={[styles.badge, { backgroundColor: badge.color + "22", borderColor: badge.color }]}>
          <Text style={[styles.badgeText, { color: badge.color }]}>{badge.label}</Text>
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.headerBtn}>
          <Ionicons name="chevron-back" size={24} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>My Orders</Text>
        <View style={styles.headerBtn} />
      </View>
      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.primary} /></View>
      ) : (
        <FlatList
          data={orders}
          keyExtractor={(o) => o.order_id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor={colors.primary} />}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="receipt-outline" size={48} color={colors.textMuted} />
              <Text style={styles.emptyTitle}>No orders yet</Text>
              <Pressable onPress={() => router.replace("/shop")} style={({ pressed }) => [styles.emptyBtn, pressed && { opacity: 0.8 }]}>
                <Text style={styles.emptyBtnText}>Browse Shop</Text>
              </Pressable>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, backgroundColor: colors.surface },
  headerBtn: { padding: spacing.xs, width: 44 },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingBold, fontSize: 20, color: colors.primary },
  list: { padding: spacing.md, gap: spacing.sm },
  card: { flexDirection: "row", alignItems: "center", gap: spacing.sm, padding: spacing.sm, backgroundColor: colors.surface, borderRadius: radius.lg, ...shadow.card, marginBottom: spacing.sm },
  thumb: { width: 64, height: 64, borderRadius: radius.md, backgroundColor: colors.background },
  thumbPlaceholder: { alignItems: "center", justifyContent: "center" },
  name: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  meta: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  tracking: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.primary, marginTop: 2 },
  dateLine: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  badge: { borderRadius: radius.round, paddingHorizontal: 10, paddingVertical: 3, borderWidth: 1 },
  badgeText: { fontFamily: fonts.uiSemi, fontSize: 11 },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  empty: { alignItems: "center", padding: spacing.xl, gap: spacing.sm },
  emptyTitle: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.primary },
  emptyBtn: { marginTop: spacing.md, paddingHorizontal: spacing.lg, paddingVertical: 10, borderRadius: radius.round, backgroundColor: colors.primary },
  emptyBtnText: { fontFamily: fonts.uiSemi, fontSize: 13, color: "#fff" },
});

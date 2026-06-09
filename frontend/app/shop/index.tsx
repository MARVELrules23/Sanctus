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

import { ShopProduct, listShopProducts } from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

function formatPrice(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

export default function ShopIndex() {
  const router = useRouter();
  const { user } = useAuth();
  const [products, setProducts] = useState<ShopProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [shipping, setShipping] = useState(500);

  const load = useCallback(async () => {
    if (!user) return;
    try {
      const r = await listShopProducts();
      setProducts(r.products);
      setShipping(r.shipping_amount_cents || 500);
    } catch (e) {
      console.warn("shop load failed", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [user]);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    load();
  }, [load]);

  const renderItem = ({ item }: { item: ShopProduct }) => (
    <Pressable
      onPress={() => router.push(`/shop/${item.product_id}`)}
      style={({ pressed }) => [styles.card, pressed && { opacity: 0.85 }]}
    >
      {item.image_url ? (
        <Image source={{ uri: item.image_url }} style={styles.image} resizeMode="cover" />
      ) : (
        <View style={[styles.image, styles.imagePlaceholder]}>
          <Ionicons name="image-outline" size={32} color={colors.textMuted} />
        </View>
      )}
      <View style={styles.body}>
        <Text style={styles.name} numberOfLines={2}>
          {item.name}
        </Text>
        <Text style={styles.price}>{formatPrice(item.price_cents)}</Text>
        {typeof item.stock === "number" && item.stock <= 5 ? (
          <Text style={styles.lowStock}>
            {item.stock <= 0 ? "Sold out" : `Only ${item.stock} left`}
          </Text>
        ) : null}
      </View>
    </Pressable>
  );

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.headerBtn}>
          <Ionicons name="chevron-back" size={24} color={colors.primary} />
        </Pressable>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>Sanctus Shop</Text>
          <Text style={styles.headerSub}>Goods for the journey</Text>
        </View>
        <Pressable
          onPress={() => router.push("/orders")}
          hitSlop={10}
          style={styles.headerBtn}
          testID="shop-orders-link"
        >
          <Ionicons name="receipt-outline" size={22} color={colors.primary} />
        </Pressable>
      </View>
      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : (
        <FlatList
          data={products}
          keyExtractor={(p) => p.product_id}
          renderItem={renderItem}
          numColumns={2}
          contentContainerStyle={styles.list}
          columnWrapperStyle={{ gap: spacing.md }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="basket-outline" size={48} color={colors.textMuted} />
              <Text style={styles.emptyTitle}>The shelves are bare</Text>
              <Text style={styles.emptyHint}>Check back soon for new arrivals.</Text>
            </View>
          }
          ListFooterComponent={
            products.length > 0 ? (
              <Text style={styles.footnote}>Flat ${(shipping / 100).toFixed(0)} shipping in the US.</Text>
            ) : null
          }
        />
      )}
    </SafeAreaView>
  );
}

const CARD_RADIUS = 14;

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
    backgroundColor: colors.surface,
  },
  headerBtn: { padding: spacing.xs, minWidth: 40, alignItems: "center" },
  headerCenter: { flex: 1, alignItems: "center" },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 22, color: colors.primary },
  headerSub: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  list: { padding: spacing.md, gap: spacing.md, paddingBottom: spacing.xl },
  card: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: CARD_RADIUS,
    overflow: "hidden",
    ...shadow.card,
  },
  image: { width: "100%", aspectRatio: 1, backgroundColor: colors.background },
  imagePlaceholder: { alignItems: "center", justifyContent: "center" },
  body: { padding: spacing.sm },
  name: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textPrimary, lineHeight: 18 },
  price: { fontFamily: fonts.headingBold, fontSize: 16, color: colors.primary, marginTop: 4 },
  lowStock: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.liturgical.red, marginTop: 2 },
  empty: { alignItems: "center", justifyContent: "center", paddingVertical: spacing.xxl, gap: spacing.sm },
  emptyTitle: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.primary },
  emptyHint: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary },
  footnote: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textMuted, textAlign: "center", marginTop: spacing.lg },
});

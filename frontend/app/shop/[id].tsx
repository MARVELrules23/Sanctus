import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import {
  ShopProduct,
  createShopCheckout,
  getShopProduct,
} from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

function formatPrice(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

function publicOrigin(): string {
  if (Platform.OS === "web" && typeof window !== "undefined") {
    return window.location.origin;
  }
  const base = process.env.EXPO_PUBLIC_BACKEND_URL || "";
  return base.replace(/\/$/, "");
}

export default function ShopProductScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [product, setProduct] = useState<ShopProduct | null>(null);
  const [loading, setLoading] = useState(true);
  const [quantity, setQuantity] = useState(1);
  const [buying, setBuying] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const r = await getShopProduct(id);
      setProduct(r);
    } catch (e: any) {
      Alert.alert("Not available", e?.message || "Could not load this item.");
      router.back();
    } finally {
      setLoading(false);
    }
  }, [id, router]);

  useEffect(() => {
    load();
  }, [load]);

  const onBuy = useCallback(async () => {
    if (!product || buying) return;
    setBuying(true);
    try {
      const origin = publicOrigin();
      const clientToken = `${product.product_id}_${Date.now()}`;
      const res = await createShopCheckout({
        product_id: product.product_id,
        quantity,
        return_origin: origin,
        client_token: clientToken,
      });
      if (Platform.OS === "web" && typeof window !== "undefined") {
        window.location.href = res.url;
      } else {
        const successUrl = `${origin}/shop/success`;
        await WebBrowser.openAuthSessionAsync(res.url, successUrl).catch(() => {});
        // After the browser closes, send the user to the success screen so we
        // can attempt to reconcile (the order_id will be queried in /orders).
        router.replace(`/orders`);
      }
    } catch (e: any) {
      const detail = e?.message || "Could not start checkout.";
      Alert.alert("Checkout unavailable", detail);
    } finally {
      setBuying(false);
    }
  }, [product, quantity, buying, router]);

  if (loading || !product) {
    return (
      <SafeAreaView style={styles.safe}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.center}><ActivityIndicator color={colors.primary} /></View>
      </SafeAreaView>
    );
  }

  const soldOut = typeof product.stock === "number" && product.stock <= 0;
  const maxQty = Math.max(1, Math.min(typeof product.stock === "number" ? product.stock : 10, 10));
  const total = product.price_cents * quantity + product.shipping_amount_cents;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.headerBtn}>
          <Ionicons name="chevron-back" size={24} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle} numberOfLines={1}>{product.name}</Text>
        <View style={styles.headerBtn} />
      </View>
      <ScrollView contentContainerStyle={styles.scroll}>
        {product.image_url ? (
          <Image source={{ uri: product.image_url }} style={styles.image} resizeMode="cover" />
        ) : (
          <View style={[styles.image, styles.imagePlaceholder]}>
            <Ionicons name="image-outline" size={48} color={colors.textMuted} />
          </View>
        )}
        <View style={styles.body}>
          <Text style={styles.name}>{product.name}</Text>
          <Text style={styles.price}>{formatPrice(product.price_cents)}</Text>
          {product.description ? (
            <Text style={styles.description}>{product.description}</Text>
          ) : null}

          <View style={styles.qtyRow}>
            <Text style={styles.qtyLabel}>Quantity</Text>
            <View style={styles.qtyControls}>
              <Pressable
                onPress={() => setQuantity(Math.max(1, quantity - 1))}
                style={({ pressed }) => [styles.qtyBtn, pressed && { opacity: 0.6 }]}
                disabled={quantity <= 1}
              >
                <Ionicons name="remove" size={18} color={colors.primary} />
              </Pressable>
              <Text style={styles.qtyValue}>{quantity}</Text>
              <Pressable
                onPress={() => setQuantity(Math.min(maxQty, quantity + 1))}
                style={({ pressed }) => [styles.qtyBtn, pressed && { opacity: 0.6 }]}
                disabled={quantity >= maxQty}
              >
                <Ionicons name="add" size={18} color={colors.primary} />
              </Pressable>
            </View>
          </View>

          <View style={styles.summary}>
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Subtotal</Text>
              <Text style={styles.summaryValue}>{formatPrice(product.price_cents * quantity)}</Text>
            </View>
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Shipping (US)</Text>
              <Text style={styles.summaryValue}>{formatPrice(product.shipping_amount_cents)}</Text>
            </View>
            <View style={[styles.summaryRow, styles.summaryTotal]}>
              <Text style={styles.summaryTotalLabel}>Total</Text>
              <Text style={styles.summaryTotalValue}>{formatPrice(total)}</Text>
            </View>
          </View>
        </View>
      </ScrollView>
      <View style={styles.footer}>
        <Pressable
          onPress={onBuy}
          disabled={soldOut || buying}
          style={({ pressed }) => [
            styles.buyBtn,
            (soldOut || buying) && { opacity: 0.6 },
            pressed && { opacity: 0.8 },
          ]}
          testID="buy-now-btn"
        >
          {buying ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Ionicons name="lock-closed" size={16} color="#fff" />
              <Text style={styles.buyText}>{soldOut ? "Sold out" : `Buy now · ${formatPrice(total)}`}</Text>
            </>
          )}
        </Pressable>
        <Text style={styles.secureNote}>Secure checkout via Stripe</Text>
      </View>
    </SafeAreaView>
  );
}

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
  headerBtn: { padding: spacing.xs, width: 44, alignItems: "flex-start" },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.uiSemi, fontSize: 16, color: colors.primary },
  scroll: { paddingBottom: spacing.xl },
  image: { width: "100%", aspectRatio: 1, backgroundColor: colors.surface },
  imagePlaceholder: { alignItems: "center", justifyContent: "center" },
  body: { padding: spacing.lg, gap: spacing.md },
  name: { fontFamily: fonts.headingBold, fontSize: 22, color: colors.primary },
  price: { fontFamily: fonts.headingBold, fontSize: 24, color: colors.gold },
  description: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textSecondary, lineHeight: 22 },
  qtyRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: spacing.sm },
  qtyLabel: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  qtyControls: { flexDirection: "row", alignItems: "center", borderWidth: 1, borderColor: colors.border, borderRadius: radius.round, overflow: "hidden" },
  qtyBtn: { padding: 10, minWidth: 44, alignItems: "center" },
  qtyValue: { paddingHorizontal: spacing.md, fontFamily: fonts.uiSemi, fontSize: 16, color: colors.primary, minWidth: 28, textAlign: "center" },
  summary: { marginTop: spacing.md, padding: spacing.md, backgroundColor: colors.surface, borderRadius: radius.lg, gap: spacing.xs, ...shadow.card },
  summaryRow: { flexDirection: "row", justifyContent: "space-between" },
  summaryLabel: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary },
  summaryValue: { fontFamily: fonts.uiMedium, fontSize: 14, color: colors.textPrimary },
  summaryTotal: { borderTopWidth: 1, borderTopColor: colors.borderSoft, paddingTop: spacing.sm, marginTop: spacing.xs },
  summaryTotalLabel: { fontFamily: fonts.uiSemi, fontSize: 15, color: colors.primary },
  summaryTotalValue: { fontFamily: fonts.headingBold, fontSize: 17, color: colors.primary },
  footer: { padding: spacing.md, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.border, backgroundColor: colors.surface },
  buyBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingVertical: 14, borderRadius: radius.round, backgroundColor: colors.primary },
  buyText: { fontFamily: fonts.uiSemi, fontSize: 15, color: "#fff" },
  secureNote: { textAlign: "center", marginTop: spacing.xs, fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
});

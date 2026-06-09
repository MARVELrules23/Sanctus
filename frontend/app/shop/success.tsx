import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { ShopOrder, reconcileShopSession } from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

function formatPrice(cents?: number, currency = "usd"): string {
  if (cents == null) return "";
  return `$${(cents / 100).toFixed(2)}`;
}

export default function ShopSuccessScreen() {
  const { session_id, order } = useLocalSearchParams<{ session_id?: string; order?: string }>();
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "paid" | "pending" | "error">("loading");
  const [orderDoc, setOrderDoc] = useState<ShopOrder | null>(null);
  const [attempts, setAttempts] = useState(0);

  const reconcile = useCallback(async () => {
    if (!session_id) {
      setStatus("error");
      return;
    }
    try {
      const r = await reconcileShopSession(session_id);
      setOrderDoc(r.order);
      if (r.payment_status === "paid") setStatus("paid");
      else if (attempts < 3) {
        setAttempts((a) => a + 1);
        setTimeout(reconcile, 1500);
      } else {
        setStatus("pending");
      }
    } catch (e) {
      console.warn("reconcile failed", e);
      if (attempts < 3) {
        setAttempts((a) => a + 1);
        setTimeout(reconcile, 1500);
      } else {
        setStatus("error");
      }
    }
  }, [session_id, attempts]);

  useEffect(() => {
    reconcile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  let icon: any = "hourglass-outline";
  let iconColor = colors.gold;
  let title = "Confirming your order…";
  let subtitle = "This usually takes a moment.";
  if (status === "paid") {
    icon = "checkmark-circle";
    iconColor = colors.liturgical.green;
    title = "Thank you!";
    subtitle = "Your order is confirmed. We'll email you when it ships.";
  } else if (status === "pending") {
    icon = "time-outline";
    iconColor = colors.textMuted;
    title = "Still processing";
    subtitle = "We're waiting on Stripe — check My Orders in a minute.";
  } else if (status === "error") {
    icon = "alert-circle-outline";
    iconColor = colors.liturgical.red;
    title = "We couldn't confirm yet";
    subtitle = "If your card was charged, the order will appear under My Orders shortly.";
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.center}>
        {status === "loading" ? (
          <ActivityIndicator size="large" color={colors.primary} />
        ) : (
          <Ionicons name={icon} size={72} color={iconColor} />
        )}
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.subtitle}>{subtitle}</Text>

        {orderDoc ? (
          <View style={styles.summary}>
            <Text style={styles.summaryTitle}>{orderDoc.product_name}</Text>
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Order #</Text>
              <Text style={styles.summaryValue}>{orderDoc.order_id.replace("ord_", "")}</Text>
            </View>
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Total</Text>
              <Text style={styles.summaryValue}>{formatPrice(orderDoc.total_cents)}</Text>
            </View>
          </View>
        ) : null}

        <Pressable
          onPress={() => router.replace("/orders")}
          style={({ pressed }) => [styles.btn, pressed && { opacity: 0.8 }]}
        >
          <Text style={styles.btnText}>View My Orders</Text>
        </Pressable>
        <Pressable
          onPress={() => router.replace("/shop")}
          style={({ pressed }) => [styles.btnGhost, pressed && { opacity: 0.6 }]}
        >
          <Text style={styles.btnGhostText}>Back to Shop</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.md },
  title: { fontFamily: fonts.headingBold, fontSize: 26, color: colors.primary, textAlign: "center", marginTop: spacing.md },
  subtitle: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textSecondary, textAlign: "center", lineHeight: 22 },
  summary: { width: "100%", padding: spacing.md, backgroundColor: colors.surface, borderRadius: radius.lg, marginTop: spacing.md, gap: spacing.xs, ...shadow.card },
  summaryTitle: { fontFamily: fonts.uiSemi, fontSize: 15, color: colors.primary, marginBottom: spacing.xs },
  summaryRow: { flexDirection: "row", justifyContent: "space-between" },
  summaryLabel: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textSecondary },
  summaryValue: { fontFamily: fonts.uiMedium, fontSize: 13, color: colors.textPrimary },
  btn: { marginTop: spacing.lg, paddingHorizontal: spacing.lg, paddingVertical: 12, borderRadius: radius.round, backgroundColor: colors.primary, minWidth: 200, alignItems: "center" },
  btnText: { fontFamily: fonts.uiSemi, fontSize: 14, color: "#fff" },
  btnGhost: { paddingVertical: 8 },
  btnGhostText: { fontFamily: fonts.uiMedium, fontSize: 13, color: colors.textSecondary },
});

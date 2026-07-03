/**
 * iOS StoreKit paywall buttons (Apple In-App Purchase).
 *
 * Rendered only on iOS (Metro picks this `.ios.tsx` file). Uses
 * `react-native-iap` (StoreKit 2 under the hood). After a purchase or restore
 * we grab the base64 app receipt via `getReceiptDataIOS()` and send it to the
 * backend (`/subscriptions/iap/apple/confirm`) for validation before granting
 * entitlement and finishing the transaction.
 *
 * NOTE: This only works in a native build (dev/production) on a real device
 * with a sandbox tester — never in Expo Go or the web preview.
 */
import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import {
  useIAP,
  finishTransaction,
  getReceiptDataIOS,
  ErrorCode,
  type Purchase,
} from "react-native-iap";

import { confirmApplePurchase } from "@/src/api";
import { colors, fonts, radius, spacing } from "@/src/theme";
import type { ApplePaywallButtonsProps } from "./ApplePaywallButtons";

const SKUS: Record<"monthly" | "annual", string> = {
  monthly: "premium_monthly",
  annual: "premium_annual",
};

export default function ApplePaywallButtons({ selectedPlan, trialDays, onEntitled }: ApplePaywallButtonsProps) {
  const [busy, setBusy] = useState<"buy" | "restore" | null>(null);

  const validateAndFinish = useCallback(
    async (purchase: Purchase) => {
      const receipt = await getReceiptDataIOS().catch(() => "");
      const res = await confirmApplePurchase({
        product_id: purchase.productId ?? SKUS[selectedPlan],
        transaction_id: purchase.transactionId ?? null,
        original_transaction_id:
          (purchase as any).originalTransactionIdentifierIOS ?? purchase.transactionId ?? null,
        receipt: receipt || purchase.purchaseToken || "",
      });
      if (!res.ok) throw new Error("Server could not validate the purchase.");
      await finishTransaction({ purchase, isConsumable: false });
    },
    [selectedPlan]
  );

  const { connected, subscriptions, fetchProducts, requestPurchase } = useIAP({
    onPurchaseSuccess: async (purchase) => {
      try {
        await validateAndFinish(purchase);
        await onEntitled();
      } catch (e: any) {
        Alert.alert("Purchase issue", e?.message || "We couldn't confirm your subscription.");
      } finally {
        setBusy(null);
      }
    },
    onPurchaseError: (e) => {
      setBusy(null);
      if (e.code !== ErrorCode.UserCancelled) {
        Alert.alert("Purchase failed", e.message || "Please try again.");
      }
    },
  });

  useEffect(() => {
    if (connected) {
      fetchProducts({ skus: [SKUS.monthly, SKUS.annual], type: "subs" }).catch(() => {});
    }
  }, [connected, fetchProducts]);

  const buy = useCallback(() => {
    if (busy) return;
    setBusy("buy");
    requestPurchase({ request: { apple: { sku: SKUS[selectedPlan] } }, type: "subs" }).catch((e: any) => {
      setBusy(null);
      if (e?.code !== ErrorCode.UserCancelled) {
        Alert.alert("Purchase failed", e?.message || "Please try again.");
      }
    });
  }, [busy, requestPurchase, selectedPlan]);

  const restore = useCallback(async () => {
    if (busy) return;
    setBusy("restore");
    try {
      const receipt = await getReceiptDataIOS().catch(() => "");
      if (!receipt) {
        Alert.alert("Nothing to restore", "We couldn't find a previous purchase on this Apple ID.");
        return;
      }
      const res = await confirmApplePurchase({ product_id: SKUS[selectedPlan], receipt });
      if (res.active) {
        await onEntitled();
        Alert.alert("Restored", "Your Sanctus Premium subscription is active again.");
      } else {
        Alert.alert("Nothing active", "No active subscription was found to restore.");
      }
    } catch (e: any) {
      Alert.alert("Restore failed", e?.message || "Please try again.");
    } finally {
      setBusy(null);
    }
  }, [busy, onEntitled, selectedPlan]);

  const priceLine = subscriptions.find((s) => s.id === SKUS[selectedPlan])?.displayPrice;

  return (
    <View>
      <Text style={styles.trialNote}>{trialDays}-day free trial. Cancel anytime before it ends.</Text>

      <Pressable
        testID="premium-apple-subscribe"
        onPress={buy}
        disabled={!connected || busy !== null}
        style={({ pressed }) => [styles.primaryBtn, pressed && { opacity: 0.85 }, (!connected || busy !== null) && { opacity: 0.6 }]}
      >
        {busy === "buy" ? (
          <ActivityIndicator color={colors.gold} />
        ) : (
          <>
            <Ionicons name="logo-apple" size={16} color={colors.gold} />
            <Text style={styles.primaryBtnText}>
              Subscribe{priceLine ? ` · ${priceLine}` : ""}
            </Text>
          </>
        )}
      </Pressable>

      <Pressable
        testID="premium-apple-restore"
        onPress={restore}
        disabled={busy !== null}
        style={({ pressed }) => [styles.restoreBtn, pressed && { opacity: 0.7 }]}
      >
        {busy === "restore" ? (
          <ActivityIndicator size="small" color={colors.textSecondary} />
        ) : (
          <Text style={styles.restoreText}>Restore purchases</Text>
        )}
      </Pressable>

      <Text style={styles.secureNote}>Billed through your Apple ID · Manage in iOS Settings</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  trialNote: {
    fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textSecondary,
    textAlign: "center", marginTop: spacing.lg,
  },
  primaryBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 8, paddingVertical: 14, borderRadius: radius.round,
    marginTop: spacing.md, backgroundColor: colors.primary,
  },
  primaryBtnText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.gold, letterSpacing: 0.6 },
  restoreBtn: { alignItems: "center", justifyContent: "center", paddingVertical: 12, marginTop: spacing.xs },
  restoreText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.textSecondary },
  secureNote: {
    fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textMuted,
    textAlign: "center", marginTop: spacing.xs,
  },
});

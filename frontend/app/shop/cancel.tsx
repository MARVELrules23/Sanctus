import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import { colors, fonts, radius, spacing } from "@/src/theme";

export default function ShopCancelScreen() {
  const router = useRouter();
  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.center}>
        <Ionicons name="close-circle-outline" size={72} color={colors.textMuted} />
        <Text style={styles.title}>Checkout cancelled</Text>
        <Text style={styles.subtitle}>No worries &mdash; you weren&apos;t charged.</Text>
        <Pressable onPress={() => router.replace("/shop")} style={({ pressed }) => [styles.btn, pressed && { opacity: 0.8 }]}>
          <Text style={styles.btnText}>Back to Shop</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: spacing.xl, gap: spacing.md },
  title: { fontFamily: fonts.headingBold, fontSize: 26, color: colors.primary, marginTop: spacing.md },
  subtitle: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textSecondary, textAlign: "center" },
  btn: { marginTop: spacing.lg, paddingHorizontal: spacing.lg, paddingVertical: 12, borderRadius: radius.round, backgroundColor: colors.primary, minWidth: 200, alignItems: "center" },
  btnText: { fontFamily: fonts.uiSemi, fontSize: 14, color: "#fff" },
});

import React from "react";
import { ImageBackground, Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";

import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, spacing } from "@/src/theme";
import Ornament from "@/src/components/Ornament";

const BG_IMAGE =
  "https://images.unsplash.com/photo-1632230997264-b2bfc65cb8b4?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NTJ8MHwxfHNlYXJjaHwxfHxzdGFpbmVkJTIwZ2xhc3MlMjBjaHVyY2glMjB3aW5kb3d8ZW58MHx8fHwxNzgwODg4OTA4fDA&ixlib=rb-4.1.0&q=85";

export default function Login() {
  const { signIn } = useAuth();
  const router = useRouter();
  return (
    <View style={styles.root} testID="login-screen">
      <ImageBackground source={{ uri: BG_IMAGE }} style={styles.bg} resizeMode="cover">
        <LinearGradient
          colors={["rgba(28,40,65,0.35)", "rgba(28,40,65,0.92)"]}
          style={StyleSheet.absoluteFillObject}
        />
        <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
          <View style={styles.top}>
            <View style={styles.crestWrap}>
              <Ionicons name="flower-outline" size={36} color={colors.gold} />
            </View>
            <Text style={styles.brand}>SANCTUS</Text>
            <View style={styles.ornamentWrap}>
              <Ornament />
            </View>
            <Text style={styles.tagline}>
              A daily rule of life — meal, movement, and prayer ordered by the Church&apos;s calendar.
            </Text>
          </View>

          <View style={styles.bottom}>
            <Pressable
              testID="google-sign-in-button"
              onPress={signIn}
              style={({ pressed }) => [styles.googleBtn, pressed && styles.googleBtnPressed]}
            >
              <Ionicons name="logo-google" size={20} color={colors.primary} />
              <Text style={styles.googleBtnText}>Continue with Google</Text>
            </Pressable>
            <Text style={styles.fineprint}>
              By continuing you agree to a simple, reverent practice. We store only your name &amp; email.
            </Text>
            <View style={styles.legalRow}>
              <Pressable
                testID="login-privacy-link"
                onPress={() => router.push("/privacy")}
                hitSlop={8}
              >
                <Text style={styles.legalLink}>Privacy</Text>
              </Pressable>
              <Text style={styles.legalDot}>·</Text>
              <Pressable
                testID="login-support-link"
                onPress={() => router.push("/support")}
                hitSlop={8}
              >
                <Text style={styles.legalLink}>Support</Text>
              </Pressable>
            </View>
          </View>
        </SafeAreaView>
      </ImageBackground>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.primary },
  bg: { flex: 1 },
  safe: { flex: 1, paddingHorizontal: spacing.lg, justifyContent: "space-between" },
  top: { alignItems: "center", marginTop: spacing.xxl },
  crestWrap: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 1,
    borderColor: colors.gold,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(212,175,55,0.08)",
  },
  brand: {
    fontFamily: fonts.headingBold,
    fontSize: 44,
    letterSpacing: 6,
    color: colors.gold,
    marginTop: spacing.md,
  },
  ornamentWrap: { width: 220, marginTop: spacing.xs },
  tagline: {
    fontFamily: fonts.bodyRegular,
    fontStyle: "italic",
    color: "#F4ECD8",
    fontSize: 17,
    textAlign: "center",
    lineHeight: 26,
    marginTop: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  bottom: { paddingBottom: spacing.lg, gap: spacing.md },
  googleBtn: {
    backgroundColor: "#FAF9F6",
    borderRadius: radius.lg,
    paddingVertical: 16,
    paddingHorizontal: spacing.lg,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.gold,
  },
  googleBtnPressed: { opacity: 0.85 },
  googleBtnText: {
    fontFamily: fonts.uiSemi,
    fontSize: 16,
    color: colors.primary,
    letterSpacing: 0.5,
  },
  fineprint: {
    fontFamily: fonts.bodyRegular,
    color: "#D8D2C0",
    fontSize: 12,
    textAlign: "center",
    lineHeight: 18,
  },
  legalRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    marginTop: 4,
  },
  legalLink: {
    fontFamily: fonts.uiSemi,
    fontSize: 12,
    color: colors.gold,
    textDecorationLine: "underline",
  },
  legalDot: {
    color: "#D8D2C0",
    fontSize: 12,
  },
});

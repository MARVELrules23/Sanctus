import { Stack, useRouter, useSegments } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import {
  useFonts as useCormorant,
  CormorantGaramond_600SemiBold,
  CormorantGaramond_700Bold,
} from "@expo-google-fonts/cormorant-garamond";
import {
  Lora_400Regular,
  Lora_400Regular_Italic,
  Lora_700Bold,
} from "@expo-google-fonts/lora";
import { Inter_500Medium, Inter_600SemiBold } from "@expo-google-fonts/inter";

import { useIconFonts } from "@/src/hooks/use-icon-fonts";
import { AuthProvider, useAuth } from "@/src/auth-context";
import { RadioPlayerProvider } from "@/src/audio/RadioPlayerContext";
import RadioMiniPlayer from "@/src/components/RadioMiniPlayer";

// Keep the native splash visible from cold start until icon fonts register.
// Required because @expo/vector-icons' componentDidMount fallback fires
// Font.loadAsync against a broken vendor path if any <Icon> mounts before
// the family is registered — which throws on Android Expo Go.
SplashScreen.preventAutoHideAsync();

function RootGate() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    if (loading) return;
    const inTabs = segments[0] === "(tabs)";
    const onLogin = segments[0] === "login";
    // Routes that anyone (signed-in or not) should be able to view directly —
    // required so the App Store / Play Store privacy + support URLs work
    // without forcing a Google sign-in.
    const isPublicRoute =
      segments[0] === "privacy" || segments[0] === "support";
    if (!user && !onLogin && !isPublicRoute) {
      router.replace("/login");
    } else if (user && (onLogin || segments.length === 0)) {
      router.replace("/(tabs)");
    } else if (user && !inTabs && !onLogin) {
      // any other deep-link without tabs stays as-is
    }
  }, [user, loading, segments, router]);

  return <Stack screenOptions={{ headerShown: false }} />;
}

function AppShell() {
  return (
    <>
      <RootGate />
      <RadioMiniPlayer />
    </>
  );
}

export default function RootLayout() {
  const [iconsLoaded, iconsError] = useIconFonts();
  const [fontsLoaded] = useCormorant({
    CormorantGaramond_600SemiBold,
    CormorantGaramond_700Bold,
    Lora_400Regular,
    Lora_400Regular_Italic,
    Lora_700Bold,
    Inter_500Medium,
    Inter_600SemiBold,
  });

  useEffect(() => {
    if ((iconsLoaded || iconsError) && fontsLoaded) {
      SplashScreen.hideAsync();
    }
  }, [iconsLoaded, iconsError, fontsLoaded]);

  if (!fontsLoaded) return null;
  if (!iconsLoaded && !iconsError) return null;

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <AuthProvider>
        <RadioPlayerProvider>
          <AppShell />
        </RadioPlayerProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}

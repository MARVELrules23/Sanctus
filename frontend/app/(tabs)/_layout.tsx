import React from "react";
import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { StyleSheet } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors, fonts } from "@/src/theme";
import { useNotifications } from "@/src/notifications-context";
import { useI18n } from "@/src/i18n";

/**
 * Bottom tab navigator.
 *
 * NOTE: expo-router auto-derives an `href` for every `Tabs.Screen` from its
 * file path. Newer versions of react-navigation's bottom-tabs error out if
 * you ALSO pass a custom `tabBarButton` to the same screen ("Cannot use
 * `href` and `tabBarButton` together."). So we rely on the default tab
 * button and just feed `tabBarTestID` to it. On web, react-native-web
 * forwards that as `data-testid` on the rendered pressable, which is
 * sufficient for headless testing.
 */
export default function TabsLayout() {
  const insets = useSafeAreaInsets();
  const { unreadDMTotal } = useNotifications();
  const { t } = useI18n();
  // expo-router's tabBarBadge accepts string|number|undefined. Undefined
  // hides the badge entirely. We cap visually at "99+" to keep the pill
  // from blowing out the icon's footprint.
  const parishBadge =
    unreadDMTotal > 0
      ? (unreadDMTotal > 99 ? "99+" : String(unreadDMTotal))
      : undefined;
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.gold,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: {
          backgroundColor: colors.primary,
          borderTopWidth: 0,
          height: 64 + insets.bottom,
          paddingBottom: insets.bottom + 6,
          paddingTop: 8,
        },
        tabBarLabelStyle: {
          fontFamily: fonts.uiMedium,
          fontSize: 11,
          letterSpacing: 0.5,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: t("tab.today"),
          tabBarIcon: ({ color, size }) => <Ionicons name="sunny-outline" color={color} size={size} />,
          tabBarTestID: "tab-today",
        }}
      />
      <Tabs.Screen
        name="meals"
        options={{
          title: t("tab.meals"),
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="restaurant-outline" color={color} size={size} />
          ),
          tabBarTestID: "tab-meals",
        }}
      />
      <Tabs.Screen
        name="workouts"
        options={{
          title: t("tab.workouts"),
          tabBarIcon: ({ color, size }) => <Ionicons name="barbell-outline" color={color} size={size} />,
          tabBarTestID: "tab-workouts",
        }}
      />
      <Tabs.Screen
        name="wellness"
        options={{
          title: t("tab.wellness"),
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="heart-circle-outline" color={color} size={size} />
          ),
          tabBarTestID: "tab-wellness",
        }}
      />
      <Tabs.Screen
        name="sanctuary"
        options={{
          title: t("tab.sanctuary"),
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="musical-notes-outline" color={color} size={size} />
          ),
          tabBarTestID: "tab-sanctuary",
        }}
      />
      <Tabs.Screen
        name="community"
        options={{
          title: t("tab.parish"),
          tabBarLabel: t("tab.parish"),
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="people-outline" color={color} size={size} />
          ),
          tabBarTestID: "tab-community",
          tabBarBadge: parishBadge,
          tabBarBadgeStyle: {
            backgroundColor: colors.gold,
            color: colors.primary,
            fontFamily: fonts.uiSemi,
            fontSize: 10,
            minWidth: 18,
            height: 18,
            lineHeight: 14,
          },
        }}
      />
      <Tabs.Screen
        name="calendar"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="family"
        options={{
          title: t("tab.family"),
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="home-outline" color={color} size={size} />
          ),
          tabBarTestID: "tab-family",
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: t("tab.profile"),
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person-circle-outline" color={color} size={size} />
          ),
          tabBarTestID: "tab-profile",
        }}
      />
    </Tabs>
  );
}

// `styles` kept for potential future use; left empty to avoid unused-warning churn.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const styles = StyleSheet.create({});

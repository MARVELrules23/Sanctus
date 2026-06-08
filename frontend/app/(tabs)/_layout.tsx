import React from "react";
import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Platform, Pressable, StyleSheet, View } from "react-native";
import type { BottomTabBarButtonProps } from "@react-navigation/bottom-tabs";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors, fonts } from "@/src/theme";

/**
 * On web, React Navigation's default tab button does NOT forward `tabBarTestID`
 * to the underlying DOM element, which makes it impossible for headless
 * test runners (Playwright etc.) to target tabs by testID. This wrapper
 * re-creates a minimally-styled button and forwards the testID directly,
 * so `data-testid="tab-*"` appears on web while native still uses the same
 * pressable behavior.
 */
function makeTabButton(testID: string) {
  return function TabButton(props: BottomTabBarButtonProps) {
    const { children, onPress, onLongPress, accessibilityState, accessibilityLabel, style } = props;
    return (
      <Pressable
        onPress={(e) => onPress?.(e as any)}
        onLongPress={(e) => onLongPress?.(e as any)}
        accessibilityRole="button"
        accessibilityState={accessibilityState}
        accessibilityLabel={accessibilityLabel}
        testID={testID}
        // @ts-expect-error react-native-web supports id but isn't typed here
        id={testID}
        style={[styles.tabButton, style as any]}
      >
        <View style={styles.tabInner}>{children}</View>
      </Pressable>
    );
  };
}

export default function TabsLayout() {
  const insets = useSafeAreaInsets();
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
          title: "Today",
          tabBarIcon: ({ color, size }) => <Ionicons name="sunny-outline" color={color} size={size} />,
          tabBarTestID: "tab-today",
          tabBarButton: makeTabButton("tab-today"),
        }}
      />
      <Tabs.Screen
        name="meals"
        options={{
          title: "Meals",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="restaurant-outline" color={color} size={size} />
          ),
          tabBarTestID: "tab-meals",
          tabBarButton: makeTabButton("tab-meals"),
        }}
      />
      <Tabs.Screen
        name="workouts"
        options={{
          title: "Workouts",
          tabBarIcon: ({ color, size }) => <Ionicons name="barbell-outline" color={color} size={size} />,
          tabBarTestID: "tab-workouts",
          tabBarButton: makeTabButton("tab-workouts"),
        }}
      />
      <Tabs.Screen
        name="wellness"
        options={{
          title: "Wellness",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="heart-circle-outline" color={color} size={size} />
          ),
          tabBarTestID: "tab-wellness",
          tabBarButton: makeTabButton("tab-wellness"),
        }}
      />
      <Tabs.Screen
        name="sanctuary"
        options={{
          title: "Sanctuary",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="musical-notes-outline" color={color} size={size} />
          ),
          tabBarTestID: "tab-sanctuary",
          tabBarButton: makeTabButton("tab-sanctuary"),
        }}
      />
      <Tabs.Screen
        name="community"
        options={{
          title: "Parish",
          tabBarLabel: "Parish",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="people-outline" color={color} size={size} />
          ),
          tabBarTestID: "tab-community",
          tabBarButton: makeTabButton("tab-community"),
        }}
      />
      <Tabs.Screen
        name="calendar"
        options={{
          href: null,
          tabBarButton: () => null,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person-circle-outline" color={color} size={size} />
          ),
          tabBarTestID: "tab-profile",
          tabBarButton: makeTabButton("tab-profile"),
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabButton: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    ...Platform.select({
      web: { cursor: "pointer" } as any,
      default: {},
    }),
  },
  tabInner: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    width: "100%",
  },
});

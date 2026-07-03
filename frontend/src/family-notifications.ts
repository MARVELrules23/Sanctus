import { Platform } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Notifications from "expo-notifications";

const SCHEDULED_KEY = "family_prayer_reminders_v1";

export type ReminderStatus = "granted" | "denied" | "blocked" | "unsupported";

/**
 * Schedule two daily local reminders in the user's OWN timezone:
 *  - 6:00 AM  → Morning Prayer Together
 *  - 7:00 PM  → Night Prayer Together
 * Uses expo-notifications DAILY trigger (device-local time). Local
 * notifications do NOT fire in Expo Go / web — a real build is required.
 */
export async function enableFamilyReminders(): Promise<ReminderStatus> {
  if (Platform.OS === "web") return "unsupported";

  const current = await Notifications.getPermissionsAsync();
  let status = current.status;
  if (status !== "granted") {
    if (current.canAskAgain === false) return "blocked";
    const req = await Notifications.requestPermissionsAsync();
    status = req.status;
    if (status !== "granted") return req.canAskAgain === false ? "blocked" : "denied";
  }

  // Clear any previous schedule then set fresh ones (idempotent).
  await Notifications.cancelAllScheduledNotificationsAsync();

  await Notifications.scheduleNotificationAsync({
    content: {
      title: "🌅 Morning Prayer Together",
      body: "Gather the family for a moment of morning prayer.",
      data: { kind: "family-morning" },
    },
    trigger: { type: Notifications.SchedulableTriggerInputTypes.DAILY, hour: 6, minute: 0 },
  });

  await Notifications.scheduleNotificationAsync({
    content: {
      title: "🌙 Night Prayer Together",
      body: "Time to thank God and pray together before bed.",
      data: { kind: "family-night" },
    },
    trigger: { type: Notifications.SchedulableTriggerInputTypes.DAILY, hour: 19, minute: 0 },
  });

  await AsyncStorage.setItem(SCHEDULED_KEY, "1");
  return "granted";
}

export async function areRemindersEnabled(): Promise<boolean> {
  if (Platform.OS === "web") return false;
  const flag = await AsyncStorage.getItem(SCHEDULED_KEY);
  return flag === "1";
}

export async function disableFamilyReminders(): Promise<void> {
  if (Platform.OS === "web") return;
  await Notifications.cancelAllScheduledNotificationsAsync();
  await AsyncStorage.removeItem(SCHEDULED_KEY);
}

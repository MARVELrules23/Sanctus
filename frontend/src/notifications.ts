/**
 * On-device reminder scheduling for Schedule items (expo-notifications).
 *
 * Local notifications only — no remote push / no API keys. Native-only:
 * on React Native Web every call is a graceful no-op so the Schedule UI still
 * works in the preview. Real reminders fire on a built iOS/Android app.
 *
 * Weekday mapping note: our items use Sun=0..Sat=6; expo WEEKLY triggers use
 * 1=Sunday..7=Saturday, so we pass (dow + 1).
 */
import { Platform } from "react-native";
import * as Notifications from "expo-notifications";

import type { ScheduleItem } from "./api";

const isWeb = Platform.OS === "web";

if (!isWeb) {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
}

export type PermResult = { granted: boolean; canAskAgain: boolean; web?: boolean };

/** Ensure the Android channel exists and notification permission is granted. */
export async function ensureNotificationPermission(): Promise<PermResult> {
  if (isWeb) return { granted: false, canAskAgain: false, web: true };
  try {
    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("reminders", {
        name: "Reminders",
        importance: Notifications.AndroidImportance.HIGH,
        sound: "default",
        vibrationPattern: [0, 250, 250, 250],
        lockscreenVisibility: Notifications.AndroidNotificationVisibility.PUBLIC,
      });
    }
    const current = await Notifications.getPermissionsAsync();
    if (current.status === "granted") {
      return { granted: true, canAskAgain: current.canAskAgain ?? true };
    }
    if (!current.canAskAgain) {
      return { granted: false, canAskAgain: false };
    }
    const req = await Notifications.requestPermissionsAsync();
    return { granted: req.status === "granted", canAskAgain: req.canAskAgain ?? false };
  } catch {
    return { granted: false, canAskAgain: false };
  }
}

function timeParts(time?: string | null): { hour: number; minute: number } {
  if (!time) return { hour: 9, minute: 0 }; // all-day reminders nudge at 9 AM
  const [h, m] = time.split(":");
  return { hour: parseInt(h, 10) || 0, minute: parseInt(m, 10) || 0 };
}

function bodyFor(item: ScheduleItem): string {
  const labelByKind: Record<string, string> = {
    meal: "Meal", workout: "Workout", virtue: "Virtue", challenge: "Challenge", custom: "Reminder", pilgrimage: "Pilgrimage",
  };
  return item.note || `${labelByKind[item.kind] || "Reminder"} from your schedule`;
}

/**
 * Schedule all OS notifications for a single item and return their IDs.
 * No-op (returns []) on web, or when notify is off / permission denied.
 */
export async function scheduleItemNotifications(item: ScheduleItem): Promise<string[]> {
  if (isWeb || !item.notify) return [];
  const perm = await ensureNotificationPermission();
  if (!perm.granted) return [];

  const { hour, minute } = timeParts(item.time);
  const channelId = Platform.OS === "android" ? "reminders" : undefined;
  const ids: string[] = [];

  try {
    if (item.recurrence === "weekly") {
      for (const dow of item.days_of_week || []) {
        const id = await Notifications.scheduleNotificationAsync({
          content: { title: item.title, body: bodyFor(item), sound: "default", data: { scheduleId: item.id } },
          trigger: {
            type: Notifications.SchedulableTriggerInputTypes.WEEKLY,
            weekday: (dow % 7) + 1, // Sun=0 -> 1
            hour,
            minute,
            channelId,
          },
        });
        ids.push(id);
      }
    } else if (item.date) {
      const when = new Date(`${item.date}T00:00:00`);
      when.setHours(hour, minute, 0, 0);
      if (when.getTime() > Date.now() + 5000) {
        const id = await Notifications.scheduleNotificationAsync({
          content: { title: item.title, body: bodyFor(item), sound: "default", data: { scheduleId: item.id } },
          trigger: { type: Notifications.SchedulableTriggerInputTypes.DATE, date: when, channelId },
        });
        ids.push(id);
      }
      // Gentle reminder the day before a pilgrimage.
      if (item.kind === "pilgrimage") {
        const dayBefore = new Date(when);
        dayBefore.setDate(dayBefore.getDate() - 1);
        dayBefore.setHours(9, 0, 0, 0);
        if (dayBefore.getTime() > Date.now() + 5000) {
          const id = await Notifications.scheduleNotificationAsync({
            content: {
              title: "Pilgrimage tomorrow",
              body: `Tomorrow: ${item.title}. Prepare your heart and any plans for the journey.`,
              sound: "default",
              data: { scheduleId: item.id },
            },
            trigger: { type: Notifications.SchedulableTriggerInputTypes.DATE, date: dayBefore, channelId },
          });
          ids.push(id);
        }
      }
    }
  } catch {
    /* best-effort */
  }
  return ids;
}

/** Cancel a set of previously-scheduled notification IDs. */
export async function cancelNotifications(ids?: string[]): Promise<void> {
  if (isWeb || !ids || ids.length === 0) return;
  for (const id of ids) {
    try {
      await Notifications.cancelScheduledNotificationAsync(id);
    } catch {
      /* ignore */
    }
  }
}

export const notificationsSupported = !isWeb;

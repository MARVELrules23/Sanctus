/**
 * Persisted user preference: liturgical season vs personal goals
 * for AI meal/workout generation.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import type { GoalMode } from "@/src/api";

const KEY = "sanctus_goal_mode";

export async function loadGoalMode(): Promise<GoalMode> {
  try {
    const v = await AsyncStorage.getItem(KEY);
    return v === "goals" ? "goals" : "liturgical";
  } catch {
    return "liturgical";
  }
}

export async function saveGoalMode(m: GoalMode): Promise<void> {
  try {
    await AsyncStorage.setItem(KEY, m);
  } catch {}
}

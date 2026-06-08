/**
 * Journal mood options — paired with Catholic affective vocabulary.
 */
import { colors } from "@/src/theme";
import type { JournalMood } from "@/src/api";

export type MoodOption = {
  value: NonNullable<JournalMood>;
  label: string;
  icon: string; // ionicon name
  color: string;
};

export const MOODS: MoodOption[] = [
  { value: "grateful", label: "Grateful", icon: "flower-outline", color: colors.gold },
  { value: "joyful", label: "Joyful", icon: "sunny-outline", color: colors.liturgical.gold },
  { value: "hopeful", label: "Hopeful", icon: "sparkles-outline", color: colors.liturgical.green },
  { value: "contrite", label: "Contrite", icon: "water-outline", color: colors.liturgical.purple },
  { value: "sorrowful", label: "Sorrowful", icon: "cloud-outline", color: colors.liturgical.red },
  { value: "weary", label: "Weary", icon: "moon-outline", color: colors.textSecondary },
];

export function moodFor(value: JournalMood): MoodOption | undefined {
  return MOODS.find((m) => m.value === value);
}

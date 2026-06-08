/**
 * Design tokens & shared styles for Sanctus.
 * Mirrors /app/design_guidelines.json.
 */
export const colors = {
  background: "#FAF9F6",
  surface: "#FFFFFF",
  surfaceDark: "#1C2841",
  primary: "#1C2841",
  gold: "#D4AF37",
  goldDark: "#C5A059",
  textPrimary: "#1C1C1E",
  textSecondary: "#5C5C60",
  textMuted: "#8A8A8E",
  border: "#E5E5EA",
  borderSoft: "#F0EBE1",
  liturgical: {
    purple: "#5B3475",
    red: "#9E1B1B",
    rose: "#D47B95",
    green: "#2A5A3B",
    white: "#A88A4A", // visual proxy — pure white on white isn't visible
    gold: "#D4AF37",
    black: "#1A1A1A",
  } as const,
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

export const radius = {
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  round: 9999,
} as const;

export const shadow = {
  card: {
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
} as const;

export const fonts = {
  headingBold: "CormorantGaramond_700Bold",
  headingSemi: "CormorantGaramond_600SemiBold",
  bodyRegular: "Lora_400Regular",
  bodyItalic: "Lora_400Regular_Italic",
  bodyBold: "Lora_700Bold",
  uiMedium: "Inter_500Medium",
  uiSemi: "Inter_600SemiBold",
} as const;

export function colorForLiturgical(c?: string): string {
  switch (c) {
    case "purple":
      return colors.liturgical.purple;
    case "red":
      return colors.liturgical.red;
    case "rose":
      return colors.liturgical.rose;
    case "green":
      return colors.liturgical.green;
    case "gold":
      return colors.liturgical.gold;
    case "black":
      return colors.liturgical.black;
    case "white":
      return colors.liturgical.white;
    default:
      return colors.liturgical.green;
  }
}

export function seasonLabel(season?: string): string {
  return season ?? "Ordinary Time";
}

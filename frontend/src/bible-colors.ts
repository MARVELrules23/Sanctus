import type { BibleColor } from "@/src/api";

export type HighlightSwatch = {
  value: BibleColor;
  label: string;
  hex: string;       // background highlight (translucent feel works best on a parchment surface)
  ring: string;      // ring around active swatch in picker
};

export const HIGHLIGHT_SWATCHES: HighlightSwatch[] = [
  { value: "rose",   label: "Rose",   hex: "#F8DDE3", ring: "#C9405A" },
  { value: "gold",   label: "Gold",   hex: "#F6E6B5", ring: "#B8862C" },
  { value: "sage",   label: "Sage",   hex: "#D8E7CF", ring: "#6B8B5C" },
  { value: "violet", label: "Violet", hex: "#E2D2EE", ring: "#6B3E8D" },
];

export function highlightHex(color: BibleColor | undefined | null): string | undefined {
  if (!color) return undefined;
  return HIGHLIGHT_SWATCHES.find((s) => s.value === color)?.hex;
}

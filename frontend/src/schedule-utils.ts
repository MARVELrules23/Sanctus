/**
 * Schedule helpers — day-of-week labels and 12-hour (American) time formatting.
 * Times are stored as 24-hour "HH:MM" strings; the UI always shows AM/PM.
 */

export const DOW_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
export const DOW_FULL = [
  "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
];

/** "08:00" -> { h12: 8, minute: 0, ampm: "AM" } */
export function parse24(time: string): { h12: number; minute: number; ampm: "AM" | "PM" } {
  const [hStr, mStr] = (time || "09:00").split(":");
  let h = parseInt(hStr, 10);
  const minute = parseInt(mStr, 10) || 0;
  const ampm: "AM" | "PM" = h >= 12 ? "PM" : "AM";
  h = h % 12;
  if (h === 0) h = 12;
  return { h12: h, minute, ampm };
}

/** (8, 0, "AM") -> "08:00" (24h) */
export function build24(h12: number, minute: number, ampm: "AM" | "PM"): string {
  let h = h12 % 12;
  if (ampm === "PM") h += 12;
  return `${String(h).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

/** "14:05" -> "2:05 PM" */
export function format12(time?: string | null): string {
  if (!time) return "All day";
  const { h12, minute, ampm } = parse24(time);
  return `${h12}:${String(minute).padStart(2, "0")} ${ampm}`;
}

/** Sunday=0..Saturday=6 for a "YYYY-MM-DD" string. */
export function dowOf(dateStr: string): number {
  const d = new Date(`${dateStr}T00:00:00`);
  return d.getDay();
}

/** Short human label for a weekly item's days, e.g. "Mon, Wed, Fri" or "Every day". */
export function daysLabel(days: number[]): string {
  if (!days || days.length === 0) return "";
  if (days.length === 7) return "Every day";
  return [...days].sort((a, b) => a - b).map((d) => DOW_SHORT[d]).join(", ");
}

/**
 * Date utilities (UTC-agnostic; uses local timezone for display, ISO for API).
 */
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const DOW = [
  "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
];

export function todayISO(d: Date = new Date()): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function parseISO(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function addDaysISO(s: string, n: number): string {
  const d = parseISO(s);
  d.setDate(d.getDate() + n);
  return todayISO(d);
}

export function formatLong(d: Date): string {
  return `${DOW[d.getDay()]}, ${MONTHS[d.getMonth()]} ${d.getDate()}`;
}

export function formatLongFromISO(s: string): string {
  return formatLong(parseISO(s));
}

export function dayOfWeek(d: Date): string {
  return DOW[d.getDay()];
}

export function monthName(m: number): string {
  return MONTHS[m - 1] ?? "";
}

export function startOfWeekISO(s: string): string {
  const d = parseISO(s);
  // Treat Monday as start of week (matches workout/meal planning)
  const day = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - day);
  return todayISO(d);
}

/**
 * Calendar export helpers — turn a saved schedule item into links the user's
 * own calendar app can open (so the calendar handles the notifications).
 *
 * - Google Calendar: a TEMPLATE "render" URL (works for Gmail, supports RRULE).
 * - Apple / phone calendar: the backend .ics capability URL (universal).
 */
import type { ScheduleItem } from "./api";

const BACKEND = process.env.EXPO_PUBLIC_BACKEND_URL || "";
const BYDAY = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"]; // 0=Sun..6=Sat

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** Next date (incl. today) whose weekday is in `days` (Sun=0..Sat=6). */
function nextWeekly(days: number[]): Date {
  const base = new Date();
  base.setHours(0, 0, 0, 0);
  for (let i = 0; i < 8; i++) {
    const d = new Date(base);
    d.setDate(d.getDate() + i);
    if (days.includes(d.getDay())) return d;
  }
  return base;
}

function ymd(d: Date): string {
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`;
}

/** Build the Google Calendar "Add event" URL for an item. */
export function googleCalUrl(item: ScheduleItem): string {
  const params = new URLSearchParams();
  params.set("action", "TEMPLATE");
  params.set("text", item.title || "Sanctus");
  if (item.note) params.set("details", item.note);

  const time = item.time;
  let startDate: Date;
  if (item.recurrence === "once" && item.date) {
    startDate = new Date(`${item.date}T00:00:00`);
  } else {
    startDate = nextWeekly(item.days_of_week?.length ? item.days_of_week : [new Date().getDay()]);
  }

  if (time) {
    const [hh, mm] = time.split(":").map((x) => parseInt(x, 10));
    const start = `${ymd(startDate)}T${pad(hh)}${pad(mm)}00`;
    const endH = (hh + 1) % 24;
    const end = `${ymd(startDate)}T${pad(endH)}${pad(mm)}00`;
    params.set("dates", `${start}/${end}`);
  } else {
    const next = new Date(startDate);
    next.setDate(next.getDate() + 1);
    params.set("dates", `${ymd(startDate)}/${ymd(next)}`);
  }

  if (item.recurrence === "weekly" && item.days_of_week?.length) {
    const byday = [...item.days_of_week].sort((a, b) => a - b).map((d) => BYDAY[d]).join(",");
    params.set("recur", `RRULE:FREQ=WEEKLY;BYDAY=${byday}`);
  }
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

/** Universal .ics link (Apple Calendar, phone calendars, Outlook). */
export function icsLink(item: ScheduleItem): string | null {
  if (!item.ics_token) return null;
  return `${BACKEND}/api/schedule/ics/${item.ics_token}.ics`;
}

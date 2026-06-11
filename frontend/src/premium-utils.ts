/**
 * Shared helpers for the Sanctus Premium flow.
 * Kept tiny on purpose so any screen can pull it in.
 */
import { Platform } from "react-native";

export function publicOrigin(): string {
  if (Platform.OS === "web" && typeof window !== "undefined") {
    return window.location.origin;
  }
  const base = process.env.EXPO_PUBLIC_BACKEND_URL || "";
  return base.replace(/\/$/, "");
}

/** Detect the 402 Payment Required error raised by backend premium gates. */
export function isPaywallError(err: unknown): boolean {
  if (!err || typeof err !== "object") return false;
  const status = (err as { status?: number }).status;
  if (status === 402) return true;
  const msg = (err as { message?: string }).message || "";
  return msg.toLowerCase().includes("sanctus premium is required");
}

export function formatCents(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

export function describeStatus(
  status?: string | null,
  trialEnd?: number | null,
): string {
  const s = (status || "").toLowerCase();
  if (s === "trialing") {
    if (trialEnd) {
      const d = new Date(trialEnd * 1000);
      return `Free trial — ends ${d.toLocaleDateString()}`;
    }
    return "Free trial active";
  }
  if (s === "active") return "Active";
  if (s === "past_due") return "Payment past due";
  if (s === "canceled" || s === "cancelled") return "Canceled";
  if (s === "unpaid") return "Unpaid";
  if (s === "incomplete") return "Awaiting payment";
  if (!s) return "Inactive";
  return s.replace(/_/g, " ");
}

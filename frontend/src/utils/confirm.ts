/**
 * Cross-platform confirm() helper.
 *
 * Problem: On the web platform, React Native's `Alert.alert(title, msg, buttons)`
 * just calls `window.alert(msg)` — it shows OK only and silently drops every
 * button callback (including destructive ones). That's why "Reject" and
 * "Delete" buttons in admin screens appear to do nothing on the web preview.
 *
 * Solution: On web, fall back to the browser's built-in `window.confirm`,
 * which returns a real boolean. On native, use `Alert.alert` with a proper
 * Cancel + destructive button pair and resolve based on which was tapped.
 *
 * Usage:
 *
 *     const ok = await confirm({
 *       title: "Delete saint?",
 *       message: "This cannot be undone.",
 *       confirmText: "Delete",
 *       destructive: true,
 *     });
 *     if (!ok) return;
 *     await adminDeleteSaint(id);
 */
import { Alert, Platform } from "react-native";

export type ConfirmOptions = {
  title: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  destructive?: boolean;
};

export async function confirm(opts: ConfirmOptions): Promise<boolean> {
  const {
    title,
    message = "",
    confirmText = "Confirm",
    cancelText = "Cancel",
    destructive = false,
  } = opts;

  if (Platform.OS === "web") {
    if (typeof window === "undefined" || typeof window.confirm !== "function") {
      // No window/confirm available — fail open (do nothing) to be safe.
      return false;
    }
    // Web's confirm only takes a single string; join title + message.
    const body = message ? `${title}\n\n${message}` : title;
    return window.confirm(body);
  }

  return new Promise<boolean>((resolve) => {
    Alert.alert(
      title,
      message || undefined,
      [
        { text: cancelText, style: "cancel", onPress: () => resolve(false) },
        {
          text: confirmText,
          style: destructive ? "destructive" : "default",
          onPress: () => resolve(true),
        },
      ],
      { cancelable: true, onDismiss: () => resolve(false) },
    );
  });
}

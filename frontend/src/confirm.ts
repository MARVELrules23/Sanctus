import { Alert, Platform } from "react-native";

/**
 * Cross-platform confirmation dialog.
 *
 * `Alert.alert` is a silent no-op on React Native Web, which meant destructive
 * actions wired only through Alert (e.g. "Delete entry") never fired in the web
 * preview. This helper falls back to `window.confirm` on web and uses the native
 * Alert elsewhere, always resolving to a boolean.
 */
export function confirmAction(
  title: string,
  message: string,
  confirmLabel = "Delete",
  destructive = true,
): Promise<boolean> {
  if (Platform.OS === "web") {
    if (typeof window !== "undefined" && typeof window.confirm === "function") {
      return Promise.resolve(window.confirm(`${title}\n\n${message}`));
    }
    return Promise.resolve(true);
  }
  return new Promise((resolve) => {
    Alert.alert(
      title,
      message,
      [
        { text: "Cancel", style: "cancel", onPress: () => resolve(false) },
        {
          text: confirmLabel,
          style: destructive ? "destructive" : "default",
          onPress: () => resolve(true),
        },
      ],
      { cancelable: true, onDismiss: () => resolve(false) },
    );
  });
}

import { Platform } from "react-native";
import { useKeepAwake as expoUseKeepAwake } from "expo-keep-awake";

/**
 * Web-safe wrapper around `expo-keep-awake`'s `useKeepAwake` hook.
 *
 * On web the underlying call requests the Wake Lock API, which can throw
 * "Wake Lock permission request denied" in iframe / dev contexts — surfacing
 * as a red-screen overlay that blocks the whole flow.
 *
 * On native (iOS / Android) we delegate normally so the screen actually
 * stays awake during meditation and study sessions.
 */
export function useKeepAwake(): void {
  if (Platform.OS === "web") {
    return;
  }
  // eslint-disable-next-line react-hooks/rules-of-hooks
  expoUseKeepAwake();
}

/**
 * useChallengeMasterPref — a single master toggle deciding whether
 * Liturgical Challenges are surfaced anywhere outside the dedicated
 * /challenges hub (i.e., the Home card and Calendar overlays).
 *
 * Persisted with AsyncStorage so the user only has to flip it once
 * per device. Hook returns `{ enabled, setEnabled, ready }`.
 */
import { useCallback, useEffect, useState } from "react";

import { storage } from "@/src/utils/storage";

const STORAGE_KEY = "sanctus:challenges:showOnCalendar";

export function useChallengeMasterPref() {
  // Default ON so every liturgical challenge is visible on the calendar out of
  // the box; the user can still turn the overlay off. We only treat an
  // explicitly-stored `false` as off.
  const [enabled, setEnabledState] = useState(true);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancel = false;
    (async () => {
      const v = await storage.getItem<boolean>(STORAGE_KEY, true);
      if (cancel) return;
      setEnabledState(v !== false);
      setReady(true);
    })();
    return () => {
      cancel = true;
    };
  }, []);

  const setEnabled = useCallback(async (next: boolean) => {
    setEnabledState(next);
    try {
      await storage.setItem(STORAGE_KEY, next);
    } catch {
      // best-effort persistence; in-memory state already updated
    }
  }, []);

  return { enabled, setEnabled, ready };
}

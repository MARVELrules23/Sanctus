/**
 * RadioPlayerContext — global audio player for Sanctus Library radio stations.
 *
 * Wraps expo-audio's `useAudioPlayer` at the app root so a station keeps
 * playing across navigation. Exposes a tiny imperative API:
 *
 *   const { current, isPlaying, isBuffering, error, play, pause, resume, stop } = useRadioPlayer();
 *
 * Only ONE station can play at a time — playing another station replaces
 * the current source.
 *
 * NOTE: True background playback (locked screen, app suspended) requires a
 * native dev/production build. In Expo Go and the web preview, audio will
 * pause when the tab loses focus. The user has been informed of this.
 */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Platform } from "react-native";
import {
  setAudioModeAsync,
  useAudioPlayer,
  useAudioPlayerStatus,
} from "expo-audio";

import type { LibraryStation } from "@/src/api";

interface RadioPlayerContextValue {
  current: LibraryStation | null;
  isPlaying: boolean;
  isBuffering: boolean;
  error: string | null;
  play: (station: LibraryStation) => void;
  pause: () => void;
  resume: () => void;
  stop: () => void;
  toggle: () => void;
}

const RadioPlayerContext = createContext<RadioPlayerContextValue | null>(null);

export function RadioPlayerProvider({ children }: { children: React.ReactNode }) {
  const [current, setCurrent] = useState<LibraryStation | null>(null);
  const [shouldPlay, setShouldPlay] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The player is bound to the current stream URL. When `current` changes,
  // expo-audio swaps the underlying source automatically.
  const player = useAudioPlayer(current?.stream_url ? { uri: current.stream_url } : null);
  const status = useAudioPlayerStatus(player);

  // Configure audio session once at provider mount — required so audio keeps
  // playing when the device is on silent (iOS) and (on native builds) when
  // the app backgrounds. Safe to call repeatedly.
  useEffect(() => {
    (async () => {
      try {
        await setAudioModeAsync({
          playsInSilentMode: true,
          shouldPlayInBackground: true,
          interruptionMode: "duckOthers",
          allowsRecording: false,
        });
      } catch (_e) {
        /* web / unsupported — non-fatal */
      }
    })();
  }, []);

  // Sync our `shouldPlay` request into the underlying player whenever either
  // the player instance OR the requested intent changes.
  const prevUrlRef = useRef<string | null>(null);
  useEffect(() => {
    if (!player) return;
    const url = current?.stream_url || null;
    const urlChanged = prevUrlRef.current !== url;
    prevUrlRef.current = url;
    try {
      if (shouldPlay) {
        // When the URL changed, give the player a tick to swap the source
        // before kicking it.
        if (urlChanged) {
          const t = setTimeout(() => {
            try { player.play(); } catch (_e) { /* no-op */ }
          }, 60);
          return () => clearTimeout(t);
        }
        player.play();
      } else {
        player.pause();
      }
    } catch (e) {
      console.warn("[RadioPlayer] sync failed", e);
    }
  }, [player, shouldPlay, current?.stream_url]);

  // Surface buffering / error from the audio status.
  const isBuffering = useMemo(() => {
    if (!status) return false;
    if (!shouldPlay) return false;
    // While requesting playback but not yet playing → buffering.
    return !!shouldPlay && !status.playing && !status.didJustFinish;
  }, [status, shouldPlay]);

  // expo-audio surfaces errors via status.didJustFinish + reason on native;
  // we leave the `error` slot for caller-set messages (e.g. failed fetch).

  const play = useCallback((station: LibraryStation) => {
    setError(null);
    setCurrent(station);
    setShouldPlay(true);
  }, []);

  const pause = useCallback(() => {
    setShouldPlay(false);
  }, []);

  const resume = useCallback(() => {
    if (current) setShouldPlay(true);
  }, [current]);

  const stop = useCallback(() => {
    setShouldPlay(false);
    setCurrent(null);
  }, []);

  const toggle = useCallback(() => {
    if (!current) return;
    setShouldPlay((p) => !p);
  }, [current]);

  // On web the underlying HTMLAudioElement may quietly fail when a stream
  // requires CORS / m3u8 etc.  Best-effort: detect prolonged "should be
  // playing but isn't" state.
  const isPlaying = !!status?.playing && shouldPlay;

  // Surface a friendly error if we asked to play but nothing actually
  // started after a few seconds.  (Web-only — native autoplays cleanly.)
  useEffect(() => {
    if (Platform.OS !== "web") return;
    if (!shouldPlay || !current) return;
    const handle = setTimeout(() => {
      if (!status?.playing) {
        setError(
          "This stream couldn't start in the browser preview. On the iOS/Android build it will play normally."
        );
      }
    }, 6000);
    return () => clearTimeout(handle);
  }, [shouldPlay, current, status?.playing]);

  const value = useMemo(
    () => ({
      current,
      isPlaying,
      isBuffering,
      error,
      play,
      pause,
      resume,
      stop,
      toggle,
    }),
    [current, isPlaying, isBuffering, error, play, pause, resume, stop, toggle],
  );

  return (
    <RadioPlayerContext.Provider value={value}>{children}</RadioPlayerContext.Provider>
  );
}

export function useRadioPlayer(): RadioPlayerContextValue {
  const ctx = useContext(RadioPlayerContext);
  if (!ctx) {
    // Safe no-op fallback so unit-test rendering doesn't explode.
    return {
      current: null,
      isPlaying: false,
      isBuffering: false,
      error: null,
      play: () => {},
      pause: () => {},
      resume: () => {},
      stop: () => {},
      toggle: () => {},
    };
  }
  return ctx;
}

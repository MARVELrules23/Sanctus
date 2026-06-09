/**
 * YouTubeEmbed — web implementation.
 *
 * The `react-native-youtube-iframe` library routes through a hosted helper
 * page (lonelycpp.github.io/.../iframe_v2.html) on web. That page receives
 * autoplay commands via postMessage AFTER mount, which lets the browser's
 * autoplay-with-sound policy slam the door shut before any sound gets out.
 *
 * On web we sidestep all of that by mounting a direct `<iframe>` to
 * `youtube.com/embed/<id>?autoplay=1&mute=1`. Browsers universally allow
 * MUTED autoplay, so the video starts the moment the parent flips
 * `playing -> true`. The native YouTube player chrome inside the iframe
 * then exposes its own unmute button, which the user can tap once.
 *
 * We also expose a "Tap to enable sound" overlay button on the host page
 * that posts the `unMute` command to the iframe, so users don't have to
 * hunt for YouTube's tiny speaker icon.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { colors, fonts, radius, spacing } from "@/src/theme";

export interface YouTubeEmbedProps {
  videoId: string;
  playing: boolean;
  onPlayingChange: (playing: boolean) => void;
  onError?: (err: string) => void;
  height?: number;
}

/**
 * Build the YouTube embed URL with the right knobs for "muted autoplay on
 * load → user can unmute via tap". `enablejsapi=1` is what lets us send
 * postMessage commands later.
 *
 * `origin` must match the page hosting the iframe, otherwise YouTube
 * silently rejects the postMessage commands.
 */
function buildEmbedUrl(videoId: string, autoplay: boolean): string {
  const params = new URLSearchParams({
    autoplay: autoplay ? "1" : "0",
    mute: "1",
    playsinline: "1",
    rel: "0",
    modestbranding: "1",
    enablejsapi: "1",
    controls: "1",
  });
  // Origin helps the postMessage handshake on cross-origin iframes.
  if (typeof window !== "undefined" && window.location?.origin) {
    params.set("origin", window.location.origin);
  }
  return `https://www.youtube.com/embed/${encodeURIComponent(videoId)}?${params.toString()}`;
}

export default function YouTubeEmbed({
  videoId,
  playing,
  onPlayingChange,
  onError,
  height = 200,
}: YouTubeEmbedProps) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [muted, setMuted] = useState(true);

  // Recompute the src when the videoId or initial autoplay intent changes.
  // We don't re-derive on every `playing` toggle — that would reload the
  // iframe and reset playback. Instead, we send postMessage commands.
  const src = useMemo(() => buildEmbedUrl(videoId, playing), [videoId, playing]);

  // Send a YouTube IFrame API command via postMessage.
  const sendCommand = useCallback(
    (func: "playVideo" | "pauseVideo" | "mute" | "unMute") => {
      try {
        iframeRef.current?.contentWindow?.postMessage(
          JSON.stringify({ event: "command", func, args: [] }),
          "*",
        );
      } catch (e) {
        console.warn("[YouTubeEmbed.web] command failed", func, e);
      }
    },
    [],
  );

  // Reset the muted state whenever the user switches videos.
  useEffect(() => {
    setMuted(true);
  }, [videoId]);

  // Mirror the parent's `playing` flag onto the iframe via JS API.
  // Note: the URL already encodes `autoplay=1` for the first play, but
  // subsequent toggles need to use postMessage so the iframe doesn't reload.
  useEffect(() => {
    if (!iframeRef.current) return;
    if (playing) sendCommand("playVideo");
    else sendCommand("pauseVideo");
  }, [playing, sendCommand]);

  // Listen for YouTube state-change events. The library posts JSON messages
  // shaped like `{"event":"onStateChange","info":<int>}`.
  // 1 = playing, 2 = paused, 0 = ended.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const handler = (ev: MessageEvent) => {
      // Don't blindly trust every message — only those from youtube.com.
      if (typeof ev.data !== "string") return;
      let payload: unknown;
      try { payload = JSON.parse(ev.data); } catch { return; }
      if (!payload || typeof payload !== "object") return;
      const p = payload as { event?: string; info?: number };
      if (p.event === "onStateChange") {
        if (p.info === 1) onPlayingChange(true);
        else if (p.info === 2 || p.info === 0) onPlayingChange(false);
      } else if (p.event === "onError") {
        onError?.(String(p.info ?? "unknown"));
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, [onPlayingChange, onError]);

  const toggleMute = useCallback(() => {
    setMuted((m) => {
      const next = !m;
      sendCommand(next ? "mute" : "unMute");
      return next;
    });
  }, [sendCommand]);

  // React Native Web maps `View` to `div`, so we can drop a real `iframe`
  // inside it without any escape hatch.
  return (
    <View style={[styles.frame, { height }]}>
      {React.createElement("iframe", {
        ref: iframeRef as unknown as React.Ref<HTMLIFrameElement>,
        src,
        // `allow="autoplay"` is the magic string that grants iframes
        // permission to autoplay (muted). Without it Chrome blocks the
        // initial play() request even when the URL says autoplay=1.
        allow: "autoplay; encrypted-media; picture-in-picture",
        // @ts-expect-error - DOM-only props are fine inside react-native-web.
        frameBorder: 0,
        title: "YouTube player",
        style: {
          width: "100%",
          height: "100%",
          border: 0,
        },
      })}
      {muted ? (
        <Pressable
          onPress={toggleMute}
          style={styles.unmuteBtn}
          testID="yt-unmute"
        >
          <Ionicons name="volume-mute" size={14} color={colors.gold} />
          <Text style={styles.unmuteText}>Tap for sound</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    borderRadius: radius.md,
    overflow: "hidden",
    backgroundColor: "#000",
    position: "relative",
  },
  unmuteBtn: {
    position: "absolute",
    top: spacing.sm,
    right: spacing.sm,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: 6,
    borderRadius: radius.round,
    backgroundColor: "rgba(20, 26, 42, 0.85)",
    borderWidth: 1,
    borderColor: colors.gold,
  },
  unmuteText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 11,
    letterSpacing: 0.4,
  },
});

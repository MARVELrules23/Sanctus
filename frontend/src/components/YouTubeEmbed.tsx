/**
 * YouTubeEmbed — native implementation.
 *
 * Uses react-native-youtube-iframe (a WebView-backed YouTube IFrame API
 * wrapper). On iOS/Android the native WebView can be configured with
 * `mediaPlaybackRequiresUserAction: false`, which is enough to autoplay
 * once `play={true}` is sent.
 *
 * Apps a "muted autoplay → unmute on confirmed play" strategy as a belt-
 * and-suspenders measure for stricter WebViews.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { StyleSheet, View } from "react-native";
import YoutubePlayer from "react-native-youtube-iframe";

import { radius } from "@/src/theme";

export interface YouTubeEmbedProps {
  videoId: string;
  playing: boolean;
  onPlayingChange: (playing: boolean) => void;
  onError?: (err: string) => void;
  height?: number;
}

export default function YouTubeEmbed({
  videoId,
  playing,
  onPlayingChange,
  onError,
  height = 200,
}: YouTubeEmbedProps) {
  const [muted, setMuted] = useState(true);
  const unmuteTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearUnmuteTimer = () => {
    if (unmuteTimerRef.current) {
      clearTimeout(unmuteTimerRef.current);
      unmuteTimerRef.current = null;
    }
  };

  // Re-arm the muted-autoplay flow whenever the parent toggles `playing`
  // on, or whenever the user switches to a different video.
  useEffect(() => {
    if (playing) {
      setMuted(true);
    } else {
      setMuted(true);
      clearUnmuteTimer();
    }
  }, [playing, videoId]);

  useEffect(() => clearUnmuteTimer, []);

  const onChangeState = useCallback(
    (event: string) => {
      if (event === "playing") {
        onPlayingChange(true);
        clearUnmuteTimer();
        unmuteTimerRef.current = setTimeout(() => {
          setMuted(false);
        }, 250);
      } else if (event === "paused" || event === "ended") {
        onPlayingChange(false);
        clearUnmuteTimer();
        setMuted(true);
      }
    },
    [onPlayingChange],
  );

  return (
    <View style={styles.frame}>
      <YoutubePlayer
        height={height}
        videoId={videoId}
        play={playing}
        mute={muted}
        onChangeState={onChangeState}
        onError={onError}
        webViewProps={{
          allowsInlineMediaPlayback: true,
          mediaPlaybackRequiresUserAction: false,
          javaScriptEnabled: true,
          domStorageEnabled: true,
        }}
        initialPlayerParams={{
          controls: true,
          modestbranding: true,
          playsinline: true,
          rel: false,
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    borderRadius: radius.md,
    overflow: "hidden",
    alignItems: "center",
  },
});

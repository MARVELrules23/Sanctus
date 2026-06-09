/**
 * YouTubeEmbed — native implementation.
 *
 * Uses react-native-youtube-iframe, which mounts a real native WebView on
 * iOS/Android. The WebView is configured with
 * `mediaPlaybackRequiresUserAction: false` and
 * `allowsInlineMediaPlayback: true`, which together tell the OS-level
 * media policy: "no user gesture required for playback to begin."
 *
 * That means we can autoplay AUDIBLY on native — the `mute=true → unmute`
 * dance the web build uses is unnecessary here. We pass `mute={false}` from
 * the start so audio starts the moment the parent flips `playing → true`.
 *
 * (Browser autoplay-with-sound restrictions only exist on the WEB target,
 * because the host browser owns the media engagement policy. That's why
 * the `.web.tsx` variant has to keep the muted-first flow.)
 */
import React, { useCallback } from "react";
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
  const onChangeState = useCallback(
    (event: string) => {
      // YouTube IFrame API lifecycle: "unstarted", "ended", "playing",
      // "paused", "buffering", "video cued".
      if (event === "playing") onPlayingChange(true);
      else if (event === "paused" || event === "ended") onPlayingChange(false);
    },
    [onPlayingChange],
  );

  return (
    <View style={styles.frame}>
      <YoutubePlayer
        height={height}
        videoId={videoId}
        play={playing}
        // Audible from the start: the WebView config below permits this.
        mute={false}
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

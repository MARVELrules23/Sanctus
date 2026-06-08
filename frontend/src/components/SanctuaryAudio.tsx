import React, { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useAudioPlayer, useAudioPlayerStatus } from "expo-audio";
import YoutubePlayer from "react-native-youtube-iframe";

import { colors, fonts, radius, spacing } from "@/src/theme";
import type { SanctuaryTrack } from "@/src/utils/sanctuary-tracks";

/**
 * SanctuaryAudio — plays either an MP3 (via expo-audio) or a YouTube video
 * (via react-native-youtube-iframe). Auto-routes by track.source.kind.
 *
 * The player tries to be transparent to the parent: pass `track` and `playing`,
 * and we keep the underlying media in sync. When the user pauses/plays, we
 * call `onPlayPauseChange` so the parent can lift state up (e.g. for a global
 * "now playing" indicator).
 */
export interface SanctuaryAudioProps {
  track: SanctuaryTrack | null;
  playing: boolean;
  onPlayPauseChange: (playing: boolean) => void;
  /**
   * "compact" hides the rich card around it and exposes only the play button
   * — useful when the parent already has its own UI for the track.
   */
  variant?: "card" | "compact";
}

export default function SanctuaryAudio({
  track,
  playing,
  onPlayPauseChange,
  variant = "card",
}: SanctuaryAudioProps) {
  if (!track) {
    return variant === "compact" ? null : (
      <View style={styles.card}>
        <Text style={styles.empty}>Pick a track to begin.</Text>
      </View>
    );
  }
  return track.source.kind === "youtube" ? (
    <YoutubeBackedPlayer
      track={track}
      videoId={track.source.videoId}
      playing={playing}
      onPlayPauseChange={onPlayPauseChange}
      variant={variant}
    />
  ) : (
    <Mp3BackedPlayer
      track={track}
      uri={track.source.uri}
      playing={playing}
      onPlayPauseChange={onPlayPauseChange}
      variant={variant}
    />
  );
}

/* -------------------------------------------------------------------------- */
/*  MP3 backend (expo-audio)                                                  */
/* -------------------------------------------------------------------------- */

function Mp3BackedPlayer({
  track,
  uri,
  playing,
  onPlayPauseChange,
  variant,
}: {
  track: SanctuaryTrack;
  uri: string;
  playing: boolean;
  onPlayPauseChange: (p: boolean) => void;
  variant: "card" | "compact";
}) {
  const player = useAudioPlayer({ uri });
  const status = useAudioPlayerStatus(player);

  // Sync external `playing` request → player state
  useEffect(() => {
    if (!player) return;
    try {
      if (playing) {
        player.play();
      } else {
        player.pause();
      }
    } catch (e) {
      console.warn("[SanctuaryAudio mp3] sync failed", e);
    }
  }, [playing, player]);

  // When the track finishes naturally, tell the parent we stopped.
  useEffect(() => {
    if (status?.didJustFinish) {
      onPlayPauseChange(false);
      try {
        player.seekTo(0);
      } catch (_e) {
        /* no-op */
      }
    }
  }, [status?.didJustFinish, onPlayPauseChange, player]);

  const isLoading = status && !status.isLoaded;

  return (
    <PlayerChrome
      track={track}
      playing={playing}
      loading={!!isLoading}
      onToggle={() => onPlayPauseChange(!playing)}
      variant={variant}
    />
  );
}

/* -------------------------------------------------------------------------- */
/*  YouTube backend (react-native-youtube-iframe)                             */
/* -------------------------------------------------------------------------- */

function YoutubeBackedPlayer({
  track,
  videoId,
  playing,
  onPlayPauseChange,
  variant,
}: {
  track: SanctuaryTrack;
  videoId: string;
  playing: boolean;
  onPlayPauseChange: (p: boolean) => void;
  variant: "card" | "compact";
}) {
  // We always render the iframe (small, but visible). When `playing` is true,
  // the iframe API drives playback.
  const [ready, setReady] = useState(false);
  const lastTrackRef = useRef<string>(track.id);

  // If the track id changes (different YouTube video), reset readiness.
  useEffect(() => {
    if (lastTrackRef.current !== track.id) {
      lastTrackRef.current = track.id;
      setReady(false);
    }
  }, [track.id]);

  const onChangeState = React.useCallback(
    (event: string) => {
      if (event === "paused" || event === "ended") {
        onPlayPauseChange(false);
      } else if (event === "playing") {
        onPlayPauseChange(true);
      }
    },
    [onPlayPauseChange],
  );

  return (
    <View>
      <PlayerChrome
        track={track}
        playing={playing}
        loading={!ready}
        onToggle={() => onPlayPauseChange(!playing)}
        variant={variant}
      />
      <View style={styles.youtubeFrame}>
        <YoutubePlayer
          height={180}
          width={300}
          videoId={videoId}
          play={playing}
          onReady={() => setReady(true)}
          onChangeState={onChangeState}
          webViewProps={{ allowsInlineMediaPlayback: true }}
          initialPlayerParams={{ controls: true, modestbranding: true }}
        />
      </View>
    </View>
  );
}

/* -------------------------------------------------------------------------- */
/*  Visual chrome shared by both player kinds                                 */
/* -------------------------------------------------------------------------- */

function PlayerChrome({
  track,
  playing,
  loading,
  onToggle,
  variant,
}: {
  track: SanctuaryTrack;
  playing: boolean;
  loading: boolean;
  onToggle: () => void;
  variant: "card" | "compact";
}) {
  if (variant === "compact") {
    return (
      <Pressable
        onPress={onToggle}
        disabled={loading}
        style={({ pressed }) => [styles.compactBtn, pressed && styles.pressed]}
        testID="sanctuary-audio-toggle"
      >
        {loading ? (
          <ActivityIndicator color={colors.gold} />
        ) : (
          <Ionicons
            name={playing ? "pause" : "play"}
            size={22}
            color={colors.gold}
          />
        )}
      </Pressable>
    );
  }
  return (
    <View style={styles.card} testID="sanctuary-audio-card">
      <View style={{ flex: 1 }}>
        <Text style={styles.title} numberOfLines={1}>{track.title}</Text>
        <Text style={styles.artist} numberOfLines={1}>{track.artist}</Text>
        {track.durationLabel ? (
          <Text style={styles.duration}>{track.durationLabel}</Text>
        ) : null}
      </View>
      <Pressable
        onPress={onToggle}
        disabled={loading}
        style={({ pressed }) => [styles.playBtn, pressed && styles.pressed]}
        testID="sanctuary-audio-toggle"
      >
        {loading ? (
          <ActivityIndicator color={colors.gold} />
        ) : (
          <Ionicons
            name={playing ? "pause" : "play"}
            size={24}
            color={colors.gold}
          />
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.md,
  },
  empty: {
    fontFamily: fonts.bodyRegular,
    color: colors.gold,
    opacity: 0.7,
    fontSize: 13,
  },
  title: {
    fontFamily: fonts.headingSemi,
    color: colors.gold,
    fontSize: 16,
  },
  artist: {
    fontFamily: fonts.bodyRegular,
    color: colors.gold,
    opacity: 0.85,
    fontSize: 12,
    marginTop: 2,
  },
  duration: {
    fontFamily: fonts.uiMedium,
    color: colors.gold,
    opacity: 0.6,
    fontSize: 11,
    marginTop: 4,
    letterSpacing: 0.5,
  },
  playBtn: {
    width: 48,
    height: 48,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: colors.gold,
    alignItems: "center",
    justifyContent: "center",
  },
  compactBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  youtubeFrame: {
    marginTop: spacing.md,
    borderRadius: radius.md,
    overflow: "hidden",
    alignItems: "center",
  },
  pressed: { opacity: 0.7 },
});

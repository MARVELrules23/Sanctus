import { Platform } from "react-native";
import * as Speech from "expo-speech";

import { storage } from "@/src/utils/storage";

const VOICE_KEY = "sanctus_sd_voice_enabled";

export async function loadVoiceEnabled(): Promise<boolean> {
  const v = await storage.getItem<boolean>(VOICE_KEY, true);
  return v !== false;
}

export async function saveVoiceEnabled(enabled: boolean): Promise<void> {
  await storage.setItem(VOICE_KEY, enabled);
}

/**
 * Pick a calm, slower voice when available. Falls back to the platform default.
 * iOS: prefers Siri (enhanced) or 'com.apple.speech.synthesis.voice.daniel'.
 * Android: prefers en-US / en-GB female voices.
 * Web: SpeechSynthesis built-in.
 */
async function pickSoothingVoice(): Promise<string | undefined> {
  try {
    const voices = await Speech.getAvailableVoicesAsync();
    if (!voices || voices.length === 0) return undefined;
    // Prefer English voices with "enhanced" / "premium" quality if available
    const candidates = voices.filter(
      (v) => v.language?.toLowerCase().startsWith("en"),
    );
    // Heuristic: enhanced/serene/calm-sounding voices first
    const preferredNames = [
      "Daniel",
      "Samantha",
      "Karen",
      "Moira",
      "Ava",
      "Serena",
      "Rishi",
      "Tessa",
    ];
    for (const name of preferredNames) {
      const found = candidates.find(
        (v) => v.name?.toLowerCase().includes(name.toLowerCase()),
      );
      if (found) return found.identifier;
    }
    return candidates[0]?.identifier;
  } catch {
    return undefined;
  }
}

let cachedVoice: string | undefined | null = null;

export async function speak(text: string, enabled: boolean): Promise<void> {
  if (!enabled) return;
  if (!text || !text.trim()) return;
  try {
    if (cachedVoice === null) {
      cachedVoice = await pickSoothingVoice();
    }
    // Stop any current speech first to avoid stacking
    Speech.stop();
    Speech.speak(text, {
      voice: cachedVoice || undefined,
      // Slower, soothing delivery
      rate: Platform.OS === "ios" ? 0.45 : 0.85,
      pitch: 0.95,
      language: "en-US",
    });
  } catch {
    // Swallow — voice is optional
  }
}

export function stopSpeaking(): void {
  try {
    Speech.stop();
  } catch {
    // ignore
  }
}

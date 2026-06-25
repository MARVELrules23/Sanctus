/**
 * AutoText — a drop-in replacement for react-native's <Text> that automatically
 * renders its (string) content in the app's currently-selected language.
 *
 * How it works:
 *  - When the language is English we render the text verbatim (zero overhead).
 *  - For Spanish / Italian we look the string up in a process-wide cache. Misses
 *    are queued and flushed as a single batched call to the permanent
 *    /api/translate cache (LLM-backed, cached forever on the server), then every
 *    mounted AutoText re-renders with the translated copy.
 *
 * Screens opt in with a single import alias:
 *    import { AutoText as Text } from "@/src/auto-text";
 * …after which every <Text>…</Text> in that screen is bilingual for free.
 *
 * Only plain string / string[] children are translated; nested elements,
 * numbers and purely numeric/symbol strings are rendered untouched.
 */
import React, { useEffect, useState } from "react";
import { Text as RNText, TextProps } from "react-native";
import { useI18n } from "@/src/i18n";
import { translateTexts } from "@/src/api";

// lang -> { englishString: translatedString }
const cache: Record<string, Record<string, string>> = {};
// lang -> set of strings awaiting translation
const queue: Record<string, Set<string>> = {};
let flushTimer: ReturnType<typeof setTimeout> | null = null;
const subscribers = new Set<() => void>();

function notifyAll() {
  subscribers.forEach((fn) => fn());
}

function enqueue(lang: string, text: string) {
  if (!cache[lang]) cache[lang] = {};
  if (cache[lang][text] !== undefined) return;
  if (!queue[lang]) queue[lang] = new Set();
  if (queue[lang].has(text)) return;
  queue[lang].add(text);
  if (flushTimer) clearTimeout(flushTimer);
  flushTimer = setTimeout(flush, 150);
}

async function flush() {
  flushTimer = null;
  for (const lang of Object.keys(queue)) {
    const arr = Array.from(queue[lang]);
    queue[lang] = new Set();
    if (!arr.length) continue;
    try {
      const items = await translateTexts(arr, lang);
      if (!cache[lang]) cache[lang] = {};
      arr.forEach((s, i) => {
        cache[lang][s] = items[i] || s;
      });
      notifyAll();
    } catch {
      // Leave English in place on failure; it can retry on a later mount.
    }
  }
}

function childToString(children: React.ReactNode): string | null {
  if (typeof children === "string") return children;
  if (typeof children === "number") return null;
  if (Array.isArray(children) && children.every((c) => typeof c === "string")) {
    return (children as string[]).join("");
  }
  return null;
}

export function AutoText({ children, ...rest }: TextProps) {
  const { lang } = useI18n();
  const [, force] = useState(0);

  useEffect(() => {
    const fn = () => force((x) => x + 1);
    subscribers.add(fn);
    return () => {
      subscribers.delete(fn);
    };
  }, []);

  let out: React.ReactNode = children;
  if (lang !== "en") {
    const s = childToString(children);
    // Translate only if there is at least one letter (skip numbers, symbols).
    if (s && /[A-Za-zÀ-ÿ]/.test(s)) {
      const hit = cache[lang]?.[s];
      if (hit !== undefined) out = hit;
      else enqueue(lang, s);
    }
  }

  return <RNText {...rest}>{out}</RNText>;
}

export default AutoText;

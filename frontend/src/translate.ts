/**
 * On-demand translation hook for otherwise-static content (prayers, chaplets,
 * rosary). When the app language is Spanish, the given strings are batch-sent
 * to the backend `/translate` endpoint (which returns canonical liturgical
 * Spanish for known prayers and caches results). Returns a `tr(s)` lookup that
 * yields the translated string, falling back to the original while loading or
 * in English.
 */
import { useEffect, useMemo, useState } from "react";

import { translateTexts } from "@/src/api";
import { useI18n } from "@/src/i18n";

export function useTranslator(strings: string[]): { tr: (s: string) => string; ready: boolean } {
  const { lang } = useI18n();
  const [map, setMap] = useState<Record<string, string>>({});

  // Stable, deduped list of non-empty strings to translate.
  const uniq = useMemo(
    () => Array.from(new Set(strings.filter((s) => s && s.trim()))),
    [strings],
  );
  const sig = useMemo(() => uniq.join("\u0001"), [uniq]);

  useEffect(() => {
    let alive = true;
    if (lang === "en" || uniq.length === 0) {
      setMap({});
      return;
    }
    translateTexts(uniq, lang)
      .then((items) => {
        if (!alive) return;
        const m: Record<string, string> = {};
        uniq.forEach((s, i) => { m[s] = items[i] || s; });
        setMap(m);
      })
      .catch(() => { /* keep English on failure */ });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, sig]);

  const tr = (s: string) => (lang !== "en" ? map[s] || s : s);
  return { tr, ready: lang === "en" || Object.keys(map).length > 0 };
}

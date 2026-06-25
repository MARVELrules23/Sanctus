"""Iteration 56 — Bug verification: /api/readings honors Accept-Language for it/es/en.

Root cause (per main agent): translation prompt produced JSON parse errors when
Scripture contained unescaped quotes, leaving readings stuck in English and
poisoning the cache. Fix: robust translate_texts batcher + plain-text fallback
+ only cache successful translations. This test verifies the endpoint returns
properly Italian / Spanish content for an arbitrary date, with citations
preserved.
"""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_feat_aug25"
DATE = "2026-06-25"  # arbitrary mid-week date used in problem statement


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Authorization": f"Bearer {TOKEN}"})
    return sess


def _fetch(s, lang: str, date: str = DATE, timeout: int = 90):
    r = s.get(
        f"{BASE_URL}/api/readings",
        params={"date": date},
        headers={"Accept-Language": lang},
        timeout=timeout,
    )
    assert r.status_code == 200, f"{lang} -> {r.status_code} {r.text[:200]}"
    return r.json()


# Quick chars used to detect non-English content. Italian/Spanish use accents,
# guillemets, "¿/¡" etc. but the most reliable signal is a non-English diacritic.
ITALIAN_HINTS = re.compile(r"[àèéìòù«»]|\b(Gesù|disse|discepoli|Vangelo|Salmo|Padre|Cristo|Signore)\b", re.IGNORECASE)
SPANISH_HINTS = re.compile(r"[ñáéíóú¿¡«»]|\b(Jesús|dijo|discípulos|Evangelio|Salmo|Padre|Cristo|Señor)\b", re.IGNORECASE)


def test_readings_english_baseline(s):
    """EN: should be in English, lang field is 'en' (or absent for legacy doc)."""
    d = _fetch(s, "en")
    assert d.get("date") == DATE
    # English doc should not have any Italian/Spanish-only diacritics in gospel
    g = (d.get("gospel_excerpt") or "")
    assert g, "gospel_excerpt missing for EN"
    # english gospel should NOT contain Italian-only words like "Gesù"
    assert "Gesù" not in g
    assert "Jesús" not in g


def test_readings_italian_translated(s):
    """IT: gospel excerpt, reflection, liturgical_title must be Italian."""
    d = _fetch(s, "it")
    assert d.get("lang") == "it", f"expected lang=it, got {d.get('lang')}"
    g = (d.get("gospel_excerpt") or "").strip()
    refl = (d.get("reflection") or "").strip()
    lit_title = (d.get("liturgical_title") or "").strip()
    assert g, "gospel_excerpt empty"
    assert refl, "reflection empty"
    assert ITALIAN_HINTS.search(g), f"gospel not Italian: {g[:200]}"
    assert ITALIAN_HINTS.search(refl), f"reflection not Italian: {refl[:200]}"
    if lit_title:
        # Lit title is typically Italian like "Giovedì della XII settimana..."
        # but tolerate if backend left it empty.
        assert ITALIAN_HINTS.search(lit_title) or any(c in lit_title for c in "àèéìòù"), \
            f"liturgical_title not Italian: {lit_title}"
    # Citation must remain like 'Mt 7:21-29' (not translated)
    gospel_cite = (d.get("gospel") or "")
    assert re.search(r"[A-Za-z]+ ?\d+[:,]\s*\d+", gospel_cite) or gospel_cite == "", \
        f"gospel citation looks malformed: {gospel_cite}"


def test_readings_spanish_translated(s):
    d = _fetch(s, "es")
    assert d.get("lang") == "es", f"expected lang=es, got {d.get('lang')}"
    g = (d.get("gospel_excerpt") or "").strip()
    refl = (d.get("reflection") or "").strip()
    assert g and refl
    assert SPANISH_HINTS.search(g), f"gospel not Spanish: {g[:200]}"
    assert SPANISH_HINTS.search(refl), f"reflection not Spanish: {refl[:200]}"


def test_readings_italian_cached_second_call_fast(s):
    """After first call, second call should be fast (cached) and stay Italian."""
    import time
    t0 = time.time()
    d = _fetch(s, "it", timeout=30)
    elapsed = time.time() - t0
    assert d.get("lang") == "it"
    g = d.get("gospel_excerpt") or ""
    assert ITALIAN_HINTS.search(g), "second call lost Italian"
    # Cached call should normally be < 5s; allow some slack on CI.
    assert elapsed < 15, f"cached call too slow: {elapsed:.1f}s (cache may be broken)"


def test_translate_endpoint_italian(s):
    """Sanity: /api/translate batched endpoint still works for Italian."""
    r = s.post(
        f"{BASE_URL}/api/translate",
        json={"texts": ["First Reading", "Responsorial Psalm", "Gospel", "Reflection"], "target": "it"},
        timeout=60,
    )
    assert r.status_code == 200, r.text[:200]
    items = r.json().get("items") or []
    assert len(items) == 4
    # Expect Italian labels
    joined = " ".join(items)
    assert ITALIAN_HINTS.search(joined) or any(w in joined.lower() for w in ["lettura", "salmo", "vangelo", "riflessione"]), \
        f"Italian labels look wrong: {items}"

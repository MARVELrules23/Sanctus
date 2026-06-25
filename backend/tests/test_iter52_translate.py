"""Iteration 52 — Translation + community post delete + AI-in-language smoke tests."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_feat_aug25"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def _auth_headers(lang: str | None = None):
    h = dict(HEADERS)
    if lang:
        h["Accept-Language"] = lang
    return h


# ---------------------------- /api/translate ----------------------------
class TestTranslateEndpoint:
    def test_translate_es_basic_phrases(self):
        payload = {
            "texts": ["Meals", "Workouts", "Wellness", "Sanctuary", "Calendar"],
            "target": "es",
        }
        r = requests.post(f"{BASE_URL}/api/translate", json=payload, headers=HEADERS, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("target") == "es"
        items = data.get("items")
        assert isinstance(items, list) and len(items) == 5
        # All translated values must be non-empty strings
        for src, tr in zip(payload["texts"], items):
            assert isinstance(tr, str) and len(tr.strip()) > 0
        # At least one item should clearly differ from English (translation occurred)
        differing = [s for s, t in zip(payload["texts"], items) if t.lower() != s.lower()]
        assert len(differing) >= 3, f"Too few translations differ from English: {items}"

    def test_translate_it_basic_phrases(self):
        payload = {
            "texts": ["Churches", "Charities", "Self-Defense", "Schedule", "Journal"],
            "target": "it",
        }
        r = requests.post(f"{BASE_URL}/api/translate", json=payload, headers=HEADERS, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("target") == "it"
        items = data["items"]
        assert len(items) == 5
        differing = [s for s, t in zip(payload["texts"], items) if t.lower() != s.lower()]
        assert len(differing) >= 3, f"Italian translations look like English passthrough: {items}"

    def test_translate_cache_hit_is_fast(self):
        # Warm cache
        payload = {"texts": ["Holy Mass", "Adoration", "Confession"], "target": "es"}
        requests.post(f"{BASE_URL}/api/translate", json=payload, headers=HEADERS, timeout=60)
        t0 = time.time()
        r = requests.post(f"{BASE_URL}/api/translate", json=payload, headers=HEADERS, timeout=15)
        dt = time.time() - t0
        assert r.status_code == 200
        # Cached call should be quick (< 5s typically; allow generous bound for preview env)
        assert dt < 8.0, f"Cached translate too slow ({dt:.2f}s)"
        items = r.json()["items"]
        assert all(isinstance(x, str) and x for x in items)

    def test_translate_passthrough_english(self):
        # English target should pass through unchanged
        payload = {"texts": ["Hello", "World"], "target": "en"}
        r = requests.post(f"{BASE_URL}/api/translate", json=payload, headers=HEADERS, timeout=15)
        assert r.status_code == 200
        assert r.json()["items"] == ["Hello", "World"]

    def test_translate_too_many_rejected(self):
        payload = {"texts": [f"item-{i}" for i in range(401)], "target": "es"}
        r = requests.post(f"{BASE_URL}/api/translate", json=payload, headers=HEADERS, timeout=15)
        assert r.status_code == 400


# ---------------------------- Community DELETE ----------------------------
class TestCommunityPostDelete:
    def test_create_then_delete_post_returns_204_and_disappears(self):
        # Create
        body = {"body": "TEST_iter52 delete me", "topic": None, "image": None}
        cr = requests.post(f"{BASE_URL}/api/community/posts", json=body, headers=HEADERS, timeout=30)
        assert cr.status_code in (200, 201), cr.text
        post = cr.json()
        pid = post.get("post_id")
        assert pid

        # Delete
        dr = requests.delete(f"{BASE_URL}/api/community/posts/{pid}", headers=HEADERS, timeout=15)
        assert dr.status_code in (200, 204), dr.text

        # Verify gone from feed (best-effort): list feed and ensure pid not present in first page
        fr = requests.get(f"{BASE_URL}/api/community/feed", headers=HEADERS, timeout=15)
        assert fr.status_code == 200
        ids = [p.get("post_id") for p in fr.json().get("items", [])]
        assert pid not in ids, f"Deleted post still in feed: {pid}"


# ---------------------------- AI in-language smoke ----------------------------
class TestAIInLanguage:
    def test_meals_generate_respects_accept_language_es(self):
        # Use a date far in the future to avoid colliding with cached generations
        from datetime import date, timedelta
        d = (date.today() + timedelta(days=37)).isoformat()
        payload = {"date": d, "goal_mode": "balanced", "notes": ""}
        r = requests.post(
            f"{BASE_URL}/api/meals/generate",
            json=payload,
            headers=_auth_headers("es"),
            timeout=90,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # Pull all string text fields out for inspection
        flat = []
        def walk(x):
            if isinstance(x, str):
                flat.append(x)
            elif isinstance(x, dict):
                for v in x.values(): walk(v)
            elif isinstance(x, list):
                for v in x: walk(v)
        walk(data)
        joined = " ".join(flat).lower()
        # Spanish-ish hints
        es_hits = sum(1 for k in [" de ", " con ", " y ", " la ", " el ", " para ", "almuerzo", "cena", "desayuno", "pollo", "verduras"] if k in joined)
        assert es_hits >= 3, f"Meal plan not in Spanish (hits={es_hits}). Sample: {joined[:300]}"

    def test_workouts_generate_respects_accept_language_it(self):
        from datetime import date, timedelta
        d = (date.today() + timedelta(days=41)).isoformat()
        payload = {"date": d, "goal_mode": "strength", "notes": ""}
        r = requests.post(
            f"{BASE_URL}/api/workouts/generate",
            json=payload,
            headers=_auth_headers("it"),
            timeout=90,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        flat = []
        def walk(x):
            if isinstance(x, str):
                flat.append(x)
            elif isinstance(x, dict):
                for v in x.values(): walk(v)
            elif isinstance(x, list):
                for v in x: walk(v)
        walk(data)
        joined = " ".join(flat).lower()
        it_hits = sum(1 for k in [" di ", " con ", " e ", " la ", " il ", " per ", "ripetizioni", "serie", "riscaldamento", "esercizio", "minuti"] if k in joined)
        assert it_hits >= 3, f"Workout plan not in Italian (hits={it_hits}). Sample: {joined[:300]}"

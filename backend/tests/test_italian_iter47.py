"""Iteration 47 - Italian (IT) language support.

Verifies:
  - POST /api/translate with target='it' returns Italian text and uses
    traditional Catholic liturgical Italian for well-known prayers.
  - GET /api/liturgy/lauds/saturday with Accept-Language: it returns Italian
    section text.
"""
import time
import pytest


# ---- /api/translate with target='it' ---------------------------------------

class TestTranslateItalian:
    def test_translate_basic_phrases_to_italian(self, base_url, auth_client):
        payload = {
            "texts": ["Sign of the Cross", "Our Father", "Glory Be"],
            "target": "it",
        }
        r = auth_client.post(f"{base_url}/api/translate", json=payload, timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["target"] == "it"
        items = data["items"]
        assert isinstance(items, list) and len(items) == 3
        # All should be non-empty and differ from the English input.
        for orig, tr in zip(payload["texts"], items):
            assert tr and tr.strip()
            assert tr.lower() != orig.lower(), f"not translated: {tr}"
        joined = " ".join(items).lower()
        # Traditional liturgical Italian markers
        assert "segno della croce" in joined, f"expected Italian Sign of the Cross, got: {items}"
        assert "padre nostro" in joined, f"expected Italian Our Father, got: {items}"
        assert ("gloria al padre" in joined) or ("gloria" in joined and "padre" in joined), \
            f"expected Italian Gloria, got: {items}"

    def test_translate_cache_hit_is_fast(self, base_url, auth_client):
        payload = {"texts": ["Sign of the Cross"], "target": "it"}
        # Warm
        auth_client.post(f"{base_url}/api/translate", json=payload, timeout=120)
        # Second call should be cached and fast
        t0 = time.time()
        r = auth_client.post(f"{base_url}/api/translate", json=payload, timeout=30)
        dt = time.time() - t0
        assert r.status_code == 200
        assert dt < 5.0, f"cached translate too slow: {dt:.2f}s"
        assert "segno della croce" in r.json()["items"][0].lower()

    def test_translate_english_target_passthrough(self, base_url, auth_client):
        payload = {"texts": ["Sign of the Cross"], "target": "en"}
        r = auth_client.post(f"{base_url}/api/translate", json=payload, timeout=30)
        assert r.status_code == 200
        assert r.json()["items"] == payload["texts"]

    def test_translate_requires_auth(self, base_url, anon_client):
        r = anon_client.post(
            f"{base_url}/api/translate",
            json={"texts": ["Hello"], "target": "it"},
            timeout=15,
        )
        assert r.status_code in (401, 403), r.text


# ---- /api/liturgy/lauds/saturday with Accept-Language: it -----------------

class TestLiturgyItalian:
    def _fetch(self, base_url, auth_client, lang):
        headers = {"Accept-Language": lang} if lang else {}
        return auth_client.get(
            f"{base_url}/api/liturgy/lauds/saturday",
            headers=headers,
            timeout=120,
        )

    def test_liturgy_lauds_saturday_italian(self, base_url, auth_client):
        r = self._fetch(base_url, auth_client, "it")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)
        # Concatenate all string content for keyword search
        def collect(o, bag):
            if isinstance(o, str):
                bag.append(o)
            elif isinstance(o, list):
                for it in o:
                    collect(it, bag)
            elif isinstance(o, dict):
                for v in o.values():
                    collect(v, bag)
        bag = []
        collect(data, bag)
        blob = " ".join(bag).lower()
        assert blob.strip(), "empty liturgy payload"
        # Italian liturgical markers (any one of these should be present)
        markers = [
            "o dio, vieni in mio aiuto",
            "gloria al padre",
            "signore",
            "padre",
            "salmo",
        ]
        hits = [m for m in markers if m in blob]
        assert hits, f"no Italian markers found in response. sample: {blob[:300]}"

    def test_liturgy_lauds_saturday_english_default(self, base_url, auth_client):
        r = self._fetch(base_url, auth_client, "en")
        assert r.status_code == 200, r.text
        data = r.json()
        bag = []
        def collect(o):
            if isinstance(o, str):
                bag.append(o)
            elif isinstance(o, list):
                for it in o: collect(it)
            elif isinstance(o, dict):
                for v in o.values(): collect(v)
        collect(data)
        blob = " ".join(bag).lower()
        # English should NOT contain Italian-specific phrase
        assert "o dio, vieni in mio aiuto" not in blob

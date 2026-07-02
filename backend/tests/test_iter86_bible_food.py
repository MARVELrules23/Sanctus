"""Iteration 86 tests — Bible translations (Vulgate) + food traditions endpoints."""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://divine-office.preview.emergentagent.com").rstrip("/")
TOKEN = "test_feat_aug25"
AUTH_HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------------- Bible translation param ----------------

class TestBibleTranslations:
    def test_default_douayrheims(self, api):
        r = api.get(f"{BASE_URL}/api/bible/chapter/john/1", headers=AUTH_HEADERS, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["translation"] == "douayrheims"
        assert "Douay-Rheims" in d["translation_label"]
        v1 = next((v for v in d["verses"] if v["n"] == 1), None)
        assert v1 is not None
        assert "beginning was the Word" in v1["text"] or "beginning" in v1["text"].lower()

    def test_vulgate_john(self, api):
        r = api.get(f"{BASE_URL}/api/bible/chapter/john/1?translation=vulgate",
                    headers=AUTH_HEADERS, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["translation"] == "vulgate"
        assert d["translation_label"] == "Vulgata Clementina (Latin)"
        v1 = next((v for v in d["verses"] if v["n"] == 1), None)
        assert v1 is not None
        assert v1["text"].lower().startswith("in principio erat verbum"), v1["text"]

    def test_douayrheims_explicit_still_english(self, api):
        r = api.get(f"{BASE_URL}/api/bible/chapter/john/1?translation=douayrheims",
                    headers=AUTH_HEADERS, timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d["translation"] == "douayrheims"
        v1 = next((v for v in d["verses"] if v["n"] == 1), None)
        assert v1 is not None
        # ensure NOT Latin
        assert "verbum" not in v1["text"].lower() or "word" in v1["text"].lower()

    def test_vulgate_deuterocanonical_tobit(self, api):
        r = api.get(f"{BASE_URL}/api/bible/chapter/tobit/1?translation=vulgate",
                    headers=AUTH_HEADERS, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["translation"] == "vulgate"
        assert d["book_slug"] == "tobit"
        assert len(d["verses"]) > 0
        # first verse should be Latin
        first = d["verses"][0]["text"].lower()
        # Latin Vulgate Tobias 1:1 begins "tobias ex tribu et civitate nephthali"
        assert any(w in first for w in ["tobias", "vir", "ex tribu"])


# ---------------- Food traditions ----------------

class TestFoodTraditions:
    def test_list_all(self, api):
        r = api.get(f"{BASE_URL}/api/food-traditions", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        items = data.get("items", [])
        assert len(items) == 12, f"expected 12, got {len(items)}"
        required = {"slug", "title", "origin", "occasion", "description", "ingredients", "steps"}
        for it in items:
            missing = required - set(it.keys())
            assert not missing, f"missing keys {missing} in {it.get('slug')}"
            assert isinstance(it["ingredients"], list) and len(it["ingredients"]) > 0
            assert isinstance(it["steps"], list) and len(it["steps"]) > 0

    def test_day_christmas(self, api):
        r = api.get(f"{BASE_URL}/api/food-traditions/day?date=2025-12-25", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        slugs = [x["slug"] for x in data.get("items", [])]
        assert "christmas-panettone" in slugs, slugs

    def test_day_lent_season(self, api):
        r = api.get(f"{BASE_URL}/api/food-traditions/day?date=2026-02-25", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # 2026-02-25 falls in Lent (Ash Wednesday 2026-02-18)
        assert (data.get("season") or "").lower() == "lent" or "lent" in (data.get("season") or "").lower()
        slugs = [x["slug"] for x in data.get("items", [])]
        assert "hot-cross-buns" in slugs, (data.get("season"), slugs)

    def test_bad_slug_returns_404(self, api):
        r = api.get(f"{BASE_URL}/api/food-traditions/king-cake", timeout=30)
        assert r.status_code == 404, r.status_code

    def test_valid_slug_kings_cake(self, api):
        r = api.get(f"{BASE_URL}/api/food-traditions/kings-cake-epiphany", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["slug"] == "kings-cake-epiphany"
        assert "Rosca" in d["title"] or "Three Kings" in d["title"]
        assert len(d["ingredients"]) > 0
        assert len(d["steps"]) > 0

    def test_bad_date_format(self, api):
        r = api.get(f"{BASE_URL}/api/food-traditions/day?date=not-a-date", timeout=30)
        assert r.status_code == 400

"""Iteration 83 — TLM (Tridentine) & Byzantine full-text readings endpoints.

Endpoints under test (both PUBLIC — no auth required):
  GET /api/tridentine/readings?date=YYYY-MM-DD
  GET /api/eastern/readings?date=YYYY-MM-DD&calendar=new

Contract: {available, proper_key, feria_fallback, epistle:{citation,verses[]},
gospel:{citation,verses[]}}
"""
import os
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _assert_shape(doc, expect_available=True):
    assert "available" in doc
    if not expect_available:
        return
    assert doc["available"] is True
    for k in ("proper_key", "feria_fallback", "epistle", "gospel"):
        assert k in doc, f"missing key {k}"
    for side in ("epistle", "gospel"):
        assert "citation" in doc[side] and doc[side]["citation"]
        assert "verses" in doc[side] and isinstance(doc[side]["verses"], list)
        assert len(doc[side]["verses"]) > 0, f"{side} verses empty"
        for v in doc[side]["verses"]:
            assert "n" in v and "text" in v
            assert isinstance(v["text"], str) and len(v["text"].strip()) > 0


# ------------------ TLM (Tridentine) ------------------
class TestTridentineReadings:
    def test_sunday_2026_06_14(self, api):
        r = api.get(f"{BASE_URL}/api/tridentine/readings", params={"date": "2026-06-14"})
        assert r.status_code == 200
        doc = r.json()
        _assert_shape(doc)
        assert doc["feria_fallback"] is False  # Sunday

    def test_major_feast_john_baptist_2026_06_24(self, api):
        r = api.get(f"{BASE_URL}/api/tridentine/readings", params={"date": "2026-06-24"})
        assert r.status_code == 200
        doc = r.json()
        _assert_shape(doc)
        assert doc["proper_key"] == "john-baptist"
        # Fixed feasts override the temporal — should NOT be a feria fallback.
        assert doc["feria_fallback"] is False
        assert "Isaiah" in doc["epistle"]["citation"]
        assert "Luke" in doc["gospel"]["citation"]

    def test_weekday_feria_fallback_2026_06_16(self, api):
        r = api.get(f"{BASE_URL}/api/tridentine/readings", params={"date": "2026-06-16"})
        assert r.status_code == 200
        doc = r.json()
        _assert_shape(doc)
        assert doc["feria_fallback"] is True

    def test_bad_date_returns_400(self, api):
        r = api.get(f"{BASE_URL}/api/tridentine/readings", params={"date": "2026-13-40"})
        assert r.status_code == 400

    def test_public_no_auth_required(self, api):
        # explicitly send NO Authorization header
        r = requests.get(f"{BASE_URL}/api/tridentine/readings", params={"date": "2026-06-14"})
        assert r.status_code == 200


# ------------------ Byzantine ------------------
class TestByzantineReadings:
    def test_sunday_after_pentecost_2026_06_14(self, api):
        r = api.get(f"{BASE_URL}/api/eastern/readings", params={"date": "2026-06-14", "calendar": "new"})
        assert r.status_code == 200
        doc = r.json()
        _assert_shape(doc)
        assert doc["feria_fallback"] is False

    def test_transfiguration_2026_08_06(self, api):
        r = api.get(f"{BASE_URL}/api/eastern/readings", params={"date": "2026-08-06", "calendar": "new"})
        assert r.status_code == 200
        doc = r.json()
        _assert_shape(doc)
        assert doc["proper_key"] == "transfiguration"
        assert "2 Peter" in doc["epistle"]["citation"] or "Peter" in doc["epistle"]["citation"]
        assert "Matthew 17" in doc["gospel"]["citation"]

    def test_cross_chapter_all_saints_2026_05_31(self, api):
        """Sunday of All Saints — Heb 11:33-12:2 must contain verses from BOTH ch 11 AND ch 12."""
        r = api.get(f"{BASE_URL}/api/eastern/readings", params={"date": "2026-05-31", "calendar": "new"})
        assert r.status_code == 200
        doc = r.json()
        _assert_shape(doc)
        assert doc["proper_key"] == "after-pentecost-1"
        verses = doc["epistle"]["verses"]
        chapters = {v.get("ch") for v in verses if "ch" in v}
        assert 11 in chapters, f"Missing chapter 11 verses; got chapters {chapters}"
        assert 12 in chapters, f"Missing chapter 12 verses; got chapters {chapters}"
        # Sanity: should include Hebrews 11:33 and 12:1 or 12:2
        vnums_ch11 = {v["n"] for v in verses if v.get("ch") == 11}
        vnums_ch12 = {v["n"] for v in verses if v.get("ch") == 12}
        assert 33 in vnums_ch11
        assert (1 in vnums_ch12) or (2 in vnums_ch12)

    def test_pascha_2026_04_05(self, api):
        r = api.get(f"{BASE_URL}/api/eastern/readings", params={"date": "2026-04-05", "calendar": "new"})
        assert r.status_code == 200
        doc = r.json()
        _assert_shape(doc)
        assert doc["proper_key"] == "pascha"
        assert "Acts 1" in doc["epistle"]["citation"]
        assert "John 1" in doc["gospel"]["citation"]

    def test_weekday_feria_fallback(self, api):
        # 2026-06-16 is Tuesday — should fall back to preceding Sunday
        r = api.get(f"{BASE_URL}/api/eastern/readings", params={"date": "2026-06-16", "calendar": "new"})
        assert r.status_code == 200
        doc = r.json()
        _assert_shape(doc)
        assert doc["feria_fallback"] is True

    def test_bad_date_returns_400(self, api):
        r = api.get(f"{BASE_URL}/api/eastern/readings", params={"date": "not-a-date"})
        assert r.status_code == 400

    def test_public_no_auth_required(self, api):
        r = requests.get(f"{BASE_URL}/api/eastern/readings", params={"date": "2026-06-14"})
        assert r.status_code == 200
